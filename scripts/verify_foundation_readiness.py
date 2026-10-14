#!/usr/bin/env python3
"""Machine-readable Foundation readiness ledger (NO deployment, network or DB writes).

A "verified" declaration in this source ledger is NOT cryptographic proof of
real-world operation. Release still requires independent evidence inspection,
owner approval, and a separately enforced GitHub/cloud change policy.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "operational-core" / "FOUNDATION_EXIT_EVIDENCE.json"
DEFAULT_REPORT = ROOT / ".buildlog" / "validation" / "foundation-readiness.json"
IDS = tuple("F%02d" % n for n in range(1, 10))
EXTERNAL = set(IDS[3:])


def evaluate(data: dict) -> dict:
    problems = []
    checks = data.get("checks") if isinstance(data, dict) else None
    if not isinstance(checks, list) or len(checks) != 9:
        return {"result": "INVALID", "verified": 0, "total": 9,
                "blockers": ["Expected exactly nine Foundation gates"]}
    if (data.get("schema_version") != 1 or
        data.get("phase") != "01-foundation" or
        data.get("policy") != "NO_GO_UNTIL_ALL_NINE_VERIFIED"):
        problems.append("Foundation release policy metadata invalid")
    ids = [x.get("id") for x in checks if isinstance(x, dict)]
    if ids != list(IDS):
        problems.append("Foundation gate IDs must be ordered F01-F09 and unique")
    verified = 0
    blockers = []
    for index, gate in enumerate(checks):
        if not isinstance(gate, dict):
            problems.append(f"Invalid gate #{index + 1}")
            continue
        ident = gate.get("id", "?")
        status = gate.get("status")
        if status not in ("verified", "blocked"):
            problems.append(f"{ident}: invalid status")
            continue
        reason = gate.get("reason")
        if not isinstance(reason, str) or len(reason.strip()) < 15:
            problems.append(f"{ident}: missing meaningful rationale")
        source_path = gate.get("source_path", "")
        if source_path:
            source = ROOT / source_path
            if not source.is_file() or not source.resolve().is_relative_to(ROOT.resolve()):
                problems.append(f"{ident}: source evidence file missing or unsafe")
        evidence = gate.get("external_evidence")
        owner = gate.get("owner_signoff")
        reviewer = gate.get("reviewer_signoff")
        if not isinstance(evidence, list):
            problems.append(f"{ident}: external evidence must be an array")
            evidence = []
        if ident in EXTERNAL and status == "verified":
            # A source branch MUST NOT silently convert unobserved operational
            # gates into PASS with an empty evidence array or a single signer.
            if not evidence or any(
                not isinstance(e, dict)
                or e.get("kind") not in ("live-provider-proof", "independent-test",
                                         "signed-approval", "pilot-measurement")
                or not isinstance(e.get("reference"), str)
                or not e.get("reference", "").startswith("https://")
                for e in evidence
            ):
                problems.append(f"{ident}: external evidence and inspectable refs required")
            if (not isinstance(owner, dict) or not owner.get("review_reference")
                or not isinstance(reviewer, dict) or not reviewer.get("review_reference")
                or owner.get("identity") == reviewer.get("identity")
                or not owner.get("identity") or not reviewer.get("identity")):
                problems.append(f"{ident}: distinct owner and independent reviewer signoffs required")
        if status == "verified":
            verified += 1
        else:
            blockers.append({"id": ident, "title": gate.get("title", ident),
                             "reason": reason})
    result = "INVALID" if problems else ("RELEASE_REVIEW_REQUIRED" if verified == 9 else "NO_GO")
    return {
        "schema_version": 1, "phase": "01-foundation",
        "result": result, "verified": verified, "total": 9,
        "blockers": blockers, "integrity_errors": problems,
        "live_operations_automatically_verified": False,
        "release_authorized": False,
        "deployment_performed": False,
        "external_evidence_requires_independent_review": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    try:
        status = evaluate(json.loads(SOURCE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        status = {"result": "INVALID", "verified": 0, "total": 9,
                  "integrity_errors": ["Cannot load Foundation evidence register"],
                  "blockers": [], "release_authorized": False}
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    except OSError:
        print("ERROR: Could not save Foundation evidence result", file=sys.stderr)
        return 1
    print(f"Foundation readiness: {status['result']} ({status['verified']}/9 documented)")
    for blocker in status.get("blockers", []):
        print(f"- {blocker['id']}: {blocker['title']}")
    for problem in status.get("integrity_errors", []):
        print(f"ERROR: {problem}", file=sys.stderr)
    if status["result"] == "INVALID":
        return 1
    if args.require_complete:
        # There is intentionally no automated GO path: 9/9 is a
        # request for final owner-controlled independent release review.
        if status["result"] != "RELEASE_REVIEW_REQUIRED":
            print("RELEASE BLOCKED: Foundation exit evidence incomplete", file=sys.stderr)
            return 1
        print("RELEASE BLOCKED: independent live evidence review and owner authorization required",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
