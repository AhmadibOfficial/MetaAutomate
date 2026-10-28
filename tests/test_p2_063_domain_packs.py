"""P2-063: read-only industry-extensible domain-pack source contract checks.

No application imports, migrations, provider calls, customer data, new permissions
or executable domain actions. Pass proves metadata consistency only.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "contracts" / "domains" / "v2"
CATALOG_PATH = V2 / "domain-packs.v1.json"
SCHEMA_PATH = V2 / "domain-pack.schema.json"
DOC_PATH = ROOT / "docs/architecture/P2_063_UNIVERSAL_BUSINESS_AUTOMATION.md"

REVIEW_TYPES = frozenset((
    "IDENTITY_TENANT", "DOMAIN_SPECIALIST", "DATA_PROTECTION",
    "SECURITY_ACCEPTANCE", "LEGAL_REGULATORY", "MEASUREMENT_BASELINE",
    "HUMAN_APPROVAL", "CONNECTOR_AUTHORIZATION",
))

def read(path: Path) -> dict:
    assert path.is_file(), str(path)
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)

def test_schema_can_extend_without_fixed_industry_enum():
    schema = read(SCHEMA_PATH)
    assert schema["$schema"].endswith("draft/2020-12/schema")
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["profiles"]["type"] == "array"
    pack = schema["$defs"]["pack"]
    assert pack["additionalProperties"] is False
    assert "enum" not in pack["properties"]["id"]
    assert pack["properties"]["status"]["const"] == "DESIGN_ONLY"
    assert pack["properties"]["enabled"]["const"] is False
    assert pack["properties"]["production_ready"]["const"] is False
    assert schema["properties"]["operational_status"]["const"] == "NO_GO"
    extension = schema["properties"]["extension_contract"]["properties"]
    assert extension["industry_count_limit"]["type"] == "null"
    assert extension["accepts_new_sector_ids"]["const"] is True
    assert extension["required_server_side_admission"]["const"] is True
    assert extension["production_enabled"]["const"] is False

def test_source_catalog_never_grants_access():
    catalog = read(CATALOG_PATH)
    assert catalog["record_type"] == "SOURCE_ONLY_DOMAIN_PACK_CATALOG"
    assert catalog["operational_status"] == "NO_GO"
    assert catalog["schema_version"] == "1.0.0"
    assert catalog["extension_contract"] == {
        "industry_count_limit": None,
        "accepts_new_sector_ids": True,
        "requires_source_review": True,
        "required_server_side_admission": True,
        "production_enabled": False,
    }
    assert len(catalog["profiles"]) >= 12
    assert len(catalog["shared_capability_ids"]) == 10
    assert len(set(catalog["shared_capability_ids"])) == 10
    ids = [entry["id"] for entry in catalog["profiles"]]
    assert len(ids) == len(set(ids))
    assert "custom_operations" in ids
    for p in catalog["profiles"]:
        assert re.fullmatch(r"[a-z][a-z0-9_]{2,55}", p["id"])
        assert p["status"] == "DESIGN_ONLY"
        assert p["enabled"] is False
        assert p["production_ready"] is False
        assert p["risk_tier"] in {"STANDARD", "ELEVATED", "REGULATED"}
        assert 3 <= len(p["label"]) <= 90
        assert 3 <= len(p["sector_group"]) <= 60
        assert 1 <= len(p["use_cases"]) <= 5
        assert all(8 <= len(c) <= 140 for c in p["use_cases"])
        assert len(p["use_cases"]) == len(set(p["use_cases"]))
        assert len(p["capability_refs"]) == len(set(p["capability_refs"]))
        assert 2 <= len(p["capability_refs"]) <= 10
        assert set(p["capability_refs"]) <= set(catalog["shared_capability_ids"])
        assert len(p["data_exclusions"]) >= 1
        assert all(len(x) >= 5 for x in p["data_exclusions"])
        assert len(p["required_reviews"]) == len(set(p["required_reviews"]))
        assert 2 <= len(p["required_reviews"]) <= 10
        assert set(p["required_reviews"]) <= REVIEW_TYPES
        assert {"IDENTITY_TENANT", "SECURITY_ACCEPTANCE", "HUMAN_APPROVAL"} <= set(p["required_reviews"])
        if p["risk_tier"] == "REGULATED":
            assert {"DOMAIN_SPECIALIST", "LEGAL_REGULATORY", "DATA_PROTECTION"} <= set(p["required_reviews"])

def test_architecture_explicitly_preserves_prior_contracts():
    doc = DOC_PATH.read_text("utf-8")
    for path in (
        "docs/registry/capabilities.csv",
        "docs/registry/engineering-capabilities.v1.json",
        "docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json",
        "contracts/domains/v1/cross_sector_workflow_contract.v1.json",
        "docs/p2-062-unified-workspace-ui.md",
    ):
        assert (ROOT / path).is_file(), path
        assert path in doc
    assert "five-industry limit" in doc
    assert "No new card, route, or feature toggle is authorized in PR #132" in doc
    assert "NO-GO" in doc or "NO_GO" in doc
    assert "human" in doc.lower()
    assert "no merge/deploy" in doc.lower()

def test_profile_manifest_has_no_execution_bypass_fields():
    content = CATALOG_PATH.read_text("utf-8")
    forbidden = (
        '"api_key"', '"access_token"', '"client_secret"',
        '"organization_id"', '"service_endpoint"',
        '"execution_enabled": true', '"operational_status": "GO"',
        '"production_ready": true', '"enabled": true',
        '"grant_scopes"', '"run_now"', '"tenant_id"',
    )
    for token in forbidden:
        assert token not in content, token

def test_catalog_is_only_source_metadata_and_not_legacy_permission_catalog():
    legacy = (ROOT / "docs/registry/capabilities.csv").read_text("utf-8")
    assert legacy.strip()
    old_cross_sector = read(ROOT / "contracts/domains/v1/cross_sector_workflow_contract.v1.json")
    assert isinstance(old_cross_sector, dict)
    doc = DOC_PATH.read_text("utf-8")
    assert "independent source-only extension proposal" in doc
    assert "does not change the API registry" in doc
