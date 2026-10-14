"""P2-02d: cryptographic verification of OneCall's separate Ed25519 M2M proof.

Matches source-only OneCall draft PR #5 wire format. No network or live route.
A valid pair DOES NOT establish a MetaAutomate user, product tenant, access
grant, OneCall account freshness, replay redemption or live service transport.
"""
from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
import json
import re
import time
from collections.abc import Mapping
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.onecall_assertion import (
    AssertionRejected, validate_onecall_assertion_signature_only,
)

SERVICE_AUDIENCE = "metaautomate-amboy-m2m-test"
SERVICE_TYPE = "onecall-amboy-service-proof+jwt"
SERVICE_SCOPE = "amboy:service-identity-test"
SERVICE_PATH = "/internal/amboy/identity-test"
SERVICE_TTL = 30
SERVICE_SUBJECT = "onecall-backend"
KID_PATTERN = re.compile(r"^oc-m2m-[A-Za-z0-9_-]{8,64}$")
SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class OfflineIdentityPairProof:
    onecall_subject: UUID
    identity_jti: UUID
    service_jti: UUID
    identity_test_only: bool = True
    metaautomate_access: bool = False
    onecall_tenant_authorized: bool = False
    execution_performed: bool = False


def _fail():
    raise AssertionRejected("Untrusted bound OneCall service proof")


def _binary(seg: str) -> bytes:
    if not isinstance(seg, str) or not SEGMENT_PATTERN.fullmatch(seg):
        _fail()
    try:
        value = urlsafe_b64decode(seg + "=" * (-len(seg) % 4))
        if urlsafe_b64encode(value).rstrip(b"=").decode("ascii") != seg:
            _fail()
        return value
    except (ValueError, UnicodeError):
        _fail()


def _json(raw: bytes) -> dict:
    def no_duplicates(pairs):
        value = {}
        for key, field in pairs:
            if key in value:
                _fail()
            value[key] = field
        return value
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates,
                             parse_constant=lambda _: _fail())
    except (ValueError, UnicodeError):
        _fail()
    if not isinstance(payload, dict):
        _fail()
    return payload


def _uuid4(value: object) -> UUID:
    if not isinstance(value, str):
        _fail()
    try:
        result = UUID(value)
    except (ValueError, TypeError):
        _fail()
    if str(result) != value or result.version != 4:
        _fail()
    return result


def verify_offline_onecall_service_proof_pair(
    *,
    identity_assertion: str,
    service_proof: str,
    identity_issuer: str,
    identity_pinned_keys: Mapping[str, bytes],
    service_issuer: str,
    service_pinned_keys: Mapping[str, bytes],
    now: int | None = None,
) -> OfflineIdentityPairProof:
    """Only validates two cryptographic proofs. Not a grant or an API principal.

    Caller MUST separately use a real verified transport, current account
    revocation, durable one-time JTI and product authorization before live use.
    """
    if (not isinstance(service_issuer, str)
        or not service_issuer.startswith("https://")
        or service_issuer.endswith("/") or len(service_issuer) > 256
        or not isinstance(service_proof, str)
        or not service_proof.isascii()
        or not (150 <= len(service_proof) <= 4096)
        or not isinstance(identity_assertion, str)
        or not isinstance(service_pinned_keys, Mapping)
        or not service_pinned_keys):
        _fail()
    stamp = int(time.time()) if now is None else now
    if type(stamp) is not int:
        _fail()
    identity = validate_onecall_assertion_signature_only(
        identity_assertion, expected_issuer=identity_issuer,
        pinned_public_keys=identity_pinned_keys, now=stamp,
    )
    parts = service_proof.split(".")
    if len(parts) != 3:
        _fail()
    h, p, sig = parts
    header = _json(_binary(h))
    if set(header) != {"alg", "typ", "kid"}:
        _fail()
    kid = header.get("kid")
    if (header.get("alg") != "EdDSA"
        or header.get("typ") != SERVICE_TYPE
        or not isinstance(kid, str)
        or not KID_PATTERN.fullmatch(kid)):
        _fail()
    key = service_pinned_keys.get(kid)
    if not isinstance(key, bytes) or len(key) != 32:
        _fail()
    # Service and identity signing keys MUST be cryptographically distinct.
    if any(key == known for known in identity_pinned_keys.values()):
        _fail()
    signature = _binary(sig)
    if len(signature) != 64:
        _fail()
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(
            signature, (h + "." + p).encode("ascii")
        )
    except (InvalidSignature, ValueError):
        _fail()
    claims = _json(_binary(p))
    if set(claims) != {"iss", "aud", "sub", "jti", "iat", "nbf", "exp",
                       "htm", "htu", "ath", "product", "scope"}:
        _fail()
    if (claims["iss"] != service_issuer
        or claims["aud"] != SERVICE_AUDIENCE
        or claims["sub"] != SERVICE_SUBJECT
        or claims["htm"] != "POST"
        or claims["htu"] != SERVICE_PATH
        or claims["product"] != "onecall"
        or claims["scope"] != SERVICE_SCOPE):
        _fail()
    for f in ("iat", "nbf", "exp"):
        if type(claims[f]) is not int:
            _fail()
    iat, nbf, exp = claims["iat"], claims["nbf"], claims["exp"]
    if (iat > stamp + 5 or nbf > stamp + 5
        or iat < stamp - SERVICE_TTL - 5
        or nbf < iat or exp <= iat
        or exp - iat > SERVICE_TTL or exp <= stamp):
        _fail()
    expected_hash = urlsafe_b64encode(
        sha256(identity_assertion.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    if (not isinstance(claims["ath"], str)
        or not compare_digest(claims["ath"], expected_hash)):
        _fail()
    return OfflineIdentityPairProof(
        onecall_subject=identity.subject,
        identity_jti=identity.token_id,
        service_jti=_uuid4(claims["jti"]),
    )
