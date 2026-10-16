#!/usr/bin/env python3
"""P2-03d: offline, read-only cross-sector contract evidence validation.

Validates seven design profiles against the source-only retail/wholesale fixture,
draft capability catalog and Foundation NO-GO policy. NO API/DB/external actions.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_business_flow import (  # noqa: E402
    FIXTURE, parse_synthetic_flow_bytes, render_synthetic_business_flow
)

CONTRACT_PATH = "contracts/domains/v1/cross_sector_workflow_contract.v1.json"
SCHEMA_PATH = "contracts/domains/v1/cross_sector_workflow_contract.v1.schema.json"
CATALOG_PATH = "docs/registry/capabilities.csv"
FOUNDATION_PATH = "docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
SOURCE_REF = {
    "module": "apps/api/app/synthetic_business_flow.py",
    "fixture": "contracts/domains/v1/fixtures/synthetic_business_flow.json",
    "tests": "tests/test_cross_functional_synthetic.py",
    "architecture": "docs/architecture/P2_03C_SYNTHETIC_RETAIL_WHOLESALE_FLOW.md",
}
STAGES = (
    "AVAILABILITY_PREVIEW", "QUOTATION_DRAFT", "CUSTOMER_FOLLOWUP_DRAFT",
    "FINANCE_PREVIEW", "VERIFY_INVARIANTS",
)
SECTORS = (
    "retail", "wholesale", "transportation", "logistics", "tourism",
    "education", "healthcare",
)
REF_SECTORS = {"retail", "wholesale"}
DESIGN_SECTORS = set(SECTORS) - REF_SECTORS
DRAFT_CAPS = {"BIZ-004", "BIZ-011", "BIZ-012"}
DENIALS = {
    "real_business_records", "personal_or_sensitive_data", "outbound_messages",
    "inventory_mutation", "reservation_or_capacity_hold", "orders_submitted",
    "invoice_issuance", "actual_payments", "ledger_posting", "external_connectors",
    "clinical_operations", "customer_activation",
}
BASE_REVIEWS = {"authorization", "privacy", "finance", "audit", "recovery"}
DOMAIN_REVIEWS = {
    "retail": set(), "wholesale": set(),
    "transportation": {"transport_safety", "sector_regulatory"},
    "logistics": {"sector_regulatory"},
    "tourism": {"sector_regulatory", "consumer_protection"},
    "education": {"sector_regulatory", "minors_and_learners"},
    "healthcare": {"sector_regulatory", "clinical_boundary"},
}
DOMAIN_EXCLUSIONS = {
    "retail": {"real_customer_contact", "real_inventory_records", "payments"},
    "wholesale": {"real_customer_contact", "real_inventory_records", "credit_terms", "payments"},
    "transportation": {"driver_identifiers", "vehicle_live_locations", "passenger_data", "payments"},
    "logistics": {"real_shipment_details", "recipient_addresses", "live_tracking", "payments"},
    "tourism": {"guest_identifiers", "passport_data", "travel_itineraries", "payments"},
    "education": {"learner_records", "guardian_contact", "minors_data", "grades", "payments"},
    "healthcare": {"patient_data", "medical_records", "diagnoses", "medications", "insurance_claims", "payments"},
}
EXPECTED_MODELS = {
    "retail": ("stock_units", "draft_sales_quote", "unsent_order_confirmation", "unposted_quote_journal"),
    "wholesale": ("bulk_stock_units", "draft_bulk_order_quote", "unsent_terms_review", "unposted_quote_journal"),
    "transportation": ("trip_and_vehicle_capacity", "unissued_trip_estimate", "unsent_rider_update", "unposted_transport_estimate"),
    "logistics": ("route_and_shipment_slots", "unissued_delivery_quote", "unsent_milestone_update", "unposted_shipping_estimate"),
    "tourism": ("tour_and_room_capacity", "unissued_reservation_estimate", "unsent_guest_enquiry", "unposted_reservation_estimate"),
    "education": ("classroom_and_enrolment_capacity", "unissued_fee_estimate", "unsent_enrolment_enquiry", "unposted_education_fee_estimate"),
    "healthcare": ("administrative_appointment_capacity", "unissued_admin_service_estimate", "unsent_admin_enquiry", "unposted_admin_estimate"),
}
ROOT_FIELDS = {
    "schema_version", "contract_id", "classification", "default_policy",
    "operational_status", "execution_enabled", "actual_business_data_allowed",
    "external_actions_allowed", "currency", "description", "source_reference",
    "capability_links", "workflow_stages", "sector_profiles", "hard_denials",
    "release_evidence",
}
PROFILE_FIELDS = {
    "sector", "readiness", "source_scenario", "capacity_model",
    "quotation_model", "followup_model", "finance_model", "profile_id",
    "excluded_data_categories", "required_reviews", "risk_notes",
    "human_review_required", "execution_available",
}
STAGE_FIELDS = {
    "sequence", "stage", "description", "effect", "output_state",
    "human_review_required",
}
RELEASE_FIELDS = {
    "foundation", "foundation_policy", "required_blocked_gates",
    "synthetic_reference_sectors", "design_only_sectors", "operational_release",
}


def _path_exists(root: Path, rel: object) -> bool:
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel:
        return False
    p = Path(rel)
    if any(x in ("..", ".") for x in p.parts):
        return False
    try:
        resolved = (root / p).resolve(strict=True)
        return resolved.is_relative_to(root.resolve()) and resolved.is_file()
    except (OSError, ValueError):
        return False


def _unique_strings(value: object, expected: set[str]) -> bool:
    return (type(value) is list and len(value) == len(expected)
            and all(type(x) is str for x in value)
            and set(value) == expected)


def _safe_profile(sector: str, p: dict) -> list[str]:
    errors: list[str] = []
    if set(p) != PROFILE_FIELDS:
        errors.append(f"{sector}: unexpected or missing profile fields")
        return errors
    if p["profile_id"] != f"meta.sector.{sector}.v1":
        errors.append(f"{sector}: invalid stable profile id")
    if p["human_review_required"] is not True or p["execution_available"] is not False:
        errors.append(f"{sector}: cannot authorize execution or bypass human review")
    expected_readiness = ("SYNTHETIC_REFERENCE_ONLY" if sector in REF_SECTORS
                          else "DESIGN_MAPPING_ONLY")
    expected_source = sector if sector in REF_SECTORS else None
    if p["readiness"] != expected_readiness or p["source_scenario"] != expected_source:
        errors.append(f"{sector}: design-only sector cannot claim synthetic source verification")
    models = tuple(p[field] for field in (
        "capacity_model", "quotation_model", "followup_model", "finance_model"
    ))
    if models != EXPECTED_MODELS[sector]:
        errors.append(f"{sector}: domain model mapping changed without reviewed contract version")
    reviews = BASE_REVIEWS | DOMAIN_REVIEWS[sector]
    if not _unique_strings(p["required_reviews"], reviews):
        errors.append(f"{sector}: mandatory domain/security reviews changed")
    if not _unique_strings(p["excluded_data_categories"], DOMAIN_EXCLUSIONS[sector]):
        errors.append(f"{sector}: forbidden sensitive/real-data categories changed")
    if not isinstance(p["risk_notes"], str) or len(p["risk_notes"].strip()) < 60:
        errors.append(f"{sector}: explicit limitations and risks required")
    return errors


def validate(doc: object, catalog: list[dict], foundation: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if type(doc) is not dict or set(doc) != ROOT_FIELDS:
        return ["Contract must be an exact, versioned source-only document"]
    constants = {
        "schema_version": "1.0.0",
        "contract_id": "metaautomate.cross_sector.business_workflow.v1",
        "classification": "SOURCE_ONLY_SYNTHETIC_AND_DESIGN",
        "default_policy": "DENY",
        "operational_status": "NO_GO",
        "execution_enabled": False,
        "actual_business_data_allowed": False,
        "external_actions_allowed": False,
        "currency": "DEMO_CREDITS_ONLY",
    }
    for field, required in constants.items():
        if doc[field] != required or type(doc[field]) is not type(required):
            errors.append(f"{field}: runtime authorization or contract identity must not change")
    if not isinstance(doc["description"], str) or len(doc["description"].strip()) < 40:
        errors.append("Contract description must distinguish source from operational scope")
    if doc["source_reference"] != SOURCE_REF or any(
        not _path_exists(root, value) for value in SOURCE_REF.values()
    ):
        errors.append("Existing P2-03c source evidence paths missing or modified")
    if not _path_exists(root, SCHEMA_PATH):
        errors.append("Machine-readable structural schema missing")
    if not _unique_strings(doc["capability_links"], DRAFT_CAPS):
        errors.append("Existing draft capability links must not change")
    caps = {r.get("capability_id"): r for r in catalog if type(r) is dict}
    if len(catalog) != 33 or len(caps) != 33 or any(
        caps.get(c, {}).get("lifecycle_status") != "DRAFT" for c in DRAFT_CAPS
    ):
        errors.append("Source capability mappings must remain DRAFT, disabled catalog records")
    if not _unique_strings(doc["hard_denials"], DENIALS):
        errors.append("Required explicit real-world side-effect denials changed")
    stages = doc["workflow_stages"]
    if type(stages) is not list or len(stages) != len(STAGES):
        errors.append("Exactly five ordered design stages required")
    else:
        for position, (stage, expected) in enumerate(zip(stages, STAGES), start=1):
            if type(stage) is not dict or set(stage) != STAGE_FIELDS:
                errors.append(f"Stage {position}: invalid fields")
                continue
            if (type(stage["sequence"]) is not int or stage["sequence"] != position
                    or stage["stage"] != expected or stage["effect"] != "NONE"
                    or stage["output_state"] != "PROPOSAL_ONLY"
                    or stage["human_review_required"] is not True):
                errors.append(f"Stage {position}: unapproved effect, reordered stage or human-review bypass")
            if not isinstance(stage["description"], str) or len(stage["description"].strip()) < 30:
                errors.append(f"Stage {position}: meaningful scope description required")
    profiles = doc["sector_profiles"]
    if type(profiles) is not list or len(profiles) != len(SECTORS):
        errors.append("Exactly seven sector design profiles required")
    else:
        names = [p.get("sector") for p in profiles if type(p) is dict]
        if len(names) != 7 or names != list(SECTORS):
            errors.append("Missing, repeated or reordered seven-sector identities")
        else:
            for p in profiles:
                errors.extend(_safe_profile(p["sector"], p))
    rel = doc["release_evidence"]
    if type(rel) is not dict or set(rel) != RELEASE_FIELDS:
        errors.append("Missing or extra release-evidence fields")
    else:
        if (rel["foundation"] != FOUNDATION_PATH
                or rel["foundation_policy"] != "NO_GO_UNTIL_ALL_NINE_VERIFIED"
                or rel["operational_release"] != "NO_GO"):
            errors.append("Release evidence cannot authorize operational use")
        if (not _unique_strings(rel["synthetic_reference_sectors"], REF_SECTORS)
                or not _unique_strings(rel["design_only_sectors"], DESIGN_SECTORS)):
            errors.append("Source reference and design-only sector classification mismatch")
        gates = foundation.get("checks", []) if type(foundation) is dict else []
        blocked = {g.get("id") for g in gates if type(g) is dict and g.get("status") != "verified"}
        if (foundation.get("policy") != "NO_GO_UNTIL_ALL_NINE_VERIFIED"
                or len(gates) != 9
                or {g.get("id") for g in gates} != {f"F{i:02d}" for i in range(1, 10)}
                or not blocked
                or not _unique_strings(rel["required_blocked_gates"], blocked)):
            errors.append("Foundation blocked gates and operational NO-GO must remain authoritative")
    return errors


def sources(root: Path = ROOT) -> tuple[dict, list[dict], dict]:
    doc = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    with (root / CATALOG_PATH).open(encoding="utf-8-sig", newline="") as f:
        catalog = list(csv.DictReader(f))
    foundation = json.loads((root / FOUNDATION_PATH).read_text(encoding="utf-8"))
    return doc, catalog, foundation


def evidence(doc: dict, root: Path = ROOT) -> dict:
    """Proof is bounded to the two unchanged invented scenarios, not new adapters."""
    path = root / SOURCE_REF["fixture"]
    raw = path.read_bytes()
    synthetic = parse_synthetic_flow_bytes(raw)
    if {x["sector"] for x in synthetic["scenarios"]} != REF_SECTORS:
        raise ValueError("Reference scenario set changed")
    output = render_synthetic_business_flow(raw)
    if output.get("operational_status") != "NO_GO" or len(output.get("scenarios", [])) != 2:
        raise ValueError("Synthetic source is not denied")
    for flag in (
        "actual_business_data", "real_customer_data_used", "execution_available",
        "customer_messages_sent", "stock_mutation_performed", "orders_submitted",
        "invoices_issued", "payments_processed", "ledger_posted",
        "database_write_performed", "external_request_performed",
    ):
        if output.get(flag) is not False:
            raise ValueError(f"Disallowed source effect: {flag}")
    summaries = []
    for preview in output["scenarios"]:
        name = preview["sector"]
        if preview.get("approval_state") != "HUMAN_REVIEW_REQUIRED":
            raise ValueError("Synthetic scenario lost human-review boundary")
        if len(preview["sales_drafts"]) != len(preview["customer_followup_drafts"]) != len(preview["finance_journal_previews"]):
            raise ValueError("Source counts disagree")
        sales = {item["order_id"] for item in preview["sales_drafts"]}
        if (sales != {item["order_id"] for item in preview["customer_followup_drafts"]}
                or sales != {item["order_id"] for item in preview["finance_journal_previews"]}
                or sales != {item["order_id"] for item in preview["trace"]}):
            raise ValueError("Synthetic order trace broken")
        for row in preview["finance_journal_previews"]:
            if (row.get("balanced") is not True or row.get("state") != "UNPOSTED_PROPOSAL"
                    or row["debit_total_demo_credits"] != row["credit_total_demo_credits"]):
                raise ValueError("Finance example not bounded or balanced")
        if any(x.get("delivery_state") != "NOT_SENT" for x in preview["customer_followup_drafts"]):
            raise ValueError("Follow-up demo attempted delivery")
        summaries.append({
            "sector": name, "source_state": "SYNTHETIC_REFERENCE_ONLY",
            "draft_orders": len(sales), "unissued_finance_previews": len(preview["finance_journal_previews"]),
            "unsent_followups": len(preview["customer_followup_drafts"]),
        })
    if {x["sector"] for x in summaries} != REF_SECTORS:
        raise ValueError("Source sector mismatch")
    return {
        "source_fixture_sha256": sha256(raw).hexdigest(),
        "synthetic_report_sha256": output["evidence_sha256"],
        "source_reference_summaries": summaries,
    }


def evaluate(doc: dict, catalog: list[dict], foundation: dict, root: Path = ROOT) -> dict:
    errors = validate(doc, catalog, foundation, root)
    report = {
        "result": "BLOCKED" if errors else "PASS_SOURCE_CONTRACT_ONLY",
        "contract_id": doc.get("contract_id") if type(doc) is dict else None,
        "operational_release": "NO_GO",
        "real_execution_authorized": False,
        "source_reference_count": len(REF_SECTORS),
        "design_only_count": len(DESIGN_SECTORS),
        "executed_adapters": 0, "outbound_actions": 0,
        "errors": errors,
    }
    if not errors:
        try:
            report.update(evidence(doc, root))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            report["errors"].append("Synthetic reference evidence invalid: " + str(exc))
            report["result"] = "BLOCKED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Optional local JSON evidence report")
    args = parser.parse_args()
    doc, catalog, foundation = sources()
    report = evaluate(doc, catalog, foundation)
    if args.report:
        destination = Path(args.report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(report["result"] != "PASS_SOURCE_CONTRACT_ONLY")


if __name__ == "__main__":
    sys.exit(main())
