"""P2-05a: fail-closed DEMO write-proposal regression and source parity."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.synthetic_write_proposals import (
    DECLINE, ENDORSE, PENDING, REJECTED, REVIEWED, MAX_PROPOSALS_TOTAL,
    DEMO_WRITE_CONTRACTS, OfflineSyntheticWriteProposals,
    SyntheticProposalDenied, SyntheticProposalNotFound,
)

ROOT = Path(__file__).resolve().parents[1]
CRM = "business.crm.sync-proposal.v1"
FIN = "business.finance.reconciliation-proposal.v1"
CRM_SCENARIO = "DEMO-CRM-LEAD-ALPHA"
FIN_SCENARIO = "DEMO-FINANCE-INVOICE-MATCH"
AUTHOR = "DEMO-ACTOR-FOUNDER"
REVIEWER_1 = "DEMO-ACTOR-MANAGER"
REVIEWER_2 = "DEMO-ACTOR-CFO"


def submit(
    model, tenant, *, operation=CRM, scenario=CRM_SCENARIO,
    actor=AUTHOR, key="DEMO-IDEMP-PRIMARY", tick=10,
):
    return model.propose(tenant, operation, scenario, actor, key, tick=tick)


def finance(model, tenant, **kwargs):
    return submit(model, tenant, operation=FIN, scenario=FIN_SCENARIO, **kwargs)


def test_exact_source_contract_parity_and_draft_deny_boundary():
    manifest = json.loads((ROOT / "contracts/domains/v1/operations.json").read_text())
    from app.domain_integrations import DOMAIN_OPERATIONS
    assert manifest["operations"] == list(DOMAIN_OPERATIONS)
    assert manifest["default_policy"] == "DENY"
    assert manifest["lifecycle"] == "draft"
    assert manifest["adapter_state"] == "unbound"
    assert manifest["external_access"] is False
    writable = [item for item in manifest["operations"] if item["effect"] == "propose_write"]
    assert len(writable) == len(DEMO_WRITE_CONTRACTS) == 2
    for item in writable:
        capability, effect, scope, risk, approval, reviewer_count, scenarios = (
            DEMO_WRITE_CONTRACTS[item["operation_id"]]
        )
        assert (capability, effect, scope, risk, approval) == (
            item["capability_id"], item["effect"], item["required_scope"],
            item["risk"], item["approval_required"],
        )
        assert reviewer_count in (1, 2)
        assert scenarios and all(s.startswith("DEMO-") for s in scenarios)
    assert DEMO_WRITE_CONTRACTS[CRM][5] == 1
    assert DEMO_WRITE_CONTRACTS[FIN][5] == 2


@pytest.mark.parametrize("operation,scenario,capability,risk,scope", [
    (CRM, CRM_SCENARIO, "BIZ-006", "moderate", "business.crm.write"),
    (FIN, FIN_SCENARIO, "BIZ-012", "high", "business.finance.write"),
])
def test_two_demo_proposal_types_are_deny_only(operation, scenario, capability, risk, scope):
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    result = submit(model, tenant, operation=operation, scenario=scenario)
    assert result.capability_id == capability
    assert result.effect == "propose_write"
    assert result.required_scope == scope
    assert result.risk == risk
    assert result.status == PENDING
    assert result.version == 0
    assert result.simulated_reviews == ()
    assert result.created_tick == 10
    assert result.expires_after_tick == 30
    assert result.decision == "DENY"
    assert result.simulation_only is True
    assert result.tenant_authenticated is False
    assert result.scope_verified is False
    assert result.human_approval_verified is False
    assert result.execution_authorized is False
    assert result.executed is False
    assert result.provider_called is False
    assert result.provider_receipt_verified is False
    assert result.persisted is False


def test_crm_one_demo_endorsement_is_never_real_approval():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposal = submit(model, tenant)
    reviewed = model.review(
        tenant, proposal.proposal_id, REVIEWER_1, ENDORSE,
        tick=11, expected_version=0,
    )
    assert reviewed.version == 1
    assert reviewed.status == REVIEWED
    assert reviewed.simulated_reviews == ((REVIEWER_1, ENDORSE),)
    assert reviewed.decision == "DENY"
    assert not reviewed.execution_authorized
    assert not reviewed.human_approval_verified
    assert not reviewed.executed


def test_finance_requires_two_distinct_simulated_reviewers():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposed = finance(model, tenant)
    first = model.review(tenant, proposed.proposal_id, REVIEWER_1, ENDORSE,
                         tick=12, expected_version=0)
    assert first.status == PENDING
    assert first.version == 1
    second = model.review(tenant, proposed.proposal_id, REVIEWER_2, ENDORSE,
                          tick=13, expected_version=1)
    assert second.status == REVIEWED
    assert second.version == 2
    assert second.simulated_reviews == (
        (REVIEWER_1, ENDORSE), (REVIEWER_2, ENDORSE),
    )
    assert second.decision == "DENY"
    assert second.provider_receipt_verified is False
    assert second.executed is False


@pytest.mark.parametrize("operation,scenario", [(CRM, CRM_SCENARIO), (FIN, FIN_SCENARIO)])
def test_explicit_decline_is_terminal(operation, scenario):
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposed = submit(model, tenant, operation=operation, scenario=scenario)
    rejected = model.review(tenant, proposed.proposal_id, REVIEWER_1, DECLINE,
                            tick=11, expected_version=0)
    assert rejected.status == REJECTED
    assert rejected.decision == "DENY"
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, proposed.proposal_id, REVIEWER_2, ENDORSE,
                     tick=12, expected_version=1)


def test_replay_returns_same_id_and_version_and_consumes_no_extra_quota():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposed = submit(model, tenant)
    same = submit(model, tenant)
    assert same == proposed
    reviewed = model.review(tenant, proposed.proposal_id, REVIEWER_1, ENDORSE,
                            tick=12, expected_version=0)
    same_after_review = submit(model, tenant, tick=12)
    assert same_after_review == reviewed
    assert same_after_review.proposal_id == proposed.proposal_id


@pytest.mark.parametrize("changed", [
    {"operation": FIN, "scenario": FIN_SCENARIO},
    {"scenario": "DEMO-CRM-LEAD-BETA"},
    {"actor": "DEMO-ACTOR-STRANGER"},
])
def test_same_idempotency_key_with_changed_payload_is_rejected(changed):
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    submit(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        submit(model, tenant, **changed)
    assert model.inspect(tenant, next(iter(model._proposals))).version == 0


def test_idempotency_key_is_partitioned_by_demo_tenant_not_authentication():
    model, first_tenant, second_tenant = OfflineSyntheticWriteProposals(), uuid4(), uuid4()
    first = submit(model, first_tenant)
    second = submit(model, second_tenant)
    assert first.proposal_id != second.proposal_id
    with pytest.raises(SyntheticProposalNotFound):
        model.inspect(second_tenant, first.proposal_id)
    with pytest.raises(SyntheticProposalNotFound):
        model.review(second_tenant, first.proposal_id, REVIEWER_1, ENDORSE,
                     tick=11, expected_version=0)
    assert model.inspect(first_tenant, first.proposal_id).status == PENDING


def test_proposer_cannot_self_endorse_even_with_demo_actor_label():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposed = submit(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, proposed.proposal_id, AUTHOR, ENDORSE,
                     tick=11, expected_version=0)
    assert model.inspect(tenant, proposed.proposal_id).version == 0


def test_duplicate_reviewer_cannot_vote_twice_for_high_risk():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposed = finance(model, tenant)
    model.review(tenant, proposed.proposal_id, REVIEWER_1, ENDORSE,
                 tick=11, expected_version=0)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, proposed.proposal_id, REVIEWER_1, ENDORSE,
                     tick=12, expected_version=1)
    assert model.inspect(tenant, proposed.proposal_id).version == 1


@pytest.mark.parametrize("expected_version", [True, -1, 1, "0", None])
def test_stale_or_invalid_expected_version_is_rejected(expected_version):
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposal = finance(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, proposal.proposal_id, REVIEWER_1, ENDORSE,
                     tick=11, expected_version=expected_version)
    assert model.inspect(tenant, proposal.proposal_id).version == 0


def test_stale_concurrent_reviews_commit_at_most_one():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    proposed = finance(model, tenant)
    def worker(i):
        try:
            model.review(tenant, proposed.proposal_id,
                         f"DEMO-ACTOR-REVIEWER-{i:03d}", ENDORSE,
                         tick=11, expected_version=0)
            return True
        except SyntheticProposalDenied:
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        flags = list(pool.map(worker, range(40)))
    assert sum(flags) == 1
    assert model.inspect(tenant, proposed.proposal_id).version == 1
    assert model.inspect(tenant, proposed.proposal_id).status == PENDING


def test_concurrent_duplicate_proposals_create_exactly_one():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    with ThreadPoolExecutor(max_workers=12) as pool:
        items = list(pool.map(lambda _: submit(model, tenant), range(60)))
    assert len({item.proposal_id for item in items}) == 1
    assert len(model._proposals) == 1


def test_review_expiry_is_fail_closed_without_applying_action():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    p = submit(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, p.proposal_id, REVIEWER_1, ENDORSE,
                     tick=31, expected_version=0)
    assert model.inspect(tenant, p.proposal_id).status == PENDING
    accepted_at_boundary = model.review(
        tenant, p.proposal_id, REVIEWER_1, ENDORSE,
        tick=30, expected_version=0,
    )
    assert accepted_at_boundary.status == REVIEWED
    assert accepted_at_boundary.executed is False


def test_retroactive_review_and_replay_ticks_denied():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    p = submit(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, p.proposal_id, REVIEWER_1, ENDORSE,
                     tick=9, expected_version=0)
    model.review(tenant, p.proposal_id, REVIEWER_1, ENDORSE,
                 tick=12, expected_version=0)
    with pytest.raises(SyntheticProposalDenied):
        submit(model, tenant, tick=11)


@pytest.mark.parametrize("invalid_operation,scenario", [
    ("business.lead-intake.validate.v1", CRM_SCENARIO),
    ("business.inventory.stock-preview.v1", CRM_SCENARIO),
    ("business.crm.sync-execute.v1", CRM_SCENARIO),
    ("business.finance.reconciliation-proposal.v1", CRM_SCENARIO),
    (None, CRM_SCENARIO),
])
def test_unknown_read_only_and_wrong_scenario_requests_fail(invalid_operation, scenario):
    with pytest.raises(SyntheticProposalDenied):
        submit(OfflineSyntheticWriteProposals(), uuid4(),
               operation=invalid_operation, scenario=scenario)


@pytest.mark.parametrize("scenario", [
    "", "REAL-CUSTOMER-123", {"secret": "injected"},
    "DEMO-CRM-LEAD-ALPHA;DROP", "DEMO-FINANCE-INVOICE-MATCH",
    None,
])
def test_untrusted_or_non_allowlisted_payloads_fail(scenario):
    with pytest.raises(SyntheticProposalDenied):
        submit(OfflineSyntheticWriteProposals(), uuid4(), scenario=scenario)


@pytest.mark.parametrize("actor", [
    "admin", "DEMO-ACTOR-", "REAL-HUMAN-123",
    "DEMO-ACTOR-operator@company.com", "DEMO-ACTOR-X" * 30,
    None, 5,
])
def test_invalid_unverified_principal_strings_fail(actor):
    with pytest.raises(SyntheticProposalDenied):
        submit(OfflineSyntheticWriteProposals(), uuid4(), actor=actor)


@pytest.mark.parametrize("key", [
    "live-key", "DEMO-IDEMP-", "DEMO-IDEMP-SECRET/FILE",
    "DEMO-IDEMP-\u2603", "DEMO-IDEMP-X" * 35, None, 7,
])
def test_invalid_idempotency_keys_fail(key):
    with pytest.raises(SyntheticProposalDenied):
        submit(OfflineSyntheticWriteProposals(), uuid4(), key=key)


@pytest.mark.parametrize("bad", ["not-a-tenant", None, True, 7])
def test_demo_tenant_must_be_uuid(bad):
    with pytest.raises(SyntheticProposalDenied):
        submit(OfflineSyntheticWriteProposals(), bad)


@pytest.mark.parametrize("tick", [-1, True, 0.5, None, "10", 1_000_001, 999_990])
def test_invalid_or_overflowing_proposal_ticks_fail(tick):
    with pytest.raises(SyntheticProposalDenied):
        submit(OfflineSyntheticWriteProposals(), uuid4(), tick=tick)


@pytest.mark.parametrize("vote", [
    "APPROVE", "EXECUTE", "SIM_APPROVED_AND_EXECUTED", "sim_endorse",
    True, None,
])
def test_simulated_vote_cannot_be_used_as_execution_command(vote):
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    p = submit(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, p.proposal_id, REVIEWER_1, vote,
                     tick=11, expected_version=0)
    assert model.inspect(tenant, p.proposal_id).version == 0


def test_reviewer_identity_must_be_demo_only_and_valid():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    p = submit(model, tenant)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, p.proposal_id, "live-user@example.com",
                     ENDORSE, tick=11, expected_version=0)


def test_completing_terminal_proposal_again_is_rejected():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    p = submit(model, tenant)
    model.review(tenant, p.proposal_id, REVIEWER_1, ENDORSE,
                 tick=11, expected_version=0)
    with pytest.raises(SyntheticProposalDenied):
        model.review(tenant, p.proposal_id, REVIEWER_2, ENDORSE,
                     tick=12, expected_version=1)


def test_per_tenant_and_total_history_caps_do_not_evict():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    first = None
    for idx in range(16):
        item = submit(model, tenant, key=f"DEMO-IDEMP-LIMIT-{idx:03}")
        first = item if first is None else first
    with pytest.raises(SyntheticProposalDenied):
        submit(model, tenant, key="DEMO-IDEMP-LIMIT-OVER")
    assert model.inspect(tenant, first.proposal_id).version == 0
    for group in range(1, 4):
        other_tenant = UUID(int=group)
        for idx in range(16):
            submit(model, other_tenant, key=f"DEMO-IDEMP-FULL-{group}-{idx:03}")
    assert len(model._proposals) == MAX_PROPOSALS_TOTAL
    with pytest.raises(SyntheticProposalDenied):
        submit(model, uuid4(), key="DEMO-IDEMP-FULL-OVER")
    assert submit(model, tenant, key="DEMO-IDEMP-LIMIT-000").proposal_id == first.proposal_id


def test_tracked_tenant_count_capped_even_if_proposals_not_expired():
    model = OfflineSyntheticWriteProposals()
    for idx in range(16):
        submit(model, UUID(int=idx + 1), key="DEMO-IDEMP-NEW")
    with pytest.raises(SyntheticProposalDenied):
        submit(model, UUID(int=17), key="DEMO-IDEMP-NEW")


def test_snapshot_is_immutable_and_reviews_not_aliases():
    model, tenant = OfflineSyntheticWriteProposals(), uuid4()
    p = finance(model, tenant)
    with pytest.raises(FrozenInstanceError):
        p.execution_authorized = True
    first = model.review(tenant, p.proposal_id, REVIEWER_1, ENDORSE,
                         tick=11, expected_version=0)
    second = model.review(tenant, p.proposal_id, REVIEWER_2, ENDORSE,
                          tick=12, expected_version=1)
    assert p.version == 0
    assert first.version == 1
    assert second.version == 2
    assert p.simulated_reviews == ()
    assert first.simulated_reviews == ((REVIEWER_1, ENDORSE),)


def test_no_runtime_import_io_route_credential_or_execution_wiring():
    source = (ROOT / "apps/api/app/synthetic_write_proposals.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "synthetic_write_proposals" not in main
    for forbidden in (
        "APIRouter(", "requests.", "httpx.", "socket.", "psycopg",
        "redis.", "subprocess.", "urlopen", "http://", "https://",
        "import os", "open(", "time.sleep", "datetime", "asyncio",
    ):
        assert forbidden not in source
