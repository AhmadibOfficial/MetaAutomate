#!/usr/bin/env python3
"""Validate P2-03j committed source-only Growth Autopilot orchestration."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_orchestrator import read_committed_growth_orchestration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", choices=["all", "academy_demo", "bespoke_demo"],
                        default="all")
    parser.add_argument("--report", help="Output local synthetic JSON evidence only")
    options = parser.parse_args()
    report = read_committed_growth_orchestration(workspace=options.workspace)
    assert report["operational_status"] == "NO_GO"
    assert report["mode"] == "READ_ONLY_GOAL_ORCHESTRATION"
    assert report["integration_mode"] == "CONTRACT_ONLY"
    assert not report["external_requests_made"]
    assert not report["real_customer_subscriptions_charged"]
    assert not report["customer_activation_authorized"]
    assert not report["live_automation_available"]
    for group in report["workspaces"]:
        assert group["subscription"]["billing_active"] is False
        assert group["automation"]["messages_sent"] == 0
        assert group["automation"]["external_actions"] == 0
        assert group["automation"]["durable_replay_protection_enabled"] is False
    if options.report:
        output = Path(options.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": "PASS_SOURCE_GOAL_ORCHESTRATION_ONLY",
        "operational_status": report["operational_status"],
        "workspaces": [
            {"workspace": w["workspace"],
             "goal": w["goal"]["metric"],
             "goal_shortfall": w["goal"]["shortfall"],
             "review_proposals": w["automation"]["proposals_for_review"],
             "suppressed_proposals": w["automation"]["provider_owned_suppressions"] +
                                     w["automation"]["unconsented_suppressions"],
             "replay_previews_suppressed": len(w["automation"]["replay_previews"]),
             "external_actions": w["automation"]["external_actions"]}
            for w in report["workspaces"]
        ],
        "subscribers_activated": 0, "provider_connections_active": 0,
        "evidence_sha256": report["evidence_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
