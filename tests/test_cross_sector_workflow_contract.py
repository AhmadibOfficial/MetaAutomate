"""P2-03d cross-sector contract: existing synthetic proof; five design-only profiles."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_cross_sector_workflow_contract as contract  # noqa: E402


def sources():
    return contract.sources(ROOT)


def check(doc, catalog, foundation):
    return contract.evaluate(doc, catalog, foundation, ROOT)


def rejects(modifier, substring):
    d, c, f = sources()
    modifier(d, c, f)
    result = check(d, c, f)
    assert result["result"] == "BLOCKED", result
    assert any(substring in msg for msg in result["errors"]), result


def test_reference_contract_checks_two_synthetic_proofs_five_design_profiles():
    doc, catalog, foundation = sources()
    result = check(doc, catalog, foundation)
    assert result["result"] == "PASS_SOURCE_CONTRACT_ONLY"
    assert result["real_execution_authorized"] is False
    assert result["executed_adapters"] == result["outbound_actions"] == 0
    assert result["source_reference_count"] == 2
    assert result["design_only_count"] == 5
    assert [p["sector"] for p in doc["sector_profiles"]] == list(contract.SECTORS)
    assert {p["sector"] for p in doc["sector_profiles"]
            if p["readiness"] == "DESIGN_MAPPING_ONLY"} == contract.DESIGN_SECTORS
    assert result["source_fixture_sha256"] == __import__("hashlib").sha256(
        (ROOT / contract.SOURCE_REF["fixture"]).read_bytes()).hexdigest()
    assert [(x["sector"], x["draft_orders"]) for x in result["source_reference_summaries"]] == [
        ("retail", 2), ("wholesale", 2)
    ]
    assert all(x["unissued_finance_previews"] == 2 and x["unsent_followups"] == 2
               for x in result["source_reference_summaries"])


def test_structural_schema_matches_contract_and_restricts_unknown_fields():
    doc, _, _ = sources()
    schema = json.loads((ROOT / contract.SCHEMA_PATH).read_text())
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == contract.ROOT_FIELDS
    assert schema["properties"]["operational_status"]["const"] == "NO_GO"
    assert schema["properties"]["execution_enabled"]["const"] is False
    assert schema["properties"]["external_actions_allowed"]["const"] is False
    assert set(schema["$defs"]["sector"]["required"]) == contract.PROFILE_FIELDS
    assert schema["$defs"]["sector"]["additionalProperties"] is False
    assert len(doc["workflow_stages"]) == 5


def test_cannot_activate_execution_or_external_providers():
    rejects(lambda d,c,f: d.update(execution_enabled=True), "runtime authorization")
    rejects(lambda d,c,f: d.update(external_actions_allowed=True), "runtime authorization")
    rejects(lambda d,c,f: d.update(actual_business_data_allowed=True), "runtime authorization")
    rejects(lambda d,c,f: d.update(default_policy="ALLOW"), "runtime authorization")
    rejects(lambda d,c,f: d.update(operational_status="GO"), "runtime authorization")


def test_currency_and_unknown_fields_fail_closed():
    rejects(lambda d,c,f: d.update(currency="NGN"), "runtime authorization")
    rejects(lambda d,c,f: d.update(production_enabled=True), "exact, versioned")


def test_disallows_side_effects_in_stages():
    rejects(lambda d,c,f: d["workflow_stages"][2].update(effect="SEND_MESSAGE"),
            "unapproved effect")
    rejects(lambda d,c,f: d["workflow_stages"][1].update(output_state="INVOICE_ISSUED"),
            "unapproved effect")
    rejects(lambda d,c,f: d["workflow_stages"][0].update(human_review_required=False),
            "human-review bypass")
    rejects(lambda d,c,f: d["workflow_stages"][1].update(stage="FINANCE_PREVIEW"),
            "reordered stage")


def test_missing_or_duplicated_sector_is_rejected():
    rejects(lambda d,c,f: d["sector_profiles"].pop(), "Exactly seven")
    rejects(lambda d,c,f: d["sector_profiles"][2].update(sector="retail"),
            "Missing, repeated")
    rejects(lambda d,c,f: d["sector_profiles"][0].update(profile_id="meta.sector.wholesale.v1"),
            "invalid stable profile id")


def test_design_only_profiles_cannot_claim_existing_synthetic_proof():
    rejects(lambda d,c,f: d["sector_profiles"][2].update(readiness="SYNTHETIC_REFERENCE_ONLY"),
            "design-only sector cannot claim")
    rejects(lambda d,c,f: d["sector_profiles"][6].update(source_scenario="retail"),
            "design-only sector cannot claim")
    rejects(lambda d,c,f: d["sector_profiles"][0].update(source_scenario=None),
            "design-only sector cannot claim")


def test_sector_specific_safeguards_and_privacy_exclusions_are_mandatory():
    rejects(lambda d,c,f: d["sector_profiles"][6]["excluded_data_categories"].remove("patient_data"),
            "forbidden sensitive")
    rejects(lambda d,c,f: d["sector_profiles"][5]["required_reviews"].remove("minors_and_learners"),
            "mandatory domain")
    rejects(lambda d,c,f: d["sector_profiles"][2]["required_reviews"].remove("transport_safety"),
            "mandatory domain")
    rejects(lambda d,c,f: d["sector_profiles"][6].update(execution_available=True),
            "cannot authorize")
    rejects(lambda d,c,f: d["sector_profiles"][4].update(human_review_required=False),
            "cannot authorize")
    rejects(lambda d,c,f: d["sector_profiles"][3].update(risk_notes="OK"),
            "explicit limitations")
    rejects(lambda d,c,f: d["sector_profiles"][2].update(
        capacity_model="patient_medical_triage"), "domain model mapping")


def test_capability_mapping_must_remain_disabled_and_draft():
    rejects(lambda d,c,f: d["capability_links"].append("CORE-001"), "capability links")
    rejects(lambda d,c,f: next(row for row in c if row["capability_id"] == "BIZ-012").update(
        lifecycle_status="ACTIVE"), "DRAFT")


def test_hard_denials_and_foundation_no_go_cannot_be_weakened():
    rejects(lambda d,c,f: d["hard_denials"].remove("clinical_operations"),
            "side-effect denials")
    rejects(lambda d,c,f: d["release_evidence"].update(operational_release="GO"),
            "cannot authorize")
    rejects(lambda d,c,f: d["release_evidence"]["required_blocked_gates"].remove("F09"),
            "Foundation blocked")
    rejects(lambda d,c,f: next(x for x in f["checks"] if x["id"] == "F09").update(
        status="verified"), "Foundation blocked")


def test_existing_synthetic_proof_is_not_fabricated_for_five_sectors():
    doc, catalog, foundation = sources()
    first = check(doc, catalog, foundation)
    second = check(doc, catalog, foundation)
    assert first == second
    assert all(x["sector"] not in contract.DESIGN_SECTORS
               for x in first["source_reference_summaries"])
    assert first["operational_release"] == "NO_GO"
    assert set(doc["release_evidence"]["design_only_sectors"]) == contract.DESIGN_SECTORS
    assert set(doc["release_evidence"]["synthetic_reference_sectors"]) == contract.REF_SECTORS


def test_no_backend_route_integration_or_database_migration():
    main = (ROOT / "apps/api/app/main.py").read_text()
    script = (ROOT / "scripts/verify_cross_sector_workflow_contract.py").read_text()
    assert "cross_sector_workflow_router" not in main
    assert "include_router(cross_sector" not in main
    for disallowed in ("psycopg", "requests.", "httpx.", "subprocess.", "send_email",
                       "openai.", "redis.", "sqlalchemy"):
        assert disallowed not in script
    assert "render_synthetic_business_flow" in script
    assert "SOURCE_ONLY_SYNTHETIC_AND_DESIGN" in script
