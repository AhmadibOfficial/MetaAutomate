"""P2-02c: offline OneCall backend proof-of-possession verification.

No FastAPI import, network operation, session, tenant mapping, or capability
permission. This verifies cryptographic request binding only. Real service
authentication also requires an approved private/mTLS transport, key lifecycle,
fresh revocation, and atomic one-time proof/identity JTI consumption.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import hmac
import re
import time
from collections.abc import Mapping
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.onecall_assertion import (
    AssertionRejected, _decode_segment, _json_object, _uuid4,
)

PROOF_TYPE = "onecall-amboy-service-proof+jwt"
PROOF_AUDIENCE = "metaautomate-amboy-m2m-test"
PROOF_SCOPE = "amboy:service-identity-test"
PROOF_PATH = "/internal/amboy/identity-test"
PROOF_TTL = 30
PROOF_KID = re.compile(r"^oc-m2m-[A-Za-z0-9_-]{8,64}$")
MAX_BYTES = 4096
CLOCK_SKEW = 5


@dataclass(frozen=True)
class VerifiedM2MProof:
    service_issuer: str
    key_id: str
    proof_jti: UUID
    expires_at: int
    assertion_sha256_b64url: str
    scope: str = PROOF_SCOPE

    # Signature validation does not create a service principal or access grant.


def reject() -> None:
    raise AssertionRejected("Untrusted OneCall service identity proof")


def verify_onecall_service_proof_signature_only(
    proof: str,
    *,
    identity_assertion: str,
    expected_service_issuer: str,
    pinned_service_keys: Mapping[str, bytes],
    pinned_identity_keys: Mapping[str, bytes],
    now: int | None = None,
) -> VerifiedM2MProof:
    """Verify a distinct service key and exact assertion + destination binding.

    Caller cannot choose method, path or scope; token-controlled key discovery,
    URL redirects, arbitrary audience and mobile HS256 keys are rejected.
    """
    if (not isinstance(proof, str) or not proof.isascii()
        or len(proof) < 150 or len(proof) > MAX_BYTES
        or not isinstance(identity_assertion, str)
        or not identity_assertion.isascii()
        or len(identity_assertion) < 150
        or len(identity_assertion) > MAX_BYTES
        or not isinstance(expected_service_issuer, str)
        or not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::443)?", expected_service_issuer)
        or not isinstance(pinned_service_keys, Mapping)
        or not isinstance(pinned_identity_keys, Mapping)
        or not pinned_service_keys or not pinned_identity_keys):
        reject()
    chunks = proof.split(".")
    if len(chunks) != 3:
        reject()
    hdr, payload, sig = chunks
    header = _json_object(_decode_segment(hdr))
    if set(header) != {"alg", "typ", "kid"}:
        reject()
    kid = header.get("kid")
    if (header.get("alg") != "EdDSA"
        or header.get("typ") != PROOF_TYPE
        or not isinstance(kid, str)
        or not PROOF_KID.fullmatch(kid)):
        reject()
    key = pinned_service_keys.get(kid)
    if not isinstance(key, bytes) or len(key) != 32:
        reject()
    # The M2M proof key MUST NOT also be trusted as an identity assertion key.
    if any(hmac.compare_digest(key, identity_key)
           for identity_key in pinned_identity_keys.values()
           if isinstance(identity_key, bytes)):
        reject()
    try:
        signature = _decode_segment(sig)
        if len(signature) != 64:
            reject()
        Ed25519PublicKey.from_public_bytes(key).verify(
            signature, (hdr + "." + payload).encode("ascii")
        )
    except (InvalidSignature, ValueError):
        reject()
    claims = _json_object(_decode_segment(payload))
    required = {
        "iss", "aud", "sub", "jti", "iat", "nbf", "exp", "htm", "htu",
        "ath", "product", "scope",
    }
    if set(claims) != required:
        reject()
    if (claims["iss"] != expected_service_issuer
        or claims["aud"] != PROOF_AUDIENCE
        or claims["sub"] != "onecall-backend"
        or claims["htm"] != "POST"
        or claims["htu"] != PROOF_PATH
        or claims["product"] != "onecall"
        or claims["scope"] != PROOF_SCOPE):
        reject()
    expected_binding = base64.urlsafe_b64encode(
        hashlib.sha256(identity_assertion.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    if (not isinstance(claims["ath"], str)
        or not hmac.compare_digest(claims["ath"], expected_binding)):
        reject()
    n = int(time.time()) if now is None else now
    if type(n) is not int:
        reject()
    if any(type(claims[k]) is not int for k in ("iat", "nbf", "exp")):
        reject()
    start, not_before, expires = claims["iat"], claims["nbf"], claims["exp"]
    if (start > n + CLOCK_SKEW
        or start < n - PROOF_TTL - CLOCK_SKEW
        or not_before != start
        or expires <= n
        or expires <= start
        or expires - start > PROOF_TTL):
        reject()
    return VerifiedM2MProof(
        service_issuer=expected_service_issuer,
        key_id=kid,
        proof_jti=_uuid4(claims["jti"]),
        expires_at=expires,
        assertion_sha256_b64url=expected_binding,
    )
