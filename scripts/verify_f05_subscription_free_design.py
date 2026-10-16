#!/usr/bin/env python3
"""F05 source-only zero-subscription design verification; no Docker or cloud calls."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"deploy/staging/subscription_free_design.v1.json"
EXISTING=ROOT/"deploy/staging/compose.yaml"
OUTPUT=ROOT/"artifacts/validation/f05-zero-subscription-staging.json"
STAGES=["S0","S1","S2"]
FALSE_FIELDS={
    "real_staging_environment_provisioned","real_provider_approved",
    "real_identity_provider_verified","actual_customer_data_allowed",
    "public_ingress_allowed","external_model_calls_allowed",
    "automated_provisioning_allowed","live_deployment_authorized",
    "release_authorized",
}
EXPECTED_PREREQUISITES={
    "F04_enforced_private_repository_merge_restrictions",
    "F05_owner_approved_host_region_cost_ceiling_and_separate_resources",
    "F06_real_OIDC_MFA_and_verified_private_ingress",
    "F07_encrypted_off_host_backup_and_independent_recovery",
    "F08_external_two_tenant_security_acceptance",
}
EXPECTED_STOP={
    "REAL_PERSONAL_OR_BUSINESS_DATA_DETECTED",
    "APP_PUBLIC_NETWORK_LISTENER_DETECTED",
    "REAL_EXTERNAL_API_TOKEN_PRESENT",
    "PAID_SUBSCRIPTION_OR_RESOURCE_REQUIRED",
    "PRODUCTION_DATABASE_OR_MIGRATION_TARGET_DETECTED",
    "UNAPPROVED_OUTBOUND_MESSAGE_OR_AI_MODEL_CALL",
}
TOP_FIELDS={
    "schema_version","name","classification","purpose",
    "proposed_subscription_cost_ngn","existing_template","existing_validator",
    "stages","prerequisites","blockers","stop_conditions",
} | FALSE_FIELDS
STEP_FIELDS={"id","name","environment","data","network",
             "requires_owner_approval","operational_f05_evidence"}


def validate(doc:dict,compose_text:str)->list[str]:
    errors=[]
    def require(ok,code):
        if not ok:errors.append(code)
    if type(doc) is not dict:return ["invalid_blueprint"]
    require(set(doc)==TOP_FIELDS,"blueprint_schema_changed")
    require(doc.get("schema_version")==1 and type(doc.get("schema_version")) is int,
            "blueprint_version_changed")
    require(doc.get("classification")=="SOURCE_ONLY_NON_DEPLOYABLE_BLUEPRINT",
            "false_operational_classification")
    require(type(doc.get("name")) is str and "subscription-free" in doc.get("name",""),
            "missing_subscription_free_scope")
    require(type(doc.get("proposed_subscription_cost_ngn")) is int and
            doc.get("proposed_subscription_cost_ngn")==0,
            "unapproved_subscription_cost")
    for field in FALSE_FIELDS:require(doc.get(field) is False,"unsafe_"+field)
    require(doc.get("existing_template")=="deploy/staging/compose.yaml"
            and doc.get("existing_validator")=="scripts/verify_private_staging_contract.py",
            "unauthorized_staging_dependencies")
    stages=doc.get("stages")
    if type(stages) is not list or len(stages)!=3:
        errors.append("unexpected_staging_progression")
    else:
        require([s.get("id") if type(s) is dict else None for s in stages]==STAGES,
                "stages_out_of_order")
        for step in stages:
            if type(step) is not dict:
                errors.append("invalid_stage");continue
            require(set(step)==STEP_FIELDS,"unrecognized_stage_field")
            require(step.get("operational_f05_evidence") is False,
                    "false_operational_staging_evidence")
        require(stages[0].get("data")=="SYNTHETIC_ONLY"
                and stages[1].get("data")=="SYNTHETIC_ONLY"
                and stages[2].get("data")=="NO_DATA",
                "customer_data_not_permitted")
        require(stages[2].get("environment")=="NOT_PROVISIONED"
                and stages[2].get("requires_owner_approval") is True,
                "premature_private_host_activation")
        require(stages[1].get("environment")=="EPHEMERAL_CI_RUNNER"
                and stages[1].get("network")=="TEST_SERVICE_LOOPBACK",
                "non_disposable_ci_risk")
    for field,expected in (("prerequisites",EXPECTED_PREREQUISITES),
                           ("stop_conditions",EXPECTED_STOP)):
        items=doc.get(field)
        require(type(items) is list and len(items)==len(expected) and
                len(set(map(str,items)))==len(items) and set(items)==expected,
                "missing_"+field)
    blockers=doc.get("blockers")
    require(type(blockers) is list and len(blockers)>=5 and
            all(type(x) is str and x.isupper() for x in blockers),
            "missing_staging_blockers")
    require("profiles: [\"owner-approved-staging\"]" in compose_text,
            "manual_opt_in_removed")
    require('\"127.0.0.1:8081:8000\"' in compose_text,
            "private_loopback_binding_removed")
    require("internal: true" in compose_text and
            "WORKSPACE_AUTH_MODE: oidc" in compose_text and
            "staging_pgdata:" in compose_text,
            "existing_staging_controls_missing")
    return errors


def inspect()->dict:
    try:
        raw=SOURCE.read_bytes()
        if len(raw)>16_384:raise ValueError("oversized")
        doc=json.loads(raw.decode("utf-8"))
        errors=validate(doc,EXISTING.read_text(encoding="utf-8"))
    except (OSError,ValueError,UnicodeDecodeError) as exc:
        errors=["unreadable_source_blueprint"]
    return {
        "schema_version":1,"gate":"F05",
        "classification":"NON_DEPLOYING_SOURCE_REVIEW",
        "status":"SOURCE_DESIGN_PASS_OPERATIONAL_BLOCKED" if not errors else "SOURCE_DESIGN_INVALID",
        "violations":errors,"subscriptions_purchased":False,
        "staging_provisioned":False,"customer_data_connected":False,
        "release_authorized":False,"operational_f05_verified":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,default=OUTPUT)
    args=p.parse_args(argv)
    result=inspect()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("F05: "+result["status"]+"; no resources provisioned")
    return 0 if not result["violations"] else 1


if __name__=="__main__":
    sys.exit(main())
