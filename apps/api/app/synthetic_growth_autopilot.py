"""P2-03h: deterministic synthetic Growth Autopilot, no execution authority.

Two fictional merchant-workspace examples: training and apparel. No real Selar
orders, personal data, social scraping, AI inference, sending, paid billing,
customer onboarding, database, external requests, or activated API route.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[3] / "contracts/domains/v1/fixtures/synthetic_growth_autopilot.v1.json"
MAX_BYTES = 24_576
MAX_ITEMS = 20
MAX_ORDERS = 24
MAX_EVENTS = 40
MAX_UNITS = 100
MAX_PRICE = 1_000_000
MAX_SPEND = 10_000_000
MAX_VALUE = 100_000_000
WORKSPACES = {"academy_demo": "education", "bespoke_demo": "apparel"}
EVENTS = {
    "LEAD_OPT_IN", "CHECKOUT_ABANDONED", "PURCHASE_COMPLETED",
    "LEARNING_COMPLETED", "GARMENT_DELIVERED"
}
RECIPES = {
    "LEAD_OPT_IN": ("ONBOARDING_VALUE_PREVIEW_DRAFT", "REVIEW_REQUIRED"),
    "CHECKOUT_ABANDONED": ("SELAR_NATIVE_REMINDER_OWNS_RECOVERY", "SUPPRESSED_PROVIDER_OWNS"),
    "PURCHASE_COMPLETED": ("POST_PURCHASE_SUPPORT_DRAFT", "REVIEW_REQUIRED"),
    "LEARNING_COMPLETED": ("RELATED_LEARNING_PATH_DRAFT", "REVIEW_REQUIRED"),
    "GARMENT_DELIVERED": ("REPEAT_STYLE_OR_CARE_DRAFT", "REVIEW_REQUIRED"),
}
DEMO_ID = re.compile(r"DEMO-[A-Z0-9-]{4,40}\Z")
LABEL = re.compile(r"Synthetic [A-Za-z0-9 -]{1,44}\Z")


class SyntheticGrowthError(ValueError):
    """Reject non-synthetic input or inconsistent automation accounting."""


def _require(ok: bool, msg: str) -> None:
    if not ok:
        raise SyntheticGrowthError(msg)


def _exact(value: object, fields: set[str], part: str) -> dict:
    _require(type(value) is dict and set(value) == fields, f"{part}: forbidden or missing fields")
    return value


def _int(value: object, low: int, high: int, name: str) -> int:
    _require(type(value) is int and low <= value <= high, f"{name}: invalid integer")
    return value


def _id(value: object, known: set[str], name: str) -> str:
    _require(type(value) is str and DEMO_ID.fullmatch(value) is not None
             and value not in known, f"{name}: invalid/duplicate ID")
    known.add(value)
    return value


def _unique_object_pairs(pairs: list[tuple[str, object]]) -> dict:
    d = {}
    for k, v in pairs:
        _require(k not in d, "Duplicate JSON field")
        d[k] = v
    return d


def _reject_number(_: str):
    raise SyntheticGrowthError("Floating-point or non-finite figure not accepted")


def parse_growth_fixture(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\x00" not in raw,
             "Fixture too large or invalid")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object_pairs,
                         parse_constant=_reject_number, parse_float=_reject_number)
    except SyntheticGrowthError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticGrowthError("Invalid synthetic JSON") from exc
    _exact(doc, {"schema_version", "classification", "currency", "workspaces"}, "root")
    _require(type(doc["schema_version"]) is int and doc["schema_version"] == 1,
             "Unsupported schema version")
    _require(doc["classification"] == "SYNTHETIC_DEMO_ONLY"
             and doc["currency"] == "DEMO_CREDITS",
             "Real business records or currency prohibited")
    groups = doc["workspaces"]
    _require(type(groups) is list and len(groups) == 2, "Exactly two fictional workspaces required")
    workspace_ids: set[str] = set()
    event_ids: set[str] = set()
    order_ids: set[str] = set()
    journey_ids: set[str] = set()
    product_ids: set[str] = set()
    for group in groups:
        g = _exact(group, {"workspace", "business_type", "goal_target_demo_credits",
                           "marketing_spend_demo_credits", "products", "orders", "events"},
                   "workspace")
        workspace = g["workspace"]
        _require(type(workspace) is str and workspace in WORKSPACES
                 and workspace not in workspace_ids, "Unknown or duplicated demo workspace")
        workspace_ids.add(workspace)
        _require(g["business_type"] == WORKSPACES[workspace], "Business type mismatch")
        _int(g["goal_target_demo_credits"], 1, MAX_VALUE, "Demo business goal")
        _int(g["marketing_spend_demo_credits"], 0, MAX_SPEND, "Synthetic marketing spend")
        prods = g["products"]
        orders = g["orders"]
        events = g["events"]
        _require(type(prods) is list and 1 <= len(prods) <= MAX_ITEMS,
                 "Invalid fictional product catalogue count")
        _require(type(orders) is list and 1 <= len(orders) <= MAX_ORDERS,
                 "Invalid invented order count")
        _require(type(events) is list and 1 <= len(events) <= MAX_EVENTS,
                 "Invalid synthetic trigger count")
        products = {}
        for p in prods:
            row = _exact(p, {"product_id", "label", "unit_price_demo_credits",
                             "variable_cost_demo_credits"}, "product")
            pid = _id(row["product_id"], product_ids, "product")
            _require(type(row["label"]) is str and LABEL.fullmatch(row["label"]),
                     "Real product names not accepted")
            price = _int(row["unit_price_demo_credits"], 1, MAX_PRICE, "Demo unit price")
            cost = _int(row["variable_cost_demo_credits"], 0, MAX_PRICE,
                        "Demo variable cost")
            _require(cost <= price, "Negative synthetic unit contribution denied")
            products[pid] = p
        by_order = {}
        for o in orders:
            row = _exact(o, {"order_id", "journey_id", "product_id", "units",
                             "attribution"}, "order")
            oid = _id(row["order_id"], order_ids, "order")
            journey = row["journey_id"]
            _require(type(journey) is str and DEMO_ID.fullmatch(journey),
                     "Only fictional journey IDs accepted")
            _require(row["product_id"] in products, "Cross-workspace/unknown product reference")
            _int(row["units"], 1, MAX_UNITS, "Completed demo units")
            _require(row["attribution"] in ("UNATTRIBUTED", "SYNTHETIC_CAMPAIGN_LABEL"),
                     "No claimed deterministic marketing attribution")
            by_order[oid] = row
        local_journeys: set[str] = set()
        for e in events:
            row = _exact(e, {"event_id", "event_type", "journey_id", "product_id",
                             "consent_status", "order_ref"}, "event")
            _id(row["event_id"], event_ids, "event")
            kind = row["event_type"]
            _require(type(kind) is str and kind in EVENTS, "Unknown automation trigger")
            journey = row["journey_id"]
            _require(type(journey) is str and DEMO_ID.fullmatch(journey),
                     "Only fictional journey IDs accepted")
            local_journeys.add(journey)
            _require(row["product_id"] in products, "Cross-workspace/unknown trigger product")
            _require(row["consent_status"] in ("SYNTHETIC_OPTED_IN", "NOT_RECORDED"),
                     "Consent status must be explicit")
            if kind in ("PURCHASE_COMPLETED", "LEARNING_COMPLETED", "GARMENT_DELIVERED"):
                oid = row["order_ref"]
                _require(type(oid) is str and oid in by_order,
                         "Completed action requires matching fictional order")
                source = by_order[oid]
                _require(source["product_id"] == row["product_id"] and
                         source["journey_id"] == journey,
                         "Cross-product or mismatched customer journey")
            else:
                _require(row["order_ref"] is None, "Lead or cart event cannot claim an order")
            _require((kind != "LEARNING_COMPLETED" or g["business_type"] == "education")
                     and (kind != "GARMENT_DELIVERED" or g["business_type"] == "apparel"),
                     "Trigger incompatible with business type")
        _require(set(o["journey_id"] for o in orders).issubset(local_journeys),
                 "All completed fictional orders require matching event journeys")
        # Separate workspaces do not share even synthetic journey IDs; this
        # is a validation property, NOT authenticated tenant isolation.
        _require(not (journey_ids & local_journeys),
                 "Cross-workspace journey reference prohibited")
        journey_ids.update(local_journeys)
        for o in orders:
            _require(any(e["event_type"] == "PURCHASE_COMPLETED"
                         and e["order_ref"] == o["order_id"] for e in events),
                     "Completed order lacks purchase trigger")
    _require(workspace_ids == set(WORKSPACES), "Missing required fictional workspace")
    return doc


def _hash(obj: object) -> str:
    return sha256(json.dumps(obj, separators=(",", ":"), sort_keys=True,
                             ensure_ascii=True).encode("ascii")).hexdigest()


def _evaluate(workspace: dict) -> dict:
    wid = workspace["workspace"]
    products = {p["product_id"]: p for p in workspace["products"]}
    gross_sales = sum(products[o["product_id"]]["unit_price_demo_credits"] * o["units"]
                      for o in workspace["orders"])
    variable_cost = sum(products[o["product_id"]]["variable_cost_demo_credits"] * o["units"]
                        for o in workspace["orders"])
    _require(gross_sales <= MAX_VALUE and variable_cost <= MAX_VALUE,
             "Demo totals exceed safety bounds")
    contribution = gross_sales - variable_cost
    spend = workspace["marketing_spend_demo_credits"]
    after_spend = contribution - spend
    goal = workspace["goal_target_demo_credits"]
    journeys = Counter(o["journey_id"] for o in workspace["orders"])
    automation_proposals = []
    for event in workspace["events"]:
        kind = event["event_type"]
        action, default_state = RECIPES[kind]
        # Selar already manages checkout reminder emails. A redundant automation
        # is ALWAYS suppressed, even when consent is recorded in the demo.
        state = default_state
        if state != "SUPPRESSED_PROVIDER_OWNS" and event["consent_status"] != "SYNTHETIC_OPTED_IN":
            state = "SUPPRESSED_NO_MARKETING_CONSENT"
        automation_proposals.append({
            "event_id": event["event_id"],
            "workspace": wid,
            "recipe": action,
            "source_event": kind,
            "state": state,
            "human_approval_required": True,
            "contact_details": None,
            "customer_message_sent": False,
            "payment_taken": False,
            "real_order_created": False,
            "provider_operation_performed": False,
            "idempotency_preview": _hash({"workspace": wid, "event_id": event["event_id"],
                                           "recipe": action})[:24],
        })
    _require(len({x["idempotency_preview"] for x in automation_proposals}) ==
             len(automation_proposals), "Duplicate deterministic proposal IDs")
    return {
        "workspace": wid, "business_type": workspace["business_type"],
        "operational_status": "NO_GO", "automation_mode": "LOCAL_PROPOSALS_ONLY",
        "financial_goal_kind": "MODELED_CONTRIBUTION_AFTER_MARKETING_SPEND",
        "goal_target_demo_credits": goal,
        "financial_summary": {
            "completed_fictional_orders": len(workspace["orders"]),
            "gross_sales_demo_credits": gross_sales,
            "variable_cost_demo_credits": variable_cost,
            "contribution_before_marketing_demo_credits": contribution,
            "marketing_spend_demo_credits": spend,
            "modeled_contribution_after_spend_demo_credits": after_spend,
            "goal_shortfall_demo_credits": max(0, goal - after_spend),
            "fictional_repeat_orders": sum(n - 1 for n in journeys.values() if n > 1),
            "sales_attributed_causally_to_automation": 0,
        },
        "automation_proposals": automation_proposals,
        "totals": {
            "triggers_considered": len(automation_proposals),
            "drafts_requiring_review": sum(x["state"] == "REVIEW_REQUIRED"
                                            for x in automation_proposals),
            "suppressed_by_provider": sum(x["state"] == "SUPPRESSED_PROVIDER_OWNS"
                                           for x in automation_proposals),
            "suppressed_by_consent": sum(x["state"] == "SUPPRESSED_NO_MARKETING_CONSENT"
                                          for x in automation_proposals),
            "messages_delivered": 0, "payments_processed": 0, "external_actions": 0,
        }
    }


def render_growth_preview(raw: bytes, *, workspace: str = "all") -> dict:
    """Pure in-memory calculation. Input is accepted only from committed demo."""
    doc = parse_growth_fixture(raw)
    _require(type(workspace) is str and workspace in {"all"} | set(WORKSPACES),
             "Unknown synthetic workspace selection")
    previews = [_evaluate(g) for g in doc["workspaces"]
                if workspace == "all" or g["workspace"] == workspace]
    report = {
        "schema_version": 1,
        "classification": "SYNTHETIC_DEMO_ONLY",
        "mode": "GROWTH_AUTOPILOT_READ_ONLY_SIMULATION",
        "currency": "DEMO_CREDITS",
        "businesses": previews,
        "operational_status": "NO_GO",
        "real_customer_data_used": False,
        "real_sales_records_used": False,
        "production_credentials_used": False,
        "actual_marketing_messages_sent": False,
        "social_posts_published": False,
        "transactions_processed": False,
        "real_customer_subscriptions_charged": False,
        "provider_api_calls_made": False,
        "database_writes_performed": False,
        "execution_available": False,
        "fixture_sha256": sha256(raw).hexdigest(),
        "causal_revenue_impact_proven": False,
        "profitability_claim_proven": False,
        "subscriptions_active": False,
    }
    report["evidence_sha256"] = _hash(report)
    return report


def read_committed_growth_demo(*, workspace: str = "all") -> dict:
    """Bounded fixture; no arbitrary input file selection or remote integrations."""
    return render_growth_preview(FIXTURE.read_bytes(), workspace=workspace)
