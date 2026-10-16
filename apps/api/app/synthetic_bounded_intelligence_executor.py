"""P2-03x — bounded, durable *synthetic* Intelligence executor.

This deliberately runs only three pure, deterministic Python functions over
numeric fictional inputs. It cannot call models, the network, a shell, databases
other than the separate disposable review ledger, or outside connectors. Its
CI JWTs are test identities; neither authenticated staff nor production agents
are present.

The execution boundary requires TWO independently signed offline identity
layers, the original owner and independent reviewer decisions, a complete
fictional workflow preview, purpose/module-specific signed-review receipt,
unrevoked original sessions, an exact hash-bound parameter contract, and
a short synthetic lease. Grant and result are written atomically with the
tenant's hash-linked audit trail; duplicate command IDs never execute twice.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_intelligence_project_architect import (
    build_intelligence_plan,
)
from .synthetic_governed_orchestration import (
    GovernedOrchestration, approved_graph_fingerprint,
)
from .synthetic_governed_intelligence_portfolio import (
    GovernedIntelligenceGateway, MODULE_ENGINE_MAP, PURPOSES, VIRTUAL_TOOLS,
    build_governed_portfolio,
)

COMMAND_RE = re.compile(r"SIM-CMD-[A-Z0-9-]{4,40}\Z")
MAX_LEASE_SECONDS = 120
MAX_COMMANDS_PER_TENANT = 32
PARAM_FIELDS = {
    "ANALYZE_SAMPLE": frozenset({"sample_count", "flagged_count"}),
    "GENERATE_REVIEW_PLAN": frozenset({"finding_count", "review_capacity"}),
    "SUMMARIZE_EVIDENCE": frozenset({"baseline_count", "current_count"}),
}
LIMITS = {
    "sample_count": (0, 1000), "flagged_count": (0, 1000),
    "finding_count": (0, 100), "review_capacity": (1, 100),
    "baseline_count": (0, 1000), "current_count": (0, 1000),
}


def require(ok: bool, error: str) -> None:
    if not ok:
        raise SyntheticGrowthError(error)


def wire(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(obj: dict) -> str:
    return sha256(wire(obj).encode("ascii")).hexdigest()


def validated_inputs(tool_id: str, values: dict) -> dict:
    require(type(tool_id) is str and tool_id in PARAM_FIELDS,
            "Unrecognized offline tool")
    require(type(values) is dict and set(values) == PARAM_FIELDS[tool_id],
            "Only exact bounded numeric synthetic fields allowed")
    for key, value in values.items():
        lower, upper = LIMITS[key]
        require(type(value) is int and lower <= value <= upper,
                "Out of range or noninteger synthetic input: " + key)
    if tool_id == "ANALYZE_SAMPLE":
        require(values["flagged_count"] <= values["sample_count"],
                "Flagged count exceeds synthetic sample")
    return dict(values)


def simulate_tool(tool_id: str, values: dict) -> dict:
    """No dynamic imports, network, subprocesses, providers or runtime plugins."""
    v = validated_inputs(tool_id, values)
    if tool_id == "ANALYZE_SAMPLE":
        output = {
            "review_population": v["sample_count"],
            "synthetic_flagged_count": v["flagged_count"],
            "flagged_share_basis_points": (
                v["flagged_count"] * 10000 // v["sample_count"]
                if v["sample_count"] else None
            ),
            "action": "REFER_TO_HUMAN_REVIEW",
        }
    elif tool_id == "GENERATE_REVIEW_PLAN":
        n = v["finding_count"]
        capacity = v["review_capacity"]
        output = {
            "fictional_findings": n,
            "review_batches": (n + capacity - 1) // capacity,
            "review_capacity_per_batch": capacity,
            "action": "HUMAN_APPROVAL_REQUIRED",
        }
    else:
        output = {
            "fictional_baseline": v["baseline_count"],
            "fictional_current": v["current_count"],
            "illustrative_change": v["current_count"] - v["baseline_count"],
            "causal_financial_impact_verified": False,
            "action": "REVIEW_DIFFERENCE_WITH_REAL_EVIDENCE",
        }
    return {
        "classification": "SYNTHETIC_DETERMINISTIC_ONLY",
        "tool_id": tool_id,
        "result": output,
        "actual_customer_records": 0,
        "provider_calls": 0,
        "model_inference_calls": 0,
        "payments": 0,
        "messages_sent": 0,
        "external_effects": 0,
        "production_result_verified": False,
    }


class BoundedIntelligenceExecutor:
    """Disposable transactional grant + execution record, never live dispatch."""

    def __init__(self, gateway: GovernedIntelligenceGateway):
        require(isinstance(gateway, GovernedIntelligenceGateway),
                "Existing dual-signature governance boundary required")
        self.gateway = gateway
        self.store = gateway.store
        # Only the explicitly restricted P2-03v disposable DB may be mutated.
        self.store.db.executescript("""
        CREATE TABLE IF NOT EXISTS bounded_virtual_actions (
            workspace TEXT NOT NULL,
            plan_ref TEXT NOT NULL,
            command_id TEXT NOT NULL,
            module_id TEXT NOT NULL,
            tool_id TEXT NOT NULL,
            purpose TEXT NOT NULL,
            request_sha256 TEXT NOT NULL,
            request_json TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            workflow_sha256 TEXT NOT NULL,
            owner_ref TEXT NOT NULL,
            owner_token_ref TEXT NOT NULL,
            reviewer_ref TEXT NOT NULL,
            reviewer_token_ref TEXT NOT NULL,
            reviewer_idp_jti TEXT NOT NULL,
            reviewer_idp_kid TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('REVIEWED','SIMULATED')),
            lease_expires_at INTEGER NOT NULL,
            result_json TEXT,
            result_sha256 TEXT,
            PRIMARY KEY(workspace,command_id),
            FOREIGN KEY(workspace,plan_ref)
                REFERENCES plans(workspace,ref)
        );
        """)

    @staticmethod
    def _id(command_id: str) -> None:
        require(type(command_id) is str
                and COMMAND_RE.fullmatch(command_id) is not None,
                "Invalid fictional command reference")

    def _plan(self, actor, plan_ref: str):
        plan=self.store._get(actor.workspace,plan_ref)
        require(plan["state"]=="SIMULATED",
                "Workflow owner and independent security approvals and internal simulation required")
        require(plan["owner_ref"]!=plan["reviewer_ref"],
                "Self-review forbidden")
        self.store._not_revoked(actor.workspace,plan["owner_token"])
        self.store._not_revoked(actor.workspace,plan["reviewer_token"])
        actual=approved_graph_fingerprint(build_intelligence_plan(plan["scenario"]))
        require(actual==plan["spec_hash"],"Original approved workflow changed")
        return plan

    def _scope(self, module_id: str, tool_id: str, purpose: str) -> None:
        require(type(module_id) is str and module_id in MODULE_ENGINE_MAP,
                "Unrecognized intelligence domain")
        require(type(tool_id) is str and tool_id in VIRTUAL_TOOLS
                and module_id in VIRTUAL_TOOLS[tool_id],
                "Tool not permitted for intelligence module")
        require(type(purpose) is str and purpose in PURPOSES,
                "Tool purpose not independently allowlisted")

    def grant(self, reviewer_jwt: str, reviewer_app: str, plan_ref: str,
              command_id: str, module_id: str, tool_id: str, purpose: str,
              values: dict) -> dict:
        """Independent reviewer grants *only* this fictional hash-bound intent."""
        self._id(command_id)
        self._scope(module_id,tool_id,purpose)
        params=validated_inputs(tool_id,values)
        ws=self.gateway._both(reviewer_jwt,reviewer_app,("reviewer",))
        idp_identity=self.gateway.trust.verify(reviewer_jwt,now=self.store._now())
        portfolio=build_governed_portfolio(ws)
        source=next(m for m in portfolio["modules"] if m["id"]==module_id)
        request={
            "workspace":ws,"plan_ref":plan_ref,"command_id":command_id,
            "module":module_id,"tool":tool_id,"purpose":purpose,
            "parameters":params,
        }
        h=digest(request)
        with self.store._transaction():
            actor=self.store._actor(reviewer_app,("reviewer",))
            plan=self._plan(actor,plan_ref)
            require(actor.workspace==ws
                    and actor.actor_ref==plan["reviewer_ref"]
                    and actor.token_ref==plan["reviewer_token"],
                    "Original independently approved reviewer required")
            count=self.store.db.execute(
                "SELECT COUNT(*) FROM bounded_virtual_actions WHERE workspace=?",
                (ws,),
            ).fetchone()[0]
            require(count < MAX_COMMANDS_PER_TENANT,
                    "Bounded tenant-specific preview quota reached")
            require(self.store.db.execute(
                "SELECT 1 FROM bounded_virtual_actions WHERE workspace=? AND command_id=?",
                (ws,command_id),
            ).fetchone() is None,
                    "No replay or rewriting previously reviewed intent")
            lease=self.store._now()+MAX_LEASE_SECONDS
            self.store.db.execute("""
                INSERT INTO bounded_virtual_actions (
                    workspace,plan_ref,command_id,module_id,tool_id,purpose,
                    request_sha256,request_json,source_sha256,workflow_sha256,
                    owner_ref,owner_token_ref,reviewer_ref,reviewer_token_ref,
                    reviewer_idp_jti,reviewer_idp_kid,state,lease_expires_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(ws,plan_ref,command_id,module_id,tool_id,purpose,
                 h,wire(request),source["source_record_sha256"],plan["spec_hash"],
                 plan["owner_ref"],plan["owner_token"],
                 actor.actor_ref,actor.token_ref,idp_identity.token_ref,
                 idp_identity.key_id,"REVIEWED",lease))
            self.store._audit(ws,{"action":"VIRTUAL_INTENT_APPROVED",
                "ref":plan_ref,"command":command_id,"request_sha256":h,
                "reviewer":actor.actor_ref})
        return {"command_id":command_id,"state":"REVIEWED",
                "intent_sha256":h,"lease_expires_at":lease,
                "approved_live_execution":False,"external_calls":0}

    def run(self, owner_jwt: str, owner_app: str, command_id: str) -> dict:
        """Original owner simulates bounded computation; atomic evidence append."""
        self._id(command_id)
        ws=self.gateway._both(owner_jwt,owner_app,("tenant_admin",))
        # Every read/decision in one SQLite IMMEDIATE transaction; revocation
        # and grants share this same database boundary.
        with self.store._transaction():
            actor=self.store._actor(owner_app,("tenant_admin",))
            row=self.store.db.execute(
                "SELECT * FROM bounded_virtual_actions WHERE workspace=? AND command_id=?",
                (ws,command_id),
            ).fetchone()
            require(row is not None,"No approved intent in authenticated workspace")
            plan=self._plan(actor,row["plan_ref"])
            require(actor.actor_ref==plan["owner_ref"]
                    and actor.token_ref==plan["owner_token"]
                    and row["owner_ref"]==actor.actor_ref
                    and row["owner_token_ref"]==actor.token_ref,
                    "Execution owner no longer matches grant")
            require(row["reviewer_ref"]==plan["reviewer_ref"]
                    and row["reviewer_token_ref"]==plan["reviewer_token"],
                    "Original security reviewer changed")
            # The two independently test-signed credential revocation views
            # are always freshly queried; a previously granted intention
            # cannot bypass a later IdP key/JTI revocation.
            require(row["reviewer_idp_jti"] not in self.gateway.trust.revoked_jtis
                    and row["reviewer_idp_kid"] not in self.gateway.trust.revoked_kids
                    and row["reviewer_idp_kid"] in self.gateway.trust.keys,
                    "Reviewer test identity or signing key revoked")
            require(row["lease_expires_at"]>self.store._now(),
                    "Synthetic tool lease expired")
            request=json.loads(row["request_json"])
            require(digest(request)==row["request_sha256"],
                    "Tampered approved input")
            require(request["workspace"]==ws
                    and request["command_id"]==command_id
                    and request["plan_ref"]==row["plan_ref"]
                    and request["module"]==row["module_id"]
                    and request["tool"]==row["tool_id"]
                    and request["purpose"]==row["purpose"],
                    "Unbound execution input")
            self._scope(row["module_id"],row["tool_id"],row["purpose"])
            portfolio=build_governed_portfolio(ws)
            source=next(m for m in portfolio["modules"]
                        if m["id"]==row["module_id"])
            require(row["source_sha256"]==source["source_record_sha256"]
                    and row["workflow_sha256"]==plan["spec_hash"],
                    "Approved input source or workflow changed")
            result=simulate_tool(row["tool_id"],request["parameters"])
            evidence={
                "command_id":command_id,"workspace":ws,
                "module":row["module_id"],"purpose":row["purpose"],
                "request_sha256":row["request_sha256"],
                "source_sha256":row["source_sha256"],
                "workflow_sha256":row["workflow_sha256"],
                "synthetic_execution":result,
            }
            result_string=wire(evidence)
            result_hash=sha256(result_string.encode("ascii")).hexdigest()
            if row["state"]=="SIMULATED":
                require(row["result_sha256"]==result_hash
                        and row["result_json"]==result_string,
                        "Conflicting deterministic retry or tampered evidence")
                return {**evidence,"evidence_sha256":result_hash,
                        "idempotent_replay":True,"executed_in_live_environment":False}
            require(row["state"]=="REVIEWED","Unrecognized command state")
            self.store.db.execute(
                "UPDATE bounded_virtual_actions SET state='SIMULATED',"
                " result_json=?,result_sha256=? WHERE workspace=? AND command_id=?",
                (result_string,result_hash,ws,command_id),
            )
            self.store._audit(ws,{"action":"VIRTUAL_INTENT_SIMULATED",
                "command":command_id,"result_sha256":result_hash,
                "owner":actor.actor_ref})
        return {**evidence,"evidence_sha256":result_hash,
                "idempotent_replay":False,"executed_in_live_environment":False}

    def verify(self, auditor_jwt: str, auditor_app: str,
               command_id: str, *, trusted_audit_head: str | None=None) -> dict:
        """Recompute simulation and verify durable ledger; no live-value claim."""
        self._id(command_id)
        ws=self.gateway._both(auditor_jwt,auditor_app,("auditor","tenant_admin"))
        audit=self.store.audit_report(auditor_app,trusted_head=trusted_audit_head)
        row=self.store.db.execute(
            "SELECT * FROM bounded_virtual_actions WHERE workspace=? AND command_id=?",
            (ws,command_id),
        ).fetchone()
        require(row is not None and row["state"]=="SIMULATED",
                "No completed fictional execution evidence")
        request=json.loads(row["request_json"])
        evidence=json.loads(row["result_json"])
        require(digest(request)==row["request_sha256"]
                and digest(evidence)==row["result_sha256"],
                "Stored input or result evidence tampered")
        require(evidence["command_id"]==command_id
                and evidence["workspace"]==ws
                and evidence["request_sha256"]==row["request_sha256"]
                and evidence["source_sha256"]==row["source_sha256"]
                and evidence["workflow_sha256"]==row["workflow_sha256"]
                and evidence["synthetic_execution"]==simulate_tool(
                    row["tool_id"],request["parameters"]),
                "Deterministic simulation evidence mismatch")
        return {
            "command_id":command_id,"workspace":ws,"evidence_sha256":row["result_sha256"],
            "audit_head_sha256":audit["head_sha256"],
            "local_audit_chain_consistent":True,"synthetic_computation_reproduced":True,
            "independent_live_identity_verified":False,
            "real_customer_data_verified":False,
            "production_runtime_verified":False,
            "live_business_impact_verified":False,
            "external_audit_anchor_verified":False,
        }
