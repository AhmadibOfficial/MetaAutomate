"""P3-07: eight-source contract drift and consolidated CLI security acceptance.

The canonical integration engine is app.phase03_integrated_conformance.
These tests deliberately avoid adding a second end-to-end engine.
"""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.phase03_contract_audit import (
    CONTRACTS, OfflineContractDenied, audit_local_contracts,
)
from app.phase03_intelligent_ecosystem import OPERATION_SPECS

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"


def _copy_contracts(tmp_path):
    for relative in CONTRACTS.values():
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


def _mutate(root, name, field, value):
    path = root / CONTRACTS[name]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(json.dumps(payload))


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, timeout=20, check=False,
    )


def test_exact_eight_source_contracts_checked_not_external_authority():
    result = audit_local_contracts(ROOT)
    assert result.contract_count == 8
    assert result.operation_count == len(OPERATION_SPECS) == 4
    assert result.source_compatible
    assert result.decision == "DENY"
    assert result.scope == "EIGHT_LOCAL_SOURCE_CONTRACTS_ONLY"
    assert not result.external_services_inspected
    assert not result.independent_human_review_verified
    assert not result.operational_recovery_verified
    assert not result.real_customer_outcome_verified
    assert not result.live_execution_authorized
    assert not result.merge_authorized


@pytest.mark.parametrize("name,field,value", [
    ("planning", "trusted_execution_authorization_available", True),
    ("planning", "trusted_execution_authorization_available", 0),
    ("planning", "external_reads_performed", True),
    ("planning", "external_writes_performed", True),
    ("outcome", "external_receipt_trust_available", True),
    ("outcome", "live_provider_readback_enabled", True),
    ("outcome", "external_execution_authorized", True),
    ("outcome", "phase02_operational_go", 0),
    ("analytics", "live_execution_authorized", True),
    ("analytics", "real_revenue_measured", True),
    ("analytics", "customer_data_used", True),
    ("analytics", "ai_model_called", True),
    ("analytics", "real_income_guarantee", True),
    ("developer", "production_ready", True),
    ("developer", "external_provider_access_enabled", True),
    ("developer", "external_write_enabled", True),
    ("developer", "customer_data_access_enabled", True),
    ("developer", "model_tool_invocation_enabled", True),
    ("execution", "real_execution_authorized", True),
    ("execution", "any_effect_performed", True),
    ("execution", "durable_replay_protection_available", True),
    ("execution", "trusted_identity_available", True),
    ("execution", "human_review_authenticated", True),
    ("execution", "independent_provider_receipt_available", True),
    ("execution", "phase02_operational_approved", 0),
    ("integration", "real_provider_execution_allowed", True),
    ("integration", "customer_data_used", True),
    ("integration", "durable_audit_available", True),
    ("integration", "independent_human_review_verified", True),
    ("integration", "phase02_operational_go", True),
    ("integration", "release_authorized", True),
    ("integration", "live_execution_authorized", True),
    ("integration", "external_provider_access_enabled", True),
    ("integration", "independent_review_verified", True),
    ("integration", "phase02_operational_approved", True),
    ("integration", "source_contract_count", 7),
    ("integration", "declared_contracts", []),
    ("integration", "source_audit_scope", "PRODUCTION"),
    ("integration", "default_policy", "ALLOW"),
    ("integration", "phase01_verified", 9),
    ("execution", "default_decision", "ALLOW"),
    ("developer", "default_decision", "ALLOW"),
    ("analytics", "decision", "ALLOW"),
    ("outcome", "release_decision", "GO"),
])
def test_source_privilege_drift_denied(tmp_path, name, field, value):
    root = _copy_contracts(tmp_path)
    _mutate(root, name, field, value)
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


@pytest.mark.parametrize("name", tuple(CONTRACTS))
def test_missing_source_manifest_denied(tmp_path, name):
    root = _copy_contracts(tmp_path)
    (root / CONTRACTS[name]).unlink()
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


@pytest.mark.parametrize("name", tuple(CONTRACTS))
def test_invalid_json_denied(tmp_path, name):
    root = _copy_contracts(tmp_path)
    (root / CONTRACTS[name]).write_text("{NOT_JSON", encoding="utf-8")
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


def test_duplicate_capability_cannot_hide_inside_manifest(tmp_path):
    root = _copy_contracts(tmp_path)
    path = root / CONTRACTS["capabilities"]
    obj = json.loads(path.read_text())
    obj["operations"].append(obj["operations"][0].copy())
    path.write_text(json.dumps(obj))
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


def test_extra_developer_tool_cannot_become_authorized(tmp_path):
    root = _copy_contracts(tmp_path)
    path = root / CONTRACTS["developer"]
    obj = json.loads(path.read_text())
    obj["actions"][0]["effect"] = "ALLOW"
    path.write_text(json.dumps(obj))
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


def test_cli_checks_only_four_synthetic_denials():
    p = _cli("ecosystem-check")
    assert p.returncode == 0, p.stderr
    obj = json.loads(p.stdout)
    assert obj["source_contract_audit"]["contract_count"] == 8
    assert obj["source_contract_audit"]["source_compatible"] is True
    assert obj["synthetic_operations_checked"] == 4
    assert obj["synthetic_denials"] == 4
    assert obj["external_operations_performed"] == 0
    assert obj["decision"] == "DENY"
    assert obj["release_authorized"] is False


def test_canonical_integrated_demo_remains_one_command():
    p = _cli("integrated-demo", "business.finance.reconciliation-proposal.v1",
             "--reviewer-count", "2", "--observed-version", "2",
             "--observed-tick", "112")
    assert p.returncode == 0, p.stderr
    obj = json.loads(p.stdout)
    assert obj["local_source_integrity_checked"] is True
    assert obj["demo_plan_expired"] is True
    assert obj["demo_resource_unchanged"] is False
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in obj["denial_reasons"]
    assert obj["decision"] == "DENY"
    assert obj["provider_called"] is False
    assert obj["side_effects_performed"] is False
    assert obj["release_authorized"] is False


@pytest.mark.parametrize("args", [
    ("integrated-demo", "business.inventory.stock-preview.v1", "--execute"),
    ("ecosystem-check", "--production"),
    ("integrated-demo", "finance.transfer.real.v1"),
    ("integration-demo", "business.inventory.stock-preview.v1"),
])
def test_cli_has_no_second_executor_or_production_actions(args):
    p = _cli(*args)
    assert p.returncode != 0
    assert p.stdout == ""


def test_no_duplicate_integration_module_or_route_in_consolidated_tree():
    assert not (ROOT / "apps/api/app/phase03_integration_safety.py").exists()
    assert not (ROOT / "contracts/intelligent/v1/integration_safety.json").exists()
    src = (ROOT / "apps/api/app/phase03_contract_audit.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_integrated_conformance" not in main
    assert "phase03_contract_audit" not in main
    for forbidden in (
        "APIRouter(", "httpx", "requests.", "socket.socket(", "subprocess.",
        "psycopg", "redis.", "urlopen(", "urllib.request", "openai.",
    ):
        assert forbidden not in src
