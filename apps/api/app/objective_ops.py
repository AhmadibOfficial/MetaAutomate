"""Tenant-scoped Objective Operations: atomic draft persistence and human review.

No route transitions a workflow into execution or activates any capability.
"""
import hashlib
import json
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from app.authn import TenantSession, get_tenant_session, require_role
from app.objectives import PreviewRequest, build_preview

router = APIRouter(prefix="/v1/objective-operations", tags=["objective-operations"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]
READ_ROLES = {"OWNER", "ADMIN", "OPERATOR", "VIEWER"}
WRITE_ROLES = {"OWNER", "ADMIN", "OPERATOR"}
REVIEW_ROLES = {"OWNER", "ADMIN"}


class PlanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    reason: str = Field(min_length=5, max_length=500)


def _json_hash(payload: PreviewRequest) -> str:
    normalized = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _plan_for_session(cur, payload: PreviewRequest) -> dict:
    requested = payload.requested_capability_ids
    cur.execute(
        "SELECT capability_id, name, domain, release, lifecycle_status, is_enabled "
        "FROM capability_definitions WHERE capability_id = ANY(%s::text[])",
        (requested,),
    )
    capabilities = cur.fetchall()
    cur.execute(
        "SELECT capability_id, depends_on_capability_id "
        "FROM capability_dependencies WHERE capability_id = ANY(%s::text[])",
        (requested,),
    )
    dependencies = cur.fetchall()
    return build_preview(payload, capabilities, dependencies)


def _audit(cur, session: TenantSession, action: str, entity_id: UUID,
           metadata: dict, key: str | None = None) -> None:
    cur.execute(
        "INSERT INTO audit_events "
        "(organization_id, actor_type, actor_user_id, action, entity_type, "
        "entity_id, idempotency_key, metadata) "
        "VALUES (%s, 'USER', %s, %s, 'OBJECTIVE', %s, %s, %s)",
        (session.principal.organization_id, session.principal.user_id,
         action, entity_id, key, Jsonb(metadata)),
    )


@router.post("", status_code=201)
def create_objective(
    payload: PreviewRequest,
    session: Session,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    require_role(session, WRITE_ROLES)
    if not idempotency_key or not re.fullmatch(r"[A-Za-z0-9_.:-]{12,100}", idempotency_key):
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 12-100 safe characters")
    org = session.principal.organization_id
    request_hash = _json_hash(payload)
    with session.conn.cursor() as cur:
        cur.execute(
            "INSERT INTO idempotency_keys "
            "(organization_id, scope, idempotency_key, request_hash, status, expires_at) "
            "VALUES (%s, 'OBJECTIVE_CREATE', %s, %s, 'IN_PROGRESS', now()+interval '24 hours') "
            "ON CONFLICT (organization_id, scope, idempotency_key) DO NOTHING RETURNING id",
            (org, idempotency_key, request_hash),
        )
        inserted = cur.fetchone() is not None
        cur.execute(
            "SELECT request_hash, status, response_body FROM idempotency_keys "
            "WHERE organization_id=%s AND scope='OBJECTIVE_CREATE' AND idempotency_key=%s "
            "FOR UPDATE", (org, idempotency_key),
        )
        existing = cur.fetchone()
        if existing["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key reused with different payload")
        if existing["status"] == "COMPLETED":
            return existing["response_body"]
        # An in-progress key can only be seen after conflicting transactions
        # finish; it cannot be reused to create a duplicate objective.
        if not inserted:
            raise HTTPException(status_code=409, detail="Concurrent objective creation")
        plan = _plan_for_session(cur, payload)

        cur.execute(
            "INSERT INTO objectives "
            "(organization_id, title, description, execution_mode, initiated_by_user_id, "
            "input_context, desired_outcome, metadata) "
            "VALUES (%s,%s,%s,'ASSIST',%s,%s,%s,%s) RETURNING id",
            (org, payload.title, payload.description, session.principal.user_id,
             Jsonb({"constraints": payload.constraints,
                    "requested_capability_ids": payload.requested_capability_ids}),
             Jsonb({"success_criteria": [x.model_dump() for x in payload.success_criteria]}),
             Jsonb({"planner_version": "1.0", "execution_allowed": False})),
        )
        objective_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO workflows "
            "(organization_id, objective_id, workflow_type, state, execution_mode, context, result) "
            "VALUES (%s,%s,'OBJECTIVE_PLAN_PREVIEW','DRAFT','ASSIST',%s,%s) RETURNING id",
            (org, objective_id,
             Jsonb({"planner_version": "1.0"}),
             Jsonb({"mode": "PLAN_PREVIEW_ONLY", "execution_allowed": False})),
        )
        workflow_id = cur.fetchone()["id"]
        nodes = plan["work_graph"]
        task_ids = {}
        for seq, node in enumerate(nodes):
            cur.execute(
                "INSERT INTO tasks "
                "(organization_id, workflow_id, task_type, name, sequence_no, capability_key, input) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (org, workflow_id, node["type"], node["summary"], seq,
                 node.get("capability_id"), Jsonb({"blocked": True})),
            )
            task_ids[node["step_id"]] = cur.fetchone()["id"]
        for node in nodes:
            for prerequisite in node["depends_on"]:
                cur.execute(
                    "INSERT INTO task_dependencies "
                    "(organization_id, task_id, depends_on_task_id) VALUES (%s,%s,%s)",
                    (org, task_ids[node["step_id"]], task_ids[prerequisite]),
                )
        cur.execute(
            "INSERT INTO approvals "
            "(organization_id, workflow_id, action_type, requested_action) "
            "VALUES (%s,%s,'PLAN_REVIEW',%s) RETURNING id",
            (org, workflow_id, Jsonb({"objective_id": str(objective_id),
                                      "execution_allowed": False})),
        )
        approval_id = cur.fetchone()["id"]
        response = {
            "objective_id": str(objective_id),
            "workflow_id": str(workflow_id),
            "review_id": str(approval_id),
            "status": "DRAFT",
            "review_status": "PENDING",
            "plan_steps": len(nodes),
            "execution_allowed": False,
            "persisted": True,
        }
        _audit(cur, session, "OBJECTIVE_DRAFT_CREATED", objective_id,
               {"workflow_id": str(workflow_id), "step_count": len(nodes)}, idempotency_key)
        cur.execute(
            "UPDATE idempotency_keys SET status='COMPLETED', response_code=201, "
            "response_body=%s, resource_type='OBJECTIVE', resource_id=%s, completed_at=now() "
            "WHERE organization_id=%s AND scope='OBJECTIVE_CREATE' AND idempotency_key=%s",
            (Jsonb(response), objective_id, org, idempotency_key),
        )
        # Make the successful write visible before the HTTP response is sent.
        # Yield-dependency cleanup otherwise commits after the browser can issue a GET.
        session.conn.commit()
        return response


@router.get("")
def list_objectives(session: Session, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    require_role(session, READ_ROLES)
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT o.id, o.title, o.status, o.created_at, o.lock_version, "
            "review.status AS review_status "
            "FROM objectives o LEFT JOIN LATERAL ("
            " SELECT a.status FROM workflows w JOIN approvals a "
            " ON a.organization_id=w.organization_id AND a.workflow_id=w.id "
            " WHERE w.organization_id=o.organization_id AND w.objective_id=o.id "
            " AND w.workflow_type='OBJECTIVE_PLAN_PREVIEW' AND a.action_type='PLAN_REVIEW' "
            " ORDER BY a.requested_at DESC LIMIT 1"
            ") review ON true "
            "WHERE o.organization_id=%s ORDER BY o.created_at DESC, o.id LIMIT %s",
            (session.principal.organization_id, limit),
        )
        return {"items": cur.fetchall()}


@router.get("/capabilities")
def workspace_capabilities(session: Session):
    """Read-only catalog for the browser; no activation or execution rights."""
    require_role(session, READ_ROLES)
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT capability_id, name, domain, release, lifecycle_status, is_enabled "
            "FROM capability_definitions ORDER BY domain, capability_id LIMIT 100"
        )
        items = cur.fetchall()
        cur.execute(
            "SELECT capability_id, depends_on_capability_id "
            "FROM capability_dependencies ORDER BY capability_id, depends_on_capability_id"
        )
        links = cur.fetchall()
    deps: dict[str, list[str]] = {}
    for row in links:
        deps.setdefault(row["capability_id"], []).append(row["depends_on_capability_id"])
    return {"items": [
        {**item, "dependencies": deps.get(item["capability_id"], []),
         "execution_ready": False}
        for item in items
    ]}


@router.get("/{objective_id}")
def get_objective(objective_id: UUID, session: Session):
    require_role(session, READ_ROLES)
    org = session.principal.organization_id
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, description, status, execution_mode, input_context, "
            "desired_outcome, created_at, lock_version "
            "FROM objectives WHERE organization_id=%s AND id=%s",
            (org, objective_id),
        )
        obj = cur.fetchone()
        if obj is None:
            raise HTTPException(status_code=404, detail="Objective not found")
        cur.execute(
            "SELECT id, state, execution_mode, result FROM workflows "
            "WHERE organization_id=%s AND objective_id=%s "
            "AND workflow_type='OBJECTIVE_PLAN_PREVIEW' ORDER BY created_at DESC LIMIT 1",
            (org, objective_id),
        )
        workflow = cur.fetchone()
        if workflow is None:
            return {
                "objective": obj,
                "workflow": None,
                "tasks": [],
                "task_dependencies": [],
                "review": None,
                "execution_allowed": False,
            }
        cur.execute(
            "SELECT id, task_type, name, sequence_no, capability_key, state "
            "FROM tasks WHERE organization_id=%s AND workflow_id=%s ORDER BY sequence_no",
            (org, workflow["id"]),
        )
        tasks = cur.fetchall()
        cur.execute(
            "SELECT task_id, depends_on_task_id FROM task_dependencies "
            "WHERE organization_id=%s AND task_id=ANY(%s::uuid[])",
            (org, [row["id"] for row in tasks]),
        )
        links = cur.fetchall()
        cur.execute(
            "SELECT id, status, decision_reason, decided_at "
            "FROM approvals WHERE organization_id=%s AND workflow_id=%s "
            "AND action_type='PLAN_REVIEW' LIMIT 1",
            (org, workflow["id"]),
        )
        review = cur.fetchone()
        return {
            "objective": obj, "workflow": workflow, "tasks": tasks,
            "task_dependencies": links, "review": review,
            "execution_allowed": False,
        }


@router.post("/{objective_id}/review")
def review_plan(objective_id: UUID, decision: PlanDecision, session: Session):
    require_role(session, REVIEW_ROLES)
    org = session.principal.organization_id
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT a.id, a.status, w.id AS workflow_id "
            "FROM approvals a JOIN workflows w "
            "ON w.organization_id=a.organization_id AND w.id=a.workflow_id "
            "WHERE a.organization_id=%s AND w.objective_id=%s "
            "AND a.action_type='PLAN_REVIEW' FOR UPDATE OF a",
            (org, objective_id),
        )
        review = cur.fetchone()
        if review is None:
            raise HTTPException(status_code=404, detail="Objective review not found")
        if review["status"] != "PENDING":
            raise HTTPException(status_code=409, detail="Plan already reviewed")
        cur.execute(
            "UPDATE approvals SET status=%s, decision_reason=%s, "
            "decided_by_user_id=%s, decided_at=now() "
            "WHERE organization_id=%s AND id=%s",
            (decision.decision, decision.reason, session.principal.user_id, org, review["id"]),
        )
        _audit(cur, session, "OBJECTIVE_PLAN_REVIEWED", objective_id,
               {"decision": decision.decision, "review_id": str(review["id"])})
        session.conn.commit()
        return {
            "objective_id": str(objective_id),
            "review_status": decision.decision,
            "execution_allowed": False,
            "workflow_state": "DRAFT",
        }
