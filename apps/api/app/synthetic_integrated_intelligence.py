"""P2-03o: integrated 12-module, five-engine business intelligence source lab.

Offline, synthetic, deterministic and tenant-scoped. No production service, external
actions, contacts, predictive claims, financial recommendations or persistence.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_growth_value_intelligence import build_committed_value_report, validate_value_evidence, TARGET_MEASURE
from .synthetic_business_decisions import decision_dashboard, simulate_decision

FIXTURE = Path(__file__).resolve().parents[3] / "contracts/domains/v1/fixtures/synthetic_business_suite.v1.json"
MODULES = (
    ("objective", "Objective Workspace"),
    ("value", "Business Value Intelligence"),
    ("decision", "Decision Intelligence"),
    ("growth", "Growth Autopilot"),
    ("crm", "CRM Intelligence"),
    ("inventory", "Inventory Intelligence"),
    ("finance", "Financial Intelligence"),
    ("marketing", "Marketing Intelligence"),
    ("commerce", "Sales & Commerce Intelligence"),
    ("workflow", "Workflow Automation"),
    ("operations", "Operations & Workforce Intelligence"),
    ("executive", "Executive Intelligence"),
)
ENGINES = ("measurement", "decision", "recommendation", "automation", "learning")
MAX_BYTES = 16_384
MAX_NUMBER = 10_000_000
MAX_SKUS = 20
WORKSPACES = {"academy_demo", "bespoke_demo"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SyntheticGrowthError(message)


def _integer(value: Any, name: str) -> int:
    _require(type(value) is int and 0 <= value <= MAX_NUMBER, "Invalid integer: " + name)
    return value


def _exact(obj: Any, keys: set[str], label: str) -> dict:
    _require(type(obj) is dict and set(obj) == keys, "Invalid fields: " + label)
    return obj


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    out = {}
    for key, value in pairs:
        _require(key not in out, "Duplicate JSON key")
        out[key] = value
    return out


def _no_float(value: str) -> None:
    raise SyntheticGrowthError("Noninteger JSON numbers prohibited")


def parse_suite_fixture(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\\x00" not in raw,
             "Invalid synthetic fixture size or type")
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_float=_no_float, parse_constant=_no_float)
    except SyntheticGrowthError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed synthetic input") from exc
    _exact(parsed, {"schema_version", "classification", "currency", "workspaces"}, "root")
    _require(type(parsed["schema_version"]) is int and parsed["schema_version"] == 1
             and parsed["classification"] == "SYNTHETIC_SOURCE_ONLY"
             and parsed["currency"] == "DEMO_CREDITS", "Only approved synthetic fixtures supported")
    workspaces = parsed["workspaces"]
    _require(type(workspaces) is list and len(workspaces) == 2, "Two example workspaces required")
    seen = set()
    for ws in workspaces:
        _exact(ws, {"workspace", "crm", "inventory", "marketing", "sales",
                    "operations", "identified_cost_budget"}, "workspace")
        name = ws["workspace"]
        _require(type(name) is str and name in WORKSPACES and name not in seen,
                 "Duplicate or unknown workspace")
        seen.add(name)
        sections = {
            "crm": {"active_contacts", "consented_contacts", "followups_due", "optouts"},
            "marketing": {"impressions", "clicks", "drafts", "reviewed"},
            "sales": {"quotes", "carts", "returns_handled"},
            "operations": {"tasks_open", "tasks_completed", "tasks_overdue",
                           "minutes_available"},
        }
        for key, fields in sections.items():
            obj = _exact(ws[key], fields, key)
            for field in fields:
                _integer(obj[field], key + "." + field)
        crm, marketing, operations = ws["crm"], ws["marketing"], ws["operations"]
        _require(crm["consented_contacts"] + crm["optouts"] <= crm["active_contacts"],
                 "CRM counts contradictory")
        _require(crm["followups_due"] <= crm["active_contacts"], "Too many followups")
        _require(marketing["clicks"] <= marketing["impressions"]
                 and marketing["reviewed"] <= marketing["drafts"], "Marketing counts contradictory")
        _require(operations["tasks_overdue"] <= operations["tasks_open"],
                 "Overdue tasks exceed open tasks")
        _integer(ws["identified_cost_budget"], "identified_cost_budget")
        inventory = ws["inventory"]
        _require(type(inventory) is list and 1 <= len(inventory) <= MAX_SKUS, "Invalid inventory list")
        seen_skus = set()
        for item in inventory:
            _exact(item, {"sku", "on_hand", "reorder_point", "unit_cost",
                          "units_sold_last_30_days"}, "inventory item")
            sku = item["sku"]
            _require(type(sku) is str and sku.startswith("SIM-") and
                     5 <= len(sku) <= 40 and sku.isascii() and sku not in seen_skus,
                     "Invalid or repeated simulated SKU")
            seen_skus.add(sku)
            for field in ("on_hand", "reorder_point", "unit_cost", "units_sold_last_30_days"):
                _integer(item[field], "inventory." + field)
    _require(seen == WORKSPACES, "Missing example workspace")
    return parsed


def _bps(part: int, whole: int) -> int | None:
    return part * 10_000 // whole if whole else None


def _engine_measure(value: dict) -> dict:
    curr = value["current"]
    base = value["baseline"]
    return {
        "gross_sales": curr["gross_sales"],
        "identified_costs": curr["total_identified_costs"],
        "modeled_contribution": curr[TARGET_MEASURE],
        "completed_orders": curr["completed_orders"],
        "previous_gross_sales": base["gross_sales"],
        "previous_modeled_contribution": base[TARGET_MEASURE],
        "gross_change": curr["gross_sales"] - base["gross_sales"],
        "contribution_change": curr[TARGET_MEASURE] - base[TARGET_MEASURE],
        "net_profit_verified": False, "data_source": "P2_03M_RECONCILED_EXAMPLES",
    }


def _engine_recommend(modules: dict) -> list[dict]:
    """Rule-derived suggestions; never infer causal revenue effects."""
    candidates = []
    def add(code: str, priority: str, reason: str, evidence: str) -> None:
        candidates.append({"code": code, "priority": priority,
                           "reason": reason, "evidence_needed": evidence,
                           "validated_incremental_impact": False,
                           "can_auto_execute": False})
    if modules["objective"]["gap_to_target"] > 0:
        add("TARGET_GAP", "HIGH", "Modeled contribution is below selected target",
            "Full actual ledger and independently verified baseline")
    if modules["inventory"]["reorder_flags"]:
        add("STOCK_REVIEW", "HIGH", "Illustrative stock is below the reorder threshold",
            "Current stocktake, demand context and supplier lead times")
    if modules["crm"]["followups_due"]:
        add("CONSENTED_FOLLOWUP_REVIEW", "MEDIUM", "Synthetic CRM followups await human review",
            "Valid current consent, customer purpose and unsubscribe handling")
    if modules["operations"]["tasks_overdue"]:
        add("BACKLOG_REVIEW", "MEDIUM", "Illustrative overdue work requires triage",
            "Task owner, deadlines and workload evidence")
    if modules["marketing"]["unreviewed_drafts"]:
        add("CONTENT_REVIEW", "LOW", "Marketing drafts require approval",
            "Brand guidelines, factual review and publishing permission")
    return sorted(candidates, key=lambda o:
                  ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[o["priority"]], o["code"]))


def build_integrated_suite(workspace: str = "academy_demo", goal: str = "CONTRIBUTION",
                           *, raw_fixture: bytes | None = None) -> dict:
    _require(type(workspace) is str and workspace in WORKSPACES, "Unsupported workspace")
    raw = FIXTURE.read_bytes() if raw_fixture is None else raw_fixture
    fixture = parse_suite_fixture(raw)
    data = next(ws for ws in fixture["workspaces"] if ws["workspace"] == workspace)
    value = build_committed_value_report(goal=goal)
    _require(validate_value_evidence(value), "Invalid P2-03m source evidence")
    decision = decision_dashboard(value, workspace)
    measured = _engine_measure(decision)
    comparison = decision["trends"]
    curr = decision["current"]
    workflow = decision["workflow_review"]
    stock = [
        {
            "sku": item["sku"], "on_hand": item["on_hand"],
            "reorder_point": item["reorder_point"],
            "reorder_quantity": max(0, item["reorder_point"]-item["on_hand"]),
            "illustrative_stock_value": item["on_hand"]*item["unit_cost"],
            "units_sold_last_30_days": item["units_sold_last_30_days"],
            "reorder_flag": item["on_hand"] < item["reorder_point"],
        }
        for item in data["inventory"]
    ]
    stock_needed = sum(int(item["reorder_flag"]) for item in stock)
    crm = data["crm"]
    marketing = data["marketing"]
    sales = data["sales"]
    ops = data["operations"]
    modules = {
        "objective": {
            "goal": goal, "target": next(b for b in value["businesses"]
                                       if b["workspace"] == workspace)["modeled_contribution_target"],
            "metric": TARGET_MEASURE,
            "current": measured["modeled_contribution"],
        },
        "value": {
            "baseline": decision["baseline"], "current": curr,
            "trends": comparison,
            "staff_time_saved_proven": False,
        },
        "decision": {
            "recommended_reviews": len(decision["opportunities"]),
            "hypothetical_zero_change": simulate_decision(value, workspace),
            "insights": decision["opportunities"],
            "forecast_available": False,
        },
        "growth": {
            "reviewable": workflow["reviewable"], "suppressed": workflow["suppressed"],
            "deferred": workflow["deferred"], "delivered": 0,
            "marketing_conversions_attributed": None,
        },
        "crm": {
            "active_contacts": crm["active_contacts"],
            "consented_contacts_in_demo": crm["consented_contacts"],
            "followups_due": crm["followups_due"], "optouts": crm["optouts"],
            "consent_share_bps": _bps(crm["consented_contacts"], crm["active_contacts"]),
            "outreach_enabled": False,
        },
        "inventory": {
            "items": stock, "reorder_flags": stock_needed,
            "illustrative_stock_value": sum(item["illustrative_stock_value"] for item in stock),
            "demand_forecast_available": False,
        },
        "finance": {
            "gross_sales": curr["gross_sales"],
            "identified_cost_breakdown": curr["identified_costs"],
            "total_identified_costs": curr["total_identified_costs"],
            "identified_cost_budget": data["identified_cost_budget"],
            "cost_vs_plan": curr["total_identified_costs"]-data["identified_cost_budget"],
            "modeled_contribution": curr[TARGET_MEASURE],
            "net_profit": None, "cash_balance": None, "bank_connected": False,
        },
        "marketing": {
            "impressions": marketing["impressions"], "clicks": marketing["clicks"],
            "click_through_bps": _bps(marketing["clicks"], marketing["impressions"]),
            "drafts": marketing["drafts"], "unreviewed_drafts": marketing["drafts"]-marketing["reviewed"],
            "attributed_sales": None, "posts_published": 0,
        },
        "commerce": {
            "completed_orders": curr["completed_orders"],
            "gross_sales": curr["gross_sales"],
            "mean_sales_per_order_floor": curr["mean_gross_per_order_floor"],
            "quotes": sales["quotes"], "carts": sales["carts"],
            "refund_amount": curr["identified_costs"]["refunds"],
            "returns_handled": sales["returns_handled"],
            "conversion_rate_verified": False,
        },
        "workflow": {
            "pending_review": workflow["reviewable"], "deferred": workflow["deferred"],
            "suppressed": workflow["suppressed"],
            "external_execution_enabled": False,
            "outbound_messages": 0,
            "review_authorizes_sending": False,
        },
        "operations": {
            "tasks_open": ops["tasks_open"], "tasks_completed": ops["tasks_completed"],
            "tasks_overdue": ops["tasks_overdue"],
            "backlog_share_bps": _bps(ops["tasks_overdue"], ops["tasks_open"]),
            "minutes_available": ops["minutes_available"],
            "observed_staff_minutes": curr["staff_minutes_observed_in_scenario"],
            "time_saved_by_ai_verified": False,
        },
        "executive": {
            **measured, "identified_cost_ratio_bps": curr["identified_cost_ratio_bps"],
            "repeat_orders": curr["repeat_orders"],
            "cross_module_review_only": True,
            "known_evidence_gaps": ["no_real_customer_records", "no_approved_integrations",
                                    "no_causal_attribution", "no_verified_net_profit"],
        },
    }
    modules["objective"]["gap_to_target"] = max(0, modules["objective"]["target"] -
                                                 modules["objective"]["current"])
    recommendations = _engine_recommend(modules)
    report = {
        "schema_version": 1, "milestone": "P2_03O_UNIFIED_INTELLIGENCE_LAB",
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "workspace": workspace, "goal": goal, "units": "DEMO_CREDITS_NOT_USD",
        "catalog": [{"id": module_id, "name": title} for module_id, title in MODULES],
        "engines": {
            "measurement": measured,
            "decision": {"simulation": modules["decision"]["hypothetical_zero_change"],
                         "forecast_available": False},
            "recommendation": {"ranked": recommendations, "actual_impact_verified": False},
            "automation": {"state": "REVIEW_ONLY", "outbound_actions": 0,
                           "customer_execution_enabled": False},
            "learning": {
                "gross_sales_change": comparison["gross_sales"],
                "contribution_change": comparison[TARGET_MEASURE],
                "equal_baseline_days": 30, "controlled_causal_effect": None,
                "experimental_evidence": False,
            },
        },
        "modules": modules,
        "source": {"value_evidence_sha256": value["evidence_sha256"],
                   "fixture_sha256": sha256(raw).hexdigest()},
        "safety": {
            "tenant_authentication_provided": False,
            "real_customer_data": False,
            "database_writes": 0,
            "provider_calls": 0,
            "messages_sent": 0,
            "payments_processed": 0,
            "subscriptions_required": False,
            "production_ready": False,
        },
    }
    _require(tuple(report["modules"]) == tuple(x[0] for x in MODULES),
             "Incomplete business module contract")
    _require(tuple(report["engines"]) == ENGINES, "Incomplete intelligence engine contract")
    return report
