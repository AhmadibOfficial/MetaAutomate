"""P2-03n: source-only, deterministic decision support over verified synthetic P2-03m reports.

No live accounts, persistence, external effects, forecasts, or asserted causal benefit.
"""
from __future__ import annotations

from copy import deepcopy

from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_growth_value_intelligence import (
    COST_FIELDS, TARGET_MEASURE, build_committed_value_report,
    validate_value_evidence,
)

PRIORITIES = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
STATES = ("PROPOSED", "APPROVED_FOR_MANUAL_REVIEW", "IN_PROGRESS", "COMPLETED", "DISMISSED")
MAX_ADJUSTMENT = 5000  # basis points, up to 50 percent magnitude


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SyntheticGrowthError(message)


def _integer(value: object, low: int, high: int, name: str) -> int:
    _require(type(value) is int and low <= value <= high, "Invalid " + name)
    return value


def _business(report: dict, workspace: str) -> dict:
    _require(validate_value_evidence(report), "Invalid source evidence")
    matches = [item for item in report["businesses"] if item["workspace"] == workspace]
    _require(len(matches) == 1 and workspace in ("academy_demo", "bespoke_demo"),
             "Unknown or duplicate workspace")
    return matches[0]


def decision_dashboard(report: dict, workspace: str) -> dict:
    """Return directly traceable data for a read-only financial workspace."""
    business = _business(report, workspace)
    comparison = business["comparison"]
    opportunities = []
    for item in business["ranked_opportunities"]:
        _require(item["priority"] in PRIORITIES and type(item["id"]) is str,
                 "Invalid recommendation")
        opportunities.append({
            "id": item["id"], "code": item["code"], "priority": item["priority"],
            "observation": item["observation"], "evidence_required": item["evidence_required"],
            "financial_benefit_verified": False,
            "evidence_quality": "SYNTHETIC_ONLY",
            "manual_decision_required": True,
        })
    opportunities.sort(key=lambda item: (PRIORITIES[item["priority"]], item["code"]))
    return {
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "workspace": workspace,
        "units": report["units"],
        "goal": report["goal"],
        "period_days": comparison["equal_periods_days"],
        "baseline": deepcopy(comparison["baseline"]),
        "current": deepcopy(comparison["current"]),
        "trends": {field: deepcopy(comparison[field]) for field in
                   ("gross_sales", "identified_costs", TARGET_MEASURE)},
        "cost_movements": deepcopy(comparison["cost_movements"]),
        "workflow_review": deepcopy(business["workflow_effectiveness"]),
        "opportunities": opportunities,
        "source_evidence_sha256": report["evidence_sha256"],
        "not_net_profit": True,
        "verified_causal_effect": False,
        "production_ready": False,
    }


def simulate_decision(report: dict, workspace: str, *,
                      price_change_bps: int = 0, order_change_bps: int = 0,
                      variable_cost_change_bps: int = 0) -> dict:
    """Hypothetical sensitivity, NOT a prediction. All math uses integers.

    Gross changes with assumed order count and per-order price. Variable costs
    change with order count and user-provided unit-cost sensitivity. Other known
    costs are held constant; these assumptions are explicitly surfaced.
    """
    view = decision_dashboard(report, workspace)
    price = _integer(price_change_bps, -MAX_ADJUSTMENT, MAX_ADJUSTMENT, "price change")
    orders = _integer(order_change_bps, -MAX_ADJUSTMENT, MAX_ADJUSTMENT, "orders change")
    variable = _integer(variable_cost_change_bps, -MAX_ADJUSTMENT, MAX_ADJUSTMENT,
                        "variable cost change")
    current = view["current"]
    new_sales = (current["gross_sales"] * (10000 + price) *
                 (10000 + orders) // 100_000_000)
    new_variable = (current["identified_costs"]["variable_cost"] *
                    (10000 + variable) * (10000 + orders) // 100_000_000)
    other_costs = sum(value for key, value in current["identified_costs"].items()
                      if key != "variable_cost")
    new_contribution = new_sales - new_variable - other_costs
    original = current[TARGET_MEASURE]
    return {
        "classification": "HYPOTHETICAL_SYNTHETIC_NOT_FORECAST",
        "workspace": workspace,
        "adjustments_bps": {"price": price, "orders": orders, "variable_unit_cost": variable},
        "illustrative_gross_sales": new_sales,
        "illustrative_identified_costs": new_variable + other_costs,
        "illustrative_contribution": new_contribution,
        "change_from_source_contribution": new_contribution - original,
        "baseline_source_contribution": original,
        "assumptions": [
            "Order count and per-order price change independently only for arithmetic illustration.",
            "Variable cost scales with assumed orders and unit cost; other identified costs stay constant.",
            "Returns, demand elasticity, taxes, fixed overhead and unrecorded costs are not modeled.",
        ],
        "forecast": False, "causal_impact_verified": False,
        "income_guarantee": False, "action_executed": False,
        "source_evidence_sha256": view["source_evidence_sha256"],
    }


def create_manual_action(report: dict, workspace: str, opportunity_id: str) -> dict:
    """Build a proposed task only. Caller retains a local copy, no persistence."""
    view = decision_dashboard(report, workspace)
    _require(type(opportunity_id) is str, "Invalid opportunity id")
    match = [item for item in view["opportunities"] if item["id"] == opportunity_id]
    _require(len(match) == 1, "Opportunity must belong to selected workspace")
    op = match[0]
    return {
        "id": "SIM-TASK-" + workspace + "-" + opportunity_id,
        "workspace": workspace, "opportunity_id": opportunity_id,
        "title": op["code"].replace("_", " ").title(),
        "required_evidence": op["evidence_required"],
        "state": "PROPOSED", "history": ["PROPOSED"],
        "owner": "UNASSIGNED_SYNTHETIC",
        "human_approval_required": True, "external_execution_enabled": False,
        "source_evidence_sha256": view["source_evidence_sha256"],
    }


def transition_manual_action(task: dict, target: str) -> dict:
    """In-memory demo transitions; approval never authorizes external execution."""
    _require(type(task) is dict and task.get("external_execution_enabled") is False
             and task.get("human_approval_required") is True
             and task.get("state") in STATES and type(target) is str
             and type(task.get("history")) is list
             and task["history"] and task["history"][-1] == task["state"],
             "Invalid manual action")
    allowed = {
        "PROPOSED": ("APPROVED_FOR_MANUAL_REVIEW", "DISMISSED"),
        "APPROVED_FOR_MANUAL_REVIEW": ("IN_PROGRESS", "DISMISSED"),
        "IN_PROGRESS": ("COMPLETED", "DISMISSED"),
        "COMPLETED": (), "DISMISSED": (),
    }
    _require(target in allowed[task["state"]], "Illegal manual task transition")
    updated = deepcopy(task)
    updated["state"] = target
    updated["history"].append(target)
    return updated


def verify_outcome(report: dict, workspace: str, task: dict) -> dict:
    """Compare observed synthetic periods, never attribute change to an action."""
    view = decision_dashboard(report, workspace)
    _require(type(task) is dict and task.get("workspace") == workspace
             and task.get("state") == "COMPLETED"
             and task.get("source_evidence_sha256") == view["source_evidence_sha256"]
             and task.get("external_execution_enabled") is False
             and task.get("opportunity_id") in {x["id"] for x in view["opportunities"]},
             "Outcome requires matching completed synthetic task")
    delta = view["trends"][TARGET_MEASURE]
    return {
        "workspace": workspace, "task_id": task["id"],
        "source_comparison": deepcopy(delta),
        "comparison_is_descriptive": True,
        "outcome_attributable_to_task": False,
        "controlled_experiment_available": False,
        "customer_sales_evidence": False,
        "effect_estimate": None,
        "next_evidence_needed": "Collect consented, comparable real periods and evaluate confounders in a separately approved environment.",
    }


def build_demo_workspace(workspace: str = "academy_demo") -> dict:
    return decision_dashboard(build_committed_value_report(), workspace)
