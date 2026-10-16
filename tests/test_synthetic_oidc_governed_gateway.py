"""P2-03w: separate offline IdP and application-actor signatures, guarded tasks."""
import base64
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_oidc_identity import (
    OfflineIdentityTrust, ISSUER as OIDC_ISSUER, AUDIENCE as OIDC_AUD,
    require_dual_identity,
)
from app.disposable_crm_authorization import (
    verify_actor_token, ISSUER as APP_ISS, AUDIENCE as APP_AUD,
)
from app.synthetic_governed_orchestration import GovernedOrchestration
from app.synthetic_governed_intelligence_portfolio import GovernedIntelligenceGateway

NOW=1800000000
MEMBERS={
    "SIM-SUB-OWNER01":{"workspace":"academy_demo","role":"owner","actor_ref":"SIM-ACTOR-OWNER01"},
    "SIM-SUB-SEC01":{"workspace":"academy_demo","role":"security_reviewer","actor_ref":"SIM-ACTOR-SEC01"},
    "SIM-SUB-AUD01":{"workspace":"academy_demo","role":"auditor","actor_ref":"SIM-ACTOR-AUD01"},
    "SIM-SUB-ADMIN02":{"workspace":"academy_demo","role":"owner","actor_ref":"SIM-ACTOR-ADMIN02"},
    "SIM-SUB-BES01":{"workspace":"bespoke_demo","role":"owner","actor_ref":"SIM-ACTOR-BES01"},
}


def enc(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def sign_idp(key,*,sub="SIM-SUB-OWNER01",kid="ci-key-one",changes=None,
             head_changes=None,payload=None):
    member=MEMBERS[sub]
    header={"alg":"EdDSA","typ":"JWT","kid":kid}
    if head_changes:header.update(head_changes)
    claims={
        "iss":OIDC_ISSUER,"aud":OIDC_AUD,"sub":sub,"iat":NOW-6,
        "nbf":NOW-7,"exp":NOW+120,"auth_time":NOW-8,
        "jti":"SIM-JTI-"+sub[8:],"workspace":member["workspace"],
        "role":member["role"],"amr":["pwd","mfa"],
    }
    if changes: claims.update(changes)
    raw_claims=(json.dumps(claims,separators=(",",":"),sort_keys=True).encode()
                if payload is None else payload)
    unsigned=enc(json.dumps(header,separators=(",",":"),sort_keys=True).encode())+"."+enc(raw_claims)
    return unsigned+"."+enc(key.sign(unsigned.encode()))


def sign_app(key,*,sub="SIM-SUB-OWNER01",changes=None):
    member=MEMBERS[sub]
    roles={"owner":"tenant_admin","security_reviewer":"reviewer","auditor":"auditor"}
    d={
        "version":1,"issuer":APP_ISS,"audience":APP_AUD,
        "workspace":member["workspace"],"actor_ref":member["actor_ref"],
        "role":roles[member["role"]],"issued_at":NOW-6,
        "expires_at":NOW+120,"token_ref":"SIM-TOKEN-"+sub[8:],
    }
    if changes:d.update(changes)
    payload=enc(json.dumps(d,sort_keys=True,separators=(",",":")).encode())
    unsigned="v1."+payload
    return unsigned+"."+enc(key.sign(unsigned.encode()))


@pytest.fixture
def security(tmp_path):
    idp_a=Ed25519PrivateKey.generate()
    idp_b=Ed25519PrivateKey.generate()
    app=Ed25519PrivateKey.generate()
    trust=OfflineIdentityTrust(
        keys={"ci-key-one":idp_a.public_key(),"ci-key-two":idp_b.public_key()},
        memberships=MEMBERS)
    store=GovernedOrchestration(tmp_path/"governed.p2-03v-demo.sqlite3",
                                app.public_key(),clock=NOW)
    gateway=GovernedIntelligenceGateway(store,trust)
    yield idp_a,idp_b,app,trust,store,gateway
    store.close()


def test_offline_idp_signed_mfa_claims_and_independent_app_role_match(security):
    idp_a,idp_b,app,trust,store,gateway=security
    oidc=trust.verify(sign_idp(idp_a),now=NOW)
    actual=verify_actor_token(sign_app(app),app.public_key(),now=NOW)
    result=require_dual_identity(oidc,actual)
    assert result["dual_signature_verified_in_ci"] is True
    assert result["production_identity_verified"] is False
    assert oidc.mfa_asserted_in_test and not oidc.real_idp_verified
    assert gateway.portfolio(sign_idp(idp_a),sign_app(app))["module_count"]==12
    assert gateway.portfolio(sign_idp(idp_a,sub="SIM-SUB-AUD01"),
                             sign_app(app,sub="SIM-SUB-AUD01"))["engine_count"]==5


@pytest.mark.parametrize("bad_claim",[
    {"iss":"https://bad.example.invalid"},
    {"aud":"production"}, {"workspace":"bespoke_demo"},
    {"role":"security_reviewer"}, {"amr":["pwd"]},
    {"amr":["pwd","sms"]}, {"amr":"mfa"},
    {"iat":NOW+99}, {"nbf":NOW+120},
    {"exp":NOW-1}, {"exp":NOW+1000}, {"exp":True},
    {"auth_time":NOW-700}, {"iat":"not-an-integer"},
    {"sub":"SIM-SUB-NOT-REGISTERED"}, {"jti":"real-email@address.invalid"},
    {"jti":None}, {"scope":"live_publish"},
])
def test_invalid_claims_fail_closed(security,bad_claim):
    idp_a,_,_,trust,_,_=security
    with pytest.raises(SyntheticGrowthError):
        trust.verify(sign_idp(idp_a,changes=bad_claim),now=NOW)


@pytest.mark.parametrize("bad_header",[
    {"alg":"none"},{"alg":"HS256"},{"kid":"ci-key-unknown"},
    {"typ":"JWE"},{"jku":"https://evil.invalid/jwks.json"},
])
def test_jose_header_pin_enforced(security,bad_header):
    idp_a,_,_,trust,_,_=security
    with pytest.raises(SyntheticGrowthError):
        trust.verify(sign_idp(idp_a,head_changes=bad_header),now=NOW)


def test_token_signature_not_trust_claimed_membership_or_second_signer(security):
    idp_a,idp_b,app,trust,store,gateway=security
    wrong=sign_idp(idp_b,kid="ci-key-one")
    with pytest.raises(SyntheticGrowthError):
        trust.verify(wrong,now=NOW)
    with pytest.raises(SyntheticGrowthError):
        gateway.portfolio(sign_idp(idp_a),sign_app(app,sub="SIM-SUB-SEC01"))
    with pytest.raises(SyntheticGrowthError):
        gateway.portfolio(sign_idp(idp_a),sign_app(app,changes={"role":"auditor"}))
    with pytest.raises(SyntheticGrowthError):
        gateway.portfolio(sign_idp(idp_a),sign_app(app,changes={"workspace":"bespoke_demo"}))
    with pytest.raises(SyntheticGrowthError):
        gateway.portfolio(sign_idp(idp_a,sub="SIM-SUB-BES01"),sign_app(app))
    assert store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0]==0


def test_second_key_rotation_revocation_and_duplicate_signed_fields(security):
    idp_a,idp_b,app,trust,_,gateway=security
    old=sign_idp(idp_a)
    new=sign_idp(idp_b,kid="ci-key-two")
    assert trust.verify(old,now=NOW).key_id=="ci-key-one"
    assert trust.verify(new,now=NOW).key_id=="ci-key-two"
    key_revoked=trust.with_revocation(kid="ci-key-one")
    with pytest.raises(SyntheticGrowthError):
        key_revoked.verify(old,now=NOW)
    assert key_revoked.verify(new,now=NOW).key_id=="ci-key-two"
    jti=trust.verify(new,now=NOW).token_ref
    with pytest.raises(SyntheticGrowthError):
        trust.with_revocation(jti=jti).verify(new,now=NOW)
    # The signed JSON cannot repeat subject and sneak an altered membership.
    duplicate_payload=(
        b'{"iss":"https://offline-idp.metaautomate.invalid/",'
        b'"iss":"https://malicious.invalid/"}'
    )
    with pytest.raises(SyntheticGrowthError):
        trust.verify(sign_idp(idp_a,payload=duplicate_payload),now=NOW)
    # A changed trust view is applied on gateway's next operation.
    gateway.trust=key_revoked
    with pytest.raises(SyntheticGrowthError):
        gateway.portfolio(old,sign_app(app))


def test_complete_tenant_gated_two_person_approval_and_virtual_tool(security):
    idp_a,_,app,trust,store,gateway=security
    owner_jwt,owner_app=sign_idp(idp_a),sign_app(app)
    reviewer_jwt,reviewer_app=(
        sign_idp(idp_a,sub="SIM-SUB-SEC01"),
        sign_app(app,sub="SIM-SUB-SEC01"))
    auditor_jwt,auditor_app=(
        sign_idp(idp_a,sub="SIM-SUB-AUD01"),
        sign_app(app,sub="SIM-SUB-AUD01"))
    ref="SIM-PLAN-AUTHORIZED"
    assert gateway.propose(owner_jwt,owner_app,ref,"CONTENT_OPERATIONS")["state"]=="DRAFT"
    with pytest.raises(SyntheticGrowthError):
        gateway.simulate(owner_jwt,owner_app,ref)
    gateway.owner_approve(owner_jwt,owner_app,ref)
    with pytest.raises(SyntheticGrowthError):
        gateway.security_approve(owner_jwt,owner_app,ref)
    assert gateway.security_approve(reviewer_jwt,reviewer_app,ref)["state"]=="SECURITY_APPROVED"
    decision=gateway.review_virtual_tool(
        reviewer_jwt,reviewer_app,ref,
        "marketing","GENERATE_REVIEW_PLAN","PREPARE_HUMAN_DECISION")
    assert decision["review_state"]=="VIRTUAL_REVIEW_ONLY"
    assert decision["actual_tool_calls"]==0 and decision["network_calls"]==0
    assert not decision["actual_execution_authorized"]
    for module,tool,purpose in (
        ("finance","GENERATE_REVIEW_PLAN","PREPARE_HUMAN_DECISION"),
        ("marketing","SEND_MESSAGE","PREPARE_HUMAN_DECISION"),
        ("marketing","ANALYZE_SAMPLE","SEND_LIVE_DM"),
        ("not_a_module","ANALYZE_SAMPLE","REVIEW_BUSINESS_EVIDENCE"),
    ):
        with pytest.raises(SyntheticGrowthError):
            gateway.review_virtual_tool(
                reviewer_jwt,reviewer_app,ref,module,tool,purpose)
    trace=gateway.simulate(owner_jwt,owner_app,ref)
    assert trace["completed_internal_simulations"]==3
    assert trace["external_actions_attempted"]==0
    assert not trace["live_workflow_started"]
    assert gateway.audit(auditor_jwt,auditor_app)["chain_consistent"]
    # Test IdP key revocation changes behavior even if app token remains valid.
    gateway.trust=trust.with_revocation(kid="ci-key-one")
    with pytest.raises(SyntheticGrowthError):
        gateway.portfolio(owner_jwt,owner_app)
    with pytest.raises(SyntheticGrowthError):
        gateway.audit(auditor_jwt,auditor_app)


def test_idp_and_app_signatures_must_remain_different_confidence_layers(security):
    idp_a,idp_b,app,trust,store,gateway=security
    with pytest.raises(SyntheticGrowthError):
        gateway.propose(sign_idp(idp_a),sign_app(app,changes={
            "actor_ref":"SIM-ACTOR-ADMIN02"}),
            "SIM-PLAN-FAIL","LEAD_QUALIFICATION")
    assert store.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]==0
