"""P2-04p offline source-only tests: deliberately synthetic PCM is not AI output."""
from __future__ import annotations
from hashlib import sha256
import math
from pathlib import Path
import struct
import wave

import pytest

from app.creative_audio_assets import (
    AudioAssetHold, canonical, pcm_metrics, sha_file, validate_job, verify_asset,
)

def make_job(kind="speech"):
    return {
        "schema_version": 1, "project_id": "sample_project",
        "asset_id": "sample_asset", "kind": kind, "use_case": "film",
        "prompt": "Create an original and clearly narrated scene for a film.",
        "target_seconds": 1, "language": "en",
        "model_checkpoint_sha256": "1"*64,
        "model_license_evidence_sha256": "2"*64,
        "content_rights_evidence_sha256": "3"*64,
        "authorization_sha256": "4"*64,
        "voice_likeness": "none",
        "voice_consent_evidence_sha256": None,
        "artist_reference": "none",
        "artist_rights_evidence_sha256": None,
        "distribution_authorized": False,
    }

def make_synthetic_wav(tmp_path, seconds=1, silent=False):
    parent=tmp_path/"quarantine"
    parent.mkdir(mode=0o700, exist_ok=True)
    audio=parent/"generated.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(44100)
        values = [
            0 if silent else int(6000 * math.sin(2 * math.pi * 440 * i/44100))
            for i in range(44100*seconds)
        ]
        stream.writeframes(b"".join(struct.pack("<h", n) for n in values))
    audio.chmod(0o600)
    return audio

def make_receipt(job, file):
    return {
        "schema_version":1, "asset_id": job["asset_id"],
        "job_sha256":sha256(canonical(job)).hexdigest(),
        "model_checkpoint_sha256":job["model_checkpoint_sha256"],
        "output_sha256":sha_file(file), "output_bytes":file.stat().st_size,
        "generation_mode":"OPERATOR_ATTESTED_LOCAL_MODEL",
        "state":"QUARANTINED_PENDING_INDEPENDENT_REVIEW",
        "published":False, "distribution_authorized":False,
    }

@pytest.mark.parametrize("kind", ["speech", "music", "sound_effect"])
def test_synthetic_audio_integrity_not_ai_proof(tmp_path, kind):
    job=make_job(kind)
    audio=make_synthetic_wav(tmp_path)
    review=verify_asset(job, make_receipt(job, audio), audio)
    assert review["kind"]==kind
    assert review["media"]["sample_rate"]==44100
    assert review["model_inference_independently_verified"] is False
    assert review["human_final_reviewed"] is False
    assert review["published"] is False

def test_tampered_bytes_rejected(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path)
    receipt=make_receipt(job,audio)
    with audio.open("ab") as output:
        output.write(b"tampered")
    with pytest.raises(AudioAssetHold, match="integrity mismatch"):
        verify_asset(job, receipt, audio)

def test_silence_not_accepted_as_generated_voice(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path,silent=True)
    with pytest.raises(AudioAssetHold, match="silent"):
        verify_asset(job, make_receipt(job,audio), audio)

def test_world_readable_wav_rejected(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path)
    audio.chmod(0o644)
    with pytest.raises(AudioAssetHold, match="permissions"):
        verify_asset(job, make_receipt(job,audio), audio)

def test_symlink_wav_rejected(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path)
    target=audio.parent/"source.wav"
    audio.rename(target)
    audio.symlink_to(target)
    with pytest.raises(AudioAssetHold, match="linked"):
        verify_asset(job, make_receipt(job, target), audio)

@pytest.mark.parametrize("field,value", [
    ("distribution_authorized", True),
    ("voice_likeness", ["x"]),
    ("artist_reference", ["x"]),
    ("kind", ["speech"]),
    ("kind", "unknown"),
    ("target_seconds", 0),
    ("model_checkpoint_sha256", "not-a-sha"),
    ("language", "../../../etc"),
    ("prompt", "hi"),
])
def test_unauthorized_or_invalid_job_rejected(field,value):
    job=make_job()
    job[field]=value
    with pytest.raises(AudioAssetHold):
        validate_job(job)

def test_voice_likeness_requires_consent():
    job=make_job()
    job["voice_likeness"]="consented"
    with pytest.raises(AudioAssetHold,match="consent"):
        validate_job(job)
    job["voice_consent_evidence_sha256"]="5"*64
    assert validate_job(job)["release_authorized"] is False

def test_artist_reference_requires_music_license():
    job=make_job("music")
    job["artist_reference"]="licensed"
    with pytest.raises(AudioAssetHold,match="Artist"):
        validate_job(job)
    job["artist_rights_evidence_sha256"]="a"*64
    assert validate_job(job)["published"] is False

def test_cannot_fake_model_receipt_as_test_fixture(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path)
    receipt=make_receipt(job,audio)
    receipt["generation_mode"]="TEST_FIXTURE"
    with pytest.raises(AudioAssetHold,match="receipt mismatches"):
        verify_asset(job,receipt,audio)

def test_receipt_for_different_job_rejected(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path)
    receipt=make_receipt(job,audio)
    job["prompt"]="A changed prompt and a different creative intent."
    with pytest.raises(AudioAssetHold,match="receipt mismatches"):
        verify_asset(job,receipt,audio)

def test_only_audio_wav_supported(tmp_path):
    job=make_job()
    audio=make_synthetic_wav(tmp_path)
    other=audio.with_suffix(".mp3")
    other.write_bytes(audio.read_bytes())
    other.chmod(0o600)
    with pytest.raises(AudioAssetHold,match="unsafe WAV"):
        verify_asset(job,make_receipt(job,other),other)
