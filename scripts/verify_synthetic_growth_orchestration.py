#!/usr/bin/env python3
"""P2-03j source-only evidence runner. No integration, side effects or billing."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_orchestration import build_committed_growth_work_plan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", choices=("CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"),
                        default="CONTRIBUTION")
    parser.add_argument("--workspace", choices=("all", "academy_demo", "bespoke_demo"), default="all")
    parser.add_argument("--report", help="Write deterministic internal synthetic evidence")
    args = parser.parse_args()
    report = build_committed_growth_work_plan(goal=args.goal, workspace=args.workspace)
    if args.report:
        destination = Path(args.report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS_SOURCE_ONLY",
        "goal": args.goal,
        "workspaces": [x["workspace"] for x in report["workspaces"]],
        "proposal_counts": [x["workflow_counts"] for x in report["workspaces"]],
        "external_actions": 0,
        "operational_status": "NO_GO",
        "evidence_sha256": report["evidence_sha256"],
    }, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
