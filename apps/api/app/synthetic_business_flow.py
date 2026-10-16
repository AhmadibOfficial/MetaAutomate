"""P2-03c: deterministic *proposal-only* retail/wholesale cross-functional simulation.

Pure Python, fixed committed synthetic fixture. No API route, connector, database,
payments, notifications, accounting posting, reservation or operational authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[3] / "contracts/domains/v1/fixtures/synthetic_business_flow.json"
MAX_BYTES = 16_384
MAX_ORDERS = 12
MAX_LINES = 8
MAX_SKUS = 20
MAX_UNIT = 10_000
MAX_DEMO_PRICE = 1_000_000
MAX_QUOTATION = 100_000_000
SECTORS = {"retail", "wholesale"}
SKU = re.compile(r"DEMO-[A-Z0-9-]{2,28}\Z")
ORDER = re.compile(r"DEMO-ORD-[A-Z0-9-]{2,28}\Z")
SCENARIO = re.compile(r"DEMO-(RETAIL|WHOLESALE)-[0-9]{2}\Z")
CUSTOMER = re.compile(r"Synthetic Customer [A-Za-z0-9 -]{1,35}\Z")
LABEL = re.compile(r"Synthetic [A-Za-z0-9 -]{1,45}\Z")
SOURCE_CAPABILITIES = ["BIZ-004", "BIZ-011", "BIZ-012"]


class SyntheticWorkflowError(ValueError):
    """Fail closed: never use rejected or non-synthetic inputs."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SyntheticWorkflowError(message)


def _object(value: object, fields: set[str], name: str) -> dict:
    _require(type(value) is dict and set(value) == fields, f"{name}: invalid fields")
    return value


def _integer(value: object, name: str, low: int, high: int) -> int:
    _require(type(value) is int and low <= value <= high, f"{name}: invalid integer")
    return value


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    item = {}
    for k, v in pairs:
        _require(k not in item, "Duplicate JSON key rejected")
        item[k] = v
    return item


def parse_synthetic_flow_bytes(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\x00" not in raw,
             "Synthetic fixture size or bytes rejected")
    try:
        obj = json.loads(raw.decode("utf-8"),
                         object_pairs_hook=_unique_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             SyntheticWorkflowError("Non-finite JSON number rejected")))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticWorkflowError("Invalid synthetic JSON") from exc
    doc = _object(obj, {"schema_version", "classification", "currency", "scenarios"}, "document")
    _require(type(doc["schema_version"]) is int and doc["schema_version"] == 1,
             "Unsupported document version")
    _require(doc["classification"] == "SYNTHETIC_DEMO_ONLY", "Synthetic classification required")
    _require(doc["currency"] == "DEMO_CREDITS", "Real monetary denomination prohibited")
    groups = doc["scenarios"]
    _require(type(groups) is list and len(groups) == 2, "Exactly two sample sectors required")
    seen_scenarios: set[str] = set()
    seen_orders: set[str] = set()
    for group in groups:
        s = _object(group, {"sector", "scenario_id", "inventory", "orders"}, "scenario")
        sector = s["sector"]
        _require(type(sector) is str and sector in SECTORS and sector not in seen_scenarios,
                 "Unknown or repeated sector")
        seen_scenarios.add(sector)
        _require(type(s["scenario_id"]) is str and SCENARIO.fullmatch(s["scenario_id"])
                 and sector.upper() in s["scenario_id"], "Invalid scenario identity")
        inventory, orders = s["inventory"], s["orders"]
        _require(type(inventory) is list and 1 <= len(inventory) <= MAX_SKUS,
                 "Invalid inventory row count")
        _require(type(orders) is list and 1 <= len(orders) <= MAX_ORDERS,
                 "Invalid synthetic order count")
        local_skus: set[str] = set()
        for item in inventory:
            row = _object(item, {"sku", "label", "on_hand_units", "reorder_threshold_units",
                                 "target_units", "unit_price_demo_credits"}, "inventory item")
            sku = row["sku"]
            _require(type(sku) is str and SKU.fullmatch(sku) and sku not in local_skus,
                     "Invalid or duplicate demo SKU")
            local_skus.add(sku)
            _require(type(row["label"]) is str and LABEL.fullmatch(row["label"]),
                     "Invalid synthetic item label")
            for field in ("on_hand_units", "reorder_threshold_units", "target_units"):
                _integer(row[field], field, 0, MAX_UNIT)
            _require(row["target_units"] >= row["reorder_threshold_units"],
                     "Stock target below reorder threshold")
            _integer(row["unit_price_demo_credits"], "synthetic unit price", 1, MAX_DEMO_PRICE)
        for order in orders:
            row = _object(order, {"order_id", "customer_label", "lines"}, "order")
            oid = row["order_id"]
            _require(type(oid) is str and ORDER.fullmatch(oid) and oid not in seen_orders,
                     "Invalid or duplicate synthetic order ID")
            seen_orders.add(oid)
            _require(type(row["customer_label"]) is str and CUSTOMER.fullmatch(row["customer_label"]),
                     "Only fictional customer labels allowed")
            lines = row["lines"]
            _require(type(lines) is list and 1 <= len(lines) <= MAX_LINES,
                     "Invalid sales line count")
            in_order = set()
            for line in lines:
                l = _object(line, {"sku", "quantity_units"}, "order line")
                _require(type(l["sku"]) is str and l["sku"] in local_skus and
                         l["sku"] not in in_order, "Unknown, duplicated or cross-sector SKU")
                in_order.add(l["sku"])
                _integer(l["quantity_units"], "sale quantity", 1, MAX_UNIT)
    _require(seen_scenarios == SECTORS, "Both retail and wholesale synthetic sectors required")
    return doc


def _digest(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                  .encode("ascii")).hexdigest()


def _sector_preview(group: dict) -> dict:
    sector = group["sector"]
    stock = {i["sku"]: i for i in group["inventory"]}
    reserved = {sku: 0 for sku in stock}
    draft_sales = []
    followups = []
    finance = []
    stages = []
    for order in group["orders"]:
        oid = order["order_id"]
        line_quotes = []
        total = 0
        for line in order["lines"]:
            sku, qty = line["sku"], line["quantity_units"]
            original = stock[sku]["on_hand_units"]
            _require(reserved[sku] + qty <= original,
                     f"Insufficient synthetic stock for proposed order {oid}: {sku}")
            reserved[sku] += qty
            line_amount = qty * stock[sku]["unit_price_demo_credits"]
            total += line_amount
            _require(total <= MAX_QUOTATION, "Synthetic quotation exceeds bounded maximum")
            line_quotes.append({"sku": sku, "quantity_units": qty,
                                "unit_price_demo_credits": stock[sku]["unit_price_demo_credits"],
                                "line_total_demo_credits": line_amount})
        sale = {"order_id": oid, "customer_label": order["customer_label"], "lines": line_quotes,
                "quotation_total_demo_credits": total, "state": "DRAFT_NOT_SUBMITTED",
                "idempotency_preview": _digest({"sector": sector, "order_id": oid})[:24]}
        draft_sales.append(sale)
        followups.append({
            "order_id": oid, "customer_label": order["customer_label"],
            "suggested_action": "ASK_FOR_ORDER_CONFIRMATION" if sector == "retail"
                                else "REVIEW_QUOTE_AND_PAYMENT_TERMS",
            "delivery_state": "NOT_SENT", "contact_details": None
        })
        entries = [
            {"account": "DEMO_ACCOUNTS_RECEIVABLE", "side": "DEBIT",
             "amount_demo_credits": total},
            {"account": "DEMO_SALES_REVENUE", "side": "CREDIT",
             "amount_demo_credits": total},
        ]
        finance.append({"order_id": oid, "state": "UNPOSTED_PROPOSAL",
                        "document_type": "QUOTE_JOURNAL_ILLUSTRATION_NOT_AN_INVOICE",
                        "entries": entries, "balanced": True,
                        "debit_total_demo_credits": total, "credit_total_demo_credits": total,
                        "actual_payment_recorded": False})
        stages.append({"order_id": oid, "steps": [
            {"stage": stage, "state": "SIMULATED_NOT_EXECUTED"} for stage in (
                "INVENTORY_ALLOCATION_PREVIEW", "SALES_QUOTATION_DRAFT",
                "CUSTOMER_FOLLOWUP_DRAFT", "FINANCE_JOURNAL_PREVIEW", "VERIFY_INVARIANTS"
            )
        ]})
    inventory = []
    for item in group["inventory"]:
        sku = item["sku"]
        projected = item["on_hand_units"] - reserved[sku]
        _require(projected >= 0, "Synthetic inventory oversold")
        low = projected < item["reorder_threshold_units"]
        inventory.append({
            "sku": sku, "label": item["label"],
            "original_on_hand_units": item["on_hand_units"],
            "proposed_allocation_units": reserved[sku],
            "projected_if_approved_units": projected,
            "reorder_threshold_units": item["reorder_threshold_units"],
            "below_threshold_if_approved": low,
            "suggested_restock_units": max(0, item["target_units"] - projected) if low else 0,
            "original_stock_unchanged": True
        })
    total_sales = sum(x["quotation_total_demo_credits"] for x in draft_sales)
    _require(total_sales == sum(x["debit_total_demo_credits"] for x in finance)
             == sum(x["credit_total_demo_credits"] for x in finance),
             "Synthetic finance proposal must balance")
    _require(sum(x["proposed_allocation_units"] for x in inventory) ==
             sum(x["quantity_units"] for o in draft_sales for x in o["lines"]),
             "Stock and sales allocation totals disagree")
    return {
        "sector": sector, "scenario_id": group["scenario_id"], "approval_state": "HUMAN_REVIEW_REQUIRED",
        "stock_allocation_state": "PROPOSAL_ONLY",
        "inventory": inventory,
        "sales_drafts": draft_sales,
        "customer_followup_drafts": followups,
        "finance_journal_previews": finance,
        "trace": stages,
        "totals": {
            "draft_orders": len(draft_sales),
            "proposed_units": sum(x["proposed_allocation_units"] for x in inventory),
            "potential_quoted_demo_credits": total_sales,
            "unissued_finance_document_count": len(finance),
            "unsent_customer_followups": len(followups)
        }
    }


def render_synthetic_business_flow(raw: bytes, *, sector: str = "all") -> dict:
    """Read-only fully deterministic demonstration; no request/session/tenant adapter."""
    doc = parse_synthetic_flow_bytes(raw)
    _require(sector in {"all", "retail", "wholesale"}, "Invalid local demo selection")
    previews = [_sector_preview(group) for group in doc["scenarios"]
                if sector == "all" or group["sector"] == sector]
    result = {
        "schema_version": 1,
        "mode": "LOCAL_SYNTHETIC_CROSS_FUNCTIONAL_PREVIEW",
        "classification": "SYNTHETIC_DEMO_ONLY",
        "product": "metaautomate", "currency": "DEMO_CREDITS",
        "draft_capability_ids": SOURCE_CAPABILITIES,
        "operational_status": "NO_GO",
        "simulation_only": True, "actual_business_data": False,
        "real_customer_data_used": False,
        "execution_available": False, "customer_messages_sent": False,
        "stock_mutation_performed": False, "orders_submitted": False,
        "invoices_issued": False, "payments_processed": False,
        "ledger_posted": False, "database_write_performed": False,
        "external_request_performed": False,
        "fixture_sha256": sha256(raw).hexdigest(),
        "scenarios": previews
    }
    result["evidence_sha256"] = _digest(result)
    return result


def read_committed_demo(*, sector: str = "all") -> dict:
    """The only accepted data source is the repository's fixed synthetic fixture."""
    return render_synthetic_business_flow(FIXTURE.read_bytes(), sector=sector)
