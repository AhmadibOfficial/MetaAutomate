"""P2-03q: negative tests for Meta Instagram acquisition and messaging boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_instagram_lead_pipeline import (
    FIXTURE, parse_instagram_fixture, evaluate_instagram_record,
    build_committed_instagram_pipeline,
)


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def row(event_id):
    return next(x for x in fixture()["records"] if x["event_id"] == event_id)


def test_all_routes_no_real_contacts_or_provider_calls():
    p=build_committed_instagram_pipeline()
    assert p == build_committed_instagram_pipeline()
    assert len(p["events"]) == 9
    assert len(p["stages"]) == 4
    assert p["metrics"]["actual_leads_captured"] == 0
    assert p["metrics"]["actual_messages_sent"] == 0
    assert p["controls"]["production_go"] is False
    assert p["permissions"]["webhook_signature_validation_active"] is False
    assert not any(e["provider_message_sent"] or e["outbound_action_authorized"]
                   or e["real_crm_write"] for e in p["events"])
    assert all(not e["customer_identity_verified"] and
               not e["campaign_attribution_verified"] for e in p["events"])


def test_form_submission_does_not_grant_dm_or_marketing_permission():
    f=fixture()
    submitted=evaluate_instagram_record(row("SIM-IG-01"),f["evaluated_at"])
    assert submitted["next_step"]=="LEAD_FORM_CRM_REVIEW"
    assert submitted["submitted_form"] is True
    assert submitted["ordinary_dm_window_in_example"] is False
    assert submitted["marketing_optin_example"] is False
    unsubmitted=evaluate_instagram_record(row("SIM-IG-07"),f["evaluated_at"])
    assert unsubmitted["next_step"]=="NO_SUBMISSION_NO_LEAD"


def test_organic_dm_24_hour_window_and_expiry():
    f=fixture()
    r=row("SIM-IG-02")
    assert evaluate_instagram_record(r,f["evaluated_at"])["next_step"]=="REVIEW_INBOUND_DM_WITHIN_24H"
    r["last_user_message_at"]="2026-10-15T09:00:00Z" # exactly 24 hours
    assert evaluate_instagram_record(r,f["evaluated_at"])["next_step"]=="HOLD_DM_WINDOW_CLOSED"


def test_ad_origin_may_offer_longer_review_not_permission():
    f=fixture()
    r=row("SIM-IG-05")
    d=evaluate_instagram_record(r,f["evaluated_at"])
    assert d["next_step"]=="REVIEW_AD_WINDOW_ONLY_IF_ORIGIN_VERIFIED"
    assert d["ad_origin_extended_window_possible"]
    assert not d["campaign_attribution_verified"] and not d["outbound_action_authorized"]
    r["first_ad_message_at"]="2026-10-09T09:00:00Z" # exactly seven days
    r["last_user_message_at"]="2026-10-12T09:10:00Z"
    assert evaluate_instagram_record(r,f["evaluated_at"])["next_step"]=="HOLD_DM_WINDOW_CLOSED"


def test_comment_one_private_reply_not_open_ended_dm():
    f=fixture()
    d=evaluate_instagram_record(row("SIM-IG-03"),f["evaluated_at"])
    assert d["next_step"]=="REVIEW_SINGLE_PRIVATE_REPLY_ONLY"
    assert not d["lead_in_example"]
    assert not d["outbound_action_authorized"]
    assert evaluate_instagram_record(row("SIM-IG-04"),f["evaluated_at"])["next_step"]=="HOLD_COMMENT_REPLY_INELIGIBLE"
    assert evaluate_instagram_record(row("SIM-IG-09"),f["evaluated_at"])["next_step"]=="HOLD_COMMENT_REPLY_INELIGIBLE"


def test_link_click_not_lead_or_inbound():
    f=fixture()
    d=evaluate_instagram_record(row("SIM-IG-06"),f["evaluated_at"])
    assert d["next_step"]=="NO_SUBMISSION_NO_CHAT"
    assert not d["lead_in_example"]


def test_optout_overrides_inbound_and_marketing():
    f=fixture()
    d=evaluate_instagram_record(row("SIM-IG-08"),f["evaluated_at"])
    assert d["next_step"]=="SUPPRESS_OPT_OUT"


def test_tenant_filter_and_unknown_scope():
    for workspace in ("academy_demo","bespoke_demo"):
        result=build_committed_instagram_pipeline(workspace)
        assert all(e["workspace"]==workspace for e in result["events"])
    with pytest.raises(SyntheticGrowthError):
        build_committed_instagram_pipeline("different_tenant")


@pytest.mark.parametrize("bad",[b"",b"{}",b"not-json",
    b'{"schema_version":1,"schema_version":1}',
    b'{"count":NaN}',b'{"count":2.5}',b"\x00"*10,b"x"*25000])
def test_bad_json_denied(bad):
    with pytest.raises(SyntheticGrowthError):
        parse_instagram_fixture(bad)


@pytest.mark.parametrize("field,value",[
    ("email","example@example.test"),
    ("phone","+234000000000"),
    ("instagram_username","someperson"),
    ("access_token","should-not-exist"),
    ("wa_id","123"),
])
def test_real_person_identifiers_rejected(field,value):
    doc=fixture()
    doc["records"][0][field]=value
    with pytest.raises(SyntheticGrowthError):
        parse_instagram_fixture(encode(doc))


def test_cross_channel_forgery_and_duplicate_event_rejected():
    doc=fixture()
    doc["records"][0]["channel"]="ORGANIC_DM"
    with pytest.raises(SyntheticGrowthError):
        parse_instagram_fixture(encode(doc))
    doc=fixture()
    doc["records"][1]["event_id"]=doc["records"][0]["event_id"]
    with pytest.raises(SyntheticGrowthError):
        parse_instagram_fixture(encode(doc))


def test_ad_window_cannot_be_claimed_by_organic_dm():
    doc=fixture()
    doc["records"][1]["first_ad_message_at"]="2026-10-12T09:00:00Z"
    with pytest.raises(SyntheticGrowthError):
        parse_instagram_fixture(encode(doc))


def test_form_submission_not_unlimited_messaging():
    doc=fixture()
    doc["records"][0]["last_user_message_at"]="2026-10-16T08:40:00Z"
    with pytest.raises(SyntheticGrowthError):
        parse_instagram_fixture(encode(doc))


def test_source_data_has_no_real_world_pii():
    raw=FIXTURE.read_text(encoding="utf-8").lower()
    for word in ('"email"','"phone"','"username"','"access_token"','"full_name"','"ig_user_id"'):
        assert word not in raw
