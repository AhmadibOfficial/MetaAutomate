"""P2-03j: goal-driven Growth Autopilot orchestration, source-only.

Pure deterministic decisions over committed synthetic evidence. The engine has
NO executable provider adapters, live users, tenant authentication, network,
scheduler, send operation, durable replay store, subscriptions, or payment path.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from app.synthetic_growth_autopilot import (
    FIXTURE as GROWTH_FIXTURE, parse_growth_fixture, render_growth_preview,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "contracts/domains/v1/growth_automation_integrations.v1.json"
SCENARIOS_PATH = ROOT / "contracts/domains/v1/fixtures/synthetic_growth_orchestration.v1.json"
MAX_BYTES = 32_768
WORKSPACES = {"academy_demo": "education", "bespoke_demo": "apparel"}
GOALS = {
    "academy_demo": ("CONTRIBUTION_AFTER_MARKETING_AND_WORKFLOW_COSTS", {"LEAD_OPT_IN", "LEARNING_COMPLETED"}),
    "bespoke_demo": ("REPEAT_ORDER_COUNT", {"PURCHASE_COMPLETED", "GARMENT_DELIVERED"}),
}
PROVIDER_CAPABILITIES = {
    "SELAR": ("education", "apparel", "COMMERCE_EVENT_READ", True),
    "METRICOOL": ("education", "apparel", "SOCIAL_CONTENT_DRAFT", False),
    "EMAIL_MARKETING": ("education", "apparel", "OPT_IN_OUTREACH_DRAFT", False),
    "CUSTOMER_MESSAGING": ("education", "apparel", "SUPPORT_MESSAGE_DRAFT", False),
    "SUBSCRIPTION_BILLING": ("education", "apparel", "ENTITLEMENT_DESIGN", False),
}
PROVIDER_FOR_EVENT = {
    "LEAD_OPT_IN": "EMAIL_MARKETING",
    "CHECKOUT_ABANDONED": "SELAR",
    "PURCHASE_COMPLETED": "CUSTOMER_MESSAGING",
    "LEARNING_COMPLETED": "EMAIL_MARKETING",
    "GARMENT_DELIVERED": "CUSTOMER_MESSAGING",
}
KNOWN_STATES = {
    "REVIEW_REQUIRED", "SUPPRESSED_PROVIDER_OWNS", "SUPPRESSED_NO_MARKETING_CONSENT"
}
DEMO_ID = re.compile(r"DEMO-[A-Z0-9-]{4,40}\Z")
READINESS_GATES = (
    "FOUNDATION_RELEASE_APPROVAL",
    "AUTHENTICATED_TENANT_ISOLATION",
    "CONSENT_AND_PROVIDER_AUTHORIZATION",
    "DURABLE_IDEMPOTENCY_AND_AUDIT",
    "VERIFIED_INCREMENTAL_CUSTOMER_VALUE",
    "BILLING_ENTITLEMENTS_AND_COMMERCIAL_APPROVAL",
)


class GrowthOrchestrationError(ValueError):
    """Fail-closed source contract or sample data violation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GrowthOrchestrationError(message)


def exact(value: object, names: set[str], label: str) -> dict:
    require(type(value) is dict and set(value) == names,
            f"{label}: unexpected or missing fields")
    return value


def bounded_int(value: object, min_value: int, max_value: int, name: str) -> int:
    require(type(value) is int and min_value <= value <= max_value,
            f"{name}: invalid integer")
    return value


def object_pairs(pairs: list[tuple[str, object]]) -> dict:
    data: dict = {}
    for key, value in pairs:
        require(key not in data, "Duplicate JSON field denied")
        data[key] = value
    return data


def reject_number(_: str):
    raise GrowthOrchestrationError("Float/non-finite number denied")


def strict_json(raw: bytes) -> dict:
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\x00" not in raw,
            "Input bytes are empty, invalid or too large")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs,
                         parse_constant=reject_number, parse_float=reject_number)
    except GrowthOrchestrationError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise GrowthOrchestrationError("Invalid JSON") from exc
    require(type(obj) is dict, "Root must be an object")
    return obj


def canonical_hash(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("ascii")).hexdigest()


def parse_provider_contract(raw: bytes) -> dict:
    obj = exact(strict_json(raw),
                {"schema_version", "classification", "execution_mode",
                 "providers", "safety_policy"}, "provider contract")
    require(type(obj["schema_version"]) is int and obj["schema_version"] == 1,
            "Unsupported integration contract")
    require(obj["classification"] == "SOURCE_DESIGN_ONLY" and
            obj["execution_mode"] == "NO_EXTERNAL_EXECUTION",
            "Operational provider integration is not authorized")
    safety = exact(obj["safety_policy"], {"customer_approval_required",
                   "consent_verification_required", "durable_replay_protection_enabled",
                   "customer_data_enabled", "billing_enabled", "live_activation_enabled"},
                   "integration safety policy")
    require(safety == {
        "customer_approval_required": True,
        "consent_verification_required": True,
        "durable_replay_protection_enabled": False,
        "customer_data_enabled": False,
        "billing_enabled": False,
        "live_activation_enabled": False,
    }, "Unsafe integration policy")
    providers = obj["providers"]
    require(type(providers) is list and len(providers) == len(PROVIDER_CAPABILITIES),
            "Invalid integration list")
    seen: set[str] = set()
    for entry in providers:
        p = exact(entry, {"provider_id", "supported_business_types", "capability",
                          "provider_owns_checkout_recovery", "connection_state",
                          "credential_use_enabled", "external_execution_enabled"}, "provider")
        pid = p["provider_id"]
        require(type(pid) is str and pid in PROVIDER_CAPABILITIES and pid not in seen,
                "Unexpected or duplicate provider")
        seen.add(pid)
        types = PROVIDER_CAPABILITIES[pid]
        require(p["supported_business_types"] == list(types[:2])
                and p["capability"] == types[2]
                and type(p["provider_owns_checkout_recovery"]) is bool
                and p["provider_owns_checkout_recovery"] is types[3],
                "Misdeclared provider role")
        require(p["connection_state"] == "CONTRACT_ONLY"
                and p["credential_use_enabled"] is False
                and p["external_execution_enabled"] is False,
                "Live provider capability prohibited")
    require(seen == set(PROVIDER_CAPABILITIES), "Missing provider contract")
    return obj


def parse_scenarios(raw: bytes, growth: dict) -> dict:
    obj = exact(strict_json(raw),
                {"schema_version", "classification", "currency", "workspaces"},
                "orchestration scenarios")
    require(type(obj["schema_version"]) is int and obj["schema_version"] == 1,
            "Unsupported orchestration scenarios")
    require(obj["classification"] == "SYNTHETIC_DEMO_ONLY"
            and obj["currency"] == "DEMO_CREDITS",
            "Only committed source scenarios are allowed")
    rows = obj["workspaces"]
    require(type(rows) is list and len(rows) == 2, "Unexpected workspace count")
    source = {g["workspace"]: g for g in growth["workspaces"]}
    names: set[str] = set()
    for row in rows:
        q = exact(row, {"workspace", "goal", "funnel", "workflow_cost_demo_credits",
                        "replayed_event_ids", "subscription_research_tier"}, "workspace scenario")
        name = q["workspace"]
        require(type(name) is str and name in WORKSPACES and name not in names,
                "Duplicate/unknown business workspace")
        names.add(name)
        goal = exact(q["goal"], {"metric", "target", "priority_event_types"}, "goal")
        expected_metric, expected_events = GOALS[name]
        require(goal["metric"] == expected_metric, "Goal incompatible with workspace")
        bounded_int(goal["target"], 1, 100_000_000, "Goal target")
        events = goal["priority_event_types"]
        require(type(events) is list and len(events) == 2
                and all(type(v) is str for v in events)
                and set(events) == expected_events, "Invalid goal trigger mapping")
        funnel = exact(q["funnel"], {"measured_sessions", "qualified_enquiries"},
                       "funnel")
        sessions = bounded_int(funnel["measured_sessions"], 1, 100_000,
                               "Synthetic session count")
        enquiries = bounded_int(funnel["qualified_enquiries"], 0, sessions,
                                "Synthetic enquiry count")
        unique_buyer_journeys = len({o["journey_id"] for o in source[name]["orders"]})
        require(unique_buyer_journeys <= sessions, "Buyer count exceeds sessions")
        require(enquiries >= unique_buyer_journeys, "Enquiries below buyer count")
        bounded_int(q["workflow_cost_demo_credits"], 0, 1_000_000,
                    "Synthetic workflow operating cost")
        event_ids = {e["event_id"] for e in source[name]["events"]}
        replays = q["replayed_event_ids"]
        require(type(replays) is list and 0 < len(replays) <= 4
                and all(type(event) is str and DEMO_ID.fullmatch(event) for event in replays)
                and len(set(replays)) == len(replays)
                and set(replays).issubset(event_ids), "Invalid or cross-workspace replay event")
        require(q["subscription_research_tier"] in
                ("STARTER_RESEARCH", "GROWTH_RESEARCH"), "Unknown pricing research tier")
    require(names == set(WORKSPACES), "Missing workspace")
    return obj


def orchestrate(growth_raw: bytes, scenarios_raw: bytes, contract_raw: bytes,
                *, workspace: str = "all") -> dict:
    """Build a deterministic in-memory proposal report; never approve or execute."""
    growth = parse_growth_fixture(growth_raw)
    providers = parse_provider_contract(contract_raw)
    scenarios = parse_scenarios(scenarios_raw, growth)
    require(type(workspace) is str and workspace in {"all"} | set(WORKSPACES),
            "Invalid requested workspace")
    base = render_growth_preview(growth_raw)
    preview_by_name = {group["workspace"]: group for group in base["businesses"]}
    growth_by_name = {group["workspace"]: group for group in growth["workspaces"]}
    results = []
    for scenario in scenarios["workspaces"]:
        wid = scenario["workspace"]
        if workspace != "all" and workspace != wid:
            continue
        source = growth_by_name[wid]
        foundation = preview_by_name[wid]
        goal = scenario["goal"]
        finance = foundation["financial_summary"]
        cost = scenario["workflow_cost_demo_credits"]
        contribution = finance["modeled_contribution_after_spend_demo_credits"] - cost
        orders = source["orders"]
        unique_buyers = len({order["journey_id"] for order in orders})
        sessions = scenario["funnel"]["measured_sessions"]
        conversion_bps = unique_buyers * 10_000 // sessions
        repeats = finance["fictional_repeat_orders"]
        actual_goal = (contribution if goal["metric"] ==
                       "CONTRIBUTION_AFTER_MARKETING_AND_WORKFLOW_COSTS" else repeats)
        target = goal["target"]
        seen_actions: set[str] = set()
        work_queue = []
        for action in foundation["automation_proposals"]:
            require(action["state"] in KNOWN_STATES, "Unexpected source proposal status")
            event = next(e for e in source["events"]
                         if e["event_id"] == action["event_id"])
            provider = PROVIDER_FOR_EVENT[event["event_type"]]
            decision = action["state"]
            if decision == "SUPPRESSED_PROVIDER_OWNS":
                require(provider == "SELAR" and event["event_type"] == "CHECKOUT_ABANDONED",
                        "Provider recovery override denied")
            if decision == "SUPPRESSED_NO_MARKETING_CONSENT":
                require(event["consent_status"] != "SYNTHETIC_OPTED_IN",
                        "Consent suppression state mismatch")
            if decision == "REVIEW_REQUIRED":
                require(event["consent_status"] == "SYNTHETIC_OPTED_IN",
                        "Unconsented draft denied")
            dedupe_key = canonical_hash({"workspace": wid, "event_id": event["event_id"],
                                         "recipe": action["recipe"], "provider": provider})[:24]
            require(dedupe_key not in seen_actions, "Duplicate generated proposal")
            seen_actions.add(dedupe_key)
            work_queue.append({
                "source_event_id": event["event_id"],
                "workspace": wid,
                "provider_contract": provider,
                "source_event_type": event["event_type"],
                "goal_relevance": ("HIGH" if event["event_type"] in
                                   goal["priority_event_types"] else "STANDARD"),
                "recipe": action["recipe"],
                "review_state": decision,
                "idempotency_preview": dedupe_key,
                "approval_granted": False,
                "dispatch_enabled": False,
                "customer_message_sent": False,
                "provider_connected": False,
                "event_consented_in_production": False,
                "reason": ("NATIVE_PROVIDER_RECOVERY" if decision ==
                           "SUPPRESSED_PROVIDER_OWNS" else
                           "NO_VERIFIED_CONSENT" if decision ==
                           "SUPPRESSED_NO_MARKETING_CONSENT" else
                           "HUMAN_REVIEW_WITH_LIVE_INTEGRATION_DISABLED"),
            })
        duplicates = []
        for eid in scenario["replayed_event_ids"]:
            event = next((x for x in work_queue if x["source_event_id"] == eid), None)
            require(event is not None, "Replay event does not belong to workspace")
            duplicates.append({"workspace": wid, "event_id": eid,
                               "idempotency_preview": event["idempotency_preview"],
                               "decision": "DUPLICATE_SOURCE_EVENT_SUPPRESSED",
                               "durably_enforced": False})
        results.append({
            "workspace": wid, "business_type": WORKSPACES[wid],
            "goal": {"metric": goal["metric"], "target": target, "current": actual_goal,
                     "shortfall": max(0, target - actual_goal),
                     "progress_basis_points": max(0, min(10_000,
                                                           actual_goal * 10_000 // target))},
            "measurement": {
                "measurement_status": "SYNTHETIC_SCENARIO_NON_CAUSAL",
                "gross_sales_demo_credits": finance["gross_sales_demo_credits"],
                "variable_cost_demo_credits": finance["variable_cost_demo_credits"],
                "marketing_spend_demo_credits": finance["marketing_spend_demo_credits"],
                "workflow_cost_demo_credits": cost,
                "contribution_after_marketing_and_workflow_costs_demo_credits": contribution,
                "completed_order_records": len(orders),
                "unique_ordering_journeys": unique_buyers,
                "repeat_order_records": repeats,
                "measured_sessions": sessions,
                "qualified_enquiries": scenario["funnel"]["qualified_enquiries"],
                "journey_conversion_basis_points": conversion_bps,
                "causal_incremental_revenue_proven": False,
                "verified_client_revenue": None,
                "verified_net_profit": None,
                "real_conversion_rate_verified": False,
            },
            "automation": {
                "proposals": work_queue,
                "proposals_for_review": sum(a["review_state"] == "REVIEW_REQUIRED"
                                            for a in work_queue),
                "provider_owned_suppressions": sum(a["review_state"] ==
                                                    "SUPPRESSED_PROVIDER_OWNS" for a in work_queue),
                "unconsented_suppressions": sum(a["review_state"] ==
                                                "SUPPRESSED_NO_MARKETING_CONSENT" for a in work_queue),
                "replay_previews": duplicates,
                "durable_replay_protection_enabled": False,
                "messages_sent": 0,
                "social_posts_published": 0,
                "external_actions": 0,
                "paid_orders_created": 0,
            },
            "subscription": {
                "research_tier": scenario["subscription_research_tier"],
                "readiness": "NOT_LAUNCH_READY",
                "required_gates": list(READINESS_GATES),
                "price_offered": None,
                "billing_active": False,
                "entitlements_active": False,
                "trial_active": False,
                "real_subscription_revenue": None,
            },
        })
    out = {
        "schema_version": 1,
        "engineering_milestone": "P2-03j",
        "classification": "SYNTHETIC_DEMO_ONLY",
        "currency": "DEMO_CREDITS",
        "mode": "READ_ONLY_GOAL_ORCHESTRATION",
        "integration_mode": "CONTRACT_ONLY",
        "operational_status": "NO_GO",
        "source_fixture_sha256": sha256(growth_raw).hexdigest(),
        "scenario_sha256": sha256(scenarios_raw).hexdigest(),
        "provider_contract_sha256": sha256(contract_raw).hexdigest(),
        "providers": [
            {"provider_id": p["provider_id"],
             "connection_state": p["connection_state"],
             "external_execution_enabled": False}
            for p in providers["providers"]
        ],
        "workspaces": results,
        "live_customer_data_used": False,
        "live_provider_credentials_used": False,
        "real_customer_subscriptions_charged": False,
        "external_requests_made": False,
        "customer_activation_authorized": False,
        "tenant_isolation_verified": False,
        "durable_idempotency_verified": False,
        "revenue_incrementality_verified": False,
        "live_automation_available": False,
    }
    out["evidence_sha256"] = canonical_hash(out)
    return out


def read_committed_growth_orchestration(*, workspace: str = "all") -> dict:
    """Only committed bounded source files, never a user-chosen live data path."""
    return orchestrate(GROWTH_FIXTURE.read_bytes(), SCENARIOS_PATH.read_bytes(),
                       CONTRACT_PATH.read_bytes(), workspace=workspace)
