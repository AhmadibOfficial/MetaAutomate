"""P2-05a: offline synthetic write PROPOSALS, never executable effects.

The caller-supplied UUID and DEMO actor strings are test partitions/labels,
NOT identity, authentication, scopes or verified human approval.
No API route, database, provider, payment, scheduling or worker exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from uuid import UUID, uuid4
import re

MAX_TICK = 1_000_000
REVIEW_TTL_TICKS = 20
MAX_PROPOSALS_PER_TENANT = 16
MAX_PROPOSALS_TOTAL = 64
MAX_TENANTS = 16

KEY = re.compile(r"DEMO-IDEMP-[A-Z0-9-]{3,48}\Z")
ACTOR = re.compile(r"DEMO-ACTOR-[A-Z0-9-]{3,40}\Z")
ENDORSE = "SIM_ENDORSE"
DECLINE = "SIM_DECLINE"
PENDING = "SIM_PENDING_REVIEW"
REVIEWED = "SIM_REVIEWED_NOT_AUTHORIZED"
REJECTED = "SIM_REJECTED"

# Mirrors the source-only DOMAIN_OPERATIONS declarations, but imports no
# FastAPI, authenticated runtime context, write-capability or provider adapter.
# A separate test checks exact parity against the machine-readable manifest.
DEMO_WRITE_CONTRACTS = {
    "business.crm.sync-proposal.v1": (
        "BIZ-006", "propose_write", "business.crm.write",
        "moderate", True, 1,
        ("DEMO-CRM-LEAD-ALPHA", "DEMO-CRM-LEAD-BETA"),
    ),
    "business.finance.reconciliation-proposal.v1": (
        "BIZ-012", "propose_write", "business.finance.write",
        "high", True, 2,
        ("DEMO-FINANCE-INVOICE-MATCH", "DEMO-FINANCE-LEDGER-DIFFERENCE"),
    ),
}


class SyntheticProposalDenied(ValueError):
    """Invalid demo proposal, idempotency conflict or stale decision."""


class SyntheticProposalNotFound(LookupError):
    """A proposal is not found in the supplied demo tenant partition."""


def _deny() -> None:
    raise SyntheticProposalDenied("Synthetic write proposal denied")


def _uuid(value: UUID) -> None:
    if type(value) is not UUID:
        _deny()


def _tick(value: int) -> None:
    if type(value) is not int or not 0 <= value <= MAX_TICK:
        _deny()


def _text(value: str, pattern: re.Pattern[str]) -> None:
    if type(value) is not str or pattern.fullmatch(value) is None:
        _deny()


@dataclass(frozen=True)
class SyntheticProposalView:
    proposal_id: UUID
    demo_tenant_id: UUID
    operation_id: str
    capability_id: str
    effect: str
    required_scope: str
    risk: str
    required_demo_reviewers: int
    demo_scenario: str
    status: str
    decision: str
    version: int
    simulated_reviews: tuple[tuple[str, str], ...]
    created_tick: int
    expires_after_tick: int
    simulation_only: bool = True
    tenant_authenticated: bool = False
    scope_verified: bool = False
    human_approval_verified: bool = False
    execution_authorized: bool = False
    executed: bool = False
    provider_called: bool = False
    provider_receipt_verified: bool = False
    persisted: bool = False


@dataclass
class _Proposal:
    tenant_id: UUID
    proposer: str
    idempotency_key: str
    operation_id: str
    scenario: str
    created_tick: int
    proposal_id: UUID = field(default_factory=uuid4)
    status: str = PENDING
    last_tick: int = 0
    reviews: list[tuple[str, str]] = field(default_factory=list)


class OfflineSyntheticWriteProposals:
    """Bounded, lock-serialized memory rehearsal. No real authorization."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._proposals: dict[UUID, _Proposal] = {}
        self._by_key: dict[tuple[UUID, str], UUID] = {}
        self._counts: dict[UUID, int] = {}

    def propose(
        self, tenant_id: UUID, operation_id: str, demo_scenario: str,
        demo_proposer: str, idempotency_key: str, *, tick: int,
    ) -> SyntheticProposalView:
        _uuid(tenant_id)
        _tick(tick)
        _text(demo_proposer, ACTOR)
        _text(idempotency_key, KEY)
        if type(operation_id) is not str or operation_id not in DEMO_WRITE_CONTRACTS:
            _deny()
        contract = DEMO_WRITE_CONTRACTS[operation_id]
        if type(demo_scenario) is not str or demo_scenario not in contract[6]:
            _deny()
        if tick + REVIEW_TTL_TICKS > MAX_TICK:
            _deny()
        with self._lock:
            known = self._by_key.get((tenant_id, idempotency_key))
            if known is not None:
                proposal = self._proposals[known]
                if (proposal.operation_id, proposal.scenario, proposal.proposer) != (
                    operation_id, demo_scenario, demo_proposer
                ) or tick < proposal.last_tick:
                    _deny()
                return self._view(proposal)
            if (len(self._proposals) >= MAX_PROPOSALS_TOTAL
                    or self._counts.get(tenant_id, 0) >= MAX_PROPOSALS_PER_TENANT
                    or (tenant_id not in self._counts and len(self._counts) >= MAX_TENANTS)):
                _deny()
            proposal = _Proposal(
                tenant_id=tenant_id, proposer=demo_proposer,
                idempotency_key=idempotency_key, operation_id=operation_id,
                scenario=demo_scenario, created_tick=tick, last_tick=tick,
            )
            self._proposals[proposal.proposal_id] = proposal
            self._by_key[(tenant_id, idempotency_key)] = proposal.proposal_id
            self._counts[tenant_id] = self._counts.get(tenant_id, 0) + 1
            return self._view(proposal)

    def review(
        self, tenant_id: UUID, proposal_id: UUID, demo_reviewer: str,
        vote: str, *, tick: int, expected_version: int,
    ) -> SyntheticProposalView:
        """Record invented review labels, NOT a verified human approval."""
        _uuid(tenant_id)
        _uuid(proposal_id)
        _text(demo_reviewer, ACTOR)
        _tick(tick)
        if (type(expected_version) is not int or expected_version < 0
                or type(vote) is not str or vote not in (ENDORSE, DECLINE)):
            _deny()
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None or proposal.tenant_id != tenant_id:
                raise SyntheticProposalNotFound("Synthetic proposal unavailable")
            if (proposal.status != PENDING
                    or tick < proposal.last_tick
                    or tick > proposal.created_tick + REVIEW_TTL_TICKS
                    or expected_version != len(proposal.reviews)
                    or demo_reviewer == proposal.proposer
                    or any(actor == demo_reviewer for actor, _ in proposal.reviews)):
                _deny()
            # A committed transition is atomic under the instance lock.
            proposal.reviews.append((demo_reviewer, vote))
            proposal.last_tick = tick
            required = DEMO_WRITE_CONTRACTS[proposal.operation_id][5]
            if vote == DECLINE:
                proposal.status = REJECTED
            elif len(proposal.reviews) >= required:
                proposal.status = REVIEWED
            return self._view(proposal)

    def inspect(self, tenant_id: UUID, proposal_id: UUID) -> SyntheticProposalView:
        _uuid(tenant_id)
        _uuid(proposal_id)
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None or proposal.tenant_id != tenant_id:
                raise SyntheticProposalNotFound("Synthetic proposal unavailable")
            return self._view(proposal)

    @staticmethod
    def _view(proposal: _Proposal) -> SyntheticProposalView:
        c = DEMO_WRITE_CONTRACTS[proposal.operation_id]
        return SyntheticProposalView(
            proposal_id=proposal.proposal_id,
            demo_tenant_id=proposal.tenant_id,
            operation_id=proposal.operation_id,
            capability_id=c[0], effect=c[1], required_scope=c[2], risk=c[3],
            required_demo_reviewers=c[5], demo_scenario=proposal.scenario,
            status=proposal.status, decision="DENY", version=len(proposal.reviews),
            simulated_reviews=tuple(proposal.reviews),
            created_tick=proposal.created_tick,
            expires_after_tick=proposal.created_tick + REVIEW_TTL_TICKS,
        )
