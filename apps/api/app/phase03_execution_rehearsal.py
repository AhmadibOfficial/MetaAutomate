"""P3-06: execution safety rehearsal that CAN ONLY REJECT.

This is not an executor and has no ALLOW path. Every effect, including reads,
is a DEMO request bound to a DENY plan. Invented reviewers are NOT human
approval. Synthetic SHA-256 audit chains are NOT signed, durable or trusted.
No I/O, network, provider calls, DB writes, message queues or customers.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from json import dumps
from re import fullmatch
from threading import RLock
from uuid import UUID

from app.phase03_capability_planning import (
    DemoPlanningRequest, OfflineCapabilityPlan, OfflinePlanDenied,
    inspect_denied_plan,
)
from app.phase03_outcome_verification import (
    DemoEvidenceRejected, make_demo_no_dispatch, make_demo_readback,
    verify_demo_negative_outcome,
)

MAX_ATTEMPTS = 64
MAX_PER_TENANT = 16
MAX_TENANTS = 16
MAX_TICK = 1_000_000
MISSING_TRUST = (
    "P01_FOUNDATION_NOT_APPROVED",
    "P02_OPERATIONAL_RELEASE_NOT_APPROVED",
    "P03_ACTOR_AND_SERVICE_IDENTITY_UNVERIFIED",
    "P03_TENANT_AND_SCOPE_UNVERIFIED",
    "P03_PROVIDER_CONSENT_AND_BOUNDARY_UNVERIFIED",
    "P03_APPROVAL_IS_DEMO_ONLY",
    "P03_NO_DURABLE_IDEMPOTENCY_OR_AUTHENTICATED_RECEIPT",
    "P03_NO_INDEPENDENT_PROVIDER_READBACK",
)
HALT_REASON = "STOP_NO_AUTOMATED_EXECUTION"
MODE = "DEMO_REHEARSAL_DENY_ONLY"


class ExecutionAttemptDenied(ValueError):
    """Cannot interpret submitted inputs as valid real-world authority."""


class DemoAuditNotFound(LookupError):
    """No audit record for this invented tenant/attempt."""


def _reject() -> None:
    raise ExecutionAttemptDenied("Controlled execution rehearsal denied")


@dataclass(frozen=True)
class DemoExecutionAttempt:
    plan: OfflineCapabilityPlan
    source_request: DemoPlanningRequest
    attempt_id: str
    observed_tick: int
    expected_resource_version: int
    reviewer_labels: tuple[str, ...] = ()
    mode: str = MODE
    claimed_approved: bool = False
    allow_side_effects: bool = False


@dataclass(frozen=True)
class ExecutionRejection:
    tenant_id: UUID
    attempt_id: str
    request_id: str
    operation_id: str
    effect: str
    target: str
    missing_trust_codes: tuple[str, ...]
    reviewer_count: int
    second_reviewer_needed: bool
    demo_plan_expired: bool
    simulated_no_dispatch_consistent: bool
    demo_resource_version_unchanged: bool
    recovery_note: str
    audit_fingerprint: str
    decision: str = "DENY"
    state: str = "REJECTED_NO_DISPATCH"
    actor_authenticated: bool = False
    human_approval_verified: bool = False
    tenant_scope_verified: bool = False
    side_effects_authorized: bool = False
    side_effects_performed: bool = False
    provider_called: bool = False
    provider_receipt_verified: bool = False
    independent_readback_performed: bool = False
    durable_idempotency_verified: bool = False
    compensation_performed: bool = False
    customer_data_accessed: bool = False
    release_authorized: bool = False


@dataclass(frozen=True)
class DemoAuditEntry:
    tenant_id: UUID
    attempt_id: str
    request_id: str
    audit_sequence: int
    previous_demo_hash: str
    rejection_fingerprint: str
    demo_chain_hash: str
    decision: str = "DENY"
    digest_is_authenticated: bool = False
    externally_persisted: bool = False
    audit_proof_is_durable: bool = False
    execution_authorized: bool = False


def _payload_hash(data: dict[str, object]) -> str:
    return sha256(dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _audit_input(report: ExecutionRejection) -> dict[str, object]:
    return {
        "domain": "metaautomate.phase03.controlled-execution-rehearsal.v1",
        "tenant": str(report.tenant_id),
        "attempt": report.attempt_id,
        "request": report.request_id,
        "operation": report.operation_id,
        "effect": report.effect,
        "target": report.target,
        "missing_trust_codes": list(report.missing_trust_codes),
        "reviewer_count": report.reviewer_count,
        "second_reviewer_needed": report.second_reviewer_needed,
        "demo_plan_expired": report.demo_plan_expired,
        "simulated_no_dispatch_consistent": report.simulated_no_dispatch_consistent,
        "demo_resource_version_unchanged": report.demo_resource_version_unchanged,
        "recovery_note": report.recovery_note,
        "decision": report.decision,
        "state": report.state,
        "side_effects_authorized": report.side_effects_authorized,
        "side_effects_performed": report.side_effects_performed,
    }


def _check(attempt: DemoExecutionAttempt) -> tuple[bool, bool]:
    if type(attempt) is not DemoExecutionAttempt:
        _reject()
    plan = attempt.plan
    if type(plan) is not OfflineCapabilityPlan or type(plan.tenant_id) is not UUID:
        _reject()
    if (type(attempt.attempt_id) is not str
            or fullmatch(r"DEMO-ATTEMPT-[A-Z0-9-]{3,40}", attempt.attempt_id) is None
            or type(attempt.observed_tick) is not int
            or not 0 <= attempt.observed_tick <= MAX_TICK
            or type(attempt.expected_resource_version) is not int
            or not 0 <= attempt.expected_resource_version <= 1000
            or type(attempt.reviewer_labels) is not tuple
            or len(attempt.reviewer_labels) > 2
            or type(attempt.mode) is not str or attempt.mode != MODE
            or attempt.claimed_approved is not False
            or attempt.allow_side_effects is not False):
        _reject()
    if any(
        type(label) is not str or
        fullmatch(r"DEMO-REVIEWER-[A-Z0-9-]{3,32}", label) is None
        for label in attempt.reviewer_labels
    ):
        _reject()
    if len(set(attempt.reviewer_labels)) != len(attempt.reviewer_labels):
        _reject()
    try:
        verdict = inspect_denied_plan(
            plan, attempt.source_request,
            observed_tick=attempt.observed_tick,
        )
    except (OfflinePlanDenied, ValueError, TypeError, AttributeError, KeyError):
        _reject()
    if not verdict.synthetic_integrity_consistent or not verdict.input_bound:
        _reject()
    if plan.decision != "DENY" or plan.execution_authorized:
        _reject()
    return verdict.expired, (
        attempt.expected_resource_version == plan.expected_resource_version
    )


def reject_demo_execution(attempt: DemoExecutionAttempt) -> ExecutionRejection:
    """Strictly offline outcome: REJECTED, even with invented reviewers."""
    expired, same_version = _check(attempt)
    plan = attempt.plan
    # This local no-dispatch evidence is *invented*. It can never show a real
    # provider effect or grant execution on its own.
    try:
        event = make_demo_no_dispatch(
            plan, attempt.source_request,
            event_id="DEMO-EVENT-EXECUTION-HALT",
            observed_tick=attempt.observed_tick,
        )
        read = make_demo_readback(
            plan, attempt.source_request, observed_tick=attempt.observed_tick,
            observed_version=attempt.expected_resource_version,
        )
        comparison = verify_demo_negative_outcome(
            plan, attempt.source_request, event, read,
            observed_tick=attempt.observed_tick,
        )
    except (DemoEvidenceRejected, ValueError, TypeError):
        _reject()
    missing = list(MISSING_TRUST)
    if plan.human_approval_required:
        missing.append("SPECIFIC_EFFECT_HUMAN_REVIEW_UNVERIFIED")
    if plan.high_risk_dual_review_required:
        missing.append("SECOND_INDEPENDENT_REVIEW_UNVERIFIED")
    if expired:
        missing.append("DEMO_PLAN_EXPIRED")
    if not same_version:
        missing.append("DEMO_RESOURCE_VERSION_CHANGED")
    if plan.effect == "propose_write":
        recovery = (
            "MANUAL_TRIAGE_ONLY_NO_WRITE_OCCURRED;"
            "FUTURE_REAL_EFFECT_REQUIRES_VERIFIED_REVERSAL_PLAN"
        )
    else:
        recovery = "NO_COMPENSATION_NEEDED_BECAUSE_NO_DISPATCH_OCCURRED"
    result = ExecutionRejection(
        tenant_id=plan.tenant_id, attempt_id=attempt.attempt_id,
        request_id=plan.request_id, operation_id=plan.operation_id,
        effect=plan.effect, target=plan.resource_label,
        missing_trust_codes=tuple(missing),
        reviewer_count=len(attempt.reviewer_labels),
        second_reviewer_needed=plan.high_risk_dual_review_required,
        demo_plan_expired=expired,
        simulated_no_dispatch_consistent=comparison.demo_evidence_consistent,
        demo_resource_version_unchanged=same_version,
        recovery_note=recovery,
        audit_fingerprint="",
    )
    return replace(result, audit_fingerprint=_payload_hash(_audit_input(result)))


class DemoExecutionAudit:
    """Bounded, same-process simulated hash chain. NEVER authoritative audit."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._entries: dict[
            tuple[UUID, str], tuple[DemoExecutionAttempt, ExecutionRejection, DemoAuditEntry]
        ] = {}
        self._last_hash: dict[UUID, str] = {}
        self._counts: dict[UUID, int] = {}

    def reject_once(
        self, attempt: DemoExecutionAttempt,
    ) -> tuple[ExecutionRejection, DemoAuditEntry]:
        result = reject_demo_execution(attempt)
        tenant = result.tenant_id
        key = (tenant, attempt.attempt_id)
        with self._lock:
            previous = self._entries.get(key)
            if previous is not None:
                if previous[0] != attempt or previous[1] != result:
                    _reject()
                return previous[1], previous[2]
            if (len(self._entries) >= MAX_ATTEMPTS
                    or self._counts.get(tenant, 0) >= MAX_PER_TENANT
                    or (tenant not in self._counts
                        and len(self._counts) >= MAX_TENANTS)):
                _reject()
            sequence = self._counts.get(tenant, 0) + 1
            previous_hash = self._last_hash.get(tenant, "0" * 64)
            link = {
                "domain": "metaautomate.p3-06.demo-audit-link.v1",
                "tenant": str(tenant), "sequence": sequence,
                "previous": previous_hash, "attempt": attempt.attempt_id,
                "rejection": result.audit_fingerprint,
            }
            entry = DemoAuditEntry(
                tenant_id=tenant, attempt_id=attempt.attempt_id,
                request_id=attempt.plan.request_id,
                audit_sequence=sequence, previous_demo_hash=previous_hash,
                rejection_fingerprint=result.audit_fingerprint,
                demo_chain_hash=_payload_hash(link),
            )
            self._entries[key] = (attempt, result, entry)
            self._counts[tenant] = sequence
            self._last_hash[tenant] = entry.demo_chain_hash
            return result, entry

    def inspect(
        self, *, tenant_id: UUID, attempt_id: str,
    ) -> DemoAuditEntry:
        if (type(tenant_id) is not UUID or type(attempt_id) is not str
                or fullmatch(r"DEMO-ATTEMPT-[A-Z0-9-]{3,40}", attempt_id) is None):
            _reject()
        with self._lock:
            entry = self._entries.get((tenant_id, attempt_id))
            if entry is None:
                raise DemoAuditNotFound("Synthetic audit entry unavailable")
            return entry[2]


@dataclass(frozen=True)
class DemoAuditInspection:
    demo_internal_links_consistent: bool
    entries_inspected: int
    decision: str = "DENY"
    trustworthy_external_evidence: bool = False
    signed_by_authoritative_identity: bool = False
    durable_storage_verified: bool = False
    real_execution_verified: bool = False


def verify_demo_audit_sequence(
    tenant_id: UUID,
    records: tuple[tuple[ExecutionRejection, DemoAuditEntry], ...],
) -> DemoAuditInspection:
    """Detect accidental chain corruption; attacker can recompute all hashes."""
    if (type(tenant_id) is not UUID or type(records) is not tuple
            or len(records) > MAX_PER_TENANT):
        _reject()
    current = "0" * 64
    valid = True
    for index, pair in enumerate(records, start=1):
        if type(pair) is not tuple or len(pair) != 2:
            _reject()
        report, entry = pair
        if type(report) is not ExecutionRejection or type(entry) is not DemoAuditEntry:
            _reject()
        material = _audit_input(report)
        link = {
            "domain": "metaautomate.p3-06.demo-audit-link.v1",
            "tenant": str(tenant_id), "sequence": index,
            "previous": current, "attempt": report.attempt_id,
            "rejection": report.audit_fingerprint,
        }
        valid &= (
            report.tenant_id == tenant_id and entry.tenant_id == tenant_id
            and report.decision == "DENY" and entry.decision == "DENY"
            and report.state == "REJECTED_NO_DISPATCH"
            and report.side_effects_performed is False
            and entry.execution_authorized is False
            and entry.digest_is_authenticated is False
            and entry.externally_persisted is False
            and entry.audit_proof_is_durable is False
            and entry.attempt_id == report.attempt_id
            and entry.request_id == report.request_id
            and entry.audit_sequence == index
            and entry.previous_demo_hash == current
            and type(report.audit_fingerprint) is str
            and report.audit_fingerprint == _payload_hash(material)
            and type(entry.rejection_fingerprint) is str
            and entry.rejection_fingerprint == report.audit_fingerprint
            and type(entry.demo_chain_hash) is str
            and entry.demo_chain_hash == _payload_hash(link)
        )
        current = entry.demo_chain_hash if type(entry.demo_chain_hash) is str else ""
    return DemoAuditInspection(
        demo_internal_links_consistent=bool(valid),
        entries_inspected=len(records),
    )
