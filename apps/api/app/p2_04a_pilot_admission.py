"""P2-04a: signed, tenant-bound private pilot ADMISSION (not operational proof).

The accepted manifest records *claims* and SHA-256 pointers that two distinct
out-of-band signers approved. Cryptography makes alteration detectable; it DOES
NOT establish GitHub branch enforcement, real IdP MFA, customer consent,
source-document authenticity, a provisioned staging host or recovery. These
must be independently verified before signing. No keys/secrets are generated
or bundled for a live environment.

This is a fail-closed extra check on the existing default-OFF OIDC-only route.
Reverify on every request so admission expiry or revocation via removal of
the local manifest also shuts intake down.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, HTTPException

from app.authn import TenantSession, get_tenant_session

REPO="AhmadibOfficial/MetaAutomate"
PURPOSE="PRIVATE_STAGING_AGGREGATE_MEASUREMENT"
GATES=frozenset({"F04","F05","F06","F07","F08"})
HEX64=re.compile(r"[a-f0-9]{64}\Z")
HEX40=re.compile(r"[a-f0-9]{40}\Z")
MAX_BYTES=16_384
SIGNERS=("OWNER","INDEPENDENT_REVIEWER")
CORE_FIELDS={
    "schema_version","purpose","repository","commit_sha","tenant_id",
    "workspace_origin","oidc_issuer","issued_at","expires_at",
    "environment","consent_scope","external_execution",
    "evidence","signatures",
}
EVIDENCE_FIELDS={"artifact_sha256","witness_url","witness_kind"}
KIND={
    "F04":"FAILED_MERGE_DENIAL",
    "F05":"PRIVATE_PERIMETER_INSPECTION",
    "F06":"LIVE_IDP_MFA_REVOCATION",
    "F07":"OFFHOST_RESTORE_WITNESS",
    "F08":"LIVE_SECURITY_ACCEPTANCE",
}
_SIGN_FIELDS={"role","signature"}


class AdmissionDenied(ValueError):
    """No pilot should accept traffic when proof is invalid or stale."""


def require(ok:bool, reason:str)->None:
    if not ok:raise AdmissionDenied(reason)


def _pairs(pairs:list[tuple[str,Any]])->dict:
    out={}
    for name,value in pairs:
        require(name not in out,"Duplicate admission JSON key")
        out[name]=value
    return out


def _invalid_number(_:str):
    raise AdmissionDenied("Non-integer or nonfinite admission fields forbidden")


def canonical(data:dict)->bytes:
    return json.dumps(
        data,sort_keys=True,separators=(",",":"),ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def decode(raw:bytes)->dict:
    require(type(raw) is bytes and 0<len(raw)<=MAX_BYTES and b"\x00" not in raw,
            "Invalid bounded admission document")
    try:
        doc=json.loads(
            raw.decode("utf-8"),object_pairs_hook=_pairs,
            parse_float=_invalid_number,parse_constant=_invalid_number,
        )
    except AdmissionDenied:raise
    except (UnicodeDecodeError,ValueError,RecursionError) as exc:
        raise AdmissionDenied("Malformed admission JSON") from exc
    require(type(doc) is dict and set(doc)==CORE_FIELDS,
            "Unreviewed admission fields")
    return doc


def _b64(value:str,length:int)->bytes:
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]+",value) is not None,
            "Invalid signature or public key encoding")
    require(len(value)<=128,"Signature encoding too long")
    try:
        raw=base64.urlsafe_b64decode(value+"="*((-len(value))%4))
    except (ValueError,base64.binascii.Error) as exc:
        raise AdmissionDenied("Invalid base64url admission data") from exc
    require(len(raw)==length and base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")==value,
            "Noncanonical or invalid admission signature bytes")
    return raw


def _utc(value:str)->datetime:
    require(type(value) is str and
            re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",value) is not None,
            "Admission time must be UTC seconds")
    try:dt=datetime.strptime(value,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:raise AdmissionDenied("Invalid admission timestamp") from exc
    return dt


def _https(url:str)->None:
    require(type(url) is str and 10<=len(url)<=500,"Missing HTTPS evidence reference")
    p=urlsplit(url)
    require(p.scheme=="https" and p.hostname and
            not p.username and not p.password and
            not p.fragment and not p.query and
            p.port in (None,443) and
            p.hostname not in {"localhost","127.0.0.1","example.com","example.invalid"},
            "External evidence URL must be HTTPS and immutable without credentials")


def verify_bundle(raw:bytes,*,owner_pub:str,reviewer_pub:str,
                  expected_commit:str,expected_tenant:str,
                  expected_origin:str,expected_issuer:str,
                  now:datetime|None=None)->dict:
    """Verify an accepted *signed claim*; never promote any Foundation gate."""
    doc=decode(raw)
    require(type(doc["schema_version"]) is int and doc["schema_version"]==1,
            "Unsupported admission schema")
    require(doc["purpose"]==PURPOSE and doc["repository"]==REPO,
            "Incorrect staging release scope")
    require(doc["environment"]=="PRIVATE_STAGING" and
            doc["consent_scope"]=="AGGREGATE_ONLY" and
            doc["external_execution"] is False,
            "Public/customer production or agent execution forbidden")
    require(type(doc["commit_sha"]) is str and HEX40.fullmatch(doc["commit_sha"]) is not None,
            "Invalid expected release SHA")
    require(doc["commit_sha"]==expected_commit,
            "Manifest does not bind deployed commit")
    try:
        claimed_tenant=str(UUID(doc["tenant_id"]))
        configured_tenant=str(UUID(expected_tenant))
    except (TypeError,ValueError,AttributeError) as exc:
        raise AdmissionDenied("Missing exact authorized tenant ID") from exc
    require(doc["tenant_id"]==claimed_tenant==configured_tenant,
            "Pilot admission bound to a different organization")
    _https(doc["workspace_origin"])
    _https(doc["oidc_issuer"])
    require(doc["workspace_origin"]==expected_origin and
            doc["oidc_issuer"]==expected_issuer,
            "Pilot does not match private HTTPS ingress or real IdP config")
    issued,expiry=_utc(doc["issued_at"]),_utc(doc["expires_at"])
    present=now or datetime.now(timezone.utc)
    require(present.tzinfo is not None,"Naive clock forbidden")
    present=present.astimezone(timezone.utc)
    require(issued<=present<expiry and timedelta(minutes=1)<=expiry-issued<=timedelta(hours=24),
            "Unsigned, future, expired or overlong pilot admission")

    evidence=doc["evidence"]
    require(type(evidence) is dict and set(evidence)==GATES,
            "Missing mandatory Foundation acceptance artifacts")
    for gate in sorted(GATES):
        proof=evidence[gate]
        require(type(proof) is dict and set(proof)==EVIDENCE_FIELDS,
                gate+": evidence shape invalid")
        require(type(proof["artifact_sha256"]) is str and
                HEX64.fullmatch(proof["artifact_sha256"]) is not None,
                gate+": SHA-256 receipt missing")
        require(proof["witness_kind"]==KIND[gate],
                gate+": wrong independent evidence kind")
        _https(proof["witness_url"])

    signatures=doc["signatures"]
    require(type(signatures) is list and len(signatures)==2 and
            all(type(x) is dict and set(x)==_SIGN_FIELDS for x in signatures),
            "Two independently signed attestations required")
    require([x["role"] for x in signatures]==list(SIGNERS),
            "Owner and independent reviewer must sign in fixed order")
    payload=canonical({k:v for k,v in doc.items() if k!="signatures"})
    key_strings=(owner_pub,reviewer_pub)
    raw_keys=[_b64(k,32) for k in key_strings]
    require(raw_keys[0]!=raw_keys[1],
            "Independent reviewer cannot reuse owner signing key")
    for sig,key in zip(signatures,raw_keys):
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(
                _b64(sig["signature"],64),payload,
            )
        except (InvalidSignature,ValueError) as exc:
            raise AdmissionDenied("Admission signature verification failed") from exc
    return {
        "tenant_id":claimed_tenant,
        "commit_sha":doc["commit_sha"],
        "expires_at":doc["expires_at"],
        "scope":PURPOSE,
        "source_claims_signed":True,
        "actual_live_provider_evidence_verified_by_this_module":False,
        "operational_foundation_promoted":False,
        "external_agents_enabled":False,
    }


def verify_private_pilot_admission()->dict:
    env=os.environ
    require(env.get("WORKSPACE_AUTH_MODE")=="oidc",
            "Only private OIDC sessions can admit a business pilot")
    require(env.get("MAT_PILOT_OUTCOMES_ENABLED")=="1",
            "Pilot intake is OFF")
    path=env.get("MAT_PILOT_ADMISSION_FILE","")
    require(path.startswith("/") and len(path)<=300,
            "Trusted absolute mounted admission path required")
    file=Path(path)
    require(file.is_file() and not file.is_symlink(),
            "An operator-mounted non-symlink evidence receipt is required")
    try:
        with file.open("rb") as source:raw=source.read(MAX_BYTES+1)
    except OSError as exc:raise AdmissionDenied("Admission receipt unavailable") from exc
    return verify_bundle(
        raw,owner_pub=env.get("MAT_PILOT_OWNER_VERIFY_KEY",""),
        reviewer_pub=env.get("MAT_PILOT_REVIEWER_VERIFY_KEY",""),
        expected_commit=env.get("MAT_DEPLOY_COMMIT_SHA",""),
        expected_tenant=env.get("MAT_PILOT_TENANT_ID",""),
        expected_origin=env.get("WORKSPACE_ORIGIN",""),
        expected_issuer=env.get("OIDC_ISSUER",""),
    )


def require_private_pilot_admission(tenant:TenantSession=Depends(get_tenant_session))->None:
    """Per-request admission; no stale startup-only permit can survive expiry."""
    try:proof=verify_private_pilot_admission()
    except (AdmissionDenied,OSError) as exc:
        raise HTTPException(status_code=503,detail="Private pilot intake not authorized") from None
    if str(tenant.principal.organization_id)!=proof["tenant_id"]:
        raise HTTPException(status_code=403,detail="Pilot tenant not authorized")
