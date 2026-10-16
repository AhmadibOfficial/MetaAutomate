"""P2-03y — deterministic PRIVATE STAGING security acceptance, no release.

This gate records missing live evidence for F04-F09 and AI-agent-specific controls.
No test output, simulated model evaluation or signed CI identity can authorize
deployment, real customer data, private IdP enrollment, or paid model calls.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .synthetic_growth_autopilot import SyntheticGrowthError

ROOT=Path(__file__).resolve().parents[3]
POLICY=ROOT/"contracts/domains/v1/policies/p2_03y_private_staging_acceptance.v1.json"
FOUNDATION=ROOT/"docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
MANDATORY={
    "F04":"GITHUB_REQUIRED_CHECK_DENIAL",
    "F05":"PRIVATE_PERIMETER_INSPECTION",
    "F06":"LIVE_IDP_LOGIN_REVOCATION_TRACE",
    "F07":"OFFHOST_RESTORE_INDEPENDENT_WITNESS",
    "F08":"SECURITY_ACCEPTANCE_RUN",
    "F09":"CONSENTED_PILOT_MEASUREMENT",
}
INTELLIGENCE={
    "OIDC":"ISSUER_SIGNED_ID_TOKEN_AND_LIVE_LOGIN_CALLBACK",
    "AGENT":"ENFORCED_RUNTIME_EGRESS_DENIAL",
    "MODEL":"APPROVED_BUDGET_AND_QUALITY_SAFETY_COST_EVALUATION",
    "TOOLS":"LIVE_TOKEN_SCOPE_AND_REPLAY_NEGATIVE_TEST",
    "DATA":"CONSENT_SOURCE_PROVENANCE_REVIEW",
    "RECOVERY":"SIGNED_OFFHOST_BACKUP_RESTORE_RUN",
}
VALID_MODEL_TASKS=frozenset({
    "BUSINESS_COST","SUPPLY_RISK","SECURITY_REVIEW","CONSENT_SOCIAL"
})
VALID_MODELS=frozenset({
    "gpt-6-astra","gpt-6.1-sol","gpt-6-luna","claude-opus-5-5"
})


def require(ok:bool,reason:str)->None:
    if not ok:
        raise SyntheticGrowthError(reason)


def unique_pairs(pairs:list[tuple[str,Any]])->dict:
    out={}
    for key,value in pairs:
        require(key not in out,"Duplicate security acceptance key")
        out[key]=value
    return out


def reject_fraction(_):
    raise SyntheticGrowthError("Fractional or nonfinite evidence rejected")


def parse_json(raw:bytes,*,max_bytes:int=16000)->dict:
    require(type(raw) is bytes and 0<len(raw)<=max_bytes and b"\x00" not in raw,
            "Invalid bounded security policy input")
    try:
        d=json.loads(raw.decode("utf-8"),object_pairs_hook=unique_pairs,
                     parse_float=reject_fraction,parse_constant=reject_fraction)
    except SyntheticGrowthError:
        raise
    except (UnicodeDecodeError,ValueError,RecursionError) as exc:
        raise SyntheticGrowthError("Malformed security policy JSON") from exc
    require(type(d) is dict,"Expected security policy object")
    return d


def check_policy(document:dict)->None:
    required_root={
        "schema_version","classification","environment","environment_approval",
        "customer_data_allowed","real_model_calls_allowed",
        "live_external_tools_allowed","release_authorized",
        "foundation_verified","foundation_total","phase02_operational_go",
        "phase03_operational_go","requirements","intelligence_gates",
        "source_rehearsal",
    }
    require(type(document) is dict and set(document)==required_root,
            "Unreviewed security acceptance policy")
    require(type(document["schema_version"]) is int
            and document["schema_version"]==1
            and document["classification"]=="SOURCE_ONLY_PRIVATE_STAGING_ACCEPTANCE"
            and document["environment"]=="NOT_PROVISIONED"
            and document["environment_approval"]=="MISSING"
            and type(document["foundation_verified"]) is int
            and document["foundation_verified"]==3
            and type(document["foundation_total"]) is int
            and document["foundation_total"]==9,
            "Do not misrepresent Foundation readiness")
    for k in ("customer_data_allowed","real_model_calls_allowed",
              "live_external_tools_allowed","release_authorized",
              "phase02_operational_go","phase03_operational_go"):
        require(document[k] is False,"Unapproved live execution claimed: "+k)
    requirements=document["requirements"]
    require(type(requirements) is list and len(requirements)==len(MANDATORY),
            "All six blocked operational gates required")
    found=set()
    for gate in requirements:
        require(type(gate) is dict and set(gate)=={
            "id","name","evidence_kind","independent_witness","available"
        },"Unknown foundational gate fields")
        key=gate["id"]
        require(type(key) is str and key in MANDATORY and key not in found
                and gate["evidence_kind"]==MANDATORY[key]
                and type(gate["name"]) is str and 8<=len(gate["name"])<=160
                and gate["independent_witness"] is True
                and gate["available"] is False,
                "Invalid gate or unsupported operational evidence claim")
        found.add(key)
    require(found==set(MANDATORY),"Missing mandatory F04-F09 gate")
    ai=document["intelligence_gates"]
    require(type(ai) is list and len(ai)==len(INTELLIGENCE),
            "Expected six Intelligence security controls")
    found=set()
    for gate in ai:
        require(type(gate) is dict
                and set(gate)=={"id","name","proof","verified"},
                "Unexpected Intelligence control")
        key=gate["id"]
        require(type(key) is str and key in INTELLIGENCE and key not in found
                and gate["proof"]==INTELLIGENCE[key]
                and type(gate["name"]) is str and 8<=len(gate["name"])<=160
                and gate["verified"] is False,
                "Unsupported real Intelligence evidence")
        found.add(key)
    require(found==set(INTELLIGENCE),"Missing Intelligence control")
    rehearsal=document["source_rehearsal"]
    require(type(rehearsal) is dict and set(rehearsal)=={
        "project_ids","data","max_model_calls","network_requests",
        "cloud_resources_provisioned","paid_subscriptions","manual_release_only"
    } and rehearsal["project_ids"]==["academy_demo","bespoke_demo"]
    and rehearsal["data"]=="SYNTHETIC_ONLY"
    and all(type(rehearsal[key]) is int and rehearsal[key]==0
            for key in ("max_model_calls","network_requests",
                        "cloud_resources_provisioned","paid_subscriptions"))
    and rehearsal["manual_release_only"] is True,
            "Source rehearsal must not activate infrastructure or subscriptions")


def check_foundation(document:dict)->dict:
    require(type(document) is dict
            and document.get("schema_version")==1
            and document.get("phase")=="01-foundation"
            and document.get("policy")=="NO_GO_UNTIL_ALL_NINE_VERIFIED",
            "Unexpected Foundation exit source")
    checks=document.get("checks")
    require(type(checks) is list and len(checks)==9,"Nine F01-F09 gates required")
    state={}
    for i,gate in enumerate(checks,1):
        expected="F"+str(i).zfill(2)
        require(type(gate) is dict and gate.get("id")==expected
                and gate.get("status") in ("verified","blocked"),
                "Missing or altered Foundation gate")
        state[expected]=gate["status"]
    require(all(state[f"F{i:02}"]=="verified" for i in range(1,4))
            and all(state[f"F{i:02}"]=="blocked" for i in range(4,10)),
            "Source-only tests cannot silently promote operational controls")
    return state


def check_staging_runtime(compose:dict)->dict:
    """Inspect existing template; identify network barriers still unproven."""
    try:
        from scripts.verify_private_staging_contract import check
    except ImportError:
        # Scripts aren't always packages when PYTHONPATH=apps/api; repository
        # root can instead call the public source verifier CLI.
        return {"source_profile_checked":False,
                "network_isolation_proven":False,
                "agent_worker_isolated":False,
                "model_provider_egress_enforced":False,
                "blockers":["SOURCE_CONTRACT_VALIDATOR_IMPORT_UNAVAILABLE"]}
    issues=check(compose)
    require(not issues,"Private staging source template drift: "+", ".join(issues))
    api=compose["services"]["api"]
    networks=compose["networks"]
    # Existing API attaches to an unrestricted egress network; this is not
    # sufficient as a deny-by-default model/agent tool capability boundary.
    require(api["networks"]==["db","egress"] and networks["egress"]=={},
            "Unexpected staging network policy")
    return {
        "source_profile_checked":True,
        "network_isolation_proven":False,
        "agent_worker_isolated":False,
        "model_provider_egress_enforced":False,
        "blockers":[
            "UNRESTRICTED_API_EGRESS_REQUIRES_NETWORK_ENFORCEMENT",
            "NO_SEPARATE_DEPLOYED_AGENT_RUNTIME",
            "NO_MEASURED_OUTBOUND_DENIAL_TEST",
        ],
    }


def evaluate_model_request(request:dict)->dict:
    """Model selection admission is planning-only; no adapter is callable."""
    require(type(request) is dict and set(request)=={
        "model_id","task_id","synthetic_only","max_cost_minor",
        "human_approval_verified","real_provider_token_present"
    },"Model policy requires exact task, data and authorization scope")
    require(type(request["model_id"]) is str
            and request["model_id"] in VALID_MODELS
            and type(request["task_id"]) is str
            and request["task_id"] in VALID_MODEL_TASKS,
            "Unknown provider/model or evaluation task")
    require(request["synthetic_only"] is True
            and request["human_approval_verified"] is False
            and request["real_provider_token_present"] is False
            and type(request["max_cost_minor"]) is int
            and request["max_cost_minor"]==0,
            "Live model use requires separate financial, security and user approval")
    return {
        "classification":"PREVIEW_ONLY",
        "model":request["model_id"],"task":request["task_id"],
        "provider_inference_authorized":False,
        "model_api_calls":0,"customer_data":False,
        "benchmark_verified":False,"model_quality_measured":False,
        "latency_measured":False,"cost_measured":False,
    }


def evaluate_recovery_receipt(receipt:dict)->dict:
    """Check report structure but never treat a submitted receipt as verified."""
    fields={
        "backup_sha256","restore_sha256","backup_encrypted","off_host",
        "separate_failure_domain","observed_rpo_seconds",
        "observed_rto_seconds","independent_witness_id",
        "external_anchor_verified",
    }
    require(type(receipt) is dict and set(receipt)==fields,
            "Incomplete independent recovery evidence")
    require(all(type(receipt[x]) is str
                and re.fullmatch(r"[0-9a-f]{64}",receipt[x]) is not None
                for x in ("backup_sha256","restore_sha256"))
            and all(type(receipt[x]) is bool for x in
                    ("backup_encrypted","off_host","separate_failure_domain",
                     "external_anchor_verified"))
            and type(receipt["observed_rpo_seconds"]) is int
            and 0<=receipt["observed_rpo_seconds"]<=604800
            and type(receipt["observed_rto_seconds"]) is int
            and 0<=receipt["observed_rto_seconds"]<=604800
            and type(receipt["independent_witness_id"]) is str
            and re.fullmatch(r"[A-Z0-9-]{6,70}",
                             receipt["independent_witness_id"]) is not None,
            "Unreviewed recovery fields")
    complete=all(receipt[k] is True for k in
                 ("backup_encrypted","off_host","separate_failure_domain",
                  "external_anchor_verified"))
    return {
        "self_reported_structural_completeness":complete,
        "actual_restore_independently_verified":False,
        "external_artifacts_read_and_validated":False,
        "f07_verified":False,
        "source_only_testing":"NOT_LIVE_RECOVERY",
    }


def source_acceptance_report(*,policy_raw:bytes|None=None,
                             foundation_raw:bytes|None=None)->dict:
    p_raw=POLICY.read_bytes() if policy_raw is None else policy_raw
    f_raw=FOUNDATION.read_bytes() if foundation_raw is None else foundation_raw
    policy=parse_json(p_raw)
    foundation=parse_json(f_raw)
    check_policy(policy)
    state=check_foundation(foundation)
    return {
        "milestone":"P2_03Y_PRIVATE_STAGING_SECURITY_ACCEPTANCE",
        "classification":"SOURCE_ONLY_NOT_OPERATIONAL",
        "source_policy_sha256":sha256(p_raw).hexdigest(),
        "source_foundation_sha256":sha256(f_raw).hexdigest(),
        "foundation_verified":sum(x=="verified" for x in state.values()),
        "foundation_total":len(state),
        "missing_foundation_controls":list(MANDATORY),
        "missing_intelligence_controls":list(INTELLIGENCE),
        "source_identity_verifier_implemented":True,
        "real_staff_login_verified":False,
        "live_mfa_verified":False,
        "source_only_model_request_policy_implemented":True,
        "live_model_evaluation_verified":False,
        "private_worker_egress_verified":False,
        "independent_restore_verified":False,
        "actual_customer_data_processed":False,
        "subscriptions_purchased":False,
        "private_staging_provisioned":False,
        "external_tools_enabled":False,
        "production_go":False,
        "public_website_deployment_authorized":False,
    }
