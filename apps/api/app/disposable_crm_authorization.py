"""P2-03t — cryptographically verified application actor RBAC, source-only.

This is a working authorization *component* for a disposable tenant-isolated
repository. It is not a login endpoint, real user directory, production token
issuer, live OIDC integration, or an authorization to activate Meta messaging.
Tokens are Ed25519-signed by the offline test harness. Only a separately
provisioned identity service could issue trusted real-actor claims in future.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
import time
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .disposable_meta_crm import (
    TENANTS, scoped_tenant, list_review_tasks, store_inspected_events,
    assign_review_agent, record_consent_evidence, store_private_evidence,
    read_private_evidence,
)
from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_meta_lead_federation import inspect_signed_meta_event
from .synthetic_source_quality import require_disposable_source

ISSUER = "metaautomate-disposable-ci"
AUDIENCE = "meta-stage-crm-rehearsal"
MAX_TOKEN_CHARS = 4096
MAX_LIFETIME_SECONDS = 300
ROLES = frozenset({"auditor", "reviewer", "tenant_admin"})
ACTIONS = {
    "read_queue": frozenset({"auditor", "reviewer", "tenant_admin"}),
    "ingest_signed_metadata": frozenset({"tenant_admin"}),
    "assign_human": frozenset({"reviewer", "tenant_admin"}),
    "record_consent_review": frozenset({"tenant_admin"}),
    "write_protected_evidence": frozenset({"tenant_admin"}),
    "read_protected_evidence": frozenset({"tenant_admin"}),
}
CLAIM_FIELDS = frozenset({
    "version", "issuer", "audience", "workspace", "actor_ref", "role",
    "issued_at", "expires_at", "token_ref",
})
ACTOR_RE = re.compile(r"SIM-ACTOR-[A-Z0-9-]{2,40}\Z")
TOKEN_RE = re.compile(r"SIM-TOKEN-[A-Z0-9-]{2,40}\Z")
BASE64URL_RE = re.compile(r"[A-Za-z0-9_-]+\Z")


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise SyntheticGrowthError(reason)


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "Repeated security claim field")
        result[key] = value
    return result


def _no_float(value):
    raise SyntheticGrowthError("Floating or nonfinite claim value prohibited")


def _decode(segment: str, maximum: int) -> bytes:
    _require(type(segment) is str and 0 < len(segment) <= maximum
             and BASE64URL_RE.fullmatch(segment) is not None,
             "Invalid token encoding")
    try:
        raw = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise SyntheticGrowthError("Invalid encoded token") from exc
    _require(base64.urlsafe_b64encode(raw).rstrip(b"=").decode() == segment,
             "Noncanonical signed token")
    return raw


@dataclass(frozen=True)
class VerifiedActor:
    workspace: str
    actor_ref: str
    role: str
    expires_at: int
    token_ref: str
    def permits(self, action: str) -> bool:
        return action in ACTIONS and self.role in ACTIONS[action]


def verify_actor_token(
    token: str, trusted_public_key: Ed25519PublicKey, *,
    now: int | None = None,
) -> VerifiedActor:
    """Verify signature before JSON decoding, then exact issuer/audience/role/time."""
    _require(isinstance(trusted_public_key, Ed25519PublicKey),
             "A pinned Ed25519 public key is required")
    _require(type(token) is str and 0 < len(token) <= MAX_TOKEN_CHARS,
             "Invalid bounded access token")
    parts = token.split(".")
    _require(len(parts) == 3 and parts[0] == "v1", "Unsupported auth envelope")
    payload = _decode(parts[1], 3000)
    signature = _decode(parts[2], 128)
    _require(len(signature) == 64, "Invalid Ed25519 signature length")
    try:
        trusted_public_key.verify(signature, ("v1." + parts[1]).encode("ascii"))
    except InvalidSignature as exc:
        raise SyntheticGrowthError("Untrusted authorization signature") from exc

    _require(0 < len(payload) <= 2048 and b"\x00" not in payload,
             "Invalid claim byte count")
    try:
        claims = json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=_no_float, parse_constant=_no_float)
    except SyntheticGrowthError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed access claims") from exc
    _require(type(claims) is dict and set(claims) == CLAIM_FIELDS,
             "Unrecognized or missing authorization claims")
    _require(type(claims["version"]) is int and claims["version"] == 1
             and claims["issuer"] == ISSUER and claims["audience"] == AUDIENCE,
             "Invalid issuer or audience")
    workspace, role, actor, ref = (claims["workspace"], claims["role"],
                                   claims["actor_ref"], claims["token_ref"])
    _require(type(workspace) is str and workspace in TENANTS
             and type(role) is str and role in ROLES
             and type(actor) is str and ACTOR_RE.fullmatch(actor) is not None
             and type(ref) is str and TOKEN_RE.fullmatch(ref) is not None,
             "Unsupported actor/role/tenant identity")
    issued, expiry = claims["issued_at"], claims["expires_at"]
    actual_now = int(time.time()) if now is None else now
    _require(type(actual_now) is int and actual_now >= 0, "Invalid clock")
    _require(type(issued) is int and type(expiry) is int and issued >= 0
             and issued <= actual_now + 30
             and expiry > actual_now and 0 < expiry - issued <= MAX_LIFETIME_SECONDS,
             "Expired, premature or overlong session")
    return VerifiedActor(workspace, actor, role, expiry, ref)


def require_actor_access(actor: VerifiedActor, workspace: str, action: str) -> None:
    _require(isinstance(actor, VerifiedActor)
             and type(workspace) is str and actor.workspace == workspace,
             "Cross-tenant application authorization denied")
    _require(type(action) is str and actor.permits(action),
             "Insufficient role permissions")


class AuthorizedMetaCRM:
    """Narrow API service adapter; every operation checks signed claims and DB login.

    A signed role claim alone cannot select a tenant: PostgreSQL's authenticated
    session_user mapping must also agree, independently of caller-provided GUCs.
    There are no HTTP routes or real identity-provider connections in this lab.
    """

    def __init__(self, conn: Any, token: str,
                 trusted_public_key: Ed25519PublicKey, *, now: int | None = None):
        self._actor = verify_actor_token(token, trusted_public_key, now=now)
        self._workspace = self._actor.workspace
        self._conn = conn
        self._clock_override = now
        scoped_tenant(conn, self._workspace)

    @property
    def actor(self) -> VerifiedActor:
        return self._actor

    def _guard(self, action: str) -> str:
        current = int(time.time()) if self._clock_override is None else self._clock_override
        _require(self._actor.expires_at > current, "Session has expired")
        require_actor_access(self._actor, self._workspace, action)
        scoped_tenant(self._conn, self._workspace)
        return self._workspace

    def tasks(self):
        return list_review_tasks(self._conn, self._guard("read_queue"))

    def ingest_signed(self, raw: bytes, signature: str, test_app_secret: bytes) -> int:
        """Verify, validate and ingest without trusting caller-supplied inspection flags."""
        workspace = self._guard("ingest_signed_metadata")
        inspected = inspect_signed_meta_event(raw, signature, test_app_secret,
                                               expected_workspace=workspace)
        require_disposable_source(inspected, raw, workspace)
        return store_inspected_events(self._conn, workspace, inspected)

    def assign(self, platform: str, event_ref: str, agent: str) -> bool:
        return assign_review_agent(self._conn, self._guard("assign_human"),
                                   platform, event_ref, agent)

    def review_consent(self, platform: str, event_ref: str, purpose: str,
                       state: str, evidence_ref: str, reviewer: str) -> None:
        self._guard("record_consent_review")
        _require(reviewer == self._actor.actor_ref.replace("SIM-ACTOR-", "SIM-AGENT-"),
                 "Reviewer identity not bound to token")
        return record_consent_evidence(
            self._conn, self._workspace, platform, event_ref,
            purpose, state, evidence_ref, reviewer,
        )

    def protect_note(self, master: bytes, platform: str, account: str,
                     event_ref: str, note: bytes) -> str:
        return store_private_evidence(
            self._conn, self._guard("write_protected_evidence"),
            master, platform, account, event_ref, note,
        )

    def read_note(self, master: bytes, platform: str, account: str,
                  event_ref: str) -> bytes | None:
        return read_private_evidence(
            self._conn, self._guard("read_protected_evidence"),
            master, platform, account, event_ref,
        )
