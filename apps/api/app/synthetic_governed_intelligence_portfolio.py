"""P2-03w: 12-module / five-engine governance and evidence routing, offline.

Bridges the existing P2-03o suite and P2-03v signed two-person rehearsal without
opening any production, provider, model or customer-data execution path.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .synthetic_growth_autopilot import SyntheticGrowthError
from .synthetic_integrated_intelligence import (
    MODULES, ENGINES, build_integrated_suite,
)
from .synthetic_business_resilience import build_continuity_intelligence
from .synthetic_model_evaluation import evaluate_model_candidates
from .synthetic_oidc_identity import OfflineIdentityTrust, require_dual_identity
from .disposable_crm_authorization import verify_actor_token
from .synthetic_governed_orchestration import GovernedOrchestration

MODULE_ENGINE_MAP = {
    "objective": ("measurement","decision"),
    "value": ("measurement","learning"),
    "decision": ("decision","recommendation"),
    "growth": ("recommendation","automation"),
    "crm": ("measurement","automation"),
    "inventory": ("measurement","recommendation"),
    "finance": ("measurement","learning"),
    "marketing": ("measurement","automation"),
    "commerce": ("measurement","decision"),
    "workflow": ("automation","recommendation"),
    "operations": ("measurement","recommendation"),
    "executive": ENGINES,
}
MODULE_TASK_MAP = {
    "objective":"BUSINESS_COST", "value":"BUSINESS_COST",
    "decision":"BUSINESS_COST", "growth":"CONSENT_SOCIAL",
    "crm":"CONSENT_SOCIAL", "inventory":"SUPPLY_RISK",
    "finance":"BUSINESS_COST", "marketing":"CONSENT_SOCIAL",
    "commerce":"BUSINESS_COST", "workflow":"CONSENT_SOCIAL",
    "operations":"SUPPLY_RISK", "executive":"BUSINESS_COST",
}
VIRTUAL_TOOLS={
    "ANALYZE_SAMPLE": frozenset({"objective","value","decision","growth","crm",
        "inventory","finance","marketing","commerce","workflow","operations","executive"}),
    "GENERATE_REVIEW_PLAN": frozenset({"objective","decision","growth","crm",
        "inventory","marketing","workflow","operations","executive"}),
    "SUMMARIZE_EVIDENCE": frozenset({"objective","value","finance",
        "decision","commerce","operations","executive"}),
}
PURPOSES=frozenset({"REVIEW_BUSINESS_EVIDENCE","PREPARE_HUMAN_DECISION"})
PROHIBITED=frozenset({"RUN_LIVE_AI","SEND_MESSAGE","PUBLISH_POST","PLACE_ORDER",
                      "READ_CLIENT_RECORD","BILL_CUSTOMER","EXECUTE_SHELL"})


def need(ok, reason):
    if not ok: raise SyntheticGrowthError(reason)


def canonical(obj)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True).encode("ascii")


def build_governed_portfolio(workspace:str="academy_demo",
                              goal:str="CONTRIBUTION")->dict:
    suite=build_integrated_suite(workspace,goal)
    safety=suite["safety"]
    need(suite["classification"]=="SYNTHETIC_SOURCE_ONLY"
         and suite["workspace"]==workspace
         and safety["tenant_authentication_provided"] is False
         and safety["real_customer_data"] is False
         and safety["database_writes"]==0 and safety["provider_calls"]==0
         and safety["messages_sent"]==0 and safety["payments_processed"]==0
         and safety["production_ready"] is False,
         "A live or altered suite is forbidden")
    need(tuple(suite["modules"])==tuple(x[0] for x in MODULES)
         and tuple(suite["engines"])==ENGINES
         and tuple(MODULE_ENGINE_MAP)==tuple(x[0] for x in MODULES)
         and set(MODULE_TASK_MAP)==set(suite["modules"]),
         "Missing or reordered intelligence domain")
    finance=suite["modules"]["finance"]
    need(finance["modeled_contribution"]==
         finance["gross_sales"]-finance["total_identified_costs"],
         "Illustrative finance reconciliation failure")
    need(finance["net_profit"] is None
         and suite["modules"]["crm"]["outreach_enabled"] is False
         and suite["modules"]["marketing"]["posts_published"]==0
         and suite["modules"]["workflow"]["external_execution_enabled"] is False
         and suite["modules"]["growth"]["delivered"]==0
         and suite["engines"]["automation"]["outbound_actions"]==0
         and suite["engines"]["learning"]["controlled_causal_effect"] is None,
         "Undemonstrated commercial or provider outcome")
    continuity=build_continuity_intelligence(workspace)
    need(continuity["financial"]["modeled_contribution"]==
         finance["modeled_contribution"],
         "Continuity and finance must reconcile")
    evaluation=evaluate_model_candidates()
    modules=[]
    for name,title in MODULES:
        raw=suite["modules"][name]
        engines=MODULE_ENGINE_MAP[name]
        need(type(raw) is dict and all(e in ENGINES for e in engines),
             "Invalid module/engine connection")
        modules.append({
            "id":name,"name":title,
            "engine_routes":list(engines),
            "model_evaluation_task":MODULE_TASK_MAP[name],
            "source_record_sha256":sha256(canonical(raw)).hexdigest(),
            "data_classification":"SYNTHETIC_ONLY",
            "human_owner_authenticated":False,
            "actual_business_evidence_verified":False,
            "external_tools_enabled":False,
            "allowed_virtual_tools":[t for t,allowed in VIRTUAL_TOOLS.items()
                                     if name in allowed],
            "release_gate":"PRIVATE_STAGING_AUTH_AND_SOURCE_VERIFICATION_REQUIRED",
        })
    return {
        "milestone":"P2_03W_PORTFOLIO_GOVERNANCE",
        "classification":"SYNTHETIC_SOURCE_ONLY",
        "workspace":workspace,"goal":goal,
        "module_count":len(modules),"engine_count":len(ENGINES),
        "modules":modules,
        "engines":[{
            "id":name,"implementation_class":"EXISTING_SOURCE_ONLY",
            "synthetic_source_sha256":sha256(canonical(suite["engines"][name])).hexdigest(),
            "outbound_enabled":False,"real_model_assigned":False,
        } for name in ENGINES],
        "model_evaluation":{
            "model_ids":evaluation["candidate_model_ids"],
            "real_provider_benchmark":False,
            "runtime_model_selected":None,
            "real_model_calls":0,
            "fixture_sha256":evaluation["fixture_sha256"],
        },
        "financial":{
            "gross_sales_demo":finance["gross_sales"],
            "known_costs_demo":finance["total_identified_costs"],
            "modeled_contribution_demo":finance["modeled_contribution"],
            "verified_net_profit":None,"validated_roi":None,
        },
        "source_evidence":{
            "suite_fixture_sha256":suite["source"]["fixture_sha256"],
            "continuity_fixture_sha256":continuity["evidence"]["risk_fixture_sha256"],
        },
        "safety":{"live_customer_data":False,"provider_calls":0,"payments":0,
                  "production_ready":False,"verified_idp_connected":False,
                  "external_execution":False,"subscriptions":False},
    }


class GovernedIntelligenceGateway:
    """Dual-signature identity and virtual-tool proposal facade, no live worker."""
    def __init__(self,store:GovernedOrchestration,
                 trust:OfflineIdentityTrust):
        need(isinstance(store,GovernedOrchestration)
             and isinstance(trust,OfflineIdentityTrust),
             "Verified offline store and signer policies required")
        self.store=store
        self.trust=trust

    def _both(self,idp_jwt:str,app_actor_token:str,
              permitted_roles:tuple[str,...])->str:
        identity=self.trust.verify(idp_jwt,now=self.store._now())
        actor=verify_actor_token(app_actor_token,self.store.key,
                                  now=self.store._now())
        require_dual_identity(identity,actor)
        need(actor.role in permitted_roles,"Insufficient signed permissions")
        return identity.workspace

    def portfolio(self,idp_jwt:str,app_token:str,goal:str="CONTRIBUTION")->dict:
        workspace=self._both(idp_jwt,app_token,("auditor","reviewer","tenant_admin"))
        return build_governed_portfolio(workspace,goal)

    def propose(self,idp_jwt:str,app_token:str,ref:str,scenario:str)->dict:
        self._both(idp_jwt,app_token,("tenant_admin",))
        return self.store.propose(app_token,ref,scenario)

    def owner_approve(self,idp_jwt:str,app_token:str,ref:str)->dict:
        self._both(idp_jwt,app_token,("tenant_admin",))
        return self.store.approve_owner(app_token,ref)

    def security_approve(self,idp_jwt:str,app_token:str,ref:str)->dict:
        self._both(idp_jwt,app_token,("reviewer",))
        return self.store.approve_security(app_token,ref)

    def simulate(self,idp_jwt:str,app_token:str,ref:str)->dict:
        self._both(idp_jwt,app_token,("tenant_admin",))
        return self.store.run_synthetic(app_token,ref)

    def review_virtual_tool(self,idp_jwt:str,app_token:str,ref:str,
                            module_id:str,tool_id:str,purpose:str)->dict:
        ws=self._both(idp_jwt,app_token,("reviewer",))
        need(type(purpose) is str and purpose in PURPOSES,
             "Unrecognized task-bound tool purpose")
        need(type(module_id) is str and module_id in MODULE_ENGINE_MAP,
             "Unknown intelligence module")
        need(type(tool_id) is str and tool_id not in PROHIBITED
             and tool_id in VIRTUAL_TOOLS
             and module_id in VIRTUAL_TOOLS[tool_id],
             "Tool prohibited for business module")
        # The underlying reviewer must be the SAME security approver for
        # that tenant, original plan and signed session.
        result=self.store.review_tool(app_token,ref,tool_id)
        need(result["decision"]=="VIRTUAL_ONLY" and
             result["external_execution"] is False,"Unsafe tool execution")
        return {"workspace":ws,"module":module_id,"purpose":purpose,
                "tool_id":tool_id,"review_state":"VIRTUAL_REVIEW_ONLY",
                "actual_tool_calls":0,"network_calls":0,
                "real_model_calls":0,"customer_data_accessed":False,
                "actual_execution_authorized":False}

    def audit(self,idp_jwt:str,app_token:str,checkpoint:str|None=None)->dict:
        self._both(idp_jwt,app_token,("auditor","tenant_admin"))
        return self.store.audit_report(app_token,trusted_head=checkpoint)
