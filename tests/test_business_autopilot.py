"""Product demo acceptance: truthful outcomes, exact approval and reproducibility."""
from pathlib import Path
import socket

import pytest

from app.business_autopilot import (
    DemoConflict, DemoRun, SCENARIOS, canonical_hash, replay, strict_json, verify_bundle,
)


@pytest.mark.parametrize("case", SCENARIOS)
def test_complete_replay_deterministic_and_no_real_outcome_claim(case):
    first, second = replay(case), replay(case)
    first.verify()
    assert first.stage == "VERIFIED"
    assert first.bundle() == second.bundle()
    assert first.verification["verified"] is True
    assert first.verification["business_outcomes_verified"] is False
    bundle = first.bundle()
    assert bundle["boundaries"]["live_execution"] == "DENY"
    assert bundle["boundaries"]["operational_release"] == "NO_GO"
    assert bundle["boundaries"]["tenant_isolation_demonstrated"] is False
    assert bundle["outcomes"]["real_business_outcomes"] == {
        "time_saved_minutes": None, "cash_saved_minor": None,
        "revenue_recovered_minor": None, "roi_verified": False, "evidence": "NOT_MEASURED"}
    assert bundle["simulation"]["inventory_after"] == bundle["assessment"]["inventory"]["items"]
    assert all(bundle["simulation"][key] == 0 for key in (
        "stock_units_moved", "purchase_orders_sent", "external_requests", "database_writes"))
    assert first.approval["identity_verified"] is False
    assert first.plan["workspace_preview"]["execution_allowed"] is False


def test_standard_arithmetic_has_units_and_distinguishes_purchase_cost():
    run = replay()
    assert [draft["units"] for draft in run.plan["drafts"]] == [37, 31]
    assert sum(d["estimated_purchase_cost_minor"] for d in run.plan["drafts"]) == 290500
    estimate = run.outcomes()["illustrative_estimate"]
    assert estimate["currency"] == "QAR"
    assert estimate["manual_minutes"] == 24
    assert estimate["assisted_minutes"] == 6
    assert estimate["capacity_minutes"] == 18
    assert estimate["capacity_value_minor"] == 1800
    assert estimate["delivery_cost_minor"] == 1000
    assert estimate["net_capacity_value_minor"] == 800


def test_blocked_step_excluded_from_benefit_no_auto_retry_or_alternative():
    run = replay("partial_failure")
    assert run.simulation["status"] == "PARTIAL_BLOCKED"
    assert len(run.simulation["steps"]) == 2
    assert [s["status"] for s in run.simulation["steps"]] == ["DRAFT_PREPARED", "BLOCKED"]
    outcome = run.outcomes()
    assert outcome["goal"] == "PREVIEW_GOAL_INCOMPLETE"
    assert outcome["observed_in_simulation"]["steps_blocked"] == 1
    assert outcome["illustrative_estimate"]["capacity_minutes"] == 9
    assert outcome["illustrative_estimate"]["net_capacity_value_minor"] == -100
    run.verify()  # Reproducibility is separate from meeting the objective.
    assert run.verification["verified"] is True


def test_high_cost_case_never_clamps_negative_benefit_to_zero():
    run = replay("high_cost")
    assert run.outcomes()["illustrative_estimate"]["net_capacity_value_minor"] == -3200
    assert run.outcomes()["real_business_outcomes"]["roi_verified"] is False


@pytest.mark.parametrize("action", ["make_plan", "simulate", "verify", "bundle"])
def test_steps_cannot_skip_the_required_state(action):
    run = DemoRun()
    before = run.snapshot()
    with pytest.raises(DemoConflict):
        getattr(run, action)()
    assert run.snapshot() == before


def planned():
    run = DemoRun()
    run.assess()
    run.make_plan()
    return run


def test_unapproved_or_rejected_plan_cannot_simulate():
    run = planned()
    with pytest.raises(DemoConflict):
        run.simulate()
    run.decide(plan_sha256=run.plan["plan_sha256"], decision="REJECT", simulation_only=True)
    with pytest.raises(DemoConflict):
        run.simulate()
    assert run.stage == "REJECTED"
    assert run.simulation is None
    assert run.events[-1]["event"] == "SIMULATION_REVIEW_REJECT"


@pytest.mark.parametrize("change", [
    {"plan_sha256": "0" * 64}, {"decision": "ENABLE_LIVE"}, {"simulation_only": False},
    {"simulation_only": 1}, {"simulation_only": "true"},
])
def test_review_does_not_accept_stale_or_wider_authority(change):
    run = planned()
    before = run.snapshot()
    payload = {"plan_sha256": run.plan["plan_sha256"], "decision": "APPROVE", "simulation_only": True}
    with pytest.raises(DemoConflict):
        run.decide(**{**payload, **change})
    assert run.snapshot() == before


def test_approval_bound_to_scenario_costs_and_inventory():
    standard, costly = planned(), DemoRun("high_cost")
    costly.assess(); costly.make_plan()
    assert standard.plan["plan_sha256"] != costly.plan["plan_sha256"]
    with pytest.raises(DemoConflict):
        costly.decide(plan_sha256=standard.plan["plan_sha256"], decision="APPROVE", simulation_only=True)
    standard.decide(plan_sha256=standard.plan["plan_sha256"], decision="APPROVE", simulation_only=True)
    standard.plan["drafts"][0]["units"] += 1
    with pytest.raises(DemoConflict):
        standard.simulate()


def test_snapshot_is_detached_and_run_state_is_not_shared():
    first, second = planned(), planned()
    snap = first.snapshot()
    snap["plan"]["drafts"][0]["units"] = 999
    assert first.plan["drafts"][0]["units"] == 37
    first.decide(plan_sha256=first.plan["plan_sha256"], decision="APPROVE", simulation_only=True)
    assert second.stage == "PLANNED"


def test_duplicate_transition_cannot_append_or_repeat_work():
    run = replay()
    before = run.bundle()
    with pytest.raises(DemoConflict):
        run.simulate()
    assert run.bundle() == before


def test_audit_hashes_bind_every_ordered_event():
    audit = replay().events
    previous = "0" * 64
    for sequence, event in enumerate(audit, 1):
        assert event["sequence"] == sequence
        assert event["previous_sha256"] == previous
        assert event["sha256"] == canonical_hash({k: v for k, v in event.items() if k != "sha256"})
        previous = event["sha256"]


@pytest.mark.parametrize("field", ["sources", "assessment", "plan", "approval", "simulation", "outcomes", "audit", "boundaries"])
def test_tampered_bundle_rejected_even_if_top_level_hash_would_be_recomputed(field):
    bundle = replay().bundle()
    bundle[field] = {} if field != "audit" else []
    assert verify_bundle(bundle)["verified"] is False


def test_changed_assumptions_with_rehashed_plan_and_chain_not_accepted():
    bundle = replay().bundle()
    bundle["plan"]["assumptions"]["staff_hourly_cost_minor"] = 600000
    bundle["plan"]["plan_sha256"] = canonical_hash({k: v for k, v in bundle["plan"].items() if k != "plan_sha256"})
    bundle["approval"]["plan_sha256"] = bundle["plan"]["plan_sha256"]
    previous = "0" * 64
    for event in bundle["audit"]:
        event["previous_sha256"] = previous
        event["sha256"] = canonical_hash({k: v for k, v in event.items() if k != "sha256"})
        previous = event["sha256"]
    assert verify_bundle(bundle)["verified"] is False


@pytest.mark.parametrize("value", [None, [], {}, {"scenario_id": "live"}, {"scenario_id": ["standard"]}])
def test_unknown_report_shapes_fail_closed(value):
    assert verify_bundle(value)["verified"] is False


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b"\xff", b"", b" " * 131073])
def test_duplicate_keys_nonfinite_and_unbounded_json_rejected(raw):
    with pytest.raises(ValueError):
        strict_json(raw)


@pytest.mark.parametrize("case", ["real", "../../.env", "https://provider.invalid", None, True])
def test_only_committed_scenarios_accepted(case):
    with pytest.raises(ValueError):
        DemoRun(case)


def test_replay_and_verification_never_connect_or_write(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("No network, database or file write is permitted")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr("psycopg.connect", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    for scenario in SCENARIOS:
        run = replay(scenario)
        run.verify()
        assert run.verification["verified"]


def test_demo_is_not_mounted_in_main_or_enabled_by_deployment():
    from app.main import app
    assert not any("/demo" in getattr(route, "path", "") for route in app.routes)
    root = Path(__file__).resolve().parents[1]
    for path in ["render.yaml", "docker-compose.yml", "deploy/staging/compose.yaml", "apps/api/Dockerfile.prod"]:
        assert "autopilot" not in (root / path).read_text().lower()
