"""P3-04: strict offline DEMO business analytics, never production finance.

All inputs are invented test fixtures. Amounts use abstract integer DEMO
minor-units (not a real currency). Rates use integer basis points (0..10_000).
No customer data, payment provider, model inference, HTTP, database, or trusted
telemetry is read. Positive scenario values are NOT measured value or forecasts.
"""
from __future__ import annotations

from dataclasses import dataclass
from re import fullmatch
from uuid import UUID

MAX_PERIODS = 12
MAX_COUNT = 10_000
MAX_AMOUNT_MINOR = 100_000_000
MAX_EXTRA_ORDERS = 100
CURRENCY = "DEMO-UNIT"
PERIOD_PATTERN = r"DEMO-PERIOD-(20[2-9][0-9])-(0[1-9]|1[0-2])"


class DemoAnalyticsDenied(ValueError):
    """Only bounded internally consistent invented data can be analyzed."""


def _deny() -> None:
    raise DemoAnalyticsDenied("Untrusted demo analytics input rejected")


@dataclass(frozen=True)
class DemoBusinessPeriod:
    tenant_id: UUID
    period_id: str
    leads: int
    qualified_leads: int
    paid_orders: int
    refunded_orders: int
    unit_price_minor: int
    variable_cost_per_paid_order_minor: int
    marketing_cost_minor: int
    fixed_cost_minor: int
    stock_units: int
    currency: str = CURRENCY
    source: str = "SYNTHETIC_TEST_FIXTURE_ONLY"


@dataclass(frozen=True)
class DemoBusinessMetrics:
    tenant_demo_marker: str
    periods: tuple[str, ...]
    qualified_leads: int
    leads: int
    paid_orders: int
    refunded_orders: int
    retained_orders: int
    gross_sales_minor: int
    refund_value_minor: int
    net_sales_minor: int
    variable_cost_minor: int
    marketing_cost_minor: int
    fixed_cost_minor: int
    hypothetical_net_minor: int
    lead_to_paid_order_bps: int | None
    refund_rate_bps: int | None
    scenario_net_margin_bps: int | None
    metric_quality_codes: tuple[str, ...]
    insight_codes: tuple[str, ...]
    decision: str = "DENY"
    source: str = "INVENTED_LOCAL_BUSINESS_SCENARIO"
    currency: str = CURRENCY
    revenue_verified: bool = False
    customer_data_processed: bool = False
    business_value_measured: bool = False
    profitability_verified: bool = False
    live_provider_called: bool = False
    execution_authorized: bool = False


@dataclass(frozen=True)
class DemoScenarioDelta:
    tenant_demo_marker: str
    period_id: str
    extra_paid_orders: int
    extra_marketing_cost_minor: int
    optimistic_incremental_net_minor: int | None
    assumptions: tuple[str, ...]
    decision: str = "DENY"
    scope: str = "DEMO_COUNTERFACTUAL_NOT_A_FORECAST"
    result_guaranteed: bool = False
    externally_measured: bool = False
    income_generation_promised: bool = False
    real_financial_advice: bool = False
    execution_authorized: bool = False


def _marker(tenant_id: UUID) -> str:
    from hashlib import sha256
    if type(tenant_id) is not UUID:
        _deny()
    return "DEMO-TENANT-" + sha256(
        b"metaautomate:p3-04:synthetic-analytics:" + tenant_id.bytes
    ).hexdigest()[:16].upper()


def _validate(period: DemoBusinessPeriod, tenant: UUID) -> None:
    if type(period) is not DemoBusinessPeriod or type(period.tenant_id) is not UUID:
        _deny()
    if period.tenant_id != tenant:
        _deny()
    if (type(period.period_id) is not str
            or fullmatch(PERIOD_PATTERN, period.period_id) is None
            or type(period.currency) is not str or period.currency != CURRENCY
            or period.source != "SYNTHETIC_TEST_FIXTURE_ONLY"):
        _deny()
    for field in (
        "leads", "qualified_leads", "paid_orders", "refunded_orders", "stock_units",
    ):
        value = getattr(period, field)
        if type(value) is not int or not 0 <= value <= MAX_COUNT:
            _deny()
    for field in (
        "unit_price_minor", "variable_cost_per_paid_order_minor",
        "marketing_cost_minor", "fixed_cost_minor",
    ):
        value = getattr(period, field)
        if type(value) is not int or not 0 <= value <= MAX_AMOUNT_MINOR:
            _deny()
    if not (
        period.refunded_orders <= period.paid_orders
        <= period.qualified_leads <= period.leads
    ):
        _deny()
    if period.paid_orders and period.unit_price_minor == 0:
        _deny()


def _rate(part: int, whole: int) -> int | None:
    return (part * 10_000 // whole) if whole > 0 else None


def analyze_demo_business(
    tenant_id: UUID, periods: tuple[DemoBusinessPeriod, ...],
) -> DemoBusinessMetrics:
    """Deterministic bounded synthetic summary; nothing is business telemetry."""
    marker = _marker(tenant_id)
    if (type(periods) is not tuple or not 1 <= len(periods) <= MAX_PERIODS):
        _deny()
    for period in periods:
        _validate(period, tenant_id)
    ids = [p.period_id for p in periods]
    if len(ids) != len(set(ids)):
        _deny()
    ordered = tuple(sorted(periods, key=lambda p: p.period_id))
    leads = sum(p.leads for p in ordered)
    qualified = sum(p.qualified_leads for p in ordered)
    paid = sum(p.paid_orders for p in ordered)
    returned = sum(p.refunded_orders for p in ordered)
    gross = sum(p.paid_orders * p.unit_price_minor for p in ordered)
    refunds = sum(p.refunded_orders * p.unit_price_minor for p in ordered)
    net_sales = gross - refunds
    variable = sum(
        p.paid_orders * p.variable_cost_per_paid_order_minor for p in ordered
    )
    marketing = sum(p.marketing_cost_minor for p in ordered)
    fixed = sum(p.fixed_cost_minor for p in ordered)
    scenario_net = net_sales - variable - marketing - fixed
    quality = ["SYNTHETIC_INPUT_UNVERIFIED"]
    if leads == 0:
        quality.append("LEAD_CONVERSION_NOT_DEFINED")
    if paid == 0:
        quality.append("REFUND_RATE_NOT_DEFINED")
    if net_sales == 0:
        quality.append("NET_MARGIN_NOT_DEFINED")
    insight: list[str] = []
    if scenario_net < 0:
        insight.append("DEMO_SCENARIO_COSTS_EXCEED_NET_SALES")
    if paid > 0 and returned * 10_000 >= paid * 1_000:
        insight.append("DEMO_REFUND_FRACTION_AT_LEAST_10_PERCENT")
    if any(p.stock_units < p.paid_orders - p.refunded_orders for p in ordered):
        insight.append("DEMO_STOCK_BELOW_RETAINED_ORDERS")
    if leads > 0 and paid * 10_000 < leads * 500:
        insight.append("DEMO_LEAD_TO_PAID_BELOW_5_PERCENT")
    if not insight:
        insight.append("DEMO_NO_RULE_BASED_ALERTS_NOT_BUSINESS_SUCCESS")
    return DemoBusinessMetrics(
        tenant_demo_marker=marker,
        periods=tuple(p.period_id for p in ordered),
        qualified_leads=qualified, leads=leads,
        paid_orders=paid, refunded_orders=returned, retained_orders=paid-returned,
        gross_sales_minor=gross, refund_value_minor=refunds,
        net_sales_minor=net_sales, variable_cost_minor=variable,
        marketing_cost_minor=marketing, fixed_cost_minor=fixed,
        hypothetical_net_minor=scenario_net,
        lead_to_paid_order_bps=_rate(paid, leads),
        refund_rate_bps=_rate(returned, paid),
        scenario_net_margin_bps=(
            scenario_net * 10_000 // net_sales if net_sales else None
        ),
        metric_quality_codes=tuple(quality), insight_codes=tuple(insight),
    )


def simulate_demo_increment(
    tenant_id: UUID, period: DemoBusinessPeriod, *,
    extra_paid_orders: int, extra_marketing_cost_minor: int,
) -> DemoScenarioDelta:
    """Bounded BEST-CASE arithmetic, assuming no returns or additional costs.

    No value is promised. A lack of provider/customer data means this
    counterfactual is NOT a prediction, projection or verified ROI.
    """
    marker = _marker(tenant_id)
    _validate(period, tenant_id)
    if (type(extra_paid_orders) is not int
            or not 0 <= extra_paid_orders <= MAX_EXTRA_ORDERS
            or type(extra_marketing_cost_minor) is not int
            or not 0 <= extra_marketing_cost_minor <= MAX_AMOUNT_MINOR):
        _deny()
    delta = (
        extra_paid_orders * (
            period.unit_price_minor - period.variable_cost_per_paid_order_minor
        ) - extra_marketing_cost_minor
    )
    return DemoScenarioDelta(
        tenant_demo_marker=marker, period_id=period.period_id,
        extra_paid_orders=extra_paid_orders,
        extra_marketing_cost_minor=extra_marketing_cost_minor,
        optimistic_incremental_net_minor=delta,
        assumptions=(
            "ALL_EXTRA_ORDERS_PAID_AND_RETAINED_NOT_OBSERVED",
            "SAME_UNIT_PRICE_AND_VARIABLE_COST_NOT_VALIDATED",
            "NO_ADDITIONAL_FIXED_COSTS_NOT_VALIDATED",
            "NO_REAL_CUSTOMER_OR_MARKET_DEMAND_DATA",
        ),
    )


def demo_business_fixture(tenant_id: UUID) -> tuple[DemoBusinessPeriod, ...]:
    """Fixed invented examples, not imported business records."""
    _marker(tenant_id)
    return (
        DemoBusinessPeriod(
            tenant_id, "DEMO-PERIOD-2026-01",
            leads=160, qualified_leads=50, paid_orders=20, refunded_orders=2,
            unit_price_minor=12_500, variable_cost_per_paid_order_minor=7_000,
            marketing_cost_minor=30_000, fixed_cost_minor=25_000,
            stock_units=32,
        ),
        DemoBusinessPeriod(
            tenant_id, "DEMO-PERIOD-2026-02",
            leads=190, qualified_leads=64, paid_orders=25, refunded_orders=1,
            unit_price_minor=12_500, variable_cost_per_paid_order_minor=7_000,
            marketing_cost_minor=40_000, fixed_cost_minor=25_000,
            stock_units=28,
        ),
    )
