"""P2-03m — Business Value Intelligence, offline and source-only.

Measures bounded illustrative 30-day scenarios with auditable arithmetic.
Produces descriptive, non-causal comparisons and evidence-needed opportunities.
No real business data, subscriber records, external APIs, hosted analytics or
automated actions. Never mistake modeled contribution for net profit or ROI.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .synthetic_growth_autopilot import (
    FIXTURE, SyntheticGrowthError, parse_growth_fixture,
)
from .synthetic_growth_orchestration import (
    GOALS, NON_OPERATIONAL, build_growth_work_plan,
)

SCENARIOS = (Path(__file__).resolve().parents[3]
             / "contracts/domains/v1/fixtures/synthetic_growth_value.v1.json")
MAX_BYTES = 24_576
MAX_AMOUNT = 100_000_000
MAX_ORDERS = 100_000
MAX_STAFF_MINUTES = 1_000_000
COST_FIELDS = ("variable_cost", "marketing_spend", "processing_fees",
               "fulfillment_cost", "software_cost", "refunds")
PERIOD_FIELDS = set(COST_FIELDS) | {
    "period_id", "days", "gross_sales", "completed_orders",
    "repeat_orders", "staff_minutes",
}
TARGET_MEASURE = "modeled_contribution_after_identified_costs"
RECOMMENDATION_PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _guard(condition: bool, message: str) -> None:
    if not condition:
        raise SyntheticGrowthError(message)


def _pairs(values: list[tuple[str, Any]]) -> dict:
    d = {}
    for key, value in values:
        _guard(key not in d, "Duplicate value-intelligence JSON field")
        d[key] = value
    return d


def _reject_numeric(value: str) -> None:
    raise SyntheticGrowthError("Floating or nonfinite numbers not supported")


def _exact(value: Any, fields: set[str], name: str) -> dict:
    _guard(type(value) is dict and set(value) == fields, f"Invalid {name} fields")
    return value


def _int(value: Any, maximum: int, name: str) -> int:
    _guard(type(value) is int and 0 <= value <= maximum, f"Invalid {name}")
    return value


def _digest(obj: Any) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True,
                             allow_nan=False, separators=(",", ":")).encode("ascii")).hexdigest()


def _parse_scenario(raw: bytes) -> dict:
    _guard(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\x00" not in raw,
           "Invalid bounded scenario input")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_float=_reject_numeric, parse_constant=_reject_numeric)
    except SyntheticGrowthError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed scenario input") from exc
    _exact(doc, {"schema_version", "classification", "currency",
                 "comparison_basis", "workspaces"}, "scenario root")
    _guard(type(doc["schema_version"]) is int and doc["schema_version"] == 1,
           "Unsupported scenario schema")
    _guard(doc["classification"] == "SYNTHETIC_SOURCE_ONLY"
           and doc["currency"] == "DEMO_CREDITS"
           and doc["comparison_basis"] == "EQUAL_30_DAY_EXAMPLES",
           "Live business records or other currencies are not accepted")
    workspaces = doc["workspaces"]
    _guard(type(workspaces) is list and len(workspaces) == 2,
           "Expected exactly two separated example businesses")
    seen = set()
    for ws in workspaces:
        _exact(ws, {"workspace", "baseline", "current"}, "workspace")
        name = ws["workspace"]
        _guard(type(name) is str and name in {"academy_demo", "bespoke_demo"}
               and name not in seen, "Unknown or duplicate workspace")
        seen.add(name)
        for phase in ("baseline", "current"):
            period = _exact(ws[phase], PERIOD_FIELDS, "financial period")
            _guard(type(period["period_id"]) is str
                   and period["period_id"] == f"SIM-{phase.upper()}-{name.upper()}",
                   "Unexpected comparison period")
            _guard(type(period["days"]) is int and period["days"] == 30,
                   "Comparison must use equal 30-day periods")
            for key in ("gross_sales", *COST_FIELDS):
                _int(period[key], MAX_AMOUNT, key)
            _int(period["completed_orders"], MAX_ORDERS, "completed orders")
            _int(period["repeat_orders"], MAX_ORDERS, "repeat orders")
            _int(period["staff_minutes"], MAX_STAFF_MINUTES, "staff minutes")
            _guard(period["repeat_orders"] <= period["completed_orders"],
                   "Repeat order count cannot exceed completed orders")
            _guard(period["refunds"] <= period["gross_sales"],
                   "Refunds cannot exceed gross sales")
            if period["completed_orders"] == 0:
                _guard(period["gross_sales"] == 0 and period["repeat_orders"] == 0,
                       "Zero orders cannot assert sales or repeat purchases")
    _guard(seen == {"academy_demo", "bespoke_demo"}, "Missing workspace")
    return doc


def _economics(period: dict) -> dict:
    cost_total = sum(period[x] for x in COST_FIELDS)
    value = period["gross_sales"] - cost_total
    gross = period["gross_sales"]
    count = period["completed_orders"]
    return {
        "gross_sales": gross,
        "identified_costs": {name: period[name] for name in COST_FIELDS},
        "total_identified_costs": cost_total,
        "modeled_contribution_after_identified_costs": value,
        "completed_orders": count,
        "repeat_orders": period["repeat_orders"],
        "staff_minutes_observed_in_scenario": period["staff_minutes"],
        "identified_cost_ratio_bps": cost_total * 10_000 // gross if gross else None,
        "contribution_margin_bps": value * 10_000 // gross if gross else None,
        "mean_gross_per_order_floor": gross // count if count else None,
        "net_profit_verified": False,
        "taxes_and_fixed_overhead_included": False,
        "staff_cost_monetized": False,
    }


def _difference(baseline: int, current: int) -> dict:
    _guard(type(baseline) is int and type(current) is int,
           "Only integer comparisons allowed")
    return {
        "absolute_change": current - baseline,
        "relative_change_bps": ((current - baseline) * 10_000 // baseline
                                if baseline > 0 else None),
        "baseline_zero": baseline == 0,
    }


def _opportunity(code: str, priority: str, why: str, evidence: str,
                 scenario: str, **detail: Any) -> dict:
    result = {
        "id": _digest({"workspace": scenario, "code": code})[:20],
        "code": code,
        "priority": priority,
        "observation": why,
        "evidence_required": evidence,
        "validated_causal_effect": False,
        "monetary_benefit_promised": False,
        "automated_action_available": False,
    }
    result.update(detail)
    return result


def _evaluate(workspace: dict, planned: dict) -> dict:
    baseline = _economics(workspace["baseline"])
    current = _economics(workspace["current"])
    old = baseline["modeled_contribution_after_identified_costs"]
    new = current["modeled_contribution_after_identified_costs"]
    target = planned["financial_summary"]["monthly_contribution_target"]
    counts = planned["workflow_counts"]
    def total(name: str) -> int:
        return counts.get(name, 0)
    ready = total("PROPOSED_HUMAN_REVIEW_ONLY")
    suppressed = total("SUPPRESSED_PROVIDER_OWNS") + total("SUPPRESSED_CONSENT_UNVERIFIED")
    deferred = total("DEFERRED_NOT_GOAL_RELEVANT")
    _guard(ready + suppressed + deferred == len(planned["workflow_proposals"]),
           "Unaccounted source-engine decision")
    # The current period is anchored to the same synthetic orders and variable
    # and advertising costs as P2-03j, rather than independently invented totals.
    source = planned["financial_summary"]
    for field, expected in (
        ("gross_sales", source["gross_sales"]),
        ("variable_cost", source["variable_cost"]),
        ("marketing_spend", source["marketing_spend"]),
        ("completed_orders", source["completed_orders"]),
        ("repeat_orders", source["repeat_orders"]),
    ):
        _guard(workspace["current"][field] == expected,
               f"Current period does not reconcile with source engine: {field}")

    cost_movements = [
        {
            "cost": key,
            **_difference(workspace["baseline"][key], workspace["current"][key]),
        }
        for key in COST_FIELDS
    ]
    increasing_costs = sorted(
        (dict(item) for item in cost_movements if item["absolute_change"] > 0),
        key=lambda row: (-row["absolute_change"], row["cost"]),
    )
    opportunities = []
    name = workspace["workspace"]
    gap = max(0, target - new)
    if gap > 0:
        opportunities.append(_opportunity(
            "INVESTIGATE_CONTRIBUTION_GAP", "HIGH",
            "Modeled contribution after identified costs is below the selected target.",
            "Validate a complete cost ledger, overhead, customer baseline and actual receipts.",
            name, modeled_gap_to_target=gap))
    old_ratio = baseline["identified_cost_ratio_bps"]
    new_ratio = current["identified_cost_ratio_bps"]
    if old_ratio is not None and new_ratio is not None and new_ratio > old_ratio:
        opportunities.append(_opportunity(
            "REVIEW_COST_LEAKAGE", "HIGH",
            "Identified cost as a share of gross sales increased in the example.",
            "Confirm supplier invoices, provider fees, returns and overhead before repricing.",
            name, cost_ratio_rise_bps=new_ratio - old_ratio,
            highest_cost_increase=increasing_costs[0] if increasing_costs else None))
    if current["gross_sales"] < baseline["gross_sales"]:
        opportunities.append(_opportunity(
            "INVESTIGATE_LOWER_SALES", "MEDIUM",
            "Gross sales in the comparison period are lower.",
            "Verify traffic, available stock, lead quality and seasonality before concluding cause.",
            name, reported_sales_change=current["gross_sales"]-baseline["gross_sales"]))
    if current["repeat_orders"] > baseline["repeat_orders"]:
        opportunities.append(_opportunity(
            "VALIDATE_REPEAT_BUSINESS", "MEDIUM",
            "More repeat-order events are present in the example; retention is not established.",
            "Use real consented cohorts and a consistent customer identity and time window.",
            name, observed_repeat_order_change=current["repeat_orders"]-baseline["repeat_orders"]))
    if ready:
        opportunities.append(_opportunity(
            "MEASURE_REVIEW_WORK", "MEDIUM",
            "The goal-specific workflow engine produced reviewable proposals, not deliveries.",
            "Measure reviews, approved deliveries, opt-outs, handling time and controlled outcomes.",
            name, reviewable_count=ready))
    if suppressed:
        opportunities.append(_opportunity(
            "KEEP_CUSTOMER_SAFEGUARDS", "LOW",
            "Provider ownership and missing marketing permission restricted some proposals.",
            "Verify authoritative provider ownership and customer consent before any live integration.",
            name, suppressed_count=suppressed))
    opportunities.sort(key=lambda x: (RECOMMENDATION_PRIORITY[x["priority"]],
                                      x["code"]))
    return {
        "workspace": name,
        "comparison": {
            "baseline": baseline,
            "current": current,
            "gross_sales": _difference(baseline["gross_sales"], current["gross_sales"]),
            "identified_costs": _difference(baseline["total_identified_costs"],
                                            current["total_identified_costs"]),
            TARGET_MEASURE: _difference(old, new),
            "staff_minutes": _difference(baseline["staff_minutes_observed_in_scenario"],
                                         current["staff_minutes_observed_in_scenario"]),
            "cost_movements": cost_movements,
            "largest_identified_cost_increases": increasing_costs,
            "equal_periods_days": 30,
            "baseline_measured_from_customer_records": False,
            "seasonality_controlled": False,
            "incremental_contribution_proven": False,
            "staff_time_saved_by_automation_proven": False,
            "conversion_rate_computable": False,
            "profit_or_roi_proven": False,
        },
        "workflow_effectiveness": {
            "reviewable": ready,
            "deferred": deferred,
            "suppressed": suppressed,
            "approved": 0,
            "delivered": 0,
            "actual_customer_responses": 0,
            "incremental_sales_from_workflows": None,
            "cost_per_verified_conversion": None,
            "provider_attribution_verified": False,
            "causal_effect_verified": False,
        },
        "modeled_contribution_target": target,
        "modeled_gap_to_target": gap,
        "ranked_opportunities": opportunities,
        "release_decision": "NO_REAL_AUTOMATION_OR_COMMERCIAL_ACTIVATION",
    }


def build_business_value_report(raw_scenarios: bytes,
                                *, raw_growth_fixture: bytes | None = None,
                                goal: str = "CONTRIBUTION") -> dict:
    """Strictly bounded analysis; the source fixture is also validated in full."""
    _guard(type(goal) is str and goal in GOALS, "Unsupported business goal")
    raw = FIXTURE.read_bytes() if raw_growth_fixture is None else raw_growth_fixture
    _guard(type(raw) is bytes, "Invalid growth fixture")
    parse_growth_fixture(raw)
    source = build_growth_work_plan(raw, goal=goal)
    example = _parse_scenario(raw_scenarios)
    plans = {x["workspace"]: x for x in source["workspaces"]}
    businesses = [
        _evaluate(group, plans[group["workspace"]])
        for group in sorted(example["workspaces"], key=lambda x: x["workspace"])
    ]
    report = {
        "schema_version": 1,
        "milestone": "P2-03m_BUSINESS_VALUE_INTELLIGENCE",
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "units": "DEMO_CREDITS_NOT_USD",
        "goal": goal,
        "businesses": businesses,
        "interpretation": {
            "descriptive_comparisons_only": True,
            "causal_roi_claim_permitted": False,
            "revenue_growth_guaranteed": False,
            "modeled_contribution_is_net_profit": False,
            "percent_changes_require_nonzero_baseline": True,
            "real_marketing_conversions_measured": False,
            "baseline_validated_with_customer_data": False,
        },
        "release_controls": dict(NON_OPERATIONAL),
        "actual_customer_data": False,
        "external_provider_calls": 0,
        "messages_sent": 0,
        "real_workflow_executions": 0,
        "actual_subscription_charges": 0,
        "database_changes": 0,
        "scenario_sha256": sha256(raw_scenarios).hexdigest(),
        "growth_fixture_sha256": sha256(raw).hexdigest(),
    }
    report["evidence_sha256"] = _digest(report)
    return report


def build_committed_value_report(*, goal: str = "CONTRIBUTION") -> dict:
    """Only committed, validated synthetic inputs; no arbitrary live account path."""
    return build_business_value_report(SCENARIOS.read_bytes(), goal=goal)


def validate_value_evidence(report: dict) -> bool:
    """Detect local report mutation, not authenticate its author or prove a sale."""
    if type(report) is not dict:
        return False
    if report.get("classification") != "SYNTHETIC_SOURCE_ONLY":
        return False
    if report.get("release_controls") != NON_OPERATIONAL:
        return False
    if report.get("external_provider_calls") != 0 or report.get("messages_sent") != 0:
        return False
    if report.get("actual_subscription_charges") != 0:
        return False
    h = report.get("evidence_sha256")
    try:
        return type(h) is str and h == _digest({
            key: val for key, val in report.items() if key != "evidence_sha256"
        })
    except (ValueError, TypeError, OverflowError):
        return False
