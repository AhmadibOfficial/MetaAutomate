"""P2-04q negative and fake-runner tests: never real speech evidence."""
from hashlib import sha256
from pathlib import Path
import pytest
from app.creative_audio_assets import AudioAssetHold
from app.creative_speech_offline import render_speech

def setup(tmp_path, monkeypatch):
    root=tmp_path/"private"
    root.mkdir(mode=0o700)
    files={}
    for name,data in (
        ("voice.onnx",b"fixture weights"),("voice.onnx.json",b"{}"),
        ("piper",b"fixture executable"),
        ("speech.txt",b"A narrated educational scene, safe and original."),
    ):
        path=root/name
        path.write_bytes(data)
        path.chmod(0o600)
        files[name]=path
    q=root/"quarantine"
    q.mkdir(mode=0o700)
    job={
        "schema_version":1,"project_id":"test_film","asset_id":"voice_asset",
        "kind":"speech","use_case":"film",
        "prompt":"A narrated educational scene, safe and original.",
        "style_direction":"Warm calm neutral voice","target_seconds":1,
        "language":"en","model_checkpoint_sha256":sha256(b"fixture weights").hexdigest(),
        "model_license_evidence_sha256":"a"*64,
        "content_rights_evidence_sha256":"b"*64,
        "authorization_sha256":"c"*64,
        "voice_likeness":"none","voice_consent_evidence_sha256":None,
        "artist_reference":"none","artist_rights_evidence_sha256":None,
        "distribution_authorized":False,
    }
    for key in (
        "MAT_SPEECH_OFFLINE_EXECUTION_ENABLED", "MAT_SPEECH_NETWORK_ISOLATED",
        "MAT_SPEECH_LICENSE_REVIEWED", "MAT_SPEECH_INDEPENDENT_HUMAN_APPROVAL"
    ):
        monkeypatch.setenv(key,"1")
    return files,q,job

def call(files,q,job,runner=None):
    return render_speech(job,text_path=files["speech.txt"],
        model_path=files["voice.onnx"],model_config=files["voice.onnx.json"],
        engine_path=files["piper"],quarantine_root=q,runner=runner)

def test_fake_runner_never_claims_real_ai(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    def fake(text,model,config,out):
        out.write_bytes(b"Not generated AI audio"*4)
    evidence=call(files,q,job,runner=fake)
    assert evidence["status"]=="TEST_ONLY_NOT_MODEL_EVIDENCE"
    assert evidence["receipt"]["generation_mode"]=="TEST_ONLY_FAKE_RUNNER_NOT_AI"
    assert evidence["independently_proven_inference"] is False
    assert evidence["published"] is False

def test_defaults_fail_closed(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    monkeypatch.delenv("MAT_SPEECH_LICENSE_REVIEWED")
    with pytest.raises(AudioAssetHold,match="HOLD"):
        call(files,q,job)

def test_modified_model_rejected(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    files["voice.onnx"].write_bytes(b"tampered")
    with pytest.raises(AudioAssetHold,match="checkpoint digest"):
        call(files,q,job)

def test_text_must_match_authorized_prompt(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    files["speech.txt"].write_text("An unapproved different voice script.")
    with pytest.raises(AudioAssetHold,match="Authorized text"):
        call(files,q,job)

def test_must_be_speech(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    job["kind"]="music"
    with pytest.raises(AudioAssetHold,match="Only speech"):
        call(files,q,job)

def test_public_weights_rejected(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    files["voice.onnx"].chmod(0o644)
    with pytest.raises(AudioAssetHold,match="public"):
        call(files,q,job)

def test_symlink_checkpoint_rejected(tmp_path,monkeypatch):
    files,q,job=setup(tmp_path,monkeypatch)
    files["voice.onnx"].rename(files["voice.onnx"].parent/"actual.onnx")
    files["voice.onnx"].symlink_to(files["voice.onnx"].parent/"actual.onnx")
    with pytest.raises(AudioAssetHold,match="linked"):
        call(files,q,job)
