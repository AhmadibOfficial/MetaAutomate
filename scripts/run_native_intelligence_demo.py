#!/usr/bin/env python3
"""Execute P2-055 retrieval + P2-054 four agents, offline and with no paid APIs."""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps"/"api"))
from app.owned_multiagent_runtime import Runtime,demo_payload,canonical,digest
from app.native_intelligence import PrivateKnowledge,NativeIntelligence

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--workdir",required=True,help="Private local workspace directory")
    parser.add_argument("--input-json",help="Authorized inventory input, 25 KB max")
    parser.add_argument("--authorized-data",action="store_true")
    parser.add_argument("--mode",choices=["EVIDENCE_ONLY","LOCAL_MODEL"],
                        default="EVIDENCE_ONLY")
    parser.add_argument("--out",help="Optional machine-readable JSON output")
    args=parser.parse_args(argv)
    if args.input_json and not args.authorized_data:
        parser.error("Authorized business inputs require --authorized-data")
    os.umask(0o077)
    folder=Path(args.workdir)
    folder.mkdir(parents=True,exist_ok=True)
    if folder.stat().st_mode & 0o077:
        parser.error("Private workspace has unsafe filesystem permissions")
    if args.input_json:
        raw=Path(args.input_json).read_bytes()
        if len(raw)>25000:
            parser.error("Authorized business input exceeds 25 KB")
        payload=json.loads(raw)
    else:
        payload=demo_payload()
    tenant="demo_retail" # Demo only. Production tenant must come from OIDC.
    actor="local_demo_owner"
    kb=PrivateKnowledge(folder/"native_knowledge.sqlite3")
    kb.ingest(tenant=tenant,actor=actor,source_ref="demo/inventory-summary-v1",
              title="Retail inventory demo procedure",
              body=("Maize stock must be reviewed when quantities fall below "
                    "the reorder target. Independent agent verification is "
                    "required before any business action or publication."),
              consent=True)
    engine=NativeIntelligence(kb,Runtime(folder/"agent_queue.sqlite3"))
    q=engine.reply(tenant=tenant,actor=actor,session="native_demo_001",
                   question="What procedure verifies maize reorder decisions?",
                   mode=args.mode)
    workflow=engine.execute_business(
        tenant=tenant,actor=actor,request_key="native-20261018-demo-001",
        payload=payload,budget=6)
    result={
        "schema":"metaautomate/native-intelligence/v1",
        "fixture_only":not bool(args.input_json),
        "question":q,"workflow":workflow,
        "paid_api_calls":0,
        "external_actions_executed":False,
    }
    encoded=canonical(result)
    if args.out:
        dest=Path(args.out)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(encoded+b"\n")
    state=workflow["run"]["state"]
    passed=(bool(workflow["evidence_chain"]["verified"]) and
            workflow["run"]["outputs"].get("verifier",{}).get("verification")=="PASS"
            and state in ("COMPLETED","AWAITING_APPROVAL"))
    print(json.dumps({
        "state":state,
        "evidence_verified":passed,
        "agent_stages":len(workflow["run"]["stage_status"]),
        "knowledge_hits":len(q["sources"]),
        "answer_mode":q["mode"],
        "report_sha256":digest(encoded),
        "third_party_cost":0,
    },indent=2,sort_keys=True))
    return 0 if passed else 2

if __name__=="__main__":
    raise SystemExit(main())
