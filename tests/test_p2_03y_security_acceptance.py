"""P2-03y: explicit F04-F09 and all Intelligence source-only GO blockers."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.p2_03y_security_acceptance import (
    POLICY,FOUNDATION,MANDATORY,INTELLIGENCE,
    parse_json,check_policy,check_foundation,
    source_acceptance_report,evaluate_model_request,
    evaluate_recovery_receipt,check_staging_runtime,
)
import yaml


def document():
    return json.loads(POLICY.read_text())


def fixture_bytes(doc):
    return json.dumps(doc,sort_keys=True).encode()


def test_source_review_never_grants_private_go():
    r=source_acceptance_report()
    assert r["foundation_verified"]==3 and r["foundation_total"]==9
    assert set(r["missing_foundation_controls"])==set(MANDATORY)
    assert set(r["missing_intelligence_controls"])==set(INTELLIGENCE)
    assert r["source_identity_verifier_implemented"]
    assert r["source_only_model_request_policy_implemented"]
    for name in (
       "real_staff_login_verified","live_mfa_verified",
       "live_model_evaluation_verified","private_worker_egress_verified",
       "independent_restore_verified","actual_customer_data_processed",
       "subscriptions_purchased","private_staging_provisioned",
       "external_tools_enabled","production_go",
       "public_website_deployment_authorized"
    ):
        assert r[name] is False,name
    assert len(r["source_policy_sha256"])==64
    assert r==source_acceptance_report()


@pytest.mark.parametrize("mutation",[
 lambda d:d.update({"foundation_verified":4}),
 lambda d:d.update({"foundation_verified":True}),
 lambda d:d.update({"environment":"DEPLOYED"}),
 lambda d:d.update({"environment_approval":"APPROVED"}),
 lambda d:d.update({"real_model_calls_allowed":True}),
 lambda d:d.update({"customer_data_allowed":True}),
 lambda d:d.update({"live_external_tools_allowed":True}),
 lambda d:d.update({"release_authorized":True}),
 lambda d:d.update({"phase02_operational_go":True}),
 lambda d:d.update({"phase03_operational_go":True}),
 lambda d:d["requirements"][0].update({"available":True}),
 lambda d:d["requirements"][0].update({"independent_witness":False}),
 lambda d:d["requirements"].pop(),
 lambda d:d["intelligence_gates"][1].update({"verified":True}),
 lambda d:d["intelligence_gates"][4].update({"proof":"NO_PROOF"}),
 lambda d:d["source_rehearsal"].update({"max_model_calls":1}),
 lambda d:d["source_rehearsal"].update({"paid_subscriptions":1}),
 lambda d:d["source_rehearsal"].update({"network_requests":2}),
 lambda d:d["source_rehearsal"].update({"cloud_resources_provisioned":1}),
 lambda d:d.update({"unreviewed_admin_override":True}),
])
def test_false_operational_evidence_is_rejected(mutation):
    doc=document();mutation(doc)
    with pytest.raises(SyntheticGrowthError):
        check_policy(doc)


@pytest.mark.parametrize("bad",[
 b"",b"null",b"{}",b"x"*20000,b'{"a":1,"a":2}',b'{"foo":Infinity}',
 b'{"a":1.5}',b"\x00",
])
def test_invalid_json_denied(bad):
    with pytest.raises(SyntheticGrowthError):
        parse_json(bad)


def test_current_foundation_register_remains_blocked():
    state=check_foundation(parse_json(FOUNDATION.read_bytes()))
    assert {x for x,v in state.items() if v=="blocked"}==set(MANDATORY)
    doc=parse_json(FOUNDATION.read_bytes())
    doc["checks"][3]["status"]="verified"
    with pytest.raises(SyntheticGrowthError):
        check_foundation(doc)


def test_existing_private_compose_is_source_valid_but_has_egress_gap():
    config=yaml.safe_load((ROOT/"deploy/staging/compose.yaml").read_text())
    report=check_staging_runtime(config)
    assert report["source_profile_checked"]
    assert report["network_isolation_proven"] is False
    assert report["agent_worker_isolated"] is False
    assert report["model_provider_egress_enforced"] is False
    assert any("UNRESTRICTED_API_EGRESS" in b for b in report["blockers"])


@pytest.mark.parametrize("model,task",[
 ("gpt-6-astra","BUSINESS_COST"),
 ("gpt-6.1-sol","SECURITY_REVIEW"),
 ("gpt-6-luna","CONSENT_SOCIAL"),
 ("claude-opus-5-5","SUPPLY_RISK"),
])
def test_provider_models_are_known_but_not_authorized(model,task):
    report=evaluate_model_request({
        "model_id":model,"task_id":task,"synthetic_only":True,
        "max_cost_minor":0,"human_approval_verified":False,
        "real_provider_token_present":False,
    })
    assert not report["provider_inference_authorized"]
    assert not report["benchmark_verified"]
    assert report["model_api_calls"]==0
    assert not report["cost_measured"]


@pytest.mark.parametrize("change",[
 {"model_id":"gpt-6-unreviewed"},
 {"task_id":"PRODUCTION_API"},
 {"synthetic_only":False},
 {"max_cost_minor":10},
 {"max_cost_minor":True},
 {"human_approval_verified":True},
 {"real_provider_token_present":True},
 {"api_key":"should never accept tokens"},
])
def test_model_access_fail_closed(change):
    case={
        "model_id":"gpt-6-astra","task_id":"BUSINESS_COST",
        "synthetic_only":True,"max_cost_minor":0,
        "human_approval_verified":False,"real_provider_token_present":False,
    }
    case.update(change)
    with pytest.raises(SyntheticGrowthError):
        evaluate_model_request(case)


def recovery(**changes):
    v={
        "backup_sha256":"a"*64,"restore_sha256":"b"*64,
        "backup_encrypted":True,"off_host":True,
        "separate_failure_domain":True,"observed_rpo_seconds":15,
        "observed_rto_seconds":45,"independent_witness_id":"REVIEWER-0002",
        "external_anchor_verified":True,
    }
    v.update(changes)
    return v


def test_recovery_claim_does_not_substitute_for_independent_proof():
    r=evaluate_recovery_receipt(recovery())
    assert r["self_reported_structural_completeness"]
    assert not r["actual_restore_independently_verified"]
    assert not r["external_artifacts_read_and_validated"]
    assert not r["f07_verified"]


@pytest.mark.parametrize("change",[
 {"backup_sha256":"X"*64},
 {"observed_rpo_seconds":-2},
 {"observed_rpo_seconds":True},
 {"observed_rto_seconds":700000},
 {"independent_witness_id":"x"},
 {"backup_encrypted":"true"},
 {"off_host":1},
 {"password":"do not store this here"},
])
def test_bad_recovery_receipt_rejected(change):
    with pytest.raises(SyntheticGrowthError):
        evaluate_recovery_receipt(recovery(**change))


def test_recovery_missing_offhost_is_explicitly_incomplete():
    r=evaluate_recovery_receipt(recovery(off_host=False))
    assert not r["self_reported_structural_completeness"]
    assert not r["f07_verified"]
