"""F05 staging blueprint negative tests; source pass != operational approval."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/verify_f05_subscription_free_design.py"
spec=importlib.util.spec_from_file_location("f05_design",SCRIPT)
validator=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=validator
spec.loader.exec_module(validator)


def fixtures():
    return (
        json.loads((ROOT/"deploy/staging/subscription_free_design.v1.json").read_text()),
        (ROOT/"deploy/staging/compose.yaml").read_text()
    )


def test_real_source_design_passes_but_f05_stays_blocked(tmp_path):
    result=validator.inspect()
    assert result["status"]=="SOURCE_DESIGN_PASS_OPERATIONAL_BLOCKED"
    assert result["violations"]==[]
    assert result["release_authorized"] is False
    assert result["operational_f05_verified"] is False
    assert result["staging_provisioned"] is False
    assert result["subscriptions_purchased"] is False
    path=tmp_path/"f05-source.json"
    assert validator.main(["--report",str(path)])==0
    assert json.loads(path.read_text())["operational_f05_verified"] is False


@pytest.mark.parametrize("change,expect_code",[
 (lambda d:d.update({"live_deployment_authorized":True}),
  "unsafe_live_deployment_authorized"),
 (lambda d:d.update({"real_staging_environment_provisioned":True}),
  "unsafe_real_staging_environment_provisioned"),
 (lambda d:d.update({"actual_customer_data_allowed":True}),
  "unsafe_actual_customer_data_allowed"),
 (lambda d:d.update({"public_ingress_allowed":True}),
  "unsafe_public_ingress_allowed"),
 (lambda d:d.update({"external_model_calls_allowed":True}),
  "unsafe_external_model_calls_allowed"),
 (lambda d:d.update({"real_identity_provider_verified":True}),
  "unsafe_real_identity_provider_verified"),
 (lambda d:d.update({"proposed_subscription_cost_ngn":1}),
  "unapproved_subscription_cost"),
 (lambda d:d.update({"proposed_subscription_cost_ngn":True}),
  "unapproved_subscription_cost"),
 (lambda d:d.update({"classification":"PRODUCTION_READY"}),
  "false_operational_classification"),
 (lambda d:d["stages"][2].update({"operational_f05_evidence":True}),
  "false_operational_staging_evidence"),
 (lambda d:d["stages"][1].update({"data":"CUSTOMER_DATA"}),
  "customer_data_not_permitted"),
 (lambda d:d["stages"][1].update({"network":"PUBLIC_INGRESS"}),
  "non_disposable_ci_risk"),
 (lambda d:d["stages"][2].update({"requires_owner_approval":False}),
  "premature_private_host_activation"),
 (lambda d:d["prerequisites"].remove(
        "F04_enforced_private_repository_merge_restrictions"),
  "missing_prerequisites"),
 (lambda d:d["stop_conditions"].remove(
        "REAL_PERSONAL_OR_BUSINESS_DATA_DETECTED"),
  "missing_stop_conditions"),
 (lambda d:d.update({"api_key":"unsafe"}),
  "blueprint_schema_changed"),
])
def test_mutated_blueprints_do_not_pass(change,expect_code):
    d,compose=fixtures()
    change(d)
    assert expect_code in validator.validate(d,compose)


@pytest.mark.parametrize("change,expected",[
 (lambda c:c.replace('profiles: ["owner-approved-staging"]',"profiles: []"),
  "manual_opt_in_removed"),
 (lambda c:c.replace('"127.0.0.1:8081:8000"','"0.0.0.0:8081:8000"'),
  "private_loopback_binding_removed"),
 (lambda c:c.replace("internal: true","internal: false"),
  "existing_staging_controls_missing"),
 (lambda c:c.replace("WORKSPACE_AUTH_MODE: oidc","WORKSPACE_AUTH_MODE: dev_key"),
  "existing_staging_controls_missing"),
])
def test_existing_staging_safety_controls_must_remain(change,expected):
    data,compose=fixtures()
    assert expected in validator.validate(data,change(compose))
