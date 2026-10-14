"""AMBOY M1: authenticated MetaAutomate-only no-model admission test.

Disabled by default. No OneCall identities, model calls, retrieval, workflows,
bookings, payments or external actions. All accepted requests create durable
tenant-scoped metadata receipts; no raw user message is stored in the ledger.
"""
import hashlib
import json
import os
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from app.authn import TenantSession, get_tenant_session, require_role

router = APIRouter(prefix="/v1/amboy", tags=["amboy-m1"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]
DRY_RUN_ROLES = {"OWNER", "ADMIN", "OPERATOR"}
LIMIT_PER_HOUR = 10
NO_MODEL_REPLY = (
    "AMBOY M1 is an authenticated access test only. "
    "No AI model, business record lookup, booking, payment, or other action was performed."
)


class ContextHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surface: Literal["metaautomate_workspace", "onecall_app"] | None = None
    resource_id: str | None = Field(default=None, max_length=128)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_request_id: UUID
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=8000)
    locale: str | None = Field(default=None, min_length=2, max_length=35)
    requested_mode: Literal["answer", "prepare_plan", "propose_action"] = "answer"
    context_hint: ContextHint | None = None


def _payload_digest(payload: TurnRequest) -> str:
    canonical = json.dumps(payload.model_dump(mode="json", exclude_none=True),
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _receipt(event_id: UUID, conversation_id: UUID, client_id: UUID) -> dict:
    return {
        "request_id": str(client_id),
        "conversation_id": str(conversation_id),
        "status": "unsupported",
        "reply": NO_MODEL_REPLY,
        "execution_performed": False,
        "evidence_refs": [f"amboy:m1:{event_id}"],
    }


@router.post("/turn")
def dry_run_turn(payload: TurnRequest, session: Session):
    # Environment opt-in is deliberately independent of WORKSPACE_AUTH_MODE.
    if os.environ.get("AMBOY_M1_ENABLED") != "1":
        raise HTTPException(status_code=404, detail="AMBOY gateway is disabled")
    require_role(session, DRY_RUN_ROLES)

    # A OneCall surface hint NEVER implies an authenticated OneCall identity.
    # No OneCall route exists until its real backend supplies server-side identity.
    if payload.context_hint and (
        payload.context_hint.surface == "onecall_app"
        or payload.context_hint.resource_id is not None
    ):
        raise HTTPException(status_code=403, detail="Product context is not authorized in M1")
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message must contain visible text")

    org = session.principal.organization_id
    actor = session.principal.user_id
    fingerprint = _payload_digest(payload)
    with session.conn.cursor() as cur:
        # Serialize same-actor requests, including retries, to enforce a strict
        # per-user quota rather than a best-effort in-process counter.
        cur.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"amboy:m1:metaautomate:{org}:{actor}",),
        )
        cur.execute(
            "SELECT id, conversation_id, payload_sha256 "
            "FROM amboy_m1_requests "
            "WHERE organization_id=%s AND actor_user_id=%s "
            "AND product='metaautomate' AND client_request_id=%s",
            (org, actor, payload.client_request_id),
        )
        existing = cur.fetchone()
        if existing:
            if existing["payload_sha256"] != fingerprint:
                raise HTTPException(status_code=409, detail="Request ID reused with different content")
            return _receipt(existing["id"], existing["conversation_id"],
                            payload.client_request_id)

        cur.execute(
            "INSERT INTO amboy_m1_quotas "
            "(organization_id, actor_user_id, product, hour_start, request_count) "
            "VALUES (%s,%s,'metaautomate',date_trunc('hour',now()),1) "
            "ON CONFLICT (organization_id, actor_user_id, product, hour_start) "
            "DO UPDATE SET request_count=amboy_m1_quotas.request_count+1 "
            "WHERE amboy_m1_quotas.request_count < %s "
            "RETURNING request_count",
            (org, actor, LIMIT_PER_HOUR),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=429, detail="AMBOY M1 hourly quota exceeded")

        conversation_id = payload.conversation_id or uuid4()
        cur.execute(
            "INSERT INTO amboy_m1_requests "
            "(organization_id,actor_user_id,product,client_request_id,"
            "conversation_id,payload_sha256) "
            "VALUES (%s,%s,'metaautomate',%s,%s,%s) RETURNING id",
            (org, actor, payload.client_request_id, conversation_id, fingerprint),
        )
        receipt_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO audit_events "
            "(organization_id,actor_type,actor_user_id,action,entity_type,"
            "entity_id,request_id,metadata) "
            "VALUES (%s,'USER',%s,'AMBOY_M1_NO_MODEL','AMBOY_M1',%s,%s,%s)",
            (org, actor, receipt_id, payload.client_request_id,
             Jsonb({"product": "metaautomate", "payload_sha256": fingerprint,
                    "model_called": False, "execution_performed": False})),
        )
    session.conn.commit()
    return _receipt(receipt_id, conversation_id, payload.client_request_id)
