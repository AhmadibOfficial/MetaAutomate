"""P2-04q human-review signing tests, using an explicitly synthetic WAV fixture."""
from datetime import datetime, timezone
import base64
from hashlib import sha256
import wave

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption, PublicFormat,
)
import pytest

from app.creative_audio_assets import AudioAssetHold, validate_job, sha_file
from app.creative_speech_review_signing import (
    prepare_review_request, sign_completed_review, BOOL_FIELDS,
)
from app.creative_speech_final_review import verify_speech_review

def setup(tmp_path):
    root=tmp_path/"private"
    root.mkdir(mode=0o700)
    output=root/"generated.wav"
    with wave.open(str(output),"wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(b"\x01\x00"*22050)
    output.chmod(0o600)
    job={
        "schema_version":1,"project_id":"voice_project","asset_id":"voice_sample",
        "kind":"speech","use_case":"film","prompt":"Original documentary narration sample.",
        "style_direction":"Warm natural English reading",
        "target_seconds":1,"language":"en",
        "model_checkpoint_sha256":"a"*64,"model_license_evidence_sha256":"b"*64,
        "content_rights_evidence_sha256":"c"*64,"authorization_sha256":"d"*64,
        "voice_likeness":"none","voice_consent_evidence_sha256":None,
        "artist_reference":"none","artist_rights_evidence_sha256":None,
        "distribution_authorized":False,
    }
    receipt={
        "job_sha256":validate_job(job)["job_sha256"],
        "output_sha256":sha_file(output),
        "generation_mode":"OPERATOR_ATTESTED_LOCAL_MODEL",
        "state":"QUARANTINED_PENDING_INDEPENDENT_REVIEW",
        "published":False,"distribution_authorized":False,
    }
    reviewer=Ed25519PrivateKey.generate()
    key_file=root/"reviewer.pem"
    key_file.write_bytes(reviewer.private_bytes(
        Encoding.PEM,PrivateFormat.PKCS8,NoEncryption()))
    key_file.chmod(0o600)
    pub=base64.urlsafe_b64encode(reviewer.public_key().public_bytes(
        Encoding.Raw,PublicFormat.Raw)).rstrip(b"=").decode()
    req=prepare_review_request(
        job,receipt,output,producer_id="producer_one",reviewer_id="reviewer_two")
    return job,receipt,output,key_file,pub,req

def complete(req):
    for flag in BOOL_FIELDS:
        req[flag]=True
    req["safety_report_sha256"]="e"*64
    req["transcript_review_sha256"]="f"*64
    req["decision"]="ACCEPTED"

def test_unsigned_checklist_requires_human_review(tmp_path):
    job,receipt,audio,key,pub,req=setup(tmp_path)
    assert req["decision"]=="REJECTED"
    assert all(req[flag] is False for flag in BOOL_FIELDS)
    with pytest.raises(AudioAssetHold,match="Human must"):
        sign_completed_review(job,receipt,req,audio,key)

def test_signed_complete_review_stays_quarantined(tmp_path):
    job,receipt,audio,key,pub,req=setup(tmp_path)
    complete(req)
    signed=sign_completed_review(job,receipt,req,audio,key)
    result=verify_speech_review(job,receipt,signed,audio,reviewer_public_key=pub)
    assert result["status"]=="SIGNED_HUMAN_REVIEW_CLAIM_RECORDED_STILL_QUARANTINED"
    assert result["publication_authorized"] is False
    assert result["model_execution_independently_verified"] is False

def test_forged_human_review_cannot_be_signed(tmp_path):
    job,receipt,audio,key,pub,req=setup(tmp_path)
    complete(req)
    req["rights_review_passed"]=False
    with pytest.raises(AudioAssetHold,match="Human must"):
        sign_completed_review(job,receipt,req,audio,key)

def test_modified_audio_cannot_be_signed(tmp_path):
    job,receipt,audio,key,pub,req=setup(tmp_path)
    complete(req)
    audio.write_bytes(b"tampered")
    with pytest.raises(AudioAssetHold):
        sign_completed_review(job,receipt,req,audio,key)

def test_private_key_must_be_owner_only(tmp_path):
    job,receipt,audio,key,pub,req=setup(tmp_path)
    complete(req)
    key.chmod(0o644)
    with pytest.raises(AudioAssetHold,match="Private absolute"):
        sign_completed_review(job,receipt,req,audio,key)

def test_review_signature_bound_to_report_digest(tmp_path):
    job,receipt,audio,key,pub,req=setup(tmp_path)
    complete(req)
    signed=sign_completed_review(job,receipt,req,audio,key)
    signed["transcript_review_sha256"]="0"*64
    with pytest.raises(AudioAssetHold,match="signature"):
        verify_speech_review(job,receipt,signed,audio,reviewer_public_key=pub)
