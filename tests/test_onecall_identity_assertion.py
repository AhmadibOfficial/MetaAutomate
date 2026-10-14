"""P2-02 dedicated OneCall assertion tests: synthetic identities and ephemeral keys only.

The assertions in this test suite are deliberately not a OneCall-issued
production token and cannot authenticate to any MetaAutomate route.
"""
import base64
import json
from pathlib import Path
import time
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.onecall_assertion import (
    ASSERTION_AUDIENCE,
    ASSERTION_SCOPE,
    ASSERTION_TYPE,
    AssertionRejected,
    validate_onecall_assertion_signature_only,
)

TEST_ISSUER = "https://onecall-identity.invalid"
TEST_KID = "onecall-test-key-2026"
NOW = 1790000000


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def encode_json(value: object) -> str:
    return b64(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def claims():
    return {
        "iss": TEST_ISSUER,
        "aud": ASSERTION_AUDIENCE,
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "iat": NOW - 10,
        "nbf": NOW - 10,
        "exp": NOW + 40,
        "product": "onecall",
        "scope": ASSERTION_SCOPE,
        "token_version": 0,
        "authority": "onecall-backend",
    }


def header():
    return {"alg": "EdDSA", "typ": ASSERTION_TYPE, "kid": TEST_KID}


@pytest.fixture
def signing():
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return key, {TEST_KID: public}


def sign(key, payload=None, protected=None, *, raw_payload=None):
    parts = [
        encode_json(protected if protected is not None else header()),
        b64(raw_payload) if raw_payload is not None else
        encode_json(payload if payload is not None else claims()),
    ]
    data = ".".join(parts).encode()
    return ".".join(parts) + "." + b64(key.sign(data))


def validate(token, public, at=NOW):
    return validate_onecall_assertion_signature_only(
        token,
        expected_issuer=TEST_ISSUER,
        pinned_public_keys=public,
        now=at,
    )


def test_strict_dedicated_signature_and_subject(signing):
    private, keys = signing
    c = claims()
    result = validate(sign(private, c), keys)
    assert str(result.subject) == c["sub"]
    assert str(result.token_id) == c["jti"]
    assert result.issuer == TEST_ISSUER
    assert result.key_id == TEST_KID
    assert result.token_version == 0
    assert result.scope == "amboy:identity-test"
    assert not hasattr(result, "organization_id")
    assert not hasattr(result, "authorized")


@pytest.mark.parametrize(("field", "value"), [
    ("iss", "https://lookalike-onecall.invalid"),
    ("aud", "onecall-mobile"),
    ("aud", ["onecall-mobile", ASSERTION_AUDIENCE]),
    ("product", "metaautomate"),
    ("product", "OneCall"),
    ("scope", "amboy:bookings.write"),
    ("scope", "amboy:identity-test amboy:orders.read"),
    ("authority", "onecall-customer"),
    ("sub", "person@example.com"),
    ("sub", "not-a-uuid"),
    ("jti", "reuse-session"),
    ("token_version", -1),
    ("token_version", True),
    ("iat", NOW + 60),
    ("iat", NOW - 90),
    ("nbf", NOW + 50),
    ("exp", NOW - 2),
    ("exp", NOW + 1000),
])
def test_wrong_identity_or_authority_claims_rejected(signing, field, value):
    key, pub = signing
    c = claims()
    c[field] = value
    with pytest.raises(AssertionRejected):
        validate(sign(key, c), pub)


@pytest.mark.parametrize("extra_field", [
    "email", "email_verified", "tenant_id", "organization_id", "roles",
    "permissions", "booking_id", "mobile_access_token", "user_id",
    "client_secret", "actor_id", "scope_grant"
])
def test_extra_client_or_tenant_authority_is_rejected(signing, extra_field):
    key, pub = signing
    c = claims()
    c[extra_field] = "some-user-controlled-value"
    with pytest.raises(AssertionRejected):
        validate(sign(key, c), pub)


@pytest.mark.parametrize("field", ["jti", "nbf", "scope", "authority", "token_version"])
def test_missing_claim_is_rejected(signing, field):
    key, pub = signing
    c = claims()
    del c[field]
    with pytest.raises(AssertionRejected):
        validate(sign(key, c), pub)


@pytest.mark.parametrize("unsafe_header", [
    {"alg": "none", "typ": ASSERTION_TYPE, "kid": TEST_KID},
    {"alg": "HS256", "typ": ASSERTION_TYPE, "kid": TEST_KID},
    {"alg": "RS256", "typ": ASSERTION_TYPE, "kid": TEST_KID},
    {"alg": "EdDSA", "typ": "JWT", "kid": TEST_KID},
    {"alg": "EdDSA", "typ": ASSERTION_TYPE, "kid": "unknown-key"},
    {"alg": "EdDSA", "typ": ASSERTION_TYPE, "kid": TEST_KID,
     "jku": "https://attacker.invalid/jwks.json"},
    {"alg": "EdDSA", "typ": ASSERTION_TYPE, "kid": TEST_KID,
     "jwk": {"kty": "OKP"}},
    {"alg": "EdDSA", "typ": ASSERTION_TYPE, "kid": TEST_KID,
     "crit": ["b64"]},
])
def test_mobile_unsigned_wrong_algorithm_or_untrusted_header_rejected(signing, unsafe_header):
    key, pub = signing
    with pytest.raises(AssertionRejected):
        validate(sign(key, protected=unsafe_header), pub)


def test_signature_forgery_key_substitution_and_tampering_rejected(signing):
    private, pub = signing
    token = sign(private)
    other = Ed25519PrivateKey.generate()
    with pytest.raises(AssertionRejected):
        validate(sign(other), pub)
    with pytest.raises(AssertionRejected):
        validate(token + "A", pub)
    with pytest.raises(AssertionRejected):
        validate(token, {"unknown": next(iter(pub.values()))})
    with pytest.raises(AssertionRejected):
        validate(token, {TEST_KID: bytes(32)})


def test_malformed_compact_and_json_fail_closed(signing):
    key, pub = signing
    for bad in ("", "abc", "..", "a.b.c.d", ".".join(["!", "!", "!"])):
        with pytest.raises(AssertionRejected):
            validate(bad, pub)
    duplicate = ('{"iss":"' + TEST_ISSUER + '","iss":"https://evil.invalid",'
                 + json.dumps(claims())[1:]).encode()
    with pytest.raises(AssertionRejected):
        validate(sign(key, raw_payload=duplicate), pub)


def test_expiry_boundary_requires_short_time_bound(signing):
    key, pub = signing
    c = claims()
    c["iat"] = NOW
    c["nbf"] = NOW
    c["exp"] = NOW + 60
    assert validate(sign(key, c), pub, NOW + 59)
    with pytest.raises(AssertionRejected):
        validate(sign(key, c), pub, NOW + 60)


def test_offline_signature_proof_is_not_wired_to_live_routes():
    root = Path(__file__).resolve().parents[1]
    main = (root / "apps/api/app/main.py").read_text()
    amboy = (root / "apps/api/app/amboy_m1.py").read_text()
    routes = (root / "apps/api/app/domain_integrations.py").read_text()
    for component in (main, amboy, routes):
        assert "onecall_assertion" not in component
    assert "onecall_app" in amboy
    assert '"amboy:identity-test"' == ASSERTION_SCOPE
