#!/usr/bin/env python3
"""Fail-closed, stdlib-only validation of the source-only engineering capability inventory.

The manifest describes development maturity, NOT the authority to run anything.
It never seeds PostgreSQL, contacts providers, enables capabilities or deploys services.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "docs/registry/engineering-capabilities.v1.json"
SOURCE_CATALOG = "docs/registry/capabilities.csv"
FOUNDATION = "docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
VALID_MATURITY = {"VISION", "SOURCE_CANDIDATE", "SOURCE_TESTED", "LOCAL_SYNTHETIC_DEMO"}
VALID_KINDS = {"technology_area", "platform_system"}
VALID_EVIDENCE = {"source_reference", "test_definition", "gate_record"}
VALID_RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
EXPECTED_LEGACY_COUNT = 33
MANIFEST_FIELDS = {
    "schema_version", "registry_id", "as_of_date", "purpose", "relationship",
    "release_boundary", "maturity_definitions", "security_control_definitions", "entries",
}
RELATIONSHIP_FIELDS = {"existing_catalog", "existing_definition_schema", "contract"}
RELEASE_FIELDS = {
    "foundation_evidence", "required_policy", "operational_authorization",
    "all_capabilities_disabled", "reference_deploy",
}
ENTRY_FIELDS = {
    "id", "kind", "name", "maturity", "operational_status", "implementation_scope",
    "modules", "verification_evidence", "security_requirements", "depends_on",
    "catalog_ids", "unmet_release_gates", "risk_class", "known_limitations",
    "next_acceptance",
}
EXPECTED_TECHNOLOGY = {
    "CAP-AI", "CAP-MEDIA", "CAP-SOCIAL", "CAP-SOFTWARE", "CAP-SECURITY",
    "CAP-DATA", "CAP-CLOUD", "CAP-BUSINESS", "CAP-ISLAMIC",
}
EXPECTED_PLATFORM = {
    "SYS-OBJECTIVES", "SYS-PLANNING", "SYS-ORCHESTRATION", "SYS-REGISTRY",
    "SYS-DATA", "SYS-CREATION", "SYS-VERIFICATION", "SYS-INTEGRATIONS",
    "SYS-IDENTITY", "SYS-IMPROVEMENT",
}


def load_sources(root: Path = ROOT) -> tuple[dict, list[dict], dict]:
    manifest = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    with (root / SOURCE_CATALOG).open(newline="", encoding="utf-8-sig") as f:
        catalog = list(csv.DictReader(f))
    foundation = json.loads((root / FOUNDATION).read_text(encoding="utf-8"))
    return manifest, catalog, foundation


def _file(root: Path, value: str) -> bool:
    """Only existing regular files inside the repository count as path evidence."""
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        return False
    p = Path(value)
    if any(part in (".", "..") for part in p.parts):
        return False
    try:
        resolved = (root / p).resolve(strict=True)
        return resolved.is_relative_to(root.resolve()) and resolved.is_file()
    except (ValueError, OSError):
        return False


def validate(manifest: dict, catalog: list[dict], foundation: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["Manifest is not an object"]
    unexpected = set(manifest) - MANIFEST_FIELDS
    missing = MANIFEST_FIELDS - set(manifest)
    if unexpected or missing:
        errors.append(f"Unexpected/missing manifest fields: {sorted(unexpected)} / {sorted(missing)}")
    if manifest.get("schema_version") != "1.0.0":
        errors.append("Schema version must be 1.0.0")
    if manifest.get("registry_id") != "metaautomate-engineering-capability-registry":
        errors.append("Registry identity mismatch")
    rel = manifest.get("relationship", {})
    rb = manifest.get("release_boundary", {})
    if not isinstance(rel, dict) or set(rel) != RELATIONSHIP_FIELDS:
        errors.append("Unexpected/missing relationship fields")
        rel = {} if not isinstance(rel, dict) else rel
    if not isinstance(rb, dict) or set(rb) != RELEASE_FIELDS:
        errors.append("Unexpected/missing release boundary fields")
        rb = {} if not isinstance(rb, dict) else rb
    if rel.get("existing_catalog") != SOURCE_CATALOG or not _file(root, SOURCE_CATALOG):
        errors.append("Existing draft catalog linkage is missing")
    if rel.get("existing_definition_schema") != "docs/registry/capability.schema.json" or not _file(root, "docs/registry/capability.schema.json"):
        errors.append("Existing registry definition schema linkage is missing")
    if not _file(root, "docs/registry/engineering-capabilities.v1.schema.json"):
        errors.append("Engineering JSON Schema is missing")
    if rb.get("foundation_evidence") != FOUNDATION or rb.get("required_policy") != "NO_GO_UNTIL_ALL_NINE_VERIFIED":
        errors.append("Foundation gate policy reference mismatch")
    if rb.get("operational_authorization") != "NO_GO" or rb.get("all_capabilities_disabled") is not True:
        errors.append("Engineering registry cannot authorize activation or operation")
    if foundation.get("policy") != "NO_GO_UNTIL_ALL_NINE_VERIFIED":
        errors.append("Foundation evidence policy mismatch")

    checks = foundation.get("checks", [])
    if not isinstance(checks, list):
        return errors + ["Foundation checks must be an array"]
    actual_ids = [x.get("id") for x in checks]
    if len(checks) != 9 or set(actual_ids) != {f"F{i:02d}" for i in range(1, 10)}:
        errors.append("Foundation evidence must retain all nine unique gate IDs")
    blocked = {x.get("id") for x in checks if x.get("status") != "verified"}
    # A source-only inventory must NEVER treat the foundation as GO.
    if not blocked:
        errors.append("All foundation gates appear verified; require a separate release review")
    if any(x.get("status") not in {"verified", "blocked"} for x in checks):
        errors.append("Unrecognized foundation evidence gate status")

    controls = manifest.get("security_control_definitions")
    if not isinstance(controls, dict) or not controls or any(not v for v in controls.values()):
        errors.append("Security control dictionary missing")
        controls = {}
    maturity_definitions = manifest.get("maturity_definitions", {})
    if not isinstance(maturity_definitions, dict) or set(maturity_definitions) != VALID_MATURITY:
        errors.append("Maturity definitions are incomplete")

    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return errors + ["Entries must be an array"]
    ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    if len(ids) != len(entries) or len(ids) != len(set(ids)):
        errors.append("Duplicate or invalid engineering capability IDs")
    got_tech = {x.get("id") for x in entries if isinstance(x, dict) and x.get("kind") == "technology_area"}
    got_sys = {x.get("id") for x in entries if isinstance(x, dict) and x.get("kind") == "platform_system"}
    if got_tech != EXPECTED_TECHNOLOGY or got_sys != EXPECTED_PLATFORM:
        errors.append("Nine technology areas and ten platform systems must be covered")

    catalog_ids = {row.get("capability_id") for row in catalog}
    if len(catalog) != EXPECTED_LEGACY_COUNT or len(catalog) != len(catalog_ids) or any(row.get("lifecycle_status") != "DRAFT" for row in catalog):
        errors.append("Legacy catalog must preserve exactly 33 unique disabled DRAFT entries")
    referenced: list[str] = []
    graph: dict[str, list[str]] = {}
    idset = set(ids)
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Non-object entry")
            continue
        key = str(entry.get("id", "<missing>"))
        extra_fields = set(entry) - ENTRY_FIELDS
        missing_fields = ENTRY_FIELDS - set(entry)
        if extra_fields or missing_fields:
            errors.append(f"{key}: unexpected/missing entry fields: {sorted(extra_fields)} / {sorted(missing_fields)}")
        if not re.fullmatch(r"(CAP|SYS)-[A-Z]+", key):
            errors.append(f"{key}: invalid stable engineering ID")
        if entry.get("kind") not in VALID_KINDS:
            errors.append(f"{key}: unknown kind")
        maturity = entry.get("maturity")
        if maturity not in VALID_MATURITY:
            errors.append(f"{key}: invalid maturity")
        if entry.get("operational_status") != "NO_GO":
            errors.append(f"{key}: engineering maturity cannot grant real execution")
        if entry.get("risk_class") not in VALID_RISKS:
            errors.append(f"{key}: invalid risk class")
        if not all(isinstance(entry.get(x), str) and entry[x].strip() for x in ("name", "implementation_scope", "known_limitations", "next_acceptance")):
            errors.append(f"{key}: missing scope, limitations or next acceptance")
        gates = entry.get("unmet_release_gates")
        if not isinstance(gates, list) or set(gates) != blocked or len(gates) != len(blocked):
            errors.append(f"{key}: unmet gates must equal the authoritative blocked foundation gates")
        requirements = entry.get("security_requirements")
        if not isinstance(requirements, list) or len(requirements) < 2 or len(requirements) != len(set(requirements)) or not set(requirements).issubset(controls):
            errors.append(f"{key}: security controls invalid")
        dependencies = entry.get("depends_on")
        if not isinstance(dependencies, list) or len(dependencies) != len(set(dependencies)) or any(d not in idset or d == key for d in dependencies):
            errors.append(f"{key}: invalid dependencies")
        else:
            graph[key] = dependencies
        catalog_refs = entry.get("catalog_ids")
        if not isinstance(catalog_refs, list) or len(catalog_refs) != len(set(catalog_refs)):
            errors.append(f"{key}: invalid legacy catalog mapping")
        else:
            referenced.extend(catalog_refs)
        modules = entry.get("modules")
        proofs = entry.get("verification_evidence")
        if not isinstance(modules, list) or not isinstance(proofs, list):
            errors.append(f"{key}: modules/evidence must be arrays")
            continue
        if maturity == "VISION" and (modules or proofs):
            errors.append(f"{key}: VISION must not claim implementation evidence")
        if maturity != "VISION" and (not modules or not proofs):
            errors.append(f"{key}: source maturity requires actual modules and test definitions")
        if maturity in {"SOURCE_TESTED", "LOCAL_SYNTHETIC_DEMO"} and not any(x.get("kind") == "test_definition" for x in proofs if isinstance(x, dict)):
            errors.append(f"{key}: tested maturity needs a test definition")
        for module in modules:
            if not isinstance(module, dict) or not _file(root, module.get("path")) or module.get("scope") != "source_reference":
                errors.append(f"{key}: invalid or missing source module")
        for proof in proofs:
            if not isinstance(proof, dict) or proof.get("kind") not in VALID_EVIDENCE or not _file(root, proof.get("path")) or not isinstance(proof.get("note"), str) or not proof["note"].strip():
                errors.append(f"{key}: invalid or missing evidence path")

    counts = Counter(referenced)
    if set(counts) != catalog_ids or any(n != 1 for n in counts.values()):
        errors.append("Existing CSV catalog must be crosswalked exactly once, with no orphans or duplicates")
    if any(code not in catalog_ids for code in referenced):
        errors.append("Engineering crosswalk references nonexistent legacy capabilities")

    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"{node}: dependency cycle")
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Write a local JSON validation report (no network or DB)")
    args = parser.parse_args()
    registry, catalog, foundation = load_sources()
    errors = validate(registry, catalog, foundation)
    report = {
        "result": "PASS_SOURCE_INVENTORY_ONLY" if not errors else "FAIL",
        "real_execution_authorized": False,
        "operational_release": "NO_GO",
        "engineering_entries": len(registry.get("entries", [])),
        "legacy_catalog_entries": len(catalog),
        "foundation_verified": sum(x.get("status") == "verified" for x in foundation["checks"]),
        "foundation_total": len(foundation["checks"]),
        "errors": errors,
    }
    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
