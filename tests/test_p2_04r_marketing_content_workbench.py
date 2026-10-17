"""P2-04r marketing source-only policy tests. Zero LLM or publishing APIs."""
import pytest

from app.marketing_content_workbench import ContentHold, KINDS, create_campaign, inspect_candidate

def brief():
    return {
        "campaign_id":"metareach_october",
        "brand":"MetaAutomate",
        "industry":"Business automation and AI",
        "offer":"Secure digital workflows for business teams",
        "audience":"Small business owners and startup founders",
        "goal":"Explain product value without promising income",
        "channels":["instagram","website"],
        "verified_facts":[
            {"claim":"The company develops AI and automation capabilities.",
             "source_reference":"Approved internal company positioning"},
            {"claim":"Real customer-facing AI film generation is not yet released.",
             "source_reference":"P2-04 project acceptance register"},
        ],
        "approved_cta":"Explore what MetaAutomate is building",
        "content_kinds":list(KINDS),
        "country":"Nigeria",
        "evidence_owner":"content_reviewer",
    }

def test_all_eight_content_formats_are_available_as_drafts():
    result=create_campaign(brief())
    assert len(result["work_orders"])==16
    assert {x["content_kind"] for x in result["work_orders"]}==set(KINDS)
    assert all(x["status"]=="DRAFT_UNGENERATED" for x in result["work_orders"])
    assert all(x["external_action_authorized"] is False for x in result["work_orders"])
    assert result["generation_engine_connected"] is False
    assert result["publication_authorized"] is False

def test_facts_cited_inside_each_prompt():
    result=create_campaign(brief())
    for item in result["work_orders"]:
        assert "approved internal company positioning" in item["prompt"].lower()
        assert "Never invent prices" in item["prompt"]
        assert "No model invocation" in item["prompt"]

def test_campaign_id_and_content_scope_are_deterministic():
    one=create_campaign(brief())
    two=create_campaign(brief())
    assert one["brief_sha256"]==two["brief_sha256"]
    assert one["work_orders"]==two["work_orders"]

@pytest.mark.parametrize("field,value",[
    ("channels",["instagram","instagram"]),
    ("channels",["unapproved_platform"]),
    ("content_kinds",["unknown"]),
    ("content_kinds",["social","social"]),
    ("verified_facts",[]),
    ("approved_cta",""),
    ("brand",123),
    ("campaign_id","../outside"),
])
def test_bad_campaigns_blocked(field,value):
    candidate=brief()
    candidate[field]=value
    with pytest.raises(ContentHold):
        create_campaign(candidate)

def test_unsourced_fact_blocked():
    candidate=brief()
    candidate["verified_facts"]=[{"claim":"Guaranteed 100% revenue growth"}]
    with pytest.raises(ContentHold):
        create_campaign(candidate)

def test_extra_hidden_command_blocked():
    candidate=brief()
    candidate["publish_now"]=True
    with pytest.raises(ContentHold):
        create_campaign(candidate)

def test_human_claim_does_not_enable_publishing():
    campaign=create_campaign(brief())
    result=inspect_candidate(campaign,
        "metareach_october:social:instagram",
        "MetaAutomate develops AI and automation solutions. Explore our work today.",
        evidence_checked=True,rights_checked=False)
    assert result["review_status"]=="HUMAN_REVIEW_CLAIM_RECORDED_NOT_PUBLISHED"
    assert result["publication_authorized"] is False
    assert result["actual_model_execution_verified"] is False

def test_video_requires_rights_review():
    campaign=create_campaign(brief())
    result=inspect_candidate(campaign,
        "metareach_october:video:instagram",
        "A source-based video concept with original visuals and properly licensed music.",
        evidence_checked=True,rights_checked=False)
    assert result["review_status"]=="HOLD_UNVERIFIED_DRAFT"

def test_unknown_work_order_rejected():
    campaign=create_campaign(brief())
    with pytest.raises(ContentHold,match="Unknown"):
        inspect_candidate(campaign,"not-a-job",
            "A valid thirty-character draft for manual review.",
            evidence_checked=True,rights_checked=True)

def test_short_draft_rejected():
    campaign=create_campaign(brief())
    with pytest.raises(ContentHold):
        inspect_candidate(campaign,"metareach_october:social:instagram",
            "short",evidence_checked=True,rights_checked=True)
