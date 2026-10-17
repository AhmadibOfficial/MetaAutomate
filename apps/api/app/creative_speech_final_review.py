"""P2-04q: independently signed *human claim* about finished speech WAV.

No automatic proof of legal rights, model inference, transcript accuracy or safe publication.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.creative_audio_assets import AudioAssetHold, canonical, sha_file, hash_valid, private_wav
from app.creative_speech_authorization import _b64, _utc

FIELDS={
    "schema_version","asset_id","job_sha256","output_sha256",
    "producer_id","reviewer_id","licence_evidence_sha256","consent_evidence_sha256",
    "safety_report_sha256","transcript_review_sha256",
    "human_listened","language_review_passed","intelligibility_review_passed",
    "transcript_match_review_passed","rights_review_passed","consent_review_passed",
    "safety_review_passed","decision","issued_at","expires_at","signature",
}

def verify_speech_review(job:dict,receipt:dict,review:dict,output:Path,*,
                         reviewer_public_key:str,now:datetime|None=None)->dict:
    if (type(review) is not dict or set(review)!=FIELDS or
        type(review["schema_version"]) is not int or review["schema_version"]!=1):
        raise AudioAssetHold("Signed output review schema invalid")
    if (type(receipt) is not dict or receipt.get("generation_mode")!="OPERATOR_ATTESTED_LOCAL_MODEL"
        or receipt.get("state")!="QUARANTINED_PENDING_INDEPENDENT_REVIEW"
        or receipt.get("published") is not False or receipt.get("distribution_authorized") is not False):
        raise AudioAssetHold("Only quarantined operator-attested model output can be reviewed")
    expected={
        "asset_id":job.get("asset_id"),
        "job_sha256":receipt.get("job_sha256"),
        "output_sha256":receipt.get("output_sha256"),
        "licence_evidence_sha256":job.get("model_license_evidence_sha256"),
        "consent_evidence_sha256":job.get("voice_consent_evidence_sha256"),
    }
    if (any(type(review.get(key)) is not type(value) or review.get(key)!=value
            for key,value in expected.items()) or
        review.get("producer_id")==review.get("reviewer_id") or
        not isinstance(review.get("producer_id"),str) or len(review["producer_id"])<8 or
        not isinstance(review.get("reviewer_id"),str) or len(review["reviewer_id"])<8):
        raise AudioAssetHold("Reviewer must be independent and review exact job/output")
    if not all(hash_valid(review[key]) for key in ("safety_report_sha256","transcript_review_sha256")):
        raise AudioAssetHold("Independent safety/transcript evidence references required")
    private_wav(output)
    if sha_file(output)!=review["output_sha256"]:
        raise AudioAssetHold("Finished speech file was altered after review")
    issued,expires=_utc(review.get("issued_at")),_utc(review.get("expires_at"))
    current=now or datetime.now(timezone.utc)
    if (current.tzinfo is None or not issued<=current.astimezone(timezone.utc)<expires
        or not timedelta(minutes=1)<=expires-issued<=timedelta(hours=24)):
        raise AudioAssetHold("Final speech review expired or out of bounds")
    data=canonical({k:v for k,v in review.items() if k!="signature"})
    try:
        Ed25519PublicKey.from_public_bytes(_b64(reviewer_public_key,32)).verify(
            _b64(review["signature"],64),data)
    except (InvalidSignature,ValueError) as exc:
        raise AudioAssetHold("Invalid speech human-review signature") from exc
    flags=[
        "human_listened","language_review_passed","intelligibility_review_passed",
        "transcript_match_review_passed","rights_review_passed",
        "consent_review_passed","safety_review_passed",
    ]
    accepted=(all(review.get(field) is True for field in flags)
              and review.get("decision")=="ACCEPTED")
    if review.get("decision") not in ("ACCEPTED","REJECTED"):
        raise AudioAssetHold("Invalid human-review decision")
    return {
        "review_sha256":sha256(data).hexdigest(),
        "output_sha256":review["output_sha256"],
        "status": ("SIGNED_HUMAN_REVIEW_CLAIM_RECORDED_STILL_QUARANTINED"
                   if accepted else "HOLD_REJECTED_OR_INCOMPLETE_REVIEW"),
        "model_execution_independently_verified":False,
        "rights_legal_authenticity_verified_by_code":False,
        "content_safety_scanned_by_code":False,
        "publication_authorized":False,"published":False,
    }
