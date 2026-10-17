"""P2-04q optional, locally authorized Piper ONNX speech inference.

OFF by default. No voice files, downloads, installed inference dependencies,
customer data, public API, distribution, or automatic licence clearance.
A signed operator statement and valid WAV are not independent AI proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from app.creative_audio_assets import AudioAssetHold, canonical, sha_file, validate_job, verify_asset
from app.creative_local_generation import _b64, _time, read_json

class SpeechHold(ValueError):
    pass

HEXDIGEST = re.compile(r"^[a-f0-9]{64}$")
ROLE_ORDER = ("OWNER", "INDEPENDENT_REVIEWER")

class SignedApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: StrictInt = 1
    job_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    piper_binary_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    issued_at: str
    expires_at: str
    prompt_human_checked: StrictBool
    model_license_human_checked: StrictBool
    content_rights_human_checked: StrictBool
    voice_consent_human_checked: StrictBool
    isolated_worker_human_checked: StrictBool
    release_authorized: StrictBool
    signatures: list[dict]

def _regular(path: Path, *, max_bytes: int, suffix: str | None = None) -> None:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve() != path or not 0 < path.stat().st_size <= max_bytes
        or (suffix is not None and not str(path).endswith(suffix))):
        raise SpeechHold("A required absolute regular local file is missing or untrusted")

def _private_root(path: Path) -> Path:
    if (not path.is_absolute() or path.is_symlink() or not path.is_dir()
        or path.resolve() != path or stat.S_IMODE(path.stat().st_mode) & 0o077):
        raise SpeechHold("Quarantine must exist as a trusted owner-only directory")
    return path

def validate_materials(job: dict, *, model: Path, config: Path, model_card: Path,
                       rights: Path, consent: Path | None, binary: Path) -> dict:
    plan = validate_job(job)
    if job["kind"] != "speech":
        raise SpeechHold("This worker supports speech only, not music/SFX")
    _regular(model, max_bytes=5_000_000_000, suffix=".onnx")
    _regular(config, max_bytes=1_000_000, suffix=".onnx.json")
    _regular(model_card, max_bytes=64_000)
    _regular(rights, max_bytes=64_000)
    _regular(binary, max_bytes=100_000_000)
    if binary.name not in ("piper", "piper.exe"):
        raise SpeechHold("Only an explicitly hashed Piper executable is permitted")
    if not os.access(binary, os.X_OK):
        raise SpeechHold("Piper executable is unavailable")
    if model.parent != config.parent or config.name != model.name + ".json":
        raise SpeechHold("Local ONNX model/config must be paired")
    if model_card.parent != model.parent:
        raise SpeechHold("Model licence card must accompany voice checkpoint")
    if sha_file(model) != job["model_checkpoint_sha256"]:
        raise SpeechHold("Model checkpoint SHA-256 mismatch")
    if sha_file(model_card) != job["model_license_evidence_sha256"]:
        raise SpeechHold("Model licence evidence hash mismatch")
    if sha_file(rights) != job["content_rights_evidence_sha256"]:
        raise SpeechHold("Content rights evidence hash mismatch")
    if job["voice_likeness"] == "consented":
        if consent is None:
            raise SpeechHold("Voice likeness consent document required")
        _regular(consent, max_bytes=64_000)
        if sha_file(consent) != job["voice_consent_evidence_sha256"]:
            raise SpeechHold("Consent document hash mismatch")
    elif consent is not None:
        raise SpeechHold("Unnecessary consent document supplied")
    # JSON parsing is for format validation, NOT a licence decision.
    # Piper voice JSON normally contains finite floating-point inference
    # defaults: the stricter signed-job JSON reader would reject those.
    try:
        def reject_duplicates(pairs):
            output = {}
            for key, value in pairs:
                if key in output:
                    raise SpeechHold("Duplicate Piper config key")
                output[key] = value
            return output
        def reject_nonfinite(_):
            raise SpeechHold("Non-finite Piper model config value")
        descriptor = json.loads(
            config.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates, parse_constant=reject_nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise SpeechHold("Invalid ONNX voice configuration") from exc
    if (type(descriptor) is not dict or type(descriptor.get("audio")) is not dict
        or type(descriptor["audio"].get("sample_rate")) is not int
        or descriptor["audio"]["sample_rate"] not in
        (16000, 22050, 24000, 32000, 44100, 48000)):
        raise SpeechHold("Missing supported Piper audio sample rate")
    # If the checkpoint declares a language, it must agree with the job.
    language = descriptor.get("language")
    if type(language) is dict and type(language.get("code")) is str:
        checkpoint_lang = language["code"].split("_")[0].split("-")[0].lower()
        job_lang = job["language"].split("-")[0].lower()
        if checkpoint_lang != job_lang:
            raise SpeechHold("Job language disagrees with voice checkpoint")
    return {
        "job_sha256": plan["job_sha256"],
        "config_sha256": sha_file(config),
        "binary_sha256": sha_file(binary),
        "model_sha256": sha_file(model),
        "expected_sample_rate": descriptor["audio"]["sample_rate"],
    }

def approve(job: dict, approval: SignedApproval, material: dict, *,
            owner_key: str, reviewer_key: str, now: datetime | None = None) -> str:
    if (approval.schema_version != 1 or
        approval.job_sha256 != material["job_sha256"] or
        approval.model_config_sha256 != material["config_sha256"] or
        approval.piper_binary_sha256 != material["binary_sha256"] or
        not all((approval.prompt_human_checked, approval.model_license_human_checked,
                 approval.content_rights_human_checked, approval.voice_consent_human_checked,
                 approval.isolated_worker_human_checked)) or
        approval.release_authorized is not False):
        raise SpeechHold("Current signed authorization is required")
    issued, expiry = _time(approval.issued_at), _time(approval.expires_at)
    current = now or datetime.now(timezone.utc)
    if (current.tzinfo is None or not issued <= current.astimezone(timezone.utc) < expiry
        or not timedelta(minutes=1) <= expiry-issued <= timedelta(minutes=30)):
        raise SpeechHold("Approval must be current and valid for <=30 minutes")
    if (len(approval.signatures) != 2 or
        any(type(x) is not dict or set(x) != {"role", "signature"}
            for x in approval.signatures) or
        tuple(x["role"] for x in approval.signatures) != ROLE_ORDER):
        raise SpeechHold("Two independent ordered signature claims required")
    k1, k2 = _b64(owner_key, 32), _b64(reviewer_key, 32)
    if k1 == k2:
        raise SpeechHold("Owner and reviewer must have independent signing keys")
    payload = canonical(approval.model_dump(exclude={"signatures"}))
    for key, claim in zip((k1, k2), approval.signatures):
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(
                _b64(claim["signature"], 64), payload)
        except (InvalidSignature, ValueError) as exc:
            raise SpeechHold("Invalid approval signature") from exc
    return sha256(payload).hexdigest()

def generate(job: dict, approval: SignedApproval, *, model: Path, config: Path,
             model_card: Path, rights: Path, consent: Path | None,
             binary: Path, quarantine: Path, owner_key: str, reviewer_key: str,
             now: datetime | None = None) -> dict:
    """Actually call a local Piper binary after all approval gates, if installed.

    The runtime must independently enforce blocked network access, e.g. isolated
    container/network namespace; environment flags are merely attestations.
    """
    if (os.environ.get("MAT_CREATIVE_SPEECH_OFFLINE_ENABLED") != "1" or
        os.environ.get("MAT_CREATIVE_NETWORK_ISOLATED") != "1"):
        raise SpeechHold("Real speech inference disabled until operator authorization")
    material = validate_materials(
        job, model=model, config=config, model_card=model_card,
        rights=rights, consent=consent, binary=binary)
    approval_hash = approve(job, approval, material,
                            owner_key=owner_key, reviewer_key=reviewer_key, now=now)
    root = _private_root(quarantine)
    folder = root / uuid4().hex
    folder.mkdir(mode=0o700)
    try:
        output = folder / "generated.wav"
        env = dict(os.environ)
        env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                    "HF_HUB_DISABLE_TELEMETRY": "1"})
        try:
            subprocess.run(
                [str(binary), "--model", str(model), "--config", str(config),
                 "--output_file", str(output)],
                input=job["prompt"].strip()+"\n", text=True,
                cwd=folder, env=env, capture_output=True,
                check=True, timeout=180)
        except (OSError, subprocess.SubprocessError) as exc:
            raise SpeechHold("Local Piper process failed or timed out") from exc
        if output.is_symlink() or not output.is_file():
            raise SpeechHold("Piper did not produce a private regular WAV")
        output.chmod(0o600)
        receipt = {
            "schema_version": 1,
            "asset_id": job["asset_id"],
            "job_sha256": material["job_sha256"],
            "model_checkpoint_sha256": material["model_sha256"],
            "output_sha256": sha_file(output),
            "output_bytes": output.stat().st_size,
            "generation_mode": "OPERATOR_ATTESTED_LOCAL_MODEL",
            "state": "QUARANTINED_PENDING_INDEPENDENT_REVIEW",
            "published": False, "distribution_authorized": False,
        }
        # Verify that trusted model/binary/evidence files remained unchanged.
        if (sha_file(model) != material["model_sha256"] or
            sha_file(config) != material["config_sha256"] or
            sha_file(binary) != material["binary_sha256"] or
            sha_file(model_card) != job["model_license_evidence_sha256"] or
            sha_file(rights) != job["content_rights_evidence_sha256"] or
            (consent is not None and
             sha_file(consent) != job["voice_consent_evidence_sha256"])):
            raise SpeechHold("Signed inference inputs changed during execution")
        evidence = verify_asset(job, receipt, output)
        if evidence["media"]["sample_rate"] != material["expected_sample_rate"]:
            raise SpeechHold("WAV sample rate disagrees with signed model config")
        path = folder / "receipt.json"
        path.write_bytes(canonical(receipt) + b"\n")
        path.chmod(0o600)
        run = {
            "schema_version": 1, "job_sha256": material["job_sha256"],
            "private_quarantine_receipt_id": folder.name,
            "signed_approval_payload_sha256": approval_hash,
            "model_checkpoint_sha256": material["model_sha256"],
            "model_config_sha256": material["config_sha256"],
            "piper_binary_sha256": material["binary_sha256"],
            "voice_model_card_sha256": sha_file(model_card),
            "output_sha256": receipt["output_sha256"],
            "output_receipt_sha256": sha256(canonical(receipt)).hexdigest(),
            "measurement": evidence["media"],
            "operator_claimed_local_inference": True,
            "independently_verified_model_inference": False,
            "license_legality_verified_by_code": False,
            "language_quality_human_verified": False,
            "content_safety_verified": False,
            "final_human_approval": False,
            "distribution_authorized": False, "published": False,
        }
        log = folder / "operator-run.json"
        log.write_bytes(canonical(run) + b"\n")
        log.chmod(0o600)
        return run
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="P2-04q signed offline Piper voice worker")
    for name in ("job", "approval", "model", "config", "model-card",
                 "rights", "binary", "quarantine"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--consent", type=Path)
    args = parser.parse_args(argv)
    try:
        job = read_json(args.job)
        approval = SignedApproval.model_validate(read_json(args.approval))
        run = generate(
            job, approval, model=args.model, config=args.config,
            model_card=args.model_card, rights=args.rights,
            consent=args.consent, binary=args.binary,
            quarantine=args.quarantine,
            owner_key=os.environ.get("MAT_CREATIVE_OWNER_VERIFY_KEY", ""),
            reviewer_key=os.environ.get("MAT_CREATIVE_REVIEWER_VERIFY_KEY", ""),
        )
    except (SpeechHold, AudioAssetHold, ValueError, OSError) as exc:
        print("Speech generation HOLD: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(run, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
