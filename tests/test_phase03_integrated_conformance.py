"""P3-07: integrated P3-01..P3-06 denied-transaction security conformance."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

import pytest

from app.phase03_intelligent_ecosystem import OPERATION_SPECS
import app.phase03_integrated_conformance as integrated
from app.phase03_integrated_conformance import (
    DemoIntegratedRequest, IntegratedSourceDenied, OfflineIntegratedReport,
    run_integrated_demo, inspect_integrated_demo,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"
MANIFEST = ROOT / "contracts/intelligent/v1/integration_conformance.json"


def fixture(op="business.inventory.stock-preview.v1", **changes):
    return replace(DemoIntegratedRequest(
        tenant_id=uuid4(), operation_id=op,
        request_id="DEMO-REQ-INTEGRATION-001",
        attempt_id="DEMO-ATTEMPT-INTEGRATION-001",
    ), **changes)


@pytest.mark.parametrize("op", tuple(OPERATION_SPECS))
def test_all_four_operations_join_denial_and_keep_external_trust_false(op):
    query = fixture(op)
    report = run_integrated_demo(query)
    assert report.operation_id == op
    assert report.capability_id == OPERATION_SPECS[op][0]
    assert report.effect == OPERATION_SPECS[op][1]
    assert report.required_scope == OPERATION_SPECS[op][2]
    assert report.request_id == query.request_id
    assert report.decision == "DENY"
    assert report.finding == "SYNTHETIC_CROSS_MODULE_DENIAL_ONLY"
    assert report.source == "UNAUTHENTICATED_INVENTED_FIXTURES"
    assert report.demo_source_consistent
    assert report.synthetic_business_periods == 2
    assert report.hypothetical_net_minor == 90_000
    assert report.demo_resource_unchanged
    assert not report.demo_plan_expired
    assert report.second_reviewer_needed is (OPERATION_SPECS[op][3] == "high")
    assert len(report.admission_digest) == 64
    assert len(report.planning_digest) == 64
    assert len(report.execution_rejection_digest) == 64
    assert len(report.demo_audit_hash) == 64
    assert not report.execution_authorized
    assert not report.side_effects_performed
    assert not report.provider_called
    assert not report.provider_result_verified
    assert not report.independent_security_review_complete
    assert not report.real_revenue_measured
    assert not report.customer_data_processed
    assert not report.audit_durable
    assert not report.production_ready
    assert not report.release_authorized
    assert inspect_integrated_demo(report, query)


def test_finance_fake_dual_reviewer_labels_cannot_approve():
    query = fixture(
        "business.finance.reconciliation-proposal.v1",
        reviewer_labels=("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA"),
    )
    report = run_integrated_demo(query)
    assert report.second_reviewer_needed
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in report.denial_reasons
    assert "SPECIFIC_EFFECT_HUMAN_REVIEW_UNVERIFIED" in report.denial_reasons
    assert report.decision == "DENY"
    assert not report.execution_authorized


def test_stale_plan_and_changed_resource_reconciled_without_execution():
    query = fixture(observed_tick=112, observed_version=2)
    report = run_integrated_demo(query)
    assert report.demo_plan_expired
    assert not report.demo_resource_unchanged
    assert "DEMO_PLAN_EXPIRED" in report.denial_reasons
    assert "DEMO_RESOURCE_VERSION_CHANGED" in report.denial_reasons
    assert report.demo_source_consistent
    assert report.decision == "DENY"
    assert not report.side_effects_performed


def test_two_separate_tenants_cannot_reuse_evidence():
    a = fixture()
    b = replace(a, tenant_id=uuid4())
    report_a = run_integrated_demo(a)
    report_b = run_integrated_demo(b)
    assert report_a.tenant_demo_marker != report_b.tenant_demo_marker
    assert report_a.demo_audit_hash != report_b.demo_audit_hash
    assert not inspect_integrated_demo(report_a, b)
    assert not inspect_integrated_demo(report_b, a)
    assert inspect_integrated_demo(report_a, a)
    assert inspect_integrated_demo(report_b, b)


@pytest.mark.parametrize("change", [
    {"operation_id": "business.live.bank-payment.v1"},
    {"operation_id": []},
    {"operation_id": None},
    {"tenant_id": "real-tenant"},
    {"tenant_id": True},
    {"request_id": "REAL-CUSTOMER-REQUEST"},
    {"request_id": []},
    {"request_id": "DEMO-REQ-A\n"},
    {"attempt_id": "LIVE-PAYMENT"},
    {"attempt_id": True},
    {"observed_tick": True},
    {"observed_tick": -1},
    {"observed_tick": 1_000_001},
    {"observed_tick": "101"},
    {"observed_version": False},
    {"observed_version": -1},
    {"observed_version": 1001},
    {"observed_version": "1"},
    {"reviewer_labels": ["DEMO-REVIEWER-ALPHA"]},
    {"reviewer_labels": ("REAL-REVIEWER",)},
    {"reviewer_labels": ("DEMO-REVIEWER-ALPHA","DEMO-REVIEWER-ALPHA")},
    {"reviewer_labels": ("DEMO-REVIEWER-ALPHA",)*3},
    {"reviewer_labels": (None,)},
])
def test_malformed_external_like_inputs_never_build_traces(change):
    with pytest.raises(IntegratedSourceDenied):
        run_integrated_demo(fixture(**change))


@pytest.mark.parametrize("tamper", [
    {"decision": "ALLOW"},
    {"execution_authorized": True},
    {"side_effects_performed": True},
    {"provider_called": True},
    {"provider_result_verified": True},
    {"independent_security_review_complete": True},
    {"real_revenue_measured": True},
    {"customer_data_processed": True},
    {"audit_durable": True},
    {"production_ready": True},
    {"release_authorized": True},
    {"required_scope": "finance.unrestricted"},
    {"denial_reasons": ()},
    {"planning_digest": "f" * 64},
    {"demo_audit_hash": "0"*64},
    {"hypothetical_net_minor": 500_000},
    {"demo_source_consistent": False},
])
def test_caller_forged_grant_or_profit_claim_cannot_verify(tamper):
    query = fixture()
    report = run_integrated_demo(query)
    assert not inspect_integrated_demo(replace(report, **tamper), query)


def test_immutable_trace_not_mutated_into_grant():
    report = run_integrated_demo(fixture())
    with pytest.raises(FrozenInstanceError):
        report.release_authorized = True


def test_parallel_reconstruction_deterministic_and_still_denied():
    query = fixture()
    with ThreadPoolExecutor(max_workers=8) as executor:
        reports = list(executor.map(lambda _: run_integrated_demo(query), range(14)))
    assert len(reports) == 14
    assert all(x == reports[0] for x in reports)
    assert not any(x.execution_authorized for x in reports)


def test_cross_module_failure_propagates_fail_closed(monkeypatch):
    query = fixture()
    original = integrated.verify_demo_negative_outcome
    def fake_verify(*args, **kwargs):
        return replace(original(*args, **kwargs), execution_verified=True)
    monkeypatch.setattr(integrated, "verify_demo_negative_outcome", fake_verify)
    with pytest.raises(IntegratedSourceDenied):
        run_integrated_demo(query)


def test_mocked_measured_revenue_is_rejected(monkeypatch):
    query = fixture()
    original = integrated.analyze_demo_business
    def fake_metrics(*args, **kwargs):
        return replace(original(*args, **kwargs), business_value_measured=True)
    monkeypatch.setattr(integrated, "analyze_demo_business", fake_metrics)
    with pytest.raises(IntegratedSourceDenied):
        run_integrated_demo(query)


def test_integrated_report_requires_expected_input_type():
    report = run_integrated_demo(fixture())
    for invalid in (None, {}, 100, True, "report"):
        with pytest.raises(IntegratedSourceDenied):
            inspect_integrated_demo(invalid, fixture())


def test_cross_module_manifest_never_authorizes_a_provider():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["milestone"] == "P3-07"
    assert data["source_dependency"] == "P3-01_THROUGH_P3-06_DRAFTS"
    assert data["default_policy"] == "DENY"
    assert data["scope"] == "OFFLINE_SYNTHETIC_CONFORMANCE_ONLY"
    assert data["phase01_verified"] == 3
    assert data["phase02_operational_go"] is False
    assert data["independent_human_review_verified"] is False
    assert data["real_provider_execution_allowed"] is False
    assert data["production_dashboard_enabled"] is False
    assert data["release_authorized"] is False
    assert data["customer_data_used"] is False
    assert data["durable_audit_available"] is False


@pytest.mark.parametrize("op", tuple(OPERATION_SPECS))
def test_integrated_demo_cli_all_four_capabilities_remain_denied(op):
    p = subprocess.run(
        [sys.executable, str(CLI), "integrated-demo", op],
        check=False, timeout=20, capture_output=True, text=True,
    )
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert data["operation_id"] == op
    assert data["decision"] == "DENY"
    assert data["local_source_integrity_checked"] is True
    assert data["demo_source_consistent"] is True
    assert data["side_effects_performed"] is False
    assert data["real_revenue_measured"] is False
    assert data["release_authorized"] is False


def test_cli_expired_modified_state_and_two_fake_finance_reviewers():
    p = subprocess.run(
        [sys.executable, str(CLI), "integrated-demo",
         "business.finance.reconciliation-proposal.v1",
         "--observed-version", "2", "--observed-tick", "112",
         "--reviewer-count", "2"],
        check=False, timeout=20, capture_output=True, text=True,
    )
    assert p.returncode == 0, p.stderr
    result = json.loads(p.stdout)
    assert result["decision"] == "DENY"
    assert result["second_reviewer_needed"] is True
    assert result["demo_plan_expired"] is True
    assert result["demo_resource_unchanged"] is False
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in result["denial_reasons"]
    assert not result["execution_authorized"]


@pytest.mark.parametrize("args", [
    ["integrated-demo", "business.live.payment.v1"],
    ["integrated-demo", "business.inventory.stock-preview.v1", "--execute"],
    ["integrated-demo", "business.inventory.stock-preview.v1", "--observed-tick", "-1"],
    ["integrated-demo", "business.inventory.stock-preview.v1", "--reviewer-count", "3"],
    ["integrated-demo", "business.inventory.stock-preview.v1", "--request-id", "CLIENT-123"],
    ["integrated-demo", "business.inventory.stock-preview.v1", "--observed-version", "1001"],
])
def test_cli_rejects_live_like_commands(args):
    p = subprocess.run([sys.executable, str(CLI), *args],
                       check=False, timeout=20, capture_output=True, text=True)
    assert p.returncode != 0
    assert not p.stdout


def test_new_module_has_no_live_transport_or_persistent_store():
    src = (ROOT / "apps/api/app/phase03_integrated_conformance.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_integrated_conformance" not in main
    for forbidden in (
        "APIRouter(", "httpx", "requests.", "urllib.request", "urlopen(",
        "socket.socket(", "psycopg", "redis.", "subprocess.", "openai.",
    ):
        assert forbidden not in src
