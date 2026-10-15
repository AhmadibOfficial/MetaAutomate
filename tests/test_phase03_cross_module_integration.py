"""P3-07: cross-module offline DENY integration and threat regression.

No test here can represent real customer or production security approval.
"""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from app.phase03_integration_safety import (
    EXPECTED_CONTRACTS, OfflineIntegratedInput,
    OfflineIntegrationDenied, audit_offline_contracts,
    run_offline_integration,
)
from app.phase03_intelligent_ecosystem import OPERATION_SPECS

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"


def make(**updates):
    source = OfflineIntegratedInput(tenant_id=uuid4())
    return replace(source, **updates)


@pytest.mark.parametrize("operation", tuple(OPERATION_SPECS))
def test_all_four_capabilities_reject_end_to_end(operation):
    out = run_offline_integration(make(operation_id=operation))
    assert out.capability_id == OPERATION_SPECS[operation][0]
    assert out.denial_receipt_consistent is True
    assert out.denied_plan_consistent is True
    assert out.negative_evidence_consistent is True
    assert out.invented_state_unchanged is True
    assert out.demo_plan_expired is False
    assert out.audited_denial_consistent is True
    assert out.decision == "DENY"
    assert out.mandatory_trust_checks_missing
    assert not out.actual_authorization_verified
    assert not out.real_provider_receipt_verified
    assert not out.provider_called
    assert not out.customer_data_accessed
    assert not out.real_financial_result_measured
    assert not out.real_customer_outcome_verified
    assert not out.business_effect_performed
    assert not out.release_authorized


def test_finance_even_with_two_dummy_reviewers_stays_unapproved():
    v = run_offline_integration(make(
        operation_id="business.finance.reconciliation-proposal.v1",
        reviewer_labels=("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA"),
    ))
    assert "SPECIFIC_EFFECT_HUMAN_REVIEW_UNVERIFIED" in v.mandatory_trust_checks_missing
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in v.mandatory_trust_checks_missing
    assert not v.actual_authorization_verified
    assert v.decision == "DENY"


def test_changes_and_expiration_remain_denial():
    v = run_offline_integration(make(
        observed_resource_version=2, observed_tick=112,
    ))
    assert not v.invented_state_unchanged
    assert v.demo_plan_expired
    assert "DEMO_RESOURCE_VERSION_CHANGED" in v.mandatory_trust_checks_missing
    assert "DEMO_PLAN_EXPIRED" in v.mandatory_trust_checks_missing
    assert v.decision == "DENY"


def test_optional_metrics_are_synthetic_not_provider_telemetry():
    v = run_offline_integration(make(attach_synthetic_analytics=True))
    assert v.synthetic_business_alerts == (
        "DEMO_NO_RULE_BASED_ALERTS_NOT_BUSINESS_SUCCESS",
    )
    assert not v.real_financial_result_measured
    assert not v.provider_called


def test_no_analytics_when_not_requested():
    assert run_offline_integration(make()).synthetic_business_alerts == ()


def test_same_request_in_two_demo_tenants_is_not_same_partition():
    request = make()
    other = replace(request, tenant_id=uuid4())
    a = run_offline_integration(request)
    b = run_offline_integration(other)
    assert a.tenant_marker != b.tenant_marker
    assert a.decision == b.decision == "DENY"
    assert a.audited_denial_consistent
    assert b.audited_denial_consistent


@pytest.mark.parametrize("field,value", [
    ("tenant_id", "customer"),
    ("tenant_id", None),
    ("tenant_id", True),
    ("operation_id", "business.finance.transfer.v1"),
    ("operation_id", []),
    ("operation_id", None),
    ("request_id", "LIVE-CUSTOMER"),
    ("request_id", "DEMO-REQ-"),
    ("request_id", "DEMO-REQ-A\n"),
    ("request_id", True),
    ("request_id", None),
    ("attempt_id", "REAL-ATTEMPT"),
    ("attempt_id", "DEMO-ATTEMPT-"),
    ("attempt_id", None),
    ("attempt_id", True),
    ("resource_version", 0),
    ("resource_version", -1),
    ("resource_version", "1"),
    ("resource_version", True),
    ("resource_version", 1001),
    ("observed_resource_version", -1),
    ("observed_resource_version", 1001),
    ("observed_resource_version", True),
    ("observed_tick", -1),
    ("observed_tick", 99),
    ("observed_tick", 1000001),
    ("observed_tick", "101"),
    ("observed_tick", True),
    ("reviewer_labels", None),
    ("reviewer_labels", ["DEMO-REVIEWER-ALPHA"]),
    ("reviewer_labels", ("REAL-APPROVER",)),
    ("reviewer_labels", ("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-ALPHA")),
    ("reviewer_labels", ("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA",
                         "DEMO-REVIEWER-GAMMA")),
    ("reviewer_labels", (True,)),
    ("attach_synthetic_analytics", "true"),
    ("attach_synthetic_analytics", 1),
])
def test_untrusted_or_privilege_claiming_input_is_rejected(field, value):
    with pytest.raises(OfflineIntegrationDenied):
        run_offline_integration(make(**{field: value}))


def test_frozen_output_cannot_claim_live_execution():
    result = run_offline_integration(make())
    with pytest.raises(FrozenInstanceError):
        result.release_authorized = True


def test_eight_source_manifests_are_checked_but_not_operationally_approved():
    audit = audit_offline_contracts(ROOT)
    assert audit.contracts_checked == 8
    assert audit.operation_count == 4
    assert audit.controls_denied
    assert audit.decision == "DENY"
    assert audit.source_verified_only
    assert not audit.external_services_verified
    assert not audit.live_execution_authorized
    assert not audit.independent_review_performed


def copied_contracts(tmp_path: Path) -> Path:
    for location in EXPECTED_CONTRACTS.values():
        dest = tmp_path / location
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / location).read_bytes())
    return tmp_path


@pytest.mark.parametrize("name,field,value", [
    ("planning", "trusted_execution_authorization_available", True),
    ("planning", "external_writes_performed", 0),
    ("outcome", "external_execution_authorized", True),
    ("outcome", "live_provider_readback_enabled", True),
    ("analytics", "live_execution_authorized", "false"),
    ("analytics", "real_revenue_measured", True),
    ("execution", "real_execution_authorized", True),
    ("execution", "any_effect_performed", 0),
    ("execution", "durable_replay_protection_available", True),
    ("integration", "live_execution_authorized", True),
    ("integration", "external_provider_access_enabled", True),
    ("integration", "independent_review_verified", True),
    ("integration", "phase02_operational_approved", True),
    ("integration", "phase01_foundation_verified", 9),
    ("integration", "default_decision", "ALLOW"),
    ("integration", "source_contract_count", 7),
    ("integration", "scope", "LIVE"),
    ("execution", "default_decision", "ALLOW"),
])
def test_modified_source_manifest_fails_closed(tmp_path, name, field, value):
    root = copied_contracts(tmp_path)
    path = root / EXPECTED_CONTRACTS[name]
    j = json.loads(path.read_text())
    j[field] = value
    path.write_text(json.dumps(j))
    with pytest.raises(OfflineIntegrationDenied):
        audit_offline_contracts(root)


def test_missing_and_malformed_contracts_fail_closed(tmp_path):
    root = copied_contracts(tmp_path)
    missing = root / EXPECTED_CONTRACTS["execution"]
    missing.unlink()
    with pytest.raises(OfflineIntegrationDenied):
        audit_offline_contracts(root)
    missing.write_text("{invalid json")
    with pytest.raises(OfflineIntegrationDenied):
        audit_offline_contracts(root)


def test_added_capability_drift_is_detected(tmp_path):
    root = copied_contracts(tmp_path)
    p = root / EXPECTED_CONTRACTS["capabilities"]
    j = json.loads(p.read_text())
    j["operations"].append(j["operations"][0].copy())
    p.write_text(json.dumps(j))
    with pytest.raises(OfflineIntegrationDenied):
        audit_offline_contracts(root)


def test_changed_tool_spec_is_detected(tmp_path):
    root = copied_contracts(tmp_path)
    p = root / EXPECTED_CONTRACTS["developer"]
    j = json.loads(p.read_text())
    j["actions"][0]["effect"] = "ALLOW"
    p.write_text(json.dumps(j))
    with pytest.raises(OfflineIntegrationDenied):
        audit_offline_contracts(root)


def test_cross_module_module_is_unrouted_no_external_transport():
    module = (ROOT / "apps/api/app/phase03_integration_safety.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_integration_safety" not in main
    for forbidden in (
        "APIRouter(", "requests.", "httpx", "urllib.request",
        "urlopen(", "subprocess.", "socket.socket(", "psycopg",
        "redis.", "openai.", "google.generativeai",
    ):
        assert forbidden not in module


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args], text=True,
        capture_output=True, check=False, timeout=20,
    )


def test_cli_ecosystem_check_all_four_operations():
    p = run_cli("ecosystem-check")
    assert p.returncode == 0, p.stderr
    j = json.loads(p.stdout)
    assert j["synthetic_operations_checked"] == 4
    assert j["synthetic_denials"] == 4
    assert j["external_operations_performed"] == 0
    assert j["contract_audit"]["contracts_checked"] == 8
    assert not j["release_authorized"]
    assert j["decision"] == "DENY"


@pytest.mark.parametrize("operation", tuple(OPERATION_SPECS))
def test_cli_integrated_demonstration_denies_all_operations(operation):
    p = run_cli("integration-demo", operation)
    assert p.returncode == 0, p.stderr
    j = json.loads(p.stdout)
    assert j["operation_id"] == operation
    assert j["decision"] == "DENY"
    assert j["denied_plan_consistent"]
    assert j["audited_denial_consistent"]
    assert not j["provider_called"]
    assert not j["business_effect_performed"]


def test_cli_finance_still_denied_with_fake_reviewers_and_analytics():
    p = run_cli(
        "integration-demo", "business.finance.reconciliation-proposal.v1",
        "--reviewer-count", "2", "--demo-analytics",
    )
    assert p.returncode == 0, p.stderr
    j = json.loads(p.stdout)
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in j["mandatory_trust_checks_missing"]
    assert j["synthetic_business_alerts"]
    assert j["decision"] == "DENY"


def test_cli_expired_fake_version_reports_failures_without_side_effects():
    p = run_cli(
        "integration-demo", "business.inventory.stock-preview.v1",
        "--observed-version", "2", "--observed-tick", "112",
    )
    assert p.returncode == 0, p.stderr
    j = json.loads(p.stdout)
    assert j["demo_plan_expired"]
    assert not j["invented_state_unchanged"]
    assert "DEMO_RESOURCE_VERSION_CHANGED" in j["mandatory_trust_checks_missing"]
    assert not j["provider_called"]


@pytest.mark.parametrize("args", [
    ["integration-demo", "finance.wire"],
    ["integration-demo", "business.inventory.stock-preview.v1", "--execute"],
    ["integration-demo", "business.inventory.stock-preview.v1",
     "--reviewer-count", "3"],
    ["integration-demo", "business.inventory.stock-preview.v1",
     "--observed-tick", "99"],
    ["integration-demo", "business.inventory.stock-preview.v1",
     "--observed-version", "-1"],
    ["ecosystem-check", "--production"],
])
def test_cli_rejects_invalid_or_real_operations(args):
    p = run_cli(*args)
    assert p.returncode != 0
    assert not p.stdout
