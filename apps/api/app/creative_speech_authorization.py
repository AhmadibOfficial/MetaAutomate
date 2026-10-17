"""P2-04q independent Ed25519 authorization of one offline speech inference.

Verifies consent/licence-review *claims* and binding, not legal authenticity.
"""
from __future__ import annotations
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.creative_audio_assets import AudioAssetHold, canonical, hash_valid, validate_job

_FIELDS = {
    "schema_version", "job_sha256", "model_checkpoint_sha256",
    "model_config_sha256", "engine_sha256", "text_sha256",
    "license_evidence_sha256", "rights_evidence_sha256",
    "consent_evidence_sha256", "issued_at", "expires_at",
    "licence_human_reviewed", "rights_human_reviewed",
    "consent_human_reviewed", "isolated_execution_required",
    "publication_authorized", "signatures",
}
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

def _b64(value, required_len):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise AudioAssetHold("Invalid signing encoding")
    try:
        raw=base64.urlsafe_b64decode(value+"="*((-len(value))%4))
    except (ValueError, base64.binascii.Error) as exc:
        raise AudioAssetHold("Invalid signing encoding") from exc
    if len(raw)!=required_len or base64.urlsafe_b64encode(raw).rstrip(b"=").decode()!=value:
        raise AudioAssetHold("Invalid signing key/signature")
    return raw

def _utc(text):
    if type(text) is not str or not _TIME.fullmatch(text):
        raise AudioAssetHold("UTC-second ISO timestamp required")
    try:
        return datetime.strptime(text,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AudioAssetHold("Invalid approval timestamp") from exc

def verify_speech_approval(job:dict, approval:dict, *, config_sha256:str,
                           engine_sha256:str, text_sha256:str,
                           owner_public_key:str, reviewer_public_key:str,
                           now:datetime|None=None) -> str:
    plan=validate_job(job)
    if type(approval) is not dict or set(approval)!=_FIELDS:
        raise AudioAssetHold("Complete signed speech approval required")
    expected={
        "schema_version":1,
        "job_sha256":plan["job_sha256"],
        "model_checkpoint_sha256":job["model_checkpoint_sha256"],
        "model_config_sha256":config_sha256,
        "engine_sha256":engine_sha256,
        "text_sha256":text_sha256,
        "license_evidence_sha256":job["model_license_evidence_sha256"],
        "rights_evidence_sha256":job["content_rights_evidence_sha256"],
        "consent_evidence_sha256":job["voice_consent_evidence_sha256"],
        "licence_human_reviewed":True,
        "rights_human_reviewed":True,
        "consent_human_reviewed":True,
        "isolated_execution_required":True,
        "publication_authorized":False,
    }
    if any(type(approval.get(k)) is not type(v) or approval.get(k)!=v
           for k,v in expected.items()):
        raise AudioAssetHold("Approval does not match job, model, text or evidence")
    if type(approval["signatures"]) is not list or len(approval["signatures"])!=2:
        raise AudioAssetHold("Owner and independent reviewer signatures required")
    signatures=approval["signatures"]
    if [entry.get("role") for entry in signatures if type(entry) is dict]!=["OWNER","REVIEWER"]:
        raise AudioAssetHold("Two ordered independent roles required")
    issued, expires=_utc(approval["issued_at"]),_utc(approval["expires_at"])
    current=now or datetime.now(timezone.utc)
    if (current.tzinfo is None or not issued<=current.astimezone(timezone.utc)<expires
        or not timedelta(minutes=1)<=expires-issued<=timedelta(minutes=30)):
        raise AudioAssetHold("Missing current short-lived speech authorization")
    keys=[_b64(owner_public_key,32),_b64(reviewer_public_key,32)]
    if keys[0]==keys[1]:
        raise AudioAssetHold("Reviewer key must differ from owner key")
    payload=canonical({k:v for k,v in approval.items() if k!="signatures"})
    for key, sig in zip(keys,signatures):
        if type(sig) is not dict or set(sig)!={"role","signature"}:
            raise AudioAssetHold("Malformed approval signature")
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(_b64(sig["signature"],64),payload)
        except (InvalidSignature,ValueError) as exc:
            raise AudioAssetHold("Invalid independently signed speech approval") from exc
    return sha256(payload).hexdigest()
