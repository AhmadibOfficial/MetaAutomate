"""P2-05b: default-DENY offline approval/execution preflight rehearsal.

All IDs, reviewers and evidence are invented test inputs. None establish
authentication, trusted tenant context, provider identity, scope or approval.
This module NEVER grants execution and has NO API route, external I/O or worker.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from uuid import UUID
import re

MAX_TICK = 1_000_000
MAX_CASES = 64
MAX_CASES_PER_TENANT = 16
MAX_TENANTS = 16
MAX_REVIEW_AGE_TICKS = 20
REQ_PATTERN = re.compile(r"DEMO-PREFLIGHT-[A-Z0-9-]{3,48}\Z")
ACTOR_PATTERN = re.compile(r"DEMO-ACTOR-[A-Z0-9-]{3,40}\Z")

# These are machine-contract allowlist copies, NOT rights or enabled adapters.
# Exact parity with contracts/domains/v1/operations.json is unit-tested.
WRITE_CONTRACTS = {
    "business.crm.sync-proposal.v1": (
        "BIZ-006", "propose_write", "business.crm.write", "moderate", True, 1,
        frozenset({"DEMO-CRM-LEAD-ALPHA", "DEMO-CRM-LEAD-BETA"}),
    ),
    "business.finance.reconciliation-proposal.v1": (
        "BIZ-012", "propose_write", "business.finance.write", "high", True, 2,
        frozenset({"DEMO-FINANCE-INVOICE-MATCH",
                   "DEMO-FINANCE-LEDGER-DIFFERENCE"}),
    ),
}

PERMANENT_GATES = (
    "capability_draft",
    "connector_unbound",
    "server_identity_not_verified",
    "server_scope_not_issued",
    "real_human_approval_not_verified",
    "provider_preflight_not_verified",
    "provider_receipt_not_verified",
    "private_staging_not_verified",
    "phase01_foundation_no_go",
)


class SyntheticPreflightDenied(ValueError):
    """Invalid or conflicting synthetic preflight input; no authority granted."""


def _deny() -> None:
    raise SyntheticPreflightDenied("Synthetic preflight request denied")


def _uuid(value: UUID) -> None:
    if type(value) is not UUID:
        _deny()


def _tick(value: int) -> None:
    if type(value) is not int or not 0 <= value <= MAX_TICK:
        _deny()


def _label(value: str, expression: re.Pattern[str]) -> None:
    if type(value) is not str or expression.fullmatch(value) is None:
        _deny()


@dataclass(frozen=True)
class SyntheticApprovalClaims:
    """Never treated as actual provider/human/identity evidence."""
    demo_identity_matches: bool = False
    demo_scope_matches: bool = False
    demo_provider_ready: bool = False
    demo_proposal_version_matches: bool = False


@dataclass(frozen=True)
class SyntheticPreflightRequest:
    tenant_id: UUID
    proposal_id: UUID
    request_id: str
    operation_id: str
    scenario: str
    proposer_label: str
    reviewer_labels: tuple[str, ...]
    proposal_version: int
    created_tick: int
    now_tick: int
    claims: SyntheticApprovalClaims


@dataclass(frozen=True)
class SyntheticPreflightDecision:
    request_id: str
    proposal_id: UUID
    demo_tenant_marker: str
    operation_id: str
    capability_id: str
    effect: str
    risk: str
    required_scope: str
    proposal_version: int
    demo_review_count: int
    required_demo_review_count: int
    demo_checks_complete: bool
    decision: str
    missing_gates: tuple[str, ...]
    simulation_only: bool = True
    server_identity_verified: bool = False
    real_scope_issued: bool = False
    human_approval_verified: bool = False
    approval_reusable_for_execution: bool = False
    execution_authorized: bool = False
    executed: bool = False
    provider_called: bool = False
    provider_receipt_verified: bool = False
    data_accessed: bool = False
    persisted: bool = False


def evaluate_synthetic_preflight(
    request: SyntheticPreflightRequest,
) -> SyntheticPreflightDecision:
    """Pure denied decision for exactly two invented write-proposal contracts."""
    if type(request) is not SyntheticPreflightRequest:
        _deny()
    _uuid(request.tenant_id)
    _uuid(request.proposal_id)
    _label(request.request_id, REQ_PATTERN)
    _label(request.proposer_label, ACTOR_PATTERN)
    _tick(request.created_tick)
    _tick(request.now_tick)
    if (type(request.operation_id) is not str
            or request.operation_id not in WRITE_CONTRACTS
            or type(request.scenario) is not str):
        _deny()
    capability, effect, required_scope, risk, required_approval, count, scenarios = (
        WRITE_CONTRACTS[request.operation_id]
    )
    if request.scenario not in scenarios or required_approval is not True:
        _deny()
    if (type(request.proposal_version) is not int
            or not 0 <= request.proposal_version <= 2
            or type(request.reviewer_labels) is not tuple
            or len(request.reviewer_labels) > count
            or type(request.claims) is not SyntheticApprovalClaims):
        _deny()
    if any(type(getattr(request.claims, key)) is not bool
           for key in (
               "demo_identity_matches", "demo_scope_matches",
               "demo_provider_ready", "demo_proposal_version_matches",
           )):
        _deny()
    if request.now_tick < request.created_tick:
        _deny()
    if request.proposal_version != len(request.reviewer_labels):
        _deny()
    if any(type(actor) is not str
           or ACTOR_PATTERN.fullmatch(actor) is None
           or actor == request.proposer_label
           for actor in request.reviewer_labels):
        _deny()
    if len(set(request.reviewer_labels)) != len(request.reviewer_labels):
        _deny()
    missing = list(PERMANENT_GATES)
    if request.now_tick - request.created_tick > MAX_REVIEW_AGE_TICKS:
        missing.append("synthetic_proposal_expired")
    if len(request.reviewer_labels) < count:
        missing.append("synthetic_review_count_incomplete")
    for attr, reason in (
        ("demo_identity_matches", "synthetic_identity_claim_missing"),
        ("demo_scope_matches", "synthetic_scope_claim_missing"),
        ("demo_provider_ready", "synthetic_provider_claim_missing"),
        ("demo_proposal_version_matches", "synthetic_version_claim_missing"),
    ):
        if getattr(request.claims, attr) is False:
            missing.append(reason)
    demo_complete = (
        len(request.reviewer_labels) == count
        and request.now_tick - request.created_tick <= MAX_REVIEW_AGE_TICKS
        and all((
            request.claims.demo_identity_matches,
            request.claims.demo_scope_matches,
            request.claims.demo_provider_ready,
            request.claims.demo_proposal_version_matches,
        ))
    )
    # DEMO success flags NEVER eliminate permanent gates.
    marker = "DEMO-TENANT-" + sha256(
        b"metaautomate:p2-05b:tenant:" + request.tenant_id.bytes
    ).hexdigest()[:16].upper()
    return SyntheticPreflightDecision(
        request_id=request.request_id, proposal_id=request.proposal_id,
        demo_tenant_marker=marker, operation_id=request.operation_id,
        capability_id=capability, effect=effect, risk=risk,
        required_scope=required_scope, proposal_version=request.proposal_version,
        demo_review_count=len(request.reviewer_labels),
        required_demo_review_count=count,
        demo_checks_complete=demo_complete, decision="DENY",
        missing_gates=tuple(missing),
    )


class OfflineSyntheticPreflightRegistry:
    """Bounded per-instance replay illustration; not distributed or durable."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[tuple[UUID, str], tuple[SyntheticPreflightRequest, SyntheticPreflightDecision]] = {}
        self._counts: dict[UUID, int] = {}

    def inspect_once(self, request: SyntheticPreflightRequest) -> SyntheticPreflightDecision:
        # Validate before lock, avoiding state mutation on denied invalid input.
        response = evaluate_synthetic_preflight(request)
        with self._lock:
            identity = (request.tenant_id, request.request_id)
            old = self._by_id.get(identity)
            if old is not None:
                if old[0] != request:
                    _deny()  # no ambiguous conflicting replay
                return old[1]
            if (len(self._by_id) >= MAX_CASES
                    or self._counts.get(request.tenant_id, 0) >= MAX_CASES_PER_TENANT
                    or (request.tenant_id not in self._counts
                        and len(self._counts) >= MAX_TENANTS)):
                _deny()
            self._by_id[identity] = (request, response)
            self._counts[request.tenant_id] = (
                self._counts.get(request.tenant_id, 0) + 1
            )
            return response
