"""P2-03q: Instagram acquisition/DM policy lab — synthetic and non-operational.

Meta docs:
https://developers.facebook.com/documentation/instagram-platform/private-replies
https://developers.facebook.com/documentation/business-messaging/messenger-platform/policy
https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/

All recommendations are HUMAN REVIEW ONLY, NEVER a send authorization.
No names, Meta IDs, emails, phone numbers, tokens, signed webhooks, customer data or outbound calls.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any

from .synthetic_growth_autopilot import SyntheticGrowthError

FIXTURE = (Path(__file__).resolve().parents[3] /
           "contracts/domains/v1/fixtures/synthetic_instagram_leads.v1.json")
WORKSPACES = frozenset({"academy_demo", "bespoke_demo"})
CHANNELS = frozenset({"INSTANT_FORM", "ORGANIC_DM", "CLICK_TO_DIRECT", "COMMENT_KEYWORD", "LINK_IN_BIO"})
RECORD_FIELDS = frozenset({
    "workspace", "event_id", "channel", "source_ref", "submitted",
    "last_user_message_at", "first_ad_message_at", "comment_at",
    "private_reply_used", "keyword_match", "has_marketing_optin", "opted_out",
    "qualification", "agent_available",
})
QUESTION_VALUES = {
    "interest": frozenset({"COURSES", "FASHION"}),
    "budget_band": frozenset({"LOW", "MEDIUM", "HIGH", "UNKNOWN"}),
    "location_band": frozenset({"LOCAL", "REMOTE", "UNKNOWN"}),
    "timeline": frozenset({"NOW", "SOON", "LATER", "UNKNOWN"}),
}
MAX_BYTES = 24_576
MAX_RECORDS = 30
SOURCE_PREFIX = {
    "INSTANT_FORM": "SIM-CAMPAIGN-",
    "ORGANIC_DM": "SIM-PROFILE-",
    "CLICK_TO_DIRECT": "SIM-IGAD-",
    "COMMENT_KEYWORD": "SIM-MEDIA-",
    "LINK_IN_BIO": "SIM-BIO-",
}
IDENTIFIER = re.compile(r"SIM-[A-Z0-9-]{3,48}\Z")
DM_WINDOW = timedelta(hours=24)
COMMENT_PRIVATE_REPLY_WINDOW = timedelta(days=7)
AD_WINDOW_UPPER_BOUND = timedelta(days=7)


def _require(predicate: bool, reason: str) -> None:
    if not predicate:
        raise SyntheticGrowthError(reason)


def _exact(value: Any, expected: frozenset | set, name: str) -> dict:
    _require(type(value) is dict and set(value) == expected, "Invalid fields: " + name)
    return value


def _pairs(values: list[tuple[str, Any]]) -> dict:
    result = {}
    for name, item in values:
        _require(name not in result, "Repeated Instagram fixture field")
        result[name] = item
    return result


def _bad_float(value: str) -> None:
    raise SyntheticGrowthError("Floating or non-finite values prohibited")


def _utc(text: Any, now: datetime | None = None) -> datetime:
    _require(type(text) is str and len(text) == 20 and text.endswith("Z"),
             "Canonical UTC timestamp required")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SyntheticGrowthError("Invalid UTC timestamp") from exc
    if now is not None:
        _require(parsed <= now, "Future events are invalid")
    return parsed


def parse_instagram_fixture(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\x00" not in raw,
             "Invalid synthetic input")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_float=_bad_float, parse_constant=_bad_float)
    except SyntheticGrowthError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed Instagram fixture") from exc
    _exact(doc, {"schema_version", "classification", "evaluated_at", "records"}, "root")
    _require(type(doc["schema_version"]) is int and doc["schema_version"] == 1
             and doc["classification"] == "SYNTHETIC_SOURCE_ONLY",
             "Unsupported Instagram source type")
    now = _utc(doc["evaluated_at"])
    records = doc["records"]
    _require(type(records) is list and 1 <= len(records) <= MAX_RECORDS, "Invalid count")
    ids = set()
    for event in records:
        _exact(event, RECORD_FIELDS, "record")
        _require(type(event["workspace"]) is str and event["workspace"] in WORKSPACES,
                 "Cross-workspace source")
        event_id, channel, ref = event["event_id"], event["channel"], event["source_ref"]
        _require(type(event_id) is str and IDENTIFIER.fullmatch(event_id) is not None
                 and event_id.startswith("SIM-IG-") and event_id not in ids, "Invalid ID")
        ids.add(event_id)
        _require(type(channel) is str and channel in CHANNELS
                 and type(ref) is str and IDENTIFIER.fullmatch(ref) is not None
                 and ref.startswith(SOURCE_PREFIX[channel]), "Unknown acquisition source")
        for field in ("submitted", "private_reply_used", "keyword_match",
                      "has_marketing_optin", "opted_out", "agent_available"):
            _require(type(event[field]) is bool, "Invalid boolean: " + field)
        answers = _exact(event["qualification"], set(QUESTION_VALUES), "qualification")
        for field, accepted in QUESTION_VALUES.items():
            _require(type(answers[field]) is str and answers[field] in accepted,
                     "Invalid qualification value: " + field)
        for field in ("last_user_message_at", "first_ad_message_at", "comment_at"):
            if event[field] is not None:
                _utc(event[field], now)
        inbound = event["last_user_message_at"]
        first_ad = event["first_ad_message_at"]
        commented = event["comment_at"]
        if channel == "INSTANT_FORM":
            _require(inbound is None and first_ad is None and commented is None
                     and not event["private_reply_used"] and not event["keyword_match"],
                     "A lead form does not open a DM")
        elif channel in ("ORGANIC_DM", "CLICK_TO_DIRECT"):
            _require(inbound is not None and commented is None
                     and not event["submitted"] and not event["keyword_match"]
                     and not event["private_reply_used"], "DM must be inbound")
            if channel == "CLICK_TO_DIRECT":
                _require(first_ad is not None and _utc(first_ad, now) <= _utc(inbound, now),
                         "Ad conversation timestamp required")
            else:
                _require(first_ad is None, "Organic source cannot claim ad window")
        elif channel == "COMMENT_KEYWORD":
            _require(commented is not None and first_ad is None and inbound is None
                     and not event["submitted"], "Comment is not a DM")
        elif channel == "LINK_IN_BIO":
            _require(inbound is None and first_ad is None and commented is None
                     and not event["submitted"] and not event["keyword_match"]
                     and not event["private_reply_used"], "Bio click is not a lead")
        if channel in ("COMMENT_KEYWORD", "LINK_IN_BIO") or (
            channel == "INSTANT_FORM" and not event["submitted"]
        ):
            _require(all(answers[key] == "UNKNOWN"
                         for key in ("budget_band", "location_band", "timeline")),
                     "Engagement/click alone cannot provide answers")
    return doc


def evaluate_instagram_record(event: dict, evaluated_at: str) -> dict:
    """Only accepts validated-shaped records. All provider eligibility unverified."""
    # parse the record through the same complete strict parser to prevent policy
    # bypass via additional fields or unverified input.
    example = {"schema_version": 1, "classification": "SYNTHETIC_SOURCE_ONLY",
               "evaluated_at": evaluated_at, "records": [event]}
    validated = parse_instagram_fixture(
        json.dumps(example, sort_keys=True, ensure_ascii=True,
                   separators=(",", ":"), allow_nan=False).encode("utf-8"))
    row = validated["records"][0]
    now = _utc(validated["evaluated_at"])
    channel = row["channel"]
    inbound = row["last_user_message_at"]
    comment = row["comment_at"]
    within_dm = bool(inbound and now - _utc(inbound, now) < DM_WINDOW)
    within_comment = bool(comment and now - _utc(comment, now) < COMMENT_PRIVATE_REPLY_WINDOW)
    ad_window = bool(channel == "CLICK_TO_DIRECT"
                     and now - _utc(row["first_ad_message_at"], now) < AD_WINDOW_UPPER_BOUND)
    complete = all(x != "UNKNOWN" for x in row["qualification"].values())
    if row["opted_out"]:
        next_step, priority = "SUPPRESS_OPT_OUT", "NONE"
    elif channel == "INSTANT_FORM":
        next_step, priority = (
            ("LEAD_FORM_CRM_REVIEW", "HUMAN_QUEUE") if row["submitted"]
            else ("NO_SUBMISSION_NO_LEAD", "NONE"))
    elif channel == "COMMENT_KEYWORD":
        if row["keyword_match"] and within_comment and not row["private_reply_used"]:
            next_step, priority = "REVIEW_SINGLE_PRIVATE_REPLY_ONLY", "HUMAN_QUEUE"
        else:
            next_step, priority = "HOLD_COMMENT_REPLY_INELIGIBLE", "NONE"
    elif channel == "LINK_IN_BIO":
        next_step, priority = "NO_SUBMISSION_NO_CHAT", "NONE"
    elif within_dm:
        next_step, priority = "REVIEW_INBOUND_DM_WITHIN_24H", "HUMAN_QUEUE"
    elif ad_window:
        # Meta's policy says *may* last up to seven days for verified Click-to-Direct
        # initiated messaging. A client-provided source flag is never sufficient.
        next_step, priority = "REVIEW_AD_WINDOW_ONLY_IF_ORIGIN_VERIFIED", "HUMAN_QUEUE"
    else:
        next_step, priority = "HOLD_DM_WINDOW_CLOSED", "NONE"
    if priority == "HUMAN_QUEUE" and complete and row["agent_available"]:
        priority = "HUMAN_HANDOVER_REVIEW"
    return {
        "event_id": row["event_id"], "workspace": row["workspace"],
        "entry_point": channel, "source_ref": row["source_ref"],
        "lead_in_example": bool((channel == "INSTANT_FORM" and row["submitted"])
                                or inbound),
        "submitted_form": bool(channel == "INSTANT_FORM" and row["submitted"]),
        "qualification_fields": 4, "fully_qualified_in_example": complete,
        "opted_out": row["opted_out"],
        "marketing_optin_example": row["has_marketing_optin"],
        "customer_identity_verified": False,
        "live_consent_verified": False,
        "campaign_attribution_verified": False,
        "real_account_permissions_verified": False,
        "ordinary_dm_window_in_example": within_dm,
        "ad_origin_extended_window_possible": ad_window,
        "single_private_reply_window_in_example": within_comment,
        "private_reply_already_used": row["private_reply_used"],
        "next_step": next_step, "routing": priority,
        "provider_message_sent": False, "real_crm_write": False,
        "outbound_action_authorized": False,
    }


def build_committed_instagram_pipeline(
    workspace: str | None = None, raw_fixture: bytes | None = None
) -> dict:
    _require(workspace is None or (type(workspace) is str and workspace in WORKSPACES),
             "Invalid workspace filter")
    doc = parse_instagram_fixture(FIXTURE.read_bytes() if raw_fixture is None else raw_fixture)
    events = [evaluate_instagram_record(x, doc["evaluated_at"]) for x in doc["records"]
              if workspace is None or x["workspace"] == workspace]
    return {
        "milestone": "P2_03Q_INSTAGRAM_CONSENT_FIRST",
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "schema_version": 1,
        "stages": ["ACQUISITION", "QUALIFICATION", "CRM_REVIEW", "HUMAN_HANDOVER"],
        "events": events,
        "metrics": {
            "example_leads": sum(x["lead_in_example"] for x in events),
            "example_forms": sum(x["submitted_form"] for x in events),
            "example_qualified": sum(x["fully_qualified_in_example"]
                                     and x["lead_in_example"] for x in events),
            "actual_leads_captured": 0, "actual_messages_sent": 0,
            "real_conversions_verified": None, "incremental_revenue_verified": None,
        },
        "permissions": {
            "meta_app_review_completed": False, "official_ig_account_connected": False,
            "lead_retrieval_authorized": False, "instagram_messaging_authorized": False,
            "instagram_comment_management_authorized": False,
            "webhook_signature_validation_active": False,
            "secure_crm_storage_enabled": False,
            "real_human_agent_connected": False,
        },
        "controls": {
            "source_only": True, "operator_review_required": True,
            "customer_data_collected": False, "webhook_receivers_enabled": False,
            "outbound_messages": 0, "database_writes": 0, "paid_ad_spend": 0,
            "subscriptions_purchased": 0, "production_go": False,
        },
    }
