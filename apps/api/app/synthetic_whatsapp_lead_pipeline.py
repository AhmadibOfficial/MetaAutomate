"""P2-03p — WhatsApp lead pipeline policy lab (source-only).

No phone, contacts, messages, customer identifiers, live consent, Cloud API, credentials
or message dispatch. Every inbound and opt-in value is invented and NOT verified
by WhatsApp or a real business. Reference: WhatsApp Business Messaging Policy,
updated 2026-09-23, https://whatsappbusiness.com/policy/.

Deterministic proposed next-step controls only. Not a substitute for verifying
current platform policy, data protection law, real consent or webhook signatures.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json
import re

from .synthetic_growth_autopilot import SyntheticGrowthError

FIXTURE = (Path(__file__).resolve().parents[3]
           / "contracts/domains/v1/fixtures/synthetic_whatsapp_leads.v1.json")
MAX_BYTES = 24_576
MAX_LEADS = 30
WINDOW = timedelta(hours=24)
WORKSPACES = frozenset({"academy_demo", "bespoke_demo"})
ENTRIES = frozenset({"CTWA_AD", "WEBSITE_LINK", "QR_CODE", "OWNED_LINK"})
PURPOSES = frozenset({"SERVICE", "MARKETING", "UTILITY"})
TEMPLATES = frozenset({"NONE", "PENDING", "APPROVED", "REJECTED", "PAUSED"})
FIELDS = frozenset({"workspace", "lead_id", "entry", "source_reference",
                    "last_user_message_at", "qualification", "message_purpose",
                    "optin", "opted_out", "template_state", "agent_available"})
QUAL_VALUES = {
    "interest": {"COURSES", "FASHION"},
    "budget_band": {"LOW", "MEDIUM", "HIGH", "UNKNOWN"},
    "location_band": {"LOCAL", "REMOTE", "UNKNOWN"},
    "timeline": {"NOW", "SOON", "LATER", "UNKNOWN"},
}
SOURCE_REFERENCE = re.compile(r"SIM-(?:AD|QR|WEB|LINK)-[A-Z0-9-]{2,30}\Z")
LEAD_ID = re.compile(r"SIM-LEAD-[A-Z0-9-]{2,30}\Z")


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SyntheticGrowthError(message)


def _exact(value: Any, keys: set[str] | frozenset[str], label: str) -> dict:
    _require(type(value) is dict and set(value) == keys, "Unexpected " + label + " fields")
    return value


def _pairs(items: list[tuple[str, Any]]) -> dict:
    d = {}
    for key, value in items:
        _require(key not in d, "Duplicate WhatsApp JSON key")
        d[key] = value
    return d


def _reject_float(value: str) -> None:
    raise SyntheticGrowthError("Floating and nonfinite numbers not allowed")


def _utc(value: Any, now: datetime | None = None) -> datetime:
    _require(type(value) is str and len(value) == 20 and value.endswith("Z"),
             "Only canonical UTC timestamps supported")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SyntheticGrowthError("Invalid UTC timestamp") from exc
    if now is not None:
        _require(parsed <= now, "Future customer messages or consent not supported")
    return parsed


def parse_whatsapp_fixture(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES
             and b"\x00" not in raw, "Invalid bounded source-only fixture")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_float=_reject_float, parse_constant=_reject_float)
    except SyntheticGrowthError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed WhatsApp fixture") from exc
    _exact(doc, {"schema_version", "classification", "evaluated_at", "leads"}, "root")
    _require(type(doc["schema_version"]) is int and doc["schema_version"] == 1
             and doc["classification"] == "SYNTHETIC_SOURCE_ONLY",
             "Only versioned synthetic lead examples accepted")
    now = _utc(doc["evaluated_at"])
    leads = doc["leads"]
    _require(type(leads) is list and 1 <= len(leads) <= MAX_LEADS, "Invalid lead count")
    seen = set()
    for lead in leads:
        _exact(lead, FIELDS, "lead")
        ws, lead_id, entry, reference = (
            lead["workspace"], lead["lead_id"], lead["entry"], lead["source_reference"])
        _require(type(ws) is str and ws in WORKSPACES, "Unknown workspace")
        _require(type(lead_id) is str and LEAD_ID.fullmatch(lead_id) is not None
                 and lead_id not in seen, "Invalid or duplicate simulated lead")
        seen.add(lead_id)
        _require(type(entry) is str and entry in ENTRIES
                 and type(reference) is str
                 and SOURCE_REFERENCE.fullmatch(reference) is not None,
                 "Unsupported entry or attribution field")
        allowed_prefix = {
            "CTWA_AD": "SIM-AD-", "QR_CODE": "SIM-QR-",
            "WEBSITE_LINK": "SIM-WEB-", "OWNED_LINK": "SIM-LINK-",
        }
        _require(reference.startswith(allowed_prefix[entry]),
                 "Entry-source reference mismatch")
        _require(type(lead["message_purpose"]) is str
                 and lead["message_purpose"] in PURPOSES
                 and type(lead["template_state"]) is str
                 and lead["template_state"] in TEMPLATES, "Invalid message policy parameters")
        _require(type(lead["opted_out"]) is bool
                 and type(lead["agent_available"]) is bool, "Invalid boolean controls")
        q = _exact(lead["qualification"], set(QUAL_VALUES), "qualification")
        for k, options in QUAL_VALUES.items():
            _require(type(q[k]) is str and q[k] in options, "Invalid qualification answer")
        optin = _exact(lead["optin"], {"marketing", "utility", "recorded_at"}, "opt-in")
        _require(type(optin["marketing"]) is bool and type(optin["utility"]) is bool,
                 "Invalid consent value")
        recorded = optin["recorded_at"]
        if optin["marketing"] or optin["utility"]:
            _require(recorded is not None, "Positive consent must have source time")
            _utc(recorded, now)
        else:
            _require(recorded is None, "Consent timestamp without opt-in")
        inbound = lead["last_user_message_at"]
        if inbound is not None:
            received = _utc(inbound, now)
            if recorded is not None:
                _require(_utc(recorded, now) >= received,
                         "Example opt-in must not predate this simulated conversation")
        else:
            _require(not optin["marketing"] and not optin["utility"],
                     "Link click without message cannot imply consent")
            _require(all(v == "UNKNOWN" for k,v in q.items()
                         if k in ("budget_band", "location_band", "timeline")),
                     "No qualification before a conversation")
    return doc


def evaluate_whatsapp_lead(lead: dict, evaluated_at: str) -> dict:
    """Analyze a validated synthetic lead. NO output represents send authorization."""
    now = _utc(evaluated_at)
    _exact(lead, FIELDS, "lead")
    _require(type(lead["workspace"]) is str and lead["workspace"] in WORKSPACES
             and type(lead["lead_id"]) is str and LEAD_ID.fullmatch(lead["lead_id"]),
             "Unknown simulated lead")
    inbound = lead["last_user_message_at"]
    latest = _utc(inbound, now) if inbound is not None else None
    _require(type(lead["opted_out"]) is bool and type(lead["agent_available"]) is bool,
             "Unverified controls")
    q = _exact(lead["qualification"], set(QUAL_VALUES), "qualification")
    _require(all(type(q[k]) is str and q[k] in options
                 for k, options in QUAL_VALUES.items()), "Invalid qualification")
    optin = _exact(lead["optin"], {"marketing", "utility", "recorded_at"}, "opt-in")
    _require(type(optin["marketing"]) is bool and type(optin["utility"]) is bool,
             "Invalid opt-in")
    _require(lead["message_purpose"] in PURPOSES and lead["template_state"] in TEMPLATES,
             "Invalid template parameters")
    open_window = latest is not None and timedelta(0) <= now - latest < WINDOW
    qualified = (latest is not None and q["interest"] != "UNKNOWN"
                 and q["budget_band"] != "UNKNOWN"
                 and q["timeline"] != "UNKNOWN"
                 and q["location_band"] != "UNKNOWN")
    # A WhatsApp sender identifier/number is NOT proof of a real person's identity.
    # CTWA source is NOT verifiably ad-attributed without authenticated referral metadata.
    route = "NOT_A_LEAD"
    if latest is None:
        next_step = "NO_MESSAGE_NO_CONTACT"
    elif lead["opted_out"]:
        next_step = "SUPPRESS_OPT_OUT"
        route = "SUPPRESSED"
    else:
        route = ("HUMAN_HANDOVER_REVIEW" if qualified and lead["agent_available"]
                 else "HUMAN_QUEUE_REVIEW")
        purpose = lead["message_purpose"]
        if purpose == "SERVICE" and open_window:
            next_step = "REVIEW_IN_WINDOW_SERVICE_REPLY"
        elif (purpose in ("MARKETING", "UTILITY")
              and optin[purpose.lower()]
              and lead["template_state"] == "APPROVED"):
            next_step = "REVIEW_APPROVED_TEMPLATE_ONLY"
        else:
            next_step = "HOLD_NO_AUTHORIZED_MESSAGE_PATH"
    return {
        "lead_id": lead["lead_id"],
        "workspace": lead["workspace"],
        "entry_point": lead["entry"],
        "source_reference": lead["source_reference"],
        "source_attribution": "SIMULATED_UNVERIFIED",
        "customer_identity_verified": False,
        "real_consent_verified": False,
        "inbound_conversation": latest is not None,
        "qualification_questions": 4,
        "qualified_in_example": qualified,
        "customer_service_window_open": open_window,
        "opted_out": lead["opted_out"],
        "marketing_optin_in_example": optin["marketing"],
        "recommended_next_step": next_step,
        "human_route": route,
        "message_sent": False,
        "template_approval_live_verified": False,
        "actual_provider_costs": None,
        "outbound_dispatch_enabled": False,
    }


def build_committed_whatsapp_pipeline(workspace: str | None = None,
                                      raw_fixture: bytes | None = None) -> dict:
    _require(workspace is None or (type(workspace) is str and workspace in WORKSPACES),
             "Invalid workspace selection")
    doc = parse_whatsapp_fixture(FIXTURE.read_bytes() if raw_fixture is None else raw_fixture)
    leads = [evaluate_whatsapp_lead(lead, doc["evaluated_at"])
             for lead in doc["leads"] if workspace is None or lead["workspace"] == workspace]
    return {
        "milestone": "P2_03P_WHATSAPP_CONSENT_FIRST",
        "schema_version": 1, "classification": "SYNTHETIC_SOURCE_ONLY",
        "policy_reference": "https://whatsappbusiness.com/policy/",
        "stages": ("ACQUISITION", "IN_CHAT_QUALIFICATION", "CRM_REVIEW", "HUMAN_HANDOVER"),
        "leads": leads,
        "metrics": {
            "inbound": sum(x["inbound_conversation"] for x in leads),
            "qualified_in_example": sum(x["qualified_in_example"] for x in leads),
            "suppressed": sum(x["opted_out"] for x in leads),
            "queued_for_human_review": sum(x["human_route"] in
                ("HUMAN_HANDOVER_REVIEW", "HUMAN_QUEUE_REVIEW") for x in leads),
            "actual_messages_sent": 0,
            "actual_conversion_rate": None,
            "marketing_open_rate_claim": None,
        },
        "gates": {
            "real_contact_records": False,
            "real_customer_consent": False,
            "verified_provider_attribution": False,
            "provider_credentials_loaded": False,
            "authenticated_webhook_receiver": False,
            "templates_verified_with_meta": False,
            "operator_authorized_live_use": False,
            "messaging_active": False,
            "messages_sent": 0,
            "external_calls": 0,
            "database_writes": 0,
        },
    }
