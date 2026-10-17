"""P2-04q source contract tests. Mock Piper is NEVER genuine inference evidence."""
from datetime import datetime, timedelta, timezone
import base64
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import wave

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.creative_audio_assets import canonical, sha_file
from app.creative_offline_speech import (
    SpeechHold, SignedApproval, validate_materials, approve, generate,
)

def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

def _timestamp(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")

def fixture(tmp_path):
    checkpoint_root = tmp_path / "voice"
    checkpoint_root.mkdir()
    model = checkpoint_root / "voice.onnx"
    model.write_bytes(b"FAKE-TEST-CHECKPOINT-NOT-A-MODEL")
    config = checkpoint_root / "voice.onnx.json"
    config.write_text('{"audio":{"sample_rate":22050}}')
    card = checkpoint_root / "MODEL_CARD"
    card.write_text("TEST LICENSE PLACEHOLDER - NOT REVIEWED")
    rights = tmp_path / "rights.txt"
    rights.write_text("TEST RIGHTS DECLARATION ONLY")
    executable = tmp_path / "piper"
    executable.write_bytes(b"mock test executable")
    executable.chmod(0o700)
    output = tmp_path / "quarantine"
    output.mkdir(mode=0o700)
    job = {
        "schema_version": 1, "project_id": "project_demo",
        "asset_id": "speech_demo", "kind": "speech", "use_case": "podcast",
        "prompt": "This is a synthetic fixture and not a real generated voice.",
        "target_seconds": 1, "language": "en",
        "style_direction": "warm, measured narration",
        "model_checkpoint_sha256": sha_file(model),
        "model_license_evidence_sha256": sha_file(card),
        "content_rights_evidence_sha256": sha_file(rights),
        "authorization_sha256": "a"*64,
        "voice_likeness": "none", "voice_consent_evidence_sha256": None,
        "artist_reference": "none", "artist_rights_evidence_sha256": None,
        "distribution_authorized": False,
    }
    materials = validate_materials(
        job, model=model, config=config, model_card=card,
        rights=rights, consent=None, binary=executable)
    owner, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "schema_version": 1, "job_sha256": materials["job_sha256"],
        "model_config_sha256": materials["config_sha256"],
        "piper_binary_sha256": materials["binary_sha256"],
        "issued_at": _timestamp(now), "expires_at": _timestamp(now+timedelta(minutes=10)),
        "prompt_human_checked": True, "model_license_human_checked": True,
        "content_rights_human_checked": True, "voice_consent_human_checked": True,
        "isolated_worker_human_checked": True, "release_authorized": False,
    }
    raw = canonical(payload)
    payload["signatures"] = [
        {"role": "OWNER", "signature": b64(owner.sign(raw))},
        {"role": "INDEPENDENT_REVIEWER", "signature": b64(reviewer.sign(raw))},
    ]
    keys = [
        b64(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
        for key in (owner, reviewer)
    ]
    args = dict(
        model=model, config=config, model_card=card, rights=rights,
        consent=None, binary=executable, quarantine=output,
        owner_key=keys[0], reviewer_key=keys[1], now=now,
    )
    return job, SignedApproval.model_validate(payload), args

def test_valid_two_signer_approval_only_attests(tmp_path):
    job, approval, args = fixture(tmp_path)
    materials = validate_materials(
        job, model=args["model"], config=args["config"], model_card=args["model_card"],
        rights=args["rights"], consent=None, binary=args["binary"])
    result = approve(job, approval, materials, owner_key=args["owner_key"],
                     reviewer_key=args["reviewer_key"], now=args["now"])
    assert len(result) == 64

def test_no_runtime_opt_in_blocks_inference(tmp_path, monkeypatch):
    job, approval, args = fixture(tmp_path)
    monkeypatch.delenv("MAT_CREATIVE_SPEECH_OFFLINE_ENABLED", raising=False)
    with pytest.raises(SpeechHold, match="disabled"):
        generate(job, approval, **args)

def test_expired_authorization_blocks(tmp_path):
    job, approval, args = fixture(tmp_path)
    materials = validate_materials(
        job, model=args["model"], config=args["config"], model_card=args["model_card"],
        rights=args["rights"], consent=None, binary=args["binary"])
    with pytest.raises(SpeechHold, match="current"):
        approve(job, approval, materials, owner_key=args["owner_key"],
                reviewer_key=args["reviewer_key"], now=args["now"]+timedelta(hours=1))

def test_tampered_signed_job_blocks(tmp_path):
    job, approval, args = fixture(tmp_path)
    job["prompt"] = "A different signed utterance should never be authorized."
    materials = validate_materials(
        job, model=args["model"], config=args["config"], model_card=args["model_card"],
        rights=args["rights"], consent=None, binary=args["binary"])
    with pytest.raises(SpeechHold, match="Current signed authorization"):
        approve(job, approval, materials, owner_key=args["owner_key"],
                reviewer_key=args["reviewer_key"], now=args["now"])

def test_tampered_model_blocks(tmp_path):
    job, approval, args = fixture(tmp_path)
    args["model"].write_bytes(b"model replaced")
    with pytest.raises(SpeechHold, match="checkpoint"):
        validate_materials(
            job, model=args["model"], config=args["config"],
            model_card=args["model_card"], rights=args["rights"],
            consent=None, binary=args["binary"])

def test_consent_required_for_likeness(tmp_path):
    job, approval, args = fixture(tmp_path)
    job["voice_likeness"] = "consented"
    job["voice_consent_evidence_sha256"] = "b"*64
    with pytest.raises(SpeechHold, match="consent"):
        validate_materials(
            job, model=args["model"], config=args["config"],
            model_card=args["model_card"], rights=args["rights"],
            consent=None, binary=args["binary"])

def test_mocked_runner_never_means_real_model_proof(tmp_path, monkeypatch):
    job, approval, args = fixture(tmp_path)
    monkeypatch.setenv("MAT_CREATIVE_SPEECH_OFFLINE_ENABLED", "1")
    monkeypatch.setenv("MAT_CREATIVE_NETWORK_ISOLATED", "1")
    def fake_subprocess(command, **kwargs):
        assert command[0] == str(args["binary"])
        output = Path(command[command.index("--output_file")+1])
        with wave.open(str(output), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(22050)
            stream.writeframes(struct.pack("<h", 2000) * 22050)
        return subprocess.CompletedProcess(command, 0, b"", b"")
    monkeypatch.setattr("app.creative_offline_speech.subprocess.run", fake_subprocess)
    receipt = generate(job, approval, **args)
    assert receipt["operator_claimed_local_inference"] is True
    assert receipt["independently_verified_model_inference"] is False
    assert receipt["license_legality_verified_by_code"] is False
    assert receipt["final_human_approval"] is False
    assert receipt["published"] is False
    assert receipt["measurement"]["sample_rate"] == 22050
    folders = list(args["quarantine"].iterdir())
    assert len(folders) == 1
    assert (folders[0] / "receipt.json").exists()

def test_no_voice_card_means_hold(tmp_path):
    job, approval, args = fixture(tmp_path)
    args["model_card"].unlink()
    with pytest.raises(SpeechHold, match="missing"):
        validate_materials(job, model=args["model"], config=args["config"],
                           model_card=args["model_card"], rights=args["rights"],
                           consent=None, binary=args["binary"])
