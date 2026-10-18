"""P2-054: MetaAutomate-owned offline multi-agent execution runtime.

Standard-library Python + SQLite. No cloud providers, model calls, tokens,
Docker, Redis, external subprocesses, third-party agents or paid services.

Four real deterministic specialists run a reproducible inventory-to-business-
report pipeline. The durable queue, leases, retry/dead-letter, virtual budget,
tenant-bound reads, evidence chain and independent numerical verifier work
without an LLM. Sensitive external actions are *never* executed here.

This is an offline private runtime, not yet connected to public accounts, an
OIDC service, or deployed PostgreSQL. Do not expose these methods over HTTP.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager, closing
from pathlib import Path
from typing import Any
from uuid import uuid4

ENGINE_VERSION="1.0.0"
AGENT_ORDER=("inventory","business","creative","verifier")
AGENT_COST={"inventory":2,"business":1,"creative":1,"verifier":2}
REQUIRED_CREDITS=sum(AGENT_COST.values())
MAX_ATTEMPTS=3
LEASE_SECONDS=30
MAX_ARTIFACT_BYTES=45000
ALLOWED_ACTIONS={"NONE","PUBLISH_CAMPAIGN","ORDER_STOCK"}
TENANT_RE=re.compile(r"^[a-z][a-z0-9_-]{3,49}$")
SKU_RE=re.compile(r"^[A-Za-z0-9_-]{2,32}$")
CURRENCY_RE=re.compile(r"^[A-Z]{3}$")
IDEMP_RE=re.compile(r"^[A-Za-z0-9_.:-]{12,100}$")

def canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")

def digest(value:bytes)->str:
    return hashlib.sha256(value).hexdigest()

def validate(tenant:str,key:str,payload:dict,budget:int)->dict:
    if not isinstance(tenant,str) or not TENANT_RE.fullmatch(tenant):
        raise ValueError("Invalid tenant identity")
    if not isinstance(key,str) or not IDEMP_RE.fullmatch(key):
        raise ValueError("Invalid idempotency key")
    if type(budget) is not int or not REQUIRED_CREDITS<=budget<=100:
        raise ValueError("Not enough bounded compute credits")
    if type(payload) is not dict or set(payload)!={
        "project_name","currency","items","audience","requested_external_action"
    }:
        raise ValueError("Unexpected input fields")
    project=payload["project_name"]
    audience=payload["audience"]
    if (type(project) is not str or not 8<=len(project.strip())<=100 or
        type(audience) is not str or not 5<=len(audience.strip())<=120 or
        any(ord(ch)<32 for ch in project+audience)):
        raise ValueError("Invalid business project labels")
    if (type(payload["currency"]) is not str or
        not CURRENCY_RE.fullmatch(payload["currency"])):
        raise ValueError("Three-letter currency code required")
    if (type(payload["requested_external_action"]) is not str or
        payload["requested_external_action"] not in ALLOWED_ACTIONS):
        raise ValueError("Unapproved action class")
    items=payload["items"]
    if type(items) is not list or not 1<=len(items)<=80:
        raise ValueError("Expected 1 to 80 inventory rows")
    seen=set()
    for row in items:
        if type(row) is not dict or set(row)!={
            "sku","label","on_hand","reorder_at","unit_cost_minor"
        }:
            raise ValueError("Unexpected inventory fields")
        sku,label=row["sku"],row["label"]
        if (type(sku) is not str or not SKU_RE.fullmatch(sku) or
            sku in seen or type(label) is not str or
            not 2<=len(label.strip())<=100 or any(ord(c)<32 for c in label)):
            raise ValueError("Duplicate or invalid inventory identification")
        seen.add(sku)
        for name,maxval in [("on_hand",10_000_000),
                            ("reorder_at",10_000_000),
                            ("unit_cost_minor",1_000_000_000)]:
            if type(row[name]) is not int or not 0<=row[name]<=maxval:
                raise ValueError("Inventory counts and costs must be nonnegative integers")
    if len(canonical(payload))>25000:
        raise ValueError("Input exceeds memory budget")
    return payload

def inventory_agent(p:dict,context:dict)->dict:
    rows=[]
    for item in p["items"]:
        reorder=max(0,item["reorder_at"]-item["on_hand"])
        rows.append({
            "sku":item["sku"],"label":item["label"],"on_hand":item["on_hand"],
            "reorder_units":reorder,
            "purchase_estimate_minor":reorder*item["unit_cost_minor"],
            "stock_value_minor":item["on_hand"]*item["unit_cost_minor"],
        })
    return {"rows":rows,"items_count":len(rows),"currency":p["currency"]}

def business_agent(p:dict,context:dict)->dict:
    rows=context["inventory"]["rows"]
    shortages=sorted((r for r in rows if r["reorder_units"]>0),
                     key=lambda r:(-r["purchase_estimate_minor"],r["sku"]))
    return {
        "reorder_skus":len(shortages),
        "estimated_replenishment_minor":sum(r["purchase_estimate_minor"] for r in rows),
        "existing_stock_minor":sum(r["stock_value_minor"] for r in rows),
        "priority_skus":[r["sku"] for r in shortages[:3]],
        "currency":p["currency"],
        "financial_figures_independently_verified":False,
    }

def creative_agent(p:dict,context:dict)->dict:
    count=context["business"]["reorder_skus"]
    return {
        "audience":p["audience"],
        "draft_message":(
            f"Inventory update: {count} product lines are below their reorder "
            "targets. Review the stock report and confirm purchasing needs "
            "before placing any orders."
        ),
        "publication_authorized":False,
        "model_generated":False,
    }

def verifier_agent(p:dict,context:dict)->dict:
    inv=context["inventory"]
    biz=context["business"]
    # Separate recomputation directly from untrusted input, not from the
    # inventory-agent implementation. This catches corrupt upstream artifacts.
    expected_rows=[]
    for item in p["items"]:
        units=max(0,item["reorder_at"]-item["on_hand"])
        expected_rows.append({
            "sku":item["sku"],"label":item["label"],
            "on_hand":item["on_hand"],"reorder_units":units,
            "purchase_estimate_minor":units*item["unit_cost_minor"],
            "stock_value_minor":item["on_hand"]*item["unit_cost_minor"],
        })
    if (inv.get("rows")!=expected_rows or
        inv.get("items_count")!=len(p["items"]) or
        inv.get("currency")!=p["currency"]):
        raise ValueError("Independent inventory recomputation disagrees")
    expected_priorities=sorted(
        (row for row in expected_rows if row["reorder_units"]>0),
        key=lambda row:(-row["purchase_estimate_minor"],row["sku"]),
    )
    expected_business={
        "reorder_skus":len(expected_priorities),
        "estimated_replenishment_minor":sum(row["purchase_estimate_minor"]
                                           for row in expected_rows),
        "existing_stock_minor":sum(row["stock_value_minor"]
                                   for row in expected_rows),
        "priority_skus":[row["sku"] for row in expected_priorities[:3]],
        "currency":p["currency"],
        "financial_figures_independently_verified":False,
    }
    if biz!=expected_business:
        raise ValueError("Independent business recomputation disagrees")
    creative=context["creative"]
    if (type(creative) is not dict or
        creative.get("publication_authorized") is not False or
        creative.get("model_generated") is not False or
        creative.get("audience")!=p["audience"] or
        type(creative.get("draft_message")) is not str or
        not creative["draft_message"].startswith("Inventory update:")):
        raise ValueError("Creative draft is not a permitted local output")
    return {
        "verification":"PASS",
        "method":"INDEPENDENT_DETERMINISTIC_RECOMPUTATION",
        "input_digest":digest(canonical(p)),
        "inventory_digest":digest(canonical(inv)),
        "business_digest":digest(canonical(biz)),
        "neural_inference_performed":False,
        "customer_data_source_authenticated":False,
    }

AGENTS={
    "inventory":inventory_agent,"business":business_agent,
    "creative":creative_agent,"verifier":verifier_agent,
}

SCHEMA="""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs(
 id TEXT PRIMARY KEY,tenant TEXT NOT NULL,request_key TEXT NOT NULL,
 input_sha TEXT NOT NULL,input_json TEXT NOT NULL,state TEXT NOT NULL,
 actor TEXT NOT NULL,budget INTEGER NOT NULL,spent INTEGER NOT NULL DEFAULT 0,
 created REAL NOT NULL,updated REAL NOT NULL,
 UNIQUE(tenant,request_key)
);
CREATE TABLE IF NOT EXISTS steps(
 run_id TEXT NOT NULL,seq INTEGER NOT NULL,agent TEXT NOT NULL,
 state TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
 next_at REAL NOT NULL DEFAULT 0,lease_until REAL,
 claim_id TEXT,output_json TEXT,output_sha TEXT,error TEXT,
 PRIMARY KEY(run_id,seq),
 FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_step_queue ON steps(state,next_at,seq);
CREATE TABLE IF NOT EXISTS evidence(
 id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,
 kind TEXT NOT NULL,body TEXT NOT NULL,prev_sha TEXT NOT NULL,
 event_sha TEXT NOT NULL,created REAL NOT NULL,
 FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence(run_id,id);
CREATE TABLE IF NOT EXISTS approvals(
 run_id TEXT PRIMARY KEY,action TEXT NOT NULL,state TEXT NOT NULL,
 requested_by TEXT NOT NULL,reviewed_by TEXT,reason TEXT,
 updated REAL NOT NULL,
 FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE RESTRICT
);
"""

class Runtime:
    def __init__(self,path:str|Path,now=None):
        self.path=str(path)
        self.now=now if now is not None else time.time
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript(SCHEMA)

    def connect(self):
        db=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    @contextmanager
    def txn(self):
        db=self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def _event(self,db,run_id:str,kind:str,detail:dict):
        prev=db.execute(
            "SELECT event_sha FROM evidence WHERE run_id=? ORDER BY id DESC LIMIT 1",
            (run_id,)).fetchone()
        prior=prev["event_sha"] if prev else "0"*64
        body=canonical({"kind":kind,"detail":detail}).decode("utf-8")
        checksum=digest((prior+body).encode("utf-8"))
        db.execute(
            "INSERT INTO evidence(run_id,kind,body,prev_sha,event_sha,created) "
            "VALUES(?,?,?,?,?,?)",
            (run_id,kind,body,prior,checksum,self.now())
        )

    def submit(self,tenant:str,request_key:str,payload:dict,*,
               actor:str,budget:int=REQUIRED_CREDITS)->str:
        validate(tenant,request_key,payload,budget)
        if type(actor) is not str or not 4<=len(actor)<=80:
            raise ValueError("Actor identity required")
        key=digest(canonical(payload))
        with self.txn() as db:
            prior=db.execute("SELECT id,input_sha FROM runs WHERE tenant=? AND request_key=?",
                             (tenant,request_key)).fetchone()
            if prior:
                if prior["input_sha"]!=key:
                    raise ValueError("Idempotency key reused for different input")
                return prior["id"]
            run_id=str(uuid4())
            stamp=self.now()
            db.execute("INSERT INTO runs(id,tenant,request_key,input_sha,input_json,"
                       "state,actor,budget,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (run_id,tenant,request_key,key,canonical(payload).decode(),
                        "QUEUED",actor,budget,stamp,stamp))
            for index,agent in enumerate(AGENT_ORDER):
                db.execute("INSERT INTO steps(run_id,seq,agent,state) VALUES(?,?,?,?)",
                           (run_id,index,agent,"READY"))
            self._event(db,run_id,"SUBMITTED",{
                "input_sha256":key,"agents":AGENT_ORDER,"budget_units":budget,
                "external_action":payload["requested_external_action"],
            })
            return run_id

    def _expire_leases(self,db):
        rows=db.execute("SELECT run_id,seq,attempts FROM steps "
                        "WHERE state='CLAIMED' AND lease_until<?",(self.now(),)).fetchall()
        for r in rows:
            failed=r["attempts"]>=MAX_ATTEMPTS
            db.execute("UPDATE steps SET state=?,claim_id=NULL,lease_until=NULL,"
                       "next_at=? WHERE run_id=? AND seq=?",
                       ("DEAD" if failed else "READY",self.now(),
                        r["run_id"],r["seq"]))
            if failed:
                db.execute("UPDATE runs SET state='FAILED',updated=? WHERE id=?",
                           (self.now(),r["run_id"]))
            self._event(db,r["run_id"],"LEASE_EXPIRED",{
                "step":r["seq"],"dead_letter":failed
            })

    def claim(self,tenant:str|None=None)->dict|None:
        if tenant is not None and not TENANT_RE.fullmatch(tenant):
            raise ValueError("Invalid worker tenant")
        with self.txn() as db:
            self._expire_leases(db)
            sql=("SELECT s.run_id,s.seq,s.agent,s.attempts,r.budget,r.spent,r.tenant "
                 "FROM steps s JOIN runs r ON r.id=s.run_id "
                 "WHERE s.state='READY' AND s.next_at<=? "
                 "AND r.state IN ('QUEUED','RUNNING') "
                 "AND NOT EXISTS (SELECT 1 FROM steps older "
                 "WHERE older.run_id=s.run_id AND older.seq<s.seq "
                 "AND older.state!='DONE') ")
            args=[self.now()]
            if tenant:
                sql+="AND r.tenant=? "
                args.append(tenant)
            sql+="ORDER BY r.created,s.seq LIMIT 1"
            row=db.execute(sql,args).fetchone()
            if not row:
                return None
            if row["spent"]+AGENT_COST[row["agent"]]>row["budget"]:
                db.execute("UPDATE runs SET state='FAILED',updated=? WHERE id=?",
                           (self.now(),row["run_id"]))
                db.execute("UPDATE steps SET state='DEAD',error='BUDGET_EXCEEDED' "
                           "WHERE run_id=? AND seq=?",(row["run_id"],row["seq"]))
                self._event(db,row["run_id"],"BUDGET_DENIED",{"step":row["seq"]})
                return None
            claim_id=str(uuid4())
            db.execute("UPDATE steps SET state='CLAIMED',claim_id=?,"
                       "attempts=attempts+1,lease_until=? "
                       "WHERE run_id=? AND seq=?",
                       (claim_id,self.now()+LEASE_SECONDS,row["run_id"],row["seq"]))
            db.execute("UPDATE runs SET state='RUNNING',updated=? WHERE id=?",
                       (self.now(),row["run_id"]))
            self._event(db,row["run_id"],"CLAIMED",{
                "step":row["seq"],"agent":row["agent"],
                "attempt":row["attempts"]+1,
            })
            return {
                "run_id":row["run_id"],"tenant":row["tenant"],
                "seq":row["seq"],"agent":row["agent"],"claim_id":claim_id,
                "attempt":row["attempts"]+1,
            }

    def _run_agent(self,job):
        with self.connect() as db:
            run=db.execute("SELECT input_json FROM runs WHERE id=? AND tenant=?",
                           (job["run_id"],job["tenant"])).fetchone()
            if not run:
                raise ValueError("Run does not exist in tenant")
            previous=db.execute(
                "SELECT agent,output_json,output_sha FROM steps "
                "WHERE run_id=? AND seq<? ORDER BY seq",
                (job["run_id"],job["seq"])).fetchall()
        context={}
        for row in previous:
            if not row["output_json"] or digest(row["output_json"].encode())!=row["output_sha"]:
                raise ValueError("Prior artifact integrity check failed")
            context[row["agent"]]=json.loads(row["output_json"])
        output=AGENTS[job["agent"]](json.loads(run["input_json"]),context)
        raw=canonical(output)
        if len(raw)>MAX_ARTIFACT_BYTES:
            raise ValueError("Output memory limit exceeded")
        return raw.decode(),digest(raw)

    def _settle(self,job,output:str|None,output_sha:str|None,error:str|None):
        with self.txn() as db:
            row=db.execute("SELECT state,claim_id,attempts FROM steps "
                           "WHERE run_id=? AND seq=?",
                           (job["run_id"],job["seq"])).fetchone()
            if not row or row["state"]!="CLAIMED" or row["claim_id"]!=job["claim_id"]:
                raise ValueError("Stale worker lease; result rejected")
            if error:
                terminal=row["attempts"]>=MAX_ATTEMPTS
                next_at=self.now()+min(60,2**row["attempts"])
                db.execute("UPDATE steps SET state=?,claim_id=NULL,lease_until=NULL,"
                           "next_at=?,error=? WHERE run_id=? AND seq=?",
                           ("DEAD" if terminal else "READY",next_at,
                            type(error).__name__,job["run_id"],job["seq"]))
                if terminal:
                    db.execute("UPDATE runs SET state='FAILED',updated=? WHERE id=?",
                               (self.now(),job["run_id"]))
                self._event(db,job["run_id"],"FAILED_ATTEMPT",{
                    "step":job["seq"],"retry":not terminal,
                    "error_type":type(error).__name__,
                })
                return
            db.execute("UPDATE steps SET state='DONE',claim_id=NULL,lease_until=NULL,"
                       "output_json=?,output_sha=?,error=NULL WHERE run_id=? AND seq=?",
                       (output,output_sha,job["run_id"],job["seq"]))
            db.execute("UPDATE runs SET spent=spent+?,updated=? WHERE id=?",
                       (AGENT_COST[job["agent"]],self.now(),job["run_id"]))
            self._event(db,job["run_id"],"AGENT_COMPLETED",{
                "step":job["seq"],"agent":job["agent"],"artifact_sha256":output_sha,
                "virtual_compute_units":AGENT_COST[job["agent"]],
            })
            if job["seq"]==len(AGENT_ORDER)-1:
                run=db.execute("SELECT actor,input_json FROM runs WHERE id=?",
                               (job["run_id"],)).fetchone()
                requested=json.loads(run["input_json"])["requested_external_action"]
                if requested=="NONE":
                    state="COMPLETED"
                else:
                    state="AWAITING_APPROVAL"
                    db.execute("INSERT INTO approvals(run_id,action,state,requested_by,"
                               "updated) VALUES(?,?,'PENDING',?,?)",
                               (job["run_id"],requested,run["actor"],self.now()))
                    self._event(db,job["run_id"],"APPROVAL_REQUIRED",{
                        "action":requested,"external_action_executed":False,
                    })
                db.execute("UPDATE runs SET state=?,updated=? WHERE id=?",
                           (state,self.now(),job["run_id"]))
                self._event(db,job["run_id"],"WORKFLOW_FINISHED",{
                    "state":state,"verification":"PASS",
                    "external_action_executed":False,
                })

    def work_once(self,tenant:str|None=None)->bool:
        job=self.claim(tenant)
        if not job:
            return False
        try:
            result,sha=self._run_agent(job)
        except Exception as exc:
            self._settle(job,None,None,exc)
        else:
            self._settle(job,result,sha,None)
        return True

    def work_until_idle(self,tenant:str|None=None,limit:int=40)->int:
        if type(limit) is not int or not 1<=limit<=100:
            raise ValueError("Invalid work loop limit")
        count=0
        while count<limit and self.work_once(tenant):
            count+=1
        return count

    def approval(self,tenant:str,run_id:str,reviewer:str,reason:str,approve:bool):
        if not TENANT_RE.fullmatch(tenant) or type(approve) is not bool:
            raise ValueError("Invalid approval request")
        if type(reviewer) is not str or not 4<=len(reviewer)<=80:
            raise ValueError("Reviewer identity required")
        if type(reason) is not str or not 10<=len(reason.strip())<=400:
            raise ValueError("Substantive approval reason required")
        with self.txn() as db:
            row=db.execute("SELECT r.actor,r.state,a.state AS approval_state "
                           "FROM runs r JOIN approvals a ON a.run_id=r.id "
                           "WHERE r.id=? AND r.tenant=?",(run_id,tenant)).fetchone()
            if not row or row["state"]!="AWAITING_APPROVAL" or row["approval_state"]!="PENDING":
                raise ValueError("No awaiting approval exists for this tenant")
            if row["actor"]==reviewer:
                raise ValueError("Requester cannot self-approve external action")
            state="APPROVED_NOT_EXECUTED" if approve else "REJECTED"
            db.execute("UPDATE approvals SET state=?,reviewed_by=?,reason=?,updated=? "
                       "WHERE run_id=?",(state,reviewer,reason,self.now(),run_id))
            db.execute("UPDATE runs SET state=?,updated=? WHERE id=?",
                       (state,self.now(),run_id))
            self._event(db,run_id,"REVIEW_DECISION",{
                "decision":state,"reviewer":reviewer,
                "external_action_executed":False,
            })
            return state

    def report(self,tenant:str,run_id:str)->dict:
        if not TENANT_RE.fullmatch(tenant):
            raise ValueError("Invalid tenant")
        with self.connect() as db:
            run=db.execute("SELECT * FROM runs WHERE id=? AND tenant=?",
                           (run_id,tenant)).fetchone()
            if not run:
                raise KeyError("Run not found in tenant")
            steps=db.execute("SELECT seq,agent,state,attempts,output_sha,output_json,error "
                             "FROM steps WHERE run_id=? ORDER BY seq",(run_id,)).fetchall()
            outputs={}
            stages=[]
            for item in steps:
                if item["output_json"]:
                    if digest(item["output_json"].encode())!=item["output_sha"]:
                        raise ValueError("Artifact integrity failed")
                    outputs[item["agent"]]=json.loads(item["output_json"])
                stages.append({k:item[k] for k in
                               ("seq","agent","state","attempts","output_sha","error")})
            approval=db.execute("SELECT action,state,reviewed_by FROM approvals "
                                "WHERE run_id=?",(run_id,)).fetchone()
        return {
            "run_id":run_id,"tenant":tenant,"state":run["state"],
            "budget_units":run["budget"],"spent_units":run["spent"],
            "stage_status":stages,"outputs":outputs,
            "external_approval":dict(approval) if approval else None,
            "external_action_executed":False,
            "third_party_model_calls":0,"paid_api_cost":0,
            "neural_reasoning_claimed":False,
        }

    def verify_evidence(self,tenant:str,run_id:str)->dict:
        if not TENANT_RE.fullmatch(tenant):
            raise ValueError("Invalid tenant")
        with self.connect() as db:
            owned=db.execute("SELECT 1 FROM runs WHERE tenant=? AND id=?",
                             (tenant,run_id)).fetchone()
            if not owned:
                raise KeyError("Run not found in tenant")
            rows=db.execute("SELECT kind,body,prev_sha,event_sha FROM evidence "
                            "WHERE run_id=? ORDER BY id",(run_id,)).fetchall()
        previous="0"*64
        for row in rows:
            expected=digest((previous+row["body"]).encode())
            if row["prev_sha"]!=previous or expected!=row["event_sha"]:
                return {"verified":False,"events":len(rows),
                        "reason":"EVENT_CHAIN_MISMATCH"}
            previous=expected
        return {"verified":bool(rows),"events":len(rows),
                "final_sha256":previous,"reason":"VERIFIED" if rows else "NO_EVENTS"}

def agent_manifest()->dict:
    """Local A2A-inspired discovery, not a remotely compliant A2A server."""
    return {
        "name":"MetaAutomate Owned Multi-Agent Runtime",
        "version":ENGINE_VERSION,
        "transport":"IN_PROCESS_ONLY",
        "a2a_compatible_concepts":["agent_skills","task_states","artifacts"],
        "a2a_protocol_implemented":False,
        "mcp_network_server_implemented":False,
        "agents":[{"id":name,"virtual_compute_units":AGENT_COST[name],
                   "side_effecting":False} for name in AGENT_ORDER],
    }

def mcp_tool_descriptors()->list[dict]:
    """MCP-style whitelisted tool schemas; no untrusted calls or network RPC."""
    return [{
        "name":"metaautomate.inventory_reorder",
        "description":"Compute inventory reorder recommendations, without purchases.",
        "inputSchema":{
            "type":"object",
            "properties":{"items":{"type":"array","maxItems":80}},
            "required":["items"],"additionalProperties":False,
        },
        "annotations":{"readOnlyHint":True,"destructiveHint":False},
    },{
        "name":"metaautomate.business_review",
        "description":"Calculate inventory costs from supplied records, no payments.",
        "inputSchema":{"type":"object","properties":{
            "inventory":{"type":"object"}},
            "required":["inventory"],"additionalProperties":False},
        "annotations":{"readOnlyHint":True,"destructiveHint":False},
    }]

def demo_payload()->dict:
    return {
        "project_name":"Retail stock improvement demonstration",
        "currency":"NGN","audience":"small independent retail teams",
        "requested_external_action":"NONE",
        "items":[
            {"sku":"MAIZE25","label":"Maize bags","on_hand":7,
             "reorder_at":20,"unit_cost_minor":125000},
            {"sku":"SOYA25","label":"Soybeans bags","on_hand":25,
             "reorder_at":10,"unit_cost_minor":78000},
        ],
    }
