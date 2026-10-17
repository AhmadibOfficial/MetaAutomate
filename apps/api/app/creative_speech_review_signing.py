"""P2-04q private offline final-review signing workflow.

This tool can only SIGN a review that a named independent human actually completed.
It does not listen to audio, authenticate licences, prove model inference,
send anything over a network, or authorize release.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import stat
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.creative_audio_assets import AudioAssetHold, canonical, sha_file, validate_job, private_wav
from app.creative_speech_authorization import _utc, _b64
from app.creative_speech_final_review import FIELDS, verify_speech_review

BOOL_FIELDS = (
    "human_listened", "language_review_passed", "intelligibility_review_passed",
    "transcript_match_review_passed", "rights_review_passed",
    "consent_review_passed", "safety_review_passed",
)

def _private(path: Path, limit: int) -> None:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve() != path or not 0 < path.stat().st_size <= limit
        or stat.S_IMODE(path.stat().st_mode) & 0o077):
        raise AudioAssetHold("Private absolute non-symlink review input required")

def load_json(path: Path) -> dict:
    _private(path, 65536)
    value=json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise AudioAssetHold("Expected a private JSON object")
    return value

def prepare_review_request(job:dict, receipt:dict, output:Path, *,
                           producer_id:str, reviewer_id:str,
                           now:datetime | None = None) -> dict:
    """Make an UNSIGNED checklist with every quality check initially FALSE."""
    plan=validate_job(job)
    private_wav(output)
    if (type(receipt) is not dict
        or receipt.get("job_sha256") != plan["job_sha256"]
        or receipt.get("output_sha256") != sha_file(output)
        or receipt.get("generation_mode") != "OPERATOR_ATTESTED_LOCAL_MODEL"
        or receipt.get("state") != "QUARANTINED_PENDING_INDEPENDENT_REVIEW"
        or receipt.get("published") is not False
        or receipt.get("distribution_authorized") is not False):
        raise AudioAssetHold("Unsigned review requires exact quarantined operator-attested speech job")
    if (type(producer_id) is not str or len(producer_id)<8
        or type(reviewer_id) is not str or len(reviewer_id)<8
        or producer_id == reviewer_id):
        raise AudioAssetHold("Independent identified human reviewer required")
    current=(now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    data={
        "schema_version":1,
        "asset_id":job["asset_id"],"job_sha256":plan["job_sha256"],
        "output_sha256":receipt["output_sha256"],
        "producer_id":producer_id,"reviewer_id":reviewer_id,
        "licence_evidence_sha256":job["model_license_evidence_sha256"],
        "consent_evidence_sha256":job["voice_consent_evidence_sha256"],
        "safety_report_sha256":None,
        "transcript_review_sha256":None,
        "decision":"REJECTED",
        "issued_at":current.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at":(current+timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    data.update({key:False for key in BOOL_FIELDS})
    return data

def sign_completed_review(job:dict, receipt:dict, reviewed:dict, output:Path,
                          key_path:Path, *,now:datetime|None=None)->dict:
    """Sign the human's completed checklist without inferring any True field."""
    if type(reviewed) is not dict or set(reviewed) != (FIELDS-{"signature"}):
        raise AudioAssetHold("Incomplete independent review request")
    if reviewed["decision"] != "ACCEPTED" or any(reviewed[key] is not True for key in BOOL_FIELDS):
        raise AudioAssetHold("Human must explicitly complete and accept all quality reviews")
    from app.creative_audio_assets import hash_valid
    for key in ("safety_report_sha256","transcript_review_sha256"):
        if not hash_valid(reviewed[key]):
            raise AudioAssetHold("Observed safety and transcript evidence digests required")
    _private(key_path, 8192)
    try:
        key=serialization.load_pem_private_key(key_path.read_bytes(),password=None)
    except (ValueError,TypeError) as exc:
        raise AudioAssetHold("Malformed local review private key") from exc
    if not isinstance(key,Ed25519PrivateKey):
        raise AudioAssetHold("Final review must use a private Ed25519 key")
    # Obtain public key WITHOUT exporting private key bytes or storing it in
    # the reviewed JSON. Public bytes only, used for post-sign verification.
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    import base64
    pub=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    pub_text=base64.urlsafe_b64encode(pub).rstrip(b"=").decode()
    payload=canonical(reviewed)
    signature=base64.urlsafe_b64encode(key.sign(payload)).rstrip(b"=").decode()
    signed={**reviewed,"signature":signature}
    # Use the existing independent output review verifier before yielding.
    result=verify_speech_review(job,receipt,signed,output,
                                reviewer_public_key=pub_text,now=now)
    if result["status"]!="SIGNED_HUMAN_REVIEW_CLAIM_RECORDED_STILL_QUARANTINED":
        raise AudioAssetHold("Final speech assessment not accepted")
    return signed

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description="Offline independently signed speech review")
    ap.add_argument("--job",type=Path,required=True)
    ap.add_argument("--receipt",type=Path,required=True)
    ap.add_argument("--audio",type=Path,required=True)
    ap.add_argument("--review",type=Path,required=True)
    ap.add_argument("--reviewer-key",type=Path,required=True)
    ap.add_argument("--signed-output",type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if (not args.signed_output.is_absolute() or args.signed_output.is_symlink()
            or args.signed_output.exists()):
            raise AudioAssetHold("New absolute signed output path required")
        reviewed=load_json(args.review)
        signed=sign_completed_review(
            load_json(args.job),load_json(args.receipt),reviewed,
            args.audio,args.reviewer_key)
        # Exclusive create prevents overwriting an earlier recorded review.
        fd=os.open(str(args.signed_output),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w") as f:
            json.dump(signed,f,indent=2,sort_keys=True)
            f.write("\n")
    except (AudioAssetHold,OSError,ValueError,KeyError) as exc:
        print("HOLD: "+str(exc),file=sys.stderr)
        return 2
    print("Signed review created locally. Distribution remains DISABLED.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
