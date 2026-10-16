"""P2-03j orchestration: goal alignment, economic integrity, safe source-only gates."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_orchestrator import (  # noqa: E402
    CONTRACT_PATH, SCENARIOS_PATH, GROWTH_FIXTURE, MAX_BYTES,
    GrowthOrchestrationError, parse_provider_contract, parse_scenarios,
    strict_json, orchestrate, read_committed_growth_orchestration,
)
from app.synthetic_growth_autopilot import parse_growth_fixture


def docs():
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in (GROWTH_FIXTURE, SCENARIOS_PATH, CONTRACT_PATH)]


def raw(obj):
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def preview(source=None, scenarios=None, contract=None, workspace="all"):
    defaults = docs()
    a, b, c = [given if given is not None else default
               for given, default in zip((source, scenarios, contract), defaults)]
    return orchestrate(raw(a), raw(b), raw(c), workspace=workspace)


def denied(change, document_index, expected):
    items = docs()
    change(items[document_index])
    with pytest.raises((GrowthOrchestrationError, ValueError), match=expected):
        preview(*items)


def test_goal_driven_report_is_deterministic_and_client_activation_is_false():
    full = read_committed_growth_orchestration()
    assert full == read_committed_growth_orchestration()
    assert full["schema_version"] == 1
    assert full["engineering_milestone"] == "P2-03j"
    assert full["classification"] == "SYNTHETIC_DEMO_ONLY"
    assert full["currency"] == "DEMO_CREDITS"
    assert full["mode"] == "READ_ONLY_GOAL_ORCHESTRATION"
    assert full["integration_mode"] == "CONTRACT_ONLY"
    assert full["operational_status"] == "NO_GO"
    assert len(full["evidence_sha256"]) == 64
    assert len(full["providers"]) == 5
    assert all(p["connection_state"] == "CONTRACT_ONLY" and
               p["external_execution_enabled"] is False for p in full["providers"])
    assert [w["workspace"] for w in full["workspaces"]] == [
        "academy_demo", "bespoke_demo"
    ]
    for field in ("live_customer_data_used", "live_provider_credentials_used",
                  "real_customer_subscriptions_charged", "external_requests_made",
                  "customer_activation_authorized", "tenant_isolation_verified",
                  "durable_idempotency_verified", "revenue_incrementality_verified",
                  "live_automation_available"):
        assert full[field] is False


def test_education_goal_enforces_economic_costs_and_protects_conversion_denominator():
    academy = read_committed_growth_orchestration(workspace="academy_demo")
    assert len(academy["workspaces"]) == 1
    group = academy["workspaces"][0]
    assert group["workspace"] == "academy_demo"
    assert group["goal"] == {
        "metric": "CONTRIBUTION_AFTER_MARKETING_AND_WORKFLOW_COSTS",
        "target": 20000, "current": 13900,
        "shortfall": 6100, "progress_basis_points": 6950
    }
    finance = group["measurement"]
    assert finance["gross_sales_demo_credits"] == 25000
    assert finance["variable_cost_demo_credits"] == 8000
    assert finance["marketing_spend_demo_credits"] == 2500
    assert finance["workflow_cost_demo_credits"] == 600
    assert finance["contribution_after_marketing_and_workflow_costs_demo_credits"] == 13900
    assert finance["completed_order_records"] == 2
    assert finance["unique_ordering_journeys"] == 1
    assert finance["repeat_order_records"] == 1
    assert finance["measured_sessions"] == 40
    assert finance["qualified_enquiries"] == 7
    assert finance["journey_conversion_basis_points"] == 250
    assert finance["measurement_status"] == "SYNTHETIC_SCENARIO_NON_CAUSAL"
    assert finance["causal_incremental_revenue_proven"] is False
    assert finance["verified_client_revenue"] is None
    assert finance["verified_net_profit"] is None
    assert finance["real_conversion_rate_verified"] is False


def test_apparel_goal_focuses_repeats_not_false_attribution():
    group = read_committed_growth_orchestration(workspace="bespoke_demo")["workspaces"][0]
    assert group["goal"] == {
        "metric": "REPEAT_ORDER_COUNT", "target": 3, "current": 1,
        "shortfall": 2, "progress_basis_points": 3333
    }
    finance = group["measurement"]
    assert finance["gross_sales_demo_credits"] == 35000
    assert finance["variable_cost_demo_credits"] == 23500
    assert finance["marketing_spend_demo_credits"] == 1500
    assert finance["workflow_cost_demo_credits"] == 500
    assert finance["contribution_after_marketing_and_workflow_costs_demo_credits"] == 9500
    assert finance["unique_ordering_journeys"] == 1
    assert finance["journey_conversion_basis_points"] == 400
    assert finance["real_conversion_rate_verified"] is False


def test_each_workspace_proposes_drafts_suppresses_checkout_and_no_consent():
    for group in read_committed_growth_orchestration()["workspaces"]:
        automation = group["automation"]
        assert len(automation["proposals"]) == 6
        assert automation["proposals_for_review"] == 4
        assert automation["provider_owned_suppressions"] == 1
        assert automation["unconsented_suppressions"] == 1
        assert len({p["idempotency_preview"] for p in automation["proposals"]}) == 6
        assert len(automation["replay_previews"]) == 1
        assert automation["replay_previews"][0]["decision"] == "DUPLICATE_SOURCE_EVENT_SUPPRESSED"
        assert automation["replay_previews"][0]["durably_enforced"] is False
        assert automation["durable_replay_protection_enabled"] is False
        for field in ("messages_sent", "social_posts_published", "external_actions",
                      "paid_orders_created"):
            assert automation[field] == 0
        actions = automation["proposals"]
        checkout = [p for p in actions if p["source_event_type"] == "CHECKOUT_ABANDONED"]
        assert len(checkout) == 1
        assert checkout[0]["provider_contract"] == "SELAR"
        assert checkout[0]["review_state"] == "SUPPRESSED_PROVIDER_OWNS"
        assert checkout[0]["reason"] == "NATIVE_PROVIDER_RECOVERY"
        opted_out = [p for p in actions if p["review_state"] ==
                     "SUPPRESSED_NO_MARKETING_CONSENT"]
        assert len(opted_out) == 1
        assert opted_out[0]["reason"] == "NO_VERIFIED_CONSENT"
        for p in actions:
            assert p["workspace"] == group["workspace"]
            assert p["approval_granted"] is False
            assert p["dispatch_enabled"] is False
            assert p["customer_message_sent"] is False
            assert p["provider_connected"] is False
            assert p["event_consented_in_production"] is False
            assert p["goal_relevance"] in ("HIGH", "STANDARD")
        assert automation["replay_previews"][0]["idempotency_preview"] in {
            p["idempotency_preview"] for p in actions
        }


def test_replay_idempotency_is_only_a_pure_preview_not_a_durable_outbound_guarantee():
    first = read_committed_growth_orchestration()
    second = read_committed_growth_orchestration()
    for group, another in zip(first["workspaces"], second["workspaces"]):
        assert group["automation"] == another["automation"]
        assert group["automation"]["durable_replay_protection_enabled"] is False
    assert first["durable_idempotency_verified"] is False


def test_research_tiers_have_no_active_entitlements_prices_trials_or_billing():
    full = read_committed_growth_orchestration()
    assert {w["subscription"]["research_tier"] for w in full["workspaces"]} == {
        "STARTER_RESEARCH", "GROWTH_RESEARCH"
    }
    for group in full["workspaces"]:
        s = group["subscription"]
        assert s["readiness"] == "NOT_LAUNCH_READY"
        assert len(s["required_gates"]) == 6
        assert "BILLING_ENTITLEMENTS_AND_COMMERCIAL_APPROVAL" in s["required_gates"]
        assert s["price_offered"] is None
        assert s["real_subscription_revenue"] is None
        assert s["billing_active"] is False
        assert s["entitlements_active"] is False
        assert s["trial_active"] is False


def test_workspace_filter_validates_all_input_before_selecting():
    selected = read_committed_growth_orchestration(workspace="academy_demo")
    assert selected["workspaces"][0]["workspace"] == "academy_demo"
    assert selected["evidence_sha256"] != read_committed_growth_orchestration()["evidence_sha256"]
    with pytest.raises(GrowthOrchestrationError, match="Invalid requested workspace"):
        read_committed_growth_orchestration(workspace="unknown")
    with pytest.raises(GrowthOrchestrationError, match="Invalid requested workspace"):
        read_committed_growth_orchestration(workspace=0)
    c = docs()
    c[1]["workspaces"][1]["customer_email"] = "person@example.com"
    with pytest.raises(GrowthOrchestrationError, match="unexpected or missing fields"):
        preview(*c, workspace="academy_demo")


def test_cross_workspace_replays_and_object_references_are_denied():
    denied(lambda d: d["workspaces"][1]["replayed_event_ids"].append(
        "DEMO-EVENT-EDU01"), 1, "Invalid or cross-workspace replay event")
    denied(lambda d: d["workspaces"][0]["replayed_event_ids"].append(
        "DEMO-EVENT-EDU01"), 1, "Invalid or cross-workspace replay event")
    denied(lambda d: d["workspaces"][1].update(workspace="academy_demo"),
           1, "Duplicate/unknown business workspace")
    denied(lambda d: d["workspaces"][1]["goal"].update(
        metric="CONTRIBUTION_AFTER_MARKETING_AND_WORKFLOW_COSTS"),
           1, "Goal incompatible with workspace")


@pytest.mark.parametrize("price", [True, False, -1, 1.5, None, "20000", 100_000_001])
def test_invalid_target_values_denied(price):
    denied(lambda d: d["workspaces"][0]["goal"].update(target=price), 1,
           "Float/non-finite" if type(price) is float else "invalid integer")


@pytest.mark.parametrize("spend", [True, -1, 1.3, "10", 1_000_001])
def test_invalid_workflow_operating_cost_denied(spend):
    denied(lambda d: d["workspaces"][1].update(workflow_cost_demo_credits=spend),
           1, "Float/non-finite" if type(spend) is float else "invalid integer")


def test_goal_events_funnel_count_and_plan_validation_fail_closed():
    denied(lambda d: d["workspaces"][0]["goal"].update(
        priority_event_types=["LEAD_OPT_IN", "LEAD_OPT_IN"]), 1,
        "Invalid goal trigger mapping")
    denied(lambda d: d["workspaces"][1]["goal"].update(
        priority_event_types=["LEAD_OPT_IN", "CHECKOUT_ABANDONED"]), 1,
        "Invalid goal trigger mapping")
    denied(lambda d: d["workspaces"][0]["funnel"].update(measured_sessions=0),
           1, "invalid integer")
    denied(lambda d: d["workspaces"][1]["funnel"].update(qualified_enquiries=0),
           1, "Enquiries below buyer count")
    denied(lambda d: d["workspaces"][0]["funnel"].update(
        qualified_enquiries=100), 1, "invalid integer")
    denied(lambda d: d["workspaces"][0].update(
        subscription_research_tier="PAID_ACTIVE"), 1, "Unknown pricing research tier")
    denied(lambda d: d["workspaces"][0].update(
        monthly_subscription_usd=29), 1, "unexpected or missing fields")
    denied(lambda d: d["workspaces"][0]["goal"].update(
        guarantee_revenue=True), 1, "unexpected or missing fields")
    denied(lambda d: d["workspaces"][0]["funnel"].update(
        customer_phone="123456"), 1, "unexpected or missing fields")


def test_provider_contract_cannot_be_activated_or_extended_with_credentials():
    denied(lambda d: d["providers"][0].update(connection_state="CONNECTED"),
           2, "Live provider capability prohibited")
    denied(lambda d: d["providers"][1].update(credential_use_enabled=True),
           2, "Live provider capability prohibited")
    denied(lambda d: d["providers"][2].update(external_execution_enabled=True),
           2, "Live provider capability prohibited")
    denied(lambda d: d["safety_policy"].update(billing_enabled=True),
           2, "Unsafe integration policy")
    denied(lambda d: d["safety_policy"].update(
        durable_replay_protection_enabled=True), 2, "Unsafe integration policy")
    denied(lambda d: d["providers"][0].update(
        provider_owns_checkout_recovery=False), 2, "Misdeclared provider role")
    denied(lambda d: d["providers"][0].update(
        password="secret"), 2, "unexpected or missing fields")
    denied(lambda d: d["providers"][1].update(provider_id="SELAR"),
           2, "Unexpected or duplicate provider")
    denied(lambda d: d.update(execution_mode="PRODUCTION"),
           2, "Operational provider integration is not authorized")
    denied(lambda d: d["providers"][4].update(capability="CHARGE_CUSTOMER"),
           2, "Misdeclared provider role")
    denied(lambda d: d["providers"].append(deepcopy(d["providers"][0])),
           2, "Invalid integration list")


def test_base_growth_contract_must_fail_closed_before_orchestration():
    denied(lambda d: d["workspaces"][0]["events"][0].update(
        email="person@example.com"), 0, "forbidden or missing")
    denied(lambda d: d["workspaces"][0]["events"][0].update(
        consent_status="ASSUMED"), 0, "Consent status")
    denied(lambda d: d["workspaces"][1]["orders"][0].update(
        product_id="DEMO-COURSE-ALPHA"), 0, "Cross-workspace/unknown")
    denied(lambda d: d.update(currency="USD"), 0,
           "Real business records or currency")


def test_invalid_json_bytes_duplicate_keys_and_floats_denied():
    for input_bytes in (b"", b"\xff", b"\x00", b"[]", b" " * (MAX_BYTES + 1),
                        b'{"schema_version": NaN}', b'{"schema_version": 1.5}',
                        b'{"schema_version": Infinity}'):
        with pytest.raises(GrowthOrchestrationError):
            strict_json(input_bytes)
    with pytest.raises(GrowthOrchestrationError, match="Duplicate JSON field"):
        strict_json(b'{"schema_version":1,"schema_version":1}')
    with pytest.raises(GrowthOrchestrationError, match="Root must be an object"):
        strict_json(b'["a", "b"]')


def test_no_runtime_provider_connector_router_or_outbound_sdk():
    src = (ROOT / "apps/api/app/synthetic_growth_orchestrator.py").read_text()
    root_main = (ROOT / "apps/api/app/main.py").read_text()
    for forbidden in ("requests.", "httpx.", "smtplib.", "subprocess.",
                      "stripe.", "redis.", "psycopg.", "os.environ[",
                      "urllib.request", "getenv(", "eval(", "exec("):
        assert forbidden not in src
    assert "synthetic_growth_orchestrator_router" not in root_main
    assert "include_router(synthetic_growth_orchestrator" not in root_main
    assert "read_committed_growth_orchestration" in src
    assert "GROWTH_FIXTURE.read_bytes()" in src
    assert "billing_active" in src
    assert "durable_replay_protection_enabled" in src
