#!/usr/bin/env python3
"""Build/check a public-safe, read-only P2-03j browser contract offline.

No network, secrets, external service, visitor data, payment, database or action.
The output contains only allowlisted values computed by the approved source engine.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_orchestration import build_committed_growth_work_plan  # noqa: E402

OUTPUT = ROOT / "apps/site/automation/engine-snapshot.js"
GOALS = ("CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS")


def create_contract():
    contract = {
        "schema_version": 1,
        "access": "FREE_EXPLORER_NO_ACCOUNT",
        "source": "P2-03j_GOAL_ORCHESTRATION",
        "amounts": "ILLUSTRATIVE_NOT_LIVE_USD",
        "workspaces": {},
    }
    for goal in GOALS:
        result = build_committed_growth_work_plan(goal=goal)
        assert result["non_operational_controls"]["operational_status"] == "NO_GO"
        assert result["non_operational_controls"]["provider_calls"] == 0
        for business in result["workspaces"]:
            name = business["workspace"]
            item = contract["workspaces"].setdefault(name, {"goals": {}})
            m = business["financial_summary"]
            item["goals"][goal] = {
                "metrics": {
                    "gross_sales": m["gross_sales"],
                    "variable_cost": m["variable_cost"],
                    "marketing_spend": m["marketing_spend"],
                    "modeled_contribution": m["modeled_contribution_after_marketing"],
                    "contribution_target": m["monthly_contribution_target"],
                    "contribution_shortfall": m["contribution_shortfall"],
                    "repeat_orders": m["repeat_orders"],
                    "completed_orders": m["completed_orders"],
                },
                "decisions": {
                    p["source_event"]: {
                        "state": p["state"],
                        "reason": p["review_reason"],
                    }
                    for p in business["workflow_proposals"]
                },
            }
    assert sorted(contract["workspaces"]) == ["academy_demo", "bespoke_demo"]
    for item in contract["workspaces"].values():
        assert sorted(item["goals"]) == sorted(GOALS)
        for g in item["goals"].values():
            assert len(g["decisions"]) == 6
            assert g["metrics"]["modeled_contribution"] >= 0
    return contract


def render() -> str:
    data = json.dumps(create_contract(), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True)
    return ("/* Generated from P2-03j source by "
            "scripts/build_growth_workspace_contract.py; never edit by hand. */\n"
            "window.GrowthAutopilotPreviewData = Object.freeze(" + data + ");\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Fail if the committed browser contract is stale.")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("P2-03k browser engine contract is missing or stale", file=sys.stderr)
            return 1
        print("PASS: P2-03k browser contract matches tested P2-03j engine")
    else:
        OUTPUT.write_text(expected, encoding="utf-8")
        print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
