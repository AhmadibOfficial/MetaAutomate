"""P3-07 source-only cross-module conformance: no effects, no trusted evidence.

Reconstructs the same local DEMO request across P3-01 (admission), P3-02
(planning), P3-03 (negative evidence), P3-04 (invented KPI arithmetic),
P3-05 (source SDK spec), and P3-06 (execution rejection/audit). This is
not an agent, service, externally signed trace, true ROI, or execution path.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from app.phase03_intelligent_ecosystem import (
    DemoCapabilityIntent, OfflineCapabilityPreview, OPERATION_SPECS,
    verify_synthetic_denial,
)
from app.phase03_capability_planning import (
    DemoPlanningRequest, TARGETS, create_denied_plan, inspect_denied_plan,
)
from app.phase03_outcome_verification import (
    make_demo_no_dispatch, make_demo_readback, verify_demo_negative_outcome,
)
from app.phase03_business_analytics import (
    analyze_demo_business, demo_business_fixture,
)
from app.phase03_developer_tools import source_spec, validate_source_spec
from app.phase03_execution_rehearsal import (
    DemoExecutionAttempt, DemoExecutionAudit, verify_demo_audit_sequence,
)

MAX_TICK = 1_000_000
ACTOR = "DEMO-ACTOR-CONFORMANCE"


class IntegratedSourceDenied(ValueError):
    """Only exactly reconstructed, DENY-only synthetic integrations are valid."""


def _reject() -> None:
    raise IntegratedSourceDenied("Phase 03 offline integration rejected")


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


def _check(request: DemoIntegratedRequest) -> None:
    if type(request) is not DemoIntegratedRequest:
        _reject()
    if (type(request.tenant_id) is not UUID
            or type(request.operation_id) is not str
            or request.operation_id not in OPERATION_SPECS
            or type(request.request_id) is not str
            or type(request.attempt_id) is not str
            or type(request.observed_tick) is not int
            or not 100 <= request.observed_tick <= MAX_TICK
            or type(request.observed_version) is not int
            or not 0 <= request.observed_version <= 1000
            or type(request.reviewer_labels) is not tuple
            or len(request.reviewer_labels) > 2):
        _reject()
    # Any invalid synthetic ID or reviewer is refused by source modules, too.
    if request.reviewer_labels and len(set(
        label for label in request.reviewer_labels if type(label) is str
    )) != len(request.reviewer_labels):
        _reject()


def run_integrated_demo(request: DemoIntegratedRequest) -> OfflineIntegratedReport:
    """In-memory source reconciliation; no trust is acquired anywhere."""
    _check(request)
    try:
        spec = source_spec()
        validate_source_spec(spec)
        if (
            spec["transport"] != "NONE"
            or spec["production_ready"] is not False
            or spec["external_provider_access_enabled"] is not False
            or request.operation_id not in spec["operations"]
        ):
            _reject()
        op = request.operation_id
        intent = DemoCapabilityIntent(
            tenant_id=request.tenant_id, actor_label=ACTOR,
            request_id=request.request_id, operation_id=op,
            scenario=OPERATION_SPECS[op][5], logical_tick=100,
        )
        receipt = OfflineCapabilityPreview().inspect_once(intent)
        origin_check = verify_synthetic_denial(receipt, intent)
        planning_request = DemoPlanningRequest(
            intent=intent, denial_receipt=receipt, target_label=TARGETS[op],
            expected_resource_version=1, requested_tick=100,
        )
        plan = create_denied_plan(planning_request)
        plan_check = inspect_denied_plan(
            plan, planning_request, observed_tick=request.observed_tick,
        )
        event = make_demo_no_dispatch(
            plan, planning_request, event_id="DEMO-EVENT-INTEGRATION-HALT",
            observed_tick=request.observed_tick,
        )
        snapshot = make_demo_readback(
            plan, planning_request, observed_tick=request.observed_tick,
            observed_version=request.observed_version,
        )
        verification = verify_demo_negative_outcome(
            plan, planning_request, event, snapshot,
            observed_tick=request.observed_tick,
        )
        attempt = DemoExecutionAttempt(
            plan=plan, source_request=planning_request,
            attempt_id=request.attempt_id, observed_tick=request.observed_tick,
            expected_resource_version=request.observed_version,
            reviewer_labels=request.reviewer_labels,
        )
        rejection, audit = DemoExecutionAudit().reject_once(attempt)
        audit_check = verify_demo_audit_sequence(
            request.tenant_id, ((rejection, audit),),
        )
        metrics = analyze_demo_business(
            request.tenant_id, demo_business_fixture(request.tenant_id),
        )
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        _reject()
    consistent = (
        type(origin_check.synthetic_checksum_consistent) is bool
        and origin_check.synthetic_checksum_consistent
        and origin_check.request_matches
        and plan_check.synthetic_integrity_consistent
        and plan_check.input_bound
        and verification.demo_evidence_consistent
        and audit_check.demo_internal_links_consistent
        and receipt.decision == plan.decision == rejection.decision == "DENY"
        and verification.decision == metrics.decision == "DENY"
        and receipt.tenant_id == plan.tenant_id == rejection.tenant_id
        and receipt.operation_id == plan.operation_id == rejection.operation_id
        and receipt.capability_id == plan.capability_id
        and receipt.required_scope == plan.required_scope
        and receipt.request_id == plan.request_id == rejection.request_id
        and rejection.attempt_id == audit.attempt_id
        and not any((
            receipt.execution_authorized,
            plan.execution_authorized, rejection.side_effects_performed,
            rejection.provider_called, verification.execution_verified,
            metrics.business_value_measured, audit.execution_authorized,
            rejection.release_authorized, audit.digest_is_authenticated,
            audit.externally_persisted, audit.audit_proof_is_durable,
        ))
    )
    if not consistent:
        _reject()
    return OfflineIntegratedReport(
        tenant_demo_marker=receipt.tenant_demo_marker,
        operation_id=op, request_id=intent.request_id,
        capability_id=plan.capability_id, effect=plan.effect,
        required_scope=plan.required_scope,
        admission_digest=receipt.checksum,
        planning_digest=plan.checksum,
        execution_rejection_digest=rejection.audit_fingerprint,
        demo_audit_hash=audit.demo_chain_hash,
        denial_reasons=rejection.missing_trust_codes,
        second_reviewer_needed=rejection.second_reviewer_needed,
        demo_plan_expired=plan_check.expired,
        demo_resource_unchanged=verification.demo_state_unchanged,
        synthetic_business_periods=len(metrics.periods),
        hypothetical_net_minor=metrics.hypothetical_net_minor,
        demo_source_consistent=True,
    )


def inspect_integrated_demo(
    report: OfflineIntegratedReport,
    expected_request: DemoIntegratedRequest,
) -> bool:
    """Equality to a newly rebuilt DENY trace, not authentication or approval.

    All data is author-controlled. Even a perfect comparison grants no
    identity, execution, true business value or external evidence.
    """
    _check(expected_request)
    if type(report) is not OfflineIntegratedReport:
        _reject()
    # Cannot accept extra caller-controlled "approved" fields: the dataclass
    # must match the fresh offline result exactly.
    return report == run_integrated_demo(expected_request)
