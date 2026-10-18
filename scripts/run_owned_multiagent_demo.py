#!/usr/bin/env python3
"""Run P2-054 MetaAutomate-owned four-agent workflow without third parties.

Use a private local SQLite path; demo inputs are fictional and do not
represent a customer's actual inventory, revenue or business outcome.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps"/"api"))
from app.owned_multiagent_runtime import Runtime,demo_payload,canonical,digest

def main(argv=None)->int:
    p=argparse.ArgumentParser(description="Offline MetaAutomate owned agent runtime")
    p.add_argument("--db",required=True,help="Local SQLite file, NOT a public upload")
    p.add_argument("--tenant",default="demo_retail")
    p.add_argument("--actor",default="local_demo_owner")
    p.add_argument("--request-key",default="local-demo-20261018-001")
    p.add_argument("--requested-action",choices=[
        "NONE","PUBLISH_CAMPAIGN","ORDER_STOCK"],default="NONE")
    p.add_argument("--output",help="Optional local JSON result file")
    p.add_argument("--input-json",help="Optional user-authorized business input file")
    p.add_argument("--authorized-data",action="store_true",
                   help="Confirm permission to process supplied non-demo data on private disk")
    args=p.parse_args(argv)
    os.umask(0o077)  # local SQLite, -wal, -shm and exported data are owner-only.
    if args.input_json and not args.authorized_data:
        p.error("--authorized-data is required before using non-demo records")
    if args.input_json:
        path=Path(args.input_json)
        raw=path.read_bytes()
        if len(raw)>25000:
            p.error("Input JSON exceeds the 25 KB limit")
        payload=json.loads(raw)
        if args.requested_action!="NONE":
            payload["requested_external_action"]=args.requested_action
    else:
        payload=demo_payload()
        payload["requested_external_action"]=args.requested_action
    engine=Runtime(args.db)
    job=engine.submit(args.tenant,args.request_key,payload,
                      actor=args.actor,budget=6)
    steps=engine.work_until_idle(args.tenant)
    result=engine.report(args.tenant,job)
    chain=engine.verify_evidence(args.tenant,job)
    evidence={"schema":"metautomate-owned-agent-result/v1",
              "fixture_data_only":True,
              "agent_steps_executed_this_invocation":steps,
              "run":result,"evidence_chain":chain}
    raw=canonical(evidence)
    checksum=digest(raw)
    if args.output:
        target=Path(args.output)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw+b"\n")
    print(json.dumps({
        "run_id":job,"state":result["state"],
        "agents_completed":sum(s["state"]=="DONE" for s in result["stage_status"]),
        "virtual_credits_used":result["spent_units"],
        "paid_provider_calls":0,
        "evidence_chain_valid":chain["verified"],
        "report_sha256":checksum,
        "output_file":args.output,
    },indent=2,sort_keys=True))
    if result["state"] not in ("COMPLETED","AWAITING_APPROVAL",
                               "APPROVED_NOT_EXECUTED"):
        return 2
    if not chain["verified"] or result["outputs"].get("verifier",{}).get(
        "verification")!="PASS":
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
