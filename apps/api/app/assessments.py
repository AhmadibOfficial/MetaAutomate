"""Authenticated, immutable assessment reports: first Operational Core capability.

An explicit user request executes a deterministic assessment and stores an
auditable receipt. This is not model inference or external workflow execution.
"""
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from psycopg.types.json import Jsonb

from app.assessment_engine import (
    AssessmentInput, VERSION, canonical_hash, input_document,
    produce_report, questionnaire,
)
from app.authn import TenantSession, get_tenant_session, require_role

router = APIRouter(prefix="/v1/assessments", tags=["operational-assessments"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]
READ_ROLES = {"OWNER", "ADMIN", "OPERATOR", "VIEWER"}
WRITE_ROLES = {"OWNER", "ADMIN", "OPERATOR"}
KEY_FORMAT = re.compile(r"[A-Za-z0-9_.:-]{12,100}")


def _verified_receipt(row: dict) -> dict:
    """Verify persisted input, output and deterministic scoring before disclosure."""
    try:
        model = AssessmentInput.model_validate({
            "business_label": row["business_label"],
            "objective": row["objective"],
            "answers": row["answers"],
        })
        evidence = input_document(model)
        recomputed = produce_report(model)
        valid = (
            row["scoring_version"] == VERSION
            and row["input_sha256"] == canonical_hash(evidence)
            and row["report_sha256"] == canonical_hash(recomputed)
            and row["report"] == recomputed
        )
    except (ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise HTTPException(status_code=409, detail="Stored assessment calculation or evidence integrity mismatch")
    return {
        "assessment_id": str(row["id"]),
        "status": "COMPLETED",
        "verification_status": "CALCULATION_VERIFIED",
        "receipt": {
            "scoring_version": row["scoring_version"],
            "input_sha256": row["input_sha256"],
            "report_sha256": row["report_sha256"],
            "created_at": row["created_at"],
            "verification_scope": "Saved input and deterministic scoring only",
        },
        "report": row["report"],
        "external_actions_executed": False
    }


@router.get("/questions")
def get_questions(session: Session):
    require_role(session, READ_ROLES)
    return questionnaire()


@router.get("")
def list_assessments(session: Session, limit: Annotated[int, Query(ge=1, le=50)] = 20):
    require_role(session, READ_ROLES)
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT id, business_label, objective, created_at "
            "FROM digital_assessments WHERE organization_id=%s "
            "ORDER BY created_at DESC, id DESC LIMIT %s",
            (session.principal.organization_id, limit),
        )
        items = cur.fetchall()
    return {"items": [
        {**row, "assessment_id": str(row["id"])} for row in items
    ]}


@router.post("", status_code=201)
def run_assessment(
    payload: AssessmentInput,
    session: Session,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    consent: Annotated[str | None, Header(alias="X-Assessment-Consent")] = None,
):
    require_role(session, WRITE_ROLES)
    if not idempotency_key or KEY_FORMAT.fullmatch(idempotency_key) is None:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 12-100 safe characters")
    if consent != "generate-report":
        raise HTTPException(status_code=403, detail="Explicit report-generation authorization is required")
    inputs = input_document(payload)
    report = produce_report(payload)
    input_hash = canonical_hash(inputs)
    report_hash = canonical_hash(report)
    org, actor = session.principal.organization_id, session.principal.user_id
    with session.conn.cursor() as cur:
        # The unique organization/key constraint serializes concurrent retries.
        cur.execute(
            "INSERT INTO digital_assessments "
            "(organization_id,created_by_user_id,business_label,objective,answers,report,"
            "input_sha256,report_sha256,scoring_version,request_key) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (organization_id,request_key) DO NOTHING RETURNING id",
            (org, actor, payload.business_label, payload.objective,
             Jsonb(inputs["answers"]), Jsonb(report), input_hash, report_hash,
             VERSION, idempotency_key),
        )
        inserted = cur.fetchone()
        if inserted:
            cur.execute(
                "INSERT INTO audit_events "
                "(organization_id,actor_type,actor_user_id,action,entity_type,"
                "entity_id,idempotency_key,metadata) "
                "VALUES (%s,'USER',%s,'ASSESSMENT_REPORT_GENERATED','ASSESSMENT',%s,%s,%s)",
                (org, actor, inserted["id"], idempotency_key,
                 Jsonb({"scoring_version": VERSION, "input_sha256": input_hash,
                        "report_sha256": report_hash,
                        "external_actions_executed": False})),
            )
        cur.execute(
            "SELECT id,business_label,objective,answers,report,input_sha256,"
            "report_sha256,scoring_version,created_at "
            "FROM digital_assessments WHERE organization_id=%s AND request_key=%s",
            (org, idempotency_key),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=503, detail="Assessment could not be persisted")
    if row["input_sha256"] != input_hash:
        raise HTTPException(status_code=409, detail="Idempotency key reused with different answers")
    verified = _verified_receipt(row)
    # Commit atomically persisted report and audit before returning its receipt.
    session.conn.commit()
    return verified


@router.get("/{assessment_id}")
def get_assessment(assessment_id: UUID, session: Session):
    require_role(session, READ_ROLES)
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT id,business_label,objective,answers,report,input_sha256,"
            "report_sha256,scoring_version,created_at "
            "FROM digital_assessments WHERE organization_id=%s AND id=%s",
            (session.principal.organization_id, assessment_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Assessment report not found")
    return _verified_receipt(row)
