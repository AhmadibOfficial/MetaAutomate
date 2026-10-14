"""P2-04a: pure in-memory delivery rehearsal with invented events ONLY.

No API router, provider callback, I/O, clock, database, worker, webhook, or
execution capability is present. Caller-provided UUIDs are NOT authorization:
a future adapter must derive tenant identity from a verified server session.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID, uuid4

OPERATION = "sandbox.synthetic.inventory.delivery-rehearsal.v1"
SCENARIOS = frozenset({
    "DEMO-INVENTORY-LOW-STOCK",
    "DEMO-INVENTORY-IN-RANGE",
    "DEMO-DELIVERY-TRANSIENT",
})
OUTCOMES = frozenset({
    "SIM_SUCCESS", "SIM_TRANSIENT_FAILURE", "SIM_PERMANENT_FAILURE",
})
SIM_QUEUED = "SIM_QUEUED"
SIM_RETRY_WAIT = "SIM_RETRY_WAIT"
SIM_COMPLETED = "SIM_COMPLETED"
SIM_DEAD_LETTER = "SIM_DEAD_LETTER"
SIM_PERMANENT_FAILURE = "SIM_PERMANENT_FAILURE"
MAX_AUTOMATIC_ATTEMPTS = 3
MAX_TOTAL_ATTEMPTS = 4  # includes at most one manually rehearsed recovery
MAX_PER_TENANT = 32
MAX_TOTAL = 128
MAX_TICK = 1_000_000
IDEMPOTENCY = re.compile(r"DEMO-[A-Z0-9-]{3,48}\Z")
EVENT_ID = re.compile(r"DEMO-(?:EVT|RCV)-[A-Z0-9-]{3,48}\Z")
ZERO_HASH = "0" * 64


class SimulationError(ValueError):
    """Invalid synthetic input, timing, quota or transition."""


class SimulationConflict(SimulationError):
    """Idempotency key or event identifier was reused inconsistently."""


class SimulationNotFound(LookupError):
    """Job absent in the authenticated caller's tenant scope."""


@dataclass(frozen=True)
class Receipt:
    sequence: int
    kind: str
    event_id: str
    tick: int
    state: str
    attempts: int
    due_tick: int | None
    previous_sha256: str
    sha256: str


@dataclass(frozen=True)
class Snapshot:
    job_id: UUID
    operation: str
    scenario: str
    tenant_demo_marker: str
    state: str
    attempts: int
    recoveries: int
    due_tick: int | None
    receipts: tuple[Receipt, ...]
    simulation_only: bool = True
    actual_business_data: bool = False
    persisted: bool = False
    external_request_performed: bool = False
    execution_available: bool = False


@dataclass
class _Record:
    job_id: UUID
    tenant_id: UUID
    scenario: str
    key: str
    marker: str
    state: str
    attempts: int
    recoveries: int
    due_tick: int | None
    last_tick: int
    receipts: list[Receipt] = field(default_factory=list)
    seen_outcomes: dict[str, str] = field(default_factory=dict)
    recovery_event_id: str | None = None


def _tick(tick: int) -> None:
    if type(tick) is not int or not 0 <= tick <= MAX_TICK:
        raise SimulationError("Synthetic tick must be a bounded non-negative integer")


def _identifier(value: str, pattern: re.Pattern[str]) -> None:
    if type(value) is not str or len(value) > 64 or pattern.fullmatch(value) is None:
        raise SimulationError("Only bounded DEMO- identifiers are accepted")


def _digest(job_id: UUID, marker: str, receipt: Receipt) -> str:
    fields = {
        "domain": "metaautomate-p2-04a-simulation-receipt-v1",
        "job": str(job_id), "marker": marker,
        "sequence": receipt.sequence, "kind": receipt.kind,
        "event_id": receipt.event_id, "tick": receipt.tick,
        "state": receipt.state, "attempts": receipt.attempts,
        "due_tick": receipt.due_tick,
        "previous_sha256": receipt.previous_sha256,
    }
    return sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_receipt_chain(snapshot: Snapshot) -> bool:
    """Check consistency, NOT authenticity or durable forensic evidence."""
    previous = ZERO_HASH
    for number, receipt in enumerate(snapshot.receipts, 1):
        if (receipt.sequence != number
                or receipt.previous_sha256 != previous
                or receipt.sha256 != _digest(snapshot.job_id, snapshot.tenant_demo_marker, receipt)):
            return False
        previous = receipt.sha256
    return bool(snapshot.receipts)


class SyntheticDeliveryRehearsal:
    """Bounded, thread-safe, instance-local state machine; never delivers work."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._jobs: dict[UUID, _Record] = {}
        self._by_key: dict[tuple[UUID, str], UUID] = {}

    @staticmethod
    def _tenant(tenant_id: UUID) -> UUID:
        if type(tenant_id) is not UUID:
            raise SimulationError("Tenant context must come from a trusted caller")
        return tenant_id

    @staticmethod
    def _snapshot(record: _Record) -> Snapshot:
        return Snapshot(
            job_id=record.job_id, operation=OPERATION, scenario=record.scenario,
            tenant_demo_marker=record.marker, state=record.state,
            attempts=record.attempts, recoveries=record.recoveries,
            due_tick=record.due_tick, receipts=tuple(record.receipts),
        )

    @staticmethod
    def _append(record: _Record, kind: str, event_id: str, tick: int) -> None:
        previous = record.receipts[-1].sha256 if record.receipts else ZERO_HASH
        base = Receipt(
            sequence=len(record.receipts) + 1, kind=kind, event_id=event_id,
            tick=tick, state=record.state, attempts=record.attempts,
            due_tick=record.due_tick, previous_sha256=previous, sha256="",
        )
        from dataclasses import replace
        record.receipts.append(
            replace(base, sha256=_digest(record.job_id, record.marker, base))
        )

    def _scoped(self, tenant_id: UUID, job_id: UUID) -> _Record:
        if type(job_id) is not UUID:
            raise SimulationNotFound("Synthetic job unavailable")
        record = self._jobs.get(job_id)
        if record is None or record.tenant_id != tenant_id:
            raise SimulationNotFound("Synthetic job unavailable")
        return record

    def submit(self, tenant_id: UUID, idempotency_key: str,
               scenario: str, *, tick: int = 0) -> Snapshot:
        self._tenant(tenant_id)
        _identifier(idempotency_key, IDEMPOTENCY)
        _tick(tick)
        if type(scenario) is not str or scenario not in SCENARIOS:
            raise SimulationError("Only invented, allowlisted scenario names are supported")
        with self._lock:
            old_id = self._by_key.get((tenant_id, idempotency_key))
            if old_id is not None:
                old = self._jobs[old_id]
                if old.scenario != scenario:
                    raise SimulationConflict("Idempotency key reused for another scenario")
                return self._snapshot(old)
            if len(self._jobs) >= MAX_TOTAL:
                raise SimulationError("Instance-wide synthetic job cap reached")
            if sum(record.tenant_id == tenant_id for record in self._jobs.values()) >= MAX_PER_TENANT:
                raise SimulationError("Tenant synthetic job cap reached")
            marker = sha256(
                ("metaautomate-p2-04a-demo-tenant:" + str(tenant_id)).encode("ascii")
            ).hexdigest()[:24]
            job = _Record(
                job_id=uuid4(), tenant_id=tenant_id, scenario=scenario,
                key=idempotency_key, marker=marker, state=SIM_QUEUED,
                attempts=0, recoveries=0, due_tick=tick, last_tick=tick,
            )
            self._append(job, "SIM_ENQUEUED", idempotency_key, tick)
            self._jobs[job.job_id] = job
            self._by_key[(tenant_id, idempotency_key)] = job.job_id
            return self._snapshot(job)

    def inspect(self, tenant_id: UUID, job_id: UUID) -> Snapshot:
        self._tenant(tenant_id)
        with self._lock:
            return self._snapshot(self._scoped(tenant_id, job_id))

    def simulate_outcome(self, tenant_id: UUID, job_id: UUID, event_id: str,
                         outcome: str, *, tick: int) -> Snapshot:
        self._tenant(tenant_id)
        _identifier(event_id, EVENT_ID)
        if not event_id.startswith("DEMO-EVT-"):
            raise SimulationError("Only synthetic outcome event IDs are permitted")
        if type(outcome) is not str or outcome not in OUTCOMES:
            raise SimulationError("Unknown simulated outcome")
        _tick(tick)
        with self._lock:
            job = self._scoped(tenant_id, job_id)
            prior = job.seen_outcomes.get(event_id)
            if prior is not None:
                if prior != outcome:
                    raise SimulationConflict("Event ID replay with changed outcome")
                return self._snapshot(job)
            if job.state not in (SIM_QUEUED, SIM_RETRY_WAIT):
                raise SimulationError("Terminal synthetic job cannot be processed")
            if tick < job.last_tick or job.due_tick is None or tick < job.due_tick:
                raise SimulationError("Simulated work is not due, or tick moved backwards")
            attempts = job.attempts + 1
            if attempts > MAX_TOTAL_ATTEMPTS:
                raise SimulationError("Synthetic attempt budget exhausted")
            if outcome == "SIM_SUCCESS":
                state, due_tick = SIM_COMPLETED, None
            elif outcome == "SIM_PERMANENT_FAILURE":
                state, due_tick = SIM_PERMANENT_FAILURE, None
            elif attempts < MAX_AUTOMATIC_ATTEMPTS:
                state, due_tick = SIM_RETRY_WAIT, tick + 2 ** attempts
            else:
                state, due_tick = SIM_DEAD_LETTER, None
            if due_tick is not None and due_tick > MAX_TICK:
                raise SimulationError("Backoff exceeds bounded synthetic tick range")
            job.attempts, job.state, job.due_tick, job.last_tick = (
                attempts, state, due_tick, tick,
            )
            job.seen_outcomes[event_id] = outcome
            self._append(job, "SIM_OUTCOME_" + outcome, event_id, tick)
            return self._snapshot(job)

    def simulate_manual_recovery(self, tenant_id: UUID, job_id: UUID,
                                 recovery_event_id: str, *, tick: int) -> Snapshot:
        """One simulated operator-initiated replay; no actual approval is claimed."""
        self._tenant(tenant_id)
        _identifier(recovery_event_id, EVENT_ID)
        if not recovery_event_id.startswith("DEMO-RCV-"):
            raise SimulationError("Only synthetic recovery event IDs are permitted")
        _tick(tick)
        with self._lock:
            job = self._scoped(tenant_id, job_id)
            if job.recovery_event_id == recovery_event_id:
                return self._snapshot(job)
            if (job.state != SIM_DEAD_LETTER or job.recoveries != 0
                    or job.attempts != MAX_AUTOMATIC_ATTEMPTS):
                raise SimulationError("Only one exhausted transient job recovery is allowed")
            if tick < job.last_tick or tick + 8 > MAX_TICK:
                raise SimulationError("Invalid synthetic recovery tick")
            job.recoveries = 1
            job.recovery_event_id = recovery_event_id
            job.state, job.due_tick, job.last_tick = SIM_RETRY_WAIT, tick + 8, tick
            self._append(job, "SIM_MANUAL_RECOVERY_REHEARSAL", recovery_event_id, tick)
            return self._snapshot(job)
