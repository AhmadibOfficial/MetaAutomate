"""P2-04c synthetic-only failure analytics: deterministic negative tests."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from uuid import uuid4

import pytest

from app.synthetic_incident_observability import (
    COMPLETED, DEAD, PERMANENT, QUEUED, RECOVERY, RETRY,
    SyntheticIncidentDenied, SyntheticObservation,
    analyze_synthetic_incidents,
)


def evt(tenant, idx, kind, tick, attempts, job="DEMO-JOB-PRIMARY"):
    return SyntheticObservation(
        tenant, job, f"DEMO-EVT-{idx:04d}", kind, tick, attempts
    )


def cycle(tenant):
    return [
        evt(tenant, 0, QUEUED, 0, 0),
        evt(tenant, 1, RETRY, 0, 1),
        evt(tenant, 2, RETRY, 2, 2),
        evt(tenant, 3, DEAD, 6, 3),
    ]


def test_empty_report_is_local_only_and_safe():
    result = analyze_synthetic_incidents(uuid4(), [], now_tick=0)
    assert result.event_count == result.job_count == 0
    assert result.recommendation == "NO_SYNTHETIC_ALERT"
    assert result.simulation_only is True
    assert result.persisted is False
    assert result.executed is False
    assert result.authenticated_tenancy is False
    assert result.actual_business_data is False
    assert result.provider_receipts_verified is False
    assert result.external_incident_created is False


def test_single_job_success_state_and_no_fabricated_alert():
    tenant = uuid4()
    report = analyze_synthetic_incidents(tenant, [
        evt(tenant, 0, QUEUED, 0, 0),
        evt(tenant, 1, COMPLETED, 0, 1),
    ], now_tick=10)
    assert report.completed_count == 1
    assert report.job_count == 1
    assert report.recommendation == "NO_SYNTHETIC_ALERT"
    assert report.jobs[0].state == COMPLETED
    assert report.jobs[0].due_tick is None


def test_transient_retries_and_dead_letter_signal():
    tenant = uuid4()
    report = analyze_synthetic_incidents(tenant, cycle(tenant), now_tick=6)
    assert report.dead_letter_count == 1
    assert report.completed_count == 0
    assert report.jobs[0].attempts == 3
    assert report.recommendation == "REVIEW_SYNTHETIC_INCIDENTS_ONLY"
    assert report.recovery_rehearsal_count == 0


def test_one_synthetic_recovery_then_success():
    tenant = uuid4()
    events = cycle(tenant) + [
        evt(tenant, 4, RECOVERY, 7, 3),
        evt(tenant, 5, COMPLETED, 15, 4),
    ]
    report = analyze_synthetic_incidents(tenant, events, now_tick=15)
    assert report.completed_count == 1
    assert report.dead_letter_count == 0
    assert report.recovery_rehearsal_count == 1
    assert report.jobs[0].simulated_recovery_count == 1
    assert report.jobs[0].event_count == 6


def test_terminal_dead_after_recovery_has_no_second_recovery():
    tenant = uuid4()
    events = cycle(tenant) + [
        evt(tenant, 4, RECOVERY, 7, 3),
        evt(tenant, 5, DEAD, 15, 4),
    ]
    report = analyze_synthetic_incidents(tenant, events, now_tick=15)
    assert report.dead_letter_count == 1
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(
            tenant,
            events + [evt(tenant, 6, RECOVERY, 16, 4)],
            now_tick=16,
        )


def test_recovered_but_waiting_is_observation_not_action():
    tenant = uuid4()
    report = analyze_synthetic_incidents(
        tenant, cycle(tenant) + [evt(tenant, 4, RECOVERY, 7, 3)],
        now_tick=25,
    )
    assert report.retry_wait_count == 1
    assert report.stalled_count == 1
    assert report.jobs[0].due_tick == 15
    assert report.recommendation == "REVIEW_SYNTHETIC_INCIDENTS_ONLY"


def test_observed_queued_and_retry_staleness():
    tenant = uuid4()
    queued = analyze_synthetic_incidents(tenant, [evt(tenant, 0, QUEUED, 0, 0)], now_tick=10)
    assert queued.queued_count == queued.stalled_count == 1
    retry = analyze_synthetic_incidents(
        tenant,
        [evt(tenant, 0, QUEUED, 0, 0), evt(tenant, 1, RETRY, 0, 1)],
        now_tick=12,
    )
    assert retry.retry_wait_count == retry.stalled_count == 1


def test_mixed_job_summary_is_sorted_and_tenant_scoped():
    tenant = uuid4()
    events = [
        evt(tenant, 0, QUEUED, 0, 0, job="DEMO-JOB-ZZZ"),
        evt(tenant, 1, QUEUED, 0, 0, job="DEMO-JOB-AAA"),
        evt(tenant, 2, PERMANENT, 0, 1, job="DEMO-JOB-ZZZ"),
        evt(tenant, 3, COMPLETED, 1, 1, job="DEMO-JOB-AAA"),
    ]
    report = analyze_synthetic_incidents(tenant, events, now_tick=2)
    assert report.permanent_failure_count == 1
    assert report.completed_count == 1
    assert report.event_count == 4
    assert [j.job_id for j in report.jobs] == ["DEMO-JOB-AAA", "DEMO-JOB-ZZZ"]
    assert str(tenant) not in repr(report)


def test_multiple_tenants_are_rejected_in_one_report():
    tenant, intruder = uuid4(), uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [
            evt(tenant, 0, QUEUED, 0, 0),
            evt(intruder, 1, QUEUED, 0, 0, job="DEMO-JOB-OTHER"),
        ], now_tick=1)


def test_duplicate_event_id_across_jobs_denied():
    tenant = uuid4()
    a = evt(tenant, 0, QUEUED, 0, 0)
    b = replace(a, job_id="DEMO-JOB-SECOND")
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [a, b], now_tick=0)


@pytest.mark.parametrize("event", [
    lambda t: evt(t, 0, RETRY, 0, 1),
    lambda t: evt(t, 0, QUEUED, 0, 1),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), kind="LIVE_DELIVER"),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), job_id="../PRIVATE"),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), event_id="REAL-EVENT-ID"),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), attempts=True),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), attempts=-1),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), attempts=5),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), tick=-1),
    lambda t: replace(evt(t, 0, QUEUED, 0, 0), tick="0"),
])
def test_malformed_first_event_rejected(event):
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [event(tenant)], now_tick=1)


def test_untrusted_data_type_and_subclass_denied():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [{"secret": "not an event"}], now_tick=0)
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(str(tenant), [], now_tick=0)


@pytest.mark.parametrize("now", [-1, True, 1000001, "10", 2.0])
def test_invalid_analysis_tick_rejected(now):
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(uuid4(), [], now_tick=now)


def test_future_and_out_of_order_observations_rejected():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [evt(tenant, 0, QUEUED, 11, 0)], now_tick=10)
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [
            evt(tenant, 0, QUEUED, 10, 0),
            evt(tenant, 1, COMPLETED, 9, 1),
        ], now_tick=10)


def test_invalid_jump_over_retry_due_time_rejected():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [
            evt(tenant, 0, QUEUED, 0, 0),
            evt(tenant, 1, RETRY, 0, 1),
            evt(tenant, 2, COMPLETED, 1, 2),
        ], now_tick=10)


def test_skip_attempt_fails():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [
            evt(tenant, 0, QUEUED, 0, 0),
            evt(tenant, 1, RETRY, 0, 2),
        ], now_tick=2)


def test_terminal_state_cannot_be_extended():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [
            evt(tenant, 0, QUEUED, 0, 0),
            evt(tenant, 1, PERMANENT, 0, 1),
            evt(tenant, 2, COMPLETED, 1, 2),
        ], now_tick=2)


def test_no_manual_recovery_before_third_dead_letter_attempt():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, [
            evt(tenant, 0, QUEUED, 0, 0),
            evt(tenant, 1, RECOVERY, 1, 0),
        ], now_tick=2)


def test_recovery_due_tick_enforced():
    tenant = uuid4()
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant,
            cycle(tenant) + [
                evt(tenant, 4, RECOVERY, 7, 3),
                evt(tenant, 5, COMPLETED, 14, 4),
            ], now_tick=15)


def test_boundaries_do_not_evict_or_accept_unbounded_events():
    tenant = uuid4()
    events = [evt(tenant, i, QUEUED, 0, 0, job=f"DEMO-JOB-{i:03d}") for i in range(33)]
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, events, now_tick=0)
    with pytest.raises(SyntheticIncidentDenied):
        analyze_synthetic_incidents(tenant, events * 4, now_tick=0)


def test_staleness_does_not_execute_a_recovery():
    tenant = uuid4()
    report = analyze_synthetic_incidents(
        tenant, cycle(tenant), now_tick=100,
    )
    assert report.recommendation == "REVIEW_SYNTHETIC_INCIDENTS_ONLY"
    assert report.executed is False
    assert report.external_incident_created is False
    assert report.persisted is False


def test_frozen_report_cannot_be_rewritten():
    report = analyze_synthetic_incidents(uuid4(), [], now_tick=0)
    with pytest.raises(FrozenInstanceError):
        report.completed_count = 999


def test_no_api_route_webhook_storage_secrets_or_network():
    root = Path(__file__).resolve().parents[1]
    module = (root / "apps/api/app/synthetic_incident_observability.py").read_text()
    api = (root / "apps/api/app/main.py").read_text()
    for fragment in (
        "APIRouter(", "requests.", "httpx.", "socket.",
        "psycopg", "redis.", "subprocess.", "urlopen", "http://",
        "https://", "import os", "open(", "datetime", "time.sleep",
    ):
        assert fragment not in module
    assert "synthetic_incident_observability" not in api
