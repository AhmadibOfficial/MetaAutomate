"""P2-03c cross-functional retail/wholesale source-only demo, negative-first."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from app.synthetic_business_flow import (  # noqa: E402
    SyntheticWorkflowError,
    parse_synthetic_flow_bytes, read_committed_demo, render_synthetic_business_flow,
    FIXTURE, MAX_BYTES
)


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def encoded(data):
    return json.dumps(data, sort_keys=True).encode("utf-8")


def rejects(data, match=None):
    with pytest.raises(SyntheticWorkflowError, match=match):
        render_synthetic_business_flow(encoded(data))


def test_retail_and_wholesale_are_composable_and_mathematically_correct():
    result = read_committed_demo()
    assert result["mode"] == "LOCAL_SYNTHETIC_CROSS_FUNCTIONAL_PREVIEW"
    assert result["draft_capability_ids"] == ["BIZ-004", "BIZ-011", "BIZ-012"]
    assert [s["sector"] for s in result["scenarios"]] == ["retail", "wholesale"]
    retail, wholesale = result["scenarios"]
    assert [x["quotation_total_demo_credits"] for x in retail["sales_drafts"]] == [7200, 8000]
    assert [x["quotation_total_demo_credits"] for x in wholesale["sales_drafts"]] == [111600, 182000]
    assert retail["totals"] == {
        "draft_orders": 2, "proposed_units": 8,
        "potential_quoted_demo_credits": 15200,
        "unissued_finance_document_count": 2, "unsent_customer_followups": 2
    }
    assert wholesale["totals"]["potential_quoted_demo_credits"] == 293600
    assert wholesale["totals"]["proposed_units"] == 50
    assert [(x["sku"], x["projected_if_approved_units"], x["suggested_restock_units"])
            for x in retail["inventory"]] == [("DEMO-TEA", 11, 0), ("DEMO-BAG", 2, 10)]
    assert [(x["sku"], x["projected_if_approved_units"], x["suggested_restock_units"])
            for x in wholesale["inventory"]] == [("DEMO-GRAIN", 8, 72), ("DEMO-PACK", 12, 0)]


def test_quotes_followups_and_finance_share_order_ids_but_have_no_side_effects():
    report = read_committed_demo()
    for scenario in report["scenarios"]:
        ids = [x["order_id"] for x in scenario["sales_drafts"]]
        assert ids == [x["order_id"] for x in scenario["customer_followup_drafts"]]
        assert ids == [x["order_id"] for x in scenario["finance_journal_previews"]]
        assert ids == [x["order_id"] for x in scenario["trace"]]
        assert scenario["approval_state"] == "HUMAN_REVIEW_REQUIRED"
        for followup in scenario["customer_followup_drafts"]:
            assert followup["delivery_state"] == "NOT_SENT"
            assert followup["contact_details"] is None
        for statement in scenario["finance_journal_previews"]:
            assert statement["state"] == "UNPOSTED_PROPOSAL"
            assert statement["document_type"] == "QUOTE_JOURNAL_ILLUSTRATION_NOT_AN_INVOICE"
            assert not statement["actual_payment_recorded"]
            assert statement["balanced"]
            assert statement["debit_total_demo_credits"] == statement["credit_total_demo_credits"]
            assert [x["side"] for x in statement["entries"]] == ["DEBIT", "CREDIT"]
        for item in scenario["inventory"]:
            assert item["original_stock_unchanged"]
            assert item["original_on_hand_units"] - item["proposed_allocation_units"] == item["projected_if_approved_units"]
        for event in scenario["trace"]:
            assert len(event["steps"]) == 5
            assert all(s["state"] == "SIMULATED_NOT_EXECUTED" for s in event["steps"])
    for field in ("simulation_only",):
        assert report[field] is True
    for field in ("actual_business_data", "real_customer_data_used", "execution_available",
                  "customer_messages_sent", "stock_mutation_performed", "orders_submitted",
                  "invoices_issued", "payments_processed", "ledger_posted",
                  "database_write_performed", "external_request_performed"):
        assert report[field] is False
    assert report["operational_status"] == "NO_GO"


def test_repeatability_partition_selection_and_immutability():
    fixture_bytes = FIXTURE.read_bytes()
    snapshot = fixture_bytes[:]
    first = read_committed_demo()
    second = read_committed_demo()
    assert first == second
    assert first["evidence_sha256"] == second["evidence_sha256"]
    assert FIXTURE.read_bytes() == snapshot
    ret = read_committed_demo(sector="retail")
    who = read_committed_demo(sector="wholesale")
    assert len(ret["scenarios"]) == len(who["scenarios"]) == 1
    assert ret["scenarios"][0] == first["scenarios"][0]
    assert who["scenarios"][0] == first["scenarios"][1]
    assert ret["evidence_sha256"] != who["evidence_sha256"]
    assert not any("DEMO-ORD-W" in json.dumps(s) for s in ret["scenarios"])
    assert not any("DEMO-ORD-R" in json.dumps(s) for s in who["scenarios"])


def test_negative_stock_or_oversell_rejected_before_output():
    d = fixture()
    d["scenarios"][0]["orders"][1]["lines"][0]["quantity_units"] = 15
    rejects(d, "Insufficient synthetic stock")


def test_cross_sector_sku_rejected():
    d = fixture()
    d["scenarios"][1]["orders"][0]["lines"][0]["sku"] = "DEMO-TEA"
    rejects(d, "cross-sector SKU")


def test_unknown_sector_and_duplicate_sector_rejected():
    d = fixture()
    d["scenarios"][1]["sector"] = "healthcare"
    rejects(d, "Unknown or repeated sector")
    d = fixture()
    d["scenarios"][1]["sector"] = "retail"
    rejects(d, "Unknown or repeated sector")


def test_extra_fields_and_real_customer_contact_rejected():
    d = fixture()
    d["scenarios"][0]["orders"][0]["customer_phone"] = "+1234567890"
    rejects(d, "invalid fields")
    d = fixture()
    d["scenarios"][0]["orders"][0]["customer_label"] = "James Smith"
    rejects(d, "fictional customer")
    d = fixture()
    d["scenarios"][0]["inventory"][0]["supplier_url"] = "https://example.com"
    rejects(d, "invalid fields")


@pytest.mark.parametrize("amount", [True, False, None, 3.5, -1, 1_000_001, "12"])
def test_invalid_synthetic_unit_prices_rejected(amount):
    d = fixture()
    d["scenarios"][0]["inventory"][0]["unit_price_demo_credits"] = amount
    rejects(d, "synthetic unit price")


@pytest.mark.parametrize("qty", [True, 0, -2, 1.5, "4", 10001])
def test_invalid_sale_quantities_rejected(qty):
    d = fixture()
    d["scenarios"][0]["orders"][0]["lines"][0]["quantity_units"] = qty
    rejects(d, "sale quantity")


def test_repeat_order_sku_and_json_keys_rejected():
    d = fixture()
    d["scenarios"][1]["orders"][0]["order_id"] = "DEMO-ORD-R1"
    rejects(d, "duplicate synthetic order")
    d = fixture()
    d["scenarios"][0]["orders"][0]["lines"].append(copy.deepcopy(
        d["scenarios"][0]["orders"][0]["lines"][0]))
    rejects(d, "duplicated")
    raw = FIXTURE.read_text(encoding="utf-8").replace(
        '"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1
    )
    with pytest.raises(SyntheticWorkflowError, match="Duplicate JSON key"):
        parse_synthetic_flow_bytes(raw.encode("utf-8"))


def test_fixture_classification_currency_and_schema_fail_closed():
    for field, value in [
        ("classification", "CUSTOMER_DATA"),
        ("currency", "NGN"),
        ("schema_version", True)
    ]:
        d = fixture()
        d[field] = value
        rejects(d)


def test_unknown_stock_amounts_floating_nonfinite_and_oversized_inputs():
    d = fixture()
    d["scenarios"][0]["inventory"][0]["on_hand_units"] = True
    rejects(d, "on_hand_units")
    for raw in [b"", b"\x00" + FIXTURE.read_bytes(), b" " * (MAX_BYTES + 1),
                b"\xff", b'{"schema_version": NaN}']:
        with pytest.raises(SyntheticWorkflowError):
            render_synthetic_business_flow(raw)


def test_demo_does_not_register_routes_connectors_or_storage():
    main = (ROOT / "apps/api/app/main.py").read_text()
    source = (ROOT / "apps/api/app/synthetic_business_flow.py").read_text()
    assert "synthetic_business_flow_router" not in main
    assert "include_router(synthetic_business_flow" not in main
    for dangerous in ("psycopg", "httpx", "requests.", "urllib.request", "subprocess",
                      "send_email", "smtp", "openai", "redis", "sqlalchemy"):
        assert dangerous not in source
    assert "FIXTURE.read_bytes()" in source
    assert "ledger_posted" in source
    assert "execution_available" in source


def test_baseline_capability_registry_remains_draft():
    catalog = (ROOT / "docs/registry/capabilities.csv").read_text()
    assert "BIZ-004,Sales Outreach & Follow-up,BIZ,R1,P0,DRAFT" in catalog
    assert "BIZ-011,Inventory & Operations,BIZ,R3,P2,DRAFT" in catalog
    assert "BIZ-012,Financial Operations,BIZ,R3,P2,DRAFT" in catalog
