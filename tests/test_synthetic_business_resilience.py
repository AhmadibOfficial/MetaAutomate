"""P2-03s risk prioritization, descriptive unit economics and 90-day pilot guardrails."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_business_resilience import (
    FIXTURE, SCENARIOS, build_continuity_intelligence,
    parse_continuity_fixture, stress_test,
)


def test_90_day_evidence_disciplined_plan_for_both_businesses():
    for ws in ("academy_demo","bespoke_demo"):
        report=build_continuity_intelligence(ws)
        assert report==build_continuity_intelligence(ws)
        assert report["financial"]["cac"] is None
        assert report["financial"]["ltv"] is None
        assert report["financial"]["ebitda"] is None
        assert report["financial"]["net_profit"] is None
        assert report["financial"]["actual_savings"] is None
        assert not report["evidence"]["causation_demonstrated"]
        assert not report["evidence"]["deployment_authorized"]
        assert not report["continuity"]["automatic_recovery_enabled"]
        assert report["evidence"]["provider_calls"]==0
        assert report["evidence"]["database_writes"]==0
        assert [x["stage"] for x in report["pilot_90_days"]] == [
            "ESTABLISH_BASELINE","SUPERVISED_IMPROVEMENTS","VERIFY_OUTCOMES"]
        assert all(x["actual_evidence_complete"] is False
                   for x in report["pilot_90_days"])
        assert len(report["continuity"]["risk_reviews"])==3
        assert report["continuity"]["risk_reviews"] == sorted(
            report["continuity"]["risk_reviews"],
            key=lambda x:(-x["ordinal_priority"],x["code"]))
        assert all(r["auto_trigger_enabled"] is False and
                   r["cost_avoided_verified"] is False
                   for r in report["continuity"]["risk_reviews"])


def test_stress_scenarios_are_not_forecasts_or_real_profit():
    for workspace in ("academy_demo","bespoke_demo"):
        current=stress_test(workspace)
        report=build_continuity_intelligence(workspace)
        assert current["illustrative_contribution"]==report["financial"]["modeled_contribution"]
        assert current["change_vs_current_modeled_contribution"]==0
        for choice in SCENARIOS:
            scenario=stress_test(workspace,choice)
            assert scenario["forecast"] is False
            assert scenario["automated_failover"] is False
            assert scenario["actual_disruption"] is False
            assert scenario["causal_effect_estimated"] is False
            assert scenario["illustrative_contribution"] <= current["illustrative_contribution"]


def test_cost_ratios_are_exact_integer_arithmetic():
    report=build_continuity_intelligence()
    m=report["financial"]
    assert m["identified_cost_to_sales_bps"]==(
        m["identified_costs"]*10000//m["illustrative_gross_sales"])
    assert m["modeled_contribution"]==(
        m["illustrative_gross_sales"]-m["identified_costs"])


@pytest.mark.parametrize("workspace",["unknown", None, False, 1])
def test_unknown_business_rejected(workspace):
    with pytest.raises(SyntheticGrowthError):
        build_continuity_intelligence(workspace)


@pytest.mark.parametrize("scenario",["unexpected", 1, None, True])
def test_unknown_shock_rejected(scenario):
    with pytest.raises(SyntheticGrowthError):
        stress_test("academy_demo",scenario)


@pytest.mark.parametrize("bad",[
    b"",b"{}",b"not-json",b'{"schema_version":1,"schema_version":1}',
    b'{"anything":NaN}',b'{"anything":3.14}',b"\x00"*9,b"x"*40000,
])
def test_bad_inputs_rejected(bad):
    with pytest.raises(SyntheticGrowthError):
        parse_continuity_fixture(bad)


def test_unapproved_personal_data_and_false_predictions_refused():
    doc=json.loads(FIXTURE.read_bytes())
    doc["risk_inputs"][0]["customer_email"]="example@invalid.test"
    with pytest.raises(SyntheticGrowthError):
        parse_continuity_fixture(json.dumps(doc).encode())
    doc=json.loads(FIXTURE.read_bytes())
    doc["risk_inputs"][0]["risks"][0]["predicted_profit"]=6000
    with pytest.raises(SyntheticGrowthError):
        parse_continuity_fixture(json.dumps(doc).encode())


def test_invalid_risk_rank_and_workspace_isolation():
    doc=json.loads(FIXTURE.read_bytes())
    doc["risk_inputs"][0]["risks"][0]["likelihood_score"]=6
    with pytest.raises(SyntheticGrowthError):
        parse_continuity_fixture(json.dumps(doc).encode())
    doc=json.loads(FIXTURE.read_bytes())
    doc["risk_inputs"][1]["workspace"]="academy_demo"
    with pytest.raises(SyntheticGrowthError):
        parse_continuity_fixture(json.dumps(doc).encode())
    doc=json.loads(FIXTURE.read_bytes())
    doc["risk_inputs"][0]["risks"][1]["code"]="SUPPLIER_DELAY"
    with pytest.raises(SyntheticGrowthError):
        parse_continuity_fixture(json.dumps(doc).encode())


def test_cost_exposure_is_not_assumed_savings():
    for workspace in ("academy_demo","bespoke_demo"):
        report=build_continuity_intelligence(workspace)
        risks=report["continuity"]["risk_reviews"]
        assert all(r["mitigation_example"]>=0 for r in risks)
        assert report["financial"]["actual_savings"] is None
        assert report["continuity"]["predicted_incident_probability"] is None
