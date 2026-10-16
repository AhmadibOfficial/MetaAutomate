"""P2-03s disposable-only Meta lead CRM repository.

No HTTP endpoint, production migration, provider calls, or actual customer data.
Requires an ephemeral PostgreSQL CI database whose roles are authenticated via
separate database-login credentials. Keys are generated for test sessions only;
real data and external provider credentials are deliberately unsupported.
"""
from __future__ import annotations

import json
import re
import secrets
from hashlib import sha256
from uuid import UUID
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .synthetic_growth_autopilot import SyntheticGrowthError

TENANTS = {
    "academy_demo": UUID("11111111-1111-4111-8111-111111111111"),
    "bespoke_demo": UUID("22222222-2222-4222-8222-222222222222"),
}
SIM = re.compile(r"SIM-[A-Z0-9-]{3,48}\Z")
AGENT = re.compile(r"SIM-AGENT-[A-Z0-9-]{2,40}\Z")


def check(condition: bool, error: str):
    if not condition:
        raise SyntheticGrowthError(error)


def scoped_tenant(conn, workspace: str) -> UUID:
    check(workspace in TENANTS, "Unknown workspace")
    db_name = conn.execute("SELECT current_database()").fetchone()[0]
    check(db_name == "meta_stage_ci", "Not the disposable PostgreSQL rehearsal")
    row = conn.execute("SELECT meta_stage.session_tenant()").fetchone()
    check(row and row[0] == TENANTS[workspace], "Authenticated tenant mismatch")
    return row[0]


def store_inspected_events(conn, workspace: str, inspection: dict) -> int:
    """Idempotent durable inserts of minimal signed synthetic metadata."""
    tenant = scoped_tenant(conn, workspace)
    check(type(inspection) is dict
          and inspection.get("classification") == "SYNTHETIC_VERIFIED_SIGNATURE_ONLY"
          and inspection.get("workspace") == workspace
          and inspection.get("signature_check") == "LOCAL_HMAC_PASSED"
          and inspection.get("live_webhook_endpoint") is False
          and inspection.get("messages_sent") == 0, "Invalid source-only inspection")
    records = inspection.get("events")
    check(type(records) is list and 1 <= len(records) <= 50,
          "No validated synthetic records")
    source_digest = inspection.get("raw_body_sha256")
    check(type(source_digest) is str and re.fullmatch(r"[0-9a-f]{64}", source_digest),
          "Missing source digest")
    result = 0
    with conn.transaction():
        for event in records:
            check(type(event) is dict and event.get("workspace") == workspace
                  and event.get("customer_contact") is None
                  and event.get("outbound_eligible") is False,
                  "Unsafe event fields")
            platform, account, event_id = (
                event.get("platform"), event.get("account_ref"), event.get("event_ref"))
            check(platform in ("FACEBOOK", "INSTAGRAM", "WHATSAPP")
                  and type(account) is str and SIM.fullmatch(account)
                  and type(event_id) is str and SIM.fullmatch(event_id),
                  "Unexpected event identifiers")
            permitted = conn.execute(
                "SELECT 1 FROM meta_stage.accounts "
                "WHERE tenant_id=%s AND platform=%s AND account_ref=%s",
                (tenant, platform, account),
            ).fetchone()
            check(permitted is not None, "Account not registered for authenticated tenant")
            inserted = conn.execute(
                "INSERT INTO meta_stage.events "
                "(tenant_id,platform,account_ref,event_ref,payload_sha256,event_kind)"
                " VALUES (%s,%s,%s,%s,%s,%s)"
                " ON CONFLICT DO NOTHING RETURNING event_ref",
                (tenant, platform, account, event_id, source_digest, event["kind"]),
            ).fetchone()
            if inserted:
                conn.execute(
                    "INSERT INTO meta_stage.review_tasks "
                    "(tenant_id,platform,account_ref,event_ref) VALUES (%s,%s,%s,%s)",
                    (tenant, platform, account, event_id),
                )
                result += 1
            else:
                previous = conn.execute(
                    "SELECT payload_sha256, event_kind FROM meta_stage.events "
                    "WHERE tenant_id=%s AND platform=%s AND account_ref=%s AND event_ref=%s",
                    (tenant, platform, account, event_id),
                ).fetchone()
                check(previous == (source_digest, event["kind"]),
                      "Conflicting repeat event cannot be silently accepted")
    return result


def list_review_tasks(conn, workspace: str) -> list[dict[str, Any]]:
    tenant = scoped_tenant(conn, workspace)
    rows = conn.execute(
        "SELECT platform,event_ref,state,agent_ref,outbound_enabled "
        "FROM meta_stage.review_tasks WHERE tenant_id=%s "
        "ORDER BY platform,event_ref",
        (tenant,),
    ).fetchall()
    return [{"platform": p, "event_ref": e, "state": s,
             "agent_ref": a, "outbound_enabled": flag}
            for p, e, s, a, flag in rows]


def assign_review_agent(conn, workspace: str, platform: str, event_ref: str, agent: str) -> bool:
    tenant = scoped_tenant(conn, workspace)
    check(type(agent) is str and AGENT.fullmatch(agent) is not None,
          "Only fictional reviewer references accepted")
    check(type(event_ref) is str and SIM.fullmatch(event_ref)
          and platform in ("FACEBOOK", "INSTAGRAM", "WHATSAPP"),
          "Invalid review reference")
    with conn.transaction():
        result = conn.execute(
            "UPDATE meta_stage.review_tasks "
            "SET state='ASSIGNED_SYNTHETIC_HUMAN', agent_ref=%s "
            "WHERE tenant_id=%s AND platform=%s AND event_ref=%s "
            "AND state='HUMAN_REVIEW_REQUIRED' RETURNING event_ref",
            (agent, tenant, platform, event_ref),
        ).fetchone()
    return result is not None


def record_consent_evidence(conn, workspace: str, platform: str, event_ref: str,
                            purpose: str, state: str, evidence_ref: str,
                            actor_ref: str) -> None:
    tenant = scoped_tenant(conn, workspace)
    check(platform in ("FACEBOOK", "INSTAGRAM", "WHATSAPP")
          and type(event_ref) is str and SIM.fullmatch(event_ref)
          and purpose in ("SERVICE", "MARKETING")
          and state in ("UNVERIFIED", "DOCUMENTED_EXAMPLE", "REVOKED_EXAMPLE")
          and type(evidence_ref) is str and SIM.fullmatch(evidence_ref)
          and type(actor_ref) is str and AGENT.fullmatch(actor_ref),
          "Not a permitted synthetic consent review")
    # This does NOT create independently verified customer consent.
    with conn.transaction():
        account = conn.execute(
            "SELECT account_ref FROM meta_stage.events "
            "WHERE tenant_id=%s AND platform=%s AND event_ref=%s",
            (tenant, platform, event_ref),
        ).fetchone()
        check(account is not None, "Consent evidence refers to unknown tenant event")
        if state == "DOCUMENTED_EXAMPLE":
            prior_revoked = conn.execute(
                "SELECT 1 FROM meta_stage.consent_reviews "
                "WHERE tenant_id=%s AND platform=%s AND event_ref=%s "
                "AND purpose=%s AND reviewed_state='REVOKED_EXAMPLE' LIMIT 1",
                (tenant, platform, event_ref, purpose),
            ).fetchone()
            check(prior_revoked is None, "Revoked consent cannot be silently regranted")
        conn.execute(
            "INSERT INTO meta_stage.consent_reviews "
            "(tenant_id,platform,account_ref,event_ref,purpose,reviewed_state,"
            "evidence_ref,actor_ref) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (tenant, platform, account[0], event_ref, purpose, state,
             evidence_ref, actor_ref),
        )


def derive_ephemeral_tenant_key(master: bytes, tenant: UUID) -> bytes:
    check(type(master) is bytes and len(master) == 32, "Ephemeral master key required")
    return HKDF(algorithm=hashes.SHA256(), length=32,
                salt=tenant.bytes, info=b"metaautomate-p2-03s-disposable-only").derive(master)


def _aad(tenant: UUID, platform: str, account: str, event_ref: str) -> bytes:
    return (str(tenant) + "|" + platform + "|" + account + "|" + event_ref).encode("ascii")


def encrypt_evidence_note(master: bytes, tenant: UUID, platform: str,
                          account: str, event_ref: str, note: bytes) -> tuple[bytes, bytes]:
    check(type(note) is bytes and 1 <= len(note) <= 2048 and b"\x00" not in note,
          "Only bounded fictional notes")
    key = derive_ephemeral_tenant_key(master, tenant)
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, note, _aad(tenant, platform, account, event_ref))
    return nonce, ciphertext


def store_private_evidence(conn, workspace: str, master: bytes, platform: str,
                           account: str, event_ref: str, sample_note: bytes):
    tenant = scoped_tenant(conn, workspace)
    check(platform in ("FACEBOOK", "INSTAGRAM", "WHATSAPP") and
          all(type(x) is str and SIM.fullmatch(x) for x in (account, event_ref)),
          "Unsafe evidence scope")
    check(sample_note.startswith(b"SIMULATED:"), "Never store actual customer data")
    nonce, blob = encrypt_evidence_note(master, tenant, platform, account,
                                        event_ref, sample_note)
    with conn.transaction():
        conn.execute(
            "INSERT INTO meta_stage.private_evidence "
            "(tenant_id,platform,account_ref,event_ref,nonce,ciphertext)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            (tenant, platform, account, event_ref, nonce, blob),
        )
    return sha256(blob).hexdigest()


def read_private_evidence(conn, workspace: str, master: bytes, platform: str,
                          account: str, event_ref: str) -> bytes | None:
    tenant = scoped_tenant(conn, workspace)
    row = conn.execute(
        "SELECT nonce,ciphertext FROM meta_stage.private_evidence "
        "WHERE tenant_id=%s AND platform=%s AND account_ref=%s AND event_ref=%s",
        (tenant, platform, account, event_ref),
    ).fetchone()
    if row is None:
        return None
    return AESGCM(derive_ephemeral_tenant_key(master, tenant)).decrypt(
        bytes(row[0]), bytes(row[1]), _aad(tenant, platform, account, event_ref))
