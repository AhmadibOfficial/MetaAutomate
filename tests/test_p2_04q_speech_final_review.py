"""P2-04q independent post-inference review uses synthetic fixture only."""
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import wave

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from app.creative_audio_assets import AudioAssetHold, canonical, sha_file, validate_job
from app.creative_speech_final_review import verify_speech_review

def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def sample(tmp_path):
    folder=tmp_path/"quarantine"
    folder.mkdir(mode=0o700)
    wav=folder/"generated.wav"
    with wave.open(str(wav),"wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(22050)
        f.writeframes(b"\x01\x00"*22050)
    wav.chmod(0o600)
    digest=sha_file(wav)
    job={
        "schema_version":1,"project_id":"voice_project","asset_id":"voice_sample",
        "kind":"speech","use_case":"film",
        "prompt":"An original educational documentary narration.",
        "style_direction":"Warm clear English narrator","target_seconds":1,
        "language":"en","model_checkpoint_sha256":"e"*64,
        "model_license_evidence_sha256":"a"*64,
        "content_rights_evidence_sha256":"f"*64,
        "authorization_sha256":"1"*64,"voice_likeness":"none",
        "voice_consent_evidence_sha256":None,"artist_reference":"none",
        "artist_rights_evidence_sha256":None,"distribution_authorized":False}
    job_hash=validate_job(job)["job_sha256"]
    receipt={
        "job_sha256":job_hash,"output_sha256":digest,
        "generation_mode":"OPERATOR_ATTESTED_LOCAL_MODEL",
        "state":"QUARANTINED_PENDING_INDEPENDENT_REVIEW",
        "published":False,"distribution_authorized":False}
    now=datetime.now(timezone.utc).replace(microsecond=0)
    review={
        "schema_version":1,"asset_id":"voice_sample","job_sha256":job_hash,
        "output_sha256":digest,"producer_id":"producer_1",
        "reviewer_id":"reviewer_2","licence_evidence_sha256":"a"*64,
        "consent_evidence_sha256":None,"safety_report_sha256":"c"*64,
        "transcript_review_sha256":"d"*64,
        "human_listened":True,"language_review_passed":True,
        "intelligibility_review_passed":True,
        "transcript_match_review_passed":True,
        "rights_review_passed":True,"consent_review_passed":True,
        "safety_review_passed":True,"decision":"ACCEPTED",
        "issued_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at":(now+timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    key=Ed25519PrivateKey.generate()
    review["signature"]=b64(key.sign(canonical(review)))
    pub=b64(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
    return wav,job,receipt,review,pub,now

def check(parts):
    wav,job,receipt,review,pub,now=parts
    return verify_speech_review(job,receipt,review,wav,reviewer_public_key=pub,now=now)

def test_signed_human_review_keeps_distribution_off(tmp_path):
    result=check(sample(tmp_path))
    assert result["status"]=="SIGNED_HUMAN_REVIEW_CLAIM_RECORDED_STILL_QUARANTINED"
    assert result["publication_authorized"] is False
    assert result["model_execution_independently_verified"] is False

def test_output_tampering_blocks_review(tmp_path):
    items=list(sample(tmp_path))
    items[0].write_bytes(b"tampered")
    with pytest.raises(AudioAssetHold,match="altered"):
        check(items)

def test_independent_reviewer_required(tmp_path):
    items=list(sample(tmp_path))
    items[3]["reviewer_id"]=items[3]["producer_id"]
    with pytest.raises(AudioAssetHold,match="independent"):
        check(items)

def test_review_signature_binds_evidence(tmp_path):
    items=list(sample(tmp_path))
    items[3]["safety_report_sha256"]="0"*64
    with pytest.raises(AudioAssetHold,match="signature"):
        check(items)

def test_expired_review_not_allowed(tmp_path):
    items=list(sample(tmp_path))
    items[-1] += timedelta(days=2)
    with pytest.raises(AudioAssetHold,match="expired"):
        check(items)

def test_no_model_claim_from_fixture(tmp_path):
    items=list(sample(tmp_path))
    items[2]["generation_mode"]="TEST_ONLY_FAKE_RUNNER_NOT_AI"
    with pytest.raises(AudioAssetHold,match="Only quarantined"):
        check(items)
