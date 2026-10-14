"""P2-02c cryptographic M2M proof tests; entirely synthetic, no network."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.onecall_assertion import AssertionRejected
from app.onecall_m2m_proof import (
    PROOF_AUDIENCE, PROOF_TYPE, PROOF_PATH, PROOF_SCOPE, PROOF_TTL,
    verify_onecall_service_proof_signature_only,
)

ISSUER = "https://onecall-service.invalid"
KID = "oc-m2m-staging2026"
NOW = 1790000000


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def enc(doc):
    return b64(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode())


@pytest.fixture
def signed_pair():
    identity_private = Ed25519PrivateKey.generate()
    service_private = Ed25519PrivateKey.generate()
    raw_key = lambda priv: priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    identity_header = {"alg": "EdDSA", "typ": "onecall-amboy-identity+jwt",
                       "kid": "identity-ci-key-2026"}
    identity = {"sub": str(uuid4()), "iat": NOW, "jti": str(uuid4())}
    input_value = enc(identity_header) + "." + enc(identity)
    assertion = input_value + "." + b64(identity_private.sign(input_value.encode()))
    payload = {
        "iss": ISSUER, "aud": PROOF_AUDIENCE, "sub": "onecall-backend",
        "jti": str(uuid4()), "iat": NOW, "nbf": NOW, "exp": NOW + PROOF_TTL,
        "htm": "POST", "htu": PROOF_PATH, "product": "onecall",
        "scope": PROOF_SCOPE,
        "ath": b64(hashlib.sha256(assertion.encode("ascii")).digest()),
    }
    header = {"alg": "EdDSA", "typ": PROOF_TYPE, "kid": KID}
    def signer(data=payload, protected=header, *, json_raw=None):
        head = enc(protected)
        body = enc(data) if json_raw is None else b64(json_raw)
        compact = head + "." + body
        return compact + "." + b64(service_private.sign(compact.encode()))
    return assertion, {KID: raw_key(service_private)}, {
        "identity-ci-key-2026": raw_key(identity_private)}, payload, header, signer


def verify_fixture(signed_pair, token=None, assertion=None, keys=None, identity_keys=None, now=NOW):
    a, pub, idpub, data, header, signer = signed_pair
    return verify_onecall_service_proof_signature_only(
        token if token is not None else signer(),
        identity_assertion=assertion if assertion is not None else a,
        expected_service_issuer=ISSUER,
        pinned_service_keys=keys if keys is not None else pub,
        pinned_identity_keys=identity_keys if identity_keys is not None else idpub,
        now=now,
    )


def test_proof_binds_exact_assertion_and_never_grants_tenant_access(signed_pair):
    result = verify_fixture(signed_pair)
    assert result.service_issuer == ISSUER
    assert result.key_id == KID
    assert result.scope == "amboy:service-identity-test"
    assert result.expires_at == NOW + 30
    assert not hasattr(result, "user_id")
    assert not hasattr(result, "organization_id")
    assert not hasattr(result, "permitted")


@pytest.mark.parametrize(("claim", "invalid"), [
    ("iss", "https://attacker.invalid"), ("aud", "onecall-mobile"),
    ("aud", ["onecall-mobile", PROOF_AUDIENCE]),
    ("sub", "user@example.com"), ("htm", "GET"),
    ("htu", "/internal/amboy/bookings"), ("htu", "http://example.invalid"),
    ("scope", "amboy:bookings.write"), ("product", "metaautomate"),
    ("exp", NOW + 120), ("exp", NOW), ("iat", NOW + 100),
    ("iat", NOW - 75), ("nbf", NOW + 10), ("jti", "replay"),
])
def test_signed_wrong_route_or_authority_rejected(signed_pair, claim, invalid):
    _, _, _, payload, _, signer = signed_pair
    changed = {**payload, claim: invalid}
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=signer(changed))


@pytest.mark.parametrize("extra", [
    "tenant_id", "organization_id", "roles", "approval", "email", "wallet",
    "payload", "connector_url", "claims", "jwk", "jwt_secret",
])
def test_untrusted_scope_or_tenant_fields_rejected(signed_pair, extra):
    _, _, _, payload, _, signer = signed_pair
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=signer({**payload, extra: "forged"}))


@pytest.mark.parametrize("extra", ["jku", "jwk", "crit", "x5u"])
def test_untrusted_header_key_discovery_forbidden(signed_pair, extra):
    _, _, _, _, head, signer = signed_pair
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=signer(protected={**head, extra: "bad"}))


@pytest.mark.parametrize("algorithm", ["none", "HS256", "RS256"])
def test_wrong_signing_algorithm_rejected(signed_pair, algorithm):
    _, _, _, _, head, signer = signed_pair
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=signer(protected={**head, "alg": algorithm}))


def test_exact_assertion_digest_key_separation_and_signature_required(signed_pair):
    assertion, pub, idkeys, _, _, signer = signed_pair
    token = signer()
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=token, assertion=assertion + "a")
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=token, keys={"unknown": next(iter(pub.values()))})
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=token, identity_keys={KID: next(iter(pub.values()))})
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=token[:-4] + "AAAA")


def test_expired_or_malformed_proof_rejected(signed_pair):
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, now=NOW + PROOF_TTL)
    for token in ("", "...", "abc.def", "!~.a.b"):
        with pytest.raises(AssertionRejected):
            verify_fixture(signed_pair, token=token)


def test_duplicate_json_field_rejected(signed_pair):
    _, _, _, payload, _, signer = signed_pair
    raw = ('{"aud":"wrong",'+json.dumps(payload)[1:]).encode()
    with pytest.raises(AssertionRejected):
        verify_fixture(signed_pair, token=signer(json_raw=raw))


def test_no_route_imports_proof_and_no_live_m2m_endpoint():
    root = Path(__file__).resolve().parents[1]
    for name in ("apps/api/app/main.py", "apps/api/app/amboy_m1.py",
                 "apps/api/app/domain_integrations.py",
                 "apps/api/app/onecall_identity_gate.py"):
        assert "onecall_m2m_proof" not in (root / name).read_text()
