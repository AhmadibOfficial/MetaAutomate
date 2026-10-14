"""P2-07: actual cross-PR offline source coexistence and DEMO workflow checks.

This suite imports the original pinned module snapshots copied from draft PRs
#32-#39 into one isolated branch. This is neither a real adapter nor a merge.
The 'joined' paths are manual test orchestration and never authorize execution.
"""
from dataclasses import replace
from hashlib import sha1
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.synthetic_delivery import (
    SyntheticDeliveryRehearsal, SimulationNotFound, SIM_COMPLETED,
    verify_receipt_chain,
)
from app.synthetic_webhook_proof import (
    DemoWebhookDenied, OfflineSyntheticWebhookVerifier,
    SCHEMA, EVENT_TYPE, sign_synthetic_fixture, synthetic_tenant_marker,
)
from app.synthetic_incident_observability import (
    SyntheticObservation, analyze_synthetic_incidents,
)
from app.synthetic_delivery_resilience import (
    OfflineSyntheticResilience, SyntheticTicketNotFound, SUCCEED,
)
from app.synthetic_write_proposals import (
    OfflineSyntheticWriteProposals, SyntheticProposalNotFound,
)
from app.synthetic_approval_preflight import (
    OfflineSyntheticPreflightRegistry, SyntheticApprovalClaims,
    SyntheticPreflightDenied, SyntheticPreflightRequest,
)
from app.phase02_approval_evidence import (
    DemoNotFound, OfflineApprovalEvidence,
)
from app.phase02_receipt_simulation import (
    OfflineReceiptReplayRegistry, make_demo_receipt,
)
from app.phase02_pilot_simulation import (
    DemoPilotMetrics, evaluate_demo_pilot, synthetic_stock_preview,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts/engineering/p2_full_offline_integration_lock.json"
CRM = "business.crm.sync-proposal.v1"
FIN = "business.finance.reconciliation-proposal.v1"
DEMO_KEY = b"DEMO-KEY-MATERIAL-CROSS-PR-SOURCE-TEST-ONLY-001"


def test_exact_source_blobs_are_unchanged_and_no_release_claims():
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["phase"] == "02"
    assert data["default_decision"] == "DENY"
    assert data["foundation_gates_verified"] == 3
    assert data["foundation_gates_required"] == 9
    assert data["execution_authorized"] is False
    assert data["merging_permitted"] is False
    assert data["automatic_deployment"] is False
    assert data["production_ready"] is False
    assert data["requires_independent_review"] is True
    assert data["base_main_sha"] == "7144451b0ac37349c3e731bac76d14338280c42e"
    assert set(data["locked_head_shas"]) == {str(i) for i in range(32, 40)}
    files = data["source_files"]
    assert len(files) == 31
    assert {item["pr"] for item in files} == set(range(32, 40))
    assert len({item["path"] for item in files}) == len(files)
    for item in files:
        assert set(item) == {"pr", "path", "blob_sha"}
        assert type(item["pr"]) is int
        assert type(item["path"]) is str
        assert type(item["blob_sha"]) is str
        assert len(item["blob_sha"]) == 40
        path = ROOT / item["path"]
        assert path.resolve().is_relative_to(ROOT.resolve())
        blob = path.read_bytes()
        # Git SHA1 blob digest: verify exact source/test/docs bytes from PR head.
        digest = sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest()
        assert digest == item["blob_sha"], item["path"]
    assert not any(x["path"] == "apps/api/app/main.py" for x in files)


def test_joint_p2_04_resilience_delivery_webhook_and_incident_source_only():
    tenant = uuid4()
    resilience = OfflineSyntheticResilience()
    delivery = SyntheticDeliveryRehearsal()
    reservation = resilience.propose(tenant, "DEMO-REQ-INTEGRATION", tick=100)
    assert reservation.admitted
    assert reservation.ticket_id is not None
    assert reservation.provider_operation_performed is False

    # Manually combine two independent simulations: NEVER a queued worker.
    job = delivery.submit(
        tenant, "DEMO-KEY-INTEGRATION",
        "DEMO-INVENTORY-LOW-STOCK", tick=100,
    )
    assert job.execution_available is False
    assert verify_receipt_chain(job)

    # A signed DEMO message only proves consistency of invented fixture bytes.
    key_id = "DEMO-KID-PRIMARY"
    webhook = OfflineSyntheticWebhookVerifier({(tenant, key_id): DEMO_KEY})
    payload = {
        "schema": SCHEMA, "event_id": "DEMO-EVT-INTEGRATION",
        "tenant_marker": synthetic_tenant_marker(tenant),
        "event_type": EVENT_TYPE,
        "scenario": "DEMO-INVENTORY-LOW-STOCK",
        "issued_tick": 100,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = sign_synthetic_fixture(tenant, key_id, DEMO_KEY, raw)
    proof = webhook.verify_once(tenant, key_id, raw, signature, now_tick=101)
    assert proof.accepted_for_simulation
    assert not proof.executed and not proof.webhook_endpoint_available
    with pytest.raises(DemoWebhookDenied):
        webhook.verify_once(tenant, key_id, raw, signature, now_tick=101)

    # No verifier invokes delivery. The test explicitly simulates next state.
    completed = delivery.simulate_outcome(
        tenant, job.job_id, "DEMO-EVT-INTEGRATION",
        "SIM_SUCCESS", tick=100,
    )
    assert completed.state == SIM_COMPLETED
    assert completed.external_request_performed is False
    assert verify_receipt_chain(completed)
    result = resilience.simulate_result(
        tenant, reservation.ticket_id, SUCCEED, tick=100,
    )
    assert not result.real_delivery_performed

    incident = analyze_synthetic_incidents(tenant, [
        SyntheticObservation(
            tenant, "DEMO-JOB-INTEGRATION", "DEMO-EVT-INTEGRATION-Q",
            "SIM_QUEUED", 100, 0,
        ),
        SyntheticObservation(
            tenant, "DEMO-JOB-INTEGRATION", "DEMO-EVT-INTEGRATION-C",
            "SIM_COMPLETED", 100, 1,
        ),
    ], now_tick=101)
    assert incident.completed_count == 1
    assert incident.executed is False
    assert incident.provider_receipts_verified is False
    assert incident.actual_business_data is False


def test_cross_tenant_denial_through_distinct_delivery_security_modules():
    tenant, other = uuid4(), uuid4()
    delivery = SyntheticDeliveryRehearsal()
    resilience = OfflineSyntheticResilience()
    job = delivery.submit(tenant, "DEMO-KEY-TENANT", "DEMO-INVENTORY-LOW-STOCK")
    ticket = resilience.propose(tenant, "DEMO-REQ-TENANT", tick=0)
    with pytest.raises(SimulationNotFound):
        delivery.inspect(other, job.job_id)
    with pytest.raises(SyntheticTicketNotFound):
        resilience.inspect(other, ticket.ticket_id)
    body = json.dumps({
        "schema": SCHEMA, "event_id": "DEMO-EVT-TENANT",
        "tenant_marker": synthetic_tenant_marker(tenant),
        "event_type": EVENT_TYPE, "scenario": "DEMO-INVENTORY-LOW-STOCK",
        "issued_tick": 10,
    }, sort_keys=True, separators=(",", ":")).encode()
    verifier = OfflineSyntheticWebhookVerifier({
        (tenant, "DEMO-KID-MAIN"): DEMO_KEY
    })
    sig = sign_synthetic_fixture(tenant, "DEMO-KID-MAIN", DEMO_KEY, body)
    with pytest.raises(DemoWebhookDenied):
        verifier.verify_once(other, "DEMO-KID-MAIN", body, sig, now_tick=11)
    assert delivery.inspect(tenant, job.job_id).execution_available is False


@pytest.mark.parametrize("operation,scenario,reviewers", [
    (CRM, "DEMO-CRM-LEAD-ALPHA", ("DEMO-ACTOR-REVIEWER",)),
    (FIN, "DEMO-FINANCE-INVOICE-MATCH",
     ("DEMO-ACTOR-REVIEWER", "DEMO-ACTOR-AUDITOR")),
])
def test_joined_p2_05_write_evidence_preflight_receipt_and_pilot_still_deny(
    operation, scenario, reviewers,
):
    tenant = uuid4()
    proposer = "DEMO-ACTOR-FOUNDER"
    proposals = OfflineSyntheticWriteProposals()
    audit = OfflineApprovalEvidence()

    first = proposals.propose(
        tenant, operation, scenario, proposer, "DEMO-IDEMP-JOINED", tick=100,
    )
    parallel = audit.propose(
        tenant_id=tenant, proposal_id=first.proposal_id,
        operation_id=operation, scenario=scenario, proposer=proposer,
        request_key="DEMO-IDEMP-JOINED", tick=100,
    )
    assert parallel.proposal_id == first.proposal_id
    assert first.execution_authorized is False and parallel.decision == "DENY"

    current = first
    history = parallel
    for version, reviewer in enumerate(reviewers):
        current = proposals.review(
            tenant, first.proposal_id, reviewer, "SIM_ENDORSE",
            tick=101 + version, expected_version=version,
        )
        history = audit.review(
            tenant_id=tenant, proposal_id=first.proposal_id,
            reviewer=reviewer, vote="SIM_ENDORSE",
            expected_revision=version, tick=101 + version,
        )
    assert current.status == "SIM_REVIEWED_NOT_AUTHORIZED"
    assert history.status == "SIM_REVIEWED_NOT_AUTHORIZED"
    assert audit.verify_demo_audit_chain(tenant_id=tenant)

    request = SyntheticPreflightRequest(
        tenant_id=tenant, proposal_id=first.proposal_id,
        request_id="DEMO-PREFLIGHT-JOINED",
        operation_id=operation, scenario=scenario,
        proposer_label=proposer, reviewer_labels=reviewers,
        proposal_version=len(reviewers), created_tick=100, now_tick=110,
        claims=SyntheticApprovalClaims(True, True, True, True),
    )
    preflights = OfflineSyntheticPreflightRegistry()
    denial = preflights.inspect_once(request)
    assert denial.demo_checks_complete
    assert denial.decision == "DENY"
    assert denial.execution_authorized is False
    assert not denial.human_approval_verified
    assert not denial.real_scope_issued
    assert preflights.inspect_once(request) == denial
    with pytest.raises(SyntheticPreflightDenied):
        preflights.inspect_once(replace(
            request, now_tick=111
        ))

    fake_receipt = make_demo_receipt(
        history, "DEMO-RECEIPT-JOINED",
        "SIM_PROVIDER_REPORTS_MATCH",
    )
    receipts = OfflineReceiptReplayRegistry()
    checked = receipts.inspect_once(
        tenant_id=tenant, proposal=history, receipt=fake_receipt,
    )
    assert checked.synthetic_consistency
    assert checked.decision == "DENY"
    assert checked.executed is False
    assert checked.authoritative_receipt_verified is False
    assert checked.independent_provider_query_performed is False

    pilot = evaluate_demo_pilot(
        DemoPilotMetrics(tenant, 10, 10, 2, 1000, 999),
        alleged_approval_from_input=True,
    )
    assert pilot.decision == "DENY"
    assert pilot.production_ready is False
    assert pilot.real_customer_onboarded is False
    stock = synthetic_stock_preview(
        demo_tenant=tenant, sku="DEMO-SKU-MAIZE",
    )
    assert stock.provider_called is False and not stock.data_accessed

    with pytest.raises(SyntheticProposalNotFound):
        proposals.inspect(uuid4(), first.proposal_id)
    with pytest.raises(DemoNotFound):
        audit.inspect(tenant_id=uuid4(), proposal_id=first.proposal_id)


def test_all_synthetic_sources_remain_unrouted_and_company_denial_is_consistent():
    main = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
    source_names = [
        "synthetic_delivery", "synthetic_webhook_proof",
        "synthetic_incident_observability", "synthetic_delivery_resilience",
        "synthetic_write_proposals", "synthetic_approval_preflight",
        "phase02_approval_evidence", "phase02_pilot_simulation",
        "phase02_receipt_simulation",
    ]
    for module in source_names:
        assert module not in main, module
    runtime_contract = json.loads(
        (ROOT / "contracts/domains/v1/operations.json").read_text()
    )
    assert runtime_contract["lifecycle"] == "draft"
    assert runtime_contract["adapter_state"] == "unbound"
    assert runtime_contract["external_access"] is False
    assert runtime_contract["default_policy"] == "DENY"
