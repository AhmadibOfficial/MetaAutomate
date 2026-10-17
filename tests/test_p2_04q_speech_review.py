"""Speech final-review signature tests; dummy audio is NEVER a real model output."""
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.creative_audio_assets import canonical
from app.creative_offline_speech import SpeechHold
from app.creative_speech_review import SpeechReview, inspect_audio_review

def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def setup(tmp_path):
    folder = tmp_path/"private"
    folder.mkdir(mode=0o700)
    wav = folder/"generated.wav"
    wav.write_bytes(b"DUMMY-NOT-REAL-SPEECH" * 20)
    wav.chmod(0o600)
    job = {"fake_test": "job-bound dummy transcript"}
    job_sha = sha256(canonical(job)).hexdigest()
    wav_sha = sha256(wav.read_bytes()).hexdigest()
    receipt = {
        "job_sha256": job_sha,
        "output_sha256": wav_sha,
        "generation_mode": "OPERATOR_ATTESTED_LOCAL_MODEL",
        "state": "QUARANTINED_PENDING_INDEPENDENT_REVIEW",
        "published": False, "distribution_authorized": False,
    }
    now = datetime.now(timezone.utc).replace(microsecond=0)
    review = {
        "schema_version": 1, "job_sha256": job_sha, "final_wav_sha256": wav_sha,
        "requester_id": "requester_one", "reviewer_id": "reviewer_two",
        "transcript_alignment_evidence_sha256": "1"*64,
        "language_quality_evidence_sha256": "2"*64,
        "model_license_evidence_sha256": "3"*64,
        "rights_and_consent_evidence_sha256": "4"*64,
        "safety_review_evidence_sha256": "5"*64,
        "human_listened_to_whole_recording": True,
        "transcript_match_checked": True,
        "language_quality_checked": True,
        "licence_and_consent_checked": True,
        "content_safety_checked": True, "decision": "REVIEWED",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now+timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    key = Ed25519PrivateKey.generate()
    review["signature"] = b64(key.sign(canonical(review)))
    pub = b64(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    return job, receipt, review, wav, pub, now

def test_valid_signer_claim_never_means_real_inference_or_release(tmp_path):
    job, receipt, review, wav, pub, now = setup(tmp_path)
    outcome = inspect_audio_review(
        job, receipt, SpeechReview.model_validate(review), wav, pub, now=now)
    assert outcome["status"].startswith("HUMAN_SPEECH_REVIEW_CLAIM_")
    assert outcome["independent_model_inference_proof"] is False
    assert outcome["language_quality_verified_by_software"] is False
    assert outcome["distribution_authorized"] is False

def test_tampered_recording_rejected(tmp_path):
    job, receipt, review, wav, pub, now = setup(tmp_path)
    wav.write_bytes(b"tampered-dummy-recording")
    with pytest.raises(SpeechHold, match="Audio changed"):
        inspect_audio_review(job, receipt, SpeechReview.model_validate(review), wav, pub, now=now)

def test_invalid_signature_rejected(tmp_path):
    job, receipt, review, wav, pub, now = setup(tmp_path)
    review["language_quality_evidence_sha256"]="0"*64
    with pytest.raises(SpeechHold, match="signature"):
        inspect_audio_review(job, receipt, SpeechReview.model_validate(review), wav, pub, now=now)

def test_expired_review_rejected(tmp_path):
    job, receipt, review, wav, pub, now = setup(tmp_path)
    with pytest.raises(SpeechHold, match="Expired"):
        inspect_audio_review(
            job, receipt, SpeechReview.model_validate(review), wav, pub,
            now=now + timedelta(days=3))

def test_same_requester_reviewer_rejected(tmp_path):
    _, _, review, _, _, _ = setup(tmp_path)
    review["reviewer_id"] = "requester_one"
    with pytest.raises(ValueError, match="independent"):
        SpeechReview.model_validate(review)

def test_rejected_decision_never_grants_release(tmp_path):
    job, receipt, review, wav, pub, now = setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    review["decision"] = "REJECTED"
    raw = canonical({k:v for k,v in review.items() if k != "signature"})
    review["signature"]=b64(key.sign(raw))
    pub=b64(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    result = inspect_audio_review(
        job, receipt, SpeechReview.model_validate(review), wav, pub, now=now)
    assert result["status"]=="HOLD_REVIEW_REJECTED_OR_INCOMPLETE"
