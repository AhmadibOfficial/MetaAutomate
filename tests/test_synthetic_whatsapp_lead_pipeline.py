"""P2-03p WhatsApp policy-first synthetic scenario and adversarial validation."""
import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_whatsapp_lead_pipeline import (
    FIXTURE, build_committed_whatsapp_pipeline, evaluate_whatsapp_lead,
    parse_whatsapp_fixture,
)


def raw(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fixture():
    return json.loads(FIXTURE.read_bytes())


def test_no_real_contacts_no_messages_no_conversion_claims():
    result = build_committed_whatsapp_pipeline()
    assert result == build_committed_whatsapp_pipeline()
    assert len(result["stages"]) == 4
    assert result["metrics"]["actual_messages_sent"] == 0
    assert result["metrics"]["actual_conversion_rate"] is None
    assert result["metrics"]["marketing_open_rate_claim"] is None
    assert result["gates"]["messaging_active"] is False
    assert result["gates"]["real_contact_records"] is False
    assert result["gates"]["verified_provider_attribution"] is False
    assert all(not lead["customer_identity_verified"] and
               not lead["outbound_dispatch_enabled"] and
               not lead["real_consent_verified"] for lead in result["leads"])
    assert all("phone" not in str(lead).lower() and
               "email" not in str(lead).lower() for lead in result["leads"])


def test_source_scope_isolated():
    all_leads = build_committed_whatsapp_pipeline()["leads"]
    for workspace in ("academy_demo", "bespoke_demo"):
        report = build_committed_whatsapp_pipeline(workspace)
        assert all(x["workspace"] == workspace for x in report["leads"])
        assert len(report["leads"]) == len([x for x in all_leads
                                             if x["workspace"] == workspace])
    with pytest.raises(SyntheticGrowthError):
        build_committed_whatsapp_pipeline("invalid")


def test_inbound_service_replies_require_open_window():
    scenario = fixture()
    user = scenario["leads"][0]
    current = evaluate_whatsapp_lead(user, scenario["evaluated_at"])
    assert current["customer_service_window_open"] is True
    assert current["recommended_next_step"] == "REVIEW_IN_WINDOW_SERVICE_REPLY"
    assert current["human_route"] == "HUMAN_HANDOVER_REVIEW"
    user["last_user_message_at"] = "2026-10-15T09:00:00Z"  # 24h exactly
    expired = evaluate_whatsapp_lead(user, scenario["evaluated_at"])
    assert expired["customer_service_window_open"] is False
    assert expired["recommended_next_step"] == "HOLD_NO_AUTHORIZED_MESSAGE_PATH"


def test_approved_template_needs_purpose_consent_even_outside_window():
    scenario = fixture()
    user = scenario["leads"][1]
    assert evaluate_whatsapp_lead(user, scenario["evaluated_at"])["recommended_next_step"] == "REVIEW_APPROVED_TEMPLATE_ONLY"
    user["optin"]["marketing"] = False
    assert evaluate_whatsapp_lead(user, scenario["evaluated_at"])["recommended_next_step"] == "HOLD_NO_AUTHORIZED_MESSAGE_PATH"
    user["optin"]["marketing"] = True
    user["template_state"] = "PENDING"
    assert evaluate_whatsapp_lead(user, scenario["evaluated_at"])["recommended_next_step"] == "HOLD_NO_AUTHORIZED_MESSAGE_PATH"
    user["template_state"] = "APPROVED"
    user["opted_out"] = True
    assert evaluate_whatsapp_lead(user, scenario["evaluated_at"])["recommended_next_step"] == "SUPPRESS_OPT_OUT"


def test_click_is_not_inbound_chat_or_consent():
    scenario = fixture()
    user = scenario["leads"][3]
    status = evaluate_whatsapp_lead(user, scenario["evaluated_at"])
    assert status["inbound_conversation"] is False
    assert status["recommended_next_step"] == "NO_MESSAGE_NO_CONTACT"
    assert status["human_route"] == "NOT_A_LEAD"
    assert status["source_attribution"] == "SIMULATED_UNVERIFIED"


def test_wrong_purpose_consent_is_not_messaging_authorization():
    report = build_committed_whatsapp_pipeline()
    denied = next(x for x in report["leads"] if x["lead_id"] == "SIM-LEAD-EDU-03")
    assert denied["recommended_next_step"] == "HOLD_NO_AUTHORIZED_MESSAGE_PATH"


@pytest.mark.parametrize("raw_bytes", [
    b"", b"{}", b"not json", b'{"schema_version":1,"schema_version":1}',
    b'{"value":3.14}', b'{"a":NaN}', b"\x00" * 100, b"x" * 25_000
])
def test_malformed_or_nonfinite_fixture_rejected(raw_bytes):
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw_bytes)


def test_unknown_fields_and_personal_contacts_fail_closed():
    for key, val in (("phone_number", "+2348000000000"),
                     ("email", "fake@example.invalid"),
                     ("wa_id", "000000000000")):
        obj = fixture()
        obj["leads"][0][key] = val
        with pytest.raises(SyntheticGrowthError):
            parse_whatsapp_fixture(raw(obj))


def test_duplicate_leads_cross_source_and_future_timestamp_rejected():
    obj = fixture()
    obj["leads"][1]["lead_id"] = obj["leads"][0]["lead_id"]
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))
    obj = fixture()
    obj["leads"][0]["source_reference"] = "SIM-QR-EDU-01"
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))
    obj = fixture()
    obj["leads"][0]["last_user_message_at"] = "2026-10-17T09:00:00Z"
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))


def test_no_optin_from_link_click_and_no_blank_consent_evidence():
    obj = fixture()
    obj["leads"][3]["optin"]["marketing"] = True
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))
    obj = fixture()
    obj["leads"][0]["optin"]["marketing"] = True
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))


def test_qualification_is_bounded_not_sensitive():
    obj = fixture()
    obj["leads"][0]["qualification"]["medical_history"] = "none"
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))
    obj = fixture()
    obj["leads"][0]["qualification"]["budget_band"] = 100000
    with pytest.raises(SyntheticGrowthError):
        parse_whatsapp_fixture(raw(obj))
