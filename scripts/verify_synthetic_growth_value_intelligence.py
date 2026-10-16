#!/usr/bin/env python3
"""P2-03m read-only, source-only value intelligence evidence generator."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_value_intelligence import (
    build_committed_value_report, validate_value_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="CONTRIBUTION",
                        choices=("CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"))
    parser.add_argument("--report", help="Write deterministic internal engineering evidence")
    args = parser.parse_args()
    report = build_committed_value_report(goal=args.goal)
    if not validate_value_evidence(report):
        raise SystemExit("FAIL: inconsistent business-value evidence")
    businesses = report["businesses"]
    if not (len(businesses) == 2
            and all(not b["comparison"]["profit_or_roi_proven"] for b in businesses)
            and all(not b["workflow_effectiveness"]["causal_effect_verified"] for b in businesses)
            and report["messages_sent"] == 0
            and report["external_provider_calls"] == 0
            and report["actual_subscription_charges"] == 0):
        raise SystemExit("FAIL: non-operational business-value constraints")
    if args.report:
        location = Path(args.report)
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n",
                            encoding="utf-8")
    print(json.dumps({
        "result": "PASS_SOURCE_ONLY",
        "milestone": report["milestone"],
        "goal": report["goal"],
        "workspaces": [b["workspace"] for b in businesses],
        "contribution_gaps": [b["modeled_gap_to_target"] for b in businesses],
        "provider_calls": report["external_provider_calls"],
        "messages_sent": report["messages_sent"],
        "billing_charges": report["actual_subscription_charges"],
        "evidence_sha256": report["evidence_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
