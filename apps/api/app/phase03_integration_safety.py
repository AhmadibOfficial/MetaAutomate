"""P3-07: fully OFFLINE Phase 03 cross-module conformance and negative-flow tests.

This is a composite *denial* check, not a new capability executor.
No user trust can be established by a caller-provided UUID, demo checksum,
invented reviewer, AI statement, simulated receipt, or green CI result.
Never accepts an ALLOW outcome. No HTTP, DB, network or external effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from uuid import UUID

from app.phase03_intelligent_ecosystem import (
    DemoCapabilityIntent, OfflineCapabilityPreview, OPERATION_SPECS,
    validate_phase03_manifest,
)
from app.phase03_capability_planning import (
    DemoPlanningRequest, TARGETS, create_denied_plan, inspect_denied_plan,
)
from app.phase03_outcome_verification import (
    make_demo_no_dispatch, make_demo_readback, verify_demo_negative_outcome,
)
from app.phase03_execution_rehearsal import (
    DemoExecutionAttempt, DemoExecutionAudit, verify_demo_audit_sequence,
    MISSING_TRUST,
)
from app.phase03_business_analytics import (
    analyze_demo_business, demo_business_fixture,
)
from app.phase03_developer_tools import (
    validate_source_spec, source_spec,
)

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = {
    "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
    "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
    "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
    "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
}
MAX_TICK = 1_000_000
EXPECTED_CONTRACTS = {
    "domain": "contracts/domains/v1/operations.json",
    "capabilities": "contracts/intelligent/v1/capabilities.json",
    "planning": "contracts/intelligent/v1/planning.json",
    "outcome": "contracts/intelligent/v1/outcome_verification.json",
    "analytics": "contracts/intelligent/v1/business_analytics.json",
    "developer": "contracts/intelligent/v1/developer_tools.json",
    "execution": "contracts/intelligent/v1/execution_rehearsal.json",
    "integration": "contracts/intelligent/v1/integration_safety.json",
}


class OfflineIntegrationDenied(ValueError):
    """Unknown or privilege-claiming synthetic flow is refused."""


def _deny() -> None:
    raise OfflineIntegrationDenied("Phase 03 offline integration denied")


@dataclass(frozen=True)
class OfflineIntegratedInput:
    tenant_id: UUID
    operation_id: str = "business.inventory.stock-preview.v1"
    request_id: str = "DEMO-REQ-P307-001"
    attempt_id: str = "DEMO-ATTEMPT-P307-001"
    resource_version: int = 1
    observed_resource_version: int = 1
    observed_tick: int = 101
    reviewer_labels: tuple[str, ...] = ()
    attach_synthetic_analytics: bool = False


@dataclass(frozen=True)
class OfflineIntegrationResult:
    operation_id: str
    request_id: str
    capability_id: str
    tenant_marker: str
    denial_receipt_consistent: bool
    denied_plan_consistent: bool
    negative_evidence_consistent: bool
    invented_state_unchanged: bool
    demo_plan_expired: bool
    audited_denial_consistent: bool
    mandatory_trust_checks_missing: tuple[str, ...]
    synthetic_business_alerts: tuple[str, ...]
    decision: str = "DENY"
    scope: str = "LOCAL_SYNTHETIC_CROSS_MODULE_NEGATIVE_CONFORMANCE"
    actual_authorization_verified: bool = False
    real_provider_receipt_verified: bool = False
    provider_called: bool = False
    customer_data_accessed: bool = False
    real_financial_result_measured: bool = False
    real_customer_outcome_verified: bool = False
    business_effect_performed: bool = False
    release_authorized: bool = False


def _check(inp: OfflineIntegratedInput) -> None:
    if type(inp) is not OfflineIntegratedInput or type(inp.tenant_id) is not UUID:
        _deny()
    if (
        type(inp.operation_id) is not str
        or inp.operation_id not in OPERATION_SPECS
        or type(inp.request_id) is not str
        or re.fullmatch(r"DEMO-REQ-[A-Z0-9-]{3,48}", inp.request_id) is None
        or type(inp.attempt_id) is not str
        or re.fullmatch(r"DEMO-ATTEMPT-[A-Z0-9-]{3,40}", inp.attempt_id) is None
        or type(inp.resource_version) is not int
        or not 1 <= inp.resource_version <= 1000
        or type(inp.observed_resource_version) is not int
        or not 0 <= inp.observed_resource_version <= 1000
        or type(inp.observed_tick) is not int
        or not 100 <= inp.observed_tick <= MAX_TICK
        or type(inp.reviewer_labels) is not tuple
        or len(inp.reviewer_labels) > 2
        or len(inp.reviewer_labels) != len(set(
            x for x in inp.reviewer_labels if type(x) is str
        ))
        or any(
            type(x) is not str
            or re.fullmatch(r"DEMO-REVIEWER-[A-Z0-9-]{3,32}", x) is None
            for x in inp.reviewer_labels
        )
        or type(inp.attach_synthetic_analytics) is not bool
    ):
        _deny()


def run_offline_integration(inp: OfflineIntegratedInput) -> OfflineIntegrationResult:
    """Rehearse an entire phase's DENY path with NO external dispatch."""
    _check(inp)
    intent = DemoCapabilityIntent(
        tenant_id=inp.tenant_id,
        actor_label="DEMO-ACTOR-INTEGRATION",
        request_id=inp.request_id,
        operation_id=inp.operation_id,
        scenario=SCENARIOS[inp.operation_id],
        logical_tick=100,
    )
    receipt = OfflineCapabilityPreview().inspect_once(intent)
    req = DemoPlanningRequest(
        intent=intent, denial_receipt=receipt,
        target_label=TARGETS[inp.operation_id],
        expected_resource_version=inp.resource_version, requested_tick=100,
    )
    plan = create_denied_plan(req)
    plan_check = inspect_denied_plan(plan, req, observed_tick=inp.observed_tick)
    event = make_demo_no_dispatch(
        plan, req, event_id="DEMO-EVENT-P307-NO-DISPATCH",
        observed_tick=inp.observed_tick,
    )
    local_read = make_demo_readback(
        plan, req, observed_tick=inp.observed_tick,
        observed_version=inp.observed_resource_version,
    )
    neg = verify_demo_negative_outcome(
        plan, req, event, local_read, observed_tick=inp.observed_tick,
    )
    execution_attempt = DemoExecutionAttempt(
        plan=plan, source_request=req,
        attempt_id=inp.attempt_id,
        observed_tick=inp.observed_tick,
        expected_resource_version=inp.observed_resource_version,
        reviewer_labels=inp.reviewer_labels,
    )
    rejection, chain = DemoExecutionAudit().reject_once(execution_attempt)
    chain_check = verify_demo_audit_sequence(
        inp.tenant_id, ((rejection, chain),),
    )
    if (
        receipt.decision != "DENY"
        or plan.decision != "DENY"
        or rejection.decision != "DENY"
        or neg.decision != "DENY"
        or plan.execution_authorized is not False
        or rejection.side_effects_performed is not False
        or receipt.provider_called is not False
        or not plan_check.synthetic_integrity_consistent
        or not neg.demo_evidence_consistent
        or not chain_check.demo_internal_links_consistent
        or rejection.missing_trust_codes[:len(MISSING_TRUST)] != MISSING_TRUST
        or neg.demo_state_unchanged != rejection.demo_resource_version_unchanged
        or plan_check.expired != rejection.demo_plan_expired
    ):
        _deny()
    alerts: tuple[str, ...] = ()
    if inp.attach_synthetic_analytics:
        business = analyze_demo_business(
            inp.tenant_id, demo_business_fixture(inp.tenant_id),
        )
        if business.decision != "DENY" or business.business_value_measured:
            _deny()
        alerts = business.insight_codes
    return OfflineIntegrationResult(
        operation_id=inp.operation_id,
        request_id=inp.request_id,
        capability_id=plan.capability_id,
        tenant_marker=plan.tenant_demo_marker,
        denial_receipt_consistent=True,
        denied_plan_consistent=plan_check.synthetic_integrity_consistent,
        negative_evidence_consistent=neg.demo_evidence_consistent,
        invented_state_unchanged=neg.demo_state_unchanged,
        demo_plan_expired=plan_check.expired,
        audited_denial_consistent=chain_check.demo_internal_links_consistent,
        mandatory_trust_checks_missing=rejection.missing_trust_codes,
        synthetic_business_alerts=alerts,
    )


@dataclass(frozen=True)
class OfflineContractAudit:
    contracts_checked: int
    operation_count: int
    controls_denied: bool
    decision: str = "DENY"
    source_verified_only: bool = True
    external_services_verified: bool = False
    live_execution_authorized: bool = False
    independent_review_performed: bool = False


def audit_offline_contracts(root: Path = ROOT) -> OfflineContractAudit:
    """Check 8 source manifests; NOT an operational signoff or real identity."""
    if not isinstance(root, Path):
        _deny()
    try:
        documents = {
            name: json.loads((root / path).read_text(encoding="utf-8"))
            for name, path in EXPECTED_CONTRACTS.items()
        }
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise OfflineIntegrationDenied("Missing or invalid offline contract") from exc
    if any(type(value) is not dict for value in documents.values()):
        _deny()
    try:
        validate_phase03_manifest(
            documents["capabilities"], documents["domain"],
        )
        validate_source_spec(documents["developer"])
    except ValueError as exc:
        raise OfflineIntegrationDenied("Source contract mismatch") from exc
    predicates = (
        (documents["planning"], "trusted_execution_authorization_available", False),
        (documents["planning"], "external_writes_performed", False),
        (documents["outcome"], "external_execution_authorized", False),
        (documents["outcome"], "live_provider_readback_enabled", False),
        (documents["analytics"], "live_execution_authorized", False),
        (documents["analytics"], "real_revenue_measured", False),
        (documents["execution"], "real_execution_authorized", False),
        (documents["execution"], "any_effect_performed", False),
        (documents["execution"], "durable_replay_protection_available", False),
        (documents["integration"], "live_execution_authorized", False),
        (documents["integration"], "external_provider_access_enabled", False),
        (documents["integration"], "independent_review_verified", False),
        (documents["integration"], "phase02_operational_approved", False),
    )
    if any(
        type(source.get(key)) is not type(expected)
        or source.get(key) != expected
        for source, key, expected in predicates
    ):
        _deny()
    expected = (
        ("integration", "P3-07"),
        ("execution", "P3-06"),
        ("developer", "P3-05"),
        ("analytics", "P3-04"),
        ("outcome", "P3-03"),
        ("planning", "P3-02"),
    )
    if any(documents[name].get("milestone") != milestone
           for name, milestone in expected):
        _deny()
    if (
        documents["execution"].get("default_decision") != "DENY"
        or documents["integration"].get("default_decision") != "DENY"
        or documents["planning"].get("default_decision") != "DENY"
        or documents["analytics"].get("decision") != "DENY"
        or documents["outcome"].get("release_decision") != "NO_GO"
        or documents["integration"].get("source_contract_count") != 8
        or documents["integration"].get("phase01_foundation_verified") != 3
        or documents["integration"].get("phase01_foundation_required") != 9
        or documents["integration"].get("scope")
        != "OFFLINE_DENY_ONLY_CROSS_MODULE_CONFORMANCE"
        or documents["integration"].get("declared_contracts") != [
            EXPECTED_CONTRACTS[k] for k in EXPECTED_CONTRACTS
        ]
    ):
        _deny()
    return OfflineContractAudit(
        contracts_checked=len(documents),
        operation_count=len(OPERATION_SPECS),
        controls_denied=True,
    )
