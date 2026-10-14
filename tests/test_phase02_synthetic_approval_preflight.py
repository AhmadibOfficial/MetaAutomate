"""P2-05b: deny-only preflight and simulated trust-boundary regression tests."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from uuid import UUID, uuid4
import json

import pytest

from app.synthetic_approval_preflight import (
    MAX_CASES, MAX_CASES_PER_TENANT,
    PERMANENT_GATES, WRITE_CONTRACTS,
    OfflineSyntheticPreflightRegistry, SyntheticApprovalClaims,
    SyntheticPreflightDecision, SyntheticPreflightDenied,
    SyntheticPreflightRequest, evaluate_synthetic_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
CRM = "business.crm.sync-proposal.v1"
FIN = "business.finance.reconciliation-proposal.v1"
A = "DEMO-ACTOR-FOUNDER"
B = "DEMO-ACTOR-MANAGER"
C = "DEMO-ACTOR-FINANCE"


def req(
    tenant=None, *, operation=CRM, scenario=None,
    reviewers=(B,), claims=None, request_id="DEMO-PREFLIGHT-001",
    version=None, created=100, now=101,
):
    if scenario is None:
        scenario = ("DEMO-CRM-LEAD-ALPHA" if operation == CRM
                    else "DEMO-FINANCE-INVOICE-MATCH")
    return SyntheticPreflightRequest(
        tenant_id=tenant or uuid4(), proposal_id=uuid4(),
        request_id=request_id, operation_id=operation, scenario=scenario,
        proposer_label=A, reviewer_labels=reviewers,
        proposal_version=len(reviewers) if version is None else version,
        created_tick=created, now_tick=now,
        claims=claims if claims is not None else SyntheticApprovalClaims(),
    )


def all_demo_flags():
    return SyntheticApprovalClaims(True, True, True, True)


def test_write_contract_parity_without_binding_connector():
    manifest = json.loads((ROOT / "contracts/domains/v1/operations.json").read_text())
    assert manifest["product"] == "metaautomate"
    assert manifest["default_policy"] == "DENY"
    assert manifest["adapter_state"] == "unbound"
    assert manifest["lifecycle"] == "draft"
    assert manifest["external_access"] is False
    write = [x for x in manifest["operations"] if x["effect"] == "propose_write"]
    assert set(WRITE_CONTRACTS) == {x["operation_id"] for x in write}
    for item in write:
        a = WRITE_CONTRACTS[item["operation_id"]]
        assert a[:5] == (
            item["capability_id"], item["effect"], item["required_scope"],
            item["risk"], item["approval_required"]
        )


@pytest.mark.parametrize("operation,capability,risk,reviewers", [
    (CRM, "BIZ-006", "moderate", (B,)),
    (FIN, "BIZ-012", "high", (B, C)),
])
def test_even_all_demo_flags_true_does_not_grant_authority(
    operation, capability, risk, reviewers,
):
    response = evaluate_synthetic_preflight(req(
        operation=operation, reviewers=reviewers, claims=all_demo_flags(),
    ))
    assert response.capability_id == capability
    assert response.risk == risk
    assert response.demo_checks_complete is True
    assert response.decision == "DENY"
    assert response.missing_gates == PERMANENT_GATES
    assert not response.server_identity_verified
    assert not response.real_scope_issued
    assert not response.human_approval_verified
    assert not response.approval_reusable_for_execution
    assert not response.execution_authorized
    assert not response.executed
    assert not response.provider_called
    assert not response.provider_receipt_verified
    assert not response.data_accessed
    assert not response.persisted


def test_default_missing_claims_report_specific_reasons():
    decision = evaluate_synthetic_preflight(req(reviewers=()))
    assert decision.decision == "DENY"
    assert not decision.demo_checks_complete
    assert "synthetic_review_count_incomplete" in decision.missing_gates
    for s in (
        "synthetic_identity_claim_missing", "synthetic_scope_claim_missing",
        "synthetic_provider_claim_missing", "synthetic_version_claim_missing",
    ):
        assert s in decision.missing_gates


def test_high_risk_finance_requires_two_distinct_demo_review_labels():
    incomplete = evaluate_synthetic_preflight(req(
        operation=FIN, reviewers=(B,), claims=all_demo_flags(),
    ))
    assert incomplete.required_demo_review_count == 2
    assert "synthetic_review_count_incomplete" in incomplete.missing_gates
    complete = evaluate_synthetic_preflight(req(
        operation=FIN, reviewers=(B, C), claims=all_demo_flags(),
    ))
    assert complete.demo_checks_complete
    assert complete.execution_authorized is False


def test_synthetic_age_window_is_not_a_trusted_clock():
    boundary = evaluate_synthetic_preflight(req(
        created=100, now=120, claims=all_demo_flags(),
    ))
    assert boundary.demo_checks_complete
    stale = evaluate_synthetic_preflight(req(
        created=100, now=121, claims=all_demo_flags(),
    ))
    assert "synthetic_proposal_expired" in stale.missing_gates
    assert not stale.demo_checks_complete
    assert stale.decision == "DENY"


def test_same_request_id_and_tenant_deduplicates_without_side_effect():
    registry = OfflineSyntheticPreflightRegistry()
    r = req(claims=all_demo_flags())
    first = registry.inspect_once(r)
    assert registry.inspect_once(r) is first
    assert len(registry._by_id) == 1
    assert not first.executed


@pytest.mark.parametrize("field,new", [
    ("operation_id", FIN),
    ("scenario", "DEMO-CRM-LEAD-BETA"),
    ("proposer_label", "DEMO-ACTOR-SUBSTITUTE"),
    ("proposal_version", 0),
    ("reviewer_labels", (C,)),
    ("now_tick", 102),
    ("claims", SyntheticApprovalClaims(True, True, False, True)),
])
def test_replayed_request_with_changed_input_denied(field, new):
    registry = OfflineSyntheticPreflightRegistry()
    request = req()
    registry.inspect_once(request)
    with pytest.raises(SyntheticPreflightDenied):
        registry.inspect_once(replace(request, **{field: new}))
    assert len(registry._by_id) == 1


def test_replay_is_partitioned_only_by_demo_uuid_not_authenticated_identity():
    registry = OfflineSyntheticPreflightRegistry()
    x, y = uuid4(), uuid4()
    first = req(tenant=x)
    second = replace(first, tenant_id=y)
    d1 = registry.inspect_once(first)
    d2 = registry.inspect_once(second)
    assert d1.demo_tenant_marker != d2.demo_tenant_marker
    assert len(registry._by_id) == 2
    assert d1.execution_authorized is False
    assert d2.execution_authorized is False


def test_concurrent_duplicate_preflight_in_memory_is_one_record():
    registry = OfflineSyntheticPreflightRegistry()
    r = req(claims=all_demo_flags())
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: registry.inspect_once(r), range(64)))
    assert len({id(x) for x in results}) == 1
    assert len(registry._by_id) == 1


def test_concurrent_conflicting_preflights_do_not_override_original():
    registry = OfflineSyntheticPreflightRegistry()
    original = req()
    alternative = replace(original, scenario="DEMO-CRM-LEAD-BETA")
    def submit(x):
        try:
            return registry.inspect_once(x)
        except SyntheticPreflightDenied:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        a, b = list(pool.map(submit, [original, alternative]))
    assert (a is None) != (b is None)
    assert len(registry._by_id) == 1


@pytest.mark.parametrize("field,value", [
    ("tenant_id", "fake-tenant"), ("tenant_id", None),
    ("proposal_id", "DEMO-PROPOSAL-123"),
    ("request_id", "REAL-REQUEST-1"),
    ("request_id", "DEMO-PREFLIGHT-"),
    ("request_id", "../DEMO-PREFLIGHT-HELLO"),
    ("operation_id", "business.inventory.stock-preview.v1"),
    ("operation_id", "business.lead-intake.validate.v1"),
    ("operation_id", "business.crm.execute.v1"),
    ("scenario", "ACTUAL-CUSTOMER-DATA"),
    ("scenario", {"account": 400}),
    ("proposer_label", "real-human@example.com"),
    ("proposer_label", None),
    ("reviewer_labels", ["DEMO-ACTOR-MANAGER"]),
    ("reviewer_labels", ("DEMO-ACTOR-MANAGER", "DEMO-ACTOR-MANAGER")),
    ("reviewer_labels", ("DEMO-ACTOR-FOUNDER",)),
    ("reviewer_labels", ("LIVE-USER",)),
    ("proposal_version", True),
    ("proposal_version", -1),
    ("proposal_version", 3),
    ("created_tick", True),
    ("created_tick", -1),
    ("now_tick", "102"),
    ("now_tick", 1_000_001),
    ("claims", {"demo_identity_matches": True}),
])
def test_malformed_fake_authority_and_payload_denied(field, value):
    with pytest.raises(SyntheticPreflightDenied):
        evaluate_synthetic_preflight(replace(req(), **{field: value}))


def test_wrong_scenario_for_operation_and_future_created_tick_denied():
    with pytest.raises(SyntheticPreflightDenied):
        evaluate_synthetic_preflight(req(operation=FIN, scenario="DEMO-CRM-LEAD-ALPHA"))
    with pytest.raises(SyntheticPreflightDenied):
        evaluate_synthetic_preflight(req(created=110, now=100))


def test_non_boolean_fake_evidence_flags_fail_closed():
    claims = SyntheticApprovalClaims(
        demo_identity_matches="true",
        demo_scope_matches=True,
        demo_provider_ready=True,
        demo_proposal_version_matches=True,
    )
    with pytest.raises(SyntheticPreflightDenied):
        evaluate_synthetic_preflight(req(claims=claims))


def test_no_more_reviewers_than_allowlist_count():
    with pytest.raises(SyntheticPreflightDenied):
        evaluate_synthetic_preflight(req(reviewers=(B, C), operation=CRM))


def test_version_must_equal_exact_number_of_reviews_even_when_simulated():
    with pytest.raises(SyntheticPreflightDenied):
        evaluate_synthetic_preflight(req(reviewers=(B,), version=0))


def test_quota_boundaries_fail_closed_no_eviction():
    registry = OfflineSyntheticPreflightRegistry()
    tenant = uuid4()
    first_request = None
    for i in range(MAX_CASES_PER_TENANT):
        current = req(tenant=tenant, request_id=f"DEMO-PREFLIGHT-Q-{i:03}")
        first_request = current if first_request is None else first_request
        registry.inspect_once(current)
    with pytest.raises(SyntheticPreflightDenied):
        registry.inspect_once(req(tenant=tenant, request_id="DEMO-PREFLIGHT-OVER"))
    for group in range(1, 4):
        t = UUID(int=group)
        for i in range(MAX_CASES_PER_TENANT):
            registry.inspect_once(req(
                tenant=t, request_id=f"DEMO-PREFLIGHT-G-{group}-{i:03}",
            ))
    assert len(registry._by_id) == MAX_CASES
    assert registry.inspect_once(first_request).decision == "DENY"
    with pytest.raises(SyntheticPreflightDenied):
        registry.inspect_once(req(request_id="DEMO-PREFLIGHT-TOTAL-OVER"))


def test_tenant_partition_tracking_is_bounded():
    registry = OfflineSyntheticPreflightRegistry()
    for n in range(16):
        registry.inspect_once(req(tenant=UUID(int=n + 1)))
    with pytest.raises(SyntheticPreflightDenied):
        registry.inspect_once(req(tenant=UUID(int=17)))


def test_immutable_result_cannot_be_made_to_claim_execution():
    response = evaluate_synthetic_preflight(req())
    with pytest.raises(FrozenInstanceError):
        response.executed = True
    with pytest.raises(FrozenInstanceError):
        response.decision = "ALLOW"


def test_module_has_no_route_worker_network_or_db_io():
    source = (ROOT / "apps/api/app/synthetic_approval_preflight.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "synthetic_approval_preflight" not in main
    for forbidden in (
        "APIRouter(", "requests.", "httpx.", "socket.", "psycopg",
        "redis.", "subprocess.", "urlopen", "http://", "https://",
        "import os", "open(", "asyncio", "datetime", "time.sleep",
    ):
        assert forbidden not in source
