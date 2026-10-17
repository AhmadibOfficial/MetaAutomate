"""P2-04q: optional offline Piper speech adapter. Disabled by default.

Not an online API. The operator must separately verify model/engine licenses,
voice rights, independent human authorization and actual egress isolation.
No model downloads, public endpoint or automatic publishing.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from uuid import uuid4

from app.creative_audio_assets import (
    AudioAssetHold, canonical, sha_file, validate_job, verify_asset,
)
from app.creative_speech_authorization import verify_speech_approval

def _file(path: Path, *, max_bytes: int):
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve() != path or not 0 < path.stat().st_size <= max_bytes
        or stat.S_IMODE(path.stat().st_mode) & 0o077):
        raise AudioAssetHold("Missing, public, linked or oversized trusted input")

def _engine(path: Path):
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve() != path or not 0 < path.stat().st_size <= 100_000_000
        or stat.S_IMODE(path.stat().st_mode) & 0o077
        or not (stat.S_IMODE(path.stat().st_mode) & stat.S_IXUSR)):
        raise AudioAssetHold("Private owner-executable pinned speech engine required")

def _directory(path: Path):
    if (not path.is_absolute() or path.is_symlink() or not path.is_dir()
        or path.resolve() != path or stat.S_IMODE(path.stat().st_mode) & 0o077):
        raise AudioAssetHold("Private non-symlink directory required")

def render_speech(job: dict, *, text_path: Path, model_path: Path,
                  model_config: Path, engine_path: Path,
                  quarantine_root: Path, runner=None,
                  authorization: dict | None = None,
                  owner_public_key: str = "", reviewer_public_key: str = "") -> dict:
    """Local input/weights only. Test injection cannot claim model inference."""
    if (os.environ.get("MAT_SPEECH_OFFLINE_EXECUTION_ENABLED") != "1"
        or os.environ.get("MAT_SPEECH_NETWORK_ISOLATED") != "1"
        or os.environ.get("MAT_SPEECH_LICENSE_REVIEWED") != "1"
        or os.environ.get("MAT_SPEECH_INDEPENDENT_HUMAN_APPROVAL") != "1"):
        raise AudioAssetHold("P2-04q speech execution HOLD: independent approvals required")
    validation=validate_job(job)
    if job["kind"] != "speech":
        raise AudioAssetHold("Only speech generation is supported")
    _directory(quarantine_root)
    _file(text_path, max_bytes=8192)
    _file(model_path, max_bytes=2_000_000_000)
    _file(model_config, max_bytes=128_000)
    _engine(engine_path)
    if model_path.suffix != ".onnx" or model_config.name != model_path.name + ".json":
        raise AudioAssetHold("Offline Piper voice needs matching ONNX and JSON")
    if engine_path.name not in {"piper", "piper.exe"}:
        raise AudioAssetHold("Unrecognized pinned speech engine")
    if sha_file(model_path) != job["model_checkpoint_sha256"]:
        raise AudioAssetHold("Voice model checkpoint digest mismatch")
    text=text_path.read_text(encoding="utf-8")
    if not 1 <= len(text.strip()) <= 6000 or "\x00" in text:
        raise AudioAssetHold("Speech text length or encoding invalid")
    requested = job["prompt"]
    if requested != text.strip():
        raise AudioAssetHold("Authorized text must match speech job prompt")
    signed_approval_sha256 = None
    if runner is None:
        if authorization is None:
            raise AudioAssetHold("Signed owner and independent reviewer authorization required")
        signed_approval_sha256 = verify_speech_approval(
            job, authorization, config_sha256=sha_file(model_config),
            engine_sha256=sha_file(engine_path), text_sha256=sha_file(text_path),
            owner_public_key=owner_public_key,
            reviewer_public_key=reviewer_public_key)
    output_dir=quarantine_root/uuid4().hex
    output_dir.mkdir(mode=0o700)
    try:
        target=output_dir/"generated.wav"
        if runner is not None:
            runner(text,model_path,model_config,target)
            mode="TEST_ONLY_FAKE_RUNNER_NOT_AI"
        else:
            # Verify the actual Linux namespace; environment flags alone
            # cannot prove that no external network interface is reachable.
            from app.creative_speech_runtime_preflight import kernel_network_evidence
            kernel_network_evidence()
            # Must run in an independently network-denied container/process.
            # Piper version/CLI is operator-pinned. No package or voice retrieval.
            cmd=[str(engine_path),"--model",str(model_path),
                 "--config",str(model_config),"--output_file",str(target)]
            try:
                subprocess.run(cmd,input=text,encoding="utf-8",
                    check=True,timeout=180,capture_output=True,
                    env={"PATH":"/usr/bin:/bin","HOME":str(output_dir),
                         "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"})
            except (OSError,subprocess.SubprocessError) as exc:
                raise AudioAssetHold("Local speech synthesis failed") from exc
            mode="OPERATOR_ATTESTED_LOCAL_MODEL"
        if target.is_symlink() or not target.is_file():
            raise AudioAssetHold("No regular audio output")
        target.chmod(0o600)
        receipt={
            "schema_version":1,"asset_id":job["asset_id"],
            "job_sha256":validation["job_sha256"],
            "model_checkpoint_sha256":job["model_checkpoint_sha256"],
            "output_sha256":sha_file(target),
            "output_bytes":target.stat().st_size,
            "generation_mode":mode,
            "state":"QUARANTINED_PENDING_INDEPENDENT_REVIEW",
            "published":False,"distribution_authorized":False,
        }
        if runner is None:
            verified=verify_asset(job,receipt,target)
            status=verified["acceptance"]
        else:
            # Fixtures must never pass the inference mode check.
            status="TEST_ONLY_NOT_MODEL_EVIDENCE"
        info={"receipt":receipt,"config_sha256":sha_file(model_config),
              "engine_sha256":sha_file(engine_path),
              "text_sha256":sha_file(text_path),"status":status,
              "independently_proven_inference":False,
              "licence_authenticated_by_code":False,
              "signed_approval_verified_by_code":signed_approval_sha256 is not None,
              "signed_approval_sha256":signed_approval_sha256,
              "published":False}
        (output_dir/"evidence.json").write_bytes(canonical(info)+b"\n")
        (output_dir/"evidence.json").chmod(0o600)
        return info
    except Exception:
        shutil.rmtree(output_dir)
        raise
