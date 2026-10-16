#!/usr/bin/env python3
"""Produce optional *local, synthetic-only* transportation evidence report."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_transportation import (  # noqa: E402
    SyntheticTransportationError, read_committed_synthetic_transportation
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Optional JSON evidence output path")
    parser.add_argument("--trip", choices=["DEMO-TRIP-A1", "DEMO-TRIP-B2"],
                        help="Optional fictional trip only; full fixture still validated")
    args = parser.parse_args()
    try:
        result = read_committed_synthetic_transportation(trip=args.trip)
    except (SyntheticTransportationError, OSError, ValueError) as exc:
        print(f"SYNTHETIC_TRANSPORTATION_DENIED: {exc}", file=sys.stderr)
        return 1
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": "PASS_SOURCE_SYNTHETIC_ONLY",
        "contract_status": result["cross_sector_profile_readiness"],
        "operational_release": result["operational_status"],
        "real_execution_authorized": False,
        "draft_requests": result["totals"]["draft_requests"],
        "proposed_seats": result["totals"]["proposed_seats"],
        "demo_credits_quoted_not_earned": result["totals"]["quoted_demo_credits"],
        "unsent_followups": result["totals"]["unsent_followups"],
        "posted_finance_entries": 0,
        "real_bookings_created": 0,
        "evidence_sha256": result["evidence_sha256"]
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
