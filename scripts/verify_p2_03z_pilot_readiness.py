#!/usr/bin/env python3
"""P2-03z prospective pilot admission: source evidence != operational proof."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
FOUNDATION=ROOT/"docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
OUTPUT=ROOT/"artifacts/validation/p2-03z-operational-pilot-readiness.json"
API=ROOT/"apps/api/app/pilot_outcomes.py"
SCHEMA=ROOT/"database/migrations/016_pilot_outcome_evidence.sql"
MAIN=ROOT/"apps/api/app/main.py"

def inspect()->dict:
    doc=json.loads(FOUNDATION.read_text())
    checks=doc["checks"]
    if [x["id"] for x in checks]!=[f"F{n:02}" for n in range(1,10)]:
        raise ValueError("Invalid Foundation ledger")
    if not (all(x["status"]=="verified" for x in checks[:3]) and
            all(x["status"]=="blocked" for x in checks[3:])):
        raise ValueError("Source code cannot promote incomplete operational gates")
    sql=SCHEMA.read_text()
    code=API.read_text()
    main=MAIN.read_text()
    required={
        "immutable_postgres_evidence":"FORCE ROW LEVEL SECURITY" in sql
             and "prevent_pilot_evidence_change" in sql,
        "independent_database_review":"submitted_by=NEW.reviewer_user_id" in sql
             and "role_in_org NOT IN ('OWNER','ADMIN')" in sql,
        "tenant_bound_api":"get_tenant_session" in code
             and "require_role" in code,
        "aggregate_only":"source_sha256" in code and
             "customer_email" not in code and
             "SEND_EMAIL" not in code,
        "noncausal_arithmetic":"financial_causation_attributed_to_metaautomate" in code
             and "net_profit_verified" in code,
        "private_feature_disabled_default":'os.environ.get("MAT_PILOT_OUTCOMES_ENABLED") == "1"' in main
             and '_mode != "oidc"' in main,
    }
    if not all(required.values()):
        raise ValueError("Missing source-only guard")
    return {
        "milestone":"P2-03z Evidence-backed Business Outcomes",
        "classification":"PROSPECTIVE_OFF_BY_DEFAULT",
        "source_checks":required,
        "foundation_verified":3,"foundation_total":9,
        "missing_operational_gates":[x["id"] for x in checks[3:]],
        "live_staff_sso_mfa_verified":False,
        "real_customer_data_processed":False,
        "real_source_documents_authenticated":False,
        "actual_customer_consent_verified":False,
        "independent_review_in_live_staging_verified":False,
        "actual_baseline_collected":False,
        "real_business_financial_impact_verified":False,
        "migration_016_applied_to_owner_or_production":False,
        "live_pilot_intake_enabled":False,
        "external_integrations_called":False,
        "new_subscriptions_purchased":False,
        "website_deployed":False,
        "operational_go":False,
    }

def main(argv=None):
    arg=argparse.ArgumentParser()
    arg.add_argument("--report",type=Path,default=OUTPUT)
    arg.add_argument("--require-operational-go",action="store_true")
    a=arg.parse_args(argv)
    try:r=inspect()
    except (OSError,ValueError,KeyError,TypeError):
        print("FAIL: source-only milestone evidence malformed",file=sys.stderr)
        return 1
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("P2-03z: evidence intake source ready for review; F04-F09 BLOCKED")
    if a.require_operational_go:
        print("DENIED: real staff/private-stage consent and independently verified"
              " business outcomes are missing",file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
