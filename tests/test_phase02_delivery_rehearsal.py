"""P2-04a invented-event delivery rehearsal safety and state-machine tests."""
from dataclasses import replace
from uuid import uuid4

import pytest

from app.synthetic_delivery import (
    MAX_PER_TENANT, MAX_TOTAL_ATTEMPTS, OPERATION, SIM_COMPLETED,
    SIM_DEAD_LETTER, SIM_PERMANENT_FAILURE, SIM_QUEUED, SIM_RETRY_WAIT,
    SimulationConflict, SimulationError, SimulationNotFound,
    SyntheticDeliveryRehearsal, verify_receipt_chain,
)

SCENE = "DEMO-INVENTORY-LOW-STOCK"


def new_job(service=None, tenant=None, key="DEMO-KEY-001"):
    service = service or SyntheticDeliveryRehearsal()
    tenant = tenant or uuid4()
    return service, tenant, service.submit(tenant, key, SCENE)


def fail_thrice(service, tenant, job):
    for attempt, tick in enumerate((0, 2, 6), 1):
        job = service.simulate_outcome(
            tenant, job.job_id, f"DEMO-EVT-FAIL-{attempt}",
            "SIM_TRANSIENT_FAILURE", tick=tick,
        )
    return job


def test_enqueue_is_source_only_and_never_authorizes_execution():
    service, tenant, job = new_job()
    assert job.operation == OPERATION
    assert job.state == SIM_QUEUED
    assert job.attempts == 0
    assert job.simulation_only is True
    assert job.persisted is False
    assert job.actual_business_data is False
    assert job.external_request_performed is False
    assert job.execution_available is False
    assert job.due_tick == 0
    assert verify_receipt_chain(job)


def test_idempotency_same_tenant_and_conflicting_scenario():
    service, tenant, first = new_job()
    assert service.submit(tenant, "DEMO-KEY-001", SCENE) == first
    with pytest.raises(SimulationConflict):
        service.submit(tenant, "DEMO-KEY-001", "DEMO-INVENTORY-IN-RANGE")


def test_key_scope_and_foreign_job_reads_do_not_leak():
    service = SyntheticDeliveryRehearsal()
    a, b = uuid4(), uuid4()
    first = service.submit(a, "DEMO-KEY-123", SCENE)
    second = service.submit(b, "DEMO-KEY-123", SCENE)
    assert first.job_id != second.job_id
    assert first.tenant_demo_marker != second.tenant_demo_marker
    with pytest.raises(SimulationNotFound):
        service.inspect(a, second.job_id)
    with pytest.raises(SimulationNotFound):
        service.simulate_outcome(a, second.job_id, "DEMO-EVT-ONE",
                                 "SIM_SUCCESS", tick=0)
    with pytest.raises(SimulationNotFound):
        service.simulate_manual_recovery(a, second.job_id, "DEMO-RCV-ONE", tick=1)


@pytest.mark.parametrize("key", [
    "../tmp/a", "CUSTOMER-123", "DEMO-LOW;DROP", "DEMO-\u2603",
    "DEMO-" + "A" * 100, "", None,
])
def test_rejects_unsafe_identifiers(key):
    with pytest.raises(SimulationError):
        SyntheticDeliveryRehearsal().submit(uuid4(), key, SCENE)


def test_rejects_arbitrary_payloads_unknown_cases_and_fake_tenant():
    service = SyntheticDeliveryRehearsal()
    for tenant, key, scenario in [
        ("other-tenant", "DEMO-KEY-111", SCENE),
        (uuid4(), "DEMO-KEY-111", "CUSTOMER-LIVE-INVENTORY"),
        (uuid4(), "DEMO-KEY-111", {"customer": "anything"}),
    ]:
        with pytest.raises(SimulationError):
            service.submit(tenant, key, scenario)


@pytest.mark.parametrize("tick", [-1, True, 1_000_001, 1.5, "0"])
def test_rejects_noncanonical_ticks(tick):
    with pytest.raises(SimulationError):
        SyntheticDeliveryRehearsal().submit(uuid4(), "DEMO-KEY-222", SCENE, tick=tick)


def test_retry_backoff_then_dead_letter_and_final_receipts():
    service, tenant, job = new_job()
    for number, now, due in [(1, 0, 2), (2, 2, 6)]:
        job = service.simulate_outcome(
            tenant, job.job_id, f"DEMO-EVT-FAIL-{number}",
            "SIM_TRANSIENT_FAILURE", tick=now,
        )
        assert job.attempts == number
        assert job.state == SIM_RETRY_WAIT
        assert job.due_tick == due
        assert verify_receipt_chain(job)
    with pytest.raises(SimulationError):
        service.simulate_outcome(tenant, job.job_id, "DEMO-EVT-TOO-EARLY",
                                 "SIM_SUCCESS", tick=5)
    job = service.simulate_outcome(tenant, job.job_id, "DEMO-EVT-FAIL-3",
                                   "SIM_TRANSIENT_FAILURE", tick=6)
    assert job.state == SIM_DEAD_LETTER
    assert job.attempts == 3
    assert job.due_tick is None
    assert len(job.receipts) == 4
    with pytest.raises(SimulationError):
        service.simulate_outcome(tenant, job.job_id, "DEMO-EVT-FAIL-4",
                                 "SIM_TRANSIENT_FAILURE", tick=7)


def test_at_most_one_manual_recovery_and_four_total_attempts():
    service, tenant, first = new_job()
    job = fail_thrice(service, tenant, first)
    job = service.simulate_manual_recovery(
        tenant, job.job_id, "DEMO-RCV-FIRST", tick=7,
    )
    assert job.state == SIM_RETRY_WAIT
    assert job.due_tick == 15
    assert job.recoveries == 1
    assert service.simulate_manual_recovery(
        tenant, job.job_id, "DEMO-RCV-FIRST", tick=7,
    ) == job
    with pytest.raises(SimulationError):
        service.simulate_manual_recovery(
            tenant, job.job_id, "DEMO-RCV-SECOND", tick=8,
        )
    with pytest.raises(SimulationError):
        service.simulate_outcome(
            tenant, job.job_id, "DEMO-EVT-FAIL-4",
            "SIM_TRANSIENT_FAILURE", tick=14,
        )
    job = service.simulate_outcome(
        tenant, job.job_id, "DEMO-EVT-FAIL-4",
        "SIM_TRANSIENT_FAILURE", tick=15,
    )
    assert job.state == SIM_DEAD_LETTER
    assert job.attempts == MAX_TOTAL_ATTEMPTS
    assert verify_receipt_chain(job)
    with pytest.raises(SimulationError):
        service.simulate_manual_recovery(
            tenant, job.job_id, "DEMO-RCV-THIRD", tick=16,
        )


def test_permanent_failure_terminal_and_not_recoverable():
    service, tenant, job = new_job()
    job = service.simulate_outcome(
        tenant, job.job_id, "DEMO-EVT-PERM", "SIM_PERMANENT_FAILURE", tick=0,
    )
    assert job.state == SIM_PERMANENT_FAILURE
    with pytest.raises(SimulationError):
        service.simulate_manual_recovery(
            tenant, job.job_id, "DEMO-RCV-REPLAY", tick=1,
        )


def test_success_terminal_and_duplicate_event_cannot_change_result():
    service, tenant, first = new_job()
    done = service.simulate_outcome(
        tenant, first.job_id, "DEMO-EVT-SUCCESS", "SIM_SUCCESS", tick=0,
    )
    assert done.state == SIM_COMPLETED
    assert service.simulate_outcome(
        tenant, first.job_id, "DEMO-EVT-SUCCESS", "SIM_SUCCESS", tick=0,
    ) == done
    with pytest.raises(SimulationConflict):
        service.simulate_outcome(
            tenant, first.job_id, "DEMO-EVT-SUCCESS",
            "SIM_TRANSIENT_FAILURE", tick=0,
        )
    with pytest.raises(SimulationError):
        service.simulate_outcome(
            tenant, first.job_id, "DEMO-EVT-DIFFERENT", "SIM_SUCCESS", tick=1,
        )


def test_replay_of_first_failed_event_never_increments():
    service, tenant, original = new_job()
    failed = service.simulate_outcome(
        tenant, original.job_id, "DEMO-EVT-FAILED", "SIM_TRANSIENT_FAILURE", tick=0,
    )
    assert failed == service.simulate_outcome(
        tenant, original.job_id, "DEMO-EVT-FAILED", "SIM_TRANSIENT_FAILURE", tick=0,
    )
    assert failed.attempts == 1


def test_rejects_unknown_outcomes_and_invalid_recovery_event():
    service, tenant, job = new_job()
    with pytest.raises(SimulationError):
        service.simulate_outcome(
            tenant, job.job_id, "DEMO-EVT-X123", "NETWORK_REQUEST", tick=0,
        )
    with pytest.raises(SimulationError):
        service.simulate_outcome(
            tenant, job.job_id, "DEMO-RCV-X123", "SIM_SUCCESS", tick=0,
        )
    with pytest.raises(SimulationError):
        service.simulate_manual_recovery(
            tenant, job.job_id, "DEMO-EVT-X123", tick=1,
        )


def test_receipt_snapshot_is_immutable_and_not_signed_evidence():
    service, tenant, job = new_job()
    assert verify_receipt_chain(job)
    with pytest.raises(Exception):
        job.state = SIM_COMPLETED
    tampered = replace(job, receipts=(
        replace(job.receipts[0], state=SIM_COMPLETED),
    ))
    assert not verify_receipt_chain(tampered)


def test_receipt_chain_must_match_reported_final_state():
    service, tenant, job = new_job()
    job = service.simulate_outcome(
        tenant, job.job_id, "DEMO-EVT-SUCCESS", "SIM_SUCCESS", tick=0,
    )
    assert verify_receipt_chain(job)
    for stale in (
        replace(job, state=SIM_QUEUED),
        replace(job, attempts=0),
        replace(job, due_tick=99),
    ):
        assert not verify_receipt_chain(stale)


def test_idempotent_simulated_concurrent_submission():
    from concurrent.futures import ThreadPoolExecutor
    service = SyntheticDeliveryRehearsal()
    tenant = uuid4()
    with ThreadPoolExecutor(max_workers=12) as pool:
        ids = list(pool.map(
            lambda _: service.submit(tenant, "DEMO-KEY-THREAD", SCENE).job_id,
            range(80),
        ))
    assert len(set(ids)) == 1
    assert len(service.inspect(tenant, ids[0]).receipts) == 1


def test_quotas_are_bounded_and_independent_by_tenant():
    service = SyntheticDeliveryRehearsal()
    tenant = uuid4()
    for i in range(MAX_PER_TENANT):
        service.submit(tenant, f"DEMO-KEY-{i:03d}", SCENE)
    with pytest.raises(SimulationError):
        service.submit(tenant, "DEMO-KEY-OVER", SCENE)
    # Re-submitting an existing key consumes no additional quota.
    job = service.submit(tenant, "DEMO-KEY-000", SCENE)
    assert job.state == SIM_QUEUED
    service.submit(uuid4(), "DEMO-KEY-NEW", SCENE)


def test_no_http_worker_storage_or_live_route_wiring():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = (root / "apps/api/app/synthetic_delivery.py").read_text()
    main = (root / "apps/api/app/main.py").read_text()
    for forbidden in (
        "requests.", "httpx.", "psycopg.", "sqlite3", "subprocess",
        "APIRouter(", "app.include_router(synthetic_delivery",
        "socket.", "http://", "https://",
    ):
        assert forbidden not in source
    assert "synthetic_delivery" not in main
