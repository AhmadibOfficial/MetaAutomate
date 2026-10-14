"""P2-02b deny-only OneCall admission and revocation/replay unit tests.

All token keys and identities are synthetic; no OneCall service is connected.
"""
import base64
import json
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.onecall_assertion import AssertionRejected
from app.onecall_identity_gate import (
    IdentityTestReceipt,
    OneCallCurrentIdentity,
    evaluate_identity_test_no_access,
)

ISSUER = "https://onecall-identity.invalid"
KEY_ID = "onecall-test-key-2026"
NOW = 1790000000


def token_and_keys():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    subject, jti = str(uuid4()), str(uuid4())
    header = {"alg": "EdDSA", "typ": "onecall-amboy-identity+jwt", "kid": KEY_ID}
    claims = {
        "iss": ISSUER, "aud": "metaautomate-amboy-identity-test",
        "sub": subject, "jti": jti, "iat": NOW, "nbf": NOW,
        "exp": NOW + 50, "product": "onecall", "scope": "amboy:identity-test",
        "token_version": 4, "authority": "onecall-backend",
    }
    b64 = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    signing = b64(header) + "." + b64(claims)
    signature = base64.urlsafe_b64encode(
        private.sign(signing.encode())).rstrip(b"=").decode()
    return signing + "." + signature, {KEY_ID: public}, subject


def gate(token, keys, subject, *, active=True, version=4, consume=lambda _: True):
    return evaluate_identity_test_no_access(
        token, expected_issuer=ISSUER, pinned_keys=keys, now=NOW,
        load_current_onecall_identity=lambda _: OneCallCurrentIdentity(
            subject=subject, token_version=version, active=active,
            email_verified=True, phone_verified=True),
        atomic_consume_once=consume,
    )


def test_identity_test_cannot_grant_cross_product_access():
    token, keys, subject = token_and_keys()
    receipt = gate(token, keys, subject)
    assert receipt == IdentityTestReceipt(decision="IDENTITY_TEST_ONLY_NO_ACCESS")
    assert receipt.product == "onecall"
    assert receipt.metaautomate_principal_created is False
    assert receipt.tenant_mapping_granted is False
    assert receipt.external_action_performed is False
    assert not hasattr(receipt, "organization_id")


@pytest.mark.parametrize(("status", "version"), [
    (False, 4), (True, 5), (True, -1), (None, 4),
])
def test_revoked_or_changed_account_denied(status, version):
    token, keys, subject = token_and_keys()
    with pytest.raises(AssertionRejected):
        gate(token, keys, subject, active=status, version=version)


def test_bad_subject_and_stale_signature_cannot_consume_jti():
    token, keys, subject = token_and_keys()
    consumed = []
    with pytest.raises(AssertionRejected):
        gate(token, keys, str(uuid4()), consume=lambda t: consumed.append(t))
    assert not consumed
    with pytest.raises(AssertionRejected):
        gate(token[:-1] + ("A" if token[-1] != "A" else "B"),
             keys, subject, consume=lambda t: consumed.append(t))
    assert not consumed


def test_replay_and_backend_outage_both_fail_closed():
    token, keys, subject = token_and_keys()
    redeemed = set()

    def consume(info):
        if info.token_id in redeemed:
            return False
        redeemed.add(info.token_id)
        return True

    assert gate(token, keys, subject, consume=consume).decision == "IDENTITY_TEST_ONLY_NO_ACCESS"
    with pytest.raises(AssertionRejected):
        gate(token, keys, subject, consume=consume)
    with pytest.raises(AssertionRejected):
        gate(token, keys, subject, consume=lambda _: (_ for _ in ()).throw(OSError()))


def test_no_live_route_or_privilege_grants():
    root = Path(__file__).resolve().parents[1]
    for path in ["apps/api/app/main.py", "apps/api/app/amboy_m1.py",
                 "apps/api/app/domain_integrations.py"]:
        src = (root / path).read_text()
        assert "onecall_identity_gate" not in src
        assert "onecall_assertion" not in src
    sql = (root / "database/migrations/014_onecall_identity_test_replay.sql").read_text()
    assert "ON CONFLICT (assertion_jti) DO NOTHING" in sql
    assert "CREATE TABLE onecall_tenant_mapping_reviews" in sql
    assert "CHECK (review_state = 'PENDING')" in sql
    assert "FROM metaautomate_runtime" in sql
    assert "GRANT EXECUTE ON FUNCTION app.consume_onecall_identity_test_jti" not in sql
