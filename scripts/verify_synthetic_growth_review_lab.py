#!/usr/bin/env python3
"""P2-03l synthetic source-only review-lifecycle evidence."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_review_lab import run_committed_review_lab, validate_review_evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", help="Write internal source evidence report")
    args = parser.parse_args()
    workflow = {
        "schema_version": 1,
        "workspace": "academy_demo",
        "goal": "CONTRIBUTION",
        "steps": [
            {"intent_id":"SIM-INTENT-REVIEW1", "action":"REVIEW_ACCEPT",
             "actor_role":"REVIEWER", "source_event":"DEMO-EVENT-EDU03"},
            {"intent_id":"SIM-INTENT-REVIEW1", "action":"REVIEW_ACCEPT",
             "actor_role":"REVIEWER", "source_event":"DEMO-EVENT-EDU03"},
            {"intent_id":"SIM-INTENT-REVOKE1", "action":"REVOKE_CONSENT",
             "actor_role":"OWNER", "source_event":"DEMO-EVENT-EDU03"},
            {"intent_id":"SIM-INTENT-ATTEMPT", "action":"REVIEW_ACCEPT",
             "actor_role":"OWNER", "source_event":"DEMO-EVENT-EDU04"},
            {"intent_id":"SIM-INTENT-NATIVE", "action":"ACK_PROVIDER_OWNERSHIP",
             "actor_role":"OWNER", "source_event":"DEMO-EVENT-EDU02"},
        ],
    }
    raw = json.dumps(workflow, sort_keys=True, separators=(",", ":")).encode("ascii")
    report = run_committed_review_lab(raw)
    if not validate_review_evidence(report):
        raise SystemExit("Review audit evidence validation failed")
    if not (report["ignored_exact_intent_replays"] == 1
            and report["state_totals"]["SUPPRESSED_PROVIDER_OWNS"] == 1
            and report["real_actions_sent"] == 0
            and report["real_approvals_recorded"] == 0
            and report["subscriptions_started"] == 0):
        raise SystemExit("Synthetic safety constraints failed")
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({
        "status":"PASS_SOURCE_ONLY",
        "milestone":report["milestone"],
        "audit_chain_valid":report["audit_chain_valid"],
        "review_events":len(report["review_audit"]),
        "ignored_exact_replays":report["ignored_exact_intent_replays"],
        "state_totals":report["state_totals"],
        "external_actions":report["real_actions_sent"],
        "evidence_sha256":report["evidence_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
