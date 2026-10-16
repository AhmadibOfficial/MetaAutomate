#!/usr/bin/env python3
"""P2-03y source-only acceptance. Never provisions staging or issues GO."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.p2_03y_security_acceptance import source_acceptance_report
from verify_private_staging_contract import COMPOSE,check as source_staging_check

REPORT=ROOT/"artifacts/validation/p2-03y-private-staging-security.json"

def inspect() -> dict:
    import yaml
    report=source_acceptance_report()
    try:
        c=yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
        violations=source_staging_check(c)
        report["existing_compose_source_valid"]=not violations
        report["existing_compose_source_errors"]=violations
        if not violations:
            report["current_api_egress_explicitly_denied"]=False
            report["real_agent_worker_provisioned"]=False
            report["remaining_network_blockers"]=[
                "Existing API attaches to an unrestricted egress network",
                "No deployed zero-egress agent worker and no live denial test",
                "Actual model adapters, scopes and consent remain disabled",
            ]
    except (OSError,yaml.YAMLError,TypeError,ValueError):
        report["existing_compose_source_valid"]=False
        report["existing_compose_source_errors"]=["SOURCE_COMPOSE_UNREADABLE"]
    # Guard: source checks can only confirm design; never change operative GO.
    assert report["production_go"] is False
    assert report["private_staging_provisioned"] is False
    assert report["foundation_verified"]==3
    return report

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",type=Path,default=REPORT)
    parser.add_argument("--require-operational-go",action="store_true",
                        help="Intentionally fails closed until separately verified live gates")
    args=parser.parse_args(argv)
    try:
        result=inspect()
    except Exception as exc:
        print("P2-03y source acceptance failed validation: "+str(exc),file=sys.stderr)
        return 1
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",
                           encoding="utf-8")
    print("P2-03y: source contract inspected; Phase 01 3/9; LIVE NO-GO")
    if args.require_operational_go:
        print("DENIED: real staff SSO, private staging, model, worker, backup "
              "and independent acceptance not verified",file=sys.stderr)
        return 1
    return 0 if result.get("existing_compose_source_valid") else 1

if __name__=="__main__":
    raise SystemExit(main())
