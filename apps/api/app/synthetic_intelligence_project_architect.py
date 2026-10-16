"""P2-03u: deterministic AI-project architect and gated workflow graph simulator.

Synthetic-only design capability. It is NOT a connected LLM, AI agent provider,
a real model assessment, staff-identity system, or a workflow execution service.
Only internal rules-based, side-effect-free steps can be simulated.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .synthetic_growth_autopilot import SyntheticGrowthError

SOURCE = (Path(__file__).resolve().parents[3] /
          "contracts/domains/v1/fixtures/synthetic_intelligence_projects.v1.json")
MAX_BYTES = 32_768
SCENARIOS = frozenset({
    "LEAD_QUALIFICATION", "INVENTORY_RESILIENCE",
    "CONTENT_OPERATIONS", "SECURITY_TRIAGE",
})
STEP_TYPES = {
    "INTAKE": "INPUT", "VALIDATE": "QUALITY", "ASSESS": "ANALYSIS",
    "REVIEW": "HUMAN_REVIEW", "EXTERNAL": "EXTERNAL_ACTION",
}
DATA_STATES = frozenset({"MISSING", "SAMPLE_ONLY", "APPROVED_SOURCE_CLAIM"})
SENSITIVITIES = frozenset({"NONE", "PERSONAL", "CONFIDENTIAL"})
REQUESTS = frozenset({"DESIGN_ONLY", "REQUEST_EXTERNAL_WORKFLOW"})
ID_RE = re.compile(r"[A-Z][A-Z0-9_]{2,48}\Z")
TEXT_FIELDS = frozenset({
    "id", "label", "sector", "objective", "success_metric",
    "metric_unit", "sample_baseline", "description", "steps",
})
STEP_FIELDS = frozenset({
    "id", "type", "depends_on", "description", "requires_review",
    "external_effect",
})


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise SyntheticGrowthError(detail)


def _object(value: Any, fields: set[str] | frozenset[str], title: str) -> dict:
    _require(type(value) is dict and set(value) == set(fields),
             "Unexpected project " + title + " fields")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    found = {}
    for name, value in pairs:
        _require(name not in found, "Repeated project JSON key")
        found[name] = value
    return found


def _no_fraction(value: str):
    raise SyntheticGrowthError("Fractional or nonfinite values are forbidden")


def _text(value: Any, name: str, minlen: int=8, maxlen: int=180) -> str:
    _require(type(value) is str and minlen <= len(value) <= maxlen
             and value.isprintable() and all(c not in value for c in "<>{}\r\n"),
             "Invalid descriptive text: " + name)
    return value


def parse_project_library(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES
             and b"\x00" not in raw, "Invalid project input size/type")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                         parse_float=_no_fraction, parse_constant=_no_fraction)
    except SyntheticGrowthError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed project library") from exc
    _object(doc, {"schema_version", "classification", "scenarios"}, "root")
    _require(type(doc["schema_version"]) is int and doc["schema_version"] == 1
             and doc["classification"] == "SYNTHETIC_SOURCE_ONLY",
             "Only versioned fictional plans are accepted")
    scenarios = doc["scenarios"]
    _require(type(scenarios) is list and len(scenarios) == len(SCENARIOS),
             "Expected four distinct scenario architectures")
    found = set()
    for scenario in scenarios:
        _object(scenario, TEXT_FIELDS, "scenario")
        scenario_id = scenario["id"]
        _require(type(scenario_id) is str and scenario_id in SCENARIOS
                 and scenario_id not in found, "Unrecognized or duplicate project")
        found.add(scenario_id)
        for field in ("label", "sector", "objective", "success_metric", "description"):
            _text(scenario[field], field)
        _require(scenario["metric_unit"] == "COUNT"
                 and type(scenario["sample_baseline"]) is int
                 and 0 <= scenario["sample_baseline"] <= 10_000,
                 "Metrics must be bounded sample counts, not money or promises")
        steps = scenario["steps"]
        _require(type(steps) is list and len(steps) == len(STEP_TYPES),
                 "Five workflow nodes required")
        step_map = {}
        for step in steps:
            _object(step, STEP_FIELDS, "workflow node")
            ident = step["id"]
            _require(type(ident) is str and ident in STEP_TYPES and
                     ident not in step_map and step["type"] == STEP_TYPES[ident],
                     "Unknown or repeated workflow node")
            _text(step["description"], "step description")
            _require(type(step["requires_review"]) is bool
                     and type(step["external_effect"]) is bool,
                     "Review flags must be booleans")
            _require(step["requires_review"] == (ident in ("REVIEW", "EXTERNAL"))
                     and step["external_effect"] == (ident == "EXTERNAL"),
                     "Side-effect or human-review guard changed")
            parents = step["depends_on"]
            _require(type(parents) is list and len(parents) <= 3
                     and len(parents) == len(set(map(str, parents)))
                     and all(type(x) is str and x in STEP_TYPES and x != ident
                             for x in parents), "Invalid dependencies")
            step_map[ident] = step
        _require(set(step_map) == set(STEP_TYPES), "Incomplete graph")
        _require(step_map["INTAKE"]["depends_on"] == []
                 and step_map["VALIDATE"]["depends_on"] == ["INTAKE"]
                 and step_map["ASSESS"]["depends_on"] == ["VALIDATE"]
                 and step_map["REVIEW"]["depends_on"] == ["ASSESS"]
                 and step_map["EXTERNAL"]["depends_on"] == ["REVIEW"],
                 "Graph edges must be ordered and explicitly gated")
        _require([step["id"] for step in steps] == list(STEP_TYPES),
                 "Unapproved or out-of-order execution plan")
    _require(found == SCENARIOS, "Missing scenario architecture")
    return doc


def build_intelligence_plan(
    scenario_id: str, *, data_state: str="SAMPLE_ONLY",
    sensitivity: str="NONE", requested_action: str="DESIGN_ONLY",
    raw_library: bytes | None=None,
) -> dict:
    _require(type(scenario_id) is str and scenario_id in SCENARIOS,
             "Unknown project architecture")
    _require(type(data_state) is str and data_state in DATA_STATES,
             "Unsupported data-readiness state")
    _require(type(sensitivity) is str and sensitivity in SENSITIVITIES,
             "Unsupported data-sensitivity category")
    _require(type(requested_action) is str and requested_action in REQUESTS,
             "Unsupported execution request")
    raw = SOURCE.read_bytes() if raw_library is None else raw_library
    library = parse_project_library(raw)
    scene = next(x for x in library["scenarios"] if x["id"] == scenario_id)
    blockers = []
    if data_state == "MISSING":
        blockers.append("Define a lawful, representative data source and baseline")
    if data_state == "APPROVED_SOURCE_CLAIM":
        blockers.append("Verify source ownership, minimization, provenance and authorization")
    if sensitivity != "NONE":
        blockers.append("Security and privacy review required before handling sensitive information")
    blockers.extend((
        "Authenticate the real workflow owner and independent security reviewer",
        "Validate source quality, measured baseline and approval evidence",
        "Complete private-staging identity, audit, recovery and release verification",
    ))
    if requested_action == "REQUEST_EXTERNAL_WORKFLOW":
        blockers.append("External platform permissions, consent and publication approvals not verified")
    graph = []
    for step in scene["steps"]:
        state = ("BLOCKED_EXTERNAL" if step["external_effect"]
                 else "HUMAN_REVIEW_REQUIRED" if step["requires_review"]
                 else "SAFE_SYNTHETIC_PREVIEW")
        graph.append({
            "id": step["id"], "type": step["type"], "description": step["description"],
            "depends_on": list(step["depends_on"]), "status": state,
            "actual_execution_authorized": False, "provider_calls": 0,
        })
    return {
        "milestone": "P2_03U_INTELLIGENCE_PROJECT_ARCHITECT",
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "project": {
            "id": scene["id"], "name": scene["label"],
            "sector": scene["sector"], "objective": scene["objective"],
            "metric": scene["success_metric"], "metric_unit": scene["metric_unit"],
            "illustrative_baseline": scene["sample_baseline"],
            "baseline_verified": False,
        },
        "choices": {"data_state": data_state, "sensitivity": sensitivity,
                    "requested_action": requested_action},
        "workflow": graph,
        "architecture": {
            "input": "Synthetic scoped intake, contract and source provenance",
            "intelligence": "Deterministic assessment only; no connected AI model",
            "orchestration": "Dependency-based local simulation with no side effects",
            "governance": "Authentic actor roles, independent approval, consent and audit required",
            "measurement": "Define baseline and compare outcomes; no causal/financial claim",
        },
        "acceptance": [
            "Source approved by owner, with minimization and quality evidence",
            "Workflow tasks have named authenticated owner and security approver",
            "Audit/recovery and tenant isolation independently tested in approved staging",
            "Success measure has an actual baseline and comparison methodology",
            "External effects have provider-specific permissions and distinct approval",
        ],
        "blockers": blockers,
        "evidence": {
            "fixture_sha256": sha256(raw).hexdigest(),
            "real_client_approval_verified": False,
            "live_customer_data": False,
            "real_model_or_agent_connected": False,
            "provider_requests": 0,
            "autonomous_actions": 0,
            "real_financial_value_verified": False,
            "production_ready": False,
        },
    }


def simulate_intelligence_graph(plan: dict) -> dict:
    """Run only fictional internal preprocessing; never human or external nodes."""
    _require(type(plan) is dict
             and plan.get("milestone") == "P2_03U_INTELLIGENCE_PROJECT_ARCHITECT"
             and plan.get("classification") == "SYNTHETIC_SOURCE_ONLY"
             and type(plan.get("workflow")) is list and len(plan["workflow"]) == 5,
             "Invalid simulated execution contract")
    expected = list(STEP_TYPES)
    _require([s.get("id") for s in plan["workflow"] if type(s) is dict] == expected,
             "Unexpected execution graph")
    trace = []
    for step in plan["workflow"]:
        ident = step["id"]
        _require(step.get("actual_execution_authorized") is False
                 and step.get("provider_calls") == 0
                 and step.get("type") == STEP_TYPES[ident],
                 "Unsafe execution claims")
        status = ("SIMULATED_COMPLETED" if ident in ("INTAKE", "VALIDATE", "ASSESS")
                  else "HALTED_HUMAN_REVIEW" if ident == "REVIEW"
                  else "NOT_RUN_EXTERNAL_BLOCKED")
        trace.append({"node": ident, "state": status})
    return {
        "classification": "FICTIONAL_TRACE_ONLY",
        "nodes": trace,
        "completed_internal_simulations": 3,
        "human_decisions_recorded": 0,
        "external_actions_attempted": 0,
        "provider_requests": 0,
        "customer_records_created": 0,
        "real_ai_inference_calls": 0,
        "live_workflow_started": False,
    }
