#!/usr/bin/env python3
"""Read-only synthetic Growth Autopilot source evidence, not client automation."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import (  # noqa: E402
    SyntheticGrowthError, read_committed_growth_demo,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", choices=["all", "academy_demo", "bespoke_demo"],
                   default="all")
    p.add_argument("--report", help="Optional synthetic JSON report; no external output")
    args = p.parse_args()
    try:
        result = read_committed_growth_demo(workspace=args.workspace)
    except (OSError, ValueError, SyntheticGrowthError) as exc:
        print(f"DENY_SYNTHETIC_GROWTH_PREVIEW: {exc}", file=sys.stderr)
        return 1
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": "PASS_SOURCE_AUTOMATION_PROPOSALS_ONLY",
        "operational_status": result["operational_status"],
        "workspace_summaries": [{
            "workspace": b["workspace"], "modeled_contribution_demo_credits":
                b["financial_summary"]["modeled_contribution_after_spend_demo_credits"],
            "drafts": b["totals"]["drafts_requiring_review"],
            "suppressed": b["totals"]["suppressed_by_provider"] +
                          b["totals"]["suppressed_by_consent"],
            "outbound_actions": b["totals"]["external_actions"]
        } for b in result["businesses"]],
        "real_customer_data": False,
        "social_publications": 0, "subscriptions_charged": 0,
        "attributed_real_revenue": 0,
        "evidence_sha256": result["evidence_sha256"]
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
