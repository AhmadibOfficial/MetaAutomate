#!/usr/bin/env python3
"""Generate the exact zero-network governance map from P2-03w Python contracts."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))

from app.synthetic_integrated_intelligence import MODULES, ENGINES
from app.synthetic_governed_intelligence_portfolio import (
    MODULE_ENGINE_MAP, MODULE_TASK_MAP, VIRTUAL_TOOLS,
)
from app.synthetic_model_evaluation import MODEL_IDS

OUTPUT=ROOT/"apps/site/intelligence/governance/data.js"


def render():
    contract={
        "schema_version":1,"classification":"SYNTHETIC_SOURCE_ONLY",
        "modules":[{
            "id":ident,"name":name,"engines":list(MODULE_ENGINE_MAP[ident]),
            "evaluation_task":MODULE_TASK_MAP[ident],
            "virtual_tools":[tool for tool,names in VIRTUAL_TOOLS.items()
                             if ident in names],
            "status":"SOURCE_ONLY_UNVERIFIED_CUSTOMER_DATA",
        } for ident,name in MODULES],
        "engines":[{"id":e,"status":"SOURCE_ONLY_NO_DISPATCH"}
                   for e in ENGINES],
        "candidate_models":[{"id":mid,"evidence":"OFFICIAL_MODEL_ID_NOT_EVALUATED"}
                            for mid in sorted(MODEL_IDS)],
        "limitations":{
            "mfa_verified_with_live_idp":False,
            "customer_data_connected":False,
            "live_ai_model_calls":0,
            "external_tools_enabled":False,
            "actual_roi_verified":False,
            "production_enabled":False,
            "foundation_gates_verified":3,
            "foundation_gates_total":9,
        },
    }
    return ("/* Generated from P2-03w source-only governance contracts. */\n"
           "window.MetaAutomateGovernanceMap = Object.freeze("
           +json.dumps(contract,sort_keys=True,separators=(",",":"),ensure_ascii=True)
           +");\n")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    a=p.parse_args()
    expected=render()
    if a.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8")!=expected:
            raise SystemExit("FAIL: browser governance map differs from Python architecture")
        print("PASS: browser governance map matches 12 modules, 5 engines and tool policy")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(expected,encoding="utf-8")
        print("Generated synthetic governance map")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
