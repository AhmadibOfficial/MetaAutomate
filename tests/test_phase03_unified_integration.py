"""P3-07 unified: one underlying negative-flow engine, two safe report shapes."""
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from app import phase03_integrated_conformance as adapter
from app import phase03_integration_safety as shared
from app.phase03_integration_safety import (
    OfflineIntegratedInput, run_offline_integration, audit_offline_contracts,
)

ROOT = Path(__file__).resolve().parents[1]


def request():
    return adapter.DemoIntegratedRequest(
        tenant_id=uuid4(), operation_id="business.inventory.stock-preview.v1",
        request_id="DEMO-REQ-UNIFIED-001",
        attempt_id="DEMO-ATTEMPT-UNIFIED-001",
    )


def test_adapter_uses_exact_one_shared_denial_engine(monkeypatch):
    calls = []
    original = shared.run_offline_integration

    def once(arg):
        calls.append(arg)
        return original(arg)

    # Import-binding patch is intentional; it proves the adapter uses the
    # shared implementation rather than an independently duplicated flow.
    monkeypatch.setattr(adapter, "run_offline_integration", once)
    inp = request()
    report = adapter.run_integrated_demo(inp)
    assert len(calls) == 1
    assert calls[0].operation_id == inp.operation_id
    assert calls[0].tenant_id == inp.tenant_id
    assert calls[0].attach_synthetic_analytics is True
    assert report.decision == "DENY"
    assert not report.provider_called
    assert not report.release_authorized


def test_richer_report_fields_are_derived_from_single_shared_trace():
    inp = request()
    shared_report = run_offline_integration(OfflineIntegratedInput(
        tenant_id=inp.tenant_id,
        operation_id=inp.operation_id,
        request_id=inp.request_id,
        attempt_id=inp.attempt_id,
        observed_tick=inp.observed_tick,
        observed_resource_version=inp.observed_version,
        reviewer_labels=inp.reviewer_labels,
        attach_synthetic_analytics=True,
    ))
    detailed = adapter.run_integrated_demo(inp)
    assert detailed.tenant_demo_marker == shared_report.tenant_marker
    assert detailed.capability_id == shared_report.capability_id
    assert detailed.admission_digest == shared_report.admission_digest
    assert detailed.planning_digest == shared_report.planning_digest
    assert detailed.execution_rejection_digest == shared_report.execution_rejection_digest
    assert detailed.demo_audit_hash == shared_report.demo_audit_hash
    assert detailed.hypothetical_net_minor == shared_report.hypothetical_net_minor
    assert detailed.required_scope == shared_report.required_scope
    assert detailed.denial_reasons == shared_report.mandatory_trust_checks_missing
    assert detailed.decision == shared_report.decision == "DENY"


def test_modified_shared_source_success_cannot_pass_adapter(monkeypatch):
    inp = request()
    original = adapter.run_offline_integration

    def fake(*args, **kwargs):
        return replace(original(*args, **kwargs), real_financial_result_measured=True)

    monkeypatch.setattr(adapter, "run_offline_integration", fake)
    with pytest.raises(adapter.IntegratedSourceDenied):
        adapter.run_integrated_demo(inp)


def test_the_facade_cannot_import_underlying_business_execution_components():
    content = (ROOT / "apps/api/app/phase03_integrated_conformance.py").read_text()
    assert "run_offline_integration" in content
    assert "from app.phase03_intelligent_ecosystem import" not in content
    assert "from app.phase03_capability_planning import" not in content
    assert "from app.phase03_outcome_verification import" not in content
    assert "from app.phase03_execution_rehearsal import" not in content
    assert "from app.phase03_business_analytics import" not in content
    assert "APIRouter(" not in content
    assert "socket.socket(" not in content


def test_combined_review_never_reports_real_environment_ready():
    audit = audit_offline_contracts()
    assert audit.contracts_checked == 8
    assert audit.decision == "DENY"
    assert not audit.external_services_verified
    assert not audit.independent_review_performed
    assert not audit.live_execution_authorized
