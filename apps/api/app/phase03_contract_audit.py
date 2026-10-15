"""P3-07 consolidated source contract audit — no execution and no network.

This module only validates local versioned JSON manifests for known NO-GO
settings. The single canonical execution-denial conformance implementation is
phase03_integrated_conformance.py; this auditor never runs another flow.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from app.phase03_intelligent_ecosystem import (
    OPERATION_SPECS, validate_phase03_manifest,
)
from app.phase03_developer_tools import validate_source_spec

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = {
    "domain": "contracts/domains/v1/operations.json",
    "capabilities": "contracts/intelligent/v1/capabilities.json",
    "planning": "contracts/intelligent/v1/planning.json",
    "outcome": "contracts/intelligent/v1/outcome_verification.json",
    "analytics": "contracts/intelligent/v1/business_analytics.json",
    "developer": "contracts/intelligent/v1/developer_tools.json",
    "execution": "contracts/intelligent/v1/execution_rehearsal.json",
    "integration": "contracts/intelligent/v1/integration_conformance.json",
}
MILESTONES = {
    "planning": "P3-02",
    "outcome": "P3-03",
    "analytics": "P3-04",
    "developer": "P3-05",
    "execution": "P3-06",
    "integration": "P3-07",
}
DENIAL_FIELDS = {
    "planning": {
        "trusted_execution_authorization_available": False,
        "external_reads_performed": False,
        "external_writes_performed": False,
        "phase02_operational_accepted": False,
    },
    "outcome": {
        "external_receipt_trust_available": False,
        "live_provider_readback_enabled": False,
        "external_execution_authorized": False,
        "phase02_operational_go": False,
    },
    "analytics": {
        "live_execution_authorized": False,
        "real_revenue_measured": False,
        "customer_data_used": False,
        "ai_model_called": False,
        "real_income_guarantee": False,
        "phase02_operational_go": False,
    },
    "developer": {
        "production_ready": False,
        "external_provider_access_enabled": False,
        "external_write_enabled": False,
        "customer_data_access_enabled": False,
        "model_tool_invocation_enabled": False,
        "phase02_operational_go": False,
    },
    "execution": {
        "real_execution_authorized": False,
        "any_effect_performed": False,
        "durable_replay_protection_available": False,
        "trusted_identity_available": False,
        "human_review_authenticated": False,
        "independent_provider_receipt_available": False,
        "phase02_operational_approved": False,
    },
    "integration": {
        "real_provider_execution_allowed": False,
        "customer_data_used": False,
        "durable_audit_available": False,
        "independent_human_review_verified": False,
        "phase02_operational_go": False,
        "release_authorized": False,
        "live_execution_authorized": False,
        "external_provider_access_enabled": False,
        "independent_review_verified": False,
        "phase02_operational_approved": False,
    },
}


class OfflineContractDenied(ValueError):
    """Synthetic source manifest no longer matches the reviewed NO-GO schema."""


def _deny() -> None:
    raise OfflineContractDenied("Source contract audit DENIED; never release")


@dataclass(frozen=True)
class LocalContractAudit:
    contract_count: int
    operation_count: int
    source_compatible: bool
    decision: str = "DENY"
    scope: str = "EIGHT_LOCAL_SOURCE_CONTRACTS_ONLY"
    external_services_inspected: bool = False
    independent_human_review_verified: bool = False
    operational_recovery_verified: bool = False
    real_customer_outcome_verified: bool = False
    live_execution_authorized: bool = False
    merge_authorized: bool = False


def audit_local_contracts(root: Path = ROOT) -> LocalContractAudit:
    """Check only local disk contracts, never a running/deployed service."""
    if not isinstance(root, Path):
        _deny()
    try:
        manifests = {
            key: json.loads((root / name).read_text(encoding="utf-8"))
            for key, name in CONTRACTS.items()
        }
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise OfflineContractDenied("Missing, malformed or unreadable source contract") from exc
    if any(type(value) is not dict for value in manifests.values()):
        _deny()
    try:
        validate_phase03_manifest(manifests["capabilities"], manifests["domain"])
        validate_source_spec(manifests["developer"])
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise OfflineContractDenied("Upstream source contracts diverged") from exc
    if any(
        manifests[key].get("milestone") != expected
        for key, expected in MILESTONES.items()
    ):
        _deny()
    for key, conditions in DENIAL_FIELDS.items():
        actual = manifests[key]
        if any(
            type(actual.get(field)) is not bool
            or actual.get(field) is not expected
            for field, expected in conditions.items()
        ):
            _deny()
    if any((
        manifests["planning"].get("default_decision") != "DENY",
        manifests["outcome"].get("release_decision") != "NO_GO",
        manifests["analytics"].get("decision") != "DENY",
        manifests["developer"].get("default_decision") != "DENY",
        manifests["execution"].get("default_decision") != "DENY",
        manifests["integration"].get("default_policy") != "DENY",
        manifests["integration"].get("source_contract_count") != len(CONTRACTS),
        manifests["integration"].get("declared_contracts")
        != list(CONTRACTS.values()),
        manifests["integration"].get("source_audit_scope")
        != "LOCAL_ONLY_NO_EXTERNAL_AUTHORITY",
        manifests["integration"].get("phase01_verified") != 3,
        manifests["integration"].get("phase01_required") != 9,
        type(manifests["integration"].get("phase01_verified")) is not int,
        type(manifests["integration"].get("phase01_required")) is not int,
        manifests["execution"].get("phase01_verified") != 3,
        manifests["execution"].get("phase01_required") != 9,
        set(manifests["developer"].get("operations", []))
        != set(OPERATION_SPECS),
    )):
        _deny()
    return LocalContractAudit(
        contract_count=len(CONTRACTS),
        operation_count=len(OPERATION_SPECS),
        source_compatible=True,
    )
