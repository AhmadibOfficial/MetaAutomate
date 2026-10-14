"""P2-04d model-based negative tests; only invented events and no effects."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.synthetic_delivery_resilience import (
    ADMISSIONS_PER_WINDOW, BREAKER_COOLDOWN_TICKS, CLOSED, FAIL, FAILED,
    HALF_OPEN, MAX_OUTSTANDING_PER_TENANT, MAX_TRACKED_TICKETS,
    OPEN, PENDING, SUCCEED, SUCCEEDED, WINDOW_TICKS,
    OfflineSyntheticResilience, SyntheticAdmissionDenied,
    SyntheticTicketNotFound,
)


def reserve(system, tenant, key="DEMO-REQ-ALPHA", tick=0):
    return system.propose(tenant, key, tick=tick)


def trip(system, tenant):
    first = reserve(system, tenant, "DEMO-REQ-ONE", 0)
    second = reserve(system, tenant, "DEMO-REQ-TWO", 0)
    assert first.admitted and second.admitted
    r1 = system.simulate_result(tenant, first.ticket_id, FAIL, tick=1)
    r2 = system.simulate_result(tenant, second.ticket_id, FAIL, tick=2)
    assert r1.breaker_state == CLOSED
    assert r2.breaker_state == OPEN
    return first, second


def test_reservation_is_not_real_execution_and_completion_frees_capacity():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    decision = reserve(sim, tenant)
    assert decision.admitted
    assert decision.reason == "SIM_RESERVED_ONLY"
    assert decision.ticket_state == PENDING
    assert decision.simulation_only
    assert not decision.authenticated_tenancy
    assert not decision.real_rate_limit_enforced
    assert not decision.provider_operation_performed
    assert not decision.persisted
    completed = sim.simulate_result(tenant, decision.ticket_id, SUCCEED, tick=1)
    assert completed.ticket_state == SUCCEEDED
    assert completed.outstanding_for_tenant == 0
    assert not completed.real_delivery_performed
    assert not completed.persisted
    assert sim.inspect(tenant, decision.ticket_id) == completed


def test_idempotent_replay_does_not_consume_quota_or_backpressure():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    first = reserve(sim, tenant)
    again = reserve(sim, tenant, tick=0)
    assert again.admitted
    assert again.reason == "SIM_IDEMPOTENT_REPLAY"
    assert again.ticket_id == first.ticket_id
    assert sim.inspect(tenant, first.ticket_id).outstanding_for_tenant == 1
    sim.simulate_result(tenant, first.ticket_id, SUCCEED, tick=1)
    completed = reserve(sim, tenant, tick=1)
    assert completed.ticket_id == first.ticket_id
    assert completed.ticket_state == SUCCEEDED
    assert completed.reason == "SIM_IDEMPOTENT_REPLAY"


def test_per_tenant_backpressure_rejects_and_completion_releases():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    tickets = [
        reserve(sim, tenant, f"DEMO-REQ-ITEM-{i}", tick=0)
        for i in range(MAX_OUTSTANDING_PER_TENANT)
    ]
    assert all(x.admitted for x in tickets)
    rejected = reserve(sim, tenant, "DEMO-REQ-EXTRA", tick=0)
    assert not rejected.admitted
    assert rejected.reason == "SIM_TENANT_BACKPRESSURE"
    assert rejected.ticket_id is None
    sim.simulate_result(tenant, tickets[0].ticket_id, SUCCEED, tick=1)
    resumed = reserve(sim, tenant, "DEMO-REQ-EXTRA", tick=1)
    assert resumed.admitted
    assert sim.inspect(tenant, resumed.ticket_id).outstanding_for_tenant == 2


def test_quota_denial_then_new_window_recovers():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    for number in range(ADMISSIONS_PER_WINDOW):
        a = reserve(sim, tenant, f"DEMO-REQ-QUOTA-{number}", tick=number)
        assert a.admitted
        sim.simulate_result(tenant, a.ticket_id, SUCCEED, tick=number)
    limited = reserve(sim, tenant, "DEMO-REQ-QUOTA-LATE", tick=WINDOW_TICKS - 1)
    assert limited.reason == "SIM_TENANT_QUOTA" and not limited.admitted
    new = reserve(sim, tenant, "DEMO-REQ-QUOTA-LATE", tick=WINDOW_TICKS)
    assert new.admitted


def test_quota_and_backpressure_are_isolated_per_tenant():
    sim, a, b = OfflineSyntheticResilience(), uuid4(), uuid4()
    first = reserve(sim, a, "DEMO-REQ-SHARED")
    other = reserve(sim, b, "DEMO-REQ-SHARED")
    assert first.admitted and other.admitted
    assert first.ticket_id != other.ticket_id
    assert first.tenant_demo_marker != other.tenant_demo_marker
    assert sim.inspect(b, other.ticket_id).outstanding_for_tenant == 1
    with pytest.raises(SyntheticTicketNotFound):
        sim.inspect(a, other.ticket_id)
    with pytest.raises(SyntheticTicketNotFound):
        sim.simulate_result(b, first.ticket_id, SUCCEED, tick=0)


def test_global_backpressure_fails_closed_until_capacity_released():
    sim = OfflineSyntheticResilience()
    tenants, outstanding = [], []
    for i in range(4):
        tenant = uuid4()
        tenants.append(tenant)
        for n in range(2):
            decision = reserve(sim, tenant, f"DEMO-REQ-GLOBAL-{n}")
            assert decision.admitted
            outstanding.append((tenant, decision.ticket_id))
    newcomer = uuid4()
    denied = reserve(sim, newcomer, "DEMO-REQ-NEW")
    assert not denied.admitted
    assert denied.reason == "SIM_GLOBAL_BACKPRESSURE"
    first_tenant, ticket = outstanding[0]
    sim.simulate_result(first_tenant, ticket, SUCCEED, tick=0)
    assert reserve(sim, newcomer, "DEMO-REQ-NEW").admitted


def test_open_breaker_denies_new_admissions_even_when_capacity_is_free():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    trip(sim, tenant)
    blocked = reserve(sim, tenant, "DEMO-REQ-BLOCKED", tick=6)
    assert blocked.reason == "SIM_BREAKER_OPEN" and not blocked.admitted
    assert blocked.breaker_state == OPEN


def test_cooldown_allows_exactly_one_probe_then_success_closes():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    trip(sim, tenant)
    probe = reserve(sim, tenant, "DEMO-REQ-PROBE", tick=7)
    assert probe.admitted
    assert probe.breaker_state == HALF_OPEN
    blocked = reserve(sim, tenant, "DEMO-REQ-ANOTHER", tick=7)
    assert not blocked.admitted
    assert blocked.reason == "SIM_PROBE_IN_PROGRESS"
    view = sim.simulate_result(tenant, probe.ticket_id, SUCCEED, tick=7)
    assert view.breaker_state == CLOSED
    assert view.outstanding_for_tenant == 0
    # The quota has been consumed (3 accepted admissions this window).
    limited = reserve(sim, tenant, "DEMO-REQ-POST-PROBE", tick=7)
    assert limited.reason == "SIM_TENANT_QUOTA"
    assert reserve(sim, tenant, "DEMO-REQ-POST-PROBE", tick=10).admitted


def test_failed_probe_reopens_breaker_after_cooldown():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    trip(sim, tenant)
    probe = reserve(sim, tenant, "DEMO-REQ-PROBE", tick=7)
    view = sim.simulate_result(tenant, probe.ticket_id, FAIL, tick=7)
    assert view.ticket_state == FAILED and view.breaker_state == OPEN
    assert reserve(sim, tenant, "DEMO-REQ-PROBE2", tick=11).reason == "SIM_BREAKER_OPEN"
    assert reserve(sim, tenant, "DEMO-REQ-PROBE2", tick=12).breaker_state == HALF_OPEN


def test_success_resets_failure_streak():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    first = reserve(sim, tenant, "DEMO-REQ-FIRST")
    sim.simulate_result(tenant, first.ticket_id, FAIL, tick=0)
    second = reserve(sim, tenant, "DEMO-REQ-SECOND")
    sim.simulate_result(tenant, second.ticket_id, SUCCEED, tick=0)
    third = reserve(sim, tenant, "DEMO-REQ-THIRD")
    assert sim.simulate_result(tenant, third.ticket_id, FAIL, tick=0).breaker_state == CLOSED


def test_terminal_results_cannot_be_modified_or_duplicated():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    ticket = reserve(sim, tenant)
    sim.simulate_result(tenant, ticket.ticket_id, SUCCEED, tick=0)
    for outcome in (SUCCEED, FAIL):
        with pytest.raises(SyntheticAdmissionDenied):
            sim.simulate_result(tenant, ticket.ticket_id, outcome, tick=0)


def test_tick_cannot_move_backwards_within_tenant():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    first = reserve(sim, tenant, tick=10)
    with pytest.raises(SyntheticAdmissionDenied):
        reserve(sim, tenant, "DEMO-REQ-OLD", tick=9)
    with pytest.raises(SyntheticAdmissionDenied):
        sim.simulate_result(tenant, first.ticket_id, SUCCEED, tick=9)


@pytest.mark.parametrize("bad_tenant", [None, "DEMO-TENANT-ONE", 7])
def test_unverified_tenant_type_rejected(bad_tenant):
    with pytest.raises(SyntheticAdmissionDenied):
        reserve(OfflineSyntheticResilience(), bad_tenant)


@pytest.mark.parametrize("bad_key", [
    "real-customer-request", "DEMO-REQ-", "DEMO-REQ-\u2603",
    "../tmp/DEMO-REQ-FOO", "DEMO-REQ-" + "A" * 80, None,
])
def test_non_demo_and_invalid_idempotency_keys_rejected(bad_key):
    with pytest.raises(SyntheticAdmissionDenied):
        reserve(OfflineSyntheticResilience(), uuid4(), bad_key)


@pytest.mark.parametrize("bad_tick", [True, -1, 1_000_001, "0", 2.5, None])
def test_invalid_logical_ticks_rejected(bad_tick):
    with pytest.raises(SyntheticAdmissionDenied):
        reserve(OfflineSyntheticResilience(), uuid4(), tick=bad_tick)


def test_boolean_outcome_and_wrong_ticket_type_rejected():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    ticket = reserve(sim, tenant)
    for outcome in (True, "LIVE_PROVIDER_OK", None):
        with pytest.raises(SyntheticAdmissionDenied):
            sim.simulate_result(tenant, ticket.ticket_id, outcome, tick=0)
    with pytest.raises(SyntheticAdmissionDenied):
        sim.simulate_result(tenant, "some ticket", SUCCEED, tick=0)


def test_global_history_cap_bounds_memory_without_eviction():
    sim = OfflineSyntheticResilience()
    for index in range(MAX_TRACKED_TICKETS):
        tenant = UUID(int=index // 4 + 1)
        tick = (index % 4) * 10
        decision = reserve(sim, tenant, f"DEMO-REQ-HIST-{index:03d}", tick=tick)
        assert decision.admitted
        sim.simulate_result(tenant, decision.ticket_id, SUCCEED, tick=tick)
    last = reserve(sim, UUID(int=1), "DEMO-REQ-HIST-OVER", tick=40)
    assert not last.admitted and last.reason == "SIM_HISTORY_CAP"
    # Existing requests still deduplicate when the store is at its cap.
    replay = reserve(sim, UUID(int=1), "DEMO-REQ-HIST-000", tick=40)
    assert replay.admitted and replay.reason == "SIM_IDEMPOTENT_REPLAY"


def test_tenant_tracking_cap_without_unbounded_growth():
    sim = OfflineSyntheticResilience()
    for index in range(16):
        tenant = UUID(int=index + 1)
        ticket = reserve(sim, tenant)
        assert ticket.admitted
        sim.simulate_result(tenant, ticket.ticket_id, SUCCEED, tick=0)
    blocked = reserve(sim, UUID(int=17), "DEMO-REQ-BEYOND")
    assert blocked.reason == "SIM_TENANT_CAP" and not blocked.admitted


def test_cooldown_overflow_fails_without_mutating_ticket():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    a = reserve(sim, tenant, "DEMO-REQ-ONE", tick=999_990)
    b = reserve(sim, tenant, "DEMO-REQ-TWO", tick=999_990)
    sim.simulate_result(tenant, a.ticket_id, FAIL, tick=999_995)
    with pytest.raises(SyntheticAdmissionDenied):
        sim.simulate_result(tenant, b.ticket_id, FAIL, tick=999_999)
    assert sim.inspect(tenant, b.ticket_id).ticket_state == PENDING
    assert sim.inspect(tenant, b.ticket_id).breaker_state == CLOSED


def test_concurrent_duplicate_request_is_one_reservation():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    with ThreadPoolExecutor(max_workers=12) as pool:
        values = list(pool.map(lambda _: reserve(sim, tenant), range(80)))
    assert all(x.admitted for x in values)
    assert len({x.ticket_id for x in values}) == 1
    assert sim.inspect(tenant, values[0].ticket_id).outstanding_for_tenant == 1


def test_concurrent_capacity_cannot_exceed_per_tenant_limit():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(
            lambda i: reserve(sim, tenant, f"DEMO-REQ-CONC-{i:03d}"),
            range(30),
        ))
    assert sum(x.admitted for x in results) == MAX_OUTSTANDING_PER_TENANT


def test_frozen_snapshot_cannot_be_rewritten():
    sim, tenant = OfflineSyntheticResilience(), uuid4()
    result = reserve(sim, tenant)
    with pytest.raises(FrozenInstanceError):
        result.admitted = False


def test_no_api_queue_worker_db_network_secrets_or_real_effect():
    root = Path(__file__).resolve().parents[1]
    text = (root / "apps/api/app/synthetic_delivery_resilience.py").read_text()
    main = (root / "apps/api/app/main.py").read_text()
    for forbidden in (
        "APIRouter(", "requests.", "httpx.", "socket.", "psycopg",
        "redis.", "subprocess.", "urlopen", "http://", "https://",
        "import os", "open(", "time.sleep", "datetime", "asyncio",
    ):
        assert forbidden not in text
    assert "synthetic_delivery_resilience" not in main
