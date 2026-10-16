"""P2-03v: signed-test-actor governed orchestration with durable offline approval.

This component accepts only P2-03u synthetic project templates and test-issued
Ed25519 claims. It models a two-person approval boundary with actual on-disk
SQLite commits, revocations and a hash-linked audit trace. IT IS NOT a real
identity provider, OIDC/MFA implementation, live agent runtime, immutable audit
store or production authorization service. All tools are fictional and no
network, customer data, payments, publishing or external action is possible.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .disposable_crm_authorization import verify_actor_token, VerifiedActor
from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_intelligence_project_architect import (
    SCENARIOS, build_intelligence_plan, simulate_intelligence_graph,
)

DEMO_PROJECT = re.compile(r"SIM-PLAN-[A-Z0-9-]{2,40}\Z")
TOKEN = re.compile(r"SIM-TOKEN-[A-Z0-9-]{2,40}\Z")
TOOLS = frozenset({"ANALYZE_SAMPLE", "GENERATE_REVIEW_PLAN", "SUMMARIZE_EVIDENCE"})
ROLES = {"owner": "tenant_admin", "reviewer": "reviewer"}
STATES = frozenset({"DRAFT", "OWNER_APPROVED", "SECURITY_APPROVED", "SIMULATED", "REVOKED"})
KNOWN_WORKSPACES = frozenset({"academy_demo", "bespoke_demo"})
MAX_AUDIT_ROWS = 250


def require(ok: bool, message: str):
    if not ok:
        raise SyntheticGrowthError(message)


def demo_database_path(path: str | Path) -> Path:
    require(isinstance(path, (str, Path)), "Disposable database path required")
    source = Path(path).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    require(source.is_relative_to(temp_root) and
            source.name.endswith(".p2-03v-demo.sqlite3") and
            len(source.name) < 100,
            "Only temporary, explicitly suffixed synthetic rehearsal databases")
    return source


def json_wire(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class GovernedOrchestration:
    """Transactional two-person review using independently signed test actors.

    Every operation verifies the actor again, checks session revocation inside
    the same serialized transaction, and scopes all records by actor.workspace.
    A simulation advances *only* the three synthetic internal graph nodes.
    """

    def __init__(self, path: str | Path, trusted_public_key: Ed25519PublicKey,
                 *, clock: int | None = None):
        require(isinstance(trusted_public_key, Ed25519PublicKey),
                "Pinned test public key required")
        require(clock is None or (type(clock) is int and clock >= 0),
                "Invalid test clock")
        self.path = demo_database_path(path)
        self.key = trusted_public_key
        self.clock_override = clock
        self.db = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS plans (
            workspace TEXT NOT NULL, ref TEXT NOT NULL,
            scenario TEXT NOT NULL, spec_hash TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN (
                'DRAFT','OWNER_APPROVED','SECURITY_APPROVED','SIMULATED','REVOKED'
            )),
            owner_ref TEXT NOT NULL, owner_token TEXT,
            reviewer_ref TEXT, reviewer_token TEXT,
            PRIMARY KEY (workspace,ref)
        );
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            workspace TEXT NOT NULL, token_ref TEXT NOT NULL,
            revoked_by TEXT NOT NULL, reason TEXT NOT NULL,
            PRIMARY KEY (workspace,token_ref)
        );
        CREATE TABLE IF NOT EXISTS audit (
            workspace TEXT NOT NULL, sequence INTEGER NOT NULL,
            previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL,
            event_json TEXT NOT NULL, PRIMARY KEY (workspace,sequence)
        );
        CREATE TABLE IF NOT EXISTS synthetic_tool_reviews (
            workspace TEXT NOT NULL, plan_ref TEXT NOT NULL, tool_id TEXT NOT NULL,
            summary TEXT NOT NULL, PRIMARY KEY (workspace,plan_ref,tool_id),
            FOREIGN KEY (workspace,plan_ref) REFERENCES plans(workspace,ref)
        );
        """)
        self.db.execute("PRAGMA trusted_schema=OFF")

    def close(self):
        self.db.close()

    def _now(self) -> int:
        return int(time.time()) if self.clock_override is None else self.clock_override

    @contextmanager
    def _transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _actor(self, token: str, roles: tuple[str, ...]) -> VerifiedActor:
        actor = verify_actor_token(token, self.key, now=self._now())
        require(actor.role in roles, "Actor lacks required task role")
        revoked = self.db.execute(
            "SELECT 1 FROM revoked_tokens WHERE workspace=? AND token_ref=?",
            (actor.workspace, actor.token_ref),
        ).fetchone()
        require(revoked is None, "Test session revoked")
        return actor

    def _get(self, workspace: str, plan_ref: str) -> sqlite3.Row:
        require(type(plan_ref) is str and DEMO_PROJECT.fullmatch(plan_ref) is not None,
                "Invalid fictional plan reference")
        row = self.db.execute(
            "SELECT * FROM plans WHERE workspace=? AND ref=?",
            (workspace, plan_ref),
        ).fetchone()
        require(row is not None, "No accessible plan in authenticated tenant")
        return row

    def _not_revoked(self, ws: str, ref: str | None):
        require(ref is not None, "Missing approval session")
        require(self.db.execute(
            "SELECT 1 FROM revoked_tokens WHERE workspace=? AND token_ref=?",
            (ws,ref),
        ).fetchone() is None, "Approval session was revoked")

    def _audit(self, workspace: str, event: dict):
        require(len(json_wire(event)) <= 800, "Oversized audit event")
        latest = self.db.execute(
            "SELECT sequence,entry_hash FROM audit WHERE workspace=?"
            " ORDER BY sequence DESC LIMIT 1", (workspace,),
        ).fetchone()
        sequence = latest["sequence"]+1 if latest else 1
        prev = latest["entry_hash"] if latest else "0"*64
        doc = json_wire({
            "sequence": sequence, "workspace": workspace, "event": event,
        })
        digest = sha256((prev + "|" + doc).encode("ascii")).hexdigest()
        self.db.execute(
            "INSERT INTO audit(workspace,sequence,previous_hash,entry_hash,event_json)"
            " VALUES (?,?,?,?,?)", (workspace,sequence,prev,digest,doc),
        )

    def propose(self, token: str, plan_ref: str, scenario_id: str) -> dict:
        require(type(scenario_id) is str and scenario_id in SCENARIOS,
                "Only synthetic intelligence templates allowed")
        require(type(plan_ref) is str and DEMO_PROJECT.fullmatch(plan_ref) is not None,
                "Only fictional plan references supported")
        plan = build_intelligence_plan(scenario_id)
        digest = sha256(json_wire(plan["project"]).encode("ascii")).hexdigest()
        with self._transaction():
            actor = self._actor(token, ("tenant_admin",))
            require(actor.workspace in KNOWN_WORKSPACES, "Unknown tenant")
            require(self.db.execute(
                "SELECT COUNT(*) FROM plans WHERE workspace=?",
                (actor.workspace,),
            ).fetchone()[0] < 25, "Bounded offline plans only")
            try:
                self.db.execute(
                    "INSERT INTO plans(workspace,ref,scenario,spec_hash,state,owner_ref)"
                    " VALUES (?,?,?,?,?,?)",
                    (actor.workspace,plan_ref,scenario_id,digest,"DRAFT",actor.actor_ref),
                )
            except sqlite3.IntegrityError as exc:
                raise SyntheticGrowthError("Duplicate plan; no replay overwrite") from exc
            self._audit(actor.workspace,{"action":"PLAN_CREATED",
                        "ref":plan_ref,"actor":actor.actor_ref,"spec":digest})
        return self.read(token,plan_ref)

    def approve_owner(self, token: str, plan_ref: str) -> dict:
        with self._transaction():
            actor=self._actor(token,("tenant_admin",))
            plan=self._get(actor.workspace,plan_ref)
            require(plan["state"]=="DRAFT" and plan["owner_ref"]==actor.actor_ref,
                    "Only original project owner can approve a draft")
            self.db.execute(
                "UPDATE plans SET state='OWNER_APPROVED',owner_token=?"
                " WHERE workspace=? AND ref=?",
                (actor.token_ref,actor.workspace,plan_ref),
            )
            self._audit(actor.workspace,{"action":"OWNER_APPROVED",
                        "ref":plan_ref,"actor":actor.actor_ref,
                        "token_ref":actor.token_ref})
        return self.read(token,plan_ref)

    def approve_security(self, token: str, plan_ref: str) -> dict:
        with self._transaction():
            actor=self._actor(token,("reviewer",))
            plan=self._get(actor.workspace,plan_ref)
            require(plan["state"]=="OWNER_APPROVED",
                    "Security review requires owner approval")
            require(actor.actor_ref != plan["owner_ref"],
                    "Independent human reviewer required")
            self._not_revoked(actor.workspace,plan["owner_token"])
            self.db.execute(
                "UPDATE plans SET state='SECURITY_APPROVED',reviewer_ref=?,"
                " reviewer_token=? WHERE workspace=? AND ref=?",
                (actor.actor_ref,actor.token_ref,actor.workspace,plan_ref),
            )
            self._audit(actor.workspace,{"action":"SECURITY_APPROVED",
                        "ref":plan_ref,"actor":actor.actor_ref,
                        "token_ref":actor.token_ref})
        return self.read(token,plan_ref)

    def run_synthetic(self, token: str, plan_ref: str) -> dict:
        with self._transaction():
            actor=self._actor(token,("tenant_admin",))
            plan=self._get(actor.workspace,plan_ref)
            require(plan["state"]=="SECURITY_APPROVED" and
                    actor.actor_ref==plan["owner_ref"] and
                    actor.token_ref==plan["owner_token"],
                    "Only original signed owner may simulate approved plan")
            self._not_revoked(actor.workspace,plan["reviewer_token"])
            design=build_intelligence_plan(plan["scenario"])
            current=sha256(json_wire(design["project"]).encode("ascii")).hexdigest()
            require(current == plan["spec_hash"], "Approved architecture changed")
            trace=simulate_intelligence_graph(design)
            require(trace["external_actions_attempted"]==0 and
                    trace["customer_records_created"]==0 and
                    trace["provider_requests"]==0 and
                    trace["real_ai_inference_calls"]==0,
                    "Unsafe workflow simulation")
            self.db.execute(
                "UPDATE plans SET state='SIMULATED' WHERE workspace=? AND ref=?",
                (actor.workspace,plan_ref),
            )
            self._audit(actor.workspace,{"action":"INTERNAL_SIMULATED",
                        "ref":plan_ref,"actor":actor.actor_ref})
        return trace

    def review_tool(self, token: str, plan_ref: str, tool_id: str) -> dict:
        """Restricted virtual tool review, NEVER invokes a real tool."""
        require(type(tool_id) is str and len(tool_id)<=80 and
                re.fullmatch(r"[A-Z][A-Z0-9_]+",tool_id) is not None,
                "Invalid proposed tool identifier")
        with self._transaction():
            actor=self._actor(token,("reviewer",))
            plan=self._get(actor.workspace,plan_ref)
            self._not_revoked(actor.workspace,plan["owner_token"])
            require(plan["reviewer_ref"]==actor.actor_ref
                    and plan["reviewer_token"]==actor.token_ref
                    and plan["state"] in ("SECURITY_APPROVED","SIMULATED"),
                    "Tool decisions require original approved reviewer")
            allowed=tool_id in TOOLS
            # Even allowlisted tools are only names in a test ledger; no callable
            # network/publishing/tool execution interface is exposed.
            if allowed:
                self.db.execute(
                    "INSERT OR IGNORE INTO synthetic_tool_reviews"
                    "(workspace,plan_ref,tool_id,summary) VALUES (?,?,?,?)",
                    (actor.workspace,plan_ref,tool_id,"VIRTUAL_REVIEW_ONLY"),
                )
            self._audit(actor.workspace,{"action":"TOOL_REVIEW",
                        "ref":plan_ref,"actor":actor.actor_ref,
                        "tool":tool_id,"decision":"VIRTUAL_ONLY" if allowed else "DENIED"})
        return {"tool":tool_id,"decision":"VIRTUAL_ONLY" if allowed else "DENIED",
                "external_execution":False,"model_calls":0,
                "real_customer_data":False}

    def revoke(self, token: str, target_token_ref: str, *, reason: str="SECURITY_HOLD") -> dict:
        require(type(target_token_ref) is str and TOKEN.fullmatch(target_token_ref),
                "Unknown test token ID")
        require(reason in ("SECURITY_HOLD","OWNER_WITHDRAWAL","KEY_ROTATION"),
                "Unsupported revocation reason")
        with self._transaction():
            actor=self._actor(token,("tenant_admin",))
            require(target_token_ref != actor.token_ref,
                    "Use an independent active administrator to revoke this session")
            try:
                self.db.execute(
                    "INSERT INTO revoked_tokens(workspace,token_ref,revoked_by,reason)"
                    " VALUES (?,?,?,?)",
                    (actor.workspace,target_token_ref,actor.actor_ref,reason),
                )
            except sqlite3.IntegrityError as exc:
                raise SyntheticGrowthError("Already revoked; replay denied") from exc
            affected=self.db.execute(
                "UPDATE plans SET state='REVOKED' WHERE workspace=?"
                " AND (owner_token=? OR reviewer_token=?) AND state != 'REVOKED'",
                (actor.workspace,target_token_ref,target_token_ref),
            ).rowcount
            self._audit(actor.workspace,{"action":"TOKEN_REVOKED",
                        "token_ref":target_token_ref,"actor":actor.actor_ref,
                        "plans_invalidated":affected,"reason":reason})
        return {"token_ref":target_token_ref,"revoked":True,
                "plans_invalidated":affected,"provider_calls":0}

    def read(self, token: str, plan_ref: str) -> dict:
        actor=self._actor(token,("auditor","reviewer","tenant_admin"))
        row=self._get(actor.workspace,plan_ref)
        return {
            "workspace":actor.workspace, "ref":row["ref"],
            "scenario":row["scenario"],"state":row["state"],
            "owner_ref":row["owner_ref"],"reviewer_ref":row["reviewer_ref"],
            "external_execution_enabled":False,"model_connected":False,
            "customer_data_stored":False,"live_identity_provider":False,
        }

    def audit_report(self, token: str, *, trusted_head: str | None=None) -> dict:
        actor=self._actor(token,("auditor","tenant_admin"))
        if trusted_head is not None:
            require(type(trusted_head) is str and
                    re.fullmatch(r"[0-9a-f]{64}",trusted_head) is not None,
                    "Invalid external checkpoint")
        rows=self.db.execute(
            "SELECT sequence,previous_hash,entry_hash,event_json FROM audit"
            " WHERE workspace=? ORDER BY sequence", (actor.workspace,),
        ).fetchall()
        require(len(rows)<=MAX_AUDIT_ROWS,"Audit snapshot requires controlled pagination")
        prev="0"*64
        for i,row in enumerate(rows,start=1):
            doc=row["event_json"]
            require(row["sequence"]==i and row["previous_hash"]==prev and
                    sha256((prev+"|"+doc).encode("ascii")).hexdigest()==row["entry_hash"],
                    "Persistent audit chain integrity error")
            claims=json.loads(doc)
            require(type(claims) is dict and claims.get("workspace")==actor.workspace
                    and claims.get("sequence")==i,
                    "Audit tenant or sequence mismatch")
            prev=row["entry_hash"]
        if trusted_head is not None:
            require(trusted_head==prev, "Trusted audit checkpoint mismatch")
        return {"workspace":actor.workspace,"events":len(rows),"head_sha256":prev,
                "chain_consistent":True,"external_immutable_anchor_verified":False,
                "real_staff_identity_verified":False,"production_ready":False}

    def backup_to(self, token: str, target: str | Path) -> dict:
        actor=self._actor(token,("tenant_admin",))
        dest=demo_database_path(target)
        require(dest!=self.path and not dest.exists(),"Backup destination must be unused")
        self.audit_report(token)
        # SQLite's online backup API creates a consistent snapshot, even under WAL.
        with sqlite3.connect(str(dest)) as out:
            self.db.backup(out)
        return {"workspace":actor.workspace,"copied_to_disposable_snapshot":True,
                "customer_data":False,"production_recovery_verified":False}
