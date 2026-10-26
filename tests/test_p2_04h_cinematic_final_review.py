"""Signed final review assertions, not actual scan/consent proof."""
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.creative_cinematic_final_review import FinalReview, inspect_final
from app.creative_cinematic_preflight import CinematicHold
from app.creative_local_generation import canonical

def urlsafe(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

def fixture(tmp_path):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    film = directory / "film.mp4"
    film.write_bytes(b"fixture only, no actual film inference")
    film.chmod(0o600)
    digest = sha256(film.read_bytes()).hexdigest()
    receipt = dict(project_id="sample_film", final_sha256=digest,
        manifest_sha256="a"*64, state="QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW",
        final_human_approval=False, published=False, release_authorized=False)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    review = dict(schema_version=1, project_id="sample_film", final_sha256=digest,
        manifest_sha256="a"*64, producer_id="producer_one", reviewer_id="reviewer_two",
        safety_evidence_sha256="b"*64, rights_evidence_sha256="c"*64,
        voice_consent_evidence_sha256="d"*64, audio_mix_review_sha256="e"*64,
        captions_review_sha256="f"*64, scene_continuity_review_sha256="1"*64,
        final_media_human_watched=True, safety_review_human_checked=True,
        rights_review_human_checked=True, audio_caption_human_checked=True,
        decision="REVIEWED", issued_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_at=(now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    key = Ed25519PrivateKey.generate()
    review["signature"] = urlsafe(key.sign(canonical(review)))
    pub = urlsafe(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    return film, receipt, review, pub, now

def test_valid_signature_still_not_distribution(tmp_path):
    film, receipt, review, pub, now = fixture(tmp_path)
    result = inspect_final(receipt, FinalReview.model_validate(review), film,
                           reviewer_public_key=pub, now=now)
    assert result["signed_human_review_claim_authenticated"] is True
    assert result["distribution_authorized"] is False
    assert result["rights_authenticity_verified_by_code"] is False

def test_modified_video_rejected(tmp_path):
    film, receipt, review, pub, now = fixture(tmp_path)
    film.write_bytes(b"tampered")
    with pytest.raises(CinematicHold, match="digest changed"):
        inspect_final(receipt, FinalReview.model_validate(review), film,
                      reviewer_public_key=pub, now=now)

def test_signature_tampering_rejected(tmp_path):
    film, receipt, review, pub, now = fixture(tmp_path)
    review["rights_evidence_sha256"] = "0"*64
    with pytest.raises(CinematicHold, match="signature"):
        inspect_final(receipt, FinalReview.model_validate(review), film,
                      reviewer_public_key=pub, now=now)

def test_review_for_another_film_rejected(tmp_path):
    film, receipt, review, pub, now = fixture(tmp_path)
    receipt["final_sha256"] = "0"*64
    with pytest.raises(CinematicHold, match="different film"):
        inspect_final(receipt, FinalReview.model_validate(review), film,
                      reviewer_public_key=pub, now=now)

def test_missing_independent_reviewer_rejected(tmp_path):
    _, _, review, _, _ = fixture(tmp_path)
    review["reviewer_id"] = review["producer_id"]
    with pytest.raises(ValueError, match="Independent"):
        FinalReview.model_validate(review)

def test_expired_review_rejected(tmp_path):
    film, receipt, review, pub, now = fixture(tmp_path)
    with pytest.raises(CinematicHold, match="expired"):
        inspect_final(receipt, FinalReview.model_validate(review), film,
                      reviewer_public_key=pub, now=now+timedelta(days=2))
