"""P2-03z: authorized, append-only aggregate business outcome evidence.

This is a **real-data-capable** backend (not a synthetic model). It is not
registered unless the operator separately enables a gated private OIDC API.
No upload of personal/customer rows, no AI inference or external integration.
Input digests and reviewer attestations do NOT establish that accounting
source documents are genuine or that MetaAutomate caused a financial result.

This module is prospective until F04-F08 pass, migration 016 is separately
approved on an isolated staging database and pilot consent is verified.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from psycopg.types.json import Jsonb

from app.authn import TenantSession, get_tenant_session, require_role

router=APIRouter(prefix="/v1/pilot-outcomes",tags=["pilot-evidence"])
Session=Annotated[TenantSession,Depends(get_tenant_session)]
READ={"OWNER","ADMIN","OPERATOR","VIEWER"}
SUBMIT={"OWNER","ADMIN","OPERATOR"}
REVIEW={"OWNER","ADMIN"}
MAX_MINOR=1_000_000_000_000
MONEY_FIELDS=(
    "gross_sales_minor","variable_cost_minor","marketing_spend_minor",
    "processing_fees_minor","fulfillment_cost_minor","software_cost_minor",
    "refunds_minor",
)
COST_FIELDS=MONEY_FIELDS[1:]
HASH=re.compile(r"[0-9a-f]{64}\Z")
KEY=re.compile(r"[A-Za-z0-9_.:-]{12,100}\Z")

class OutcomePeriodInput(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    project_key:str=Field(min_length=8,max_length=64,pattern=r"^[a-z][a-z0-9_-]{7,63}$")
    period_kind:Literal["BASELINE","CURRENT"]
    period_start:date
    period_end:date
    currency:str=Field(min_length=3,max_length=3,pattern=r"^[A-Z]{3}$")
    gross_sales_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    variable_cost_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    marketing_spend_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    processing_fees_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    fulfillment_cost_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    software_cost_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    refunds_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    completed_orders:StrictInt=Field(ge=0,le=10_000_000)
    source_kind:Literal["BOOKKEEPING_EXPORT","POS_SUMMARY","MANUAL_AGGREGATE"]
    source_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    consent_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def period_is_observed(self):
        days=(self.period_end-self.period_start).days
        if days<0 or days>366 or self.period_end>date.today():
            raise ValueError("Only bounded past or current observation periods allowed")
        return self


class ReviewInput(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    decision:Literal["EVIDENCE_CHECKED","REJECTED"]
    reason:str=Field(min_length=20,max_length=600)
    source_sha256_confirmed:str=Field(pattern=r"^[0-9a-f]{64}$")


def canonical_hash(data:dict)->str:
    return sha256(json.dumps(data,sort_keys=True,separators=(",",":"),
                             ensure_ascii=True,allow_nan=False).encode("ascii")).hexdigest()


def input_document(x:OutcomePeriodInput)->dict:
    return x.model_dump(mode="json")


def measure(x:OutcomePeriodInput)->dict:
    known_costs=sum(getattr(x,k) for k in COST_FIELDS)
    contribution=x.gross_sales_minor-known_costs
    return {
        "currency":x.currency,
        "gross_sales_minor":x.gross_sales_minor,
        "identified_costs_minor":known_costs,
        "contribution_after_identified_costs_minor":contribution,
        "completed_orders":x.completed_orders,
        "average_gross_sale_per_order_minor":(
            x.gross_sales_minor//x.completed_orders if x.completed_orders else None
        ),
        "net_profit_verified":False,
        "attributable_platform_impact_verified":False,
        "source_documents_independently_authenticated":False,
        "calculation_status":"ARITHMETIC_VERIFIED_ONLY",
    }


def _require_key(value:str|None)->str:
    if not value or KEY.fullmatch(value) is None:
        raise HTTPException(422,"Idempotency-Key must be 12-100 safe characters")
    return value


def _evidence(row:dict, review:dict|None=None)->dict:
    try:
        original={k:row[k] for k in OutcomePeriodInput.model_fields}
        x=OutcomePeriodInput.model_validate(original)
        checksum=canonical_hash(input_document(x))
    except (KeyError,TypeError,ValueError):
        raise HTTPException(409,"Stored pilot evidence malformed") from None
    if row["input_sha256"]!=checksum:
        raise HTTPException(409,"Stored pilot evidence changed")
    decision=review["decision"] if review else "PENDING_REVIEW"
    return {
        "period_id":str(row["id"]),
        "project_key":x.project_key,
        "period_kind":x.period_kind,
        "period_start":x.period_start.isoformat(),
        "period_end":x.period_end.isoformat(),
        "measurements":measure(x),
        "review_state":decision,
        "source_provenance_claim":x.source_kind,
        "attestation_hashes":{
            "source_sha256":x.source_sha256,
            "consent_sha256":x.consent_sha256,
            "input_sha256":checksum,
            "review_receipt_sha256":review["reviewer_receipt_sha256"] if review else None,
        },
        "submitted_by_user_id":str(row["submitted_by_user_id"]),
        "source_documents_independently_verified":False,
        "human_consent_independently_verified":False,
        "live_customer_impact_verified":False,
        "external_actions_executed":False,
        "release_ready":False,
    }


def _one(session:TenantSession,period_id:UUID)->tuple[dict,dict|None]:
    org=session.principal.organization_id
    with session.conn.cursor() as cur:
        cur.execute("SELECT * FROM pilot_outcome_periods WHERE "
                    "organization_id=%s AND id=%s",(org,period_id))
        row=cur.fetchone()
        if row is None:raise HTTPException(404,"Period not found in authorized workspace")
        cur.execute("SELECT * FROM pilot_outcome_reviews WHERE "
                    "organization_id=%s AND period_id=%s",(org,period_id))
        review=cur.fetchone()
    return row,review


@router.post("",status_code=201)
def submit_period(
    payload:OutcomePeriodInput,session:Session,
    idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None,
    consent:Annotated[str|None,Header(alias="X-Pilot-Aggregate-Consent")]=None,
):
    require_role(session,SUBMIT)
    _require_key(idempotency_key)
    if consent!="authorized-aggregate-measurement":
        raise HTTPException(403,"Explicit aggregate measurement consent claim required")
    doc=input_document(payload)
    checksum=canonical_hash(doc)
    org=session.principal.organization_id
    user=session.principal.user_id
    fields=list(OutcomePeriodInput.model_fields)
    field_sql=",".join(fields)
    placeholder=",".join(["%s"]*(len(fields)+4))
    params=[org,user,idempotency_key,checksum]+[getattr(payload,f) for f in fields]
    # String-form SQL columns are a fixed, code-owned model definition, never
    # derived from client-supplied keys.
    with session.conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pilot_outcome_periods "
            "(organization_id,submitted_by_user_id,request_key,input_sha256,"+
            field_sql+") VALUES ("+placeholder+") "
            "ON CONFLICT (organization_id,request_key) DO NOTHING RETURNING id",
            params,
        )
        inserted=cur.fetchone()
        if inserted:
            cur.execute(
                "INSERT INTO audit_events "
                "(organization_id,actor_type,actor_user_id,action,entity_type,"
                "entity_id,idempotency_key,metadata) "
                "VALUES (%s,'USER',%s,'PILOT_AGGREGATE_SUBMITTED','PILOT_PERIOD',%s,%s,%s)",
                (org,user,inserted["id"],idempotency_key,Jsonb({
                    "source_sha256":payload.source_sha256,
                    "input_sha256":checksum,
                    "source_independently_verified":False,
                    "external_execution":False,
                }))
            )
        cur.execute(
            "SELECT * FROM pilot_outcome_periods WHERE "
            "organization_id=%s AND request_key=%s",(org,idempotency_key))
        record=cur.fetchone()
    if record is None:raise HTTPException(503,"Evidence persistence not confirmed")
    if record["input_sha256"]!=checksum or record["submitted_by_user_id"]!=user:
        raise HTTPException(409,"Idempotency key already used for a different submission")
    result=_evidence(record)
    session.conn.commit()
    return result


@router.post("/{period_id}/review",status_code=201)
def review_period(period_id:UUID,payload:ReviewInput,session:Session):
    require_role(session,REVIEW)
    org=session.principal.organization_id
    actor=session.principal.user_id
    row,review=_one(session,period_id)
    if row["submitted_by_user_id"]==actor:
        raise HTTPException(403,"Independent reviewer must be different from submitter")
    if row["source_sha256"]!=payload.source_sha256_confirmed:
        raise HTTPException(409,"Reviewed evidence hash does not match submitted source")
    receipt=canonical_hash({
        "period_id":str(period_id),"org":str(org),"reviewer":str(actor),
        "input_sha256":row["input_sha256"],"source_sha256":row["source_sha256"],
        "decision":payload.decision,"reason":payload.reason,
    })
    if review:
        if review["reviewer_receipt_sha256"]!=receipt:
            raise HTTPException(409,"Review is immutable and already decided")
        return _evidence(row,review)
    with session.conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pilot_outcome_reviews "
            "(organization_id,period_id,reviewer_user_id,decision,reason,"
            "source_sha256_confirmed,reviewer_receipt_sha256) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (organization_id,period_id) DO NOTHING RETURNING id",
            (org,period_id,actor,payload.decision,payload.reason,
             payload.source_sha256_confirmed,receipt),
        )
        inserted=cur.fetchone()
        if inserted:
            cur.execute(
                "INSERT INTO audit_events "
                "(organization_id,actor_type,actor_user_id,action,entity_type,"
                "entity_id,metadata) "
                "VALUES (%s,'USER',%s,'PILOT_AGGREGATE_REVIEWED',"
                "'PILOT_PERIOD',%s,%s)",
                (org,actor,period_id,Jsonb({
                    "review_sha256":receipt,"decision":payload.decision,
                    "external_verification":False,
                }))
            )
        cur.execute("SELECT * FROM pilot_outcome_reviews WHERE "
                    "organization_id=%s AND period_id=%s",(org,period_id))
        result_review=cur.fetchone()
    if result_review is None or result_review["reviewer_receipt_sha256"]!=receipt:
        raise HTTPException(409,"Concurrent or conflicting independent review")
    verified=_evidence(row,result_review)
    session.conn.commit()
    return verified


@router.get("/{period_id}")
def get_period(period_id:UUID,session:Session):
    require_role(session,READ)
    return _evidence(*_one(session,period_id))


@router.get("")
def list_periods(session:Session,limit:Annotated[int,Query(ge=1,le=50)]=20):
    require_role(session,READ)
    org=session.principal.organization_id
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT id,project_key,period_kind,period_start,period_end,currency,"
            "input_sha256,created_at FROM pilot_outcome_periods "
            "WHERE organization_id=%s ORDER BY created_at DESC,id DESC LIMIT %s",
            (org,limit),
        )
        data=cur.fetchall()
    return {"items":[{**r,"period_id":str(r["id"])} for r in data],
            "personal_customer_records_returned":0}


@router.get("/compare/periods")
def compare_periods(
    baseline:UUID,current:UUID,session:Session,
):
    require_role(session,READ)
    if baseline==current:raise HTTPException(422,"Different periods are required")
    base=_evidence(*_one(session,baseline))
    now=_evidence(*_one(session,current))
    if (base["review_state"]!="EVIDENCE_CHECKED" or
        now["review_state"]!="EVIDENCE_CHECKED"):
        raise HTTPException(409,"Separate human source-evidence reviews required")
    if (base["period_kind"]!="BASELINE" or now["period_kind"]!="CURRENT" or
        base["project_key"]!=now["project_key"] or
        base["measurements"]["currency"]!=now["measurements"]["currency"] or
        base["period_end"]>=now["period_start"]):
        raise HTTPException(422,"Incompatible, overlapping or mismatched periods")
    b=base["measurements"]["contribution_after_identified_costs_minor"]
    n=now["measurements"]["contribution_after_identified_costs_minor"]
    return {
        "project_key":base["project_key"],
        "currency":base["measurements"]["currency"],
        "baseline_period_id":str(baseline),
        "current_period_id":str(current),
        "baseline_contribution_minor":b,
        "current_contribution_minor":n,
        "descriptive_difference_minor":n-b,
        "financial_causation_attributed_to_metaautomate":False,
        "net_profit_verified":False,
        "source_documents_independently_authenticated":False,
        "outcome_status":"REVIEWED_AGGREGATES_DESCRIPTIVE_ONLY",
        "external_actions_executed":False,
    }
