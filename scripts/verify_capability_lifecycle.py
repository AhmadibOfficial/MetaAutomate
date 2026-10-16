#!/usr/bin/env python3
"""Offline capability lifecycle and evidence-upgrade preflight.

Never applies a proposed upgrade, changes the registry or grants runtime access.
A passing proposal means REVIEW REQUIRED, not source approval or operational GO.
"""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

import verify_engineering_capability_registry as registry

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = "docs/registry/capability-lifecycle-policy.v1.json"
HISTORY_PATH = "docs/registry/capability-lifecycle-history.v1.json"
BASELINE_COMMIT = "7d86f3ec1ce9b2b77a9cec9b64c6f919ca74176c"
CHANGE_TYPES = {"PROMOTE", "SCOPE_CHANGE", "EVIDENCE_REFRESH", "DOWNGRADE"}
EXPECTED_PAIRS = {
    "PROMOTE": {
        ("VISION", "SOURCE_CANDIDATE"),
        ("SOURCE_CANDIDATE", "SOURCE_TESTED"),
        ("SOURCE_CANDIDATE", "LOCAL_SYNTHETIC_DEMO"),
    },
    "SCOPE_CHANGE": {
        ("SOURCE_TESTED", "LOCAL_SYNTHETIC_DEMO"),
        ("LOCAL_SYNTHETIC_DEMO", "SOURCE_TESTED"),
    },
    "EVIDENCE_REFRESH": {(x, x) for x in registry.VALID_MATURITY},
    "DOWNGRADE": {
        ("SOURCE_TESTED", "SOURCE_CANDIDATE"),
        ("LOCAL_SYNTHETIC_DEMO", "SOURCE_CANDIDATE"),
        ("SOURCE_CANDIDATE", "VISION"),
        ("SOURCE_TESTED", "VISION"),
        ("LOCAL_SYNTHETIC_DEMO", "VISION"),
    },
}
REVIEW_FIELDS = {"decision", "review_ref", "reviewer", "decision_date", "separation_statement"}
PROPOSAL_FIELDS = {
    "capability_id", "change_type", "from_maturity", "to_maturity",
    "motivation", "after", "evidence", "dependency_assessments", "control_assessments",
}
EVIDENCE_FIELDS = {
    "positive_test_paths", "negative_test_paths", "source_paths",
    "scope_note", "known_limits", "ci_run_url",
}
CONTROL_STATES = {"SOURCE_TESTED", "DESIGNED", "UNVERIFIED"}
HISTORY_FIELDS = {"schema_version", "purpose", "baseline", "events"}
POLICY_FIELDS = {
    "schema_version", "purpose", "reference_registry", "reference_foundation",
    "operational_status", "change_types", "source_evidence_thresholds",
    "requirements", "decision_rules",
}


def load_sources(root: Path = ROOT) -> tuple[dict, dict, dict, dict, list[dict], dict]:
    manifest, catalog, foundation = registry.load_sources(root)
    policy = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    history = json.loads((root / HISTORY_PATH).read_text(encoding="utf-8"))
    return manifest, policy, history, foundation, catalog, root


def _ref_url(value: object, kind: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    base = r"^/AhmadibOfficial/MetaAutomate/"
    end = r"pull/[1-9][0-9]*$" if kind == "pr" else r"actions/runs/[1-9][0-9]*$"
    return re.fullmatch(base + end, parsed.path) is not None


def validate_policy(policy: dict) -> list[str]:
    errors = []
    if not isinstance(policy, dict) or set(policy) != POLICY_FIELDS:
        return ["Lifecycle policy has missing or unexpected top-level fields"]
    if policy["schema_version"] != "1.0.0" or policy["operational_status"] != "NO_GO":
        errors.append("Lifecycle policy must remain source-only version 1.0.0 NO_GO")
    if policy["reference_registry"] != registry.REGISTRY or policy["reference_foundation"] != registry.FOUNDATION:
        errors.append("Lifecycle policy must reference authoritative registry and Foundation evidence")
    if not isinstance(policy["change_types"], dict) or set(policy["change_types"]) != CHANGE_TYPES:
        errors.append("Lifecycle change-type set is invalid")
    else:
        for name, expected in EXPECTED_PAIRS.items():
            value = policy["change_types"][name]
            if not isinstance(value, dict) or set(value) != {"allowed_pairs"}:
                errors.append(f"{name}: change-type specification invalid")
                continue
            pairs = value["allowed_pairs"]
            if not isinstance(pairs, list) or any(not isinstance(x, list) or len(x) != 2 for x in pairs):
                errors.append(f"{name}: invalid transition pairs")
                continue
            given = [tuple(x) for x in pairs]
            if len(given) != len(expected) or set(given) != expected:
                errors.append(f"{name}: lifecycle transition policy changed without v2 review")
    thresholds = policy.get("source_evidence_thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != registry.VALID_MATURITY:
        errors.append("Evidence maturity thresholds are incomplete")
    else:
        for maturity in registry.VALID_MATURITY:
            threshold = thresholds[maturity]
            if not isinstance(threshold, dict):
                errors.append(f"{maturity}: thresholds invalid")
                continue
            if maturity == "VISION" and (threshold.get("max_modules") != 0 or threshold.get("max_proofs") != 0):
                errors.append("VISION cannot claim source evidence")
            if maturity != "VISION" and (threshold.get("min_modules", 0) < 1 or
                    threshold.get("min_proofs", 0) < 1):
                errors.append(f"{maturity}: source and proof thresholds too weak")
            if maturity in {"SOURCE_TESTED", "LOCAL_SYNTHETIC_DEMO"} and threshold.get("min_test_definitions", 0) < 1:
                errors.append(f"{maturity}: source tests required")
            if maturity == "LOCAL_SYNTHETIC_DEMO" and (threshold.get("required_control") != "EXTERNAL_ACTION_DENY" or
                    threshold.get("scope_must_declare") != "synthetic"):
                errors.append("Synthetic scope deny-control requirement removed")
    requirements = policy.get("requirements", {})
    if not isinstance(requirements, dict) or set(requirements) != {
        "proposal_positive_and_negative_tests", "per_dependency_assessment",
        "per_security_control_assessment", "manual_review_for_accepted_event",
        "scope_and_limits_required", "no_execution_or_customer_activation",
    } or any(value is not True for value in requirements.values()):
        errors.append("Mandatory lifecycle review controls cannot be waived")
    rules = policy.get("decision_rules", {})
    if not isinstance(rules, dict) or rules != {
        "proposal_result": "EVIDENCE_REVIEW_REQUIRED",
        "accepted_event_result": "SOURCE_TRACKED_NOT_OPERATIONAL",
        "review_decision": "SOURCE_REVIEWED_ONLY",
        "review_separation_statement": "NOT_OPERATIONAL_AUTHORIZATION",
    }:
        errors.append("Decision rules cannot authorize operational release")
    return errors


def validate_transition(
    before: dict, change: dict, current: dict[str, dict], policy: dict,
    root: Path = ROOT, *, require_review: bool = False
) -> list[str]:
    errors: list[str] = []
    if not isinstance(change, dict) or not PROPOSAL_FIELDS.issubset(change):
        return ["Proposal/event is missing required fields"]
    key = before.get("id")
    after = change.get("after")
    if not isinstance(after, dict):
        return [f"{key}: proposed entry is not an object"]
    if key != change.get("capability_id") or key != after.get("id"):
        errors.append(f"{key}: immutable capability ID mismatch")
    kind = change.get("change_type")
    old = before.get("maturity")
    new = after.get("maturity")
    if old != change.get("from_maturity") or new != change.get("to_maturity"):
        errors.append(f"{key}: stale/incorrect from or to maturity")
    if kind not in CHANGE_TYPES or (old, new) not in EXPECTED_PAIRS.get(kind, set()):
        errors.append(f"{key}: disallowed lifecycle transition")
    if before == after:
        errors.append(f"{key}: proposed entry has no actual source evidence or scope change")
    for field in ("id", "kind", "name", "catalog_ids"):
        if after.get(field) != before.get(field):
            errors.append(f"{key}: {field} cannot change through lifecycle v1")
    if after.get("operational_status") != "NO_GO" or before.get("operational_status") != "NO_GO":
        errors.append(f"{key}: operational status cannot change")
    if after.get("unmet_release_gates") != before.get("unmet_release_gates"):
        errors.append(f"{key}: Foundation gate state cannot change in lifecycle updates")
    if not isinstance(change.get("motivation"), str) or len(change["motivation"].strip()) < 20:
        errors.append(f"{key}: meaningful review rationale required")
    if not isinstance(after.get("known_limitations"), str) or len(after["known_limitations"].strip()) < 15:
        errors.append(f"{key}: state explicit scope limitations")
    if not isinstance(after.get("implementation_scope"), str) or len(after["implementation_scope"].strip()) < 20:
        errors.append(f"{key}: detailed implementation scope required")

    threshold = policy.get("source_evidence_thresholds", {}).get(new, {})
    modules = after.get("modules", [])
    proofs = after.get("verification_evidence", [])
    if not isinstance(modules, list) or not isinstance(proofs, list):
        return errors + [f"{key}: modules/evidence must be arrays"]
    tests = [x.get("path") for x in proofs if isinstance(x, dict) and x.get("kind") == "test_definition"]
    if len(modules) < threshold.get("min_modules", 0) or len(proofs) < threshold.get("min_proofs", 0) or len(tests) < threshold.get("min_test_definitions", 0):
        errors.append(f"{key}: insufficient implementation or test definition evidence for {new}")
    if new == "VISION" and (modules or proofs):
        errors.append(f"{key}: VISION has no implementation evidence")
    if new == "LOCAL_SYNTHETIC_DEMO":
        if "synthetic" not in (after.get("implementation_scope", "") + " " + after.get("known_limitations", "")).lower():
            errors.append(f"{key}: synthetic-only scope not disclosed")
        if "EXTERNAL_ACTION_DENY" not in after.get("security_requirements", []):
            errors.append(f"{key}: synthetic demo missing external action denial")

    ev = change.get("evidence")
    if not isinstance(ev, dict) or set(ev) != EVIDENCE_FIELDS:
        return errors + [f"{key}: evidence record missing/unexpected fields"]
    positive, negative, source = ev["positive_test_paths"], ev["negative_test_paths"], ev["source_paths"]
    if not all(isinstance(x, list) and x and len(set(x)) == len(x) for x in (positive, negative, source)):
        errors.append(f"{key}: at least one distinct positive test, negative test and source path required")
    else:
        archived = kind == "DOWNGRADE"
        defined_tests = set(tests)
        defined_modules = {x.get("path") for x in modules if isinstance(x, dict)}
        if archived:
            # Downgrade records cite prior evidence being withdrawn; it must not
            # be carried forward as implementation evidence of a VISION entry.
            defined_tests.update(
                x.get("path") for x in before.get("verification_evidence", [])
                if isinstance(x, dict) and x.get("kind") == "test_definition"
            )
            defined_modules.update(
                x.get("path") for x in before.get("modules", []) if isinstance(x, dict)
            )
        for path in positive + negative:
            if not registry._file(root, path) or path not in defined_tests:
                errors.append(f"{key}: positive/negative test not in scoped verified evidence: {path}")
        for path in source:
            if not registry._file(root, path) or path not in defined_modules:
                errors.append(f"{key}: source path is not a declared scoped module: {path}")
    if new == "VISION" and kind == "DOWNGRADE":
        # A downgrade explicitly removes claims of implementation but can still
        # cite archived tests; they are not new evidence of vision execution.
        if not source:
            errors.append(f"{key}: downgrade must identify the removed source boundary")
    if any(not isinstance(ev.get(field), str) or len(ev[field].strip()) < 12 for field in ("scope_note", "known_limits")):
        errors.append(f"{key}: scoped evidence notes missing")
    if require_review:
        if not _ref_url(ev.get("ci_run_url"), "ci"):
            errors.append(f"{key}: accepted event needs a valid CI run reference")
    elif ev.get("ci_run_url") is not None and not _ref_url(ev["ci_run_url"], "ci"):
        errors.append(f"{key}: optional CI URL is malformed")

    deps = after.get("depends_on", [])
    assessments = change.get("dependency_assessments")
    if not isinstance(deps, list) or not isinstance(assessments, list) or set(deps) != {
        x.get("id") for x in assessments if isinstance(x, dict)
    } or len(deps) != len(assessments):
        errors.append(f"{key}: every dependency requires one review")
    else:
        for assessment in assessments:
            dependency = current.get(assessment.get("id"))
            if not dependency or assessment.get("current_maturity") != dependency.get("maturity"):
                errors.append(f"{key}: dependency maturity review is stale or missing")
            if not isinstance(assessment.get("impact"), str) or len(assessment["impact"].strip()) < 12:
                errors.append(f"{key}: dependency limitation assessment missing")
            if set(assessment) != {"id", "current_maturity", "impact"}:
                errors.append(f"{key}: unexpected dependency assessment fields")

    requirements = after.get("security_requirements", [])
    controls = change.get("control_assessments")
    if not isinstance(requirements, list) or not isinstance(controls, list) or set(requirements) != {
        x.get("id") for x in controls if isinstance(x, dict)
    } or len(requirements) != len(controls):
        errors.append(f"{key}: every security control requires one review")
    else:
        for control in controls:
            if set(control) != {"id", "state", "note"} or control.get("state") not in CONTROL_STATES:
                errors.append(f"{key}: invalid control assessment")
            if not isinstance(control.get("note"), str) or len(control["note"].strip()) < 12:
                errors.append(f"{key}: control evidence notes missing")

    if require_review:
        review = change.get("review")
        if not isinstance(review, dict) or set(review) != REVIEW_FIELDS:
            errors.append(f"{key}: explicit reviewer metadata missing")
        else:
            if review.get("decision") != "SOURCE_REVIEWED_ONLY" or review.get("separation_statement") != "NOT_OPERATIONAL_AUTHORIZATION":
                errors.append(f"{key}: review cannot authorize customer or operational execution")
            if not _ref_url(review.get("review_ref"), "pr"):
                errors.append(f"{key}: accepted record requires a GitHub pull request")
            if not isinstance(review.get("reviewer"), str) or len(review["reviewer"].strip()) < 2:
                errors.append(f"{key}: named reviewer required")
            try:
                date.fromisoformat(review.get("decision_date", ""))
            except (ValueError, TypeError):
                errors.append(f"{key}: ISO decision date required")
    return errors


def evaluate(manifest: dict, policy: dict, history: dict, foundation: dict, catalog: list[dict],
             root: Path = ROOT, proposal: dict | None = None) -> tuple[list[str], dict]:
    errors = registry.validate(manifest, catalog, foundation, root)
    errors.extend(validate_policy(policy))
    if not isinstance(history, dict) or set(history) != HISTORY_FIELDS:
        return errors + ["Lifecycle history missing/unknown top-level fields"], {}
    if history.get("schema_version") != "1.0.0":
        errors.append("Lifecycle history schema must be version 1.0.0")
    baseline = history.get("baseline")
    if not isinstance(baseline, dict) or set(baseline) != {"commit", "registry_version", "entries"}:
        return errors + ["Invalid lifecycle baseline metadata"], {}
    if baseline.get("commit") != BASELINE_COMMIT or baseline.get("registry_version") != "1.0.0":
        errors.append("Baseline reference is not the accepted PR #60 source commit")
    entries = baseline.get("entries")
    if not isinstance(entries, list):
        return errors + ["Missing baseline records"], {}
    expected_ids = set(registry.EXPECTED_TECHNOLOGY | registry.EXPECTED_PLATFORM)
    if len(entries) != 19 or len({x.get("id") for x in entries if isinstance(x, dict)}) != 19 or {
        x.get("id") for x in entries if isinstance(x, dict)
    } != expected_ids:
        return errors + ["Lifecycle baseline must include the original 19 stable IDs"], {}
    if any(not isinstance(x, dict) or x.get("operational_status") != "NO_GO" for x in entries):
        return errors + ["Lifecycle baseline cannot include an operational capability"], {}
    current = {x["id"]: copy.deepcopy(x) for x in entries}
    events = history.get("events")
    if not isinstance(events, list):
        return errors + ["Lifecycle events must be a list"], current
    seen = set()
    for idx, event in enumerate(events, start=1):
        if not isinstance(event, dict) or set(event) != PROPOSAL_FIELDS | {"event_id", "review"}:
            errors.append(f"Event {idx} has missing or unknown fields")
            continue
        event_id = f"LCE-{idx:04d}"
        if event.get("event_id") != event_id or event_id in seen:
            errors.append(f"Lifecycle event IDs must be sequential: {event_id}")
        seen.add(event_id)
        capid = event.get("capability_id")
        before = current.get(capid)
        if not before:
            errors.append(f"{event_id}: unknown capability ID")
            continue
        errors.extend(validate_transition(before, event, current, policy, root, require_review=True))
        after = event.get("after")
        if isinstance(after, dict):
            current[capid] = copy.deepcopy(after)
    declared = {x["id"]: x for x in manifest.get("entries", []) if isinstance(x, dict) and "id" in x}
    if current != declared:
        mismatched = sorted(x for x in expected_ids if current.get(x) != declared.get(x))
        errors.append(f"Manifest changes require sequential accepted source lifecycle events: {mismatched}")
    if proposal is not None:
        if not isinstance(proposal, dict) or set(proposal) != PROPOSAL_FIELDS | {"proposal_schema_version", "example_only"}:
            errors.append("Proposal must contain exact source-only review fields")
        elif proposal.get("proposal_schema_version") != "1.0.0" or not isinstance(proposal.get("example_only"), bool):
            errors.append("Proposal version / example-only marker invalid")
        else:
            key = proposal.get("capability_id")
            before = current.get(key)
            if not before:
                errors.append("Proposal references unknown capability")
            else:
                errors.extend(validate_transition(before, proposal, current, policy, root))
                # Reuse all existing manifest+catalog+no-GO validators before a
                # proposed entry can be considered complete for human review.
                clone = copy.deepcopy(manifest)
                clone["entries"] = [proposal["after"] if x.get("id") == key else x for x in clone["entries"]]
                errors.extend(registry.validate(clone, catalog, foundation, root))
    return errors, current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Optional local JSON report; no runtime changes")
    parser.add_argument("--proposal", help="Offline proposal path relative to repository root")
    args = parser.parse_args()
    manifest, policy, history, foundation, catalog, root = load_sources()
    proposal = None
    if args.proposal:
        if not registry._file(root, args.proposal):
            parser.error("Proposal must be a regular file within the repository")
        proposal = json.loads((root / args.proposal).read_text(encoding="utf-8"))
    errors, current = evaluate(manifest, policy, history, foundation, catalog, root, proposal)
    result = "BLOCKED" if errors else ("EVIDENCE_REVIEW_REQUIRED" if proposal is not None else "PASS_SOURCE_LIFECYCLE_ONLY")
    output = {
        "result": result, "operational_release": "NO_GO",
        "real_execution_authorized": False, "proposal_was_applied": False,
        "capability_entries": len(current), "accepted_source_events": len(history.get("events", [])),
        "foundation_verified": sum(x.get("status") == "verified" for x in foundation.get("checks", [])),
        "foundation_total": len(foundation.get("checks", [])), "errors": errors,
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
