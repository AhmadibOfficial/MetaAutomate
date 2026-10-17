"""Independent human output review AFTER local inference, never publication.

Output media stays in an owner-managed private quarantine. A valid human
review signature records the reviewer's *claim* that a qualified screening
tool and rights records were inspected. No actual classifier, distribution,
public download route, social publishing or generated media serving exists.
"""
from __future__ import annotations

from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt,model_validator

from app.creative_local_generation import GenerationBlocked,_b64,_time,canonical

class Review(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    schema_version:StrictInt=1
    job_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    output_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    reviewer_id:str=Field(min_length=8,max_length=80,pattern=r"^[A-Za-z0-9_:-]+$")
    requester_id:str=Field(min_length=8,max_length=80,pattern=r"^[A-Za-z0-9_:-]+$")
    rights_review_artifact_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    consent_review_artifact_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    safety_scanner_report_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    safety_scanner_passed:StrictBool
    visual_human_review_passed:StrictBool
    licence_rights_review_passed:StrictBool
    likeness_consent_review_passed:StrictBool
    decision:str=Field(pattern="^(REVIEWED|REJECTED)$")
    issued_at:str
    expires_at:str
    signature:str

    @model_validator(mode="after")
    def reviewer_independent(self):
        if self.schema_version!=1 or self.reviewer_id==self.requester_id:
            raise ValueError("Independent output reviewer required")
        return self

def inspect_review(receipt:dict,review:Review,*,reviewer_public_key:str,
                   original_artifact:Path,now:datetime|None=None)->dict:
    """Only returns hold/reviewed; never release authorization."""
    if type(receipt) is not dict or (
        receipt.get("generation_mode")!="LOCAL_DIFFUSERS_REAL_INFERENCE" or
        receipt.get("real_ai_output_verified") is not True or
        receipt.get("published") is not False or
        receipt.get("output_state")!="QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW"
    ):
        raise GenerationBlocked("Only real quarantined media may be reviewed for real use")
    if (review.job_sha256!=receipt.get("job_sha256") or
        review.output_sha256!=receipt.get("output_sha256")):
        raise GenerationBlocked("Review does not bind the exact job and output")
    if (original_artifact.is_symlink() or not original_artifact.is_file()
        or original_artifact.stat().st_size>100_000_000):
        raise GenerationBlocked("Quarantined media unavailable or replaced")
    content_hasher=sha256()
    with original_artifact.open("rb") as media:
        for chunk in iter(lambda:media.read(1024*1024),b""):
            content_hasher.update(chunk)
    if content_hasher.hexdigest()!=review.output_sha256:
        raise GenerationBlocked("Quarantined file content changed")
    issued,expired=_time(review.issued_at),_time(review.expires_at)
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None or not (issued<=now.astimezone(timezone.utc)<expired and
                                   timedelta(minutes=1)<=expired-issued<=timedelta(hours=24)):
        raise GenerationBlocked("Missing recent signed human output review")
    data=canonical(review.model_dump(exclude={"signature"}))
    try:
        Ed25519PublicKey.from_public_bytes(_b64(reviewer_public_key,32)).verify(
            _b64(review.signature,64),data
        )
    except (InvalidSignature,ValueError) as exc:
        raise GenerationBlocked("Invalid signed output review") from exc
    can_review=all((
        review.safety_scanner_passed,
        review.visual_human_review_passed,
        review.licence_rights_review_passed,
        review.likeness_consent_review_passed,
        review.decision=="REVIEWED",
    ))
    return {
        "schema_version":1,"job_sha256":review.job_sha256,
        "output_sha256":review.output_sha256,
        "review_receipt_sha256":sha256(data).hexdigest(),
        "status":"HUMAN_REVIEW_CLAIM_RECORDED_PENDING_SEPARATE_RELEASE"
                 if can_review else "HOLD_REVIEW_REJECTED_OR_INCOMPLETE",
        "output_safety_verified_by_code":False,
        "license_authenticity_verified_by_code":False,
        "external_distribution_authorized":False,
        "published":False,
    }
