"""P2-03h synthetic Growth Autopilot: fail closed, deduplicate, never transmit."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import (  # noqa: E402
    FIXTURE, MAX_BYTES, SyntheticGrowthError, parse_growth_fixture,
    read_committed_growth_demo, render_growth_preview,
)


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def data(obj):
    return json.dumps(obj, sort_keys=True).encode("utf-8")


def rejected(change, match):
    doc = fixture()
    change(doc)
    with pytest.raises(SyntheticGrowthError, match=match):
        render_growth_preview(data(doc))


def test_both_businesses_simulate_growth_without_activating_real_workflows():
    report = read_committed_growth_demo()
    assert report["operational_status"] == "NO_GO"
    assert report["classification"] == "SYNTHETIC_DEMO_ONLY"
    assert report["currency"] == "DEMO_CREDITS"
    assert report["mode"] == "GROWTH_AUTOPILOT_READ_ONLY_SIMULATION"
    assert [x["workspace"] for x in report["businesses"]] == [
        "academy_demo", "bespoke_demo"
    ]
    academy, bespoke = report["businesses"]
    assert academy["financial_summary"] == {
        "completed_fictional_orders": 2,
        "gross_sales_demo_credits": 25000,
        "variable_cost_demo_credits": 8000,
        "contribution_before_marketing_demo_credits": 17000,
        "marketing_spend_demo_credits": 2500,
        "modeled_contribution_after_spend_demo_credits": 14500,
        "goal_shortfall_demo_credits": 5500,
        "fictional_repeat_orders": 1,
        "sales_attributed_causally_to_automation": 0,
    }
    assert bespoke["financial_summary"] == {
        "completed_fictional_orders": 2,
        "gross_sales_demo_credits": 35000,
        "variable_cost_demo_credits": 23500,
        "contribution_before_marketing_demo_credits": 11500,
        "marketing_spend_demo_credits": 1500,
        "modeled_contribution_after_spend_demo_credits": 10000,
        "goal_shortfall_demo_credits": 5000,
        "fictional_repeat_orders": 1,
        "sales_attributed_causally_to_automation": 0,
    }
    for group in report["businesses"]:
        assert group["totals"] == {
            "triggers_considered": 6, "drafts_requiring_review": 4,
            "suppressed_by_provider": 1, "suppressed_by_consent": 1,
            "messages_delivered": 0, "payments_processed": 0, "external_actions": 0,
        }
        assert group["automation_mode"] == "LOCAL_PROPOSALS_ONLY"
        assert group["operational_status"] == "NO_GO"
        assert len({x["idempotency_preview"] for x in group["automation_proposals"]}) == 6
        assert all(x["contact_details"] is None and x["human_approval_required"] is True
                   and x["customer_message_sent"] is False
                   and x["provider_operation_performed"] is False
                   and x["payment_taken"] is False and x["real_order_created"] is False
                   for x in group["automation_proposals"])
    for flag in ("real_customer_data_used", "real_sales_records_used",
                 "production_credentials_used", "actual_marketing_messages_sent",
                 "social_posts_published", "transactions_processed",
                 "real_customer_subscriptions_charged", "provider_api_calls_made",
                 "database_writes_performed", "execution_available",
                 "causal_revenue_impact_proven", "profitability_claim_proven",
                 "subscriptions_active"):
        assert report[flag] is False


def test_selar_recovery_is_not_duplicated_or_used_as_marketing_consent():
    report = read_committed_growth_demo()
    for workspace in report["businesses"]:
        actions = workspace["automation_proposals"]
        recoveries = [x for x in actions if x["source_event"] == "CHECKOUT_ABANDONED"]
        assert len(recoveries) == 1
        assert recoveries[0]["state"] == "SUPPRESSED_PROVIDER_OWNS"
        assert recoveries[0]["recipe"] == "SELAR_NATIVE_REMINDER_OWNS_RECOVERY"
        assert any(x["state"] == "SUPPRESSED_NO_MARKETING_CONSENT" for x in actions)
        assert all(x["state"] != "SENT" for x in actions)
        assert all(x["state"] not in ("SCHEDULED", "POSTED") for x in actions)


def test_deterministic_and_workspace_filter_does_not_hide_invalid_other_workspace():
    raw = FIXTURE.read_bytes()
    full = read_committed_growth_demo()
    assert read_committed_growth_demo() == full
    assert FIXTURE.read_bytes() == raw
    academy = read_committed_growth_demo(workspace="academy_demo")
    assert len(academy["businesses"]) == 1
    assert academy["businesses"][0]["workspace"] == "academy_demo"
    assert academy["evidence_sha256"] != full["evidence_sha256"]
    with pytest.raises(SyntheticGrowthError, match="Unknown synthetic workspace"):
        read_committed_growth_demo(workspace="third_party")
    d = fixture()
    d["workspaces"][1]["events"][0]["contact_email"] = "person@example.com"
    with pytest.raises(SyntheticGrowthError, match="forbidden or missing"):
        render_growth_preview(data(d), workspace="academy_demo")


def test_no_cross_workspace_orders_events_or_customer_journeys():
    rejected(lambda d: d["workspaces"][1]["orders"][0].update(
        product_id="DEMO-COURSE-ALPHA"), "Cross-workspace/unknown")
    rejected(lambda d: d["workspaces"][1]["events"][0].update(
        product_id="DEMO-COURSE-ALPHA"), "Cross-workspace/unknown")
    rejected(lambda d: d["workspaces"][1]["events"][0].update(
        journey_id="DEMO-JOURNEY-EDU01"), "Cross-workspace journey")
    rejected(lambda d: d["workspaces"][1]["events"][0].update(
        event_id="DEMO-EVENT-EDU01"), "invalid/duplicate ID")
    rejected(lambda d: d["workspaces"][1]["orders"][0].update(
        order_id="DEMO-ORDER-EDU01"), "invalid/duplicate ID")
    rejected(lambda d: d["workspaces"][1].update(workspace="academy_demo"),
             "Unknown or duplicated demo workspace")


def test_fictitious_order_and_repeat_event_must_match_and_be_justified():
    rejected(lambda d: d["workspaces"][0]["events"][3].update(
        order_ref="DEMO-ORDER-EDU02"), "Cross-product or mismatched")
    rejected(lambda d: d["workspaces"][0]["events"][2].update(
        order_ref=None), "Completed action requires")
    rejected(lambda d: d["workspaces"][0]["events"][1].update(
        order_ref="DEMO-ORDER-EDU01"), "Lead or cart event")
    rejected(lambda d: d["workspaces"][0]["events"][3].update(
        event_type="GARMENT_DELIVERED"), "Trigger incompatible")
    rejected(lambda d: d["workspaces"][1]["events"][3].update(
        event_type="LEARNING_COMPLETED"), "Trigger incompatible")
    rejected(lambda d: d["workspaces"][0]["events"][4].update(
        event_type="LEAD_OPT_IN", order_ref=None), "lacks purchase trigger")


@pytest.mark.parametrize("amount", [True, False, -1, 1.4, None, "100"])
def test_reject_bad_prices(amount):
    rejected(lambda d: d["workspaces"][0]["products"][0].update(
        unit_price_demo_credits=amount), "invalid integer")


@pytest.mark.parametrize("amount", [True, False, -1, 1.4, None, "1", 101])
def test_reject_bad_units(amount):
    rejected(lambda d: d["workspaces"][0]["orders"][0].update(units=amount),
             "invalid integer")


def test_reject_negative_unit_contribution_goal_or_misleading_attribution():
    rejected(lambda d: d["workspaces"][0]["products"][0].update(
        variable_cost_demo_credits=20000), "Negative synthetic unit contribution")
    rejected(lambda d: d["workspaces"][0].update(
        goal_target_demo_credits=-1), "invalid integer")
    rejected(lambda d: d["workspaces"][0]["orders"][0].update(
        attribution="AUTOMATION_CAUSED_SALE"), "deterministic marketing attribution")


def test_reject_unknown_fields_personal_data_and_real_money():
    rejected(lambda d: d["workspaces"][1]["events"][0].update(
        phone="+234123456789"), "forbidden or missing")
    rejected(lambda d: d["workspaces"][0]["orders"][0].update(
        email="person@example.com"), "forbidden or missing")
    rejected(lambda d: d.update(currency="NGN"), "Real business records or currency")
    rejected(lambda d: d.update(classification="ACTUAL_CUSTOMERS"), "Real business records")
    rejected(lambda d: d["workspaces"][0]["products"][0].update(
        label="Artificial Intelligence Course"), "Real product names")
    rejected(lambda d: d["workspaces"][0]["events"][0].update(
        consent_status="ASSUMED_CONSENT"), "Consent status")
    rejected(lambda d: d["workspaces"][1]["events"][0].update(
        event_type="SEND_WHATSAPP"), "Unknown automation trigger")


def test_reject_duplicate_json_fields_nonfinite_floats_nuls_and_size():
    duplicated = FIXTURE.read_text(encoding="utf-8").replace(
        '"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1)
    with pytest.raises(SyntheticGrowthError, match="Duplicate JSON field"):
        parse_growth_fixture(duplicated.encode())
    for bad in (b"", b"\xff", b"\x00", b"[]" , b" "*(MAX_BYTES+1),
                b'{"schema_version": NaN}', b'{"schema_version": 1.4}',
                b'{"schema_version": Infinity}'):
        with pytest.raises(SyntheticGrowthError):
            render_growth_preview(bad)


def test_proposed_is_not_automatic_real_execution_or_tenant_authentication():
    module = (ROOT / "apps/api/app/synthetic_growth_autopilot.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "include_router(synthetic_growth_autopilot" not in main
    assert "synthetic_growth_autopilot_router" not in main
    import ast
    imports = set()
    for node in ast.walk(ast.parse(module)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint({
        "requests", "httpx", "urllib", "redis", "sqlalchemy", "psycopg",
        "smtplib", "fastapi", "subprocess", "stripe", "celery", "aiohttp",
    })
    assert "FIXTURE.read_bytes()" in module
    assert "SUPPRESSED_PROVIDER_OWNS" in module
    assert "real_customer_subscriptions_charged" in module
