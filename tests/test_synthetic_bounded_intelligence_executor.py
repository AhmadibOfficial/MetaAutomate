"""P2-03x: full source-only signed approvals -> bounded tool -> audit verification."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))

from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_oidc_identity import OfflineIdentityTrust, ISSUER, AUDIENCE
from app.disposable_crm_authorization import (
    ISSUER as APP_ISS, AUDIENCE as APP_AUD,
)
from app.synthetic_governed_orchestration import GovernedOrchestration
from app.synthetic_governed_intelligence_portfolio import (
    GovernedIntelligenceGateway, VIRTUAL_TOOLS, MODULE_ENGINE_MAP,
)
from app.synthetic_bounded_intelligence_executor import (
    BoundedIntelligenceExecutor, simulate_tool, validated_inputs,
)

NOW=1800000000
MEMBER={
    "owner":{"sub":"SIM-SUB-OWNER01","actor":"SIM-ACTOR-OWNER01",
             "jti":"SIM-JTI-OWNER01","token":"SIM-TOKEN-OWNER01","role":"owner",
             "app_role":"tenant_admin"},
    "reviewer":{"sub":"SIM-SUB-REVIEWER01","actor":"SIM-ACTOR-REVIEWER01",
                "jti":"SIM-JTI-REVIEWER01","token":"SIM-TOKEN-REVIEWER01",
                "role":"security_reviewer","app_role":"reviewer"},
    "auditor":{"sub":"SIM-SUB-AUDITOR01","actor":"SIM-ACTOR-AUDITOR01",
               "jti":"SIM-JTI-AUDITOR01","token":"SIM-TOKEN-AUDITOR01",
               "role":"auditor","app_role":"auditor"},
    "admin2":{"sub":"SIM-SUB-ADMIN02","actor":"SIM-ACTOR-ADMIN02",
              "jti":"SIM-JTI-ADMIN02","token":"SIM-TOKEN-ADMIN02",
              "role":"owner","app_role":"tenant_admin"},
    "other":{"sub":"SIM-SUB-OTHER01","actor":"SIM-ACTOR-OTHER01",
             "jti":"SIM-JTI-OTHER01","token":"SIM-TOKEN-OTHER01",
             "role":"owner","app_role":"tenant_admin"},
}


def enc(payload):
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def signed(key,part1,part2):
    data=enc(json.dumps(part1,sort_keys=True,separators=(",",":")).encode())+"."+enc(
        json.dumps(part2,sort_keys=True,separators=(",",":")).encode())
    return data+"."+enc(key.sign(data.encode()))


def idp(key,person,*,ws="academy_demo"):
    m=MEMBER[person]
    return signed(key,{"typ":"JWT","alg":"EdDSA","kid":"ci-key-one"},
                  {"iss":ISSUER,"aud":AUDIENCE,"sub":m["sub"],
                   "iat":NOW-6,"nbf":NOW-7,"exp":NOW+100,"auth_time":NOW-8,
                   "jti":m["jti"],"workspace":ws,"role":m["role"],
                   "amr":["pwd","mfa"]})


def app(key,person,*,ws="academy_demo"):
    m=MEMBER[person]
    body={"version":1,"issuer":APP_ISS,"audience":APP_AUD,
          "workspace":ws,"actor_ref":m["actor"],"role":m["app_role"],
          "issued_at":NOW-6,"expires_at":NOW+100,"token_ref":m["token"]}
    payload=enc(json.dumps(body,sort_keys=True,separators=(",",":")).encode())
    pre="v1."+payload
    return pre+"."+enc(key.sign(pre.encode()))


@pytest.fixture
def env(tmp_path):
    private_idp=Ed25519PrivateKey.generate()
    private_app=Ed25519PrivateKey.generate()
    membership={m["sub"]:{"workspace":"bespoke_demo" if name=="other" else "academy_demo",
                         "role":m["role"],"actor_ref":m["actor"]}
                for name,m in MEMBER.items()}
    trust=OfflineIdentityTrust(
        keys={"ci-key-one":private_idp.public_key()},memberships=membership)
    db=GovernedOrchestration(tmp_path/"agent.p2-03v-demo.sqlite3",
                             private_app.public_key(),clock=NOW)
    gateway=GovernedIntelligenceGateway(db,trust)
    runner=BoundedIntelligenceExecutor(gateway)
    tokens={name:(
        idp(private_idp,name,ws="bespoke_demo" if name=="other" else "academy_demo"),
        app(private_app,name,ws="bespoke_demo" if name=="other" else "academy_demo")
    ) for name in MEMBER}
    yield db,gateway,runner,tokens,private_idp,private_app,tmp_path
    db.close()


def approved(env,ref="SIM-PLAN-DEMO",scenario="LEAD_QUALIFICATION"):
    db,gateway,runner,token,*_=env
    gateway.propose(*token["owner"],ref,scenario)
    gateway.owner_approve(*token["owner"],ref)
    gateway.security_approve(*token["reviewer"],ref)
    before=gateway.simulate(*token["owner"],ref)
    assert before["provider_requests"]==0
    return ref


@pytest.mark.parametrize("module",list(MODULE_ENGINE_MAP))
def test_each_module_runs_only_scoped_synthetic_sample(env,module):
    db,gateway,runner,tokens,*_=env
    ref=approved(env,ref="SIM-PLAN-"+module.upper().replace("_","-"))
    tool="ANALYZE_SAMPLE"
    cmd="SIM-CMD-"+module.upper().replace("_","-")+"-TASK"
    grant=runner.grant(*tokens["reviewer"],ref,cmd,module,tool,
                       "REVIEW_BUSINESS_EVIDENCE",
                       {"sample_count":10,"flagged_count":3})
    assert grant["state"]=="REVIEWED" and grant["approved_live_execution"] is False
    evidence=runner.run(*tokens["owner"],cmd)
    assert evidence["synthetic_execution"]["result"]["flagged_share_basis_points"]==3000
    assert evidence["synthetic_execution"]["external_effects"]==0
    assert not evidence["executed_in_live_environment"]
    replay=runner.run(*tokens["owner"],cmd)
    assert replay["evidence_sha256"]==evidence["evidence_sha256"]
    assert replay["idempotent_replay"] is True
    assert db.db.execute("SELECT COUNT(*) FROM bounded_virtual_actions WHERE command_id=?",
                         (cmd,)).fetchone()[0]==1
    checked=runner.verify(*tokens["auditor"],cmd)
    assert checked["synthetic_computation_reproduced"]
    assert not checked["production_runtime_verified"]
    assert not checked["real_customer_data_verified"]


@pytest.mark.parametrize("tool,params,expected",[
    ("ANALYZE_SAMPLE",{"sample_count":0,"flagged_count":0},None),
    ("ANALYZE_SAMPLE",{"sample_count":3,"flagged_count":3},10000),
    ("GENERATE_REVIEW_PLAN",{"finding_count":31,"review_capacity":10},4),
    ("GENERATE_REVIEW_PLAN",{"finding_count":0,"review_capacity":1},0),
    ("SUMMARIZE_EVIDENCE",{"baseline_count":20,"current_count":13},-7),
    ("SUMMARIZE_EVIDENCE",{"baseline_count":0,"current_count":1000},1000),
])
def test_pure_virtual_tool_outputs_are_bounded_and_noncausal(tool,params,expected):
    trace=simulate_tool(tool,params)
    value=trace["result"]
    metric={"ANALYZE_SAMPLE":"flagged_share_basis_points",
            "GENERATE_REVIEW_PLAN":"review_batches",
            "SUMMARIZE_EVIDENCE":"illustrative_change"}[tool]
    assert value[metric]==expected
    assert trace["model_inference_calls"]==0
    assert trace["payments"]==0 and trace["provider_calls"]==0
    assert trace["messages_sent"]==0 and trace["external_effects"]==0


@pytest.mark.parametrize("tool,parameters",[
    ("SEND_WHATSAPP",{"sample_count":1,"flagged_count":0}),
    ("EXECUTE_SHELL",{"sample_count":1,"flagged_count":0}),
    ("ANALYZE_SAMPLE",{"sample_count":True,"flagged_count":0}),
    ("ANALYZE_SAMPLE",{"sample_count":1.0,"flagged_count":0}),
    ("ANALYZE_SAMPLE",{"sample_count":1,"flagged_count":2}),
    ("ANALYZE_SAMPLE",{"sample_count":-1,"flagged_count":0}),
    ("ANALYZE_SAMPLE",{"sample_count":1001,"flagged_count":0}),
    ("ANALYZE_SAMPLE",{"sample_count":1,"flagged_count":0,"email":"a@example.org"}),
    ("ANALYZE_SAMPLE",{"sample_count":"1","flagged_count":0}),
    ("GENERATE_REVIEW_PLAN",{"finding_count":1,"review_capacity":0}),
    ("SUMMARIZE_EVIDENCE",{"baseline_count":2,"current_count":None}),
])
def test_no_arbitrary_input_or_live_tool(tool,parameters):
    with pytest.raises(SyntheticGrowthError):
        simulate_tool(tool,parameters)


def test_owner_must_complete_full_prior_two_person_workflow(env):
    db,gateway,runner,tokens,*_=env
    ref="SIM-PLAN-UNAPPROVED"
    gateway.propose(*tokens["owner"],ref,"LEAD_QUALIFICATION")
    with pytest.raises(SyntheticGrowthError):
        runner.grant(*tokens["reviewer"],ref,"SIM-CMD-UNAPPROVED",
                     "finance","ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                     {"sample_count":10,"flagged_count":1})
    gateway.owner_approve(*tokens["owner"],ref)
    gateway.security_approve(*tokens["reviewer"],ref)
    with pytest.raises(SyntheticGrowthError):
        runner.grant(*tokens["reviewer"],ref,"SIM-CMD-UNAPPROVED",
                     "finance","ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                     {"sample_count":10,"flagged_count":1})
    assert db.db.execute("SELECT COUNT(*) FROM bounded_virtual_actions").fetchone()[0]==0


def test_policy_rejects_foreign_scope_and_prohibited_module_tool(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    inputs={"finding_count":4,"review_capacity":2}
    for module,tool,purpose in [
        ("finance","GENERATE_REVIEW_PLAN","PREPARE_HUMAN_DECISION"),
        ("no_such_module","ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE"),
        ("finance","SEND_EMAIL","REVIEW_BUSINESS_EVIDENCE"),
        ("finance","GENERATE_REVIEW_PLAN","PUBLISH_POST"),
    ]:
        with pytest.raises(SyntheticGrowthError):
            runner.grant(*tokens["reviewer"],ref,"SIM-CMD-BADPOLICY",
                         module,tool,purpose,inputs)
    with pytest.raises(SyntheticGrowthError):
        runner.grant(*tokens["owner"],ref,"SIM-CMD-IMPERSONATE",
                     "finance","ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                     {"sample_count":3,"flagged_count":1})
    with pytest.raises(SyntheticGrowthError):
        runner.grant(*tokens["other"],ref,"SIM-CMD-CROSSTENANT",
                     "finance","ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                     {"sample_count":3,"flagged_count":1})
    assert db.db.execute("SELECT COUNT(*) FROM bounded_virtual_actions").fetchone()[0]==0


def test_replay_and_changed_input_forbidden(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    good={"baseline_count":17,"current_count":14}
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-ONE1","finance",
                 "SUMMARIZE_EVIDENCE","REVIEW_BUSINESS_EVIDENCE",good)
    with pytest.raises(SyntheticGrowthError):
        runner.grant(*tokens["reviewer"],ref,"SIM-CMD-ONE1","finance",
                     "SUMMARIZE_EVIDENCE","REVIEW_BUSINESS_EVIDENCE",
                     {"baseline_count":17,"current_count":13})
    evidence=runner.run(*tokens["owner"],"SIM-CMD-ONE1")
    assert evidence["synthetic_execution"]["result"]["illustrative_change"]==-3
    with pytest.raises(SyntheticGrowthError):
        runner.run(*tokens["other"],"SIM-CMD-ONE1")
    with pytest.raises(SyntheticGrowthError):
        runner.run(*tokens["reviewer"],"SIM-CMD-ONE1")


def test_expiry_and_role_revocation_after_grant_are_fail_closed(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-EXPIRE","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":5,"flagged_count":1})
    db.clock_override=NOW+121
    with pytest.raises(SyntheticGrowthError):
        runner.run(*tokens["owner"],"SIM-CMD-EXPIRE")
    db.clock_override=NOW
    result=db.revoke(tokens["admin2"][1],MEMBER["reviewer"]["token"])
    assert result["revoked"]
    with pytest.raises(SyntheticGrowthError):
        runner.run(*tokens["owner"],"SIM-CMD-EXPIRE")


def test_independent_idp_jti_revocation_after_review_denies_execution(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-REVOKED","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":5,"flagged_count":1})
    gateway.trust=gateway.trust.with_revocation(jti=MEMBER["reviewer"]["jti"])
    with pytest.raises(SyntheticGrowthError,match="revoked"):
        runner.run(*tokens["owner"],"SIM-CMD-REVOKED")


def test_stored_evidence_and_audit_tampering_are_detected(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-AUDIT","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":5,"flagged_count":1})
    runner.run(*tokens["owner"],"SIM-CMD-AUDIT")
    before=runner.verify(*tokens["auditor"],"SIM-CMD-AUDIT")
    assert before["local_audit_chain_consistent"]
    with pytest.raises(SyntheticGrowthError):
        runner.verify(*tokens["other"],"SIM-CMD-AUDIT")
    db.db.execute("UPDATE bounded_virtual_actions SET result_sha256=?"
                  " WHERE command_id='SIM-CMD-AUDIT'",("f"*64,))
    with pytest.raises(SyntheticGrowthError):
        runner.verify(*tokens["auditor"],"SIM-CMD-AUDIT")


def test_audit_chain_cannot_be_forged_without_detection(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-CHECKPOINT","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":5,"flagged_count":1})
    runner.run(*tokens["owner"],"SIM-CMD-CHECKPOINT")
    head=runner.verify(*tokens["auditor"],"SIM-CMD-CHECKPOINT")[
        "audit_head_sha256"]
    assert runner.verify(*tokens["auditor"],"SIM-CMD-CHECKPOINT",
                         trusted_audit_head=head)["audit_head_sha256"]==head
    db.db.execute("UPDATE audit SET event_json='{}'"
                  " WHERE workspace='academy_demo' AND sequence=1")
    with pytest.raises(SyntheticGrowthError):
        runner.verify(*tokens["auditor"],"SIM-CMD-CHECKPOINT")


def test_disposable_backup_recovery_retains_receipts(env):
    db,gateway,runner,tokens,_,app_key,tmp_path=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-BACKUP","finance",
                 "SUMMARIZE_EVIDENCE","REVIEW_BUSINESS_EVIDENCE",
                 {"baseline_count":5,"current_count":4})
    result=runner.run(*tokens["owner"],"SIM-CMD-BACKUP")
    checkpoint=db.audit_report(tokens["auditor"][1])["head_sha256"]
    target=tmp_path/"recovered.p2-03v-demo.sqlite3"
    db.backup_to(tokens["owner"][1],target)
    recovered=GovernedOrchestration(target,app_key.public_key(),clock=NOW)
    try:
        recovered_gateway=GovernedIntelligenceGateway(recovered,gateway.trust)
        restored=BoundedIntelligenceExecutor(recovered_gateway)
        verified=restored.verify(*tokens["auditor"],"SIM-CMD-BACKUP",
                                 trusted_audit_head=checkpoint)
        assert verified["evidence_sha256"]==result["evidence_sha256"]
        assert verified["synthetic_computation_reproduced"]
        assert recovered.db.execute(
            "SELECT COUNT(*) FROM bounded_virtual_actions").fetchone()[0]==1
        assert restored.run(*tokens["owner"],"SIM-CMD-BACKUP")[
            "idempotent_replay"] is True
    finally:
        recovered.close()


def test_expiring_lease_even_when_session_still_valid(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-SHORTLEASE","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":2,"flagged_count":1})
    db.db.execute(
        "UPDATE bounded_virtual_actions SET lease_expires_at=? "
        "WHERE command_id='SIM-CMD-SHORTLEASE'",(NOW+4,))
    db.clock_override=NOW+6
    with pytest.raises(SyntheticGrowthError,match="lease expired"):
        runner.run(*tokens["owner"],"SIM-CMD-SHORTLEASE")
    assert db.db.execute(
        "SELECT state FROM bounded_virtual_actions WHERE "
        "command_id='SIM-CMD-SHORTLEASE'").fetchone()[0]=="REVIEWED"


def test_revoked_ci_signing_key_invalidates_preapproved_tool(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-KEYREVOKED","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":2,"flagged_count":1})
    gateway.trust=gateway.trust.with_revocation(kid="ci-key-one")
    with pytest.raises(SyntheticGrowthError):
        runner.run(*tokens["owner"],"SIM-CMD-KEYREVOKED")


def test_atomic_evidence_rollback_when_audit_insert_fails(env):
    db,gateway,runner,tokens,*_=env
    ref=approved(env)
    runner.grant(*tokens["reviewer"],ref,"SIM-CMD-ROLLBACK","finance",
                 "ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE",
                 {"sample_count":4,"flagged_count":1})
    import sqlite3
    db.db.execute("""
        CREATE TRIGGER force_audit_failure BEFORE INSERT ON audit
        BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END
    """)
    with pytest.raises(sqlite3.IntegrityError):
        runner.run(*tokens["owner"],"SIM-CMD-ROLLBACK")
    row=db.db.execute(
        "SELECT state,result_json FROM bounded_virtual_actions "
        "WHERE command_id='SIM-CMD-ROLLBACK'").fetchone()
    assert row["state"]=="REVIEWED" and row["result_json"] is None
