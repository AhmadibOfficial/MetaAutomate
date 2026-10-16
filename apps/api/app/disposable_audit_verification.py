"""P2-03t: verify a persisted per-tenant SHA-256 audit chain.

Provides detection of modifications/gaps within the accessible chain and optional
comparison against a previously retained trusted head. Does not make PostgreSQL
superuser changes impossible or substitute for immutable external audit anchoring.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

from .disposable_meta_crm import scoped_tenant
from .synthetic_growth_autopilot import SyntheticGrowthError

HEX = re.compile(r"[0-9a-f]{64}\Z")


def verify_tenant_audit(conn, workspace: str, trusted_head: str | None = None) -> dict:
    tenant = scoped_tenant(conn, workspace)
    if trusted_head is not None and (
        type(trusted_head) is not str or HEX.fullmatch(trusted_head) is None
    ):
        raise SyntheticGrowthError("Invalid external audit checkpoint")
    data = conn.execute(
        "SELECT sequence_number, source_login::text, payload::text, "
        "previous_sha256, entry_sha256 FROM meta_stage.audit_events "
        "WHERE tenant_id=%s ORDER BY sequence_number",
        (tenant,),
    ).fetchall()
    predecessor = "0"*64
    for i, row in enumerate(data, start=1):
        sequence, login, payload, prior, stored = row
        if (sequence != i or prior != predecessor
            or type(payload) is not str
            or HEX.fullmatch(stored) is None
            or sha256((prior+":"+payload).encode("utf-8")).hexdigest() != stored
            or json.loads(payload).get("tenant") != str(tenant)):
            raise SyntheticGrowthError("Audit chain invalid or incomplete")
        predecessor = stored
    if trusted_head is not None and predecessor != trusted_head:
        raise SyntheticGrowthError("Persisted audit head differs from trusted checkpoint")
    return {
        "workspace": workspace, "entry_count": len(data),
        "head_sha256": predecessor,
        "integrity_verified_against_stored_chain": True,
        "external_immutable_anchor_verified": False,
        "operator_identity_live_verified": False,
        "production_ready": False,
    }
