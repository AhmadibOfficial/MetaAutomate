"""P2-03r: offline signed Meta-event intake and tenant-isolated lead-review foundation.

Accepted inputs are *synthetic metadata only*. Signatures are checked before
any JSON parsing; account -> tenant mapping comes from a trusted registry, never
from the event or the caller. No Graph API, credentials, PII, persistence,
webhook endpoint, advertisement spend, or outgoing messages.

Signed synthetic events establish only that the supplied bytes match a supplied
test secret, NOT that a live Meta app or a customer was authenticated.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any

from .meta_webhook_signature import verify_meta_webhook_signature
from .synthetic_growth_autopilot import SyntheticGrowthError

REGISTRY = {
    ("page", "SIM-PAGE-ACADEMY"): "academy_demo",
    ("page", "SIM-PAGE-BESPOKE"): "bespoke_demo",
    ("instagram", "SIM-IG-ACADEMY"): "academy_demo",
    ("instagram", "SIM-IG-BESPOKE"): "bespoke_demo",
    ("whatsapp_business_account", "SIM-WABA-ACADEMY"): "academy_demo",
    ("whatsapp_business_account", "SIM-WABA-BESPOKE"): "bespoke_demo",
}
CHANNELS = {
    "page": "FACEBOOK",
    "instagram": "INSTAGRAM",
    "whatsapp_business_account": "WHATSAPP",
}
MAX_RAW_BYTES = 16_384
MAX_ENTRIES = 10
MAX_ITEMS = 10
SIM_ID = re.compile(r"SIM-[A-Z0-9-]{3,48}\Z")

# Explicitly not sufficient for live activation. These are prerequisite names,
# not asserted current grants, and Meta may change applicable permissions.
REQUIRED_PERMISSIONS = {
    "FACEBOOK": ("APP_REVIEW", "PAGE_LEAD_ACCESS", "LEADS_RETRIEVAL",
                 "WEBHOOK_SUBSCRIPTION"),
    "INSTAGRAM": ("APP_REVIEW", "PROFESSIONAL_ACCOUNT_ACCESS",
                  "INSTAGRAM_MESSAGING", "WEBHOOK_SUBSCRIPTION"),
    "WHATSAPP": ("BUSINESS_OWNERSHIP", "WABA_ACCESS",
                 "WEBHOOK_SUBSCRIPTION", "TEMPLATE_AND_CONSENT_REVIEW"),
}


def _check(test: bool, reason: str) -> None:
    if not test:
        raise SyntheticGrowthError(reason)


def _exact(data: Any, fields: set[str], name: str) -> dict:
    _check(type(data) is dict and set(data) == fields, "Unexpected " + name + " fields")
    return data


def _id(value: Any, label: str) -> str:
    _check(type(value) is str and SIM_ID.fullmatch(value) is not None,
           "Not an approved synthetic " + label)
    return value


def _pairs(values: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, val in values:
        _check(key not in result, "Duplicate JSON key")
        result[key] = val
    return result


def _reject_float(value: str) -> None:
    raise SyntheticGrowthError("Only supported integer fields are accepted")


def _parse(raw: bytes) -> dict:
    _check(type(raw) is bytes and 0 < len(raw) <= MAX_RAW_BYTES and b"\x00" not in raw,
           "Invalid webhook envelope size")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_float=_reject_float, parse_constant=_reject_float)
    except SyntheticGrowthError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed webhook envelope") from exc
    return _exact(doc, {"object", "entry"}, "webhook")


def _normalize_item(event: dict, kind: str, account: str, workspace: str) -> dict:
    if kind == "page":
        _exact(event, {"field", "value"}, "Facebook event")
        _check(event["field"] == "leadgen", "Only leadgen change metadata allowed")
        value = _exact(event["value"], {"leadgen_id", "form_id", "page_id"},
                       "Facebook leadgen metadata")
        _check(value["page_id"] == account, "Page ID mismatch")
        lead_id = _id(value["leadgen_id"], "leadgen ID")
        form_id = _id(value["form_id"], "form ID")
        event_id = lead_id
        event_kind = "SUBMITTED_LEAD_FORM_METADATA"
        details = {"form_id": form_id}
    elif kind == "instagram":
        _exact(event, {"message"}, "Instagram event")
        value = _exact(event["message"], {"mid"}, "Instagram message metadata")
        event_id = _id(value["mid"], "Instagram message")
        event_kind = "INBOUND_DM_METADATA"
        details = {}
    elif kind == "whatsapp_business_account":
        _exact(event, {"field", "value"}, "WhatsApp event")
        _check(event["field"] == "messages", "Unsupported WhatsApp notification")
        value = _exact(event["value"], {"messages"}, "WhatsApp messages")
        messages = value["messages"]
        _check(type(messages) is list and len(messages) == 1,
               "Only single redacted sample message supported")
        _exact(messages[0], {"id"}, "WhatsApp message metadata")
        event_id = _id(messages[0]["id"], "WhatsApp message")
        event_kind = "INBOUND_WHATSAPP_METADATA"
        details = {}
    else:
        raise SyntheticGrowthError("Unsupported platform")
    return {
        "workspace": workspace,
        "platform": CHANNELS[kind],
        "account_ref": account,
        "event_ref": event_id,
        "kind": event_kind,
        "form_ref": details.get("form_id"),
        "customer_contact": None,
        "identity_verified": False,
        "ad_attribution_verified": False,
        "permission_verified": False,
        "consent_verified": False,
        "outbound_eligible": False,
    }


def inspect_signed_meta_event(raw: bytes, signature: str, test_app_secret: bytes,
                              *, expected_workspace: str) -> dict:
    """Verify raw-byte HMAC first, then parse and scope metadata.

    expected_workspace symbolizes a separately authenticated caller context.
    It is NOT taken as proof of real authentication or an actual Meta grant.
    """
    _check(verify_meta_webhook_signature(raw, signature, test_app_secret),
           "Invalid signed webhook body")
    _check(type(expected_workspace) is str and expected_workspace in
           ("academy_demo", "bespoke_demo"), "Unsupported workspace context")
    doc = _parse(raw)
    kind = doc["object"]
    _check(type(kind) is str and kind in CHANNELS, "Unsupported Meta object")
    entries = doc["entry"]
    _check(type(entries) is list and 1 <= len(entries) <= MAX_ENTRIES,
           "Invalid entry count")
    outputs = []
    keys = set()
    for entry in entries:
        fields = {"id", "changes"} if kind != "instagram" else {"id", "messaging"}
        _exact(entry, fields, "account entry")
        account = _id(entry["id"], "platform account")
        trusted = REGISTRY.get((kind, account))
        _check(trusted is not None and trusted == expected_workspace,
               "Unrecognized platform account or cross-tenant attempt")
        items = entry["messaging"] if kind == "instagram" else entry["changes"]
        _check(type(items) is list and 1 <= len(items) <= MAX_ITEMS,
               "Invalid account change count")
        for item in items:
            record = _normalize_item(item, kind, account, trusted)
            key = (kind, account, record["event_ref"])
            _check(key not in keys, "Duplicate events in a batch")
            keys.add(key)
            outputs.append(record)
    return {
        "classification": "SYNTHETIC_VERIFIED_SIGNATURE_ONLY",
        "workspace": expected_workspace,
        "signature_check": "LOCAL_HMAC_PASSED",
        "real_provider_identity_verified": False,
        "provider_permissions_verified": False,
        "raw_body_sha256": sha256(raw).hexdigest(),
        "events": outputs,
        "provider_calls": 0,
        "database_writes": 0,
        "messages_sent": 0,
        "live_webhook_endpoint": False,
    }


def permission_readiness(channel: str, observed: dict[str, bool] | None = None) -> dict:
    """Checklist only. An all-true synthetic checklist NEVER enables real execution."""
    _check(type(channel) is str and channel in REQUIRED_PERMISSIONS,
           "Unsupported Meta platform")
    required = REQUIRED_PERMISSIONS[channel]
    flags = {} if observed is None else observed
    _check(type(flags) is dict and set(flags).issubset(set(required)) and
           all(type(v) is bool for v in flags.values()), "Invalid permission evidence")
    missing = [p for p in required if flags.get(p) is not True]
    return {
        "platform": channel,
        "requirements": list(required),
        "missing": missing,
        "checklist_complete_in_example": not missing,
        "independent_meta_grants_verified": False,
        "tenant_authentication_verified": False,
        "release_authorized": False,
        "operational_status": "NO_GO",
    }


@dataclass(frozen=True)
class AuditRecord:
    workspace: str
    event_ref: str
    purpose: str
    state: str
    evidence_ref: str
    actor: str
    previous_sha256: str
    sha256: str


class SyntheticMetaReviewLedger:
    """Small append-only *in-memory* review ledger, not CRM persistence or real consent.

    Enforces namespace isolation, duplicate detection, and a hash-linked local
    history. It deliberately cannot store PII or issue an external send.
    """

    def __init__(self, workspace: str):
        _check(workspace in ("academy_demo", "bespoke_demo"),
               "Unknown ledger workspace")
        self.workspace = workspace
        self._events: dict[str, dict] = {}
        self._audit: list[AuditRecord] = []
        self._tasks: dict[str, dict] = {}
        self._consent: dict[tuple[str, str], str] = {}

    def receive(self, inspection: dict) -> int:
        _check(type(inspection) is dict and inspection.get("workspace") == self.workspace
               and inspection.get("classification") == "SYNTHETIC_VERIFIED_SIGNATURE_ONLY"
               and inspection.get("signature_check") == "LOCAL_HMAC_PASSED"
               and inspection.get("live_webhook_endpoint") is False,
               "Only locally inspected tenant-matched synthetic input")
        records = inspection.get("events")
        _check(type(records) is list and records and all(
            type(row) is dict and row.get("workspace") == self.workspace
            and row.get("customer_contact") is None
            and row.get("outbound_eligible") is False
            and row.get("platform") in REQUIRED_PERMISSIONS
            and type(row.get("event_ref")) is str and SIM_ID.fullmatch(row["event_ref"])
            for row in records), "Invalid record")
        new = {}
        for row in records:
            key = row["platform"] + "|" + row["account_ref"] + "|" + row["event_ref"]
            _check(key not in new, "Duplicate records in batch")
            new[key] = dict(row)
        inserted = 0
        for key, row in new.items():
            if key in self._events:
                _check(self._events[key] == row, "Collision with changed webhook event")
                continue
            self._events[key] = row
            inserted += 1
            self._tasks[key] = {
                "event_ref": row["event_ref"], "platform": row["platform"],
                "workspace": self.workspace, "state": "HUMAN_REVIEW_REQUIRED",
                "assigned_agent": None, "customer_contact": None,
                "automatic_followup": False,
            }
        return inserted

    def tasks(self) -> list[dict]:
        return [dict(t) for t in self._tasks.values()]

    def assign_human(self, platform: str, event_ref: str, agent_ref: str) -> dict:
        _check(platform in REQUIRED_PERMISSIONS, "Unsupported platform")
        _id(event_ref, "event ID")
        _check(type(agent_ref) is str and agent_ref.startswith("SIM-AGENT-") and
               SIM_ID.fullmatch(agent_ref), "No authorized real human agent")
        matches = [k for k,t in self._tasks.items()
                   if t["platform"] == platform and t["event_ref"] == event_ref]
        _check(len(matches) == 1, "No matching tenant-scoped lead")
        task = self._tasks[matches[0]]
        _check(task["state"] == "HUMAN_REVIEW_REQUIRED", "Invalid task transition")
        task["state"] = "ASSIGNED_SYNTHETIC_HUMAN"
        task["assigned_agent"] = agent_ref
        return dict(task)

    def record_consent_review(self, event_ref: str, purpose: str, state: str,
                              evidence_ref: str, actor_ref: str) -> AuditRecord:
        _id(event_ref, "event ID")
        _check(any(x["event_ref"] == event_ref for x in self._events.values()),
               "Consent event not in this workspace")
        _check(purpose in ("SERVICE", "MARKETING"), "Unknown consent purpose")
        _check(state in ("UNVERIFIED", "GRANTED_EXAMPLE", "REVOKED_EXAMPLE"),
               "Unknown consent review state")
        _id(evidence_ref, "review evidence")
        _check(type(actor_ref) is str and actor_ref.startswith("SIM-AGENT-")
               and SIM_ID.fullmatch(actor_ref), "Only synthetic reviewer IDs")
        prior = self._consent.get((event_ref, purpose), "UNVERIFIED")
        _check(not (prior == "REVOKED_EXAMPLE" and state == "GRANTED_EXAMPLE"),
               "Revoked consent cannot be silently regranted")
        prev_hash = self._audit[-1].sha256 if self._audit else "0" * 64
        serialized = json.dumps([self.workspace, event_ref, purpose, state,
                                 evidence_ref, actor_ref, prev_hash],
                                separators=(",", ":"), ensure_ascii=True)
        digest = sha256(serialized.encode("ascii")).hexdigest()
        record = AuditRecord(self.workspace, event_ref, purpose, state,
                             evidence_ref, actor_ref, prev_hash, digest)
        self._audit.append(record)
        self._consent[(event_ref, purpose)] = state
        return record

    def consent_review(self, event_ref: str, purpose: str) -> str:
        _id(event_ref, "event ID")
        _check(purpose in ("SERVICE", "MARKETING"), "Unknown consent purpose")
        return self._consent.get((event_ref, purpose), "UNVERIFIED")

    def audit(self) -> tuple[AuditRecord, ...]:
        return tuple(self._audit)

    def summary(self) -> dict:
        return {
            "workspace": self.workspace, "event_count": len(self._events),
            "human_review_tasks": len(self._tasks),
            "consent_review_count": len(self._audit),
            "actual_customer_records": 0, "live_storage": False,
            "authenticated_agents": 0, "actual_permissions_verified": False,
            "messages_sent": 0, "payments_charged": 0,
            "operational_status": "NO_GO",
        }
