"""Phase 03 P3-01: DENY-only local capability gateway and verification primitives.

This module does not authenticate a user, create a tenant, verify human
approval, call any provider, queue work, perform AI inference or execute a
capability. Tenant UUIDs and reviewers are invented test inputs, not claims.
Local SHA-256 receipts prove *consistency only*, never external authenticity.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID

MAX_TICK = 1_000_000
MAX_REQUESTS = 64
MAX_TENANTS = 16
MAX_PER_TENANT = 16
MAX_ANALYTICS_EVENTS = 64
ACTOR_RE = re.compile(r"DEMO-ACTOR-[A-Z0-9-]{3,40}\Z")
REQUEST_RE = re.compile(r"DEMO-REQ-[A-Z0-9-]{3,48}\Z")

# This is the frozen source contract from Phase 02. It is not a scope grant.
# Each entry: capability, effect, required scope, risk, human approval, scenario.
OPERATION_SPECS = {
    "business.lead-intake.validate.v1": (
        "BIZ-002", "validate_only", "business.leads.preview",
        "low", False, "DEMO-LEAD-VALIDATION",
    ),
    "business.crm.sync-proposal.v1": (
        "BIZ-006", "propose_write", "business.crm.write",
        "moderate", True, "DEMO-CRM-PROPOSAL",
    ),
    "business.inventory.stock-preview.v1": (
        "BIZ-011", "read_external", "business.inventory.read",
        "moderate", False, "DEMO-STOCK-CHECK",
    ),
    "business.finance.reconciliation-proposal.v1": (
        "BIZ-012", "propose_write", "business.finance.write",
        "high", True, "DEMO-RECONCILIATION",
    ),
}
BASE_DENIAL_REASONS = (
    "foundation_release_no_go",
    "phase02_operational_no_go",
    "real_identity_not_verified",
    "tenant_authorization_not_verified",
    "provider_binding_not_verified",
    "capability_disabled",
)
APPROVAL_DENIAL_REASON = "per_effect_human_approval_not_verified"


class CapabilityDenied(ValueError):
    """Only local invented capability intents can be inspected."""


class ReceiptRejected(ValueError):
    """An invalid or cross-tenant synthetic receipt cannot enter analytics."""


class ContractRejected(ValueError):
    """Phase 03 source manifest cannot enable live capability execution."""


def _deny() -> None:
    raise CapabilityDenied("Offline capability preview rejected")


def _json_digest(values: dict[str, object]) -> str:
    data = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(data.encode("ascii")).hexdigest()


def _demo_tenant_marker(value: UUID) -> str:
    if type(value) is not UUID:
        _deny()
    return "DEMO-TENANT-" + sha256(
        b"metaautomate:phase03:offline-only:" + value.bytes
    ).hexdigest()[:16].upper()


@dataclass(frozen=True)
class DemoCapabilityIntent:
    tenant_id: UUID
    actor_label: str
    request_id: str
    operation_id: str
    scenario: str
    logical_tick: int


@dataclass(frozen=True)
class CapabilityDenialReceipt:
    tenant_id: UUID
    tenant_demo_marker: str
    actor_label: str
    request_id: str
    operation_id: str
    capability_id: str
    effect: str
    required_scope: str
    risk: str
    approval_required: bool
    scenario: str
    logical_tick: int
    reasons: tuple[str, ...]
    checksum: str
    decision: str = "DENY"
    simulation_only: bool = True
    actor_authenticated: bool = False
    tenant_authenticated: bool = False
    scope_verified: bool = False
    human_approval_verified: bool = False
    provider_identity_verified: bool = False
    execution_authorized: bool = False
    execution_performed: bool = False
    provider_called: bool = False
    customer_data_accessed: bool = False
    durable_evidence: bool = False


def _intent_check(intent: DemoCapabilityIntent) -> tuple[str, str, str, str, bool, str]:
    if type(intent) is not DemoCapabilityIntent:
        _deny()
    _demo_tenant_marker(intent.tenant_id)
    if (
        type(intent.actor_label) is not str
        or ACTOR_RE.fullmatch(intent.actor_label) is None
        or type(intent.request_id) is not str
        or REQUEST_RE.fullmatch(intent.request_id) is None
        or type(intent.operation_id) is not str
        or intent.operation_id not in OPERATION_SPECS
        or type(intent.scenario) is not str
        or type(intent.logical_tick) is not int
        or not 0 <= intent.logical_tick <= MAX_TICK
    ):
        _deny()
    spec = OPERATION_SPECS[intent.operation_id]
    if intent.scenario != spec[5]:
        _deny()
    return spec


def _receipt_material(receipt: CapabilityDenialReceipt) -> dict[str, object]:
    return {
        "domain": "metaautomate.phase03.synthetic-denial.v1",
        "tenant_marker": receipt.tenant_demo_marker,
        "actor": receipt.actor_label,
        "request_id": receipt.request_id,
        "operation_id": receipt.operation_id,
        "capability_id": receipt.capability_id,
        "effect": receipt.effect,
        "required_scope": receipt.required_scope,
        "risk": receipt.risk,
        "approval_required": receipt.approval_required,
        "scenario": receipt.scenario,
        "logical_tick": receipt.logical_tick,
        "reasons": list(receipt.reasons),
        "decision": receipt.decision,
        "simulation_only": receipt.simulation_only,
        "actor_authenticated": receipt.actor_authenticated,
        "tenant_authenticated": receipt.tenant_authenticated,
        "scope_verified": receipt.scope_verified,
        "human_approval_verified": receipt.human_approval_verified,
        "provider_identity_verified": receipt.provider_identity_verified,
        "execution_authorized": receipt.execution_authorized,
        "execution_performed": receipt.execution_performed,
        "provider_called": receipt.provider_called,
        "customer_data_accessed": receipt.customer_data_accessed,
        "durable_evidence": receipt.durable_evidence,
    }


def _receipt_for(intent: DemoCapabilityIntent) -> CapabilityDenialReceipt:
    spec = _intent_check(intent)
    receipt = CapabilityDenialReceipt(
        tenant_id=intent.tenant_id,
        tenant_demo_marker=_demo_tenant_marker(intent.tenant_id),
        actor_label=intent.actor_label, request_id=intent.request_id,
        operation_id=intent.operation_id, capability_id=spec[0],
        effect=spec[1], required_scope=spec[2], risk=spec[3],
        approval_required=spec[4], scenario=intent.scenario,
        logical_tick=intent.logical_tick,
        reasons=BASE_DENIAL_REASONS + (
            (APPROVAL_DENIAL_REASON,) if spec[4] else ()
        ),
        checksum="",
    )
    from dataclasses import replace
    return replace(receipt, checksum=_json_digest(_receipt_material(receipt)))


class OfflineCapabilityPreview:
    """Lock-serialized DEMO receipt idempotency, not durable service replay control."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[
            tuple[UUID, str], tuple[DemoCapabilityIntent, CapabilityDenialReceipt]
        ] = {}
        self._tenant_counts: dict[UUID, int] = {}

    def inspect_once(self, intent: DemoCapabilityIntent) -> CapabilityDenialReceipt:
        result = _receipt_for(intent)
        with self._lock:
            key = (intent.tenant_id, intent.request_id)
            prior = self._by_id.get(key)
            if prior is not None:
                if prior[0] != intent:
                    _deny()
                return prior[1]
            if (
                len(self._by_id) >= MAX_REQUESTS
                or self._tenant_counts.get(intent.tenant_id, 0) >= MAX_PER_TENANT
                or (
                    intent.tenant_id not in self._tenant_counts
                    and len(self._tenant_counts) >= MAX_TENANTS
                )
            ):
                _deny()
            self._by_id[key] = (intent, result)
            self._tenant_counts[intent.tenant_id] = (
                self._tenant_counts.get(intent.tenant_id, 0) + 1
            )
            return result


@dataclass(frozen=True)
class OfflineVerification:
    synthetic_checksum_consistent: bool
    request_matches: bool
    decision: str = "DENY"
    verified_execution: bool = False
    real_human_approval_verified: bool = False
    authoritative_provider_receipt_verified: bool = False
    independent_provider_readback_performed: bool = False
    external_evidence_authenticated: bool = False


def verify_synthetic_denial(
    receipt: CapabilityDenialReceipt, expected: DemoCapabilityIntent,
) -> OfflineVerification:
    """Recalculate invented values; cannot authenticate the receipt's issuer."""
    _intent_check(expected)
    if type(receipt) is not CapabilityDenialReceipt:
        raise ReceiptRejected("Invalid synthetic receipt")
    spec = OPERATION_SPECS[expected.operation_id]
    expected_receipt = _receipt_for(expected)
    # Exact equality guards against fake "authorized" fields and reason changes.
    consistent = (
        type(receipt.checksum) is str
        and receipt.checksum == _json_digest(_receipt_material(receipt))
        and receipt == expected_receipt
    )
    same_request = (
        receipt.tenant_id == expected.tenant_id
        and receipt.tenant_demo_marker == expected_receipt.tenant_demo_marker
        and receipt.actor_label == expected.actor_label
        and receipt.request_id == expected.request_id
        and receipt.operation_id == expected.operation_id
        and receipt.capability_id == spec[0]
        and receipt.scenario == expected.scenario
    )
    return OfflineVerification(
        synthetic_checksum_consistent=consistent,
        request_matches=same_request,
    )


@dataclass(frozen=True)
class OfflineDenialAnalytics:
    tenant_demo_marker: str
    synthetic_events: int
    denied_events: int
    operation_counts: tuple[tuple[str, int], ...]
    reason_counts: tuple[tuple[str, int], ...]
    decision: str = "DENY"
    source: str = "UNTRUSTED_DEMO_DENIAL_EVENTS"
    business_value_measured: bool = False
    production_telemetry_verified: bool = False
    provider_reads_performed: bool = False
    customer_data_processed: bool = False
    real_revenue_measured: bool = False


def aggregate_synthetic_denials(
    tenant_id: UUID,
    events: tuple[tuple[DemoCapabilityIntent, CapabilityDenialReceipt], ...],
) -> OfflineDenialAnalytics:
    """No raw customer events; fail closed on duplicate/cross-tenant/fake receipts."""
    marker = _demo_tenant_marker(tenant_id)
    if type(events) is not tuple or len(events) > MAX_ANALYTICS_EVENTS:
        raise ReceiptRejected("Invalid synthetic event collection")
    ids: set[str] = set()
    operation_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for pair in events:
        if type(pair) is not tuple or len(pair) != 2:
            raise ReceiptRejected("Invalid synthetic event")
        intent, receipt = pair
        if type(intent) is not DemoCapabilityIntent or intent.tenant_id != tenant_id:
            raise ReceiptRejected("Untrusted tenant partition")
        verdict = verify_synthetic_denial(receipt, intent)
        if not verdict.synthetic_checksum_consistent or not verdict.request_matches:
            raise ReceiptRejected("Inconsistent synthetic denial event")
        if intent.request_id in ids:
            raise ReceiptRejected("Duplicate synthetic event cannot inflate metrics")
        ids.add(intent.request_id)
        operation_counts[intent.operation_id] = (
            operation_counts.get(intent.operation_id, 0) + 1
        )
        for reason in receipt.reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return OfflineDenialAnalytics(
        tenant_demo_marker=marker,
        synthetic_events=len(events),
        denied_events=len(events),
        operation_counts=tuple(sorted(operation_counts.items())),
        reason_counts=tuple(sorted(reason_counts.items())),
    )


def validate_phase03_manifest(
    phase03: object, phase02: object,
) -> tuple[dict[str, object], ...]:
    """Exact source contract parity; rejects enabled flags and registry drift."""
    if type(phase03) is not dict or type(phase02) is not dict:
        raise ContractRejected("Invalid manifest format")
    required = {
        "schema_version": 1, "product": "metaautomate", "phase": "03",
        "contract_version": "0.1.0", "mode": "OFFLINE_DESIGN_ONLY",
        "default_policy": "DENY", "release_status": "NO_GO",
        "foundation_gates_verified": 3, "foundation_gates_required": 9,
        "phase02_operational_accepted": False,
        "live_execution_authorized": False, "external_data_access": False,
        "developer_interface": "LOCAL_CLI_ONLY",
        "verification_scope": "SYNTHETIC_CHECKSUM_CONSISTENCY_ONLY",
        "analytics_scope": "DEMO_DENIAL_EVENTS_ONLY",
    }
    if any(phase03.get(k) != v or type(phase03.get(k)) is not type(v)
           for k, v in required.items()):
        raise ContractRejected("Phase 03 must remain offline and denied")
    if phase02.get("default_policy") != "DENY" or phase02.get("lifecycle") != "draft":
        raise ContractRejected("Source Phase 02 contract unexpectedly changed")
    if phase02.get("adapter_state") != "unbound" or phase02.get("external_access") is not False:
        raise ContractRejected("External Phase 02 execution is not permitted")
    rows = phase03.get("operations")
    base = phase02.get("operations")
    if type(rows) is not list or type(base) is not list or len(rows) != len(OPERATION_SPECS):
        raise ContractRejected("Invalid operation registry length")
    got_ids: set[str] = set()
    expected_ids = set(OPERATION_SPECS)
    base_by_id = {}
    for item in base:
        if type(item) is not dict or type(item.get("operation_id")) is not str:
            raise ContractRejected("Invalid domain contract")
        if item["operation_id"] in base_by_id:
            raise ContractRejected("Duplicate domain operation")
        base_by_id[item["operation_id"]] = item
    if set(base_by_id) != expected_ids:
        raise ContractRejected("Unexpected Phase 02 domain operation")
    for item in rows:
        if type(item) is not dict or set(item) != {
            "operation_id", "capability_id", "effect", "required_scope",
            "risk", "approval_required", "lifecycle", "execution_enabled",
            "provider_bound", "autonomous_execution_enabled",
        }:
            raise ContractRejected("Unexpected capability metadata")
        name = item["operation_id"]
        if type(name) is not str or name in got_ids or name not in expected_ids:
            raise ContractRejected("Duplicate or unknown intelligent capability")
        got_ids.add(name)
        spec = OPERATION_SPECS[name]
        for field, value in zip(
            ("capability_id", "effect", "required_scope", "risk", "approval_required"),
            spec[:5],
        ):
            if item[field] != value or type(item[field]) is not type(value):
                raise ContractRejected("Capability parity mismatch")
        if any(item[field] != base_by_id[name][field]
               for field in (
                   "capability_id", "effect", "required_scope",
                   "risk", "approval_required",
               )):
            raise ContractRejected("Phase 02 and 03 source drift")
        for flag in ("execution_enabled", "provider_bound", "autonomous_execution_enabled"):
            if item[flag] is not False:
                raise ContractRejected("Any enabled executable capability is forbidden")
        if item["lifecycle"] != "draft":
            raise ContractRejected("Capability lifecycle must be draft")
    if got_ids != expected_ids:
        raise ContractRejected("Missing operation")
    return tuple(rows)
