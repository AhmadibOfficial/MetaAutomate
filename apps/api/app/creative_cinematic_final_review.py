"""P2-04h independently signed review of the FINAL rendered film hash.

A valid signature attests a human decision; it does not authenticate rights,
prove a content scanner ran, or authorize distribution.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from app.creative_local_generation import _b64, _time, canonical
from app.creative_cinematic_preflight import CinematicHold, digest_file
from app.creative_cinematic_render import _locked_file, _locked_dir

class FinalReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: StrictInt = 1
    project_id: str = Field(min_length=8, max_length=64, pattern=r"^[a-z][a-z0-9_-]{7,63}$")
    final_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    producer_id: str = Field(min_length=8, max_length=80)
    reviewer_id: str = Field(min_length=8, max_length=80)
    safety_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    rights_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    voice_consent_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    audio_mix_review_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    captions_review_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scene_continuity_review_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    final_media_human_watched: StrictBool
    safety_review_human_checked: StrictBool
    rights_review_human_checked: StrictBool
    audio_caption_human_checked: StrictBool
    decision: str = Field(pattern=r"^(REVIEWED|REJECTED)$")
    issued_at: str
    expires_at: str
    signature: str

    @model_validator(mode="after")
    def independent_reviewer(self):
        if self.schema_version != 1 or self.producer_id == self.reviewer_id:
            raise ValueError("Independent final film reviewer required")
        return self

def inspect_final(receipt: dict, review: FinalReview, film: Path, *,
                  reviewer_public_key: str, now: datetime | None = None) -> dict:
    if type(receipt) is not dict:
        raise CinematicHold("Invalid receipt")
    if (receipt.get("state") != "QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW"
        or receipt.get("published") is not False
        or receipt.get("release_authorized") is not False
        or receipt.get("final_human_approval") is not False):
        raise CinematicHold("Receipt no longer pending independent review")
    for key in ("project_id", "final_sha256", "manifest_sha256"):
        if getattr(review, key) != receipt.get(key):
            raise CinematicHold("Final review references a different film")
    _locked_dir(film.parent)
    _locked_file(film, maximum=1_000_000_000)
    if digest_file(film) != receipt["final_sha256"]:
        raise CinematicHold("Final film digest changed")
    issued, expiry = _time(review.issued_at), _time(review.expires_at)
    current = now or datetime.now(timezone.utc)
    if (current.tzinfo is None or not issued <= current.astimezone(timezone.utc) < expiry
        or not timedelta(minutes=1) <= expiry-issued <= timedelta(hours=24)):
        raise CinematicHold("Signed human review is expired or invalid")
    payload = canonical(review.model_dump(exclude={"signature"}))
    try:
        Ed25519PublicKey.from_public_bytes(_b64(reviewer_public_key, 32)).verify(
            _b64(review.signature, 64), payload)
    except (InvalidSignature, ValueError) as exc:
        raise CinematicHold("Invalid human review signature") from exc
    claims_passed = all((
        review.final_media_human_watched,
        review.safety_review_human_checked,
        review.rights_review_human_checked,
        review.audio_caption_human_checked,
        review.decision == "REVIEWED",
    ))
    from hashlib import sha256
    return {
        "schema_version": 1,
        "final_sha256": receipt["final_sha256"],
        "review_claim_sha256": sha256(payload).hexdigest(),
        "signed_human_review_claim_authenticated": True,
        "status": ("HUMAN_REVIEW_CLAIM_RECORDED_PENDING_SEPARATE_RELEASE"
                   if claims_passed else "HOLD_REJECTED_OR_INCOMPLETE"),
        "scanner_execution_independently_verified": False,
        "rights_authenticity_verified_by_code": False,
        "published": False,
        "distribution_authorized": False,
    }
