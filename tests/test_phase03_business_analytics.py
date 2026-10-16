"""P3-04: bounded synthetic analytics, business metrics and scenario tests."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from app.phase03_business_analytics import (
    DemoAnalyticsDenied, DemoBusinessPeriod, CURRENCY,
    MAX_COUNT, MAX_AMOUNT_MINOR, MAX_PERIODS,
    analyze_demo_business, simulate_demo_increment, demo_business_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"
MANIFEST = ROOT / "contracts/intelligent/v1/business_analytics.json"


def row(tenant=None, **changes):
    tenant = uuid4() if tenant is None else tenant
    base = DemoBusinessPeriod(
        tenant_id=tenant, period_id="DEMO-PERIOD-2026-04",
        leads=100, qualified_leads=20, paid_orders=4,
        refunded_orders=1, unit_price_minor=10_000,
        variable_cost_per_paid_order_minor=9_000,
        marketing_cost_minor=10_000, fixed_cost_minor=2_000,
        stock_units=2,
    )
    return replace(base, **changes)


def test_known_two_period_metrics_and_no_real_business_value():
    tenant = uuid4()
    periods = demo_business_fixture(tenant)
    m = analyze_demo_business(tenant, periods)
    assert m.leads == 350
    assert m.qualified_leads == 114
    assert m.paid_orders == 45
    assert m.refunded_orders == 3
    assert m.retained_orders == 42
    assert m.gross_sales_minor == 562_500
    assert m.refund_value_minor == 37_500
    assert m.net_sales_minor == 525_000
    assert m.variable_cost_minor == 315_000
    assert m.marketing_cost_minor == 70_000
    assert m.fixed_cost_minor == 50_000
    assert m.hypothetical_net_minor == 90_000
    assert m.lead_to_paid_order_bps == 1_285
    assert m.refund_rate_bps == 666
    assert m.scenario_net_margin_bps == 1_714
    assert m.insight_codes == ("DEMO_NO_RULE_BASED_ALERTS_NOT_BUSINESS_SUCCESS",)
    assert m.metric_quality_codes == ("SYNTHETIC_INPUT_UNVERIFIED",)
    assert m.decision == "DENY"
    assert m.source == "INVENTED_LOCAL_BUSINESS_SCENARIO"
    assert m.currency == CURRENCY
    assert not m.revenue_verified
    assert not m.business_value_measured
    assert not m.customer_data_processed
    assert not m.profitability_verified
    assert not m.live_provider_called
    assert not m.execution_authorized


def test_order_independent_periods_and_ordered_labels():
    tenant = uuid4()
    seq = demo_business_fixture(tenant)
    assert analyze_demo_business(tenant, seq) == analyze_demo_business(
        tenant, tuple(reversed(seq))
    )


def test_duplicate_periods_denied_even_if_data_differs():
    tenant = uuid4()
    p = row(tenant)
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(tenant, (p, replace(p, leads=110)))


def test_foreign_tenant_cannot_mix_records():
    a = uuid4()
    b = uuid4()
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(a, (row(b),))
    with pytest.raises(DemoAnalyticsDenied):
        simulate_demo_increment(a, row(b), extra_paid_orders=1,
                                extra_marketing_cost_minor=0)


@pytest.mark.parametrize("bad", [[], (), None, 5, True, "a"])
def test_invalid_period_collection_denied(bad):
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(uuid4(), bad)


def test_period_count_is_bounded():
    tenant = uuid4()
    records = tuple(
        replace(row(tenant), period_id=f"DEMO-PERIOD-2026-{i:02}")
        for i in range(1, MAX_PERIODS+1)
    )
    analyze_demo_business(tenant, records)
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(tenant, records + (
            replace(row(tenant), period_id="DEMO-PERIOD-2027-01"),
        ))


@pytest.mark.parametrize("label", [
    "2026-04", "DEMO-PERIOD-2026-00", "DEMO-PERIOD-2026-13",
    "DEMO-PERIOD-2026-4", "DEMO-PERIOD-1999-04",
    "DEMO-PERIOD-2026-04\n", None, 1, True,
])
def test_untrusted_date_fields_denied(label):
    t = uuid4()
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(t, (row(t, period_id=label),))


@pytest.mark.parametrize("field,value", [
    ("leads", -1), ("leads", True), ("leads", "100"), ("leads", 1.5),
    ("qualified_leads", -2), ("paid_orders", MAX_COUNT+1),
    ("refunded_orders", None), ("stock_units", -1),
    ("unit_price_minor", -1), ("unit_price_minor", True),
    ("unit_price_minor", 0.5), ("marketing_cost_minor", MAX_AMOUNT_MINOR+1),
    ("fixed_cost_minor", "100"), ("variable_cost_per_paid_order_minor", -1),
    ("currency", "NGN"), ("currency", None),
    ("source", "PRODUCTION_FINANCE"), ("source", True),
])
def test_values_must_be_integer_demo_only_and_bounded(field, value):
    t = uuid4()
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(t, (row(t, **{field: value}),))


@pytest.mark.parametrize("fields", [
    {"qualified_leads": 101},
    {"paid_orders": 21},
    {"refunded_orders": 5},
    {"paid_orders": 4, "unit_price_minor": 0},
    {"paid_orders": 4, "qualified_leads": 0},
])
def test_inconsistent_funnel_or_free_sales_denied(fields):
    t = uuid4()
    with pytest.raises(DemoAnalyticsDenied):
        analyze_demo_business(t, (row(t, **fields),))


def test_missing_denominators_report_null_not_fabricated_values():
    t = uuid4()
    r = row(t, leads=0, qualified_leads=0, paid_orders=0,
            refunded_orders=0, unit_price_minor=0,
            marketing_cost_minor=0, fixed_cost_minor=0)
    m = analyze_demo_business(t, (r,))
    assert m.lead_to_paid_order_bps is None
    assert m.refund_rate_bps is None
    assert m.scenario_net_margin_bps is None
    assert "LEAD_CONVERSION_NOT_DEFINED" in m.metric_quality_codes
    assert "REFUND_RATE_NOT_DEFINED" in m.metric_quality_codes
    assert "NET_MARGIN_NOT_DEFINED" in m.metric_quality_codes
    assert m.hypothetical_net_minor == 0
    assert m.decision == "DENY"


def test_negative_scenario_alerts_are_hypothetical():
    t = uuid4()
    report = analyze_demo_business(t, (row(t),))
    assert report.hypothetical_net_minor == -18_000
    assert "DEMO_SCENARIO_COSTS_EXCEED_NET_SALES" in report.insight_codes
    assert "DEMO_REFUND_FRACTION_AT_LEAST_10_PERCENT" in report.insight_codes
    assert "DEMO_STOCK_BELOW_RETAINED_ORDERS" in report.insight_codes
    assert "DEMO_LEAD_TO_PAID_BELOW_5_PERCENT" in report.insight_codes
    assert not report.business_value_measured


def test_counterfactual_is_explicitly_optimistic_not_income_promise():
    t = uuid4()
    period = demo_business_fixture(t)[-1]
    s = simulate_demo_increment(t, period, extra_paid_orders=5,
                                extra_marketing_cost_minor=10_000)
    assert s.optimistic_incremental_net_minor == 17_500
    assert s.extra_paid_orders == 5
    assert len(s.assumptions) == 4
    assert s.scope == "DEMO_COUNTERFACTUAL_NOT_A_FORECAST"
    assert s.decision == "DENY"
    assert not s.result_guaranteed
    assert not s.externally_measured
    assert not s.income_generation_promised
    assert not s.execution_authorized
    assert not s.real_financial_advice


def test_negative_increment_counterfactual_keeps_signed_integer():
    t = uuid4()
    s = simulate_demo_increment(t, row(t), extra_paid_orders=0,
                                extra_marketing_cost_minor=2_000)
    assert s.optimistic_incremental_net_minor == -2_000


@pytest.mark.parametrize("orders,cost", [
    (-1, 0), (101, 0), (True, 0), (1.5, 0),
    (1, -1), (1, True), (1, "1000"), (1, MAX_AMOUNT_MINOR+1),
])
def test_counterfactual_bounds_reject_invalid_or_overflow_inputs(orders, cost):
    t = uuid4()
    with pytest.raises(DemoAnalyticsDenied):
        simulate_demo_increment(t, row(t), extra_paid_orders=orders,
                                extra_marketing_cost_minor=cost)


def test_invalid_tenant_types_denied():
    r = row()
    for invalid in (None, "tenant", True, 33):
        with pytest.raises(DemoAnalyticsDenied):
            analyze_demo_business(invalid, (r,))


def test_source_is_not_mutable_grant():
    t = uuid4()
    r = analyze_demo_business(t, (row(t),))
    with pytest.raises(FrozenInstanceError):
        r.execution_authorized = True


def test_contract_is_versioned_and_forbids_real_value():
    m = json.loads(MANIFEST.read_text())
    assert m["milestone"] == "P3-04"
    assert m["scope"] == "SYNTHETIC_BUSINESS_ANALYTICS_ONLY"
    assert m["decision"] == "DENY"
    assert m["inputs"]["units"] == "DEMO-UNIT"
    for key in ("real_revenue_measured", "verified_business_roi_available",
                "customer_data_used", "live_provider_read_performed",
                "ai_model_called", "real_income_guarantee",
                "production_dashboard_enabled", "live_execution_authorized"):
        assert m[key] is False
    assert m["phase01_verified"] == 3
    assert m["phase02_operational_go"] is False


@pytest.mark.parametrize("cmd", [["business-demo"], ["scenario-demo"],
                                  ["scenario-demo", "--extra-orders", "0"]])
def test_developer_cli_output_never_claims_real_telemetry(cmd):
    p = subprocess.run(
        [sys.executable, str(CLI), *cmd], capture_output=True,
        text=True, check=False, timeout=15,
    )
    assert p.returncode == 0, p.stderr
    m = json.loads(p.stdout)
    assert m["decision"] == "DENY"
    if cmd[0] == "business-demo":
        assert m["hypothetical_net_minor"] == 90_000
        assert m["lead_to_paid_order_bps"] == 1_285
        assert not m["business_value_measured"]
        assert not m["customer_data_processed"]
    else:
        assert m["scope"] == "DEMO_COUNTERFACTUAL_NOT_A_FORECAST"
        assert not m["income_generation_promised"]
        assert not m["execution_authorized"]


@pytest.mark.parametrize("cmd", [
    ["business-demo", "--provider", "actual"],
    ["scenario-demo", "--extra-orders", "101"],
    ["scenario-demo", "--extra-marketing-minor", "-1"],
    ["scenario-demo", "--execute"],
    ["scenario-demo", "--extra-orders", "true"],
])
def test_developer_cli_rejects_live_and_malformed_args(cmd):
    p = subprocess.run(
        [sys.executable, str(CLI), *cmd], capture_output=True,
        text=True, check=False, timeout=15,
    )
    assert p.returncode != 0
    assert not p.stdout


def test_unrouted_pure_analytics_has_no_external_provider_or_inference():
    app = (ROOT / "apps/api/app/main.py").read_text()
    code = (ROOT / "apps/api/app/phase03_business_analytics.py").read_text()
    assert "phase03_business_analytics" not in app
    for forbidden in ("APIRouter(", "requests.", "httpx", "psycopg",
                      "urllib.request", "urlopen(", "socket.socket(",
                      "subprocess.", "redis.", "openai.", "google.generativeai"):
        assert forbidden not in code
