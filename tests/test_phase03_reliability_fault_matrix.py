"""P3-08: deterministic hostile-state matrix and injected-success rejection.

Every replay is invented. Passing never verifies real authorization, customers,
service identity, an actual provider readback, or durable audit controls.
"""
from dataclasses import replace
from uuid import uuid4

import pytest

from app import phase03_integrated_conformance as integrated
from app.phase03_intelligent_ecosystem import OPERATION_SPECS


def _case(op="business.inventory.stock-preview.v1", *, tick=101,
          version=1, reviewers=0):
    return integrated.DemoIntegratedRequest(
        tenant_id=uuid4(), operation_id=op,
        request_id="DEMO-REQ-P308-REGRESSION",
        attempt_id="DEMO-ATTEMPT-P308-REGRESSION",
        observed_tick=tick, observed_version=version,
        reviewer_labels=(
            "DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA",
        )[:reviewers],
    )


@pytest.mark.parametrize("op", tuple(OPERATION_SPECS))
@pytest.mark.parametrize("tick", (100, 101, 109, 110, 111, 112))
@pytest.mark.parametrize("version", (0, 1, 2))
@pytest.mark.parametrize("reviewers", (0, 1, 2))
def test_combinatorial_lifecycle_never_produces_real_effects(
    op, tick, version, reviewers,
):
    query = _case(op, tick=tick, version=version, reviewers=reviewers)
    report = integrated.run_integrated_demo(query)
    assert report.decision == "DENY"
    assert report.demo_source_consistent
    assert report.demo_resource_unchanged is (version == 1)
    assert report.demo_plan_expired is (tick > 110)
    assert report.side_effects_performed is False
    assert report.provider_called is False
    assert report.execution_authorized is False
    assert report.real_revenue_measured is False
    assert report.independent_security_review_complete is False
    assert report.audit_durable is False
    assert report.release_authorized is False
    assert integrated.inspect_integrated_demo(report, query)
    if reviewers == 2 and op == "business.finance.reconciliation-proposal.v1":
        assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in report.denial_reasons
    if tick > 110:
        assert "DEMO_PLAN_EXPIRED" in report.denial_reasons
    if version != 1:
        assert "DEMO_RESOURCE_VERSION_CHANGED" in report.denial_reasons


@pytest.mark.parametrize("field", [
    "actor_authenticated",
    "human_approval_verified",
    "tenant_scope_verified",
    "side_effects_authorized",
    "provider_receipt_verified",
    "independent_readback_performed",
    "durable_idempotency_verified",
    "compensation_performed",
    "customer_data_accessed",
])
def test_forged_rejection_success_signal_fails_close(monkeypatch, field):
    original = integrated.DemoExecutionAudit

    class TamperAudit(original):
        def reject_once(self, attempt):
            report, entry = super().reject_once(attempt)
            return replace(report, **{field: True}), entry

    monkeypatch.setattr(integrated, "DemoExecutionAudit", TamperAudit)
    with pytest.raises(integrated.IntegratedSourceDenied):
        integrated.run_integrated_demo(_case())


@pytest.mark.parametrize("field", [
    "external_authorization_verified",
    "authoritative_provider_receipt_verified",
    "provider_readback_performed",
    "customer_data_processed",
    "release_authorized",
    "independently_observed_real_outcome",
    "execution_verified",
])
def test_forged_verification_success_signal_fails_close(monkeypatch, field):
    original = integrated.verify_demo_negative_outcome

    def falsified(*args, **kwargs):
        return replace(original(*args, **kwargs), **{field: True})

    monkeypatch.setattr(integrated, "verify_demo_negative_outcome", falsified)
    with pytest.raises(integrated.IntegratedSourceDenied):
        integrated.run_integrated_demo(_case())


@pytest.mark.parametrize("field", [
    "revenue_verified",
    "profitability_verified",
    "live_provider_called",
    "customer_data_processed",
    "business_value_measured",
    "execution_authorized",
])
def test_forged_financial_success_signal_fails_close(monkeypatch, field):
    original = integrated.analyze_demo_business

    def falsified(*args, **kwargs):
        return replace(original(*args, **kwargs), **{field: True})

    monkeypatch.setattr(integrated, "analyze_demo_business", falsified)
    with pytest.raises(integrated.IntegratedSourceDenied):
        integrated.run_integrated_demo(_case())
