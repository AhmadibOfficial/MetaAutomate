"""P2-03u: regression and adversarial tests for offline AI workflow architect."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_intelligence_project_architect import (
    SOURCE, SCENARIOS, build_intelligence_plan, parse_project_library,
    simulate_intelligence_graph, DATA_STATES, SENSITIVITIES, REQUESTS,
)


def fixture():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def raw(data):
    return json.dumps(data,sort_keys=True,separators=(",",":")).encode()


@pytest.mark.parametrize("scenario",sorted(SCENARIOS))
def test_all_four_scenarios_and_gates(scenario):
    plan=build_intelligence_plan(scenario)
    assert plan==build_intelligence_plan(scenario)
    assert plan["project"]["id"]==scenario
    assert plan["project"]["illustrative_baseline"]==12
    assert plan["project"]["baseline_verified"] is False
    assert len(plan["workflow"])==5
    assert [n["status"] for n in plan["workflow"]]==[
        "SAFE_SYNTHETIC_PREVIEW"]*3+["HUMAN_REVIEW_REQUIRED","BLOCKED_EXTERNAL"]
    assert [n["depends_on"] for n in plan["workflow"]]==[
        [],["INTAKE"],["VALIDATE"],["ASSESS"],["REVIEW"]]
    assert all(not n["actual_execution_authorized"] and n["provider_calls"]==0
               for n in plan["workflow"])
    assert not plan["evidence"]["real_model_or_agent_connected"]
    assert not plan["evidence"]["production_ready"]
    assert not plan["evidence"]["real_financial_value_verified"]
    assert len(plan["acceptance"])==5


@pytest.mark.parametrize("data_state",sorted(DATA_STATES))
@pytest.mark.parametrize("sensitivity",sorted(SENSITIVITIES))
@pytest.mark.parametrize("action",sorted(REQUESTS))
def test_all_18_contexts_never_trigger_an_action(data_state,sensitivity,action):
    plan=build_intelligence_plan("LEAD_QUALIFICATION",data_state=data_state,
                                 sensitivity=sensitivity,requested_action=action)
    trace=simulate_intelligence_graph(plan)
    assert [r["state"] for r in trace["nodes"]]==[
        "SIMULATED_COMPLETED"]*3+[
        "HALTED_HUMAN_REVIEW","NOT_RUN_EXTERNAL_BLOCKED"]
    assert trace["completed_internal_simulations"]==3
    assert trace["external_actions_attempted"]==0
    assert trace["real_ai_inference_calls"]==0
    assert trace["customer_records_created"]==0
    assert trace["human_decisions_recorded"]==0
    assert plan["evidence"]["provider_requests"]==0
    assert plan["evidence"]["autonomous_actions"]==0
    assert len(plan["blockers"])>=3


@pytest.mark.parametrize("field,value",[
    ("scenario_id","UNREGISTERED"),("scenario_id",None),("scenario_id",False),
    ("data_state","CONNECTED"),("data_state",123),
    ("sensitivity","PRIVATE_IDENTITY"),("sensitivity",True),
    ("requested_action","AUTO_PUBLISH"),("requested_action",None),
])
def test_unknown_caller_inputs_are_refused(field,value):
    kwargs={"scenario_id":"CONTENT_OPERATIONS","data_state":"SAMPLE_ONLY",
            "sensitivity":"NONE","requested_action":"DESIGN_ONLY"}
    kwargs[field]=value
    with pytest.raises(SyntheticGrowthError):
        build_intelligence_plan(**kwargs)


@pytest.mark.parametrize("bad", [
    b"",b"{}",b"null",b"not JSON",
    b'{"schema_version":1,"schema_version":1}',
    b'{"value":2.5}',b'{"value":NaN}',b"x"*33000,
    b"\x00"*200,
])
def test_json_parser_denies_malformed_and_duplicate_inputs(bad):
    with pytest.raises(SyntheticGrowthError):
        parse_project_library(bad)


@pytest.mark.parametrize("mutation",[
    lambda d: d["scenarios"][0].update({"email":"someone@example.invalid"}),
    lambda d: d["scenarios"][0].update({"sample_baseline": True}),
    lambda d: d["scenarios"][0].update({"sample_baseline": -2}),
    lambda d: d["scenarios"][0].update({"sample_baseline": 20000}),
    lambda d: d["scenarios"][0].update({"objective": "<script>do bad things</script>"}),
    lambda d: d["scenarios"][0].update({"metric_unit":"USD"}),
    lambda d: d["scenarios"][0].update({"id":"UNAUTHORIZED"}),
    lambda d: d["scenarios"][1].update({"id":"LEAD_QUALIFICATION"}),
    lambda d: d["scenarios"].append(deepcopy(d["scenarios"][0])),
    lambda d: d["scenarios"][0]["steps"][4].update({"external_effect":False}),
    lambda d: d["scenarios"][0]["steps"][4].update({"requires_review":False}),
    lambda d: d["scenarios"][0]["steps"][3].update({"requires_review":False}),
    lambda d: d["scenarios"][0]["steps"][3].update({"depends_on":["EXTERNAL"]}),
    lambda d: d["scenarios"][0]["steps"][4].update({"depends_on":[]}),
    lambda d: d["scenarios"][0]["steps"][0].update({"depends_on":["EXTERNAL"]}),
    lambda d: d["scenarios"][0]["steps"][4].update({"type":"ANALYSIS"}),
    lambda d: d["scenarios"][0]["steps"][0].update({"customer_email":"x@x.invalid"}),
    lambda d: d["scenarios"][0]["steps"].reverse(),
    lambda d: d["scenarios"][0]["steps"][2].update({"description":"NO\nBAD"}),
])
def test_modified_graph_and_personal_data_are_denied(mutation):
    doc=fixture()
    mutation(doc)
    with pytest.raises(SyntheticGrowthError):
        parse_project_library(raw(doc))


def test_library_digests_are_explainable_and_reproducible():
    plan=build_intelligence_plan("SECURITY_TRIAGE")
    assert len(plan["evidence"]["fixture_sha256"])==64
    assert plan["evidence"]["fixture_sha256"]==__import__("hashlib").sha256(
        SOURCE.read_bytes()).hexdigest()


def test_execution_runner_rejects_forged_authorization():
    plan=build_intelligence_plan("CONTENT_OPERATIONS")
    plan["workflow"][-1]["actual_execution_authorized"]=True
    with pytest.raises(SyntheticGrowthError):
        simulate_intelligence_graph(plan)
    plan=build_intelligence_plan("CONTENT_OPERATIONS")
    plan["workflow"][-1]["provider_calls"]=1
    with pytest.raises(SyntheticGrowthError):
        simulate_intelligence_graph(plan)
    plan=build_intelligence_plan("CONTENT_OPERATIONS")
    plan["workflow"][-1]["type"]="ANALYSIS"
    with pytest.raises(SyntheticGrowthError):
        simulate_intelligence_graph(plan)


def test_sensitive_and_external_work_needs_distinct_gates():
    p=build_intelligence_plan("SECURITY_TRIAGE",
        data_state="APPROVED_SOURCE_CLAIM",sensitivity="CONFIDENTIAL",
        requested_action="REQUEST_EXTERNAL_WORKFLOW")
    b=" ".join(p["blockers"])
    assert "Verify source ownership" in b
    assert "privacy review" in b
    assert "External platform permissions" in b
    assert p["evidence"]["live_customer_data"] is False
