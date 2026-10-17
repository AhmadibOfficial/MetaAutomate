"""P2-04q independent signed human speech review. No publication route.

Attests the signer's claims tied to exact private audio bytes; it does NOT
prove language quality, rights, consent, safety scan or live inference.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from app.creative_local_generation import _b64, _time
from app.creative_audio_assets import canonical, private_wav, sha_file
from app.creative_offline_speech import SpeechHold

class SpeechReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: StrictInt = 1
    job_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    final_wav_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    requester_id: str = Field(min_length=8, max_length=80)
    reviewer_id: str = Field(min_length=8, max_length=80)
    transcript_alignment_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    language_quality_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_license_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    rights_and_consent_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    safety_review_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    human_listened_to_whole_recording: StrictBool
    transcript_match_checked: StrictBool
    language_quality_checked: StrictBool
    licence_and_consent_checked: StrictBool
    content_safety_checked: StrictBool
    decision: str = Field(pattern=r"^(REVIEWED|REJECTED)$")
    issued_at: str
    expires_at: str
    signature: str

    @model_validator(mode="after")
    def check_independent_reviewer(self):
        if self.schema_version != 1 or self.requester_id == self.reviewer_id:
            raise ValueError("An independent speech reviewer is required")
        return self

def inspect_audio_review(job: dict, receipt: dict, review: SpeechReview,
                         audio_path: Path, public_key: str, *,
                         now: datetime | None = None) -> dict:
    if (type(job) is not dict or type(receipt) is not dict or
        receipt.get("generation_mode") != "OPERATOR_ATTESTED_LOCAL_MODEL" or
        receipt.get("state") != "QUARANTINED_PENDING_INDEPENDENT_REVIEW" or
        receipt.get("published") is not False or
        receipt.get("distribution_authorized") is not False):
        raise SpeechHold("Only private operator-attested audio may be reviewed")
    expected_job_hash = sha256(canonical(job)).hexdigest()
    if (receipt.get("job_sha256") != expected_job_hash or
        review.job_sha256 != expected_job_hash or
        review.final_wav_sha256 != receipt.get("output_sha256")):
        raise SpeechHold("Review is not bound to the exact job and WAV")
    private_wav(audio_path)
    if sha_file(audio_path) != review.final_wav_sha256:
        raise SpeechHold("Audio changed since review evidence")
    issued, expiry = _time(review.issued_at), _time(review.expires_at)
    current = now or datetime.now(timezone.utc)
    if (current.tzinfo is None or
        not issued <= current.astimezone(timezone.utc) < expiry or
        not timedelta(minutes=1) <= expiry - issued <= timedelta(hours=24)):
        raise SpeechHold("Expired or invalid signed speech review")
    data = canonical(review.model_dump(exclude={"signature"}))
    try:
        Ed25519PublicKey.from_public_bytes(_b64(public_key, 32)).verify(
            _b64(review.signature, 64), data)
    except (InvalidSignature, ValueError) as exc:
        raise SpeechHold("Invalid final speech review signature") from exc
    reviewed = all((
        review.human_listened_to_whole_recording,
        review.transcript_match_checked,
        review.language_quality_checked,
        review.licence_and_consent_checked,
        review.content_safety_checked,
        review.decision == "REVIEWED",
    ))
    return {
        "schema_version": 1, "job_sha256": expected_job_hash,
        "final_wav_sha256": review.final_wav_sha256,
        "signed_human_review_claim_sha256": sha256(data).hexdigest(),
        "status": ("HUMAN_SPEECH_REVIEW_CLAIM_RECORDED_PENDING_SEPARATE_RELEASE"
                   if reviewed else "HOLD_REVIEW_REJECTED_OR_INCOMPLETE"),
        "independent_model_inference_proof": False,
        "language_quality_verified_by_software": False,
        "licence_legality_verified_by_software": False,
        "distribution_authorized": False, "published": False,
    }
