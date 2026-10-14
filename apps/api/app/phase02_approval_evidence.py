"""P2-05c/d: synthetic proposal evidence, duplicate denial and tamper checks.

Security boundary: DEMO UUIDs and actor labels are NOT authenticated identity.
This module has no API router, external signer, DB, model, network, provider or
permission to act. Every proposal/approval view is DENY, including reviewed ones.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID

WRITE_SPECS = {
    "business.crm.sync-proposal.v1": (
        "BIZ-006", "propose_write", "business.crm.write", "moderate", True,
        1, frozenset(("DEMO-CRM-LEAD-ALPHA", "DEMO-CRM-LEAD-BETA")),
    ),
    "business.finance.reconciliation-proposal.v1": (
        "BIZ-012", "propose_write", "business.finance.write", "high", True,
        2, frozenset(("DEMO-FINANCE-INVOICE-MATCH",
                      "DEMO-FINANCE-LEDGER-DIFFERENCE")),
    ),
}
ACTOR = re.compile(r"DEMO-ACTOR-[A-Z0-9-]{3,40}\Z")
KEY = re.compile(r"DEMO-IDEMP-[A-Z0-9-]{3,48}\Z")
MAX_RECORDS = 64
PER_TENANT_CAP = 16
MAX_TENANTS = 16
MAX_TICK = 1_000_000
TTL = 20
PENDING = "SIM_PENDING_REVIEW"
REVIEWED = "SIM_REVIEWED_NOT_AUTHORIZED"
DECLINED = "SIM_DECLINED"
DENY = "DENY"


class DemoDenied(ValueError):
    """Invalid or conflicting invented evidence; no write performed."""


class DemoNotFound(LookupError):
    """Cross-tenant and absent proposals are indistinguishable."""


def _deny() -> None:
    raise DemoDenied("Synthetic approval evidence denied")


def _validate_uuid(value: UUID) -> None:
    if type(value) is not UUID:
        _deny()


def _validate_tick(value: int) -> None:
    if type(value) is not int or not (0 <= value <= MAX_TICK):
        _deny()


def _validate_label(value: str, pattern: re.Pattern[str]) -> None:
    if type(value) is not str or pattern.fullmatch(value) is None:
        _deny()


def _canonical(event: dict[str, object]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _state_digest(state: DemoApprovalView) -> str:
    material = {
        "tenant_id": str(state.tenant_id), "proposal_id": str(state.proposal_id),
        "request_key": state.request_key, "operation_id": state.operation_id,
        "capability_id": state.capability_id, "required_scope": state.required_scope,
        "risk": state.risk, "scenario": state.scenario, "proposer": state.proposer,
        "created_tick": state.created_tick, "last_tick": state.last_tick,
        "revision": state.revision, "reviewers": list(state.reviewers),
        "status": state.status,
    }
    return sha256(_canonical(material).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class DemoAuditEvent:
    ordinal: int
    tenant_id: UUID
    proposal_id: UUID
    kind: str
    revision: int
    tick: int
    previous_hash: str
    state_digest: str
    hash: str


@dataclass(frozen=True)
class DemoApprovalView:
    tenant_id: UUID
    proposal_id: UUID
    request_key: str
    operation_id: str
    capability_id: str
    required_scope: str
    risk: str
    scenario: str
    proposer: str
    created_tick: int
    last_tick: int
    revision: int
    reviewers: tuple[str, ...]
    status: str
    audit_head: str
    decision: str = DENY
    simulation_only: bool = True
    tenant_authenticated: bool = False
    real_human_approval_verified: bool = False
    scope_verified: bool = False
    execution_authorized: bool = False
    executed: bool = False
    provider_called: bool = False
    provider_receipt_verified: bool = False
    persisted: bool = False


class OfflineApprovalEvidence:
    """In-memory demo recorder. No cryptographically trusted audit or durable data."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[tuple[UUID, UUID], DemoApprovalView] = {}
        self._keys: dict[tuple[UUID, str], UUID] = {}
        self._counts: dict[UUID, int] = {}
        self._audit: dict[UUID, list[DemoAuditEvent]] = {}

    def _append(self, state: DemoApprovalView, kind: str, tick: int) -> str:
        chain = self._audit.setdefault(state.tenant_id, [])
        previous = chain[-1].hash if chain else "0" * 64
        state_digest = _state_digest(state)
        payload = {
            "ordinal": len(chain), "tenant_id": str(state.tenant_id),
            "proposal_id": str(state.proposal_id),
            "kind": kind, "revision": state.revision, "tick": tick,
            "previous_hash": previous, "state_digest": state_digest,
        }
        digest = sha256(_canonical(payload).encode("ascii")).hexdigest()
        chain.append(DemoAuditEvent(
            len(chain), state.tenant_id, state.proposal_id, kind,
            state.revision, tick, previous, state_digest, digest,
        ))
        return digest

    def propose(
        self, *, tenant_id: UUID, proposal_id: UUID, operation_id: str,
        scenario: str, proposer: str, request_key: str, tick: int,
    ) -> DemoApprovalView:
        _validate_uuid(tenant_id)
        _validate_uuid(proposal_id)
        _validate_label(proposer, ACTOR)
        _validate_label(request_key, KEY)
        _validate_tick(tick)
        if (type(operation_id) is not str or operation_id not in WRITE_SPECS
                or type(scenario) is not str
                or scenario not in WRITE_SPECS[operation_id][6]
                or tick > MAX_TICK - TTL):
            _deny()
        with self._lock:
            key = (tenant_id, request_key)
            old_id = self._keys.get(key)
            if old_id is not None:
                old = self._records[(tenant_id, old_id)]
                if (old_id != proposal_id or old.operation_id != operation_id
                        or old.scenario != scenario or old.proposer != proposer
                        or tick < old.created_tick):
                    _deny()
                return old
            record_key = (tenant_id, proposal_id)
            if record_key in self._records:
                _deny()  # same proposal cannot be registered with a new key
            if (len(self._records) >= MAX_RECORDS
                    or self._counts.get(tenant_id, 0) >= PER_TENANT_CAP
                    or tenant_id not in self._counts
                    and len(self._counts) >= MAX_TENANTS):
                _deny()
            spec = WRITE_SPECS[operation_id]
            record = DemoApprovalView(
                tenant_id=tenant_id, proposal_id=proposal_id,
                request_key=request_key, operation_id=operation_id,
                capability_id=spec[0], required_scope=spec[2], risk=spec[3],
                scenario=scenario, proposer=proposer, created_tick=tick,
                last_tick=tick, revision=0, reviewers=(), status=PENDING, audit_head="",
            )
            head = self._append(record, "DEMO_PROPOSED", tick)
            record = replace(record, audit_head=head)
            self._records[record_key] = record
            self._keys[key] = proposal_id
            self._counts[tenant_id] = self._counts.get(tenant_id, 0) + 1
            return record

    def review(
        self, *, tenant_id: UUID, proposal_id: UUID, reviewer: str,
        vote: str, expected_revision: int, tick: int,
    ) -> DemoApprovalView:
        _validate_uuid(tenant_id)
        _validate_uuid(proposal_id)
        _validate_label(reviewer, ACTOR)
        _validate_tick(tick)
        if (type(expected_revision) is not int or expected_revision < 0
                or type(vote) is not str
                or vote not in ("SIM_ENDORSE", "SIM_DECLINE")):
            _deny()
        with self._lock:
            key = (tenant_id, proposal_id)
            prior = self._records.get(key)
            if prior is None:
                raise DemoNotFound("Synthetic proposal unavailable")
            if (prior.status != PENDING or prior.revision != expected_revision
                    or tick < prior.last_tick or tick > prior.created_tick + TTL
                    or reviewer == prior.proposer
                    or reviewer in prior.reviewers):
                _deny()
            n = len(prior.reviewers) + 1
            required = WRITE_SPECS[prior.operation_id][5]
            status = (DECLINED if vote == "SIM_DECLINE"
                      else REVIEWED if n >= required else PENDING)
            after = replace(prior, last_tick=tick, revision=prior.revision + 1,
                            reviewers=(*prior.reviewers, reviewer), status=status)
            head = self._append(after, vote, tick)
            after = replace(after, audit_head=head)
            self._records[key] = after
            return after

    def inspect(self, *, tenant_id: UUID, proposal_id: UUID) -> DemoApprovalView:
        _validate_uuid(tenant_id)
        _validate_uuid(proposal_id)
        with self._lock:
            record = self._records.get((tenant_id, proposal_id))
            if record is None:
                raise DemoNotFound("Synthetic proposal unavailable")
            return record

    def verify_demo_audit_chain(self, *, tenant_id: UUID) -> bool:
        """Detect accidental/demo tampering, NOT a signed/immutable audit store."""
        _validate_uuid(tenant_id)
        with self._lock:
            events = self._audit.get(tenant_id, [])
            previous = "0" * 64
            for i, event in enumerate(events):
                if (event.tenant_id != tenant_id or event.ordinal != i
                        or event.previous_hash != previous):
                    return False
                payload = {
                    "ordinal": i, "tenant_id": str(event.tenant_id),
                    "proposal_id": str(event.proposal_id), "kind": event.kind,
                    "revision": event.revision, "tick": event.tick,
                    "previous_hash": previous, "state_digest": event.state_digest,
                }
                if event.hash != sha256(_canonical(payload).encode("ascii")).hexdigest():
                    return False
                previous = event.hash
            # Also prevent a truncated chain from passing while the head
            # recorded on a proposal has no corresponding event.
            for (tenant, _), state in self._records.items():
                if tenant == tenant_id and not any(
                    x.proposal_id == state.proposal_id
                    and x.hash == state.audit_head
                    and x.state_digest == _state_digest(state) for x in events
                ):
                    return False
            return bool(events)
