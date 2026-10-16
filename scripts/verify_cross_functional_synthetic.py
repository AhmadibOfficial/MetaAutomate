#!/usr/bin/env python3
"""Local synthetic retail/wholesale cross-functional preview; no runtime API."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from app.synthetic_business_flow import SyntheticWorkflowError, read_committed_demo  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", choices=["all", "retail", "wholesale"], default="all")
    parser.add_argument("--report", help="Optional local report JSON output")
    args = parser.parse_args()
    try:
        result = read_committed_demo(sector=args.sector)
    except (SyntheticWorkflowError, ValueError) as exc:
        print(f"FAIL_SYNTHETIC_PREVIEW: {exc}", file=sys.stderr)
        return 1
    if args.report:
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = {
        "result": "PASS_SYNTHETIC_PROPOSALS_ONLY",
        "real_execution_authorized": False,
        "operational_status": result["operational_status"],
        "sectors": [x["sector"] for x in result["scenarios"]],
        "draft_orders": sum(x["totals"]["draft_orders"] for x in result["scenarios"]),
        "unsent_followups": sum(x["totals"]["unsent_customer_followups"] for x in result["scenarios"]),
        "finance_postings": 0,
        "stock_mutations": 0,
        "customer_actions": 0,
        "evidence_sha256": result["evidence_sha256"]
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
