#!/usr/bin/env python3
"""Generate a browser-safe P2-03s continuity contract from validated Python models."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_business_resilience import build_continuity_intelligence

OUTPUT=ROOT/"apps/site/intelligence-lab/continuity/data.js"


def create_contract():
    out={"schema_version":1,"classification":"SYNTHETIC_SOURCE_ONLY",
         "units":"DEMO_CREDITS_NOT_CURRENCY","workspaces":{}}
    for ws in ("academy_demo","bespoke_demo"):
        r=build_continuity_intelligence(ws)
        assert r["evidence"]["provider_calls"] == 0
        assert r["evidence"]["database_writes"] == 0
        assert r["financial"]["actual_savings"] is None
        assert r["continuity"]["predicted_incident_probability"] is None
        f=r["financial"]
        out["workspaces"][ws]={
            "financial":{
                "gross_sales":f["illustrative_gross_sales"],
                "identified_costs":f["identified_costs"],
                "modeled_contribution":f["modeled_contribution"],
                "identified_cost_to_sales_bps":f["identified_cost_to_sales_bps"],
                "cost_over_budget":f["cost_over_budget"],
            },
            "operational":{
                k:r["continuity"][k] for k in (
                    "service_downtime_hours","late_supplier_deliveries",
                    "unreconciled_cost_entries","unused_tool_seats")
            },
            "risks":[{
                "code":risk["code"],
                "priority":risk["ordinal_priority"],
                "exposure_example":risk["exposure_example"],
                "mitigation_example":risk["mitigation_example"],
                "manual_action":risk["manual_review_action"],
            } for risk in r["continuity"]["risk_reviews"]],
        }
    return out


def render():
    return ("/* Generated from P2-03s source-only continuity intelligence. */\n"
            "window.MetaAutomateContinuityData = Object.freeze("
            +json.dumps(create_contract(),sort_keys=True,separators=(",",":"),
                        ensure_ascii=True)+");\n")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    expected=render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8")!=expected:
            raise SystemExit("FAIL: continuity source and browser evidence differ")
        print("PASS: continuity browser contract matches validated Python engine")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(expected,encoding="utf-8")
        print("Generated source-only continuity browser data")


if __name__=="__main__":
    main()
