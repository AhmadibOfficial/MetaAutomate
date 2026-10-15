"""P3-02: negative-only capability planning, binding and replay regression."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

import pytest

from app.phase03_intelligent_ecosystem import (
    DemoCapabilityIntent, OfflineCapabilityPreview, OPERATION_SPECS,
)
from app.phase03_capability_planning import (
    REQUIRED_GATES, TARGETS, TTL_TICKS, MAX_PLANS, MAX_PER_TENANT,
    DemoPlanningRequest, OfflineCapabilityPlanRegistry, OfflinePlanDenied,
    OfflinePlanNotFound, create_denied_plan, inspect_denied_plan,
    _fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"
SCENE = {
    "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
    "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
    "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
    "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
}


def request(operation="business.inventory.stock-preview.v1", *,
            tenant=None, req_id="DEMO-REQ-PLANNING-001", target=None,
            version=1, tick=100):
    tenant = tenant if tenant is not None else uuid4()
    intent = DemoCapabilityIntent(
        tenant_id=tenant, actor_label="DEMO-ACTOR-PLANNER",
        request_id=req_id, operation_id=operation,
        scenario=SCENE[operation], logical_tick=tick,
    )
    receipt = OfflineCapabilityPreview().inspect_once(intent)
    return DemoPlanningRequest(
        intent=intent, denial_receipt=receipt,
        target_label=target if target is not None else TARGETS[operation],
        expected_resource_version=version, requested_tick=tick,
    )


@pytest.mark.parametrize("operation", tuple(OPERATION_SPECS))
def test_plan_never_executes_uses_operation_scope_and_denies(operation):
    req = request(operation)
    result = create_denied_plan(req)
    spec = OPERATION_SPECS[operation]
    assert result.decision == "DENY"
    assert result.lifecycle == "DESIGN_ONLY_NOT_EXECUTABLE"
    assert result.capability_id == spec[0]
    assert result.effect == spec[1]
    assert result.required_scope == spec[2]
    assert result.human_approval_required is spec[4]
    assert result.high_risk_dual_review_required is (spec[3] == "high")
    assert result.admission_receipt_checksum == req.denial_receipt.checksum
    assert result.resource_label == TARGETS[operation]
    assert result.mandatory_unverified_gates[:len(REQUIRED_GATES)] == REQUIRED_GATES
    assert result.review_steps[-1] == "STOP_NO_AUTOMATED_EXECUTION"
    assert not result.execution_authorized
    assert not result.execution_performed
    assert not result.workflow_enqueued
    assert not result.provider_called
    assert not result.provider_receipt_verified
    assert not result.human_approval_verified
    assert not result.tenant_authentication_verified
    assert not result.scope_verified
    assert not result.durable_idempotency_verified
    assert not result.persisted
    inspection = inspect_denied_plan(result, req, observed_tick=101)
    assert inspection.synthetic_integrity_consistent
    assert inspection.input_bound
    assert not inspection.expired
    assert inspection.decision == "DENY"
    assert not inspection.effective_permission_granted


def test_high_risk_finance_adds_second_review_denial():
    fin = create_denied_plan(request("business.finance.reconciliation-proposal.v1"))
    crm = create_denied_plan(request("business.crm.sync-proposal.v1"))
    assert fin.high_risk_dual_review_required is True
    assert "DEMO_SECOND_REVIEWER_NOT_VERIFIED" in fin.review_steps
    assert "specific_effect_approval_unverified" in fin.mandatory_unverified_gates
    assert crm.high_risk_dual_review_required is False
    assert "DEMO_SECOND_REVIEWER_NOT_VERIFIED" not in crm.review_steps


def test_expiration_report_cannot_enable_permission():
    req = request()
    plan = create_denied_plan(req)
    assert plan.expires_tick == req.requested_tick + TTL_TICKS
    at_boundary = inspect_denied_plan(plan, req, observed_tick=plan.expires_tick)
    after_boundary = inspect_denied_plan(plan, req, observed_tick=plan.expires_tick + 1)
    assert at_boundary.expired is False
    assert after_boundary.expired is True
    assert at_boundary.decision == after_boundary.decision == "DENY"
    assert not after_boundary.execution_authorized


@pytest.mark.parametrize("invalid", [
    "LIVE-STOCK-ABC", "DEMO-TARGET-FOREIGN-001",
    "https://provider.example.com/api", "../secrets", "",
    None, True, {"external": "provider"},
])
def test_non_allowlisted_targets_fail_closed(invalid):
    valid_request = request()
    changed = replace(valid_request, target_label=invalid)
    with pytest.raises(OfflinePlanDenied):
        create_denied_plan(changed)


@pytest.mark.parametrize("invalid", [-1, 0, 1001, 1.2, "1", None, True])
def test_invalid_resource_revision_fails_closed(invalid):
    with pytest.raises(OfflinePlanDenied):
        create_denied_plan(request(version=invalid))


@pytest.mark.parametrize("invalid", [-1, 999991, 1_000_000, True, "100", None])
def test_invalid_or_unbounded_clock_fails_closed(invalid):
    if invalid in (True,):
        expected = request()
        broken = replace(expected, requested_tick=invalid)
    elif type(invalid) is int and invalid < 0:
        # P3-01 cannot mint a receipt for negative logical ticks.
        expected = request()
        broken = replace(expected, requested_tick=invalid)
    else:
        expected = request()
        broken = replace(expected, requested_tick=invalid)
    with pytest.raises(OfflinePlanDenied):
        create_denied_plan(broken)


def test_invalid_request_and_wrong_denial_receipt_rejected():
    good = request()
    other = request(tenant=uuid4())
    invalids = [
        {"denial_receipt": other.denial_receipt},
        {"denial_receipt": replace(good.denial_receipt, decision="ALLOW")},
        {"denial_receipt": replace(good.denial_receipt, checksum="0"*64)},
        {"denial_receipt": None},
        {"intent": replace(good.intent, tenant_id=uuid4())},
        {"intent": replace(good.intent, operation_id=[])},
        {"intent": replace(good.intent, actor_label="OWNER")},
        {"intent": replace(good.intent, scenario="CUSTOMER-DATA")},
    ]
    for changes in invalids:
        with pytest.raises(OfflinePlanDenied):
            create_denied_plan(replace(good, **changes))


@pytest.mark.parametrize("changes", [
    {"decision": "ALLOW"},
    {"execution_authorized": True},
    {"execution_performed": True},
    {"provider_called": True},
    {"workflow_enqueued": True},
    {"provider_receipt_verified": True},
    {"human_approval_verified": True},
    {"tenant_authentication_verified": True},
    {"scope_verified": True},
    {"durable_idempotency_verified": True},
    {"persisted": True},
    {"resource_label": "DEMO-TARGET-OTHER-001"},
    {"expected_resource_version": 2},
    {"tenant_demo_marker": "DEMO-TENANT-ATTACKER"},
    {"admission_receipt_checksum": "f"*64},
    {"mandatory_unverified_gates": ()},
    {"checksum": "0"*64},
])
def test_forged_plan_cannot_pass_consistency_check(changes):
    req = request()
    plan = create_denied_plan(req)
    forged = replace(plan, **changes)
    assert not inspect_denied_plan(
        forged, req, observed_tick=102,
    ).synthetic_integrity_consistent
    assert inspect_denied_plan(
        forged, req, observed_tick=102,
    ).decision == "DENY"


def test_rehashed_forgery_is_still_detected_by_reconstruction():
    req = request()
    original = create_denied_plan(req)
    forged = replace(original, execution_authorized=True, checksum="")
    forged = replace(forged, checksum=_fingerprint(forged))
    result = inspect_denied_plan(forged, req, observed_tick=101)
    assert not result.synthetic_integrity_consistent
    assert result.decision == "DENY"


def test_plan_dataclass_does_not_allow_inplace_mutation():
    p = create_denied_plan(request())
    with pytest.raises(FrozenInstanceError):
        p.execution_authorized = True


def test_registry_deduplicates_and_conflicts_are_rejected():
    registry = OfflineCapabilityPlanRegistry()
    a = request()
    first = registry.plan_once(a)
    assert registry.plan_once(a) == first
    assert len(registry._by_key) == 1
    with pytest.raises(OfflinePlanDenied):
        registry.plan_once(replace(a, expected_resource_version=2))
    assert len(registry._by_key) == 1


def test_registry_denies_foreign_tenant_lookup():
    registry = OfflineCapabilityPlanRegistry()
    a = request()
    registry.plan_once(a)
    with pytest.raises(OfflinePlanNotFound):
        registry.inspect(tenant_id=uuid4(), request_id=a.intent.request_id)
    assert registry.inspect(
        tenant_id=a.intent.tenant_id, request_id=a.intent.request_id
    ).decision == "DENY"


def test_concurrent_preview_only_once():
    gate, req = OfflineCapabilityPlanRegistry(), request()
    with ThreadPoolExecutor(max_workers=10) as executor:
        values = list(executor.map(lambda _: gate.plan_once(req), range(30)))
    assert len(gate._by_key) == 1
    assert all(x == values[0] for x in values)
    assert all(x.decision == "DENY" for x in values)


def test_per_tenant_capacity_bounded():
    registry = OfflineCapabilityPlanRegistry()
    tenant = uuid4()
    for i in range(MAX_PER_TENANT):
        registry.plan_once(request(tenant=tenant, req_id=f"DEMO-REQ-ITEM-{i:03}"))
    with pytest.raises(OfflinePlanDenied):
        registry.plan_once(request(tenant=tenant, req_id="DEMO-REQ-EXTRA"))
    assert len(registry._by_key) == MAX_PER_TENANT


def test_total_capacity_bounded():
    registry = OfflineCapabilityPlanRegistry()
    for i in range(MAX_PLANS):
        registry.plan_once(request(
            tenant=UUID(int=1 + i // MAX_PER_TENANT),
            req_id=f"DEMO-REQ-ITEM-{i % MAX_PER_TENANT:03}",
        ))
    assert len(registry._by_key) == MAX_PLANS
    with pytest.raises(OfflinePlanDenied):
        registry.plan_once(request(tenant=uuid4(), req_id="DEMO-REQ-OVERFLOW"))


def test_developer_cli_plan_is_not_executable():
    for operation in OPERATION_SPECS:
        p = subprocess.run(
            [sys.executable, str(CLI), "plan", operation],
            capture_output=True, text=True, timeout=12, check=False,
        )
        assert p.returncode == 0, p.stderr
        result = json.loads(p.stdout)
        assert result["decision"] == "DENY"
        assert not result["execution_authorized"]
        assert not result["provider_called"]
        assert result["synthetic_integrity_consistent"]
        assert result["lifecycle"] == "DESIGN_ONLY_NOT_EXECUTABLE"


@pytest.mark.parametrize("args", [
    ["plan", "business.inventory.stock-preview.v1", "--resource-version", "0"],
    ["plan", "business.crm.sync-proposal.v1", "--resource-version", "-1"],
    ["plan", "business.inventory.stock-preview.v1", "--resource-version", "1001"],
    ["plan", "business.inventory.stock-preview.v1", "--request-id", "REAL"],
    ["plan", "business.inventory.stock-preview.v1", "--execute"],
    ["plan", "business.unsupported.operation.v1"],
])
def test_developer_cli_plan_rejects_unsupported_actions(args):
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, timeout=12, check=False,
    )
    assert result.returncode != 0
    assert not result.stdout


def test_planner_manifest_matches_frozen_offline_source_contract():
    from app.phase03_capability_planning import REQUIRED_GATES, TARGETS, TTL_TICKS
    manifest = json.loads(
        (ROOT / "contracts/intelligent/v1/planning.json").read_text()
    )
    assert manifest["schema_version"] == 1
    assert manifest["phase"] == "03"
    assert manifest["milestone"] == "P3-02"
    assert manifest["default_decision"] == "DENY"
    assert manifest["lifecycle"] == "DRAFT"
    assert manifest["trusted_execution_authorization_available"] is False
    assert manifest["external_reads_performed"] is False
    assert manifest["external_writes_performed"] is False
    assert manifest["real_tenant_scope_verified"] is False
    assert manifest["provider_receipts_authenticated"] is False
    assert manifest["maximum_logical_ttl_ticks"] == TTL_TICKS
    assert tuple(manifest["mandatory_unverified_gates"]) == REQUIRED_GATES
    assert {r["operation_id"] for r in manifest["operations"]} == set(OPERATION_SPECS)
    for row in manifest["operations"]:
        op = row["operation_id"]
        assert row["capability_id"] == OPERATION_SPECS[op][0]
        assert row["fixture_resource"] == TARGETS[op]
        assert row["execution_authorized"] is False
        assert row["provider_call_available"] is False
        assert row["second_reviewer_needed_for_live"] is (
            OPERATION_SPECS[op][3] == "high"
        )


def test_phase03_planner_is_unrouted_without_provider_or_db_side_effect():
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_capability_planning" not in main
    src = (ROOT / "apps/api/app/phase03_capability_planning.py").read_text()
    for forbidden in ("APIRouter(", "httpx", "requests.", "urlopen(",
                      "subprocess.", "psycopg", "redis.", "urllib.request",
                      "socket.socket(", "openai.", "google.generativeai"):
        assert forbidden not in src
