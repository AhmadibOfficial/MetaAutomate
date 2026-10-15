"""P3-07 compatibility view over the ONE shared offline-denial integration engine.

This facade preserves PR #50's richer review report and existing CLI/test
contract without duplicating cross-module request execution or denial logic.
Everything is synthetic, untrusted, nonexecuting and always DENY.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.phase03_integration_safety import (
    OfflineIntegratedInput, OfflineIntegrationDenied, run_offline_integration,
    audit_offline_contracts,
)


class IntegratedSourceDenied(ValueError):
    """The requested DEMO trace cannot be verified by the shared engine."""


def _deny() -> None:
    raise IntegratedSourceDenied("Phase 03 source conformance rejected")


@dataclass(frozen=True)
class DemoIntegratedRequest:
    tenant_id: UUID
    operation_id: str
    request_id: str
    attempt_id: str
    observed_tick: int = 101
    observed_version: int = 1
    reviewer_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class OfflineIntegratedReport:
    tenant_demo_marker: str
    operation_id: str
    request_id: str
    capability_id: str
    effect: str
    required_scope: str
    admission_digest: str
    planning_digest: str
    execution_rejection_digest: str
    demo_audit_hash: str
    denial_reasons: tuple[str, ...]
    second_reviewer_needed: bool
    demo_plan_expired: bool
    demo_resource_unchanged: bool
    synthetic_business_periods: int
    hypothetical_net_minor: int
    demo_source_consistent: bool
    decision: str = "DENY"
    finding: str = "SYNTHETIC_CROSS_MODULE_DENIAL_ONLY"
    source: str = "UNAUTHENTICATED_INVENTED_FIXTURES"
    execution_authorized: bool = False
    side_effects_performed: bool = False
    provider_called: bool = False
    provider_result_verified: bool = False
    independent_security_review_complete: bool = False
    real_revenue_measured: bool = False
    customer_data_processed: bool = False
    audit_durable: bool = False
    production_ready: bool = False
    release_authorized: bool = False


def _convert(request: DemoIntegratedRequest) -> OfflineIntegratedInput:
    if type(request) is not DemoIntegratedRequest:
        _deny()
    return OfflineIntegratedInput(
        tenant_id=request.tenant_id,
        operation_id=request.operation_id,
        request_id=request.request_id,
        attempt_id=request.attempt_id,
        observed_tick=request.observed_tick,
        observed_resource_version=request.observed_version,
        reviewer_labels=request.reviewer_labels,
        attach_synthetic_analytics=True,
    )


def run_integrated_demo(request: DemoIntegratedRequest) -> OfflineIntegratedReport:
    """Reformat shared DENY evidence; no second copy of the execution flow."""
    try:
        # This local manifest check is NOT a provider trust or release gate.
        source = audit_offline_contracts()
        if source.decision != "DENY" or not source.controls_denied:
            _deny()
        integrated = run_offline_integration(_convert(request))
    except (OfflineIntegrationDenied, ValueError, TypeError, AttributeError, KeyError):
        _deny()
    if (
        integrated.decision != "DENY"
        or integrated.audited_denial_consistent is not True
        or integrated.denial_receipt_consistent is not True
        or integrated.denied_plan_consistent is not True
        or integrated.negative_evidence_consistent is not True
        or integrated.business_effect_performed is not False
        or integrated.actual_authorization_verified is not False
        or integrated.provider_called is not False
        or integrated.real_financial_result_measured is not False
        or integrated.release_authorized is not False
        or integrated.synthetic_business_periods == 0
    ):
        _deny()
    return OfflineIntegratedReport(
        tenant_demo_marker=integrated.tenant_marker,
        operation_id=integrated.operation_id,
        request_id=integrated.request_id,
        capability_id=integrated.capability_id,
        effect=integrated.effect,
        required_scope=integrated.required_scope,
        admission_digest=integrated.admission_digest,
        planning_digest=integrated.planning_digest,
        execution_rejection_digest=integrated.execution_rejection_digest,
        demo_audit_hash=integrated.demo_audit_hash,
        denial_reasons=integrated.mandatory_trust_checks_missing,
        second_reviewer_needed=integrated.second_reviewer_needed,
        demo_plan_expired=integrated.demo_plan_expired,
        demo_resource_unchanged=integrated.invented_state_unchanged,
        synthetic_business_periods=integrated.synthetic_business_periods,
        hypothetical_net_minor=integrated.hypothetical_net_minor,
        demo_source_consistent=True,
    )


def inspect_integrated_demo(
    report: OfflineIntegratedReport,
    expected_request: DemoIntegratedRequest,
) -> bool:
    """Compare to independently re-created DEMO result, not an authentic grant."""
    _convert(expected_request)
    if type(report) is not OfflineIntegratedReport:
        _deny()
    return report == run_integrated_demo(expected_request)
