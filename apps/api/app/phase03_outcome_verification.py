"""P3-03: local NEGATIVE outcome evidence verification, not business verification.

Only consistent DEMO evidence for "the planned action was NOT dispatched"
may be described. It never accepts provider receipts, customer data, outside
authorization, success claims, or independent real readback. All DEMO checksums
are non-secret, unauthenticated and recalculable by an attacker.
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

EVIDENCE_SCHEMA = "metaautomate.p3.synthetic-denial-evidence.v1"
EVIDENCE_KIND = "DEMO_NOT_DISPATCHED"
READBACK_KIND = "DEMO_UNCHANGED_LOCAL_FIXTURE"
MAX_EVENTS = 64
MAX_PER_TENANT = 16
MAX_TENANTS = 16
MAX_TICK = 1_000_000


class DemoEvidenceRejected(ValueError):
    """Reject evidence claiming untrusted or unsupported results."""


class DemoEvidenceNotFound(LookupError):
    """No data about a real provider or foreign tenant can be disclosed."""


def _reject() -> None:
    raise DemoEvidenceRejected("Synthetic negative outcome evidence rejected")


def _hash_payload(fields: dict) -> str:
    encoded = dumps(fields, sort_keys=True, ensure_ascii=True,
                    separators=(",", ":"), allow_nan=False).encode("ascii")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DemoNoDispatchEvent:
    tenant_id: UUID
    request_id: str
    operation_id: str
    target: str
    plan_checksum: str
    event_id: str
    observed_tick: int
    kind: str
    digest: str
    schema: str = EVIDENCE_SCHEMA
    dispatch_performed: bool = False
    provider_called: bool = False
    authoritative_receipt: bool = False


@dataclass(frozen=True)
class DemoReadbackFixture:
    tenant_id: UUID
    request_id: str
    operation_id: str
    target: str
    plan_checksum: str
    claimed_source: str
    expected_version: int
    observed_version: int
    observed_tick: int
    kind: str
    digest: str
    provider_read_performed: bool = False
    externally_authenticated: bool = False
    real_customer_data_accessed: bool = False


@dataclass(frozen=True)
class NegativeOutcomeAssessment:
    tenant_id: UUID
    request_id: str
    operation_id: str
    demo_evidence_consistent: bool
    demo_state_unchanged: bool
    plan_within_demo_expiry: bool
    reasons: tuple[str, ...]
    decision: str = "DENY"
    finding: str = "DEMO_NEGATIVE_CONTROL_UNVERIFIED"
    execution_verified: bool = False
    independently_observed_real_outcome: bool = False
    authoritative_provider_receipt_verified: bool = False
    provider_readback_performed: bool = False
    customer_data_processed: bool = False
    external_authorization_verified: bool = False
    release_authorized: bool = False


def _event_material(event: DemoNoDispatchEvent) -> dict:
    return {
        "schema": event.schema, "tenant": str(event.tenant_id),
        "request": event.request_id, "operation": event.operation_id,
        "target": event.target, "plan_checksum": event.plan_checksum,
        "event_id": event.event_id, "tick": event.observed_tick,
        "kind": event.kind, "dispatch_performed": event.dispatch_performed,
        "provider_called": event.provider_called,
        "authoritative_receipt": event.authoritative_receipt,
    }


def _read_material(view: DemoReadbackFixture) -> dict:
    return {
        "tenant": str(view.tenant_id), "request": view.request_id,
        "operation": view.operation_id, "target": view.target,
        "plan_checksum": view.plan_checksum, "source": view.claimed_source,
        "expected_version": view.expected_version,
        "observed_version": view.observed_version, "tick": view.observed_tick,
        "kind": view.kind, "provider_read_performed": view.provider_read_performed,
        "externally_authenticated": view.externally_authenticated,
        "real_customer_data_accessed": view.real_customer_data_accessed,
    }


def _check_pair(plan: OfflineCapabilityPlan,
                request: DemoPlanningRequest, tick: int) -> bool:
    if type(tick) is not int or not 0 <= tick <= MAX_TICK:
        _reject()
    try:
        assessment = inspect_denied_plan(plan, request, observed_tick=tick)
    except (OfflinePlanDenied, AttributeError, KeyError, TypeError, ValueError):
        _reject()
    if not assessment.synthetic_integrity_consistent or not assessment.input_bound:
        _reject()
    if not (type(plan.tenant_id) is UUID and
            type(plan.request_id) is str and
            type(plan.operation_id) is str):
        _reject()
    return not assessment.expired


def make_demo_no_dispatch(
    plan: OfflineCapabilityPlan, request: DemoPlanningRequest, *,
    event_id: str, observed_tick: int,
) -> DemoNoDispatchEvent:
    """Create only a fake non-dispatch record; this is NOT a provider receipt."""
    _check_pair(plan, request, observed_tick)
    if type(event_id) is not str or fullmatch(
        r"DEMO-EVENT-[A-Z0-9-]{3,40}", event_id,
    ) is None:
        _reject()
    draft = DemoNoDispatchEvent(
        tenant_id=plan.tenant_id, request_id=plan.request_id,
        operation_id=plan.operation_id, target=plan.resource_label,
        plan_checksum=plan.checksum, event_id=event_id,
        observed_tick=observed_tick, kind=EVIDENCE_KIND, digest="",
    )
    return replace(draft, digest=_hash_payload(_event_material(draft)))


def make_demo_readback(
    plan: OfflineCapabilityPlan, request: DemoPlanningRequest, *,
    observed_tick: int, observed_version: int | None = None,
) -> DemoReadbackFixture:
    """Locally invented version snapshot; no provider lookup or client reads."""
    _check_pair(plan, request, observed_tick)
    if observed_version is None:
        observed_version = plan.expected_resource_version
    if (type(observed_version) is not int or
            not 0 <= observed_version <= 1000):
        _reject()
    draft = DemoReadbackFixture(
        tenant_id=plan.tenant_id, request_id=plan.request_id,
        operation_id=plan.operation_id, target=plan.resource_label,
        plan_checksum=plan.checksum,
        claimed_source="DEMO-STATIC-LOCAL-FIXTURE-ONLY",
        expected_version=plan.expected_resource_version,
        observed_version=observed_version,
        observed_tick=observed_tick, kind=READBACK_KIND,
        digest="",
    )
    return replace(draft, digest=_hash_payload(_read_material(draft)))


def verify_demo_negative_outcome(
    plan: OfflineCapabilityPlan, request: DemoPlanningRequest,
    no_dispatch: DemoNoDispatchEvent, readback: DemoReadbackFixture,
    *, observed_tick: int,
) -> NegativeOutcomeAssessment:
    """Independently reconstruct two local DEMO fixtures, not an outside source.

    Invalid or forged fixtures are *rejected*, not accepted. A consistent
    negative simulation is still UNVERIFIED externally and decision=DENY.
    """
    plan_is_current = _check_pair(plan, request, observed_tick)
    if (type(no_dispatch) is not DemoNoDispatchEvent
            or type(readback) is not DemoReadbackFixture):
        _reject()
    if (type(no_dispatch.observed_tick) is not int
            or type(readback.observed_tick) is not int
            or no_dispatch.observed_tick > observed_tick
            or readback.observed_tick > observed_tick
            or no_dispatch.observed_tick < plan.logical_tick
            or readback.observed_tick < plan.logical_tick):
        _reject()
    expected_event = make_demo_no_dispatch(
        plan, request, event_id=no_dispatch.event_id,
        observed_tick=no_dispatch.observed_tick,
    )
    expected_snapshot = make_demo_readback(
        plan, request, observed_tick=readback.observed_tick,
        observed_version=readback.observed_version,
    )
    if (type(no_dispatch.digest) is not str
            or type(readback.digest) is not str
            or no_dispatch.digest != _hash_payload(_event_material(no_dispatch))
            or readback.digest != _hash_payload(_read_material(readback))
            or no_dispatch != expected_event
            or readback != expected_snapshot):
        _reject()
    unchanged = readback.observed_version == plan.expected_resource_version
    reasons = ["real_provider_receipt_unavailable",
               "real_provider_readback_unavailable",
               "independent_real_identity_unavailable",
               "phase02_live_release_not_authorized"]
    if not unchanged:
        reasons.append("demo_resource_version_changed")
    if not plan_is_current:
        reasons.append("demo_plan_expired")
    return NegativeOutcomeAssessment(
        tenant_id=plan.tenant_id, request_id=plan.request_id,
        operation_id=plan.operation_id,
        demo_evidence_consistent=True, demo_state_unchanged=unchanged,
        plan_within_demo_expiry=plan_is_current,
        reasons=tuple(reasons),
        finding=(
            "DEMO_NO_DISPATCH_CONSISTENT_NOT_EXTERNAL_VERIFICATION"
            if unchanged and plan_is_current
            else "DEMO_NEGATIVE_CONTROL_UNVERIFIED"
        ),
    )


class OfflineEvidenceRegistry:
    """Bounded one-process negative demo replay index, never a durable ledger."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._events: dict[
            tuple[UUID, str], tuple[DemoNoDispatchEvent, NegativeOutcomeAssessment]
        ] = {}
        self._counts: dict[UUID, int] = {}

    def record_once(self, *, plan: OfflineCapabilityPlan,
                    request: DemoPlanningRequest,
                    no_dispatch: DemoNoDispatchEvent,
                    readback: DemoReadbackFixture,
                    observed_tick: int) -> NegativeOutcomeAssessment:
        result = verify_demo_negative_outcome(
            plan, request, no_dispatch, readback, observed_tick=observed_tick,
        )
        with self._lock:
            key = (plan.tenant_id, no_dispatch.event_id)
            previous = self._events.get(key)
            if previous is not None:
                if (previous[0] != no_dispatch or previous[1] != result):
                    _reject()
                return previous[1]
            if (len(self._events) >= MAX_EVENTS
                    or self._counts.get(plan.tenant_id, 0) >= MAX_PER_TENANT
                    or (plan.tenant_id not in self._counts
                        and len(self._counts) >= MAX_TENANTS)):
                _reject()
            self._events[key] = (no_dispatch, result)
            self._counts[plan.tenant_id] = (
                self._counts.get(plan.tenant_id, 0) + 1
            )
            return result

    def inspect(self, *, tenant_id: UUID, event_id: str) -> NegativeOutcomeAssessment:
        if (type(tenant_id) is not UUID or type(event_id) is not str
                or fullmatch(r"DEMO-EVENT-[A-Z0-9-]{3,40}", event_id) is None):
            _reject()
        with self._lock:
            event = self._events.get((tenant_id, event_id))
            if event is None:
                raise DemoEvidenceNotFound("Demo evidence unavailable")
            return event[1]
