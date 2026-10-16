"""Reproducible synthetic product demonstration, never an execution gateway.

Reuses the Objective Workspace's pure planner, assessment and P2-03b parser.
Only repository-owned fixtures are read. No runtime user data, network, DB,
external connector, model, real identity or operational approval is involved.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

from app.assessment_engine import AssessmentInput, canonical_hash, produce_report
from app.objectives import PreviewRequest, build_preview
from app.synthetic_inventory_import import parse_synthetic_inventory_bytes

ROOT = Path(__file__).resolve().parents[3]
SCENARIO_PATH = ROOT / "contracts/demos/business-autopilot-v1.json"
INVENTORY_PATH = ROOT / "contracts/domains/v1/fixtures/synthetic_inventory_import.json"
ENGINE_VERSION = "business-autopilot-demo/1.0.0"
CLASSIFICATION = "SYNTHETIC_DEMO_ONLY"
SCENARIOS = ("standard", "partial_failure", "high_cost")
DEMO_NAMESPACE = UUID("00000000-0000-4000-8000-000000000001")
STAGES = ("LOADED", "ASSESSED", "PLANNED", "APPROVED", "SIMULATED", "VERIFIED")


class DemoConflict(ValueError):
    """An out-of-order or stale demo operation; no state was changed."""


def strict_json(raw: bytes) -> object:
    if type(raw) is not bytes or not 1 <= len(raw) <= 128 * 1024:
        raise ValueError("JSON document size is out of range")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def bad_constant(_):
        raise ValueError("Non-finite JSON number")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=bad_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid JSON document") from exc


def fixed_source() -> tuple[dict, bytes, dict]:
    raw = SCENARIO_PATH.read_bytes()
    scenario = strict_json(raw)
    if (type(scenario) is not dict or scenario.get("classification") != CLASSIFICATION
            or type(scenario.get("schema_version")) is not int or scenario["schema_version"] != 1
            or set(scenario.get("scenarios", {})) != set(SCENARIOS)):
        raise ValueError("Invalid committed synthetic scenario")
    inventory = INVENTORY_PATH.read_bytes()  # Never open a path from JSON or HTTP input.
    source = {"scenario_sha256": sha256(raw).hexdigest(),
              "inventory_sha256": sha256(inventory).hexdigest()}
    return scenario, inventory, source


class DemoRun:
    def __init__(self, scenario_id: str = "standard"):
        if type(scenario_id) is not str or scenario_id not in SCENARIOS:
            raise ValueError("Choose a known synthetic scenario")
        self.scenario_id = scenario_id
        self.fixture, raw, self.sources = fixed_source()
        self.scenario = self.fixture["scenarios"][scenario_id]
        self.inventory = parse_synthetic_inventory_bytes(raw, "json", DEMO_NAMESPACE)
        # A fixture namespace is not a customer identity or a tenancy claim.
        self.inventory.pop("tenant_demo_partition")
        self.assumptions = deepcopy(self.fixture["assumptions"])
        self.assumptions["delivery_cost_minor"] = self.scenario["delivery_cost_minor"]
        self.input_sha256 = canonical_hash({"engine": ENGINE_VERSION,
            "scenario_id": scenario_id, "sources": self.sources,
            "assumptions": self.assumptions})
        self.stage = "LOADED"
        self.assessment = self.plan = self.approval = self.simulation = None
        self.verification = None
        self.events = []
        self._event("FIXTURE_LOADED", {"input_sha256": self.input_sha256})

    def _event(self, event: str, detail: dict) -> None:
        entry = {"sequence": len(self.events) + 1, "event": event,
                 "detail": deepcopy(detail),
                 "previous_sha256": self.events[-1]["sha256"] if self.events else "0" * 64}
        self.events.append({**entry, "sha256": canonical_hash(entry)})

    def _require(self, stage: str) -> None:
        if self.stage != stage:
            raise DemoConflict(f"This action requires {stage}; current stage is {self.stage}.")

    def assess(self) -> None:
        self._require("LOADED")
        payload = AssessmentInput(business_label=self.fixture["business_label"],
            objective=self.fixture["objective"], answers=[
                {"question_id": key, "score": value}
                for key, value in self.fixture["answers"].items()])
        self.assessment = {"maturity": produce_report(payload),
            "inventory": self.inventory,
            "evidence_type": "INVENTED_RATINGS_AND_INVENTORY",
            "finding": f'{self.inventory["totals"]["below_threshold_count"]} synthetic SKUs below threshold'}
        self.stage = "ASSESSED"
        self._event("ASSESSMENT_CALCULATED", {"assessment_sha256": canonical_hash(self.assessment)})

    def make_plan(self) -> None:
        self._require("ASSESSED")
        payload = PreviewRequest(title="Prepare low-stock replenishment drafts",
            description=self.fixture["objective"],
            success_criteria=[{"metric": "low-stock SKUs with reviewable drafts",
                "target": "All, with blocked steps reported", "timeframe_days": 1}],
            constraints=["Synthetic data only", "Approval applies only to this simulation",
                         "No supplier messages, purchase orders, stock changes or payments"],
            requested_capability_ids=["BIZ-011"])
        workspace = build_preview(payload, [{"capability_id": "BIZ-011",
            "name": "Inventory preview", "domain": "BIZ", "release": "demo",
            "lifecycle_status": "DRAFT", "is_enabled": False}], [])
        drafts = [{"draft_id": "DRAFT-" + item["sku"], "sku": item["sku"],
                   "label": item["label"], "units": item["suggested_restock_units"],
                   "estimated_purchase_cost_minor": item["suggested_restock_units"] *
                       self.assumptions["unit_cost_minor"][item["sku"]],
                   "effect": "IN_MEMORY_DRAFT_ONLY"}
                  for item in self.inventory["items"] if item["below_threshold"]]
        body = {"input_sha256": self.input_sha256,
                "assessment_sha256": canonical_hash(self.assessment),
                "workspace_preview": workspace, "drafts": drafts,
                "simulation_case": self.scenario_id,
                "assumptions": self.assumptions,
                "approval_scope": "SYNTHETIC_DRAFTS_ONLY",
                "external_execution_allowed": False}
        self.plan = {**body, "plan_sha256": canonical_hash(body)}
        self.stage = "PLANNED"
        self._event("PLAN_PROPOSED", {"plan_sha256": self.plan["plan_sha256"]})

    def decide(self, *, plan_sha256: str, decision: str, simulation_only: bool) -> None:
        self._require("PLANNED")
        if (plan_sha256 != self.plan["plan_sha256"] or simulation_only is not True
                or decision not in {"APPROVE", "REJECT"}):
            raise DemoConflict("Review must reference this exact plan and simulation-only scope.")
        self.approval = {"plan_sha256": plan_sha256, "decision": decision,
                         "scope": "SYNTHETIC_DRAFTS_ONLY",
                         "identity_verified": False, "operational_authority_granted": False}
        self.stage = "APPROVED" if decision == "APPROVE" else "REJECTED"
        self._event("SIMULATION_REVIEW_" + decision, self.approval)

    def simulate(self) -> None:
        self._require("APPROVED")
        if (self.approval["decision"] != "APPROVE"
                or self.approval["plan_sha256"] != self.plan["plan_sha256"]
                or self.plan["plan_sha256"] != canonical_hash(
                    {k: v for k, v in self.plan.items() if k != "plan_sha256"})):
            raise DemoConflict("Plan or simulation approval changed; restart the demonstration.")
        steps = []
        for draft in self.plan["drafts"]:
            blocked = draft["sku"] in self.scenario["blocked_skus"]
            steps.append({**draft, "status": "BLOCKED" if blocked else "DRAFT_PREPARED",
                          "reason": "Synthetic supplier check needs human review" if blocked
                                    else "Synthetic request draft prepared in memory",
                          "external_action_performed": False})
        self.simulation = {"steps": steps,
            "status": "PARTIAL_BLOCKED" if any(s["status"] == "BLOCKED" for s in steps)
                      else "DRAFTS_PREPARED",
            "inventory_after": deepcopy(self.inventory["items"]),
            "stock_units_moved": 0, "purchase_orders_sent": 0,
            "external_requests": 0, "database_writes": 0}
        self.stage = "SIMULATED"
        self._event("SIMULATION_FINISHED", {"simulation_sha256": canonical_hash(self.simulation)})

    def outcomes(self) -> dict | None:
        if self.simulation is None:
            return None
        prepared = sum(step["status"] == "DRAFT_PREPARED" for step in self.simulation["steps"])
        blocked = len(self.simulation["steps"]) - prepared
        a = self.assumptions
        manual = prepared * a["manual_minutes_per_draft"]
        assisted = prepared * a["assisted_minutes_per_draft"]
        minutes = manual - assisted
        capacity = minutes * a["staff_hourly_cost_minor"] // 60
        cost = a["delivery_cost_minor"]
        return {"observed_in_simulation": {"drafts_prepared": prepared,
                    "steps_blocked": blocked, "low_stock_before": self.inventory["totals"]["below_threshold_count"],
                    "low_stock_after": self.inventory["totals"]["below_threshold_count"],
                    "stock_units_moved": 0},
                "illustrative_estimate": {"currency": self.fixture["currency"],
                    "manual_minutes": manual, "assisted_minutes": assisted,
                    "capacity_minutes": minutes, "capacity_value_minor": capacity,
                    "delivery_cost_minor": cost, "net_capacity_value_minor": capacity - cost,
                    "method": "prepared drafts × (manual − assisted minutes) × hourly cost ÷ 60 − delivery cost",
                    "blocked_steps_excluded": True,
                    "assumptions": deepcopy(a), "notice": self.fixture["assumption_notice"]},
                "real_business_outcomes": {"time_saved_minutes": None,
                    "cash_saved_minor": None, "revenue_recovered_minor": None,
                    "roi_verified": False, "evidence": "NOT_MEASURED"},
                "goal": "PREVIEW_GOAL_MET" if blocked == 0 else "PREVIEW_GOAL_INCOMPLETE"}

    def bundle(self) -> dict:
        if self.simulation is None:
            raise DemoConflict("An approved simulation is required before exporting evidence.")
        # No run token, identity, wall-clock claims or private workspace data.
        return deepcopy({"schema_version": 1, "classification": CLASSIFICATION,
            "engine_version": ENGINE_VERSION, "scenario_id": self.scenario_id,
            "sources": self.sources, "input_sha256": self.input_sha256,
            "assessment": self.assessment, "plan": self.plan, "approval": self.approval,
            "simulation": self.simulation, "outcomes": self.outcomes(), "audit": self.events,
            "boundaries": {"operational_release": "NO_GO", "capabilities": "DRAFT",
                "connectors": "UNBOUND", "live_execution": "DENY",
                "customer_data_used": False, "tenant_isolation_demonstrated": False,
                "paid_infrastructure_required": False}})

    def verify(self) -> None:
        self._require("SIMULATED")
        self.verification = verify_bundle(self.bundle())
        if not self.verification["verified"]:
            raise DemoConflict("Synthetic evidence did not match the committed reference.")
        # Verification is deliberately outside the reproducible evidence body.
        self.stage = "VERIFIED"

    def snapshot(self) -> dict:
        return deepcopy({"stage": self.stage, "scenario_id": self.scenario_id,
            "scenario": self.scenario, "business_label": self.fixture["business_label"],
            "objective": self.fixture["objective"], "input_sha256": self.input_sha256,
            "sources": self.sources, "assumptions": self.assumptions,
            "inventory": self.inventory, "assessment": self.assessment, "plan": self.plan,
            "approval": self.approval, "simulation": self.simulation,
            "outcomes": self.outcomes(), "audit": self.events, "verification": self.verification})


def replay(scenario_id: str = "standard") -> DemoRun:
    run = DemoRun(scenario_id)
    run.assess()
    run.make_plan()
    run.decide(plan_sha256=run.plan["plan_sha256"], decision="APPROVE", simulation_only=True)
    run.simulate()
    return run


def verify_bundle(candidate: object) -> dict:
    """Compare against regenerated source, not just attacker-recomputed hashes.

    This proves local reproducibility, not provenance of an approval or a real
    business result. Anyone with the source can regenerate a matching bundle.
    """
    matched = False
    if type(candidate) is dict and candidate.get("scenario_id") in SCENARIOS:
        try:
            matched = canonical_hash(candidate) == canonical_hash(replay(candidate["scenario_id"]).bundle())
        except (ValueError, TypeError, RecursionError):
            matched = False
    return {"verified": matched,
            "scope": "REPRODUCIBILITY_AGAINST_COMMITTED_SYNTHETIC_REFERENCE",
            "business_outcomes_verified": False, "approval_identity_verified": False,
            "notice": "Hash comparison is not a signature, external audit, security acceptance or proof of customer value."}
