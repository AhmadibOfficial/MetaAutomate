"""P2-02d: disconnected, source-only joined OneCall identity-test admission.

Requires a real server-side mutual TLS socket, distinct signed identity and
M2M assertion keys, current authoritative OneCall account snapshot and a
durable atomic BOTH-JTI consumer. It returns no customer/tenant permissions.
Not imported into any FastAPI routes and never runs external actions.

A live account-status transport and a trusted replay-role adapter DO NOT EXIST.
Callable arguments are test seams, not production identity trust. Never expose
this as a public endpoint, or accept SSL/identity evidence from HTTP headers.
"""
from __future__ import annotations

from dataclasses import dataclass
import ssl
from collections.abc import Callable, Mapping
from datetime import datetime, timezone

from app.onecall_assertion import AssertionRejected
from app.onecall_identity_gate import OneCallCurrentIdentity
from app.onecall_mtls_adapter import verify_real_mtls_peer_for_identity_test
from app.onecall_peer_policy import ServicePeerRejected, TrustedPeerPolicy
from app.onecall_service_proof import (
    OfflineIdentityPairProof,
    verify_offline_onecall_service_proof_pair,
)


@dataclass(frozen=True)
class OneCallJoinedTestReceipt:
    decision: str = "IDENTITY_TEST_ONLY_NO_ACCESS"
    product: str = "onecall"
    metaautomate_principal_created: bool = False
    tenant_mapping_granted: bool = False
    booking_permitted: bool = False
    payment_permitted: bool = False
    model_executed: bool = False
    external_action_performed: bool = False


def evaluate_joined_onecall_identity_test(
    *,
    server_tls_socket: ssl.SSLSocket,
    peer_policy: TrustedPeerPolicy,
    identity_assertion: str,
    service_proof: str,
    identity_issuer: str,
    identity_pinned_keys: Mapping[str, bytes],
    service_issuer: str,
    service_pinned_keys: Mapping[str, bytes],
    load_authoritative_onecall_identity: Callable[[str], OneCallCurrentIdentity | None],
    consume_pair_once: Callable[[OfflineIdentityPairProof], bool],
    now: int | None = None,
) -> OneCallJoinedTestReceipt:
    """Verify the full *test* sequence, without granting any product access.

    Both callbacks must be independently secured before real staging use.
    This module deliberately does not create a session, perform network I/O,
    mutate PostgreSQL, or authorize a business action itself.
    """
    def reject() -> None:
        raise AssertionRejected("OneCall private identity test not authorized")

    if (
        not callable(load_authoritative_onecall_identity)
        or not callable(consume_pair_once)
    ):
        reject()
    # Must be a server-side SSLSocket that has completed a real certificate
    # chain-verified handshake, not a user-supplied dataclass or forwarded header.
    try:
        peer_receipt = verify_real_mtls_peer_for_identity_test(
            server_tls_socket, peer_policy)
    except (ServicePeerRejected, ssl.SSLError):
        reject()
    if peer_receipt.customer_access or peer_receipt.tenant_mapping:
        reject()
    proof = verify_offline_onecall_service_proof_pair(
        identity_assertion=identity_assertion,
        service_proof=service_proof,
        identity_issuer=identity_issuer,
        identity_pinned_keys=identity_pinned_keys,
        service_issuer=service_issuer,
        service_pinned_keys=service_pinned_keys,
        now=now,
    )
    current = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    if (
        type(current) is not int
        or proof.identity_jti == proof.service_jti
        or proof.identity_expires_at <= current
        or proof.service_expires_at <= current
    ):
        reject()

    try:
        subject = load_authoritative_onecall_identity(str(proof.onecall_subject))
    except Exception:
        reject()
    if (
        type(subject) is not OneCallCurrentIdentity
        or subject.subject != str(proof.onecall_subject)
        or type(subject.token_version) is not int
        or subject.token_version != proof.identity_token_version
        or subject.active is not True
        or subject.email_verified is not True
        or subject.phone_verified is not True
    ):
        reject()

    # This must be ONE database transaction. Never implement as two
    # independent calls to the single-JTI function.
    try:
        accepted = consume_pair_once(proof)
    except Exception:
        reject()
    if accepted is not True:
        reject()
    return OneCallJoinedTestReceipt()
