"""P2-052: bounded outputs are real bytes, not plan previews or fake AI."""
from datetime import datetime,timezone
import io
import json
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.authn import Principal, TenantSession, get_tenant_session
from app import private_task_execution as task

ORG=uuid4()
ACTOR=uuid4()
OTHER=uuid4()

def inventory_payload():
    return {
        "task_type":"INVENTORY_REORDER_CSV",
        "inventory":{"currency":"NGN","items":[
            {"sku":"MAIZE_25","label":"Maize bags","on_hand":7,
             "reorder_at":20,"unit_cost_minor":125000},
            {"sku":"SOYA_25","label":"=1+1 cell unsafe","on_hand":30,
             "reorder_at":10,"unit_cost_minor":78000},
        ]}
    }

def graphic_payload():
    return {
        "task_type":"ORIGINAL_BRANDED_SVG",
        "graphic":{"brand":"MetaAutomate",
                   "headline":"Create real business value",
                   "message":"Build practical systems that solve real problems",
                   "theme":"white"}
    }

def test_inventory_execution_produces_genuine_csv_and_reorder_calculations():
    item=task.Execute.model_validate(inventory_payload())
    body,mime,name,meta=task.execute_task(item)
    assert mime.startswith("text/csv")
    assert name=="inventory-reorder.csv"
    assert meta["records_processed"]==2
    assert meta["reorder_alerts"]==1
    assert meta["inventory_value_minor"]==7*125000+30*78000
    import csv
    rows=list(csv.reader(io.StringIO(body.decode("utf-8"))))
    assert rows[1][4]=="13"
    assert rows[2][1].startswith("'=1+1")
    assert rows[2][4]=="0"
    assert b"PLAN_PREVIEW_ONLY" not in body

def test_original_svg_generates_sanitized_downloadable_media():
    item=graphic_payload()
    item["graphic"]["brand"]="ABC & <Dev>"
    data,mime,name,metadata=task.execute_task(task.Execute.model_validate(item))
    assert mime=="image/svg+xml"
    assert name.endswith(".svg")
    assert b"ABC &amp; &lt;Dev&gt;" in data
    assert metadata["width"]==1200 and metadata["height"]==675
    assert metadata["neural_image_inference"] is False
    assert b"<script" not in data and b"<image " not in data
    import xml.etree.ElementTree as ET
    tree=ET.fromstring(data)
    assert tree.tag.endswith("svg")

def test_invalid_payloads_and_conflicting_skus_rejected():
    import pytest
    from pydantic import ValidationError
    for invalid in [
        {"task_type":"LOCAL_MODEL_TEXT","text_job":{"prompt":"short"}},
        {"task_type":"INVENTORY_REORDER_CSV","inventory":{
            "currency":"NGN","items":[
                {"sku":"sku_1","label":"Stock One","on_hand":1,
                 "reorder_at":2,"unit_cost_minor":10},
                {"sku":"sku_1","label":"Stock Two","on_hand":1,
                 "reorder_at":2,"unit_cost_minor":10}
            ]}},
        {"task_type":"ORIGINAL_BRANDED_SVG","graphic":{
            "brand":"Brand X","headline":"Original and useful",
            "message":"An original useful business graphic","theme":"green"}},
        {"task_type":"ORIGINAL_BRANDED_SVG","graphic":{
            "brand":"Brand X","headline":"Original and useful",
            "message":"An original useful business graphic","theme":"white"},
            "inventory":{"currency":"NGN","items":[]}},
    ]:
        with pytest.raises(ValidationError):
            task.Execute.model_validate(invalid)

class Cursor:
    def __init__(self,db):
        self.db=db
        self.row=None
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def execute(self,sql,params):
        self.db.calls.append(sql)
        if "pg_advisory_xact_lock" in sql:
            self.row={"lock":True}
        elif "WHERE organization_id=%s AND actor_user_id=%s AND request_key=%s" in sql:
            self.row=self.db.by_key.get((params[0],params[1],params[2]))
        elif "SELECT count(*) AS n" in sql:
            self.row={"n":self.db.count}
        elif "INSERT INTO private_execution_results" in sql:
            (org,user,key,kind,insha,outsha,mime,filename,length,
             data,metadata)=params
            row={
                "id":uuid4(),"organization_id":org,"actor_user_id":user,
                "request_key":key,"task_type":kind,"input_sha256":insha,
                "artifact_sha256":outsha,"artifact_mime":mime,
                "artifact_filename":filename,"artifact_bytes":length,
                "artifact":data,"result_metadata":metadata.obj,
                "status":"COMPLETED","created_at":datetime.now(timezone.utc),
            }
            self.db.by_key[(org,user,key)]=row
            self.db.by_id[row["id"]]=row
            self.db.count+=1
            self.row=row
        elif "AND id=%s" in sql:
            org,user,job_id=params
            candidate=self.db.by_id.get(job_id)
            self.row=candidate if candidate and candidate["organization_id"]==org and candidate["actor_user_id"]==user else None
        else:
            raise AssertionError("Unexpected query: "+sql[:200])
    def fetchone(self):
        return self.row

class FakeDB:
    def __init__(self):
        self.by_key={}
        self.by_id={}
        self.count=0
        self.calls=[]
    def cursor(self):
        return Cursor(self)

def app_client(db,actor=ACTOR,role="OPERATOR"):
    a=FastAPI()
    a.include_router(task.router)
    principal=Principal(organization_id=ORG,user_id=actor,role=role)
    def session():
        yield TenantSession(conn=db,principal=principal)
    a.dependency_overrides[get_tenant_session]=session
    return TestClient(a)

def test_real_job_post_creates_artifact_replay_and_owner_only_download():
    db=FakeDB()
    client=app_client(db)
    h={"Idempotency-Key":"inventory-2026-001"}
    first=client.post("/v1/private-tasks",json=inventory_payload(),headers=h)
    assert first.status_code==201,first.text
    receipt=first.json()
    assert receipt["executed_on_backend"] is True
    assert receipt["task_type"]=="INVENTORY_REORDER_CSV"
    assert receipt["artifact_bytes"]>30
    assert receipt["customer_publish_authorized"] is False
    again=client.post("/v1/private-tasks",json=inventory_payload(),headers=h)
    assert again.status_code==201
    assert again.json()["id"]==receipt["id"]
    assert db.count==1
    download=client.get(receipt["download_path"])
    assert download.status_code==200
    assert download.headers["x-artifact-sha256"]==receipt["artifact_sha256"]
    assert download.headers["content-disposition"]=='attachment; filename="inventory-reorder.csv"'
    assert b"Maize bags" in download.content
    assert client.get("/v1/private-tasks/"+receipt["id"]).status_code==200
    other=app_client(db,actor=OTHER)
    assert other.get(receipt["download_path"]).status_code==404
    assert other.get("/v1/private-tasks/"+receipt["id"]).status_code==404

def test_task_replay_different_content_is_conflict():
    db=FakeDB()
    client=app_client(db)
    h={"Idempotency-Key":"graphic-2026-0001"}
    assert client.post("/v1/private-tasks",json=graphic_payload(),headers=h).status_code==201
    changed=graphic_payload()
    changed["graphic"]["brand"]="Another business brand"
    response=client.post("/v1/private-tasks",json=changed,headers=h)
    assert response.status_code==409
    assert db.count==1

def test_missing_idempotency_and_viewer_role_denied():
    db=FakeDB()
    assert app_client(db).post("/v1/private-tasks",json=graphic_payload()).status_code==422
    viewer=app_client(db,role="VIEWER")
    assert viewer.post("/v1/private-tasks",json=graphic_payload(),
                       headers={"Idempotency-Key":"graphic-2026-0002"}).status_code==403

def test_tampered_artifact_is_rejected():
    db=FakeDB()
    client=app_client(db)
    response=client.post("/v1/private-tasks",json=graphic_payload(),
                        headers={"Idempotency-Key":"graphic-2026-0003"})
    assert response.status_code==201
    row=db.by_id[next(iter(db.by_id))]
    row["artifact"]=b"tampered"
    assert client.get(response.json()["download_path"]).status_code==409

def test_private_rate_limit_applies_before_executing_more_tasks():
    db=FakeDB()
    db.count=task.MAX_HOURLY
    client=app_client(db)
    result=client.post("/v1/private-tasks",json=inventory_payload(),
                       headers={"Idempotency-Key":"inventory-2026-002"})
    assert result.status_code==429
    assert not db.by_id
