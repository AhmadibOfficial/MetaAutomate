"""P2-04c: pure offline analysis of invented delivery incident timelines.

This is NOT a worker, queue, webhook, incident manager, or authenticated
business capability. No I/O, real clock, provider, API, persistence or side
effects are present. Every event is an untrusted DEMO observation supplied by
the caller; findings are simulations, not provider/delivery evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from uuid import UUID

MAX_TICK = 1_000_000
MAX_EVENTS = 128
MAX_JOBS = 32
MAX_EVENTS_PER_JOB = 8
STALE_TICKS = 10
JOB_ID = re.compile(r"DEMO-JOB-[A-Z0-9-]{3,40}\Z")
EVENT_ID = re.compile(r"DEMO-EVT-[A-Z0-9-]{3,40}\Z")

QUEUED = "SIM_QUEUED"
RETRY = "SIM_RETRY_WAIT"
COMPLETED = "SIM_COMPLETED"
DEAD = "SIM_DEAD_LETTER"
PERMANENT = "SIM_PERMANENT_FAILURE"
RECOVERY = "SIM_RECOVERY_REHEARSAL"
KINDS = frozenset({QUEUED, RETRY, COMPLETED, DEAD, PERMANENT, RECOVERY})


class SyntheticIncidentDenied(ValueError):
    """Malformed or contradictory synthetic timeline."""


def _deny() -> None:
    raise SyntheticIncidentDenied("Synthetic incident timeline rejected")


def _tick(value: int) -> None:
    if type(value) is not int or not 0 <= value <= MAX_TICK:
        _deny()


def _identifier(value: str, regex: re.Pattern[str]) -> None:
    if type(value) is not str or regex.fullmatch(value) is None:
        _deny()


def _tenant(value: UUID) -> None:
    if type(value) is not UUID:
        _deny()


@dataclass(frozen=True)
class SyntheticObservation:
    tenant_id: UUID
    job_id: str
    event_id: str
    kind: str
    tick: int
    attempts: int


@dataclass(frozen=True)
class SyntheticJobSummary:
    job_id: str
    state: str
    attempts: int
    event_count: int
    due_tick: int | None
    stalled: bool
    simulated_recovery_count: int


@dataclass(frozen=True)
class SyntheticIncidentReport:
    tenant_demo_marker: str
    observed_at_tick: int
    event_count: int
    job_count: int
    completed_count: int
    dead_letter_count: int
    permanent_failure_count: int
    retry_wait_count: int
    queued_count: int
    stalled_count: int
    recovery_rehearsal_count: int
    recommendation: str
    jobs: tuple[SyntheticJobSummary, ...]
    simulation_only: bool = True
    authenticated_tenancy: bool = False
    actual_business_data: bool = False
    provider_receipts_verified: bool = False
    external_incident_created: bool = False
    persisted: bool = False
    executed: bool = False


def analyze_synthetic_incidents(
    tenant_id: UUID,
    events: tuple[SyntheticObservation, ...] | list[SyntheticObservation],
    *,
    now_tick: int,
) -> SyntheticIncidentReport:
    """Fail closed on invalid, unsorted or contradictory DEMO-only events."""
    _tenant(tenant_id)
    _tick(now_tick)
    if type(events) not in (tuple, list) or len(events) > MAX_EVENTS:
        _deny()
    seen_ids: set[str] = set()
    timelines: dict[str, list[SyntheticObservation]] = {}
    for event in events:
        if type(event) is not SyntheticObservation or event.tenant_id != tenant_id:
            _deny()
        _identifier(event.job_id, JOB_ID)
        _identifier(event.event_id, EVENT_ID)
        _tick(event.tick)
        if (event.tick > now_tick
                or type(event.attempts) is not int
                or not 0 <= event.attempts <= 4
                or type(event.kind) is not str
                or event.kind not in KINDS
                or event.event_id in seen_ids):
            _deny()
        seen_ids.add(event.event_id)
        if event.job_id not in timelines and len(timelines) == MAX_JOBS:
            _deny()
        sequence = timelines.setdefault(event.job_id, [])
        if len(sequence) == MAX_EVENTS_PER_JOB:
            _deny()
        if sequence and event.tick < sequence[-1].tick:
            _deny()
        sequence.append(event)

    summaries: list[SyntheticJobSummary] = []
    recovery_count = 0
    for job_id, sequence in sorted(timelines.items()):
        first = sequence[0]
        if first.kind != QUEUED or first.attempts != 0:
            _deny()
        last_kind, last_attempts = QUEUED, 0
        due_tick: int | None = first.tick
        last_tick = first.tick
        recovery_used = False
        for event in sequence[1:]:
            if event.tick < last_tick:
                _deny()
            if last_kind == DEAD:
                if (event.kind != RECOVERY or last_attempts != 3
                        or recovery_used or event.attempts != 3):
                    _deny()
                recovery_used = True
                recovery_count += 1
                due_tick = event.tick + 8
            elif last_kind in (COMPLETED, PERMANENT):
                _deny()
            elif last_kind == RECOVERY:
                if (event.kind not in (COMPLETED, DEAD)
                        or event.attempts != 4
                        or due_tick is None or event.tick < due_tick):
                    _deny()
                due_tick = None
            else:
                if due_tick is None or event.tick < due_tick:
                    _deny()
                if event.attempts != last_attempts + 1:
                    _deny()
                if event.kind == RETRY:
                    if event.attempts not in (1, 2):
                        _deny()
                    due_tick = event.tick + (2 ** event.attempts)
                elif event.kind == DEAD:
                    if event.attempts != 3:
                        _deny()
                    due_tick = None
                elif event.kind in (COMPLETED, PERMANENT):
                    due_tick = None
                else:
                    _deny()
            if due_tick is not None and due_tick > MAX_TICK:
                _deny()
            last_kind, last_attempts, last_tick = (
                event.kind, event.attempts, event.tick,
            )
        stalled = (last_kind in (QUEUED, RETRY, RECOVERY)
                   and due_tick is not None
                   and now_tick - due_tick >= STALE_TICKS)
        summaries.append(SyntheticJobSummary(
            job_id=job_id,
            state=last_kind,
            attempts=last_attempts,
            event_count=len(sequence),
            due_tick=due_tick,
            stalled=stalled,
            simulated_recovery_count=int(recovery_used),
        ))
    completed = sum(x.state == COMPLETED for x in summaries)
    dead = sum(x.state == DEAD for x in summaries)
    failed = sum(x.state == PERMANENT for x in summaries)
    retrying = sum(x.state in (RETRY, RECOVERY) for x in summaries)
    queued = sum(x.state == QUEUED for x in summaries)
    stalled = sum(x.stalled for x in summaries)
    # Text is advisory about INVENTED events only. No effect plan generated.
    recommendation = ("REVIEW_SYNTHETIC_INCIDENTS_ONLY"
                      if dead or failed or stalled else "NO_SYNTHETIC_ALERT")
    marker = sha256(
        b"metaautomate:p2-04c:demo-tenant:" + tenant_id.bytes
    ).hexdigest()[:16].upper()
    return SyntheticIncidentReport(
        tenant_demo_marker="DEMO-TENANT-" + marker,
        observed_at_tick=now_tick,
        event_count=len(events),
        job_count=len(summaries),
        completed_count=completed,
        dead_letter_count=dead,
        permanent_failure_count=failed,
        retry_wait_count=retrying,
        queued_count=queued,
        stalled_count=stalled,
        recovery_rehearsal_count=recovery_count,
        recommendation=recommendation,
        jobs=tuple(summaries),
    )
