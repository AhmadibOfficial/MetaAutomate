"""P2-03s: evidence-labeled business resilience and OpEx efficiency intelligence.

A deterministic offline analysis, NOT ML forecasts, verified profit, automated
failover, real 90-day results or business financial advice. All inputs synthetic.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_integrated_intelligence import build_integrated_suite

FIXTURE = (Path(__file__).resolve().parents[3]
           / "contracts/domains/v1/fixtures/synthetic_continuity_opex.v1.json")
MAX_BYTES = 32_768
WORKSPACES = ("academy_demo", "bespoke_demo")
RISK_CODES = ("SUPPLIER_DELAY", "SYSTEM_OUTAGE", "COST_LEAKAGE")
SCENARIOS = {
    "UNCHANGED": (0, 0),
    "DEMAND_DOWN_25": (2500, 0),
    "OPERATIONAL_COST_UP_20": (0, 2000),
    "COMBINED_STRESS": (2500, 2000),
}


def _require(condition: bool, message: str):
    if not condition:
        raise SyntheticGrowthError(message)


def _pairs(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
        _require(key not in result, "Duplicate source field")
        result[key] = value
    return result


def _bad_number(value: str):
    raise SyntheticGrowthError("Floating-point or non-finite numbers are not accepted")


def _int(value: Any, maximum: int, name: str) -> int:
    _require(type(value) is int and 0 <= value <= maximum, "Invalid numeric field: "+name)
    return value


def parse_continuity_fixture(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES
             and b"\x00" not in raw, "Invalid bounded fixture")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_float=_bad_number, parse_constant=_bad_number)
    except SyntheticGrowthError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed continuity input") from exc
    _require(type(doc) is dict and set(doc) ==
             {"schema_version","classification","currency","risk_inputs"},
             "Unexpected continuity root")
    _require(type(doc["schema_version"]) is int and doc["schema_version"]==1
             and doc["classification"]=="SYNTHETIC_SOURCE_ONLY"
             and doc["currency"]=="DEMO_CREDITS", "Unsupported fixture")
    rows=doc["risk_inputs"]
    _require(type(rows) is list and len(rows)==2, "Expected two synthetic scenarios")
    seen=set()
    for row in rows:
        _require(type(row) is dict and set(row)=={"workspace","operational","risks"},
                 "Invalid continuity workspace fields")
        ws=row["workspace"]
        _require(type(ws) is str and ws in WORKSPACES and ws not in seen,
                 "Repeated or unknown workspace")
        seen.add(ws)
        op=row["operational"]
        fields={"service_downtime_hours","late_supplier_deliveries",
                "unreconciled_cost_entries","unused_tool_seats"}
        _require(type(op) is dict and set(op)==fields, "Unexpected operational data")
        for name in fields: _int(op[name],10000,name)
        risks=row["risks"]
        _require(type(risks) is list and len(risks)==3, "Three ranked risks needed")
        seen_codes=set()
        for risk in risks:
            fields={"code","likelihood_score","impact_score",
                    "illustrative_loss_exposure","mitigation_cost","manual_playbook"}
            _require(type(risk) is dict and set(risk)==fields, "Unexpected risk fields")
            code=risk["code"]
            _require(type(code) is str and code in RISK_CODES and code not in seen_codes,
                     "Unsupported or repeated risk code")
            seen_codes.add(code)
            for key in ("likelihood_score","impact_score"):
                number=_int(risk[key],5,key)
                _require(number>=1,"Invalid 1-5 ordinal score")
            for key in ("illustrative_loss_exposure","mitigation_cost"):
                _int(risk[key],1_000_000,key)
            phrase=risk["manual_playbook"]
            _require(type(phrase) is str and 10<=len(phrase)<=160
                     and phrase.isprintable(), "Invalid playbook")
        _require(seen_codes==set(RISK_CODES),"Missing resilience review")
    _require(seen==set(WORKSPACES),"Missing business")
    return doc


def stress_test(workspace: str, scenario: str="UNCHANGED") -> dict:
    _require(workspace in WORKSPACES and type(workspace) is str,
             "Unsupported source-only business")
    _require(type(scenario) is str and scenario in SCENARIOS, "Unknown stress scenario")
    suite=build_integrated_suite(workspace)
    finance=suite["modules"]["finance"]
    sales_drop,cost_up=SCENARIOS[scenario]
    gross=finance["gross_sales"]
    costs=finance["total_identified_costs"]
    stressed_gross=gross*(10000-sales_drop)//10000
    stressed_costs=costs*(10000+cost_up)//10000
    return {
        "scenario":scenario,"workspace":workspace,"illustrative_gross_sales":stressed_gross,
        "illustrative_identified_costs":stressed_costs,
        "illustrative_contribution":stressed_gross-stressed_costs,
        "change_vs_current_modeled_contribution":
            stressed_gross-stressed_costs-finance["modeled_contribution"],
        "assumptions":{"gross_sales_reduction_bps":sales_drop,
                       "identified_cost_increase_bps":cost_up,
                       "cost_behavior_mode":"ALL_COSTS_FIXED_OR_SCALED_UNIFORMLY"},
        "forecast":False,"causal_effect_estimated":False,"actual_disruption":False,
        "automated_failover":False,"unmeasured_costs_excluded":True,
    }


def build_continuity_intelligence(workspace: str="academy_demo",
                                 *, raw_fixture: bytes | None=None) -> dict:
    _require(type(workspace) is str and workspace in WORKSPACES,
             "Unknown workspace")
    raw=FIXTURE.read_bytes() if raw_fixture is None else raw_fixture
    data=parse_continuity_fixture(raw)
    selected=next(row for row in data["risk_inputs"] if row["workspace"]==workspace)
    suite=build_integrated_suite(workspace)
    finance=suite["modules"]["finance"]
    ops=selected["operational"]
    risks=sorted(({
        "code":r["code"],
        "ordinal_priority":r["likelihood_score"]*r["impact_score"],
        "likelihood_scale":"ORDINAL_1_TO_5_NOT_PROBABILITY",
        "impact_scale":"ORDINAL_1_TO_5_NOT_MONETIZED_ESTIMATE",
        "exposure_example":r["illustrative_loss_exposure"],
        "mitigation_example":r["mitigation_cost"],
        "manual_review_action":r["manual_playbook"],
        "cost_avoided_verified":False,"auto_trigger_enabled":False,
    } for r in selected["risks"]),key=lambda x:(-x["ordinal_priority"],x["code"]))
    gross=finance["gross_sales"]
    costs=finance["total_identified_costs"]
    return {
        "milestone":"P2_03S_RESILIENCE_OPEX",
        "classification":"SYNTHETIC_SOURCE_ONLY",
        "workspace":workspace,
        "financial": {
            "illustrative_gross_sales":gross,
            "identified_costs":costs,
            "modeled_contribution":finance["modeled_contribution"],
            "identified_cost_to_sales_bps":costs*10000//gross if gross else None,
            "identified_cost_budget":finance["identified_cost_budget"],
            "cost_over_budget":max(0,finance["cost_vs_plan"]),
            "sales_per_identified_cost_bps":gross*10000//costs if costs else None,
            "cac":None,"ltv":None,"ebitda":None,"net_profit":None,
            "actual_savings":None,"costs_fully_reconciled":False,
        },
        "continuity": {
            **ops,"risk_reviews":risks,
            "predicted_incident_probability":None,
            "observed_business_impact_verified":False,
            "automatic_recovery_enabled":False,
        },
        "scenarios":{name:stress_test(workspace,name) for name in SCENARIOS},
        "pilot_90_days": [
            {"days":"01-30","stage":"ESTABLISH_BASELINE",
             "deliverable":"Review actual authorized cost classifications, KPIs and critical dependencies",
             "actual_evidence_complete":False},
            {"days":"31-60","stage":"SUPERVISED_IMPROVEMENTS",
             "deliverable":"Review prioritized expense leaks and continuity playbooks with owner approval",
             "actual_evidence_complete":False},
            {"days":"61-90","stage":"VERIFY_OUTCOMES",
             "deliverable":"Compare equal time windows and record uncertainty and competing explanations",
             "actual_evidence_complete":False},
        ],
        "evidence": {
            "source_suite_sha256":suite["source"]["value_evidence_sha256"],
            "risk_fixture_sha256":sha256(raw).hexdigest(),
            "all_business_data_real":False,"causation_demonstrated":False,
            "financial_profit_verified":False,"deployment_authorized":False,
            "provider_calls":0,"database_writes":0,
        },
    }
