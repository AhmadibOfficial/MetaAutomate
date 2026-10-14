"""P2-02b: source-only OneCall identity-test admission, never an AMBOY principal.

This module is intentionally NOT wired to a route or authentication middleware.
The callbacks are interfaces that must eventually be backed by an authenticated,
live OneCall revocation service and a durable, restricted replay store.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from app.onecall_assertion import (
    AssertionRejected,
    ParsedOneCallAssertion,
    validate_onecall_assertion_signature_only,
)


@dataclass(frozen=True)
class OneCallCurrentIdentity:
    subject: str
    token_version: int
    active: bool
    email_verified: bool
    phone_verified: bool


@dataclass(frozen=True)
class IdentityTestReceipt:
    decision: str
    product: str = "onecall"
    scope: str = "amboy:identity-test"
    metaautomate_principal_created: bool = False
    tenant_mapping_granted: bool = False
    external_action_performed: bool = False


def evaluate_identity_test_no_access(
    compact_assertion: str,
    *,
    expected_issuer: str,
    pinned_keys: Mapping[str, bytes],
    load_current_onecall_identity: Callable[[str], OneCallCurrentIdentity | None],
    atomic_consume_once: Callable[[ParsedOneCallAssertion], bool],
    now: int | None = None,
) -> IdentityTestReceipt:
    """Return proof of admission only, with no organization or user authorization.

    Caller must authenticate the peer and operate in isolated test infrastructure.
    In particular the externally injected callbacks are NOT sufficient for a
    production credential boundary until real OneCall revocation and DB access
    are implemented, independently verified and audited.
    """
    if not callable(load_current_onecall_identity) or not callable(atomic_consume_once):
        raise AssertionRejected("OneCall identity admission unavailable")
    parsed = validate_onecall_assertion_signature_only(
        compact_assertion, expected_issuer=expected_issuer,
        pinned_public_keys=pinned_keys, now=now,
    )
    try:
        current = load_current_onecall_identity(str(parsed.subject))
    except Exception:
        raise AssertionRejected("OneCall identity admission unavailable") from None
    if (
        current is None
        or type(current) is not OneCallCurrentIdentity
        or current.subject != str(parsed.subject)
        or type(current.token_version) is not int
        or current.token_version != parsed.token_version
        or current.active is not True
        or current.email_verified is not True
        or current.phone_verified is not True
    ):
        raise AssertionRejected("OneCall identity admission unavailable")
    try:
        consumed = atomic_consume_once(parsed)
    except Exception:
        raise AssertionRejected("OneCall identity admission unavailable") from None
    if consumed is not True:
        raise AssertionRejected("OneCall identity assertion was previously used")
    return IdentityTestReceipt(decision="IDENTITY_TEST_ONLY_NO_ACCESS")
