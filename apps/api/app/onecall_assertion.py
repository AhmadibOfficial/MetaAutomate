"""P2-02: offline cryptographic validation of a *dedicated* OneCall assertion.

Not a FastAPI dependency, principal, OIDC issuer or authorization grant.
No routes import this module. No OneCall customer data or mobile token may
authenticate to MetaAutomate/AMBOY via this source-only validator.

Live use requires a trusted OneCall backend issuer, fresh subject/account
authorization, atomic one-time JTI redemption, revocation, quotas and audit.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
import time
from collections.abc import Mapping
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ASSERTION_AUDIENCE = "metaautomate-amboy-identity-test"
ASSERTION_TYPE = "onecall-amboy-identity+jwt"
ASSERTION_SCOPE = "amboy:identity-test"
MAX_TTL_SECONDS = 60
MAX_TOKEN_BYTES = 4096
SKEW_SECONDS = 5
KID_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class AssertionRejected(ValueError):
    """No sensitive details are reflected to callers."""


@dataclass(frozen=True)
class ParsedOneCallAssertion:
    issuer: str
    subject: UUID
    token_id: UUID
    token_version: int
    issued_at: int
    expires_at: int
    key_id: str
    scope: str = ASSERTION_SCOPE

    # This object must never be promoted to an AMBOY user or tenant principal:
    # cryptographic signature validity alone does not prove OneCall account
    # status, token revocation, tenant mapping or one-time JTI consumption.


def _reject() -> None:
    raise AssertionRejected("Untrusted OneCall identity assertion")


def _decode_segment(part: str) -> bytes:
    if not SEGMENT_RE.fullmatch(part):
        _reject()
    try:
        value = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
        if base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii") != part:
            _reject()
        return value
    except (ValueError, UnicodeError):
        _reject()


def _json_object(raw: bytes) -> dict:
    def unique(pairs):
        doc = {}
        for key, value in pairs:
            if key in doc:
                _reject()
            doc[key] = value
        return doc

    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: _reject())
    except (ValueError, UnicodeError):
        _reject()
    if not isinstance(data, dict):
        _reject()
    return data


def _uuid4(value: object) -> UUID:
    if not isinstance(value, str) or len(value) != 36:
        _reject()
    try:
        parsed = UUID(value)
    except (ValueError, TypeError):
        _reject()
    if parsed.version != 4 or str(parsed) != value:
        _reject()
    return parsed


def validate_onecall_assertion_signature_only(
    token: str,
    *,
    expected_issuer: str,
    pinned_public_keys: Mapping[str, bytes],
    now: int | None = None,
) -> ParsedOneCallAssertion:
    """Verify *candidate claims* with an out-of-band pinned Ed25519 public key.

    Never fetch JWKS from token headers. Never accept mobile HS256 secrets,
    email-based authority, client product/tenant IDs, OneCall booking scopes or
    actor permissions. Do not call from any live API endpoint.
    """
    if (not isinstance(expected_issuer, str)
        or not expected_issuer.startswith("https://")
        or len(expected_issuer) > 256
        or expected_issuer.endswith("/")
        or not isinstance(token, str)
        or not token.isascii()
        or len(token) > MAX_TOKEN_BYTES
        or len(token) < 150
        or not isinstance(pinned_public_keys, Mapping)
        or not pinned_public_keys):
        _reject()
    parts = token.split(".")
    if len(parts) != 3:
        _reject()
    header, payload, signature = parts
    protected = _json_object(_decode_segment(header))
    if set(protected) != {"alg", "kid", "typ"}:
        _reject()
    if protected.get("alg") != "EdDSA" or protected.get("typ") != ASSERTION_TYPE:
        _reject()
    kid = protected.get("kid")
    if not isinstance(kid, str) or not KID_RE.fullmatch(kid):
        _reject()
    key = pinned_public_keys.get(kid)
    if not isinstance(key, bytes) or len(key) != 32:
        _reject()
    decoded_signature = _decode_segment(signature)
    if len(decoded_signature) != 64:
        _reject()
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(
            decoded_signature, (header + "." + payload).encode("ascii")
        )
    except (ValueError, InvalidSignature):
        _reject()

    claims = _json_object(_decode_segment(payload))
    required = {"iss", "aud", "sub", "jti", "iat", "nbf", "exp",
                "product", "scope", "token_version", "authority"}
    if set(claims) != required:
        _reject()
    if (claims["iss"] != expected_issuer
        or claims["aud"] != ASSERTION_AUDIENCE
        or claims["product"] != "onecall"
        or claims["scope"] != ASSERTION_SCOPE
        or claims["authority"] != "onecall-backend"):
        _reject()
    current = int(time.time()) if now is None else now
    if type(current) is not int:
        _reject()
    for field in ("iat", "nbf", "exp", "token_version"):
        if type(claims[field]) is not int:
            _reject()
    issued, not_before, expires = claims["iat"], claims["nbf"], claims["exp"]
    if (expires <= current or issued > current + SKEW_SECONDS
        or not_before > current + SKEW_SECONDS
        or issued < current - MAX_TTL_SECONDS - SKEW_SECONDS
        or not_before < issued
        or expires <= issued or expires - issued > MAX_TTL_SECONDS
        or claims["token_version"] < 0 or claims["token_version"] > 2147483647):
        _reject()

    return ParsedOneCallAssertion(
        issuer=expected_issuer,
        subject=_uuid4(claims["sub"]),
        token_id=_uuid4(claims["jti"]),
        token_version=claims["token_version"],
        issued_at=issued,
        expires_at=expires,
        key_id=kid,
    )
