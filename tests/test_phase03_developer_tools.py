"""P3-05: typed offline developer SDK and source-spec compatibility security tests."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.phase03_developer_tools import (
    ACTION_FIELDS, SDK_REQUEST_ID, OfflineDeveloperDenied,
    OfflineToolInvocation, offline_developer_doctor,
    run_offline_tool, source_spec, validate_source_spec,
)
from app.phase03_intelligent_ecosystem import OPERATION_SPECS

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"
SPEC = ROOT / "contracts/intelligent/v1/developer_tools.json"


def request(action: str, **overrides) -> OfflineToolInvocation:
    operation = (
        "business.inventory.stock-preview.v1"
        if action in {"capability-preview", "denied-plan", "negative-proof"}
        else ""
    )
    return replace(OfflineToolInvocation(
        action=action, operation_id=operation,
    ), **overrides)


def test_manifest_matches_python_schema_with_boolean_types():
    published = json.loads(SPEC.read_text())
    assert published == source_spec()
    validate_source_spec(published)
    assert published["base_url"] is None
    assert published["transport"] == "NONE"
    assert published["default_decision"] == "DENY"
    assert published["production_ready"] is False
    assert published["external_provider_access_enabled"] is False
    assert published["model_tool_invocation_enabled"] is False
    assert len(published["actions"]) == 5
    assert published["operations"] == sorted(OPERATION_SPECS)


@pytest.mark.parametrize("key,bad", [
    ("production_ready", True),
    ("production_ready", 0),
    ("production_ready", "false"),
    ("transport", "HTTP"),
    ("base_url", "https://example.com/"),
    ("external_write_enabled", True),
    ("customer_data_access_enabled", 0),
    ("phase02_operational_go", 0),
    ("default_decision", "ALLOW"),
    ("model_tool_invocation_enabled", True),
    ("schema_version", True),
])
def test_spec_cannot_mint_unsafe_metadata_or_type_confusion(key, bad):
    altered = source_spec()
    altered[key] = bad
    with pytest.raises(OfflineDeveloperDenied):
        validate_source_spec(altered)


def test_spec_rejects_unknown_tool_or_argument_smuggling():
    for edit in ("add_tool", "remove_tool", "change_fields", "extra_grant",
                 "duplicate_operation", "change_operation"):
        modified = deepcopy(source_spec())
        if edit == "add_tool":
            modified["actions"].append({"action": "execute", "operation_required": True,
                                        "argument_names": ["payment"], "effect": "ALLOW"})
        elif edit == "remove_tool":
            modified["actions"].pop()
        elif edit == "change_fields":
            modified["actions"][0]["argument_names"].append("api_key")
        elif edit == "extra_grant":
            modified["actions"][0]["execution_authorized"] = True
        elif edit == "duplicate_operation":
            modified["operations"].append(modified["operations"][0])
        elif edit == "change_operation":
            modified["operations"][0] = "business.provider.payments.v1"
        with pytest.raises(OfflineDeveloperDenied):
            validate_source_spec(modified)


@pytest.mark.parametrize("action", [a[0] for a in ACTION_FIELDS])
def test_all_offline_typed_tools_remain_denied(action):
    result = run_offline_tool(request(action))
    assert result.action == action
    assert result.decision == "DENY"
    assert result.environment == "OFFLINE_DEMO_ONLY"
    assert result.payload["decision"] == "DENY"
    assert result.payload.get("execution_authorized") is False or (
        result.payload.get("execution_authorized") is None
        and result.executed is False
    )
    assert not result.executed
    assert not result.external_provider_called
    assert not result.user_authenticated
    assert not result.scope_verified
    assert not result.real_value_measured
    assert not result.release_authorized


def test_typed_sdk_finance_is_not_a_finance_executor():
    finance = run_offline_tool(request(
        "denied-plan", operation_id="business.finance.reconciliation-proposal.v1",
    ))
    assert finance.payload["human_approval_required"] is True
    assert finance.payload["high_risk_dual_review_required"] is True
    assert finance.payload["workflow_enqueued"] is False
    assert finance.payload["execution_performed"] is False
    assert finance.payload["execution_authorized"] is False


def test_typed_sdk_negative_proof_is_not_external_verification():
    proof = run_offline_tool(request(
        "negative-proof", observed_version=2,
    ))
    assert proof.payload["demo_state_unchanged"] is False
    assert proof.payload["finding"] == "DEMO_NEGATIVE_CONTROL_UNVERIFIED"
    assert proof.payload["execution_verified"] is False
    assert proof.payload["independently_observed_real_outcome"] is False
    assert proof.payload["provider_readback_performed"] is False


def test_typed_sdk_business_analytics_are_scenarios_not_profit():
    metrics = run_offline_tool(request("business-metrics"))
    assert metrics.payload["hypothetical_net_minor"] == 90_000
    assert metrics.payload["business_value_measured"] is False
    scenario = run_offline_tool(request("business-scenario", extra_orders=0))
    assert scenario.payload["income_generation_promised"] is False
    assert scenario.payload["result_guaranteed"] is False


@pytest.mark.parametrize("broken", [
    {"action": "execute"}, {"action": "send-payment"},
    {"operation_id": "business.finance.real-execution.v1"},
    {"operation_id": "https://api.example.com/data"},
    {"request_id": "REAL-CUSTOMER-IDENTIFIER"},
    {"request_id": None}, {"request_id": True},
    {"request_id": "DEMO-REQ-A\n"},
    {"resource_version": True}, {"resource_version": -1},
    {"resource_version": 1001}, {"observed_version": False},
    {"observed_version": -1}, {"observed_version": 1001},
    {"extra_orders": True}, {"extra_orders": 101},
    {"extra_marketing_minor": -1}, {"extra_marketing_minor": 100_000_001},
])
def test_sdk_rejects_bad_operation_and_type_confusion(broken):
    with pytest.raises(OfflineDeveloperDenied):
        run_offline_tool(request("denied-plan", **broken))


def test_operation_must_be_exact_and_nonexecuting():
    for op in OPERATION_SPECS:
        view = run_offline_tool(request("capability-preview", operation_id=op))
        assert view.payload["operation_id"] == op
        assert view.payload["execution_authorized"] is False
        plan = run_offline_tool(request("denied-plan", operation_id=op))
        assert plan.payload["resource_label"].startswith("DEMO-TARGET-")
        assert plan.payload["provider_called"] is False


@pytest.mark.parametrize("action,extra", [
    ("capability-preview", {"resource_version": 2}),
    ("capability-preview", {"observed_version": 2}),
    ("denied-plan", {"observed_version": 2}),
    ("negative-proof", {"resource_version": 2}),
    ("negative-proof", {"extra_orders": 2}),
    ("business-metrics", {"operation_id": "business.inventory.stock-preview.v1"}),
    ("business-metrics", {"request_id": "DEMO-REQ-NOT-SDK"}),
    ("business-metrics", {"extra_orders": 1}),
    ("business-scenario", {"operation_id": "business.inventory.stock-preview.v1"}),
    ("business-scenario", {"resource_version": 2}),
    ("business-scenario", {"request_id": "DEMO-REQ-OTHER"}),
])
def test_unused_parameters_cannot_smuggle_hidden_effects(action, extra):
    with pytest.raises(OfflineDeveloperDenied):
        run_offline_tool(request(action, **extra))


def test_sdk_response_and_request_models_are_immutable():
    value = run_offline_tool(request("business-metrics"))
    with pytest.raises(FrozenInstanceError):
        value.executed = True
    with pytest.raises(FrozenInstanceError):
        request("business-metrics").action = "execute"


def test_doctor_validates_all_offline_milestone_contracts():
    report = offline_developer_doctor(ROOT)
    assert report["source_contracts_checked"] == 6
    assert report["action_count"] == 5
    assert report["operation_count"] == 4
    assert report["source_compatible"] is True
    assert report["status"] == "SOURCE_CONTRACTS_VALIDATED_NOT_RELEASE_APPROVED"
    assert report["real_environment_checked"] is False
    assert report["decision"] == "DENY"
    assert not report["execution_available"]
    assert not report["customer_access_available"]
    assert not report["release_authorized"]


def test_doctor_rejects_modified_source_contract(tmp_path):
    contracts = [
        "contracts/intelligent/v1/developer_tools.json",
        "contracts/intelligent/v1/capabilities.json",
        "contracts/domains/v1/operations.json",
        "contracts/intelligent/v1/planning.json",
        "contracts/intelligent/v1/outcome_verification.json",
        "contracts/intelligent/v1/business_analytics.json",
    ]
    for source in contracts:
        dst = tmp_path / source
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT / source).read_bytes())
    bad = tmp_path / "contracts/intelligent/v1/developer_tools.json"
    payload = json.loads(bad.read_text())
    payload["customer_data_access_enabled"] = True
    bad.write_text(json.dumps(payload))
    with pytest.raises(OfflineDeveloperDenied):
        offline_developer_doctor(tmp_path)
    bad.write_bytes((ROOT / contracts[0]).read_bytes())
    p = tmp_path / "contracts/intelligent/v1/planning.json"
    payload = json.loads(p.read_text())
    payload["trusted_execution_authorization_available"] = True
    p.write_text(json.dumps(payload))
    with pytest.raises(OfflineDeveloperDenied):
        offline_developer_doctor(tmp_path)


@pytest.mark.parametrize("arguments", [
    ["dev-spec"], ["dev-doctor"],
    ["sdk-demo", "capability-preview",
     "--operation-id", "business.inventory.stock-preview.v1"],
    ["sdk-demo", "denied-plan",
     "--operation-id", "business.finance.reconciliation-proposal.v1"],
    ["sdk-demo", "negative-proof",
     "--operation-id", "business.inventory.stock-preview.v1",
     "--observed-version", "2"],
    ["sdk-demo", "business-metrics"],
    ["sdk-demo", "business-scenario", "--extra-orders", "0"],
])
def test_cli_developer_commands_are_valid_local_only_json(arguments):
    p = subprocess.run([sys.executable, str(CLI), *arguments],
                       capture_output=True, text=True, check=False, timeout=15)
    assert p.returncode == 0, p.stderr
    response = json.loads(p.stdout)
    if arguments[0] == "dev-spec":
        assert response == source_spec()
    elif arguments[0] == "dev-doctor":
        assert response["source_compatible"]
        assert not response["release_authorized"]
    else:
        assert response["decision"] == "DENY"
        assert response["environment"] == "OFFLINE_DEMO_ONLY"
        assert response["payload"]["decision"] == "DENY"
        assert response["executed"] is False


@pytest.mark.parametrize("args", [
    ["sdk-demo", "execute"],
    ["sdk-demo", "denied-plan"],
    ["sdk-demo", "business-scenario", "--extra-orders", "-1"],
    ["sdk-demo", "denied-plan", "--operation-id", "finance.wire"],
    ["sdk-demo", "business-metrics", "--operation-id", "business.inventory.stock-preview.v1"],
    ["sdk-demo", "negative-proof", "--operation-id", "business.inventory.stock-preview.v1", "--execute"],
])
def test_cli_developer_invalid_or_live_commands_denied(args):
    p = subprocess.run([sys.executable, str(CLI), *args],
                       capture_output=True, text=True, check=False, timeout=15)
    assert p.returncode != 0
    assert not p.stdout


def test_sdk_has_no_network_or_api_execution_layer():
    module = (ROOT / "apps/api/app/phase03_developer_tools.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_developer_tools" not in main
    for forbidden in ("APIRouter(", "httpx", "requests.", "subprocess.",
                      "socket.socket(", "psycopg", "urllib.request",
                      "urlopen(", "redis.", "openai.", "google.generativeai"):
        assert forbidden not in module
