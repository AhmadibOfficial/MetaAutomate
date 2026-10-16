"""P2-03n evidence: synthetic-only decision workflow and safety guards."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/api'))

from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_growth_value_intelligence import build_committed_value_report
from app.synthetic_business_decisions import (
    build_demo_workspace, decision_dashboard, simulate_decision,
    create_manual_action, transition_manual_action, verify_outcome,
)


def test_dashboard_provenance_and_ranked_opportunities():
    report = build_committed_value_report()
    for workspace in ("academy_demo", "bespoke_demo"):
        view = decision_dashboard(report, workspace)
        assert view["source_evidence_sha256"] == report["evidence_sha256"]
        assert view["not_net_profit"] and not view["production_ready"]
        assert view["current"]["gross_sales"] >= 0
        assert all(op["evidence_quality"] == "SYNTHETIC_ONLY" for op in view["opportunities"])
        assert view == build_demo_workspace(workspace)


def test_simulation_identity_and_illustrative_changes():
    report = build_committed_value_report()
    for workspace in ("academy_demo", "bespoke_demo"):
        view = decision_dashboard(report, workspace)
        sim = simulate_decision(report, workspace)
        assert sim["illustrative_contribution"] == view["current"]["modeled_contribution_after_identified_costs"]
        assert sim["change_from_source_contribution"] == 0
        assert not sim["forecast"] and not sim["action_executed"]
        changed = simulate_decision(report, workspace, price_change_bps=1000, order_change_bps=1000)
        assert changed["illustrative_gross_sales"] >= sim["illustrative_gross_sales"]


@pytest.mark.parametrize("value", [True, 1.5, "100", 5001, -5001])
def test_invalid_sensitivity_fails_closed(value):
    with pytest.raises(SyntheticGrowthError):
        simulate_decision(build_committed_value_report(), "academy_demo", price_change_bps=value)


def test_manual_lifecycle_and_noncausal_verification():
    report = build_committed_value_report()
    opportunity = decision_dashboard(report, "academy_demo")["opportunities"][0]
    task = create_manual_action(report, "academy_demo", opportunity["id"])
    with pytest.raises(SyntheticGrowthError):
        verify_outcome(report, "academy_demo", task)
    for target in ("APPROVED_FOR_MANUAL_REVIEW", "IN_PROGRESS", "COMPLETED"):
        task = transition_manual_action(task, target)
    result = verify_outcome(report, "academy_demo", task)
    assert result["outcome_attributable_to_task"] is False
    assert result["effect_estimate"] is None
    assert task["external_execution_enabled"] is False
    with pytest.raises(SyntheticGrowthError):
        transition_manual_action(task, "IN_PROGRESS")


def test_cross_workspace_and_tampered_report_are_blocked():
    report = build_committed_value_report()
    op = decision_dashboard(report, "academy_demo")["opportunities"][0]
    with pytest.raises(SyntheticGrowthError):
        create_manual_action(report, "bespoke_demo", op["id"])
    with pytest.raises(SyntheticGrowthError):
        decision_dashboard(report, "unknown_business")
    report["businesses"][0]["comparison"]["current"]["gross_sales"] += 1
    with pytest.raises(SyntheticGrowthError):
        decision_dashboard(report, "academy_demo")


def test_unapproved_or_external_task_rejected():
    report = build_committed_value_report()
    op = decision_dashboard(report, "academy_demo")["opportunities"][0]
    task = create_manual_action(report, "academy_demo", op["id"])
    task["external_execution_enabled"] = True
    with pytest.raises(SyntheticGrowthError):
        transition_manual_action(task, "APPROVED_FOR_MANUAL_REVIEW")
