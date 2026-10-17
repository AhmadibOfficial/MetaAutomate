"""P2-04u: operator-only gated multimodal production command, never public.

No AI model download, neural inference, social post, customer media or
automatic release. Run with reviewed PRIVATE assets and externally enrolled
Ed25519 reviewer public keys inside an actual network-isolated sandbox.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
import subprocess
import sys

from app.creative_multimodal_studio import StudioHold
from app.creative_voice_quality import require_technically_ready_narration, VoiceQualityHold
from app.creative_multimodal_provenance import (
    verify_source_bundle, render_with_source_proofs,
)

SHA40 = re.compile(r"^[0-9a-f]{40}$")

def _read_private_json(path: Path, maximum: int = 1_000_000) -> dict:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve() != path or not 0 < path.stat().st_size <= maximum
        or stat.S_IMODE(path.stat().st_mode) & 0o077):
        raise StudioHold("Private absolute JSON evidence file required")
    def no_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise StudioHold("Duplicate key in creative evidence")
            result[key] = value
        return result
    try:
        doc = json.loads(path.read_text(encoding="utf-8"),
                         object_pairs_hook=no_duplicate_keys,
                         parse_constant=lambda v: (_ for _ in ()).throw(
                             StudioHold("Nonfinite numeric value forbidden")))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise StudioHold("Malformed private creative evidence JSON") from exc
    if type(doc) is not dict:
        raise StudioHold("Creative evidence must be a JSON object")
    return doc

def _pinned_checkout(root: Path, sha: str) -> None:
    if (not root.is_absolute() or root.is_symlink() or not root.is_dir()
        or root.resolve() != root or
        type(sha) is not str or SHA40.fullmatch(sha) is None):
        raise StudioHold("Exact clean Git checkout and commit SHA required")
    try:
        head = subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                              capture_output=True,text=True,check=True,timeout=15)
        dirty = subprocess.run(
            ["git","-C",str(root),"status","--porcelain","--untracked-files=no"],
            capture_output=True,text=True,check=True,timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        raise StudioHold("Unable to independently inspect private source revision") from exc
    if head.stdout.strip() != sha or dirty.stdout.strip():
        raise StudioHold("Source revision differs from clean approved source")

def _private_script(path:Path)->str:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve()!=path or not 1<=path.stat().st_size<=8192
        or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise StudioHold("Private original script or recognition transcript required")
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeError as exc:
        raise StudioHold("Invalid human-reviewed narration text") from exc

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Private multimodal production evidence gate")
    parser.add_argument("--repo-root",type=Path,required=True)
    parser.add_argument("--expected-commit",required=True)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--source-evidence",type=Path,required=True)
    parser.add_argument("--trusted-reviewer-keys",type=Path,required=True)
    parser.add_argument("--assets",type=Path,required=True)
    parser.add_argument("--quarantine",type=Path,required=True)
    parser.add_argument("--approved-script",type=Path)
    parser.add_argument("--recognized-transcript",type=Path)
    parser.add_argument("--render",action="store_true",
                        help="Explicit local offline finishing after evidence verification")
    args=parser.parse_args(argv)
    try:
        _pinned_checkout(args.repo_root,args.expected_commit)
        manifest=_read_private_json(args.manifest,65536)
        evidence=_read_private_json(args.source_evidence)
        keys=_read_private_json(args.trusted_reviewer_keys,65536)
        if args.render:
            if args.approved_script is None or args.recognized_transcript is None:
                raise StudioHold("Rendering requires a reviewed script and separately checked transcript")
            # Verify source receipt signatures before trusting the filename.
            verify_source_bundle(manifest,args.assets,evidence,reviewer_keys=keys)
            script=_private_script(args.approved_script)
            transcript=_private_script(args.recognized_transcript)
            voice_file=manifest["voice"]["file"]
            if type(voice_file) is not str:
                raise StudioHold("Invalid voice source filename")
            voice_qa=require_technically_ready_narration(
                args.assets/voice_file,script,transcript=transcript)
            result=render_with_source_proofs(
                manifest,args.assets,args.quarantine,evidence,reviewer_keys=keys)
            result["narration_technical_quality"]=voice_qa
        else:
            result=verify_source_bundle(
                manifest,args.assets,evidence,reviewer_keys=keys)
    except (StudioHold,OSError,ValueError,subprocess.SubprocessError) as exc:
        print("MULTIMODAL PRODUCTION HOLD: "+str(exc),file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
