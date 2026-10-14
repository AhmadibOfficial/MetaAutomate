#!/usr/bin/env python3
"""Phase 02 operational evidence assessment, never an authorization service.

This validates declared source-ledger structure; it cannot authenticate
reviewers, GitHub branch policies, hosting, real IdPs, provider receipts or
customer consent. Even 12 submitted evidence bundles require independent
live verification and a separate explicit human release decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = ROOT / "docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
SOURCE = ROOT / "docs/operational-core/PHASE02_EXIT_EVIDENCE.json"
REPORT = ROOT / "artifacts/validation/phase02-operational-exit.json"
GATES = tuple(f"P2-G{n:02}" for n in range(1, 13))
EXTERNAL_EVIDENCE_KINDS = frozenset((
    "independent-review", "provider-authorization", "staging-validation",
    "provider-receipt", "recovery-drill", "pilot-measurement",
    "policy-enforcement", "owner-release-authorization",
))
REQUIRED_KEYS = frozenset((
    "id", "title", "criteria", "status", "owner_attestation",
    "independent_reviewer_attestation", "evidence", "blocker",
))


def _valid_attestation(value: object) -> bool:
    return (
        type(value) is dict
        and set(value) == {"identity", "review_reference"}
        and type(value.get("identity")) is str
        and len(value["identity"].strip()) >= 3
        and type(value.get("review_reference")) is str
        and value["review_reference"].startswith("https://")
        and len(value["review_reference"]) <= 1024
    )


def assess(foundation: object, ledger: object) -> dict[str, object]:
    errors: list[str] = []
    unverified: list[dict[str, str]] = []

    if type(foundation) is not dict or type(foundation.get("checks")) is not list:
        errors.append("F01-F09 foundation register missing")
        checks = []
    else:
        checks = foundation["checks"]
    foundation_ids = [
        c.get("id") if type(c) is dict else None for c in checks
    ]
    if foundation_ids != [f"F{i:02}" for i in range(1, 10)]:
        errors.append("Foundation gate IDs/order must be F01-F09")
    foundation_verified = sum(
        type(c) is dict and c.get("status") == "verified" for c in checks
    )
    if foundation_verified < 0 or foundation_verified > 9:
        errors.append("Invalid foundation verified gate count")

    if type(ledger) is not dict:
        errors.append("Operational Phase 02 ledger missing")
        ledger = {}
    if (
        ledger.get("schema_version") != 1
        or ledger.get("phase") != "02-operational"
        or ledger.get("product") != "metaautomate"
        or ledger.get("policy") != "EVIDENCE_ONLY_NO_AUTOMATED_GO"
    ):
        errors.append("Phase 02 NO-GO policy metadata invalid")
    for field, expected in (
        ("release_authorized", False),
        ("execution_authorized", False),
        ("commercial_pilot_authorized", False),
        ("no_autonomous_merging", True),
        ("no_autonomous_staging", True),
        ("provider_reads_performed", False),
        ("staging_provisioned", False),
    ):
        if ledger.get(field) is not expected:
            errors.append(f"Unverified source authority claim: {field}")
    if ledger.get("repo_visibility") != "private":
        errors.append("Private source repository constraint changed")
    if ledger.get("budget_ceiling_authorized") is not False:
        errors.append("Unverified staging budget authorization")

    controls = ledger.get("github_protection_observation")
    if (
        type(controls) is not dict
        or controls.get("observation") != "UNVERIFIED"
        or "403" not in str(controls.get("read_permission_response", ""))
    ):
        errors.append("GitHub enforcement must remain unverified without authenticated provider proof")

    gates = ledger.get("gates")
    if type(gates) is not list:
        gates = []
    if [g.get("id") if type(g) is dict else None for g in gates] != list(GATES):
        errors.append("Expected exactly 12 unique ordered Phase 02 gates")
    for index, gate in enumerate(gates):
        if type(gate) is not dict:
            errors.append(f"Invalid gate at index {index}")
            continue
        ident = gate.get("id", f"P2-G?{index}")
        if set(gate) != REQUIRED_KEYS:
            errors.append(f"{ident}: unauthorized/missing gate fields")
        if (
            type(gate.get("title")) is not str
            or len(gate["title"].strip()) < 8
            or type(gate.get("criteria")) is not str
            or len(gate["criteria"].strip()) < 15
        ):
            errors.append(f"{ident}: missing meaningful acceptance criteria")
        status = gate.get("status")
        if status not in ("blocked", "evidence-submitted"):
            errors.append(f"{ident}: invalid gate status, no self-asserted verified option")
            status = "blocked"
        evidence = gate.get("evidence")
        if type(evidence) is not list:
            errors.append(f"{ident}: invalid evidence list")
            evidence = []
        owner = gate.get("owner_attestation")
        reviewer = gate.get("independent_reviewer_attestation")
        if status == "blocked":
            if (evidence or owner is not None or reviewer is not None
                    or type(gate.get("blocker")) is not str
                    or not gate["blocker"].strip()):
                errors.append(f"{ident}: blocked gate must have rationale but no accepted attestations")
        if status == "evidence-submitted":
            if not _valid_attestation(owner) or not _valid_attestation(reviewer):
                errors.append(f"{ident}: owner and independent reviewer reference required")
            elif owner["identity"] == reviewer["identity"]:
                errors.append(f"{ident}: reviewer must differ from owner")
            if not evidence or len(evidence) > 12 or any(
                type(item) is not dict
                or set(item) != {"kind", "reference", "sha256"}
                or item.get("kind") not in EXTERNAL_EVIDENCE_KINDS
                or type(item.get("reference")) is not str
                or not item["reference"].startswith("https://")
                or len(item["reference"]) > 1024
                or type(item.get("sha256")) is not str
                or len(item["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in item["sha256"])
                for item in evidence
            ):
                errors.append(f"{ident}: inspectable external evidence references required")
        unverified.append({
            "id": str(ident),
            "status": str(status),
            "reason": "UNVERIFIED_EXTERNAL_EVIDENCE"
                if status == "evidence-submitted"
                else str(gate.get("blocker") or "Not accepted"),
        })

    status = (
        "INVALID" if errors else
        "EXTERNAL_REVIEW_REQUIRED"
        if foundation_verified == 9 and all(
            type(g) is dict and g.get("status") == "evidence-submitted"
            for g in gates
        ) else "NO_GO"
    )
    return {
        "schema_version": 1,
        "assessment": "phase02-operational-exit",
        "status": status,
        "foundation_verified": foundation_verified,
        "foundation_required": 9,
        "submitted_phase02_gate_count": sum(
            type(g) is dict and g.get("status") == "evidence-submitted"
            for g in gates
        ),
        "phase02_total_gates": len(GATES),
        "gates": unverified,
        "integrity_errors": errors,
        "external_evidence_authenticated": False,
        "independent_security_review_verified": False,
        "private_branch_protection_verified": False,
        "real_tenant_identity_verified": False,
        "real_provider_authorized": False,
        "live_recovery_verified": False,
        "real_customer_pilot_verified": False,
        "production_release_authorized": False,
        "commercial_pilot_authorized": False,
        "provider_execution_performed": False,
        "staging_provisioned": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--require-production-go", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = assess(
            json.loads(FOUNDATION.read_text(encoding="utf-8")),
            json.loads(SOURCE.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError):
        result = assess(None, None)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"P2_OPERATIONAL_STATUS={result['status']}; "
        f"FOUNDATION={result['foundation_verified']}/9; "
        f"SUBMITTED={result['submitted_phase02_gate_count']}/12; "
        "EXECUTION_AUTHORIZED=false"
    )
    for error in result["integrity_errors"]:
        print("INTEGRITY_ERROR: " + error, file=sys.stderr)
    if result["status"] == "INVALID":
        return 2
    if args.require_production_go:
        # Deliberate hard stop. This program has no trusted external identity
        # or review service and must NEVER issue a production GO from JSON.
        print("PRODUCTION_RELEASE=DENIED: independent live evidence and "
              "explicit owner approval are mandatory", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
