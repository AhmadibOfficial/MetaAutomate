"""P2-04p - offline audio asset contracts for a future Creative Studio.

No speech/music/SFX model is invoked here. The verifier checks local output
integrity and PCM audio metadata, NOT that AI inference, licensing, consent or
human safety review occurred. All assets remain quarantined; no publish API.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import math
import re
import stat
import struct
import wave

class AudioAssetHold(ValueError):
    """Reject unverified or unauthorised creative audio."""

SHA = re.compile(r"^[0-9a-f]{64}$")
SLUG = re.compile(r"^[a-z][a-z0-9_-]{7,63}$")
LANG = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
KINDS = {"speech", "music", "sound_effect"}
USE_CASES = {"film", "advertisement", "campaign", "social", "audiobook", "podcast"}
MAX_WAV = 130_000_000
FIELDS = {
    "schema_version", "project_id", "asset_id", "kind", "use_case",
    "prompt", "target_seconds", "language",
    "model_checkpoint_sha256", "model_license_evidence_sha256",
    "content_rights_evidence_sha256", "authorization_sha256",
    "voice_likeness", "voice_consent_evidence_sha256",
    "artist_reference", "artist_rights_evidence_sha256",
    "distribution_authorized",
}
RECEIPT_FIELDS = {
    "schema_version", "asset_id", "job_sha256", "model_checkpoint_sha256",
    "output_sha256", "output_bytes", "generation_mode",
    "state", "published", "distribution_authorized",
}

def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")

def sha_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def hash_valid(value) -> bool:
    return type(value) is str and SHA.fullmatch(value) is not None

def validate_job(job: dict) -> dict:
    """Validate a plan. Successful validation is NOT permission to run a model."""
    if type(job) is not dict or set(job) != FIELDS:
        raise AudioAssetHold("Unexpected audio job schema")
    if type(job["schema_version"]) is not int or job["schema_version"] != 1:
        raise AudioAssetHold("Unsupported schema version")
    for name in ("project_id", "asset_id"):
        value = job[name]
        if type(value) is not str or SLUG.fullmatch(value) is None:
            raise AudioAssetHold("Invalid project/asset identity")
    if (type(job["kind"]) is not str or job["kind"] not in KINDS or
        type(job["use_case"]) is not str or job["use_case"] not in USE_CASES):
        raise AudioAssetHold("Unknown audio kind or use case")
    prompt = job["prompt"]
    if type(prompt) is not str or not 12 <= len(prompt.strip()) <= 800:
        raise AudioAssetHold("Prompt must be bounded and meaningful")
    duration = job["target_seconds"]
    if type(duration) is not int or not 1 <= duration <= 600:
        raise AudioAssetHold("Audio duration must be 1-600 seconds")
    lang = job["language"]
    if type(lang) is not str or LANG.fullmatch(lang) is None:
        raise AudioAssetHold("Invalid language code")
    for field in ("model_checkpoint_sha256", "model_license_evidence_sha256",
                  "content_rights_evidence_sha256", "authorization_sha256"):
        if not hash_valid(job[field]):
            raise AudioAssetHold("Missing or invalid approval/evidence digest")
    if job["distribution_authorized"] is not False:
        raise AudioAssetHold("Audio distribution is forbidden")
    likeness = job["voice_likeness"]
    artist = job["artist_reference"]
    if (type(likeness) is not str or likeness not in ("none", "consented") or
        type(artist) is not str or artist not in ("none", "licensed")):
        raise AudioAssetHold("Voice or artist reference not declared")
    if likeness == "consented":
        if job["kind"] != "speech" or not hash_valid(job["voice_consent_evidence_sha256"]):
            raise AudioAssetHold("Voice likeness requires documented consent")
    elif job["voice_consent_evidence_sha256"] is not None:
        raise AudioAssetHold("Unexpected voice consent reference")
    if artist == "licensed":
        if job["kind"] != "music" or not hash_valid(job["artist_rights_evidence_sha256"]):
            raise AudioAssetHold("Artist reference requires evidence and licensed music")
    elif job["artist_rights_evidence_sha256"] is not None:
        raise AudioAssetHold("Unexpected artist reference evidence")
    return {
        "status": "PLAN_VALIDATED_NOT_AUTHORIZED_FOR_INFERENCE",
        "job_sha256": sha256(canonical(job)).hexdigest(),
        "kind": job["kind"], "use_case": job["use_case"],
        "release_authorized": False, "published": False,
    }

def private_wav(path: Path) -> None:
    if (not path.is_absolute() or path.is_symlink() or
        not path.is_file() or path.suffix != ".wav" or
        path.resolve() != path or
        not 44 < path.stat().st_size <= MAX_WAV):
        raise AudioAssetHold("Missing, linked, oversized or unsafe WAV")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise AudioAssetHold("Audio file permissions must be private")
    directory = path.parent
    if directory.is_symlink() or stat.S_IMODE(directory.stat().st_mode) & 0o077:
        raise AudioAssetHold("Private quarantine directory required")

def pcm_metrics(path: Path, expected_seconds: int) -> dict:
    """Inspect actual 16-bit PCM samples, including unexpectedly silent output."""
    private_wav(path)
    try:
        with wave.open(str(path), "rb") as wav:
            channels, width, sample_rate, frame_count, coding, _ = wav.getparams()
            if (coding != "NONE" or channels not in (1, 2) or width != 2
                or sample_rate not in (44100, 48000)):
                raise AudioAssetHold("Only 16-bit 44.1/48k mono/stereo PCM is supported")
            seconds = frame_count / sample_rate
            if not math.isfinite(seconds) or abs(seconds - expected_seconds) > 0.25:
                raise AudioAssetHold("Actual audio duration differs from job")
            energy, peak, samples, clipping = 0, 0, 0, 0
            while True:
                raw = wav.readframes(4096)
                if not raw:
                    break
                if len(raw) % 2:
                    raise AudioAssetHold("Truncated audio samples")
                for (amplitude,) in struct.iter_unpack("<h", raw):
                    a = abs(amplitude)
                    energy += a*a
                    peak = max(peak, a)
                    clipping += a >= 32760
                    samples += 1
    except (OSError, EOFError, wave.Error) as exc:
        raise AudioAssetHold("Invalid PCM audio") from exc
    if samples != frame_count*channels or peak == 0:
        raise AudioAssetHold("Audio empty, truncated or entirely silent")
    rms_dbfs = 20 * math.log10(max((energy / samples) ** 0.5, 1) / 32768)
    return {
        "format": "WAV_PCM16",
        "channels": channels, "sample_rate": sample_rate,
        "frames": frame_count, "duration_seconds": seconds,
        "peak_amplitude": peak,
        "rms_dbfs": round(rms_dbfs, 2),
        "clipping_fraction": round(clipping / samples, 8),
    }

def verify_asset(job: dict, receipt: dict, output: Path) -> dict:
    """Output integrity only. An apparently real receipt is NOT inference proof."""
    plan = validate_job(job)
    if type(receipt) is not dict or set(receipt) != RECEIPT_FIELDS:
        raise AudioAssetHold("Unexpected inference receipt")
    expected = {
        "schema_version": 1,
        "asset_id": job["asset_id"],
        "job_sha256": plan["job_sha256"],
        "model_checkpoint_sha256": job["model_checkpoint_sha256"],
        "generation_mode": "OPERATOR_ATTESTED_LOCAL_MODEL",
        "state": "QUARANTINED_PENDING_INDEPENDENT_REVIEW",
        "published": False, "distribution_authorized": False,
    }
    if any(type(receipt.get(k)) is not type(v) or receipt.get(k) != v
           for k, v in expected.items()):
        raise AudioAssetHold("Output receipt mismatches authorized plan/quarantine")
    if not hash_valid(receipt["output_sha256"]):
        raise AudioAssetHold("Output hash missing")
    private_wav(output)
    if (type(receipt["output_bytes"]) is not int or
        receipt["output_bytes"] != output.stat().st_size or
        sha_file(output) != receipt["output_sha256"]):
        raise AudioAssetHold("Output file integrity mismatch")
    metrics = pcm_metrics(output, job["target_seconds"])
    return {
        "schema_version": 1, "asset_id": job["asset_id"], "kind": job["kind"],
        "output_sha256": receipt["output_sha256"],
        "receipt_sha256": sha256(canonical(receipt)).hexdigest(),
        "job_sha256": plan["job_sha256"],
        "media": metrics,
        "acceptance": "PCM_INTEGRITY_ONLY_PENDING_MODEL_AND_RIGHTS_EVIDENCE",
        "model_inference_independently_verified": False,
        "voice_consent_independently_authenticated": False,
        "music_rights_independently_authenticated": False,
        "content_safety_verified": False,
        "human_final_reviewed": False,
        "published": False, "distribution_authorized": False,
    }
