"""P3-03: synthetic negative-control security tests; NEVER real provider verification."""
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
from app.phase03_outcome_verification import (
    EVIDENCE_SCHEMA, MAX_EVENTS, MAX_PER_TENANT, MAX_TENANTS,
    DemoEvidenceRejected, DemoEvidenceNotFound,
    OfflineEvidenceRegistry, make_demo_no_dispatch,
    make_demo_readback, verify_demo_negative_outcome,
    _hash_payload, _event_material, _read_material,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/phase03_offline_cli.py"
MANIFEST = ROOT / "contracts/intelligent/v1/outcome_verification.json"
SCENE = {
    "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
    "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
    "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
    "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
}


def fixture(operation="business.inventory.stock-preview.v1", *,
            tenant=None, request_id="DEMO-REQ-VERIFY-001",
            expected_version=1, event_id="DEMO-EVENT-NO-DISPATCH-001",
            tick=100, observed_tick=101, observed_version=None):
    tenant = uuid4() if tenant is None else tenant
    intent = DemoCapabilityIntent(
        tenant_id=tenant,
        actor_label="DEMO-ACTOR-VERIFIER",
        request_id=request_id,
        operation_id=operation,
        scenario=SCENE[operation],
        logical_tick=tick,
    )
    denied = OfflineCapabilityPreview().inspect_once(intent)
    request = DemoPlanningRequest(
        intent=intent,
        denial_receipt=denied,
        target_label=TARGETS[operation],
        expected_resource_version=expected_version,
        requested_tick=tick,
    )
    plan = create_denied_plan(request)
    event = make_demo_no_dispatch(
        plan, request, event_id=event_id, observed_tick=observed_tick,
    )
    snapshot = make_demo_readback(
        plan, request, observed_tick=observed_tick,
        observed_version=observed_version,
    )
    return plan, request, event, snapshot


def evaluate(plan, request, event, snapshot, observed_tick=102):
    return verify_demo_negative_outcome(
        plan, request, event, snapshot, observed_tick=observed_tick,
    )


@pytest.mark.parametrize("op", tuple(OPERATION_SPECS))
def test_all_four_operations_have_consistent_negative_controls_only(op):
    p, req, event, read = fixture(op)
    verdict = evaluate(p, req, event, read)
    assert verdict.demo_evidence_consistent
    assert verdict.demo_state_unchanged
    assert verdict.plan_within_demo_expiry
    assert verdict.finding == "DEMO_NO_DISPATCH_CONSISTENT_NOT_EXTERNAL_VERIFICATION"
    assert verdict.decision == "DENY"
    assert verdict.operation_id == op
    assert verdict.request_id == req.intent.request_id
    assert not verdict.execution_verified
    assert not verdict.independently_observed_real_outcome
    assert not verdict.authoritative_provider_receipt_verified
    assert not verdict.provider_readback_performed
    assert not verdict.customer_data_processed
    assert not verdict.external_authorization_verified
    assert not verdict.release_authorized
    assert event.schema == EVIDENCE_SCHEMA
    assert not event.dispatch_performed
    assert not read.provider_read_performed
    assert not read.externally_authenticated


def test_changed_fake_readback_is_a_negative_finding_not_success():
    p, req, event, read = fixture(observed_version=2)
    v = evaluate(p, req, event, read)
    assert v.demo_evidence_consistent
    assert not v.demo_state_unchanged
    assert "demo_resource_version_changed" in v.reasons
    assert v.finding == "DEMO_NEGATIVE_CONTROL_UNVERIFIED"
    assert v.decision == "DENY"


def test_expired_demo_plan_still_never_grants_execution():
    p, req, event, read = fixture()
    v = evaluate(p, req, event, read, observed_tick=111)
    assert not v.plan_within_demo_expiry
    assert "demo_plan_expired" in v.reasons
    assert not v.execution_verified
    assert v.decision == "DENY"


@pytest.mark.parametrize("changes", [
    {"tenant_id": uuid4()},
    {"request_id": "DEMO-REQ-INTRUDER"},
    {"operation_id": "business.crm.sync-proposal.v1"},
    {"target": "DEMO-TARGET-INTRUDER"},
    {"plan_checksum": "0"*64},
    {"event_id": "REAL-EVENT-ABC"},
    {"observed_tick": 2},
    {"kind": "SIM_PROVIDER_SUCCESS"},
    {"schema": "provider.v1"},
    {"dispatch_performed": True},
    {"provider_called": True},
    {"authoritative_receipt": True},
    {"digest": "a"*64},
])
def test_tampered_dispatch_evidence_rejected(changes):
    p, req, event, view = fixture()
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p, req, replace(event, **changes), view)


@pytest.mark.parametrize("changes", [
    {"tenant_id": uuid4()},
    {"request_id": "DEMO-REQ-FOREIGN"},
    {"operation_id": "business.crm.sync-proposal.v1"},
    {"target": "DEMO-TARGET-OTHER"},
    {"plan_checksum": "0"*64},
    {"claimed_source": "LIVE-REAL-PROVIDER"},
    {"expected_version": 3},
    {"observed_version": True},
    {"observed_tick": 2},
    {"kind": "REAL_READBACK"},
    {"provider_read_performed": True},
    {"externally_authenticated": True},
    {"real_customer_data_accessed": True},
    {"digest": "a"*64},
])
def test_fake_provider_or_cross_tenant_snapshot_rejected(changes):
    p, req, event, view = fixture()
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p, req, event, replace(view, **changes))


def test_recomputed_digest_cannot_make_real_receipt_trusted():
    p, req, event, view = fixture()
    forged = replace(event, provider_called=True, digest="")
    forged = replace(forged, digest=_hash_payload(_event_material(forged)))
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p, req, forged, view)
    forged_view = replace(view, externally_authenticated=True, digest="")
    forged_view = replace(
        forged_view, digest=_hash_payload(_read_material(forged_view)),
    )
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p, req, event, forged_view)


def test_plan_mismatch_rejected_not_silently_transplanted():
    p, req, ev, view = fixture()
    p2, req2, _, _ = fixture(tenant=uuid4())
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p2, req2, ev, view)
    with pytest.raises(DemoEvidenceRejected):
        evaluate(replace(p, execution_authorized=True), req, ev, view)


@pytest.mark.parametrize("invalid", [
    "REAL-EVENT-001", "DEMO-EVENT-", "", None, True, 5, "DEMO-EVENT-HELLO\n",
])
def test_event_identifier_must_be_invented_only(invalid):
    p, req, _, _ = fixture()
    with pytest.raises(DemoEvidenceRejected):
        make_demo_no_dispatch(p, req, event_id=invalid, observed_tick=101)


@pytest.mark.parametrize("bad", [True, "1", -1, 1001, 1.4])
def test_invalid_fake_readback_versions_denied(bad):
    p, req, _, _ = fixture()
    with pytest.raises(DemoEvidenceRejected):
        make_demo_readback(
            p, req, observed_tick=101, observed_version=bad,
        )


@pytest.mark.parametrize("bad", [None, "101", True, -1, 1_000_001])
def test_invalid_utc_free_demo_tick_rejected(bad):
    p, req, ev, view = fixture()
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p, req, ev, view, observed_tick=bad)


def test_future_dated_evidence_rejected():
    p, req, ev, view = fixture(observed_tick=108)
    with pytest.raises(DemoEvidenceRejected):
        evaluate(p, req, ev, view, observed_tick=102)


def test_registry_deduplicates_same_demo_event_and_denies_conflict():
    p, req, ev, view = fixture()
    store = OfflineEvidenceRegistry()
    a = store.record_once(
        plan=p, request=req, no_dispatch=ev, readback=view, observed_tick=102,
    )
    b = store.record_once(
        plan=p, request=req, no_dispatch=ev, readback=view, observed_tick=102,
    )
    assert a == b
    assert len(store._events) == 1
    with pytest.raises(DemoEvidenceRejected):
        store.record_once(
            plan=p, request=req, no_dispatch=ev,
            readback=replace(view, observed_version=2),
            observed_tick=102,
        )
    assert len(store._events) == 1


def test_registry_foreign_tenant_looks_identical_to_absent_data():
    p, req, ev, view = fixture()
    store = OfflineEvidenceRegistry()
    store.record_once(
        plan=p, request=req, no_dispatch=ev, readback=view, observed_tick=102,
    )
    with pytest.raises(DemoEvidenceNotFound):
        store.inspect(tenant_id=uuid4(), event_id=ev.event_id)
    assert store.inspect(
        tenant_id=p.tenant_id, event_id=ev.event_id,
    ).decision == "DENY"


def test_registry_same_event_id_in_distinct_demo_tenants_is_separate():
    store = OfflineEvidenceRegistry()
    for _ in range(2):
        p, req, ev, view = fixture()
        store.record_once(
            plan=p, request=req, no_dispatch=ev, readback=view,
            observed_tick=102,
        )
    assert len(store._events) == 2


def test_bounded_registry_capacity_and_no_eviction():
    store = OfflineEvidenceRegistry()
    t = uuid4()
    for i in range(MAX_PER_TENANT):
        p, req, ev, view = fixture(
            tenant=t, event_id=f"DEMO-EVENT-CAPACITY-{i:03}",
            request_id=f"DEMO-REQ-CAPACITY-{i:03}",
        )
        store.record_once(
            plan=p, request=req, no_dispatch=ev,
            readback=view, observed_tick=102,
        )
    assert len(store._events) == MAX_PER_TENANT
    p, req, ev, view = fixture(
        tenant=t, event_id="DEMO-EVENT-OVERFLOW",
        request_id="DEMO-REQ-OVERFLOW",
    )
    with pytest.raises(DemoEvidenceRejected):
        store.record_once(
            plan=p, request=req, no_dispatch=ev,
            readback=view, observed_tick=102,
        )


def test_global_registry_capacity():
    store = OfflineEvidenceRegistry()
    for i in range(MAX_EVENTS):
        t = UUID(int=1 + i // MAX_PER_TENANT)
        p, req, ev, view = fixture(
            tenant=t, event_id=f"DEMO-EVENT-FULL-{i:03}",
            request_id=f"DEMO-REQ-FULL-{i:03}",
        )
        store.record_once(
            plan=p, request=req, no_dispatch=ev, readback=view, observed_tick=102,
        )
    assert len(store._events) == MAX_EVENTS
    p, req, ev, view = fixture(
        tenant=uuid4(), event_id="DEMO-EVENT-OVERFLOW",
        request_id="DEMO-REQ-OVERFLOW",
    )
    with pytest.raises(DemoEvidenceRejected):
        store.record_once(
            plan=p, request=req, no_dispatch=ev, readback=view, observed_tick=102,
        )


def test_concurrent_same_event_never_multiplies_audit_items():
    p, req, ev, view = fixture()
    registry = OfflineEvidenceRegistry()
    def record(_):
        return registry.record_once(
            plan=p, request=req, no_dispatch=ev,
            readback=view, observed_tick=102,
        )
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(record, range(25)))
    assert len(registry._events) == 1
    assert all(x == results[0] for x in results)
    assert results[0].decision == "DENY"


def test_immutable_negative_evidence_model():
    p, req, ev, view = fixture()
    with pytest.raises(FrozenInstanceError):
        ev.provider_called = True
    with pytest.raises(FrozenInstanceError):
        view.externally_authenticated = True


def test_manifest_remains_no_go_and_distinguishes_demo_from_external():
    m = json.loads(MANIFEST.read_text())
    assert m["milestone"] == "P3-03"
    assert m["mode"] == "OFFLINE_NEGATIVE_CONTROL_ONLY"
    assert m["release_decision"] == "NO_GO"
    assert m["external_receipt_trust_available"] is False
    assert m["live_provider_readback_enabled"] is False
    assert m["verified_customer_outcomes_available"] is False
    assert m["external_execution_authorized"] is False
    assert m["phase01_foundation_verified"] == 3
    assert m["phase02_operational_go"] is False


@pytest.mark.parametrize("operation", tuple(OPERATION_SPECS))
def test_developer_cli_verifies_only_mock_non_dispatch(operation):
    proc = subprocess.run(
        [sys.executable, str(CLI), "verify-denial", operation],
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["demo_evidence_consistent"]
    assert payload["demo_state_unchanged"]
    assert payload["decision"] == "DENY"
    assert payload["evidence_scope"] == "INVENTED_UNTRUSTED_FIXTURES_ONLY"
    assert not payload["execution_verified"]
    assert not payload["independently_observed_real_outcome"]
    assert not payload["provider_readback_performed"]
    assert not payload["external_authorization_verified"]


def test_cli_changed_state_shows_negative_finding():
    p = subprocess.run(
        [sys.executable, str(CLI), "verify-denial",
         "business.inventory.stock-preview.v1",
         "--simulated-observed-version", "2"],
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert p.returncode == 0, p.stderr
    j = json.loads(p.stdout)
    assert not j["demo_state_unchanged"]
    assert j["finding"] == "DEMO_NEGATIVE_CONTROL_UNVERIFIED"
    assert j["decision"] == "DENY"


@pytest.mark.parametrize("args", [
    ["verify-denial", "business.inventory.stock-preview.v1",
     "--simulated-observed-version", "-1"],
    ["verify-denial", "business.inventory.stock-preview.v1",
     "--simulated-observed-version", "1001"],
    ["verify-denial", "business.inventory.stock-preview.v1",
     "--request-id", "REAL-CUSTOMER"],
    ["verify-denial", "business.inventory.stock-preview.v1", "--execute"],
    ["verify-denial", "business.unknown.v1"],
])
def test_cli_rejects_realistic_or_invalid_controls(args):
    p = subprocess.run(
        [sys.executable, str(CLI), *args], capture_output=True,
        text=True, check=False, timeout=15,
    )
    assert p.returncode != 0
    assert not p.stdout


def test_module_never_routes_networks_or_creates_external_verification():
    src = (ROOT / "apps/api/app/phase03_outcome_verification.py").read_text()
    app = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_outcome_verification" not in app
    for forbidden in (
        "APIRouter(", "httpx", "requests.", "urllib.request", "urlopen(",
        "socket.socket(", "psycopg", "redis.", "subprocess.", "openai.",
    ):
        assert forbidden not in src
