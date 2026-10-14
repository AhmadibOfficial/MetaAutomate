"""Only a verified mTLS peer can satisfy the future private-service boundary.

Synthetic transport evidence here is NOT proof of a real TLS deployment.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from app.onecall_peer_policy import (
    PURPOSE, SERVICE_ID, PeerIdentityTestAdmission, ServicePeerRejected,
    TrustedPeerPolicy, VerifiedTlsPeerEvidence, admit_verified_service_peer,
)

TIME = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
CERT = b"synthetic-test-certificate-data-" * 20
POLICY = TrustedPeerPolicy(
    enabled=True, service_identity=SERVICE_ID,
    purpose=PURPOSE, pinned_certificate_sha256=sha256(CERT).hexdigest(),
)


def proof(**updates):
    values = dict(
        certificate_der=CERT, identity_uri=SERVICE_ID,
        verified_chain=True, client_certificate_required=True,
        handshake_at=TIME - timedelta(seconds=3),
        evidence_origin="verified-tls-terminator",
        tls_session_bound=True,
    )
    values.update(updates)
    return VerifiedTlsPeerEvidence(**values)


def test_default_denies_even_credible_synthetic_peer():
    with pytest.raises(ServicePeerRejected):
        admit_verified_service_peer(proof(),
            TrustedPeerPolicy(service_identity=SERVICE_ID,
                purpose=PURPOSE, pinned_certificate_sha256=sha256(CERT).hexdigest()),
            now=TIME)


def test_exact_policy_returns_no_access_identity_test_receipt():
    result = admit_verified_service_peer(proof(), POLICY, now=TIME)
    assert result == PeerIdentityTestAdmission()
    assert result.customer_access is False
    assert result.tenant_mapping is False
    assert result.bookings is False
    assert result.payments is False
    assert result.model_execution is False


@pytest.mark.parametrize("patch", [
    {"identity_uri": "spiffe://attacker/onecall"},
    {"certificate_der": b"a" * 512},
    {"verified_chain": False},
    {"client_certificate_required": False},
    {"tls_session_bound": False},
    {"evidence_origin": "x-forwarded-client-cert"},
    {"handshake_at": TIME - timedelta(seconds=16)},
    {"handshake_at": TIME + timedelta(seconds=1)},
    {"handshake_at": TIME.replace(tzinfo=None)},
    {"certificate_der": b""},
])
def test_untrusted_or_stale_transport_evidence_refused(patch):
    with pytest.raises(ServicePeerRejected):
        admit_verified_service_peer(proof(**patch), POLICY, now=TIME)


def test_bad_policy_identity_fails():
    for policy in [
        TrustedPeerPolicy(enabled=True, service_identity="onecall-mobile",
            purpose=PURPOSE, pinned_certificate_sha256=sha256(CERT).hexdigest()),
        TrustedPeerPolicy(enabled=True, service_identity=SERVICE_ID,
            purpose="bookings.write", pinned_certificate_sha256=sha256(CERT).hexdigest()),
        TrustedPeerPolicy(enabled=True, service_identity=SERVICE_ID,
            purpose=PURPOSE, pinned_certificate_sha256="deadbeef"),
    ]:
        with pytest.raises(ServicePeerRejected):
            admit_verified_service_peer(proof(), policy, now=TIME)


def test_never_authorizes_on_http_route_or_parsed_forwarded_headers():
    root = Path(__file__).resolve().parents[1]
    files = ["apps/api/app/main.py", "apps/api/app/amboy_m1.py",
             "apps/api/app/onecall_identity_gate.py", "apps/api/app/domain_integrations.py"]
    for p in files:
        code = (root / p).read_text()
        assert "onecall_peer_policy" not in code
    assert "X-Forwarded-Client-Cert" not in (
        root / "apps/api/app/onecall_peer_policy.py").read_text()
