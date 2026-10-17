"""Separate model-result safety/rights attestation: claims, not publishing."""
import base64
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.creative_local_generation import GenerationBlocked,canonical
from app.creative_output_review import Review,inspect_review

NOW=datetime(2026,10,17,0,0,tzinfo=timezone.utc)

def encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def setup_review(tmp_path):
    media=tmp_path/"media.png"
    media.write_bytes(b"\x89PNG\r\n\x1a\n"+b"CI-ONLY-FAKE-DATA" *5)
    digest=sha256(media.read_bytes()).hexdigest()
    key=Ed25519PrivateKey.generate()
    public=encode(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw))
    receipt={
        "generation_mode":"LOCAL_DIFFUSERS_REAL_INFERENCE",
        "real_ai_output_verified":True,
        "published":False,
        "output_state":"QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW",
        "job_sha256":"a"*64,"output_sha256":digest,
    }
    fields={
        "schema_version":1,"job_sha256":"a"*64,
        "output_sha256":digest,
        "reviewer_id":"reviewer-002","requester_id":"requester-001",
        "rights_review_artifact_sha256":"b"*64,
        "consent_review_artifact_sha256":"c"*64,
        "safety_scanner_report_sha256":"d"*64,
        "safety_scanner_passed":True,
        "visual_human_review_passed":True,
        "licence_rights_review_passed":True,
        "likeness_consent_review_passed":True,
        "decision":"REVIEWED",
        "issued_at":"2026-10-16T23:59:00Z",
        "expires_at":"2026-10-17T00:15:00Z",
    }
    def sign(changes=None):
        r={**fields,**(changes or {})}
        r["signature"]=encode(key.sign(canonical(r)))
        return Review.model_validate(r)
    return receipt,media,public,sign

def test_signed_review_remains_nonpublishing_claim(tmp_path):
    receipt,media,pub,sign=setup_review(tmp_path)
    result=inspect_review(receipt,sign(),reviewer_public_key=pub,
                         original_artifact=media,now=NOW)
    assert result["status"]=="HUMAN_REVIEW_CLAIM_RECORDED_PENDING_SEPARATE_RELEASE"
    assert result["external_distribution_authorized"] is False
    assert result["output_safety_verified_by_code"] is False
    assert result["license_authenticity_verified_by_code"] is False
    assert result["published"] is False

@pytest.mark.parametrize("edit",[
    {"safety_scanner_passed":False},
    {"visual_human_review_passed":False},
    {"licence_rights_review_passed":False},
    {"likeness_consent_review_passed":False},
    {"decision":"REJECTED"},
])
def test_a_failed_review_holds_media_without_creating_public_release(tmp_path,edit):
    receipt,media,pub,sign=setup_review(tmp_path)
    status=inspect_review(receipt,sign(edit),reviewer_public_key=pub,
                          original_artifact=media,now=NOW)
    assert status["status"]=="HOLD_REVIEW_REJECTED_OR_INCOMPLETE"
    assert status["external_distribution_authorized"] is False

@pytest.mark.parametrize("edit",[
    {"job_sha256":"b"*64},{"output_sha256":"e"*64},
    {"expires_at":"2026-10-17T03:00:00Z"},
    {"issued_at":"2026-10-17T00:01:00Z"},
])
def test_wrong_job_media_and_expired_approval_are_denied(tmp_path,edit):
    receipt,media,pub,sign=setup_review(tmp_path)
    with pytest.raises(GenerationBlocked):
        inspect_review(receipt,sign(edit),reviewer_public_key=pub,
                       original_artifact=media,now=NOW)

def test_reviewer_replay_with_changed_signature_or_media_denied(tmp_path):
    receipt,media,pub,sign=setup_review(tmp_path)
    r=sign()
    r.decision="REJECTED"
    with pytest.raises(GenerationBlocked):
        inspect_review(receipt,r,reviewer_public_key=pub,
                       original_artifact=media,now=NOW)
    r=sign()
    media.write_bytes(b"\x89PNG\r\n\x1a\n"+b"tampered")
    with pytest.raises(GenerationBlocked):
        inspect_review(receipt,r,reviewer_public_key=pub,
                       original_artifact=media,now=NOW)

def test_mock_generated_media_never_accepted_as_real(tmp_path):
    receipt,media,pub,sign=setup_review(tmp_path)
    receipt["generation_mode"]="TEST_ONLY_FAKE_RUNNER_NOT_AI"
    receipt["real_ai_output_verified"]=False
    with pytest.raises(GenerationBlocked):
        inspect_review(receipt,sign(),reviewer_public_key=pub,
                       original_artifact=media,now=NOW)

def test_self_review_blocked(tmp_path):
    _,_,_,sign=setup_review(tmp_path)
    with pytest.raises(ValidationError):
        sign({"reviewer_id":"requester-001"})
