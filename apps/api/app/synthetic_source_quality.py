"""P2-03t — deterministic, fail-closed source-data quality and provenance gate.

Applies to minimal redacted Meta-shaped events only; does not make untrusted
provider data, customer consent or real Meta app access trusted. Missing official
grant, event freshness and lead retrieval remain blocking for production.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

from .synthetic_meta_lead_federation import REGISTRY, CHANNELS
from .synthetic_growth_autopilot import SyntheticGrowthError

HEX = re.compile(r"[0-9a-f]{64}\Z")
SIM = re.compile(r"SIM-[A-Z0-9-]{3,48}\Z")
RECORD_FIELDS = frozenset({
    "workspace", "platform", "account_ref", "event_ref", "kind", "form_ref",
    "customer_contact", "identity_verified", "ad_attribution_verified",
    "permission_verified", "consent_verified", "outbound_eligible",
})
REPORT_FIELDS = frozenset({
    "classification", "workspace", "signature_check", "real_provider_identity_verified",
    "provider_permissions_verified", "raw_body_sha256", "events",
    "provider_calls", "database_writes", "messages_sent", "live_webhook_endpoint",
})
KINDS = {
    "FACEBOOK": "SUBMITTED_LEAD_FORM_METADATA",
    "INSTAGRAM": "INBOUND_DM_METADATA",
    "WHATSAPP": "INBOUND_WHATSAPP_METADATA",
}
SOURCE_KIND = {platform: name for name, platform in CHANNELS.items()}


def quality_gate(inspection: Any, raw_body: bytes,
                 expected_workspace: str) -> dict:
    """Return reason codes without persisting raw data or exposing PII.

    pass_for_disposable_ci is for precisely the fictional, signed-source demo.
    It is NEVER an authorization for live provider ingest.
    """
    issues: list[str] = []
    def issue(reason: str):
        if reason not in issues:
            issues.append(reason)

    if type(raw_body) is not bytes or not 0 < len(raw_body) <= 16_384:
        issue("RAW_BODY_OUT_OF_BOUNDS")
    if type(expected_workspace) is not str or expected_workspace not in (
        "academy_demo", "bespoke_demo"
    ):
        issue("UNRECOGNIZED_WORKSPACE")
    if type(inspection) is not dict or set(inspection) != REPORT_FIELDS:
        issue("BAD_INSPECTION_ENVELOPE")
        return _result(issues, 0, None)

    if inspection.get("classification") != "SYNTHETIC_VERIFIED_SIGNATURE_ONLY" or (
        inspection.get("signature_check") != "LOCAL_HMAC_PASSED"
    ):
        issue("SIGNED_SOURCE_NOT_ESTABLISHED")
    if inspection.get("workspace") != expected_workspace:
        issue("WORKSPACE_MISMATCH")
    for name in ("provider_calls", "database_writes", "messages_sent"):
        if type(inspection.get(name)) is not int or inspection[name] != 0:
            issue("LIVE_SIDE_EFFECT_FLAG")
    for name in ("real_provider_identity_verified", "provider_permissions_verified",
                 "live_webhook_endpoint"):
        if inspection.get(name) is not False:
            issue("UNSUPPORTED_PRODUCTION_STATUS")

    declared_digest = inspection.get("raw_body_sha256")
    actual_digest = sha256(raw_body).hexdigest() if type(raw_body) is bytes else None
    if type(declared_digest) is not str or HEX.fullmatch(declared_digest) is None or (
        declared_digest != actual_digest
    ):
        issue("SOURCE_HASH_MISMATCH")

    entries = inspection.get("events")
    if type(entries) is not list or not 1 <= len(entries) <= 50:
        issue("INVALID_BATCH_SIZE")
        return _result(issues, 0, actual_digest)
    seen = set()
    for record in entries:
        if type(record) is not dict or set(record) != RECORD_FIELDS:
            issue("UNEXPECTED_RECORD_SHAPE")
            continue
        platform, account, ref, workspace, kind = (
            record["platform"], record["account_ref"],
            record["event_ref"], record["workspace"], record["kind"])
        if type(platform) is not str or platform not in KINDS or (
            record["kind"] != KINDS.get(platform)
        ):
            issue("CHANNEL_KIND_MISMATCH")
            continue
        if type(account) is not str or SIM.fullmatch(account) is None or (
            type(ref) is not str or SIM.fullmatch(ref) is None
        ):
            issue("UNRECOGNIZED_SOURCE_REFERENCE")
            continue
        channel = SOURCE_KIND[platform]
        if REGISTRY.get((channel,account)) != workspace or workspace != expected_workspace:
            issue("PROVIDER_ACCOUNT_TENANT_MISMATCH")
        key = (platform, account, ref)
        if key in seen:
            issue("DUPLICATE_SOURCE_EVENT")
        seen.add(key)
        if platform == "FACEBOOK":
            if type(record["form_ref"]) is not str or (
                SIM.fullmatch(record["form_ref"]) is None
            ):
                issue("MISSING_SUBMITTED_FORM_PROVENANCE")
        elif record["form_ref"] is not None:
            issue("UNEXPECTED_CHANNEL_FORM")
        if record["customer_contact"] is not None:
            issue("PERSONAL_DATA_NOT_ACCEPTED")
        for flag in ("identity_verified", "ad_attribution_verified",
                     "permission_verified", "consent_verified", "outbound_eligible"):
            if record[flag] is not False:
                issue("UNSUPPORTED_LIVE_CONSENT_OR_SEND_CLAIM")
    return _result(issues, len(entries), actual_digest)


def _result(issues: list[str], count: int, digest: str | None) -> dict:
    result = {
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "quality_state": "READY_FOR_DISPOSABLE_REHEARSAL" if not issues else "QUARANTINE",
        "reason_codes": tuple(sorted(issues)),
        "checked_event_count": count,
        "source_sha256": digest,
        "production_ready": False,
        "live_event_freshness_verified": False,
        "official_account_permission_verified": False,
        "customer_consent_verified": False,
        "actual_attribution_verified": False,
        "rejected_raw_data_retained": False,
    }
    return result


def require_disposable_source(inspection: dict, raw: bytes, workspace: str) -> dict:
    result = quality_gate(inspection, raw, workspace)
    if result["quality_state"] != "READY_FOR_DISPOSABLE_REHEARSAL":
        raise SyntheticGrowthError("Source quality rejected: " +
                                   ", ".join(result["reason_codes"]))
    return result
