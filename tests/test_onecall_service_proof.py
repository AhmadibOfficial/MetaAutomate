"""Test independent OneCall identity and M2M proof signatures (synthetic keys).

Matches OneCall's source-only PR #5. No real OneCall token/service is used.
"""
from base64 import urlsafe_b64encode
from hashlib import sha256
import json
import time
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.onecall_assertion import AssertionRejected
from app.onecall_service_proof import (
    SERVICE_AUDIENCE, SERVICE_SCOPE, SERVICE_TYPE, SERVICE_PATH,
    OfflineIdentityPairProof, verify_offline_onecall_service_proof_pair,
)

ID_ISSUER = "https://onecall-identity.invalid"
M2M_ISSUER = "https://onecall-service.invalid"
ID_KID = "onecall-test-key-2026"
M2M_KID = "oc-m2m-staging2026"


def b64(data):
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def signed(key, header, claims):
    header_text = b64(json.dumps(header, separators=(",", ":")).encode())
    claims_text = b64(json.dumps(claims, separators=(",", ":")).encode())
    signing = header_text + "." + claims_text
    return signing + "." + b64(key.sign(signing.encode("ascii")))


def base_case(now=None):
    now = int(time.time()) if now is None else now
    identity_private = Ed25519PrivateKey.generate()
    service_private = Ed25519PrivateKey.generate()
    pub = lambda key: key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    identity_claims = {
        "iss": ID_ISSUER, "aud": "metaautomate-amboy-identity-test",
        "sub": str(uuid4()), "jti": str(uuid4()), "iat": now, "nbf": now,
        "exp": now + 55, "product": "onecall", "scope": "amboy:identity-test",
        "token_version": 5, "authority": "onecall-backend",
    }
    identity = signed(identity_private, {
        "alg": "EdDSA", "typ": "onecall-amboy-identity+jwt", "kid": ID_KID,
    }, identity_claims)
    service_claims = {
        "iss": M2M_ISSUER, "aud": SERVICE_AUDIENCE, "sub": "onecall-backend",
        "jti": str(uuid4()), "iat": now, "nbf": now, "exp": now + 29,
        "htm": "POST", "htu": SERVICE_PATH,
        "ath": b64(sha256(identity.encode("ascii")).digest()),
        "product": "onecall", "scope": SERVICE_SCOPE,
    }
    proof = signed(service_private, {
        "alg": "EdDSA", "typ": SERVICE_TYPE, "kid": M2M_KID,
    }, service_claims)
    return {
        "now": now, "identity": identity, "proof": proof,
        "id_private": identity_private, "m2m_private": service_private,
        "id_keys": {ID_KID: pub(identity_private)},
        "m2m_keys": {M2M_KID: pub(service_private)},
        "id_claims": identity_claims, "m2m_claims": service_claims,
    }


def check(case, **kwargs):
    data = dict(
        identity_assertion=case["identity"], service_proof=case["proof"],
        identity_issuer=ID_ISSUER, service_issuer=M2M_ISSUER,
        identity_pinned_keys=case["id_keys"],
        service_pinned_keys=case["m2m_keys"], now=case["now"],
    )
    data.update(kwargs)
    return verify_offline_onecall_service_proof_pair(**data)


def test_distinct_signatures_bound_assertion_and_proof_no_authorization():
    c = base_case()
    result = check(c)
    assert isinstance(result, OfflineIdentityPairProof)
    assert str(result.onecall_subject) == c["id_claims"]["sub"]
    assert str(result.service_jti) == c["m2m_claims"]["jti"]
    assert str(result.identity_jti) == c["id_claims"]["jti"]
    assert result.identity_test_only is True
    assert result.metaautomate_access is False
    assert result.onecall_tenant_authorized is False
    assert result.execution_performed is False
    assert not hasattr(result, "organization_id")


@pytest.mark.parametrize(("field", "wrong"), [
    ("iss", "https://attacker.invalid"),
    ("aud", "onecall-mobile"),
    ("aud", "metaautomate-amboy-identity-test"),
    ("sub", "arbitrary-customer"),
    ("htm", "GET"),
    ("htu", "/internal/amboy/bookings"),
    ("product", "metaautomate"),
    ("scope", "amboy:bookings.write"),
    ("exp", 0),
])
def test_wrong_service_claim_rejected(field, wrong):
    c = base_case()
    claims = dict(c["m2m_claims"], **{field: wrong})
    changed = signed(c["m2m_private"], {
        "alg": "EdDSA", "typ": SERVICE_TYPE, "kid": M2M_KID,
    }, claims)
    with pytest.raises(AssertionRejected):
        check(c, service_proof=changed)


def test_tampered_or_swapped_identity_invalidates_m2m_binding():
    c = base_case()
    other = base_case(c["now"])
    with pytest.raises(AssertionRejected):
        check(c, identity_assertion=other["identity"])
    with pytest.raises(AssertionRejected):
        check(c, identity_assertion=c["identity"] + "A")
    with pytest.raises(AssertionRejected):
        check(c, service_proof=c["proof"] + "A")


def test_wrong_key_issuer_and_mobile_shared_key_fail():
    c = base_case()
    with pytest.raises(AssertionRejected):
        check(c, service_pinned_keys={M2M_KID: c["id_keys"][ID_KID]})
    with pytest.raises(AssertionRejected):
        check(c, service_issuer="https://wrong-service.invalid")
    with pytest.raises(AssertionRejected):
        check(c, service_pinned_keys={"wrong-kid": c["m2m_keys"][M2M_KID]})


def test_time_and_nonce_are_bounded():
    c = base_case()
    assert check(c).identity_test_only
    with pytest.raises(AssertionRejected):
        check(c, now=c["now"] + 30)
    with pytest.raises(AssertionRejected):
        check(c, now=c["now"] - 30)


def test_foreign_claims_and_unsigned_service_proof_rejected():
    c = base_case()
    changed = dict(c["m2m_claims"], organization_id=str(uuid4()))
    claim = signed(c["m2m_private"], {
        "alg": "EdDSA", "typ": SERVICE_TYPE, "kid": M2M_KID,
    }, changed)
    with pytest.raises(AssertionRejected):
        check(c, service_proof=claim)
    unsigned = signed(c["m2m_private"], {
        "alg": "none", "typ": SERVICE_TYPE, "kid": M2M_KID,
    }, c["m2m_claims"])
    with pytest.raises(AssertionRejected):
        check(c, service_proof=unsigned)


def test_no_live_route_or_runtime_trust_grant():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for location in ("apps/api/app/main.py", "apps/api/app/amboy_m1.py",
                     "apps/api/app/onecall_identity_gate.py"):
        assert "onecall_service_proof" not in (root / location).read_text()
