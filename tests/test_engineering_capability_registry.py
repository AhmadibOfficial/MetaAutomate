"""Fail-closed engineering registry / legacy-draft crosswalk checks (no database)."""
import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verify_engineering_capability_registry", ROOT / "scripts" / "verify_engineering_capability_registry.py"
)
registry_validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(registry_validator)


def sources():
    return registry_validator.load_sources(ROOT)


def check(registry, catalog, foundation):
    return registry_validator.validate(registry, catalog, foundation, ROOT)


def test_complete_registry_and_authoritative_draft_crosswalk():
    manifest, catalog, foundation = sources()
    assert check(manifest, catalog, foundation) == []
    assert len(manifest["entries"]) == 19
    assert len(catalog) == 33
    assert {x["maturity"] for x in manifest["entries"]} == {
        "VISION", "SOURCE_CANDIDATE", "SOURCE_TESTED", "LOCAL_SYNTHETIC_DEMO"
    }
    assert sum(g["status"] == "verified" for g in foundation["checks"]) == 3
    assert all(x["operational_status"] == "NO_GO" for x in manifest["entries"])
    assert all(set(x["unmet_release_gates"]) == {"F04", "F05", "F06", "F07", "F08", "F09"}
               for x in manifest["entries"])


def test_release_flag_cannot_enable_operations():
    m, c, f = sources()
    m["release_boundary"]["operational_authorization"] = "GO"
    assert any("cannot authorize" in e for e in check(m, c, f))


def test_individual_capability_cannot_be_promoted():
    m, c, f = sources()
    m["entries"][0]["operational_status"] = "ACTIVE"
    assert any("cannot grant real execution" in e for e in check(m, c, f))


def test_missing_legacy_catalog_link_is_rejected():
    m, c, f = sources()
    entry = next(x for x in m["entries"] if "BIZ-011" in x["catalog_ids"])
    entry["catalog_ids"].remove("BIZ-011")
    assert any("crosswalked exactly once" in e for e in check(m, c, f))


def test_duplicate_legacy_catalog_mapping_is_rejected():
    m, c, f = sources()
    m["entries"][0]["catalog_ids"].append("CORE-001")
    assert any("crosswalked exactly once" in e for e in check(m, c, f))


def test_missing_or_traversal_evidence_cannot_pass():
    m, c, f = sources()
    m["entries"][0]["modules"][0]["path"] = "../../etc/passwd"
    assert any("missing source module" in e for e in check(m, c, f))


def test_dependency_cycles_are_blocked():
    m, c, f = sources()
    node = next(x for x in m["entries"] if x["id"] == "SYS-IDENTITY")
    node["depends_on"] = ["SYS-REGISTRY"]
    assert any("dependency cycle" in e for e in check(m, c, f))


def test_blocked_foundation_gate_cannot_be_hidden():
    m, c, f = sources()
    next(x for x in f["checks"] if x["id"] == "F09")["status"] = "verified"
    assert any("unmet gates" in e for e in check(m, c, f))


def test_vision_cannot_claim_test_proof():
    m, c, f = sources()
    entry = next(x for x in m["entries"] if x["id"] == "CAP-ISLAMIC")
    entry["verification_evidence"] = [{
        "path": "tests/test_seed_registry.py",
        "kind": "test_definition",
        "note": "Unrelated test cannot prove a future product",
    }]
    assert any("VISION must not claim" in e for e in check(m, c, f))


def test_invalid_security_requirement_rejected():
    m, c, f = sources()
    m["entries"][0]["security_requirements"].append("DISABLE_ALL_SECURITY")
    assert any("security controls invalid" in e for e in check(m, c, f))
