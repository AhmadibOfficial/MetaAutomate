"""P2-04d pure memory-only admission and resilience rehearsal.

Not a queue, worker, rate-limiting middleware, provider breaker, authenticated
tenant policy, or operational recovery system. All input IDs and logical ticks
are INVENTED; no HTTP route, time, storage, external API, or actual effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from uuid import UUID, uuid4
import re

MAX_TICK = 1_000_000
WINDOW_TICKS = 10
ADMISSIONS_PER_WINDOW = 3
MAX_OUTSTANDING_PER_TENANT = 2
MAX_OUTSTANDING_GLOBAL = 8
MAX_TRACKED_TENANTS = 16
MAX_TRACKED_TICKETS = 64
FAILURE_THRESHOLD = 2
BREAKER_COOLDOWN_TICKS = 5

DEMO_KEY_PATTERN = re.compile(r"DEMO-REQ-[A-Z0-9-]{3,48}\Z")
CLOSED, OPEN, HALF_OPEN = "SIM_CLOSED", "SIM_OPEN", "SIM_HALF_OPEN"
PENDING, SUCCEEDED, FAILED = "SIM_PENDING", "SIM_SUCCEEDED", "SIM_FAILED"
SUCCEED, FAIL = "SIM_SUCCESS", "SIM_FAILURE"


class SyntheticAdmissionDenied(ValueError):
    """Invalid, ambiguous or out-of-order synthetic simulation input."""


class SyntheticTicketNotFound(LookupError):
    """Ticket is not in the supplied demo partition."""


def _reject() -> None:
    raise SyntheticAdmissionDenied("Invalid synthetic resilience request")


def _tenant(tenant_id: UUID) -> None:
    if type(tenant_id) is not UUID:
        _reject()


def _tick(tick: int) -> None:
    if type(tick) is not int or not 0 <= tick <= MAX_TICK:
        _reject()


def _key(key: str) -> None:
    if type(key) is not str or DEMO_KEY_PATTERN.fullmatch(key) is None:
        _reject()


@dataclass(frozen=True)
class Admission:
    admitted: bool
    reason: str
    ticket_id: UUID | None
    ticket_state: str | None
    breaker_state: str
    tenant_demo_marker: str
    simulation_only: bool = True
    authenticated_tenancy: bool = False
    real_rate_limit_enforced: bool = False
    provider_operation_performed: bool = False
    persisted: bool = False


@dataclass(frozen=True)
class TicketView:
    ticket_id: UUID
    ticket_state: str
    breaker_state: str
    tenant_demo_marker: str
    outstanding_for_tenant: int
    simulation_only: bool = True
    real_delivery_performed: bool = False
    persisted: bool = False


@dataclass
class _Ticket:
    tenant_id: UUID
    key: str
    state: str = PENDING


@dataclass
class _TenantState:
    last_tick: int
    window_start: int
    admissions: int = 0
    failures: int = 0
    breaker_state: str = CLOSED
    open_until_tick: int | None = None
    probe_ticket: UUID | None = None


class OfflineSyntheticResilience:
    """In-process, bounded, lock-serialized simulation; nothing executes."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tenants: dict[UUID, _TenantState] = {}
        self._tickets: dict[UUID, _Ticket] = {}
        self._by_key: dict[tuple[UUID, str], UUID] = {}

    @staticmethod
    def _marker(tenant_id: UUID) -> str:
        return "DEMO-TENANT-" + sha256(
            b"metaautomate:p2-04d:tenant:" + tenant_id.bytes
        ).hexdigest()[:16].upper()

    def _outstanding(self, tenant_id: UUID | None = None) -> int:
        return sum(ticket.state == PENDING and
                   (tenant_id is None or ticket.tenant_id == tenant_id)
                   for ticket in self._tickets.values())

    @staticmethod
    def _valid_time(state: _TenantState, tick: int) -> None:
        if tick < state.last_tick:
            _reject()

    def propose(self, tenant_id: UUID, idempotency_key: str, *, tick: int) -> Admission:
        """Admit synthetic reservation or explain denial without charging quota."""
        _tenant(tenant_id)
        _key(idempotency_key)
        _tick(tick)
        with self._lock:
            state = self._tenants.get(tenant_id)
            if state is not None:
                self._valid_time(state, tick)
            old_id = self._by_key.get((tenant_id, idempotency_key))
            marker = self._marker(tenant_id)
            if old_id is not None:
                ticket = self._tickets[old_id]
                return Admission(True, "SIM_IDEMPOTENT_REPLAY", old_id,
                                 ticket.state, state.breaker_state, marker)
            if state is None and len(self._tenants) >= MAX_TRACKED_TENANTS:
                return Admission(False, "SIM_TENANT_CAP", None, None, CLOSED, marker)
            breaker = state.breaker_state if state else CLOSED
            if breaker == HALF_OPEN:
                return Admission(False, "SIM_PROBE_IN_PROGRESS", None, None,
                                 breaker, marker)
            if breaker == OPEN and (state.open_until_tick is None or
                                   tick < state.open_until_tick):
                return Admission(False, "SIM_BREAKER_OPEN", None, None,
                                 breaker, marker)
            current_window = (state.window_start if state else tick)
            used = (state.admissions if state else 0)
            if state is not None and tick - current_window >= WINDOW_TICKS:
                current_window, used = tick, 0
            if used >= ADMISSIONS_PER_WINDOW:
                return Admission(False, "SIM_TENANT_QUOTA", None, None, breaker, marker)
            if self._outstanding(tenant_id) >= MAX_OUTSTANDING_PER_TENANT:
                return Admission(False, "SIM_TENANT_BACKPRESSURE", None, None,
                                 breaker, marker)
            if self._outstanding() >= MAX_OUTSTANDING_GLOBAL:
                return Admission(False, "SIM_GLOBAL_BACKPRESSURE", None, None,
                                 breaker, marker)
            if len(self._tickets) >= MAX_TRACKED_TICKETS:
                return Admission(False, "SIM_HISTORY_CAP", None, None, breaker, marker)
            if state is None:
                state = _TenantState(last_tick=tick, window_start=tick)
                self._tenants[tenant_id] = state
            state.last_tick = tick
            state.window_start = current_window
            state.admissions = used + 1
            ticket_id = uuid4()
            self._tickets[ticket_id] = _Ticket(tenant_id, idempotency_key)
            self._by_key[(tenant_id, idempotency_key)] = ticket_id
            if breaker == OPEN:
                # The single permitted simulated probe after cooldown.
                state.breaker_state = HALF_OPEN
                state.probe_ticket = ticket_id
            return Admission(True, "SIM_RESERVED_ONLY", ticket_id, PENDING,
                             state.breaker_state, marker)

    def simulate_result(self, tenant_id: UUID, ticket_id: UUID,
                        outcome: str, *, tick: int) -> TicketView:
        """Invent result for an accepted ticket; never call a provider."""
        _tenant(tenant_id)
        _tick(tick)
        if type(ticket_id) is not UUID or type(outcome) is not str or outcome not in (SUCCEED, FAIL):
            _reject()
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None or ticket.tenant_id != tenant_id:
                raise SyntheticTicketNotFound("Synthetic ticket unavailable")
            state = self._tenants[tenant_id]
            self._valid_time(state, tick)
            if ticket.state != PENDING:
                _reject()  # no double completion, no rewriting a terminal outcome
            is_probe = state.breaker_state == HALF_OPEN and state.probe_ticket == ticket_id
            if outcome == FAIL and (is_probe or
                                   (state.breaker_state == CLOSED and
                                    state.failures + 1 >= FAILURE_THRESHOLD)):
                if tick + BREAKER_COOLDOWN_TICKS > MAX_TICK:
                    _reject()
            ticket.state = SUCCEEDED if outcome == SUCCEED else FAILED
            state.last_tick = tick
            if is_probe:
                state.probe_ticket = None
                if outcome == SUCCEED:
                    state.breaker_state = CLOSED
                    state.open_until_tick = None
                    state.failures = 0
                else:
                    state.breaker_state = OPEN
                    state.open_until_tick = tick + BREAKER_COOLDOWN_TICKS
                    state.failures = FAILURE_THRESHOLD
            elif state.breaker_state == CLOSED:
                if outcome == SUCCEED:
                    state.failures = 0
                else:
                    state.failures += 1
                    if state.failures >= FAILURE_THRESHOLD:
                        state.breaker_state = OPEN
                        state.open_until_tick = tick + BREAKER_COOLDOWN_TICKS
            # Results on pre-existing tickets while OPEN/HALF_OPEN do not
            # close the breaker or impersonate the single recovery probe.
            return self._ticket_view(tenant_id, ticket_id)

    def _ticket_view(self, tenant_id: UUID, ticket_id: UUID) -> TicketView:
        state = self._tenants[tenant_id]
        ticket = self._tickets[ticket_id]
        return TicketView(ticket_id=ticket_id, ticket_state=ticket.state,
                          breaker_state=state.breaker_state,
                          tenant_demo_marker=self._marker(tenant_id),
                          outstanding_for_tenant=self._outstanding(tenant_id))

    def inspect(self, tenant_id: UUID, ticket_id: UUID) -> TicketView:
        _tenant(tenant_id)
        if type(ticket_id) is not UUID:
            _reject()
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None or ticket.tenant_id != tenant_id:
                raise SyntheticTicketNotFound("Synthetic ticket unavailable")
            return self._ticket_view(tenant_id, ticket_id)
