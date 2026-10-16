#!/usr/bin/env python3
"""Offline review-metadata *hold*, not identity verification or production approval.

In a draft PR the pending marker is permitted but prominently reported.
On a main-branch push, CI's --require-owner-review fails while it remains.
This checks labels, NOT GitHub reviewer authenticity (Foundation F04 blocked).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "docs/registry/capability-lifecycle-history.v1.json"
EXPECTED_PR = "https://github.com/AhmadibOfficial/MetaAutomate/pull/67"
PENDING_REVIEWER = "PENDING_OWNER_APPROVAL_REPLACE_BEFORE_MERGE"
APPROVED_REVIEWER = "OWNER_SOURCE_REVIEW_APPROVED_PR_67"


def review_status(history: dict, *, require_owner_review: bool = False) -> dict:
    errors = []
    events = history.get("events", []) if isinstance(history, dict) else []
    if not isinstance(events, list) or not events:
        errors.append("Expected at least one lifecycle source event")
        events = []
    event = events[0] if events else {}
    review = event.get("review") if isinstance(event, dict) else None
    if not isinstance(review, dict):
        errors.append("Lifecycle source review metadata absent")
        review = {}
    if (event.get("event_id") != "LCE-0001"
            or event.get("capability_id") != "CAP-BUSINESS"
            or event.get("change_type") != "EVIDENCE_REFRESH"):
        errors.append("Transportation source event is missing/changed")
    if (review.get("decision") != "SOURCE_REVIEWED_ONLY"
            or review.get("separation_statement") != "NOT_OPERATIONAL_AUTHORIZATION"
            or review.get("review_ref") != EXPECTED_PR):
        errors.append("Source-only review reference or separation is invalid")
    reviewer = review.get("reviewer")
    pending = reviewer == PENDING_REVIEWER
    approved = reviewer == APPROVED_REVIEWER
    if not pending and not approved:
        errors.append("Owner reviewer marker is unexpected or malformed")
    if require_owner_review and not approved:
        errors.append("Owner approval still PENDING — do not merge or publish")
    result = ("BLOCKED" if errors else
              "PENDING_OWNER_APPROVAL" if pending else "SOURCE_REVIEW_METADATA_PRESENT")
    return {
        "result": result, "event_id": event.get("event_id"),
        "owner_review_recorded": bool(approved and not errors),
        "owner_identity_authentication_performed": False,
        "real_execution_authorized": False,
        "operational_release": "NO_GO",
        "metadata_is_not_signed_evidence": True,
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-owner-review", action="store_true",
                    help="Fail unless the explicit PR #67 owner review marker was recorded")
    ap.add_argument("--report", help="Optional JSON report file")
    args = ap.parse_args()
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    report = review_status(history, require_owner_review=args.require_owner_review)
    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
