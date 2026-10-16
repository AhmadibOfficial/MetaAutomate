"""P2-03j guarded source-only orchestration regression suite."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_orchestration import (  # noqa: E402
    GOALS, NON_OPERATIONAL, PROVIDERS, build_growth_work_plan, build_committed_growth_work_plan,
)
from app.synthetic_growth_autopilot import FIXTURE, SyntheticGrowthError  # noqa: E402


@pytest.mark.parametrize("goal", sorted(GOALS))
def test_all_goals_are_deterministic_non_executable(goal):
    a = build_committed_growth_work_plan(goal=goal)
    assert a == build_committed_growth_work_plan(goal=goal)
    assert a["non_operational_controls"] == NON_OPERATIONAL
    assert a["classification"] == "SYNTHETIC_SOURCE_REVIEW"
    assert a["module"] == "P2-03j_BUSINESS_GROWTH_AUTOMATION"
    assert len(a["workspaces"]) == 2
    for business in a["workspaces"]:
        assert business["goal"] == goal
        assert business["operational_status"] == "NO_GO"
        assert business["ready_to_execute"] == business["externally_delivered"] == 0
        assert len(business["workflow_proposals"]) == 6
        assert len({p["plan_id"] for p in business["workflow_proposals"]}) == 6
        assert all(not p["execution_allowed"] and not p["approval_recorded"]
                   and not p["actual_customer_consent_verified"]
                   and not p["provider_request_sent"] and p["contact_address"] is None
                   and p["destination_account"] is None
                   for p in business["workflow_proposals"])
        assert business["financial_summary"]["incremental_revenue_proven"] is False
        assert business["financial_summary"]["net_profit_verified"] is False
        assert business["financial_summary"]["true_conversion_rate_computable"] is False
        assert business["financial_summary"]["currency"] == "DEMO_CREDITS"


def test_financial_goals_contribution_and_repeat_math_no_false_claims():
    r = build_committed_growth_work_plan()
    academy, garment = r["workspaces"]
    assert academy["financial_summary"]["gross_sales"] == 25000
    assert academy["financial_summary"]["variable_cost"] == 8000
    assert academy["financial_summary"]["marketing_spend"] == 2500
    assert academy["financial_summary"]["modeled_contribution_after_marketing"] == 14500
    assert academy["financial_summary"]["contribution_shortfall"] == 5500
    assert academy["financial_summary"]["completed_orders"] == 2
    assert academy["financial_summary"]["repeat_orders"] == 1
    assert garment["financial_summary"]["gross_sales"] == 35000
    assert garment["financial_summary"]["variable_cost"] == 23500
    assert garment["financial_summary"]["marketing_spend"] == 1500
    assert garment["financial_summary"]["modeled_contribution_after_marketing"] == 10000
    assert garment["financial_summary"]["contribution_shortfall"] == 5000
    assert garment["financial_summary"]["repeat_orders"] == 1
    assert academy["causal_attribution"] == garment["causal_attribution"] == "UNPROVEN"


def test_consent_goals_and_provider_native_suppression_take_priority():
    for goal in GOALS:
        for group in build_committed_growth_work_plan(goal=goal)["workspaces"]:
            by_kind = {p["event_kind"]: p for p in group["workflow_proposals"]}
            assert by_kind["CHECKOUT_ABANDONED"]["state"] == "SUPPRESSED_PROVIDER_OWNS"
            assert sum(p["state"] == "SUPPRESSED_CONSENT_UNVERIFIED"
                       for p in group["workflow_proposals"]) == 1
            assert all(p["state"] != "SENT" for p in group["workflow_proposals"])
    retention = build_committed_growth_work_plan(goal="RETENTION")
    assert any(p["state"] == "DEFERRED_NOT_GOAL_RELEVANT"
               for group in retention["workspaces"] for p in group["workflow_proposals"])
    order = build_committed_growth_work_plan(goal="COMPLETED_ORDERS")
    assert any(p["state"] == "DEFERRED_NOT_GOAL_RELEVANT"
               for group in order["workspaces"] for p in group["workflow_proposals"])


def test_integration_contracts_are_disconnected_non_secret_no_calls():
    r = build_committed_growth_work_plan()
    contracts = {x["provider"]: x for x in r["integration_contracts"]}
    assert set(contracts) == set(PROVIDERS)
    assert all(x["connection_status"] == "DISABLED_REQUIRE_AUTHORIZATION"
               and x["credential_value"] is None and not x["can_send_or_publish"]
               and not x["webhook_receiver_active"] and not x["api_endpoint_active"]
               and x["requires_separate_tenant_authentication"]
               for x in contracts.values())
    assert contracts["SELAR"]["checkout_reminders"] == "PROVIDER_OWNED"
    assert contracts["MAILERLITE"]["requires_verifiable_consent_and_unsubscribe"]
    assert not contracts["METRICOOL"]["can_send_or_publish"]


def test_subscription_readiness_is_research_not_pricing_or_billing():
    r = build_committed_growth_work_plan()
    billing = r["subscription_research"]
    assert len(billing["plans"]) == 3
    assert all(not p["billing_live"] and not p["price_committed"]
               and not p["entitlement_active"] and not p["monetization_claim_validated"]
               and "price" not in p for p in billing["plans"])
    assert not billing["checkout_enabled"] and not billing["billing_provider_enabled"]
    assert "controlled_incremental_contribution_after_all_costs" in billing["required_business_evidence"]


@pytest.mark.parametrize("goal", [None, "REVENUE", "AUTOSEND", 15, True, ["RETENTION"]])
def test_unrecognized_goals_fail_closed(goal):
    with pytest.raises(SyntheticGrowthError, match="Unknown/unauthorized business goal"):
        build_committed_growth_work_plan(goal=goal)


def test_workspace_scoping_never_ignores_invalid_sibling_data():
    single = build_committed_growth_work_plan(workspace="academy_demo")
    assert len(single["workspaces"]) == 1
    assert single["workspaces"][0]["workspace"] == "academy_demo"
    with pytest.raises(SyntheticGrowthError, match="Unknown workspace"):
        build_committed_growth_work_plan(workspace="real_customer")
    fixture = json.loads(FIXTURE.read_bytes())
    fixture["workspaces"][1]["events"][0]["customer_phone"] = "+234111111111"
    with pytest.raises(SyntheticGrowthError, match="forbidden or missing"):
        build_growth_work_plan(json.dumps(fixture).encode(), workspace="academy_demo")


def test_cross_workspace_references_and_invalid_record_fails_closed():
    fixture = json.loads(FIXTURE.read_bytes())
    fixture["workspaces"][1]["events"][0]["journey_id"] = "DEMO-JOURNEY-EDU01"
    with pytest.raises(SyntheticGrowthError, match="Cross-workspace journey"):
        build_growth_work_plan(json.dumps(fixture).encode())


def test_source_only_modules_have_no_external_effect_imports_or_live_api_route():
    import ast
    path = ROOT / "apps/api/app/synthetic_growth_orchestration.py"
    code = path.read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "include_router(synthetic_growth_orchestration" not in main
    imports = set()
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint({"requests", "httpx", "urllib", "smtplib", "fastapi",
                              "stripe", "sqlalchemy", "psycopg", "redis", "celery",
                              "subprocess", "aiohttp"})
    assert "FIXTURE.read_bytes()" in code
    assert "DISABLED_REQUIRE_AUTHORIZATION" in code
