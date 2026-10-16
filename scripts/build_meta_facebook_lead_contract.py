#!/usr/bin/env python3
"""Generate an offline Facebook Lead Ads demo strictly from signed redacted events.

There is intentionally no Graph API lead retrieval or real contact data.
"""
import argparse
import hmac
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_meta_lead_federation import inspect_signed_meta_event

FIXTURE=ROOT/"contracts/domains/v1/fixtures/synthetic_meta_lead_envelopes.v1.json"
OUTPUT=ROOT/"apps/site/intelligence-lab/facebook/data.js"
TEST_SECRET=b"fixture-only-meta-app-secret-not-for-production-2026"


def build_contract() -> dict:
    doc=json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert set(doc)=={"schema_version","classification","envelopes"}
    assert type(doc["schema_version"]) is int and doc["schema_version"]==1
    assert doc["classification"]=="SYNTHETIC_SOURCE_ONLY"
    assert type(doc["envelopes"]) is list and len(doc["envelopes"])==4
    items=[]
    channels=set()
    for envelope in doc["envelopes"]:
        body=json.dumps(envelope,sort_keys=True,separators=(",",":")).encode()
        sig="sha256="+hmac.new(TEST_SECRET,body,"sha256").hexdigest()
        account=envelope["entry"][0]["id"]
        workspace="academy_demo" if "ACADEMY" in account else "bespoke_demo"
        output=inspect_signed_meta_event(body,sig,TEST_SECRET,
                                          expected_workspace=workspace)
        assert output["messages_sent"] == 0
        assert output["database_writes"] == 0
        assert not output["live_webhook_endpoint"]
        for record in output["events"]:
            channels.add(record["platform"])
            if record["platform"]=="FACEBOOK":
                items.append({
                    "workspace":workspace,"source":"FACEBOOK_INSTANT_FORM",
                    "event_ref":record["event_ref"],
                    "form_ref":record["form_ref"],
                    "form_submitted_in_example":True,
                    "source_origin_verified_live":False,
                    "marketing_consent_live_verified":False,
                    "lead_profile_retrieved":False,
                    "outbound_allowed":False,
                })
    assert channels=={"FACEBOOK","INSTAGRAM","WHATSAPP"}
    assert len(items)==2 and len({x["workspace"] for x in items})==2
    return {
        "schema_version":1,
        "classification":"SYNTHETIC_SOURCE_ONLY",
        "platform":"FACEBOOK",
        "examples":items,
        "channels_in_federation":sorted(channels),
        "real_contacts":0,"real_crm_writes":0,"real_messages_sent":0,
        "actual_ad_spend":0,"lead_retrieval_enabled":False,
    }


def render() -> str:
    return ("/* P2-03r generated synthetic Facebook lead form metadata. No PII. */\n"
            "window.MetaAutomateFacebookLeads = Object.freeze("
            +json.dumps(build_contract(),sort_keys=True,separators=(",",":"),
                        ensure_ascii=True)+");\n")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    expected=render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("FAIL: Facebook demonstration data not equal to signed fixture")
        print("PASS: signed Meta-shaped source yields accurate Facebook demonstration contract")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(expected,encoding="utf-8")
        print("Wrote Facebook demonstration contract")


if __name__=="__main__":
    main()
