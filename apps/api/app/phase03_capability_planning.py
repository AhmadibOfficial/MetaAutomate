"""P3-02: offline-only, deny-by-construction capability execution planning.

Planning here is a strict *negative design rehearsal*: no external actions, no
authorization of customer data, no human review, no execution. It consumes only
P3-01's synthetic DENY receipt. It cannot mint a trusted intent, grant, token,
approval, or provider receipt. All IDs and logical clocks are DEMO-only.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from re import fullmatch
from threading import RLock
from uuid import UUID

from app.phase03_intelligent_ecosystem import (
    CapabilityDenialReceipt, DemoCapabilityIntent, OPERATION_SPECS,
    verify_synthetic_denial,
)

TARGETS = {
    "business.lead-intake.validate.v1": "DEMO-TARGET-LEAD-001",
    "business.crm.sync-proposal.v1": "DEMO-TARGET-CRM-001",
    "business.inventory.stock-preview.v1": "DEMO-TARGET-STOCK-001",
    "business.finance.reconciliation-proposal.v1": "DEMO-TARGET-FINANCE-001",
}
# No condition in this list is assumed met, including source-only checks.
REQUIRED_GATES = (
    "trusted_actor_identity",
    "trusted_service_identity_and_revocation",
    "authoritative_tenant_resource_ownership",
    "server_issued_scoped_credential",
    "provider_binding_and_allowlist",
    "approved_private_staging",
    "enforced_source_and_release_review",
    "durable_transactional_replay_protection",
    "customer_privacy_and_processing_authorization",
    "independent_execution_result_verification",
)
MAX_PLANS = 64
MAX_PER_TENANT = 16
MAX_TENANTS = 16
TTL_TICKS = 10
MAX_TICK = 1_000_000


class OfflinePlanDenied(ValueError):
    """No valid DEMO plan can be interpreted as execution permission."""


class OfflinePlanNotFound(LookupError):
    """Absent and cross-tenant DEMO plans are indistinguishable."""


def _deny() -> None:
    raise OfflinePlanDenied("Synthetic capability plan rejected")


@dataclass(frozen=True)
class DemoPlanningRequest:
    intent: DemoCapabilityIntent
    denial_receipt: CapabilityDenialReceipt
    target_label: str
    expected_resource_version: int
    requested_tick: int


@dataclass(frozen=True)
class OfflineCapabilityPlan:
    tenant_id: UUID
    tenant_demo_marker: str
    request_id: str
    operation_id: str
    capability_id: str
    effect: str
    resource_label: str
    expected_resource_version: int
    required_scope: str
    human_approval_required: bool
    high_risk_dual_review_required: bool
    logical_tick: int
    expires_tick: int
    admission_receipt_checksum: str
    mandatory_unverified_gates: tuple[str, ...]
    review_steps: tuple[str, ...]
    checksum: str
    decision: str = "DENY"
    lifecycle: str = "DESIGN_ONLY_NOT_EXECUTABLE"
    execution_authorized: bool = False
    execution_performed: bool = False
    workflow_enqueued: bool = False
    provider_called: bool = False
    provider_receipt_verified: bool = False
    human_approval_verified: bool = False
    tenant_authentication_verified: bool = False
    scope_verified: bool = False
    durable_idempotency_verified: bool = False
    persisted: bool = False


def _material(plan: OfflineCapabilityPlan) -> dict[str, object]:
    # Hash binds the entire present plan, excluding checksum, but offers no
    # authenticity, immutable logging or tamper resistance against its author.
    from dataclasses import asdict
    data = asdict(plan)
    data.pop("checksum")
    data["tenant_id"] = str(plan.tenant_id)
    return data


def _fingerprint(plan: OfflineCapabilityPlan) -> str:
    payload = json.dumps(_material(plan), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _validate(request: DemoPlanningRequest) -> None:
    if type(request) is not DemoPlanningRequest:
        _deny()
    intent = request.intent
    if type(intent) is not DemoCapabilityIntent or type(intent.tenant_id) is not UUID:
        _deny()
    if type(request.denial_receipt) is not CapabilityDenialReceipt:
        _deny()
    if (type(request.target_label) is not str
            or request.target_label != TARGETS.get(intent.operation_id)
            or type(request.expected_resource_version) is not int
            or not 1 <= request.expected_resource_version <= 1000
            or type(request.requested_tick) is not int
            or type(intent.logical_tick) is not int
            or not 0 <= request.requested_tick <= MAX_TICK - TTL_TICKS
            or request.requested_tick != intent.logical_tick
            or not fullmatch(r"DEMO-TARGET-[A-Z0-9-]{4,48}", request.target_label)):
        _deny()
    try:
        verdict = verify_synthetic_denial(request.denial_receipt, intent)
    except (ValueError, TypeError, AttributeError):
        _deny()
    if not verdict.synthetic_checksum_consistent or not verdict.request_matches:
        _deny()


def create_denied_plan(request: DemoPlanningRequest) -> OfflineCapabilityPlan:
    """Pure planning preview. Never returns an executable plan or usable grant."""
    _validate(request)
    intent = request.intent
    receipt = request.denial_receipt
    spec = OPERATION_SPECS[intent.operation_id]
    high_risk = spec[3] == "high" and spec[4] is True
    review = (
        ("DEMO_HUMAN_REVIEW_NOT_VERIFIED",)
        if spec[4] else ("HUMAN_REVIEW_NOT_APPLICABLE_NO_GRANT",)
    )
    if high_risk:
        review += ("DEMO_SECOND_REVIEWER_NOT_VERIFIED",)
    review += (
        "REVALIDATE_IDENTITY_SCOPE_TENANT_AT_EXECUTION",
        "REJECT_IF_RESOURCE_VERSION_CHANGED",
        "REQUIRE_AUTHORITATIVE_RECEIPT_AND_INDEPENDENT_READBACK",
        "STOP_NO_AUTOMATED_EXECUTION",
    )
    draft = OfflineCapabilityPlan(
        tenant_id=intent.tenant_id,
        tenant_demo_marker=receipt.tenant_demo_marker,
        request_id=intent.request_id,
        operation_id=intent.operation_id,
        capability_id=spec[0],
        effect=spec[1],
        resource_label=request.target_label,
        expected_resource_version=request.expected_resource_version,
        required_scope=spec[2],
        human_approval_required=spec[4],
        high_risk_dual_review_required=high_risk,
        logical_tick=request.requested_tick,
        expires_tick=request.requested_tick + TTL_TICKS,
        admission_receipt_checksum=receipt.checksum,
        mandatory_unverified_gates=REQUIRED_GATES +
        (("specific_effect_approval_unverified",) if spec[4] else ()),
        review_steps=review,
        checksum="",
    )
    return replace(draft, checksum=_fingerprint(draft))


@dataclass(frozen=True)
class OfflinePlanCheck:
    synthetic_integrity_consistent: bool
    input_bound: bool
    expired: bool
    decision: str = "DENY"
    actor_identity_verified: bool = False
    tenant_scope_verified: bool = False
    effective_permission_granted: bool = False
    execution_authorized: bool = False
    provider_called: bool = False
    authoritative_receipt_verified: bool = False


def inspect_denied_plan(
    plan: OfflineCapabilityPlan, expected: DemoPlanningRequest, *,
    observed_tick: int,
) -> OfflinePlanCheck:
    _validate(expected)
    if (type(plan) is not OfflineCapabilityPlan
            or type(observed_tick) is not int
            or not 0 <= observed_tick <= MAX_TICK):
        _deny()
    expected_plan = create_denied_plan(expected)
    # Equality with a freshly reconstructed plan also catches a fully
    # recomputed but otherwise inconsistent hash.
    same = plan == expected_plan
    return OfflinePlanCheck(
        synthetic_integrity_consistent=(
            type(plan.checksum) is str
            and plan.checksum == _fingerprint(plan)
            and same
        ),
        input_bound=same,
        expired=observed_tick > expected_plan.expires_tick,
    )


class OfflineCapabilityPlanRegistry:
    """Bounded instance-local replay protection. NOT durable or distributed."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_key: dict[
            tuple[UUID, str], tuple[DemoPlanningRequest, OfflineCapabilityPlan]
        ] = {}
        self._counts: dict[UUID, int] = {}

    def plan_once(self, request: DemoPlanningRequest) -> OfflineCapabilityPlan:
        # Validation strictly precedes cache access; no invalid input can
        # return a previously stored plan.
        plan = create_denied_plan(request)
        tenant = request.intent.tenant_id
        key = (tenant, request.intent.request_id)
        with self._lock:
            previous = self._by_key.get(key)
            if previous is not None:
                if previous[0] != request:
                    _deny()
                return previous[1]
            if (
                len(self._by_key) >= MAX_PLANS
                or self._counts.get(tenant, 0) >= MAX_PER_TENANT
                or (tenant not in self._counts and len(self._counts) >= MAX_TENANTS)
            ):
                _deny()
            self._by_key[key] = (request, plan)
            self._counts[tenant] = self._counts.get(tenant, 0) + 1
            return plan

    def inspect(
        self, *, tenant_id: UUID, request_id: str,
    ) -> OfflineCapabilityPlan:
        if (type(tenant_id) is not UUID or type(request_id) is not str
                or not fullmatch(r"DEMO-REQ-[A-Z0-9-]{3,48}", request_id)):
            _deny()
        with self._lock:
            item = self._by_key.get((tenant_id, request_id))
            if item is None:
                raise OfflinePlanNotFound("Synthetic plan not available")
            return item[1]
