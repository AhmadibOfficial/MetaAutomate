"""P2-052: private tenant-scoped task execution with downloadable artifacts.

Unlike a plan preview, these jobs compute real outputs. Runtime stays
disabled unless the private OIDC API and migration are explicitly approved.
Neither a completed deterministic task nor a successful local HTTP model
response proves independently verified neural inference or legal rights.
No outgoing email, publishing, payments, code execution or external URLs.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
import os
import re
from typing import Annotated, Literal
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.authn import TenantSession, get_tenant_session, require_role

router=APIRouter(prefix="/v1/private-tasks",tags=["private-task-execution"])
Session=Annotated[TenantSession,Depends(get_tenant_session)]
AUTH_ROLES={"OWNER","ADMIN","OPERATOR"}
READ_ROLES=AUTH_ROLES|{"VIEWER"}
IDEMPOTENCY=re.compile(r"^[A-Za-z0-9_.:-]{12,100}$")
SKU=re.compile(r"^[A-Za-z0-9_-]{2,32}$")
HEX=re.compile(r"^[a-f0-9]{64}$")
MAX_OUTPUT_BYTES=130_000
MAX_HOURLY=20

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,str_strip_whitespace=True)

class Item(Strict):
    sku:str=Field(min_length=2,max_length=32)
    label:str=Field(min_length=2,max_length=100)
    on_hand:StrictInt=Field(ge=0,le=10_000_000)
    reorder_at:StrictInt=Field(ge=0,le=10_000_000)
    unit_cost_minor:StrictInt=Field(ge=0,le=1_000_000_000)

    @model_validator(mode="after")
    def check(self):
        if not SKU.fullmatch(self.sku) or any(ord(c)<32 for c in self.label):
            raise ValueError("Unsafe inventory name or SKU")
        return self

class Inventory(Strict):
    currency:str=Field(pattern=r"^[A-Z]{3}$")
    items:list[Item]=Field(min_length=1,max_length=80)

    @model_validator(mode="after")
    def unique_skus(self):
        values=[item.sku for item in self.items]
        if len(set(values))!=len(values):
            raise ValueError("Duplicate inventory SKU")
        return self

class Graphic(Strict):
    brand:str=Field(min_length=2,max_length=45)
    headline:str=Field(min_length=8,max_length=130)
    message:str=Field(min_length=5,max_length=160)
    theme:Literal["white","navy","blue"]="white"

    @model_validator(mode="after")
    def no_controls(self):
        if any(ord(c)<32 for s in (self.brand,self.headline,self.message) for c in s):
            raise ValueError("Control characters not allowed in graphic text")
        return self

class TextJob(Strict):
    prompt:str=Field(min_length=20,max_length=1200)
    output_kind:Literal["PROJECT_SCOPE","EDUCATIONAL_POST","VIDEO_SCRIPT"]="PROJECT_SCOPE"

    @model_validator(mode="after")
    def no_controls(self):
        if any(ord(c)<32 and c not in "\n\t" for c in self.prompt):
            raise ValueError("Unsafe prompt")
        return self

class Execute(Strict):
    task_type:Literal["INVENTORY_REORDER_CSV","ORIGINAL_BRANDED_SVG","LOCAL_MODEL_TEXT"]
    inventory:Inventory|None=None
    graphic:Graphic|None=None
    text_job:TextJob|None=None

    @model_validator(mode="after")
    def one_matching_payload(self):
        key={
            "INVENTORY_REORDER_CSV":"inventory",
            "ORIGINAL_BRANDED_SVG":"graphic",
            "LOCAL_MODEL_TEXT":"text_job",
        }[self.task_type]
        if sum(getattr(self,field) is not None for field in
               ("inventory","graphic","text_job"))!=1 or getattr(self,key) is None:
            raise ValueError("Exactly one payload matching task_type required")
        return self


def _canonical(payload:dict)->bytes:
    return json.dumps(payload,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")

def _sha(data:bytes)->str:
    return sha256(data).hexdigest()

def _csv_cell(label:str)->str:
    # Formula injection can happen even when a spreadsheet parses valid CSV.
    value=label.strip()
    if value and value[0] in "=+-@\t\r\n":
        return "'"+value
    return value

def inventory_report(data:Inventory)->tuple[bytes,str,str,dict]:
    stream=StringIO(newline="")
    writer=csv.writer(stream,lineterminator="\r\n")
    writer.writerow(["sku","item","on_hand","reorder_at",
                     "reorder_units","unit_cost_minor","stock_value_minor","currency"])
    total_value=0
    alerts=0
    for item in data.items:
        value=item.on_hand*item.unit_cost_minor
        quantity=max(item.reorder_at-item.on_hand,0)
        alerts+=int(quantity>0)
        total_value+=value
        writer.writerow([item.sku,_csv_cell(item.label),item.on_hand,
                         item.reorder_at,quantity,item.unit_cost_minor,
                         value,data.currency])
    output=stream.getvalue().encode("utf-8")
    return (output,"text/csv; charset=utf-8","inventory-reorder.csv",{
        "records_processed":len(data.items),
        "reorder_alerts":alerts,
        "inventory_value_minor":total_value,
        "currency":data.currency,
        "accounting_source_verified":False,
        "result_is_independent_financial_audit":False,
    })

PALETTES={
    "white":("#f8fafc","#142941","#195fa5"),
    "navy":("#071a30","#ffffff","#82b5ff"),
    "blue":("#15539d","#ffffff","#d2e9ff"),
}

def _safe_svg_text(value:str)->str:
    # Explicit XML escaping, no external resources or user-controlled markup.
    return xml_escape(value, {'"':"&quot;","'":"&apos;"})

def branded_graphic(data:Graphic)->tuple[bytes,str,str,dict]:
    bg,fg,accent=PALETTES[data.theme]
    # Text length deliberately bounded, shown as two simple lines rather than
    # relying on a browser-side template, model or opaque asset.
    brand=_safe_svg_text(data.brand)
    line1=_safe_svg_text(data.headline[:64])
    line2=_safe_svg_text(data.headline[64:128])
    message=_safe_svg_text(data.message[:120])
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Original branded business graphic">
<rect width="1200" height="675" fill="{bg}"/>
<rect x="72" y="65" width="1056" height="545" rx="28" fill="none" stroke="{accent}" stroke-width="4"/>
<circle cx="1010" cy="195" r="130" fill="{accent}" fill-opacity=".16"/>
<rect x="94" y="93" width="16" height="44" rx="8" fill="{accent}"/>
<g fill="{fg}" font-family="Arial, Helvetica, sans-serif">
<text x="133" y="124" font-size="26" font-weight="700">{brand}</text>
<text x="102" y="285" font-size="52" font-weight="800">{line1}</text>
<text x="102" y="352" font-size="52" font-weight="800">{line2}</text>
<text x="102" y="475" font-size="28">{message}</text>
<text x="102" y="585" font-size="19">ORIGINAL LAYOUT · CREATED BY METAAUTOMATE</text>
</g>
</svg>'''
    return (svg.encode("utf-8"),"image/svg+xml","original-brand-graphic.svg",{
        "width":1200,"height":675,
        "generated_by":"DETERMINISTIC_GRAPHIC_ENGINE",
        "neural_image_inference":False,"licensing_independently_reviewed":False,
    })

def _local_text(data:TextJob)->tuple[bytes,str,str,dict]:
    # Keep the optional actual model process separate from business tools.
    from app.private_model_worker import generate_text, configured_model
    cfg=configured_model()
    answer=generate_text(data.prompt,data.output_kind,cfg)
    output=answer.encode("utf-8")
    return (output,"text/plain; charset=utf-8","model-generated-text.txt",{
        "model_label":cfg.model,
        "declared_checkpoint_sha256":cfg.digest,
        "local_model_http_response_received":True,
        "independent_neural_inference_attested":False,
        "content_fact_checked":False,"human_approved":False,
    })

def execute_task(payload:Execute)->tuple[bytes,str,str,dict]:
    if payload.task_type=="INVENTORY_REORDER_CSV":
        result=inventory_report(payload.inventory)
    elif payload.task_type=="ORIGINAL_BRANDED_SVG":
        result=branded_graphic(payload.graphic)
    else:
        result=_local_text(payload.text_job)
    if not 0<len(result[0])<=MAX_OUTPUT_BYTES:
        raise HTTPException(502,"Task result exceeds approved output size")
    return result

def _require_idempotency(value:str|None)->str:
    if not value or IDEMPOTENCY.fullmatch(value) is None:
        raise HTTPException(422,"Idempotency-Key must be 12-100 safe characters")
    return value

def _public_record(row:dict)->dict:
    return {
        "id":str(row["id"]),"task_type":row["task_type"],
        "status":row["status"],"input_sha256":row["input_sha256"],
        "artifact_sha256":row["artifact_sha256"],
        "artifact_mime":row["artifact_mime"],
        "artifact_filename":row["artifact_filename"],
        "artifact_bytes":row["artifact_bytes"],
        "result_metadata":row["result_metadata"],
        "created_at":row["created_at"].isoformat(),
        "download_path":f'/v1/private-tasks/{row["id"]}/artifact',
        "executed_on_backend":True,
        "customer_publish_authorized":False,
    }

@router.post("",status_code=201)
def create_task(
    payload:Execute,
    session:Session,
    idempotency_key:Annotated[str|None,Header(alias="Idempotency-Key")]=None,
):
    require_role(session,AUTH_ROLES)
    key=_require_idempotency(idempotency_key)
    org=session.principal.organization_id
    actor=session.principal.user_id
    fingerprint=_sha(_canonical(payload.model_dump(mode="json",exclude_none=True)))
    with session.conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                    (f"private-tasks:{org}:{actor}",))
        cur.execute(
            "SELECT * FROM private_execution_results "
            "WHERE organization_id=%s AND actor_user_id=%s AND request_key=%s",
            (org,actor,key),
        )
        row=cur.fetchone()
        if row:
            if row["input_sha256"]!=fingerprint:
                raise HTTPException(409,"Idempotency key used with different task input")
            return _public_record(row)
        cur.execute(
            "SELECT count(*) AS n FROM private_execution_results "
            "WHERE organization_id=%s AND actor_user_id=%s "
            "AND created_at>now()-interval '1 hour'",
            (org,actor),
        )
        if cur.fetchone()["n"]>=MAX_HOURLY:
            raise HTTPException(429,"Hourly private task limit reached")
        # Execution occurs now, not in a fake QUEUED state. All task kinds
        # are bounded and never call public URLs or mutate outside resources.
        artifact,mime,filename,metadata=execute_task(payload)
        output_digest=_sha(artifact)
        cur.execute(
            "INSERT INTO private_execution_results "
            "(organization_id,actor_user_id,request_key,task_type,input_sha256,"
            "artifact_sha256,artifact_mime,artifact_filename,artifact_bytes,"
            "artifact,result_metadata,status,expires_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'COMPLETED',now()+interval '7 days') "
            "RETURNING *",
            (org,actor,key,payload.task_type,fingerprint,output_digest,mime,
             filename,len(artifact),artifact,Jsonb(metadata)),
        )
        return _public_record(cur.fetchone())

def _get_row(session:TenantSession,job_id:UUID)->dict:
    with session.conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM private_execution_results "
            "WHERE organization_id=%s AND actor_user_id=%s AND id=%s "
            "AND expires_at>now()",
            (session.principal.organization_id,session.principal.user_id,job_id),
        )
        row=cur.fetchone()
    if not row:
        raise HTTPException(404,"Task result not found or expired")
    return row

@router.get("/{job_id}")
def get_task(job_id:UUID,session:Session):
    require_role(session,READ_ROLES)
    return _public_record(_get_row(session,job_id))

@router.get("/{job_id}/artifact")
def get_artifact(job_id:UUID,session:Session):
    require_role(session,READ_ROLES)
    row=_get_row(session,job_id)
    data=bytes(row["artifact"])
    if _sha(data)!=row["artifact_sha256"] or len(data)!=row["artifact_bytes"]:
        raise HTTPException(409,"Artifact integrity verification failed")
    return Response(
        content=data,media_type=row["artifact_mime"],
        headers={
            "Content-Disposition":f'attachment; filename="{row["artifact_filename"]}"',
            "Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff",
            "Content-Security-Policy":"sandbox; default-src 'none'",
            "X-Artifact-SHA256":row["artifact_sha256"],
        },
    )
