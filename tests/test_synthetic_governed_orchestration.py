"""P2-03v: durable offline two-person approvals, revocation, tool policy, recovery."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sqlite3
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_governed_orchestration import (
    GovernedOrchestration, DEMO_PROJECT, TOOLS, demo_database_path,
)
from app.disposable_crm_authorization import ISSUER,AUDIENCE

NOW=1_800_000_000


def issued(private, *, ws="academy_demo", role="tenant_admin",
           actor="SIM-ACTOR-OWNER01", ref="SIM-TOKEN-OWNER01",
           exp=NOW+90, aud=AUDIENCE, iss=ISSUER, issued_at=NOW-5):
    claims={
        "version":1,"issuer":iss,"audience":aud,"workspace":ws,
        "actor_ref":actor,"role":role,"issued_at":issued_at,
        "expires_at":exp,"token_ref":ref,
    }
    payload=base64.urlsafe_b64encode(json.dumps(
        claims,sort_keys=True,separators=(",",":")).encode()).rstrip(b"=").decode()
    statement="v1."+payload
    signature=base64.urlsafe_b64encode(private.sign(
        statement.encode("ascii"))).rstrip(b"=").decode()
    return statement+"."+signature


@pytest.fixture
def suite(tmp_path):
    private=Ed25519PrivateKey.generate()
    actor={
        "owner":issued(private),
        "reviewer":issued(private,role="reviewer",
                          actor="SIM-ACTOR-SEC01",ref="SIM-TOKEN-SEC01"),
        "auditor":issued(private,role="auditor",
                         actor="SIM-ACTOR-AUD01",ref="SIM-TOKEN-AUD01"),
        "admin2":issued(private,role="tenant_admin",
                        actor="SIM-ACTOR-ADMIN02",ref="SIM-TOKEN-ADMIN02"),
        "other":issued(private,ws="bespoke_demo",role="tenant_admin",
                       actor="SIM-ACTOR-BESPOKE",ref="SIM-TOKEN-BESPOKE"),
        "other_reviewer":issued(private,ws="bespoke_demo",role="reviewer",
                                actor="SIM-ACTOR-BESPOKE-SEC",
                                ref="SIM-TOKEN-BESPOKE-SEC"),
    }
    filename=tmp_path/"governed.p2-03v-demo.sqlite3"
    db=GovernedOrchestration(filename,private.public_key(),clock=NOW)
    yield db,actor,private,filename
    db.close()


def approved(db,actor,ref="SIM-PLAN-01",scenario="LEAD_QUALIFICATION"):
    db.propose(actor["owner"],ref,scenario)
    db.approve_owner(actor["owner"],ref)
    db.approve_security(actor["reviewer"],ref)
    return ref


@pytest.mark.parametrize("scenario",[
    "LEAD_QUALIFICATION","INVENTORY_RESILIENCE",
    "CONTENT_OPERATIONS","SECURITY_TRIAGE"
])
def test_all_four_projects_require_independent_approval(suite,scenario):
    db,actors,_,_=suite
    ref="SIM-PLAN-"+scenario.replace("_","-")
    draft=db.propose(actors["owner"],ref,scenario)
    assert draft["state"]=="DRAFT"
    assert draft["external_execution_enabled"] is False
    with pytest.raises(SyntheticGrowthError):
        db.run_synthetic(actors["owner"],ref)
    with pytest.raises(SyntheticGrowthError):
        db.approve_security(actors["reviewer"],ref)
    owner=db.approve_owner(actors["owner"],ref)
    assert owner["state"]=="OWNER_APPROVED"
    with pytest.raises(SyntheticGrowthError):
        db.run_synthetic(actors["owner"],ref)
    reviewer=db.approve_security(actors["reviewer"],ref)
    assert reviewer["state"]=="SECURITY_APPROVED"
    assert reviewer["reviewer_ref"] != reviewer["owner_ref"]
    trace=db.run_synthetic(actors["owner"],ref)
    assert trace["completed_internal_simulations"]==3
    assert trace["external_actions_attempted"]==0
    assert trace["provider_requests"]==0
    assert trace["real_ai_inference_calls"]==0
    assert trace["human_decisions_recorded"]==0
    assert db.read(actors["auditor"],ref)["state"]=="SIMULATED"
    with pytest.raises(SyntheticGrowthError):
        db.run_synthetic(actors["owner"],ref)


def test_no_self_review_without_real_independent_role(suite):
    db,actors,priv,_=suite
    ref="SIM-PLAN-NO-SELF"
    db.propose(actors["owner"],ref,"CONTENT_OPERATIONS")
    db.approve_owner(actors["owner"],ref)
    same_person_review=issued(priv,role="reviewer",
        actor="SIM-ACTOR-OWNER01",ref="SIM-TOKEN-FAKE-REVIEW")
    with pytest.raises(SyntheticGrowthError,match="Independent"):
        db.approve_security(same_person_review,ref)
    with pytest.raises(SyntheticGrowthError):
        db.approve_security(actors["owner"],ref)
    assert db.read(actors["auditor"],ref)["state"]=="OWNER_APPROVED"


def test_cross_tenant_scope_unauthorized_roles_and_duplicate_replay(suite):
    db,actors,_,_=suite
    ref="SIM-PLAN-TENANT"
    db.propose(actors["owner"],ref,"INVENTORY_RESILIENCE")
    with pytest.raises(SyntheticGrowthError):
        db.read(actors["other"],ref)
    with pytest.raises(SyntheticGrowthError):
        db.approve_owner(actors["other"],ref)
    with pytest.raises(SyntheticGrowthError):
        db.approve_owner(actors["reviewer"],ref)
    with pytest.raises(SyntheticGrowthError):
        db.propose(actors["auditor"],"SIM-PLAN-AUDITOR","CONTENT_OPERATIONS")
    with pytest.raises(SyntheticGrowthError):
        db.propose(actors["owner"],ref,"INVENTORY_RESILIENCE")
    with pytest.raises(SyntheticGrowthError):
        db.propose(actors["owner"],"SIM-PLAN-BAD","BAD_SCENARIO")
    assert db.read(actors["auditor"],ref)["state"]=="DRAFT"
    assert db.propose(actors["other"],ref,"SECURITY_TRIAGE")["workspace"]=="bespoke_demo"
    assert db.read(actors["other"],ref)["scenario"]=="SECURITY_TRIAGE"
    with pytest.raises(SyntheticGrowthError):
        db.approve_security(actors["other_reviewer"],"SIM-PLAN-BAD")


@pytest.mark.parametrize("tool",[
    "POST_INSTAGRAM","SEND_WHATSAPP","READ_CUSTOMER_PII",
    "CHARGE_CARD","EXECUTE_SHELL","DELETE_DATABASE","HTTP_REQUEST",
])
def test_external_tools_deny_even_after_both_approvals(suite,tool):
    db,actors,_,_=suite
    ref=approved(db,actors)
    decision=db.review_tool(actors["reviewer"],ref,tool)
    assert decision["decision"]=="DENIED"
    assert decision["external_execution"] is False
    assert decision["model_calls"]==0


def test_safe_virtual_tools_are_never_called(suite):
    db,actors,_,_=suite
    ref=approved(db,actors)
    for tool in TOOLS:
        verdict=db.review_tool(actors["reviewer"],ref,tool)
        assert verdict["decision"]=="VIRTUAL_ONLY"
        assert not verdict["external_execution"]
    count=db.db.execute(
        "SELECT COUNT(*) FROM synthetic_tool_reviews WHERE workspace=?",
        ("academy_demo",),
    ).fetchone()[0]
    assert count==len(TOOLS)
    with pytest.raises(SyntheticGrowthError):
        db.review_tool(actors["owner"],ref,"ANALYZE_SAMPLE")
    with pytest.raises(SyntheticGrowthError):
        db.review_tool(actors["auditor"],ref,"ANALYZE_SAMPLE")


def test_revocation_invalidates_approved_plans_and_survives_restart(suite):
    db,actors,private,path=suite
    ref=approved(db,actors)
    before=db.audit_report(actors["auditor"])
    assert before["chain_consistent"] and before["events"]>=3
    result=db.revoke(actors["admin2"],"SIM-TOKEN-SEC01")
    assert result["plans_invalidated"]==1
    assert db.read(actors["owner"],ref)["state"]=="REVOKED"
    with pytest.raises(SyntheticGrowthError):
        db.review_tool(actors["reviewer"],ref,"ANALYZE_SAMPLE")
    with pytest.raises(SyntheticGrowthError):
        db.run_synthetic(actors["owner"],ref)
    with pytest.raises(SyntheticGrowthError):
        db.revoke(actors["admin2"],"SIM-TOKEN-SEC01")
    db.close()
    reopened=GovernedOrchestration(path,private.public_key(),clock=NOW)
    try:
        assert reopened.read(actors["owner"],ref)["state"]=="REVOKED"
        assert reopened.audit_report(actors["auditor"])["events"]==before["events"]+1
        with pytest.raises(SyntheticGrowthError):
            reopened.approve_security(actors["reviewer"],ref)
    finally:
        reopened.close()


def test_owner_session_revocation_requires_independent_admin(suite):
    db,actors,_,_=suite
    ref=approved(db,actors)
    with pytest.raises(SyntheticGrowthError):
        db.revoke(actors["owner"],"SIM-TOKEN-OWNER01")
    assert db.revoke(actors["admin2"],"SIM-TOKEN-OWNER01")["plans_invalidated"]==1
    with pytest.raises(SyntheticGrowthError):
        db.read(actors["owner"],ref)
    assert db.read(actors["auditor"],ref)["state"]=="REVOKED"


def test_expired_invalid_audience_untrusted_signer_and_tampered_token(suite):
    db,actors,private,_=suite
    other_key=Ed25519PrivateKey.generate()
    bad=[
        issued(private,exp=NOW-1),
        issued(private,iss="unapproved-issuer"),
        issued(private,aud="live-production"),
        issued(other_key),
        actors["owner"]+"x",
        "unstructured-token",
    ]
    for token in bad:
        with pytest.raises(SyntheticGrowthError):
            db.propose(token,"SIM-PLAN-INVALID","LEAD_QUALIFICATION")
    assert db.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0]==0


def test_durable_hash_chain_checkpoint_and_recovery_backup(suite,tmp_path):
    db,actors,private,_=suite
    ref=approved(db,actors)
    db.review_tool(actors["reviewer"],ref,"GENERATE_REVIEW_PLAN")
    trace=db.run_synthetic(actors["owner"],ref)
    assert not trace["live_workflow_started"]
    a=db.audit_report(actors["auditor"])
    backup=tmp_path/"recovery.p2-03v-demo.sqlite3"
    assert db.backup_to(actors["owner"],backup)["copied_to_disposable_snapshot"]
    restored=GovernedOrchestration(backup,private.public_key(),clock=NOW)
    try:
        b=restored.audit_report(actors["auditor"],trusted_head=a["head_sha256"])
        assert a==b
        assert restored.read(actors["auditor"],ref)["state"]=="SIMULATED"
        assert restored.db.execute("SELECT count(*) FROM synthetic_tool_reviews").fetchone()[0]==1
        with pytest.raises(SyntheticGrowthError,match="checkpoint"):
            restored.audit_report(actors["auditor"],trusted_head="f"*64)
        with pytest.raises(SyntheticGrowthError):
            restored.propose(actors["auditor"],"SIM-PLAN-INVALID","CONTENT_OPERATIONS")
    finally:
        restored.close()


def test_tampering_with_audit_row_is_detected(suite):
    db,actors,_,_=suite
    approved(db,actors)
    before=db.audit_report(actors["auditor"])
    assert before["events"]==3
    db.db.execute("UPDATE audit SET event_json=? WHERE workspace=? AND sequence=2",
                  ('{"forged":true}',"academy_demo"))
    with pytest.raises(SyntheticGrowthError,match="integrity"):
        db.audit_report(actors["auditor"])


def test_atomic_rollback_on_audit_insert_failure(suite):
    db,actors,_,_=suite
    db.db.execute("""
      CREATE TRIGGER force_failure BEFORE INSERT ON audit
      BEGIN SELECT RAISE(ABORT, 'synthetic triggered failure'); END
    """)
    with pytest.raises(sqlite3.IntegrityError):
        db.propose(actors["owner"],"SIM-PLAN-ROLLBACK","SECURITY_TRIAGE")
    assert db.db.execute("SELECT count(*) FROM plans").fetchone()[0]==0
    assert db.db.execute("SELECT count(*) FROM audit").fetchone()[0]==0


def test_unexpected_database_path_denied(tmp_path):
    with pytest.raises(SyntheticGrowthError):
        demo_database_path("/var/lib/postgresql/customer.sqlite3")
    with pytest.raises(SyntheticGrowthError):
        demo_database_path(tmp_path/"real_customers.db")
    with pytest.raises(SyntheticGrowthError):
        demo_database_path(tmp_path/"bad.p2-03v-demo.sqlite3/../../real.sqlite3")


def test_one_unverified_revocation_cannot_activate_an_agent(suite):
    db,actors,_,_=suite
    ref=approved(db,actors,"SIM-PLAN-KILL","CONTENT_OPERATIONS")
    # Code never exposes a callable external tool, including after approval.
    for tool in ("EXECUTE_SHELL","PUBLISH_META_AD","SEND_EMAIL"):
        verdict=db.review_tool(actors["reviewer"],ref,tool)
        assert verdict["decision"]=="DENIED"
        assert not verdict["external_execution"]
    db.revoke(actors["admin2"],"SIM-TOKEN-OWNER01")
    with pytest.raises(SyntheticGrowthError):
        db.run_synthetic(actors["owner"],ref)
    assert db.db.execute(
        "SELECT count(*) FROM plans WHERE state='REVOKED'").fetchone()[0]==1
