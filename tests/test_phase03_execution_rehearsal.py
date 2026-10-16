"""P3-06: controlled execution rehearsal MUST remain offline DENY-only."""
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
    DemoPlanningRequest, TARGETS, create_denied_plan,
)
from app.phase03_execution_rehearsal import (
    DemoExecutionAttempt, ExecutionAttemptDenied, DemoAuditNotFound,
    DemoExecutionAudit, MISSING_TRUST, MAX_PER_TENANT, MAX_ATTEMPTS,
    reject_demo_execution, verify_demo_audit_sequence,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"
CONTRACT = ROOT / "contracts/intelligent/v1/execution_rehearsal.json"
SCENES = {
    "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
    "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
    "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
    "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
}


def attempt(
    operation="business.inventory.stock-preview.v1", *,
    tenant=None, request_id="DEMO-REQ-EXECUTION-001",
    attempt_id="DEMO-ATTEMPT-001", version=1,
    labels=(), tick=101,
):
    tenant = uuid4() if tenant is None else tenant
    intent = DemoCapabilityIntent(
        tenant_id=tenant, actor_label="DEMO-ACTOR-SAFETY",
        request_id=request_id, operation_id=operation,
        scenario=SCENES[operation], logical_tick=100,
    )
    denied = OfflineCapabilityPreview().inspect_once(intent)
    req = DemoPlanningRequest(
        intent=intent, denial_receipt=denied,
        target_label=TARGETS[operation], expected_resource_version=1,
        requested_tick=100,
    )
    plan = create_denied_plan(req)
    return DemoExecutionAttempt(
        plan=plan, source_request=req, attempt_id=attempt_id,
        observed_tick=tick, expected_resource_version=version,
        reviewer_labels=labels,
    )


@pytest.mark.parametrize("operation", tuple(OPERATION_SPECS))
def test_every_operation_permanently_rejects_even_with_fake_reviewers(operation):
    a = attempt(operation, labels=("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA"))
    r = reject_demo_execution(a)
    assert r.decision == "DENY"
    assert r.state == "REJECTED_NO_DISPATCH"
    assert r.effect == OPERATION_SPECS[operation][1]
    assert r.operation_id == operation
    assert r.simulated_no_dispatch_consistent
    assert r.demo_resource_version_unchanged
    assert not r.demo_plan_expired
    assert r.reviewer_count == 2
    assert r.second_reviewer_needed is (OPERATION_SPECS[operation][3] == "high")
    assert r.missing_trust_codes[:len(MISSING_TRUST)] == MISSING_TRUST
    assert not r.actor_authenticated
    assert not r.human_approval_verified
    assert not r.tenant_scope_verified
    assert not r.side_effects_authorized
    assert not r.side_effects_performed
    assert not r.provider_called
    assert not r.provider_receipt_verified
    assert not r.independent_readback_performed
    assert not r.durable_idempotency_verified
    assert not r.compensation_performed
    assert not r.customer_data_accessed
    assert not r.release_authorized


def test_high_risk_finance_no_real_approval_or_autorollback():
    r = reject_demo_execution(attempt(
        "business.finance.reconciliation-proposal.v1",
        labels=("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA"),
    ))
    assert r.second_reviewer_needed
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in r.missing_trust_codes
    assert "SPECIFIC_EFFECT_HUMAN_REVIEW_UNVERIFIED" in r.missing_trust_codes
    assert "FUTURE_REAL_EFFECT_REQUIRES_VERIFIED_REVERSAL_PLAN" in r.recovery_note
    assert not r.compensation_performed


def test_validation_only_scenario_has_no_compensation():
    r = reject_demo_execution(attempt("business.lead-intake.validate.v1"))
    assert r.recovery_note == "NO_COMPENSATION_NEEDED_BECAUSE_NO_DISPATCH_OCCURRED"
    assert not r.side_effects_performed


def test_stale_revision_and_expiry_remain_denied():
    a = attempt(version=2, tick=112)
    result = reject_demo_execution(a)
    assert not result.demo_resource_version_unchanged
    assert result.demo_plan_expired
    assert "DEMO_RESOURCE_VERSION_CHANGED" in result.missing_trust_codes
    assert "DEMO_PLAN_EXPIRED" in result.missing_trust_codes
    assert result.decision == "DENY"


@pytest.mark.parametrize("bad", [
    {"claimed_approved": True}, {"claimed_approved": 1},
    {"allow_side_effects": True}, {"allow_side_effects": 0},
    {"mode": "LIVE_EXECUTE"}, {"mode": None},
    {"attempt_id": "LIVE-TRANSACTION"},
    {"attempt_id": "DEMO-ATTEMPT-"},
    {"attempt_id": "DEMO-ATTEMPT-A\n"},
    {"attempt_id": None}, {"attempt_id": True},
    {"observed_tick": True}, {"observed_tick": None},
    {"observed_tick": -1}, {"observed_tick": 1_000_001},
    {"expected_resource_version": True},
    {"expected_resource_version": -1},
    {"expected_resource_version": 1001},
    {"reviewer_labels": ["DEMO-REVIEWER-ALPHA"]},
    {"reviewer_labels": ("REAL-APPROVAL",)},
    {"reviewer_labels": ("DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-ALPHA")},
    {"reviewer_labels": ("DEMO-REVIEWER-A", "DEMO-REVIEWER-B", "DEMO-REVIEWER-C")},
    {"reviewer_labels": (None,)},
])
def test_attempts_cannot_claim_permissions_or_smuggle_types(bad):
    with pytest.raises(ExecutionAttemptDenied):
        reject_demo_execution(replace(attempt(), **bad))


def test_wrong_tenant_plan_and_tampered_source_rejected():
    a = attempt()
    b = attempt(tenant=uuid4())
    with pytest.raises(ExecutionAttemptDenied):
        reject_demo_execution(replace(a, source_request=b.source_request))
    with pytest.raises(ExecutionAttemptDenied):
        reject_demo_execution(replace(a, plan=replace(a.plan, execution_authorized=True)))
    with pytest.raises(ExecutionAttemptDenied):
        reject_demo_execution(replace(a, plan=replace(a.plan, checksum="0"*64)))


def test_evidence_before_plan_clock_rejected():
    with pytest.raises(ExecutionAttemptDenied):
        reject_demo_execution(attempt(tick=99))


def test_audit_replay_returns_identical_local_denial():
    audit = DemoExecutionAudit()
    a = attempt()
    r, e = audit.reject_once(a)
    again_r, again_e = audit.reject_once(a)
    assert (r, e) == (again_r, again_e)
    assert e.audit_sequence == 1
    assert e.previous_demo_hash == "0"*64
    assert not e.digest_is_authenticated
    assert not e.externally_persisted
    assert not e.audit_proof_is_durable
    assert not e.execution_authorized
    result = verify_demo_audit_sequence(a.plan.tenant_id, ((r, e),))
    assert result.demo_internal_links_consistent
    assert not result.signed_by_authoritative_identity
    assert not result.durable_storage_verified
    assert not result.real_execution_verified
    assert result.decision == "DENY"


def test_conflicting_replay_cannot_replace_record():
    audit = DemoExecutionAudit()
    a = attempt()
    r, e = audit.reject_once(a)
    with pytest.raises(ExecutionAttemptDenied):
        audit.reject_once(replace(a, reviewer_labels=("DEMO-REVIEWER-ALPHA",)))
    with pytest.raises(ExecutionAttemptDenied):
        audit.reject_once(replace(a, expected_resource_version=2))
    assert audit.inspect(
        tenant_id=a.plan.tenant_id, attempt_id=a.attempt_id,
    ) == e
    assert len(audit._entries) == 1


def test_foreign_tenant_cannot_inspect_demo_audit():
    a = attempt()
    audit = DemoExecutionAudit()
    audit.reject_once(a)
    with pytest.raises(DemoAuditNotFound):
        audit.inspect(tenant_id=uuid4(), attempt_id=a.attempt_id)


def test_same_id_in_two_synthetic_tenants_is_isolated():
    audit = DemoExecutionAudit()
    first = attempt()
    other = attempt(tenant=uuid4())
    x, ex = audit.reject_once(first)
    y, ey = audit.reject_once(other)
    assert ex.demo_chain_hash != ey.demo_chain_hash
    assert ex.tenant_id != ey.tenant_id
    assert audit.inspect(tenant_id=first.plan.tenant_id,
                         attempt_id=first.attempt_id) == ex
    assert audit.inspect(tenant_id=other.plan.tenant_id,
                         attempt_id=other.attempt_id) == ey


def test_concurrent_repeated_demo_denial_is_one_entry():
    audit, a = DemoExecutionAudit(), attempt()
    with ThreadPoolExecutor(max_workers=12) as pool:
        records = list(pool.map(lambda _: audit.reject_once(a), range(30)))
    assert len(audit._entries) == 1
    assert all(r == records[0] for r in records)


def test_per_tenant_bounded_audit_memory():
    audit, tenant = DemoExecutionAudit(), uuid4()
    for i in range(MAX_PER_TENANT):
        audit.reject_once(attempt(
            tenant=tenant, attempt_id=f"DEMO-ATTEMPT-LIMIT-{i:03}",
            request_id=f"DEMO-REQ-LIMIT-{i:03}",
        ))
    assert len(audit._entries) == MAX_PER_TENANT
    with pytest.raises(ExecutionAttemptDenied):
        audit.reject_once(attempt(
            tenant=tenant, attempt_id="DEMO-ATTEMPT-OVERFLOW",
            request_id="DEMO-REQ-OVERFLOW",
        ))


def test_global_audit_capacity_limit():
    audit = DemoExecutionAudit()
    for i in range(MAX_ATTEMPTS):
        audit.reject_once(attempt(
            tenant=UUID(int=1 + i // MAX_PER_TENANT),
            attempt_id=f"DEMO-ATTEMPT-FULL-{i:03}",
            request_id=f"DEMO-REQ-FULL-{i:03}",
        ))
    assert len(audit._entries) == MAX_ATTEMPTS
    with pytest.raises(ExecutionAttemptDenied):
        audit.reject_once(attempt(
            tenant=uuid4(), attempt_id="DEMO-ATTEMPT-EXTRA",
            request_id="DEMO-REQ-EXTRA",
        ))


def test_hash_chain_two_entries_and_modified_link_detection():
    audit = DemoExecutionAudit()
    tenant = uuid4()
    a = attempt(tenant=tenant)
    b = attempt(tenant=tenant, request_id="DEMO-REQ-EXECUTION-002",
                attempt_id="DEMO-ATTEMPT-002")
    ra, ea = audit.reject_once(a)
    rb, eb = audit.reject_once(b)
    assert eb.audit_sequence == 2
    assert eb.previous_demo_hash == ea.demo_chain_hash
    valid = verify_demo_audit_sequence(tenant, ((ra, ea), (rb, eb)))
    assert valid.demo_internal_links_consistent
    assert valid.entries_inspected == 2
    assert not verify_demo_audit_sequence(
        tenant, ((ra, ea), (rb, replace(eb, demo_chain_hash="x"*64))),
    ).demo_internal_links_consistent
    assert not verify_demo_audit_sequence(
        tenant, ((rb, eb), (ra, ea)),
    ).demo_internal_links_consistent
    assert not verify_demo_audit_sequence(
        tenant, ((ra, replace(ea, execution_authorized=True)),),
    ).demo_internal_links_consistent
    assert not verify_demo_audit_sequence(
        tenant, ((ra, replace(ea, digest_is_authenticated=True)),),
    ).demo_internal_links_consistent


def test_tampered_rejection_fingerprint_breaks_demo_audit_verification():
    a = attempt()
    result, entry = DemoExecutionAudit().reject_once(a)
    assert not verify_demo_audit_sequence(
        a.plan.tenant_id, ((replace(result, side_effects_performed=True), entry),),
    ).demo_internal_links_consistent


@pytest.mark.parametrize("bad", [None, "tenant", True, 7])
def test_invalid_audit_tenant_identity_rejected(bad):
    a = attempt()
    result, entry = DemoExecutionAudit().reject_once(a)
    with pytest.raises(ExecutionAttemptDenied):
        verify_demo_audit_sequence(bad, ((result, entry),))


def test_immutable_rejection_and_audit_records():
    a = attempt()
    result, entry = DemoExecutionAudit().reject_once(a)
    with pytest.raises(FrozenInstanceError):
        result.side_effects_authorized = True
    with pytest.raises(FrozenInstanceError):
        entry.digest_is_authenticated = True


def test_execution_contract_is_explicitly_no_go():
    data = json.loads(CONTRACT.read_text())
    assert data["milestone"] == "P3-06"
    assert data["mode"] == "DENY_ONLY_EXECUTION_REHEARSAL"
    assert data["default_decision"] == "DENY"
    assert data["terminal_demo_state"] == "REJECTED_NO_DISPATCH"
    assert data["phase01_verified"] == 3
    assert data["phase02_operational_approved"] is False
    assert data["real_execution_authorized"] is False
    assert data["trusted_identity_available"] is False
    assert data["provider_access_available"] is False
    assert data["durable_replay_protection_available"] is False
    assert data["any_effect_performed"] is False
    assert data["automatic_rollback_available"] is False
    assert data["demo_audit_properties"]["signed_or_durable_evidence"] is False
    assert data["required_trust_codes"] == list(MISSING_TRUST)


@pytest.mark.parametrize("operation", tuple(OPERATION_SPECS))
def test_execution_cli_returns_no_authority(operation):
    p = subprocess.run(
        [sys.executable, str(CLI), "execution-rehearsal", operation],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert data["evidence_scope"] == "UNAUTHENTICATED_VOLATILE_DEMO_ONLY"
    rejection = data["rejection"]
    audit = data["demo_audit"]
    assert rejection["decision"] == "DENY"
    assert rejection["state"] == "REJECTED_NO_DISPATCH"
    assert rejection["side_effects_performed"] is False
    assert rejection["release_authorized"] is False
    assert audit["execution_authorized"] is False
    assert audit["digest_is_authenticated"] is False


def test_cli_fake_reviewers_do_not_approve_finance():
    p = subprocess.run([
        sys.executable, str(CLI), "execution-rehearsal",
        "business.finance.reconciliation-proposal.v1",
        "--reviewer-count", "2",
    ], capture_output=True, text=True, timeout=20, check=False)
    assert p.returncode == 0, p.stderr
    output = json.loads(p.stdout)["rejection"]
    assert output["reviewer_count"] == 2
    assert output["second_reviewer_needed"] is True
    assert "SECOND_INDEPENDENT_REVIEW_UNVERIFIED" in output["missing_trust_codes"]
    assert output["decision"] == "DENY"
    assert output["human_approval_verified"] is False


def test_cli_stale_resource_and_expired_rehearsal():
    p = subprocess.run([
        sys.executable, str(CLI), "execution-rehearsal",
        "business.inventory.stock-preview.v1",
        "--observed-version", "2", "--observed-tick", "112",
    ], capture_output=True, text=True, timeout=20, check=False)
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)["rejection"]
    assert not report["demo_resource_version_unchanged"]
    assert report["demo_plan_expired"]
    assert report["decision"] == "DENY"


@pytest.mark.parametrize("args", [
    ["execution-rehearsal", "finance.transfer.real.v1"],
    ["execution-rehearsal", "business.inventory.stock-preview.v1", "--execute"],
    ["execution-rehearsal", "business.inventory.stock-preview.v1", "--reviewer-count", "3"],
    ["execution-rehearsal", "business.inventory.stock-preview.v1", "--observed-version", "-1"],
    ["execution-rehearsal", "business.inventory.stock-preview.v1", "--observed-tick", "true"],
    ["execution-rehearsal", "business.inventory.stock-preview.v1", "--request-id", "LIVE-CUSTOMER"],
])
def test_cli_has_no_live_execution_or_untrusted_params(args):
    p = subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode != 0
    assert not p.stdout


def test_main_service_unrouted_execution_rehearsal_has_no_transport():
    src = (ROOT / "apps/api/app/phase03_execution_rehearsal.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_execution_rehearsal" not in main
    for forbidden in (
        "APIRouter(", "httpx", "requests.", "subprocess.",
        "socket.socket(", "urlopen(", "psycopg", "redis.",
        "google.generativeai", "openai.", "urllib.request",
    ):
        assert forbidden not in src
