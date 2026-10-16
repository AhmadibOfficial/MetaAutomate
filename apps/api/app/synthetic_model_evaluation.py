"""P2-03w: task-based frontier-model adapter evaluation *simulator*.

Model identifiers are from official provider docs, but scores are only from
prewritten fixture tags. No SDK, API calls, ranking, runtime prices or measured
quality/latency. No customer data, bills, subscriptions or model inference.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .synthetic_growth_autopilot import SyntheticGrowthError

SOURCE=Path(__file__).resolve().parents[3]/"contracts/domains/v1/fixtures/synthetic_model_evaluation.v1.json"
MODEL_IDS=frozenset({"gpt-6-astra","gpt-6.1-sol","gpt-6-luna","claude-opus-5-5"})
TASK_IDS=frozenset({"BUSINESS_COST","SUPPLY_RISK","SECURITY_REVIEW","CONSENT_SOCIAL"})
ALLOWED_TAGS=frozenset({
    "COST_NOT_PROFIT","BASELINE_NEEDED","GUARANTEED_SAVINGS","INCOME_PROMISE",
    "REVIEW_SUPPLIER","NO_PREDICTIVE_CLAIM","GUARANTEED_AVOIDED_LOSS","AUTO_ORDER",
    "AUTHORIZATION_REQUIRED","HUMAN_TRIAGE","EXPLOIT_UNAUTHORIZED","SEND_EXTERNAL",
    "CONSENT_NOT_VERIFIED","HUMAN_PUBLISHING","AUTO_PUBLISH","UNSOLICITED_MESSAGE",
    "NO_EARNINGS_ASSERTION",
})


def require(ok:bool, reason:str):
    if not ok: raise SyntheticGrowthError(reason)


def pairs_no_duplicates(pairs):
    result={}
    for name,value in pairs:
        require(name not in result,"Duplicate model-evaluation JSON field")
        result[name]=value
    return result


def reject_fraction(_):
    raise SyntheticGrowthError("Float and nonfinite model scores rejected")


def exact(obj:Any,keys:set[str],what:str):
    require(type(obj) is dict and set(obj)==keys,"Unrecognized "+what+" fields")
    return obj


def parse_model_fixture(raw:bytes)->dict:
    require(type(raw) is bytes and 0<len(raw)<=32000 and b"\x00" not in raw,
            "Invalid bounded model fixture")
    try:
        doc=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs_no_duplicates,
                       parse_float=reject_fraction,parse_constant=reject_fraction)
    except SyntheticGrowthError: raise
    except (ValueError,UnicodeDecodeError,RecursionError) as exc:
        raise SyntheticGrowthError("Malformed model evaluation fixture") from exc
    exact(doc,{"schema_version","classification","as_of_date","real_provider_api_calls",
               "real_model_benchmark","models","tasks","results"},"root")
    require(type(doc["schema_version"]) is int and doc["schema_version"]==1
            and doc["classification"]=="SYNTHETIC_PREWRITTEN_MODEL_OUTPUTS"
            and doc["as_of_date"]=="2026-10-16" and
            type(doc["real_provider_api_calls"]) is int
            and doc["real_provider_api_calls"]==0
            and doc["real_model_benchmark"] is False,
            "Only non-live model fixture allowed")
    models=doc["models"]
    require(type(models) is list and len(models)==len(MODEL_IDS),
            "Expected complete reference model catalog")
    seen=set()
    for model in models:
        exact(model,{"provider","id","label","source_url","fixture_evaluation_only"},"model")
        ident=model["id"]
        require(type(ident) is str and ident in MODEL_IDS and ident not in seen,
                "Unknown or duplicate model")
        seen.add(ident)
        require(model["provider"]==("anthropic" if ident.startswith("claude") else "openai")
                and model["fixture_evaluation_only"] is True
                and type(model["source_url"]) is str
                and model["source_url"].startswith(
                    "https://platform.claude.com/" if ident.startswith("claude")
                    else "https://developers.openai.com/")
                and type(model["label"]) is str and 5<=len(model["label"])<=55,
                "Unsupported provider, model provenance or evaluation flag")
    tasks=doc["tasks"];require(type(tasks) is list and len(tasks)==len(TASK_IDS),
                              "Incomplete model task catalog")
    seen=set();task_lookup={}
    for task in tasks:
        exact(task,{"id","category","prompt_id","required_tags",
                    "forbidden_tags","max_case_units"},"task")
        ident=task["id"]
        require(type(ident) is str and ident in TASK_IDS and ident not in seen,
                "Unknown or duplicate model task")
        seen.add(ident);task_lookup[ident]=task
        require(type(task["category"]) is str and 4<=len(task["category"])<=40
                and type(task["prompt_id"]) is str
                and task["prompt_id"].startswith("SIM-CASE-")
                and type(task["max_case_units"]) is int
                and task["max_case_units"]==10,"Bad synthetic task")
        for key in ("required_tags","forbidden_tags"):
            tags=task[key]
            require(type(tags) is list and tags and
                    all(type(x) is str and x in ALLOWED_TAGS for x in tags)
                    and len(set(tags))==len(tags),"Invalid evaluator tags")
        require(not set(task["required_tags"]) & set(task["forbidden_tags"]),
                "Contradictory task rubric")
    results=doc["results"]
    require(type(results) is list and len(results)==len(MODEL_IDS)*len(TASK_IDS),
            "Incomplete synthetic answer matrix")
    seen=set()
    for result in results:
        exact(result,{"model_id","task_id","generated_tags","reported_latency_ms",
                      "reported_input_tokens","reported_output_tokens","source"},"result")
        mid,tid=result["model_id"],result["task_id"]
        require(type(mid) is str and mid in MODEL_IDS and
                type(tid) is str and tid in TASK_IDS and (mid,tid) not in seen,
                "Unexpected or repeated model response")
        seen.add((mid,tid))
        tags=result["generated_tags"]
        require(type(tags) is list and all(type(x) is str and x in ALLOWED_TAGS
                for x in tags) and len(tags)==len(set(tags)),
                "Invalid sample response tags")
        require(result["source"]=="PREWRITTEN_FIXTURE_NOT_PROVIDER_RESPONSE"
                and all(type(result[key]) is int and result[key]==0
                        for key in ("reported_latency_ms","reported_input_tokens",
                                    "reported_output_tokens")),
                "Real model measurements or responses are not accepted")
    return doc


def evaluate_model_candidates(*,raw_fixture:bytes|None=None)->dict:
    raw=SOURCE.read_bytes() if raw_fixture is None else raw_fixture
    data=parse_model_fixture(raw)
    tasks={x["id"]:x for x in data["tasks"]}
    matrix=[]
    for result in data["results"]:
        task=tasks[result["task_id"]];tags=set(result["generated_tags"])
        expected=set(task["required_tags"])
        forbidden=set(task["forbidden_tags"])
        complete=expected.issubset(tags)
        safe=not bool(forbidden & tags)
        matrix.append({
            "model_id":result["model_id"],
            "task_id":result["task_id"],
            "sample_expected_tags_covered":len(expected&tags),
            "sample_expected_tags_total":len(expected),
            "sample_rubric_complete":complete,
            "sample_safety_tags_clear":safe,
            "production_model_passed":False,
        })
    return {
        "classification":"SYNTHETIC_FIXTURE_NOT_A_BENCHMARK",
        "candidate_model_ids":[x["id"] for x in data["models"]],
        "candidate_provider_docs":{x["id"]:x["source_url"] for x in data["models"]},
        "sample_case_results":matrix,
        "observed_provider_quality":None,
        "measured_latency_ms":None,
        "observed_cost_usd":None,
        "ranked_live_model":None,
        "model_choice_recommendation":"EVALUATE_ON_REPRESENTATIVE_AUTHORIZED_TASKS",
        "external_model_adapter_enabled":False,
        "model_api_calls":0,
        "inference_tokens_used":0,
        "training_or_personal_data_used":False,
        "fixture_sha256":sha256(raw).hexdigest(),
    }
