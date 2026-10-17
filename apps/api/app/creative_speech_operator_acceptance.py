"""P2-04q local operator acceptance runner, fail-closed without approved assets.

Not a public service or autonomous approval tool. Execute *only* on the
externally isolated, authorised host with owner/reviewer signed job evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from app.creative_audio_assets import AudioAssetHold
from app.creative_speech_offline import render_speech
from app.creative_speech_runtime_preflight import verify_operator_preflight

def private_json(path:Path)->dict:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.stat().st_size>65536 or
        stat.S_IMODE(path.stat().st_mode)&0o077):
        raise AudioAssetHold("Owner-controlled private absolute JSON evidence required")
    data=json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise AudioAssetHold("Expected JSON object")
    return data

def main(argv=None)->int:
    parser=argparse.ArgumentParser(
        description="Strictly authorised OFFLINE speech acceptance; no model downloads")
    parser.add_argument("--repo-root",type=Path,required=True)
    parser.add_argument("--expected-commit",required=True)
    parser.add_argument("--license-evidence",type=Path,required=True)
    parser.add_argument("--rights-evidence",type=Path,required=True)
    parser.add_argument("--consent-evidence",type=Path)
    parser.add_argument("--job",type=Path,required=True)
    parser.add_argument("--authorization",type=Path,required=True)
    parser.add_argument("--text",type=Path,required=True)
    parser.add_argument("--voice-onnx",type=Path,required=True)
    parser.add_argument("--piper-bin",type=Path,required=True)
    parser.add_argument("--quarantine",type=Path,required=True)
    parser.add_argument("--owner-public-key",required=True,
                        help="URL-safe Ed25519 public key, externally pinned")
    parser.add_argument("--reviewer-public-key",required=True,
                        help="First registered reviewer Ed25519 public key")
    parser.add_argument("--second-reviewer-public-key",required=True,
                        help="Second independent reviewer Ed25519 public key")
    args=parser.parse_args(argv)
    try:
        if os.environ.get("MAT_SPEECH_OPERATOR_ISOLATION_EVIDENCE_CONFIRMED")!="1":
            raise AudioAssetHold("Verified external no-egress runtime required")
        job=private_json(args.job)
        approval=private_json(args.authorization)
        model_config=Path(str(args.voice_onnx)+".json")
        preflight=verify_operator_preflight(
            repo_root=args.repo_root, expected_commit=args.expected_commit,
            job=job, authorization=approval,
            voice_model=args.voice_onnx, voice_config=model_config,
            engine=args.piper_bin, script=args.text,
            license_evidence=args.license_evidence,
            rights_evidence=args.rights_evidence,
            consent_evidence=args.consent_evidence,
            owner_public_key=args.owner_public_key,
            reviewer_public_key=args.reviewer_public_key,
            second_reviewer_public_key=args.second_reviewer_public_key)
        receipt=render_speech(
            job,
            text_path=args.text,
            model_path=args.voice_onnx,
            model_config=model_config,
            engine_path=args.piper_bin,
            quarantine_root=args.quarantine,
            authorization=approval,
            owner_public_key=args.owner_public_key,
            reviewer_public_key=args.reviewer_public_key,
            second_reviewer_public_key=args.second_reviewer_public_key,
        )
    except (AudioAssetHold,OSError,ValueError,json.JSONDecodeError) as exc:
        print("SPEECH ACCEPTANCE HOLD: "+str(exc),file=sys.stderr)
        return 2
    if (receipt.get("signed_approval_verified_by_code") is not True
        or receipt.get("published") is not False):
        print("SPEECH ACCEPTANCE HOLD: missing signed approval",file=sys.stderr)
        return 2
    print(json.dumps({
        "status":"OUTPUT_CREATED_PENDING_INDEPENDENT_POST_REVIEW",
        "preflight":preflight,
        "receipt":receipt["receipt"],
        "config_sha256":receipt["config_sha256"],
        "engine_sha256":receipt["engine_sha256"],
        "signed_approval_sha256":receipt["signed_approval_sha256"],
        "model_execution_independently_proven":False,
        "distribution_authorized":False,
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
