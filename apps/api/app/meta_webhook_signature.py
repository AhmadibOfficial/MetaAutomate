"""Offline verifier for Meta-style X-Hub-Signature-256 webhook envelopes.

A reusable cryptographic primitive, not a webhook endpoint or an assertion that
Meta has authenticated a particular event. It cannot establish account ownership,
app permissions, tenant authorization, event freshness or anti-replay on its own.
"""
from __future__ import annotations
import hashlib
import hmac
import re
from .synthetic_growth_autopilot import SyntheticGrowthError

SIGNATURE_RE=re.compile(r"sha256=([0-9a-f]{64})\Z")
MAX_PAYLOAD_BYTES=262_144


def verify_meta_webhook_signature(payload: bytes, signature: str, app_secret: bytes) -> bool:
    """Fail closed, never log secrets, use raw payload bytes and constant-time equality."""
    if type(payload) is not bytes or not (0 < len(payload) <= MAX_PAYLOAD_BYTES):
        return False
    if type(app_secret) is not bytes or not (16 <= len(app_secret) <= 4096):
        return False
    if type(signature) is not str or len(signature) != 71:
        return False
    match=SIGNATURE_RE.fullmatch(signature)
    if match is None:
        return False
    digest=hmac.new(app_secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest,match.group(1))


def synthetic_event_fingerprint(event_id: str, workspace: str) -> str:
    """Deterministic idempotency key for a future durable per-tenant ledger.

    NOT a durable replay defense. Never pass PII in event IDs.
    """
    if (type(event_id) is not str or not re.fullmatch(r"SIM-[A-Z0-9-]{3,48}", event_id)
        or type(workspace) is not str or workspace not in ("academy_demo","bespoke_demo")):
        raise SyntheticGrowthError("Invalid synthetic scoped event")
    return hashlib.sha256((workspace+"|"+event_id).encode("ascii")).hexdigest()
