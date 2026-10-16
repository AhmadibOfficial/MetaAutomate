"""P2-03m: non-causal, reconciled, finance-safe growth value intelligence."""
from copy import deepcopy
import ast
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import (  # noqa: E402
    FIXTURE, SyntheticGrowthError,
)
from app.synthetic_growth_value_intelligence import (  # noqa: E402
    MAX_BYTES, SCENARIOS, build_business_value_report,
    build_committed_value_report, validate_value_evidence,
)


def scenario():
    return json.loads(SCENARIOS.read_bytes())


def make_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@pytest.mark.parametrize("goal", ["CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"])
def test_reconciled_comparative_scorecards_are_deterministic(goal):
    a = build_committed_value_report(goal=goal)
    assert a == build_committed_value_report(goal=goal)
    assert validate_value_evidence(a)
    assert a["goal"] == goal
    assert a["classification"] == "SYNTHETIC_SOURCE_ONLY"
    assert a["units"] == "DEMO_CREDITS_NOT_USD"
    assert a["interpretation"]["causal_roi_claim_permitted"] is False
    assert a["interpretation"]["modeled_contribution_is_net_profit"] is False
    assert a["interpretation"]["real_marketing_conversions_measured"] is False
    assert not a["actual_customer_data"]
    assert a["external_provider_calls"] == 0
    assert a["messages_sent"] == 0
    assert a["real_workflow_executions"] == 0
    assert a["actual_subscription_charges"] == 0
    assert a["database_changes"] == 0
    assert set(row["workspace"] for row in a["businesses"]) == {
        "academy_demo", "bespoke_demo",
    }
    for b in a["businesses"]:
        c = b["comparison"]
        assert c["equal_periods_days"] == 30
        assert c["baseline_measured_from_customer_records"] is False
        assert c["incremental_contribution_proven"] is False
        assert c["profit_or_roi_proven"] is False
        assert c["staff_time_saved_by_automation_proven"] is False
        assert c["conversion_rate_computable"] is False
        assert c["baseline"]["net_profit_verified"] is False
        assert c["current"]["taxes_and_fixed_overhead_included"] is False
        assert b["workflow_effectiveness"]["delivered"] == 0
        assert b["workflow_effectiveness"]["approved"] == 0
        assert b["workflow_effectiveness"]["incremental_sales_from_workflows"] is None
        assert b["workflow_effectiveness"]["causal_effect_verified"] is False
        assert b["release_decision"] == "NO_REAL_AUTOMATION_OR_COMMERCIAL_ACTIVATION"
        assert all(p["validated_causal_effect"] is False
                   and p["monetary_benefit_promised"] is False
                   and p["automated_action_available"] is False
                   for p in b["ranked_opportunities"])


def test_accounting_cost_waterfall_and_ranked_opportunities():
    r = build_committed_value_report()
    academy, bespoke = r["businesses"]
    ab = academy["comparison"]["baseline"]
    ac = academy["comparison"]["current"]
    bb = bespoke["comparison"]["baseline"]
    bc = bespoke["comparison"]["current"]
    assert (ab["gross_sales"], ab["total_identified_costs"],
            ab["modeled_contribution_after_identified_costs"]) == (18000, 11000, 7000)
    assert (ac["gross_sales"], ac["total_identified_costs"],
            ac["modeled_contribution_after_identified_costs"]) == (25000, 12700, 12300)
    assert academy["comparison"]["modeled_contribution_after_identified_costs"][
        "absolute_change"] == 5300
    assert academy["modeled_contribution_target"] == 20000
    assert academy["modeled_gap_to_target"] == 7700
    assert not any(x["code"] == "REVIEW_COST_LEAKAGE"
                   for x in academy["ranked_opportunities"])
    assert (bb["gross_sales"], bb["total_identified_costs"],
            bb["modeled_contribution_after_identified_costs"]) == (37000, 31300, 5700)
    assert (bc["gross_sales"], bc["total_identified_costs"],
            bc["modeled_contribution_after_identified_costs"]) == (35000, 30300, 4700)
    assert bespoke["comparison"]["modeled_contribution_after_identified_costs"][
        "absolute_change"] == -1000
    assert bespoke["modeled_gap_to_target"] == 10300
    assert bespoke["comparison"]["largest_identified_cost_increases"][0] == {
        "cost": "software_cost",
        "absolute_change": 2600,
        "relative_change_bps": 65000,
        "baseline_zero": False,
    }
    codes = [x["code"] for x in bespoke["ranked_opportunities"]]
    assert "REVIEW_COST_LEAKAGE" in codes
    assert "INVESTIGATE_LOWER_SALES" in codes
    assert "KEEP_CUSTOMER_SAFEGUARDS" in codes
    assert bespoke["ranked_opportunities"][0]["priority"] == "HIGH"
    assert len({x["id"] for x in bespoke["ranked_opportunities"]}) == len(codes)
    assert bespoke["workflow_effectiveness"]["reviewable"] == 4
    assert bespoke["workflow_effectiveness"]["suppressed"] == 2
    assert bespoke["workflow_effectiveness"]["deferred"] == 0


def test_goal_relevance_changes_review_funnel_without_faking_delivery():
    report = build_committed_value_report(goal="RETENTION")
    for business in report["businesses"]:
        stats = business["workflow_effectiveness"]
        assert stats["reviewable"] == 3
        assert stats["deferred"] == 1
        assert stats["suppressed"] == 2
        assert stats["actual_customer_responses"] == 0
        assert stats["cost_per_verified_conversion"] is None
        assert stats["provider_attribution_verified"] is False


def test_zero_baseline_denominators_and_zero_orders_are_explicitly_undefined():
    doc = scenario()
    b = doc["workspaces"][0]["baseline"]
    b.update({"gross_sales": 0, "variable_cost": 0, "marketing_spend": 0,
              "processing_fees": 0, "fulfillment_cost": 0, "software_cost": 0,
              "refunds": 0, "completed_orders": 0, "repeat_orders": 0})
    r = build_business_value_report(make_bytes(doc))
    c = r["businesses"][0]["comparison"]
    assert c["baseline"]["identified_cost_ratio_bps"] is None
    assert c["baseline"]["contribution_margin_bps"] is None
    assert c["baseline"]["mean_gross_per_order_floor"] is None
    assert c["gross_sales"]["relative_change_bps"] is None
    assert c["gross_sales"]["baseline_zero"] is True
    assert c["modeled_contribution_after_identified_costs"]["relative_change_bps"] is None


@pytest.mark.parametrize("path,value", [
    (("workspaces", 0, "current", "gross_sales"), 26000),
    (("workspaces", 0, "current", "completed_orders"), 4),
    (("workspaces", 1, "current", "marketing_spend"), 0),
    (("workspaces", 1, "current", "repeat_orders"), 0),
    (("workspaces", 0, "current", "variable_cost"), 1),
])
def test_current_period_must_reconcile_to_source_orders_and_goals(path, value):
    d = scenario()
    o = d
    for key in path[:-1]:
        o = o[key]
    o[path[-1]] = value
    with pytest.raises(SyntheticGrowthError, match="does not reconcile"):
        build_business_value_report(make_bytes(d))


@pytest.mark.parametrize("field,value", [
    ("days", 29), ("gross_sales", True), ("processing_fees", -1),
    ("refunds", 999999999), ("completed_orders", -2), ("repeat_orders", 100001),
    ("staff_minutes", 1000001), ("software_cost", 100000001),
])
def test_bad_baseline_period_denied(field, value):
    d = scenario()
    d["workspaces"][0]["baseline"][field] = value
    with pytest.raises(SyntheticGrowthError):
        build_business_value_report(make_bytes(d))


def test_comparison_scope_and_human_fields_rejected():
    d = scenario()
    d["workspaces"][0]["baseline"]["customer_email"] = "owner@example.com"
    with pytest.raises(SyntheticGrowthError, match="Invalid financial period fields"):
        build_business_value_report(make_bytes(d))
    d = scenario()
    d["workspaces"][0]["workspace"] = "real_customer"
    with pytest.raises(SyntheticGrowthError, match="Unknown or duplicate workspace"):
        build_business_value_report(make_bytes(d))
    d = scenario()
    d["workspaces"][1]["workspace"] = "academy_demo"
    with pytest.raises(SyntheticGrowthError, match="Unknown or duplicate workspace"):
        build_business_value_report(make_bytes(d))
    d = scenario()
    d["workspaces"][0]["current"]["period_id"] = "SIM-BASELINE-ACADEMY_DEMO"
    with pytest.raises(SyntheticGrowthError, match="Unexpected comparison period"):
        build_business_value_report(make_bytes(d))


@pytest.mark.parametrize("raw", [
    b"", b"\x00", b"\xff", b"[]", b"{}", b" "*(MAX_BYTES+1),
    b'{"schema_version":1, "schema_version":1}',
    b'{"schema_version":NaN}',
    b'{"schema_version":Infinity}',
    b'{"schema_version":1.3}',
])
def test_malformed_inputs_are_denied(raw):
    with pytest.raises(SyntheticGrowthError):
        build_business_value_report(raw)


def test_real_customer_fixture_and_invalid_goal_denied():
    with pytest.raises(SyntheticGrowthError, match="Unsupported business goal"):
        build_committed_value_report(goal="AUTO_BILL")
    with pytest.raises(SyntheticGrowthError, match="Unsupported business goal"):
        build_committed_value_report(goal=True)
    d = scenario()
    d["currency"] = "USD"
    with pytest.raises(SyntheticGrowthError, match="Real business records"):
        build_business_value_report(make_bytes(d))
    d = scenario()
    d["classification"] = "REAL_CUSTOMER_DATA"
    with pytest.raises(SyntheticGrowthError, match="Real business records"):
        build_business_value_report(make_bytes(d))
    f = json.loads(FIXTURE.read_bytes())
    f["workspaces"][1]["events"][0]["email"] = "customer@example.com"
    with pytest.raises(SyntheticGrowthError):
        build_business_value_report(SCENARIOS.read_bytes(),
                                    raw_growth_fixture=make_bytes(f))


def test_negative_contribution_is_allowed_but_not_falsely_reported_as_profit():
    d = scenario()
    d["workspaces"][1]["current"]["processing_fees"] = 70000
    r = build_business_value_report(make_bytes(d))
    c = r["businesses"][1]
    assert c["comparison"]["current"]["modeled_contribution_after_identified_costs"] < 0
    assert c["comparison"]["current"]["contribution_margin_bps"] < 0
    assert c["modeled_gap_to_target"] > 15000
    assert c["comparison"]["current"]["net_profit_verified"] is False


def test_modified_scorecard_is_detected():
    original = build_committed_value_report()
    assert validate_value_evidence(original)
    edited = deepcopy(original)
    edited["businesses"][0]["comparison"]["current"]["gross_sales"] += 999
    assert not validate_value_evidence(edited)
    edited = deepcopy(original)
    edited["messages_sent"] = 1
    assert not validate_value_evidence(edited)
    assert not validate_value_evidence({})


def test_offline_module_cannot_call_providers_or_mount_api_route():
    path = ROOT / "apps/api/app/synthetic_growth_value_intelligence.py"
    code = path.read_text(encoding="utf-8")
    main = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
    assert "include_router(synthetic_growth_value_intelligence" not in main
    imports = set()
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint({
        "requests", "httpx", "urllib", "smtplib", "fastapi", "stripe",
        "sqlalchemy", "psycopg", "redis", "celery", "subprocess", "aiohttp",
        "socket", "boto3",
    })
    assert "NON_OPERATIONAL" in code
    assert "build_growth_work_plan" in code
    assert "modeled_contribution_is_net_profit" in code
