"""P2-03w: synthetic model evaluation + complete 12x5 governed portfolio."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_model_evaluation import (
    SOURCE, MODEL_IDS, TASK_IDS, parse_model_fixture,
    evaluate_model_candidates,
)
from app.synthetic_governed_intelligence_portfolio import (
    MODULE_ENGINE_MAP, MODULE_TASK_MAP, VIRTUAL_TOOLS,
    build_governed_portfolio,
)
from app.synthetic_integrated_intelligence import MODULES, ENGINES


def raw(doc):
    return json.dumps(doc,separators=(",",":"),sort_keys=True).encode()


def fixture():
    return json.loads(SOURCE.read_text())


def test_reference_model_ids_are_present_not_ranked():
    report=evaluate_model_candidates()
    assert set(report["candidate_model_ids"])==MODEL_IDS
    assert len(report["sample_case_results"])==len(MODEL_IDS)*len(TASK_IDS)
    assert report["ranked_live_model"] is None
    assert report["observed_provider_quality"] is None
    assert report["observed_cost_usd"] is None
    assert report["measured_latency_ms"] is None
    assert report["model_choice_recommendation"]=="EVALUATE_ON_REPRESENTATIVE_AUTHORIZED_TASKS"
    assert report["model_api_calls"]==0
    assert not report["external_model_adapter_enabled"]
    assert not report["training_or_personal_data_used"]


def test_mock_rubric_only_can_detect_missing_required_tags():
    report=evaluate_model_candidates()
    c=next(x for x in report["sample_case_results"]
           if x["model_id"]=="gpt-6-luna" and x["task_id"]=="SECURITY_REVIEW")
    assert c["sample_expected_tags_covered"]==1
    assert c["sample_expected_tags_total"]==2
    assert c["sample_rubric_complete"] is False
    assert c["production_model_passed"] is False


@pytest.mark.parametrize("bad",[
    b"",b"{}",b"null",b"not json",
    b'{"schema_version":1,"schema_version":1}',
    b'{"value":NaN}',b'{"value":1.02}',
    b"\x00"*14,b"x"*35000,
])
def test_model_fixture_parser_fail_closed(bad):
    with pytest.raises(SyntheticGrowthError):
        parse_model_fixture(bad)


@pytest.mark.parametrize("mutate",[
    lambda d:d.update({"provider_token":"sk-unwanted"}),
    lambda d:d.update({"real_provider_api_calls":True}),
    lambda d:d.update({"real_provider_api_calls":2}),
    lambda d:d.update({"real_model_benchmark":True}),
    lambda d:d["models"][0].update({"id":"not-a-real-model"}),
    lambda d:d["models"][1].update({"id":"gpt-6-astra"}),
    lambda d:d["models"][0].update({"api_key":"bad"}),
    lambda d:d["models"][0].update({"source_url":"https://attacker.test/"}),
    lambda d:d["tasks"][0].update({"personal_email":"x@invalid.test"}),
    lambda d:d["tasks"][0].update({"required_tags":["AUTO_PUBLISH"]}),
    lambda d:d["tasks"][0].update({"max_case_units":True}),
    lambda d:d["tasks"][1].update({"id":"BUSINESS_COST"}),
    lambda d:d["results"][0].update({"reported_latency_ms":100}),
    lambda d:d["results"][0].update({"reported_output_tokens":200}),
    lambda d:d["results"][0].update({"source":"LIVE_PROVIDER_RESPONSE"}),
    lambda d:d["results"][0].update({"generated_tags":["UNREGISTERED"]}),
    lambda d:d["results"][0].update({"model_id":"claude-opus-5-5"}),
    lambda d:d["results"].append(deepcopy(d["results"][0])),
])
def test_tampered_provider_model_data_rejected(mutate):
    data=fixture();mutate(data)
    with pytest.raises(SyntheticGrowthError):
        parse_model_fixture(raw(data))


@pytest.mark.parametrize("workspace",["academy_demo","bespoke_demo"])
def test_all_twelve_modules_and_five_engines_actually_connected(workspace):
    portfolio=build_governed_portfolio(workspace)
    assert portfolio["module_count"]==12 and portfolio["engine_count"]==5
    assert [m["id"] for m in portfolio["modules"]]==[m[0] for m in MODULES]
    assert [e["id"] for e in portfolio["engines"]]==list(ENGINES)
    assert all(len(m["source_record_sha256"])==64 for m in portfolio["modules"])
    assert all(set(m["engine_routes"])==set(MODULE_ENGINE_MAP[m["id"]])
               for m in portfolio["modules"])
    assert all(m["model_evaluation_task"]==MODULE_TASK_MAP[m["id"]]
               for m in portfolio["modules"])
    assert all(not m["external_tools_enabled"] and not m["human_owner_authenticated"]
               and not m["actual_business_evidence_verified"] for m in portfolio["modules"])
    assert all(not e["outbound_enabled"] and not e["real_model_assigned"]
               for e in portfolio["engines"])
    assert portfolio["safety"]["provider_calls"]==0
    assert portfolio["safety"]["live_customer_data"] is False
    assert portfolio["safety"]["verified_idp_connected"] is False
    assert portfolio["safety"]["production_ready"] is False
    assert portfolio["financial"]["verified_net_profit"] is None
    assert portfolio["financial"]["validated_roi"] is None
    assert portfolio["financial"]["gross_sales_demo"]-portfolio["financial"][
        "known_costs_demo"]==portfolio["financial"]["modeled_contribution_demo"]
    assert portfolio==build_governed_portfolio(workspace)


@pytest.mark.parametrize("module",list(MODULE_ENGINE_MAP))
def test_every_module_has_correct_virtual_tools_and_evaluation(module):
    portfolio=build_governed_portfolio()
    row=next(m for m in portfolio["modules"] if m["id"]==module)
    assert row["data_classification"]=="SYNTHETIC_ONLY"
    assert row["allowed_virtual_tools"]==[
        tool for tool,modules in VIRTUAL_TOOLS.items() if module in modules
    ]
    assert row["model_evaluation_task"] in TASK_IDS
    assert row["release_gate"]=="PRIVATE_STAGING_AUTH_AND_SOURCE_VERIFICATION_REQUIRED"


@pytest.mark.parametrize("ws",["",None,True,"real_business"])
def test_unknown_tenant_fails_not_defaulted(ws):
    with pytest.raises(SyntheticGrowthError):
        build_governed_portfolio(ws)


def test_invalid_goal_cannot_change_financial_metric_scope():
    with pytest.raises(SyntheticGrowthError):
        build_governed_portfolio(goal="GUARANTEED_ROI")
