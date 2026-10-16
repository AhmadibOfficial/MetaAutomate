"""P2-03r: signed event gate, account/tenant isolation, in-memory consent & handover."""
from copy import deepcopy
from hashlib import sha256
import hmac
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_meta_lead_federation import (
    REGISTRY, inspect_signed_meta_event, permission_readiness, SyntheticMetaReviewLedger,
    MAX_RAW_BYTES,
)

SECRET = b"synthetic-ci-only-test-key-2026"


def raw(doc):
    return json.dumps(doc, separators=(",", ":"), sort_keys=True).encode()


def signed(body, secret=SECRET):
    return "sha256=" + hmac.new(secret, body, "sha256").hexdigest()


def page(account="SIM-PAGE-ACADEMY", lead="SIM-FB-LEAD-01"):
    return {"object": "page", "entry": [{"id": account, "changes": [
        {"field": "leadgen", "value": {"leadgen_id": lead,
                                     "form_id": "SIM-FORM-ACADEMY", "page_id": account}}
    ]}]}


def instagram():
    return {"object": "instagram", "entry": [{"id": "SIM-IG-BESPOKE",
                                               "messaging": [
                                                   {"message": {"mid": "SIM-IG-MSG-01"}}]}]}


def whatsapp():
    return {"object": "whatsapp_business_account",
            "entry": [{"id": "SIM-WABA-ACADEMY", "changes": [
                {"field": "messages", "value": {
                    "messages": [{"id": "SIM-WA-MSG-01"}]}}
            ]}]}


@pytest.mark.parametrize("document,workspace,platform,kind", [
    (page(), "academy_demo", "FACEBOOK", "SUBMITTED_LEAD_FORM_METADATA"),
    (instagram(), "bespoke_demo", "INSTAGRAM", "INBOUND_DM_METADATA"),
    (whatsapp(), "academy_demo", "WHATSAPP", "INBOUND_WHATSAPP_METADATA"),
])
def test_signed_channel_input_is_minimal_and_review_only(document, workspace, platform, kind):
    body = raw(document)
    result = inspect_signed_meta_event(body, signed(body), SECRET,
                                       expected_workspace=workspace)
    assert result["signature_check"] == "LOCAL_HMAC_PASSED"
    assert result["provider_permissions_verified"] is False
    assert result["live_webhook_endpoint"] is False
    assert result["messages_sent"] == 0
    assert result["database_writes"] == 0
    event = result["events"][0]
    assert event["platform"] == platform
    assert event["kind"] == kind
    assert event["workspace"] == workspace
    assert event["customer_contact"] is None
    assert event["outbound_eligible"] is False
    assert event["consent_verified"] is False


def test_signature_must_be_valid_before_parsing_or_account_lookup():
    invalid = b'{"object":"page","entry":THIS_IS_MALFORMED}'
    with pytest.raises(SyntheticGrowthError, match="signed webhook"):
        inspect_signed_meta_event(invalid, "sha256=" + "0"*64, SECRET,
                                  expected_workspace="academy_demo")
    body = raw(page())
    for replacement in [body + b" ", body[:-1] + b"]", body + b"\n"]:
        with pytest.raises(SyntheticGrowthError):
            inspect_signed_meta_event(replacement, signed(body), SECRET,
                                      expected_workspace="academy_demo")
    assert body.decode().find("phone") == -1


def test_attacker_account_claim_and_tenant_mismatch_rejected():
    body = raw(page())
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="bespoke_demo")
    forged = page("SIM-PAGE-UNKNOWN")
    body = raw(forged)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")
    mismatch = page()
    mismatch["entry"][0]["changes"][0]["value"]["page_id"] = "SIM-PAGE-BESPOKE"
    body = raw(mismatch)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")


@pytest.mark.parametrize("extra_field", [
    "email", "phone_number", "full_name", "message_text", "ig_username",
    "lead_data", "access_token", "messaging_consent", "customer_id",
])
def test_unexpected_personal_data_fields_denied(extra_field):
    document = page()
    document["entry"][0]["changes"][0]["value"][extra_field] = "unsafe"
    body = raw(document)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")


def test_meta_page_only_leadgen_change_accepted():
    document = page()
    document["entry"][0]["changes"][0]["field"] = "feed"
    body = raw(document)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")


def test_instagram_does_not_accept_raw_sender_data():
    document = instagram()
    document["entry"][0]["messaging"][0]["sender"] = {"id": "fake"}
    body = raw(document)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="bespoke_demo")


def test_whatsapp_does_not_store_contacts_or_message_bodies():
    document = whatsapp()
    document["entry"][0]["changes"][0]["value"]["contacts"] = [{"wa_id": "123"}]
    body = raw(document)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")
    document = whatsapp()
    document["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = "hello"
    body = raw(document)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")


def test_unexpected_json_types_duplicate_keys_and_oversized_batches_fail_closed():
    cases = [
        b"{}", b"[]", b"", b"\x00",
        b'{"object":"page","object":"page","entry":[]}',
        b'{"object":"page","entry":1.1}',
        b'{"object":"page","entry":NaN}',
        raw({"object":"page","entry":[]}),
        raw({"object":"page","entry":[{"id":"SIM-PAGE-ACADEMY","changes":[] }]}),
        b"{" + b"x" * MAX_RAW_BYTES,
    ]
    for body in cases:
        with pytest.raises(SyntheticGrowthError):
            inspect_signed_meta_event(body, signed(body), SECRET,
                                      expected_workspace="academy_demo")


def test_repeated_event_in_batch_rejected():
    doc = page()
    doc["entry"][0]["changes"].append(deepcopy(doc["entry"][0]["changes"][0]))
    body=raw(doc)
    with pytest.raises(SyntheticGrowthError):
        inspect_signed_meta_event(body, signed(body), SECRET,
                                  expected_workspace="academy_demo")


def test_in_memory_dedupe_tenant_scope_human_route_and_audit():
    body=raw(page())
    inspection=inspect_signed_meta_event(body, signed(body), SECRET,
                                         expected_workspace="academy_demo")
    ledger=SyntheticMetaReviewLedger("academy_demo")
    assert ledger.receive(inspection) == 1
    assert ledger.receive(inspection) == 1  # idempotent: no new task
    assert len(ledger.tasks()) == 1
    task=ledger.assign_human("FACEBOOK", "SIM-FB-LEAD-01", "SIM-AGENT-01")
    assert task["assigned_agent"] == "SIM-AGENT-01"
    assert task["state"] == "ASSIGNED_SYNTHETIC_HUMAN"
    assert task["automatic_followup"] is False
    with pytest.raises(SyntheticGrowthError):
        ledger.assign_human("FACEBOOK", "SIM-FB-LEAD-01", "SIM-AGENT-01")
    first=ledger.record_consent_review("SIM-FB-LEAD-01","MARKETING",
                                       "UNVERIFIED","SIM-EVID-01","SIM-AGENT-01")
    second=ledger.record_consent_review("SIM-FB-LEAD-01","MARKETING",
                                        "REVOKED_EXAMPLE","SIM-EVID-02","SIM-AGENT-01")
    assert second.previous_sha256 == first.sha256
    assert ledger.consent_review("SIM-FB-LEAD-01","MARKETING") == "REVOKED_EXAMPLE"
    with pytest.raises(SyntheticGrowthError):
        ledger.record_consent_review("SIM-FB-LEAD-01","MARKETING",
                                     "GRANTED_EXAMPLE","SIM-EVID-03","SIM-AGENT-01")
    assert ledger.summary()["actual_customer_records"] == 0
    assert ledger.summary()["authenticated_agents"] == 0
    assert ledger.summary()["live_storage"] is False
    assert ledger.summary()["messages_sent"] == 0


def test_no_cross_workspace_ledger_ingest_consent_or_agents():
    b=raw(instagram())
    insp=inspect_signed_meta_event(b,signed(b),SECRET,
                                   expected_workspace="bespoke_demo")
    with pytest.raises(SyntheticGrowthError):
        SyntheticMetaReviewLedger("academy_demo").receive(insp)
    ledger=SyntheticMetaReviewLedger("bespoke_demo")
    ledger.receive(insp)
    with pytest.raises(SyntheticGrowthError):
        ledger.record_consent_review("SIM-FB-LEAD-01","MARKETING",
                                     "UNVERIFIED","SIM-EVID-01","SIM-AGENT-01")
    with pytest.raises(SyntheticGrowthError):
        ledger.assign_human("INSTAGRAM","SIM-IG-MSG-01","real-agent@example.com")


def test_permission_checklist_cannot_activate_provider_even_if_all_true():
    for channel in ("FACEBOOK","INSTAGRAM","WHATSAPP"):
        pending=permission_readiness(channel)
        assert pending["missing"] and not pending["release_authorized"]
        complete=permission_readiness(channel,{x: True for x in pending["requirements"]})
        assert not complete["missing"]
        assert complete["checklist_complete_in_example"]
        assert not complete["independent_meta_grants_verified"]
        assert not complete["release_authorized"]
        assert complete["operational_status"] == "NO_GO"
        with pytest.raises(SyntheticGrowthError):
            permission_readiness(channel, {"PRODUCTION_GO": True})
        with pytest.raises(SyntheticGrowthError):
            permission_readiness(channel, {pending["requirements"][0]: 1})


def test_registry_contains_three_platforms_and_separated_accounts():
    assert len(REGISTRY)==6
    assert {key[0] for key in REGISTRY} == {
        "page","instagram","whatsapp_business_account"
    }
    assert set(REGISTRY.values()) == {"academy_demo","bespoke_demo"}
