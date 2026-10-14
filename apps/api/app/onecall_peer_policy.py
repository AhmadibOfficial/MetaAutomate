"""P2-02c: pure, source-only mutual-TLS service-peer admission policy.

NO endpoint, proxy integration, env-based trust, network requests or DB changes.
A real deployment must obtain PeerEvidence from a trusted TLS-terminating
component (never HTTP headers) and verify the complete certificate chain.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
import re

KID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SERVICE_ID = "spiffe://onecall.internal/amboy-identity-issuer"
PURPOSE = "onecall-amboy-identity-test"
MAX_PEER_EVIDENCE_AGE = timedelta(seconds=15)


class ServicePeerRejected(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedTlsPeerEvidence:
    """Only a trusted TLS endpoint may populate this; NOT client JSON/header data."""
    certificate_der: bytes
    identity_uri: str
    verified_chain: bool
    client_certificate_required: bool
    handshake_at: datetime
    evidence_origin: str  # strong provenance from the TLS adapter, not arbitrary caller
    tls_session_bound: bool


@dataclass(frozen=True)
class TrustedPeerPolicy:
    service_identity: str
    pinned_certificate_sha256: str
    purpose: str
    enabled: bool = False


@dataclass(frozen=True)
class PeerIdentityTestAdmission:
    decision: str = "PEER_VERIFIED_IDENTITY_TEST_ONLY"
    customer_access: bool = False
    tenant_mapping: bool = False
    bookings: bool = False
    payments: bool = False
    model_execution: bool = False


def admit_verified_service_peer(
    evidence: VerifiedTlsPeerEvidence,
    policy: TrustedPeerPolicy,
    *,
    now: datetime | None = None,
) -> PeerIdentityTestAdmission:
    """Test policy over authenticated transport evidence; never validates a header.

    Source-only defense in depth. The certificate-chain verifier, termination
    adapter, replay proof and current OneCall account checks DO NOT exist yet.
    """
    def fail():
        raise ServicePeerRejected("Service peer is not authorized")

    current = now if now is not None else datetime.now(timezone.utc)
    if (
        type(evidence) is not VerifiedTlsPeerEvidence
        or type(policy) is not TrustedPeerPolicy
        or type(current) is not datetime
        or current.tzinfo is None
        or not policy.enabled
        or policy.service_identity != SERVICE_ID
        or policy.purpose != PURPOSE
        or not KID_PATTERN.fullmatch(policy.pinned_certificate_sha256)
    ):
        fail()
    if (
        not isinstance(evidence.certificate_der, bytes)
        or not (256 <= len(evidence.certificate_der) <= 16384)
        or evidence.identity_uri != policy.service_identity
        or evidence.verified_chain is not True
        or evidence.client_certificate_required is not True
        or evidence.tls_session_bound is not True
        or evidence.evidence_origin != "verified-tls-terminator"
        or type(evidence.handshake_at) is not datetime
        or evidence.handshake_at.tzinfo is None
        or evidence.handshake_at > current
        or current - evidence.handshake_at > MAX_PEER_EVIDENCE_AGE
    ):
        fail()
    digest = sha256(evidence.certificate_der).hexdigest()
    if not compare_digest(digest, policy.pinned_certificate_sha256):
        fail()
    return PeerIdentityTestAdmission()
