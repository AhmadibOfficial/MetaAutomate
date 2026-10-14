"""P3-01: deny-only intelligent capability developer contract security tests."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

import pytest

from app.phase03_intelligent_ecosystem import (
    APPROVAL_DENIAL_REASON, BASE_DENIAL_REASONS,
    MAX_ANALYTICS_EVENTS, MAX_PER_TENANT, MAX_REQUESTS, MAX_TENANTS,
    CapabilityDenied, ContractRejected, DemoCapabilityIntent,
    OfflineCapabilityPreview, ReceiptRejected,
    OPERATION_SPECS, aggregate_synthetic_denials,
    validate_phase03_manifest, verify_synthetic_denial,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "contracts/intelligent/v1/capabilities.json"
DOMAIN = ROOT / "contracts/domains/v1/operations.json"
CLI = ROOT / "scripts/phase03_offline_cli.py"
OPS = tuple(OPERATION_SPECS)
SCENARIOS = {
    "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
    "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
    "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
    "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
}


def demo(*, tenant=None, actor="DEMO-ACTOR-RESEARCHER",
         request_id="DEMO-REQ-TEST-001", operation=None, scenario=None,
         tick=100):
    op = operation if operation is not None else OPS[0]
    return DemoCapabilityIntent(
        tenant_id=tenant if tenant is not None else uuid4(),
        actor_label=actor, request_id=request_id,
        operation_id=op,
        scenario=SCENARIOS[op] if scenario is None else scenario,
        logical_tick=tick,
    )


def source_manifests():
    return json.loads(MANIFEST.read_text()), json.loads(DOMAIN.read_text())


def preview(intent):
    return OfflineCapabilityPreview().inspect_once(intent)


def test_manifest_exact_phase02_contract_parity():
    m, domain = source_manifests()
    operations = validate_phase03_manifest(m, domain)
    assert len(operations) == 4
    assert all(o["lifecycle"] == "draft" for o in operations)
    assert all(o["execution_enabled"] is False for o in operations)
    assert all(o["provider_bound"] is False for o in operations)
    assert all(o["autonomous_execution_enabled"] is False for o in operations)


@pytest.mark.parametrize("operation", OPS)
def test_all_operations_default_deny_with_no_authority(operation):
    intent = demo(operation=operation)
    proof = preview(intent)
    assert proof.operation_id == operation
    assert proof.capability_id == OPERATION_SPECS[operation][0]
    assert proof.required_scope == OPERATION_SPECS[operation][2]
    assert proof.decision == "DENY"
    assert proof.simulation_only
    assert proof.reasons[:len(BASE_DENIAL_REASONS)] == BASE_DENIAL_REASONS
    assert proof.approval_required == OPERATION_SPECS[operation][4]
    assert (APPROVAL_DENIAL_REASON in proof.reasons) == proof.approval_required
    assert not proof.actor_authenticated
    assert not proof.tenant_authenticated
    assert not proof.scope_verified
    assert not proof.human_approval_verified
    assert not proof.provider_identity_verified
    assert not proof.execution_authorized
    assert not proof.execution_performed
    assert not proof.provider_called
    assert not proof.customer_data_accessed
    assert not proof.durable_evidence
    assert verify_synthetic_denial(proof, intent).synthetic_checksum_consistent


@pytest.mark.parametrize("bad", [
    "owner", "DEMO-ACTOR-", "DEMO-ACTOR-USER@COMPANY", "", None, True, 2,
])
def test_invalid_actor_never_creates_preview(bad):
    with pytest.raises(CapabilityDenied):
        preview(demo(actor=bad))


@pytest.mark.parametrize("bad", [
    "owner-grant", "DEMO-REQ-", "../secret", "DEMO-REQ-A;DROP",
    "DEMO-REQ-B\n", None, True, 1,
])
def test_invalid_request_id_denied(bad):
    with pytest.raises(CapabilityDenied):
        preview(demo(request_id=bad))


@pytest.mark.parametrize("bad", [-1, True, "100", 1.0, None, 1_000_001])
def test_invalid_logical_clock_denied(bad):
    with pytest.raises(CapabilityDenied):
        preview(demo(tick=bad))


@pytest.mark.parametrize("bad", [
    "REAL-CUSTOMER-RECORD", "DEMO-STOCK-CHECK",
    {"account": "private"}, None, 999,
])
def test_scenario_substitution_denied(bad):
    # Passing scenario=None to helper selects an approved test fixture only.
    if bad is None:
        bad = "none"
    with pytest.raises(CapabilityDenied):
        preview(demo(scenario=bad))


def test_unlisted_operation_denied():
    fake = replace(demo(), operation_id="system.execute-real-write.v1")
    with pytest.raises(CapabilityDenied):
        preview(fake)


@pytest.mark.parametrize("tenant", [None, "org", 1, True])
def test_invalid_tenant_identity_type_denied(tenant):
    fake = replace(demo(), tenant_id=tenant)
    with pytest.raises(CapabilityDenied):
        preview(fake)


def test_cross_tenant_ids_different_and_non_privileged():
    a = demo()
    b = replace(a, tenant_id=uuid4())
    ra, rb = preview(a), preview(b)
    assert ra.tenant_demo_marker != rb.tenant_demo_marker
    assert ra.decision == rb.decision == "DENY"
    assert not verify_synthetic_denial(ra, b).request_matches
    assert not verify_synthetic_denial(ra, b).synthetic_checksum_consistent


def test_same_request_idempotent_but_conflicts_denied():
    gate = OfflineCapabilityPreview()
    a = demo()
    ra = gate.inspect_once(a)
    assert gate.inspect_once(a) == ra
    assert len(gate._by_id) == 1
    with pytest.raises(CapabilityDenied):
        gate.inspect_once(replace(a, actor_label="DEMO-ACTOR-ANOTHER"))
    assert len(gate._by_id) == 1


def test_same_key_different_tenants_are_separate_demo_partitions():
    a = demo()
    b = replace(a, tenant_id=uuid4())
    gate = OfflineCapabilityPreview()
    a_result = gate.inspect_once(a)
    b_result = gate.inspect_once(b)
    assert a_result != b_result
    assert len(gate._by_id) == 2


def test_concurrent_identical_preview_reuses_one_denial():
    gate, intent = OfflineCapabilityPreview(), demo()
    with ThreadPoolExecutor(max_workers=12) as pool:
        receipts = list(pool.map(lambda _: gate.inspect_once(intent), range(45)))
    assert all(r == receipts[0] for r in receipts)
    assert len(gate._by_id) == 1
    assert receipts[0].decision == "DENY"


def test_concurrent_conflicting_replay_exact_one_winner():
    gate = OfflineCapabilityPreview()
    base = demo()
    other = replace(base, actor_label="DEMO-ACTOR-OTHER")
    def one(i):
        try:
            gate.inspect_once(base if i % 2 else other)
            return True
        except CapabilityDenied:
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(one, range(36)))
    assert 1 <= sum(statuses) <= 18
    assert len(gate._by_id) == 1


def test_per_tenant_capacity_denial_does_not_evict():
    gate = OfflineCapabilityPreview()
    tenant = uuid4()
    for i in range(MAX_PER_TENANT):
        gate.inspect_once(demo(tenant=tenant, request_id=f"DEMO-REQ-ITEM-{i:03}"))
    with pytest.raises(CapabilityDenied):
        gate.inspect_once(demo(tenant=tenant, request_id="DEMO-REQ-EXTRA"))
    assert len(gate._by_id) == MAX_PER_TENANT


def test_global_capacity_denial_preserves_existing_receipts():
    gate = OfflineCapabilityPreview()
    tenants = [uuid4() for _ in range(MAX_TENANTS)]
    for i in range(MAX_REQUESTS):
        gate.inspect_once(demo(
            tenant=tenants[i // MAX_PER_TENANT],
            request_id=f"DEMO-REQ-{i % MAX_PER_TENANT:03}",
        ))
    assert len(gate._by_id) == MAX_REQUESTS
    with pytest.raises(CapabilityDenied):
        gate.inspect_once(demo(tenant=tenants[0], request_id="DEMO-REQ-OVERFLOW"))
    assert len(gate._by_id) == MAX_REQUESTS


@pytest.mark.parametrize("changed", [
    {"decision": "ALLOW"},
    {"execution_authorized": True},
    {"execution_performed": True},
    {"actor_authenticated": True},
    {"human_approval_verified": True},
    {"provider_called": True},
    {"provider_identity_verified": True},
    {"scope_verified": True},
    {"checksum": "0"*64},
    {"request_id": "DEMO-REQ-OTHER"},
    {"tenant_demo_marker": "DEMO-TENANT-FORGED"},
    {"required_scope": "business.finance.write"},
    {"reasons": ("allowed",)},
])
def test_forged_or_tampered_receipt_is_not_verified(changed):
    intent = demo()
    proof = preview(intent)
    bad = replace(proof, **changed)
    v = verify_synthetic_denial(bad, intent)
    assert not v.synthetic_checksum_consistent
    assert v.decision == "DENY"
    assert not v.verified_execution
    assert not v.real_human_approval_verified
    assert not v.authoritative_provider_receipt_verified
    assert not v.independent_provider_readback_performed


def test_valid_demo_checksum_is_not_real_executed_result():
    intent = demo()
    receipt = preview(intent)
    verdict = verify_synthetic_denial(receipt, intent)
    assert verdict.synthetic_checksum_consistent
    assert verdict.request_matches
    assert verdict.decision == "DENY"
    assert not verdict.external_evidence_authenticated
    assert not verdict.verified_execution


def test_frozen_receipt_cannot_grant_authority_in_place():
    receipt = preview(demo())
    with pytest.raises(FrozenInstanceError):
        receipt.execution_authorized = True


def test_analytics_two_ops_only_observes_synthetic_denials():
    tenant = uuid4()
    a = demo(tenant=tenant, request_id="DEMO-REQ-ANALYTICS-1")
    b = demo(tenant=tenant, request_id="DEMO-REQ-ANALYTICS-2",
             operation="business.finance.reconciliation-proposal.v1")
    gate = OfflineCapabilityPreview()
    report = aggregate_synthetic_denials(
        tenant, ((a, gate.inspect_once(a)), (b, gate.inspect_once(b))),
    )
    assert report.synthetic_events == report.denied_events == 2
    assert sum(count for _, count in report.operation_counts) == 2
    assert report.reason_counts
    assert report.decision == "DENY"
    assert not report.business_value_measured
    assert not report.production_telemetry_verified
    assert not report.real_revenue_measured
    assert not report.provider_reads_performed
    assert not report.customer_data_processed


def test_analytics_empty_is_explicitly_unmeasured():
    report = aggregate_synthetic_denials(uuid4(), ())
    assert report.synthetic_events == 0
    assert not report.operation_counts
    assert not report.business_value_measured


def test_analytics_rejects_cross_tenant_and_repeated_request():
    t, foreign = uuid4(), uuid4()
    intent = demo(tenant=t)
    receipt = preview(intent)
    with pytest.raises(ReceiptRejected):
        aggregate_synthetic_denials(foreign, ((intent, receipt),))
    with pytest.raises(ReceiptRejected):
        aggregate_synthetic_denials(t, ((intent, receipt), (intent, receipt)))


@pytest.mark.parametrize("mutation", [
    lambda r: replace(r, decision="ALLOW"),
    lambda r: replace(r, tenant_id=uuid4()),
    lambda r: replace(r, checksum="9"*64),
])
def test_analytics_rejects_false_proof(mutation):
    intent = demo()
    receipt = mutation(preview(intent))
    with pytest.raises(ReceiptRejected):
        aggregate_synthetic_denials(intent.tenant_id, ((intent, receipt),))


def test_analytics_rejects_malformed_inputs():
    t = uuid4()
    for records in ([], None, tuple((1,) for _ in range(1)),
                    tuple((demo(tenant=t), None) for _ in range(1)),
                    tuple((demo(tenant=t), preview(demo(tenant=t)))
                          for _ in range(1))):
        with pytest.raises((ReceiptRejected, CapabilityDenied)):
            aggregate_synthetic_denials(t, records)


def test_analytics_capacity_fails_closed():
    with pytest.raises(ReceiptRejected):
        aggregate_synthetic_denials(uuid4(), tuple((None, None) for _ in range(MAX_ANALYTICS_EVENTS+1)))


@pytest.mark.parametrize("field,fake", [
    ("mode", "PRODUCTION_EXECUTION"),
    ("default_policy", "ALLOW"),
    ("release_status", "GO"),
    ("foundation_gates_verified", 9),
    ("foundation_gates_verified", True),
    ("phase02_operational_accepted", True),
    ("live_execution_authorized", True),
    ("external_data_access", True),
    ("developer_interface", "PUBLIC_HTTP"),
    ("verification_scope", "REAL_PROVIDER"),
    ("analytics_scope", "CUSTOMER_REVENUE"),
])
def test_manifest_rejects_self_authorization(field, fake):
    manifest, source = source_manifests()
    manifest[field] = fake
    with pytest.raises(ContractRejected):
        validate_phase03_manifest(manifest, source)


@pytest.mark.parametrize("change", [
    lambda row: row.update(execution_enabled=True),
    lambda row: row.update(provider_bound=True),
    lambda row: row.update(autonomous_execution_enabled=True),
    lambda row: row.update(lifecycle="active"),
    lambda row: row.update(capability_id="BIZ-999"),
    lambda row: row.update(approval_required="false"),
    lambda row: row.update(required_scope="finance.all"),
    lambda row: row.update(production_endpoint="https://example.com"),
])
def test_manifest_rejects_executable_or_unknown_capability_fields(change):
    manifest, source = source_manifests()
    changed = deepcopy(manifest)
    change(changed["operations"][0])
    with pytest.raises(ContractRejected):
        validate_phase03_manifest(changed, source)


def test_manifest_rejects_unknown_duplicate_and_missing_capabilities():
    manifest, source = source_manifests()
    for mutation in ("duplicate", "missing", "unknown"):
        x = deepcopy(manifest)
        if mutation == "duplicate":
            x["operations"][1] = x["operations"][0].copy()
        if mutation == "missing":
            x["operations"].pop()
        if mutation == "unknown":
            x["operations"][0]["operation_id"] = "business.unknown.v1"
        with pytest.raises(ContractRejected):
            validate_phase03_manifest(x, source)


def test_manifest_rejects_reopened_phase02_authority():
    manifest, source = source_manifests()
    source["external_access"] = True
    with pytest.raises(ContractRejected):
        validate_phase03_manifest(manifest, source)


@pytest.mark.parametrize("command", [
    ["catalog"],
    ["preview", "business.inventory.stock-preview.v1"],
    ["preview", "business.finance.reconciliation-proposal.v1"],
    ["demo-analytics"],
])
def test_cli_only_produces_offline_data(command):
    p = subprocess.run([sys.executable, str(CLI), *command],
                       capture_output=True, text=True, timeout=10, check=False)
    assert p.returncode == 0, p.stderr
    value = json.loads(p.stdout)
    assert value["decision"] == "DENY"
    if command[0] == "catalog":
        assert value["execution_available"] is False
        assert value["operation_count"] == 4
    elif command[0] == "preview":
        assert value["execution_authorized"] is False
        assert value["execution_performed"] is False
        assert value["provider_called"] is False
    else:
        assert value["synthetic_events"] == 2
        assert value["business_value_measured"] is False


@pytest.mark.parametrize("command", [
    ["preview", "business.unknown.v1"],
    ["preview", "business.inventory.stock-preview.v1", "--request-id", "REAL"],
    ["preview", "business.inventory.stock-preview.v1", "--execute"],
    ["deploy"],
])
def test_cli_rejects_unknown_or_live_controls(command):
    p = subprocess.run([sys.executable, str(CLI), *command],
                       capture_output=True, text=True, timeout=10, check=False)
    assert p.returncode != 0
    assert not p.stdout


def test_phase03_source_remains_unrouted_and_offline():
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_intelligent_ecosystem" not in main
    code = (ROOT / "apps/api/app/phase03_intelligent_ecosystem.py").read_text()
    for forbidden in (
        "APIRouter(", "httpx", "requests.", "socket.socket(",
        "subprocess.", "psycopg", "urllib.request", "urlopen(",
        "redis.", "google.generativeai", "openai.",
    ):
        assert forbidden not in code
