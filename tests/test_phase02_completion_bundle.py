"""P2-05c-f/P2-06 source-only completion candidate regression suite."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.phase02_approval_evidence import (
    DemoApprovalView, DemoDenied, DemoNotFound, OfflineApprovalEvidence,
    WRITE_SPECS, REVIEWED, DECLINED, PENDING, TTL,
)
from app.phase02_receipt_simulation import (
    DemoProviderReceipt, OfflineReceiptReplayRegistry,
    inspect_demo_receipt, make_demo_receipt, MAX_RECEIPTS,
)
from app.phase02_pilot_simulation import (
    DemoPilotMetrics, GATES, OfflineSupportDesk,
    PilotDenied, PilotNotFound, evaluate_demo_pilot, synthetic_stock_preview,
)

ROOT = Path(__file__).resolve().parents[1]
CRM = "business.crm.sync-proposal.v1"
FIN = "business.finance.reconciliation-proposal.v1"
A = "DEMO-ACTOR-FOUNDER"
B = "DEMO-ACTOR-REVIEWER"
C = "DEMO-ACTOR-ACCOUNTANT"


def record(engine, tenant=None, pid=None, *, op=CRM, scenario=None,
           key="DEMO-IDEMP-ALPHA", actor=A, tick=100):
    tenant = tenant or uuid4()
    pid = pid or uuid4()
    if scenario is None:
        scenario = ("DEMO-CRM-LEAD-ALPHA" if op == CRM
                    else "DEMO-FINANCE-INVOICE-MATCH")
    return engine.propose(
        tenant_id=tenant, proposal_id=pid, operation_id=op,
        scenario=scenario, proposer=actor, request_key=key, tick=tick,
    )


def vote(engine, view, actor=B, choice="SIM_ENDORSE", tick=101, revision=None):
    return engine.review(
        tenant_id=view.tenant_id, proposal_id=view.proposal_id,
        reviewer=actor, vote=choice,
        expected_revision=view.revision if revision is None else revision,
        tick=tick,
    )


def verified_sample():
    engine = OfflineApprovalEvidence()
    pending = record(engine)
    reviewed = vote(engine, pending)
    return engine, pending, reviewed


def test_contract_parity_and_permanent_draft_flag():
    contract = json.loads(
        (ROOT / "contracts/domains/v1/operations.json").read_text()
    )
    assert contract["product"] == "metaautomate"
    assert contract["lifecycle"] == "draft"
    assert contract["default_policy"] == "DENY"
    assert contract["adapter_state"] == "unbound"
    assert contract["external_access"] is False
    write_ops = {item["operation_id"]: item for item in contract["operations"]
                 if item["effect"] == "propose_write"}
    assert set(write_ops) == set(WRITE_SPECS) == {CRM, FIN}
    for name, item in write_ops.items():
        assert WRITE_SPECS[name][:5] == (
            item["capability_id"], item["effect"], item["required_scope"],
            item["risk"], item["approval_required"],
        )


@pytest.mark.parametrize("op,risk,required", [(CRM, "moderate", 1), (FIN, "high", 2)])
def test_proposal_and_review_never_authorize_execution(op, risk, required):
    engine = OfflineApprovalEvidence()
    p = record(engine, op=op)
    assert p.risk == risk and p.status == PENDING and p.revision == 0
    assert p.decision == "DENY" and not p.tenant_authenticated
    assert not p.scope_verified and not p.real_human_approval_verified
    assert not p.executed and not p.provider_called and not p.persisted
    v = vote(engine, p)
    if required == 2:
        assert v.status == PENDING
        v = vote(engine, v, C, tick=102)
    assert v.status == REVIEWED and v.decision == "DENY"
    assert not v.execution_authorized and not v.executed
    assert not v.real_human_approval_verified
    assert engine.verify_demo_audit_chain(tenant_id=p.tenant_id)


def test_commercial_and_real_approval_strings_are_rejected():
    engine = OfflineApprovalEvidence()
    p = record(engine)
    for bogus in ("APPROVED", "ALLOW", "EXECUTE", "approved"):
        with pytest.raises(DemoDenied):
            vote(engine, p, choice=bogus)
    assert engine.inspect(tenant_id=p.tenant_id, proposal_id=p.proposal_id) == p


def test_simulated_decline_is_terminal_and_denied():
    engine = OfflineApprovalEvidence()
    p = record(engine)
    v = vote(engine, p, choice="SIM_DECLINE")
    assert v.status == DECLINED and v.decision == "DENY"
    with pytest.raises(DemoDenied):
        vote(engine, v, C, tick=102)


def test_no_self_review_or_repeat_review():
    engine = OfflineApprovalEvidence()
    p = record(engine, op=FIN)
    with pytest.raises(DemoDenied):
        vote(engine, p, A)
    first = vote(engine, p)
    with pytest.raises(DemoDenied):
        vote(engine, first, B, tick=102)


def test_no_stale_revision_or_decreasing_tick():
    engine = OfflineApprovalEvidence()
    p = record(engine, op=FIN)
    v = vote(engine, p, tick=111)
    with pytest.raises(DemoDenied):
        vote(engine, v, C, tick=110)
    with pytest.raises(DemoDenied):
        vote(engine, v, C, tick=112, revision=0)
    assert engine.inspect(tenant_id=p.tenant_id, proposal_id=p.proposal_id) == v


def test_expiry_boundary_is_fail_closed():
    engine = OfflineApprovalEvidence()
    p = record(engine, tick=10)
    with pytest.raises(DemoDenied):
        vote(engine, p, tick=10 + TTL + 1)
    v = vote(engine, p, tick=10 + TTL)
    assert v.status == REVIEWED and not v.execution_authorized


def test_replay_returns_updated_snapshot_not_duplicate_record():
    engine = OfflineApprovalEvidence()
    p = record(engine)
    assert record(engine, tenant=p.tenant_id, pid=p.proposal_id) == p
    v = vote(engine, p)
    assert record(engine, tenant=p.tenant_id, pid=p.proposal_id, tick=102) == v
    assert len(engine._records) == 1


@pytest.mark.parametrize("override", [
    {"scenario": "DEMO-CRM-LEAD-BETA"},
    {"actor": "DEMO-ACTOR-OTHER"},
    {"op": FIN, "scenario": "DEMO-FINANCE-INVOICE-MATCH"},
    {"pid": UUID(int=99)},
])
def test_conflicting_replay_does_not_write(override):
    engine = OfflineApprovalEvidence()
    p = record(engine)
    with pytest.raises(DemoDenied):
        record(engine, tenant=p.tenant_id, **override)
    assert len(engine._records) == 1


def test_duplicate_proposal_uuid_under_new_key_rejected():
    engine = OfflineApprovalEvidence()
    p = record(engine)
    with pytest.raises(DemoDenied):
        record(engine, tenant=p.tenant_id, pid=p.proposal_id,
               key="DEMO-IDEMP-BETA")


def test_cross_tenant_lookup_denied_with_no_leak():
    engine = OfflineApprovalEvidence()
    p = record(engine)
    with pytest.raises(DemoNotFound):
        engine.inspect(tenant_id=uuid4(), proposal_id=p.proposal_id)
    with pytest.raises(DemoNotFound):
        engine.review(tenant_id=uuid4(), proposal_id=p.proposal_id, reviewer=B,
                      vote="SIM_ENDORSE", expected_revision=0, tick=101)


def test_concurrent_review_compare_and_swap_one_winner():
    engine = OfflineApprovalEvidence()
    p = record(engine, op=FIN)
    def attempt(index):
        try:
            vote(engine, p, actor=f"DEMO-ACTOR-REVIEWER-{index:03}", tick=101)
            return 1
        except DemoDenied:
            return 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, range(36))) == 1
    assert engine.inspect(tenant_id=p.tenant_id, proposal_id=p.proposal_id).revision == 1


def test_concurrent_idempotent_propose_returns_single_record():
    engine = OfflineApprovalEvidence()
    t, pid = uuid4(), uuid4()
    with ThreadPoolExecutor(max_workers=8) as pool:
        views = list(pool.map(lambda _: record(engine, tenant=t, pid=pid), range(32)))
    assert len({v.audit_head for v in views}) == 1
    assert len(engine._audit[t]) == 1


@pytest.mark.parametrize("bad", [
    "DEMO-CRM-LEAD-ALPHA;DELETE", "REAL-CRM-LEAD", None,
    "DEMO-FINANCE-INVOICE-MATCH", {"customer": "private"},
])
def test_unallowlisted_scenario_fails_closed(bad):
    with pytest.raises(DemoDenied):
        record(OfflineApprovalEvidence(), scenario=bad)


@pytest.mark.parametrize("invalid", [
    "owner", "DEMO-ACTOR-", "DEMO-ACTOR-X@EMAIL.COM",
    None, 5,
])
def test_invalid_demo_proposer_fails_closed(invalid):
    with pytest.raises(DemoDenied):
        record(OfflineApprovalEvidence(), actor=invalid)


@pytest.mark.parametrize("tick", [-1, True, 1_000_000, "100", None])
def test_invalid_and_overflow_ticks_fail_closed(tick):
    with pytest.raises(DemoDenied):
        record(OfflineApprovalEvidence(), tick=tick)


def test_audit_tamper_detected_even_if_only_head_or_payload_changes():
    engine, old, current = verified_sample()
    assert engine.verify_demo_audit_chain(tenant_id=old.tenant_id)
    key = (old.tenant_id, old.proposal_id)
    engine._records[key] = replace(current, scenario="DEMO-CRM-LEAD-BETA")
    assert engine.verify_demo_audit_chain(tenant_id=old.tenant_id) is False
    engine._records[key] = current
    assert engine.verify_demo_audit_chain(tenant_id=old.tenant_id)
    engine._audit[old.tenant_id][0] = replace(engine._audit[old.tenant_id][0], kind="FAKE")
    assert not engine.verify_demo_audit_chain(tenant_id=old.tenant_id)


def test_empty_audit_never_counts_as_verified_evidence():
    assert not OfflineApprovalEvidence().verify_demo_audit_chain(tenant_id=uuid4())


def test_frozen_views_deny_mutation():
    _, _, view = verified_sample()
    with pytest.raises(FrozenInstanceError):
        view.execution_authorized = True
    with pytest.raises(FrozenInstanceError):
        view.decision = "ALLOW"


def test_demo_receipt_checksum_consistent_is_not_external_confirmation():
    _, _, view = verified_sample()
    proof = make_demo_receipt(view, "DEMO-RECEIPT-001", "SIM_PROVIDER_REPORTS_MATCH")
    verdict = inspect_demo_receipt(view, proof)
    assert verdict.synthetic_consistency
    assert verdict.decision == "DENY"
    assert not verdict.provider_identity_verified
    assert not verdict.independent_provider_query_performed
    assert not verdict.authoritative_receipt_verified
    assert not verdict.executed
    assert not verdict.execution_authorized


@pytest.mark.parametrize("changed", [
    {"checksum": "0" * 64},
    {"scenario": "DEMO-CRM-LEAD-BETA"},
    {"proposal_revision": 0},
    {"proposal_audit_head": "A" * 64},
    {"proposal_id": UUID(int=77)},
    {"simulated_outcome": "REAL_PAYMENT_SETTLED"},
])
def test_modified_receipt_fails_consistency(changed):
    _, _, view = verified_sample()
    proof = make_demo_receipt(view, "DEMO-RECEIPT-001", "SIM_PROVIDER_REPORTS_MATCH")
    verdict = inspect_demo_receipt(view, replace(proof, **changed))
    assert not verdict.synthetic_consistency
    assert verdict.decision == "DENY"


def test_receipt_made_from_stale_proposal_view_rejected():
    engine, pending, reviewed = verified_sample()
    receipt = make_demo_receipt(reviewed, "DEMO-RECEIPT-001", "SIM_PROVIDER_REPORTS_MATCH")
    assert not inspect_demo_receipt(pending, receipt).synthetic_consistency
    with pytest.raises(DemoDenied):
        make_demo_receipt(pending, "DEMO-RECEIPT-002", "SIM_PROVIDER_REPORTS_MATCH")


def test_receipt_replay_deduplicates_and_rejects_changed_contents():
    _, _, view = verified_sample()
    registry = OfflineReceiptReplayRegistry()
    first = make_demo_receipt(view, "DEMO-RECEIPT-ABC", "SIM_PROVIDER_REPORTS_MATCH")
    assert registry.inspect_once(tenant_id=view.tenant_id, proposal=view,
                                receipt=first).synthetic_consistency
    assert registry.inspect_once(tenant_id=view.tenant_id, proposal=view,
                                receipt=first).synthetic_consistency
    with pytest.raises(DemoDenied):
        registry.inspect_once(
            tenant_id=view.tenant_id, proposal=view,
            receipt=replace(first, checksum="1"*64),
        )
    assert len(registry._observations) == 1
    with pytest.raises(DemoDenied):
        registry.inspect_once(tenant_id=uuid4(), proposal=view, receipt=first)


def test_concurrent_receipt_same_key_consumed_only_once():
    _, _, view = verified_sample()
    registry = OfflineReceiptReplayRegistry()
    receipt = make_demo_receipt(view, "DEMO-RECEIPT-ABC", "SIM_PROVIDER_REPORTS_MATCH")
    with ThreadPoolExecutor(max_workers=8) as pool:
        verdicts = list(pool.map(
            lambda _: registry.inspect_once(
                tenant_id=view.tenant_id, proposal=view, receipt=receipt,
            ), range(32),
        ))
    assert all(v.decision == "DENY" for v in verdicts)
    assert len(registry._observations) == 1


def test_synthetic_inventory_preview_has_no_real_read():
    demo_tenant = uuid4()
    s = synthetic_stock_preview(demo_tenant=demo_tenant, sku="DEMO-SKU-MAIZE")
    assert s.quantity == 120 and not s.provider_called
    assert not s.tenant_authenticated and not s.data_accessed
    with pytest.raises(PilotDenied):
        synthetic_stock_preview(demo_tenant=demo_tenant, sku="LIVE-SKU-001")


def test_pilot_metrics_always_no_go_even_with_forged_approval():
    t = uuid4()
    report = evaluate_demo_pilot(
        DemoPilotMetrics(t, 100, 25, 3, 250000, 45000),
        alleged_approval_from_input=True,
    )
    assert report.synthetic_denial_rate_basis_points == 2500
    assert report.hypothetical_net_value_minor == 205000
    assert report.missing_operational_gates == GATES
    assert report.decision == "DENY" and not report.production_ready
    assert not report.real_customer_onboarded
    assert not report.real_value_proven and not report.billable_cost_verified


@pytest.mark.parametrize("changes", [
    {"observed_requests": -1},
    {"denied_requests": 11},
    {"hypothetical_value_minor": "100"},
    {"hypothetical_cost_minor": True},
    {"observed_requests": 1_000_001},
])
def test_invalid_metrics_fail_closed(changes):
    m = DemoPilotMetrics(uuid4(), 10, 0, 2, 100, 20)
    with pytest.raises(PilotDenied):
        evaluate_demo_pilot(replace(m, **changes))


def test_zero_denominator_is_safe_but_not_production_ready():
    m = DemoPilotMetrics(uuid4(), 0, 0, 0, 0, 0)
    r = evaluate_demo_pilot(m)
    assert r.synthetic_denial_rate_basis_points == 0
    assert r.decision == "DENY"


def test_support_desk_dedup_and_tenant_isolation():
    desk = OfflineSupportDesk()
    t = uuid4()
    args = dict(demo_tenant=t, ticket_id="DEMO-TICKET-001",
                severity="HIGH", category="DEMO-ACCESS", tick=20)
    first = desk.open(**args)
    assert desk.open(**args) == first
    assert not first.notification_sent and not first.real_case
    with pytest.raises(PilotNotFound):
        desk.inspect(demo_tenant=uuid4(), ticket_id="DEMO-TICKET-001")
    with pytest.raises(PilotDenied):
        desk.open(**{**args, "severity": "LOW"})


@pytest.mark.parametrize("ticket,category", [
    ("REAL-CASE-123", "DEMO-ACCESS"),
    ("DEMO-TICKET-001", "CUSTOMER-PAYMENT"),
    ("../DEMO-TICKET-XYZ", "DEMO-DENIAL"),
])
def test_support_desk_rejects_real_ticket_and_categories(ticket, category):
    with pytest.raises(PilotDenied):
        OfflineSupportDesk().open(
            demo_tenant=uuid4(), ticket_id=ticket, severity="HIGH",
            category=category, tick=10,
        )


def test_source_modules_are_unrouted_and_no_external_io():
    main = (ROOT / "apps/api/app/main.py").read_text()
    for module in (
        "phase02_approval_evidence", "phase02_receipt_simulation",
        "phase02_pilot_simulation",
    ):
        assert module not in main
        source = (ROOT / f"apps/api/app/{module}.py").read_text()
        for prohibited in (
            "APIRouter(", "import httpx", "import requests", "import socket",
            "import psycopg", "import subprocess", "import os",
            "redis.", "http://", "https://", "urlopen(",
        ):
            assert prohibited not in source


def test_phase02_closure_manifest_marks_live_gates_unsatisfied():
    data = json.loads(
        (ROOT / "contracts/engineering/phase02_source_closure.json").read_text()
    )
    assert data["phase"] == "02"
    assert data["foundation_gates_verified"] == 3
    assert data["foundation_gates_required"] == 9
    assert data["release_decision"] == "NO_GO"
    assert data["production_execution_authorized"] is False
    assert data["commercial_pilot_authorized"] is False
    assert data["required_controls"]["independent_review"] is False
    assert data["required_controls"]["enforceable_private_branch_protection"] is False
    assert data["required_controls"]["live_staging_identity_and_tenant_security"] is False
    assert data["required_controls"]["real_provider_receipt"] is False
    assert data["prs_parked_unmerged"] == [32, 33, 34, 35, 36, 37, 38]
