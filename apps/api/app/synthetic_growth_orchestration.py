"""P2-03j: goal-oriented, non-operational customer-growth orchestration.

Consumes only strictly validated P2-03h synthetic fixtures. Neither dispatches
work nor authenticates tenants; all operations are pure, in-memory and review
required. Never interpret example opt-in as verified real-world consent.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from .synthetic_growth_autopilot import (
    SyntheticGrowthError, _require, parse_growth_fixture, FIXTURE,
)

GOALS = frozenset({"CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"})
SUPPORTED_INTEGRATION_KINDS = frozenset({"COMMERCE", "PUBLISHING", "CUSTOMER_MESSAGING"})
PROVIDERS = {
    "SELAR": ("COMMERCE", ("ORDER_COMPLETED", "CHECKOUT_RECOVERY_MANAGED")),
    "METRICOOL": ("PUBLISHING", ("POST_REVIEW_QUEUE",)),
    "MAILERLITE": ("CUSTOMER_MESSAGING", ("CONSENTED_FOLLOWUP_REVIEW",)),
}
GOAL_EVENTS = {
    "CONTRIBUTION": frozenset({
        "LEAD_OPT_IN", "PURCHASE_COMPLETED", "LEARNING_COMPLETED", "GARMENT_DELIVERED",
    }),
    "RETENTION": frozenset({"PURCHASE_COMPLETED", "LEARNING_COMPLETED", "GARMENT_DELIVERED"}),
    "COMPLETED_ORDERS": frozenset({"LEAD_OPT_IN", "PURCHASE_COMPLETED"}),
}
MAX_REPORT_BYTES = 524288

# Source-only commercial plans. Do not turn these into prices or entitlements.
PLAN_ARCHETYPES = {
    "STARTER_RESEARCH": {"value_hypothesis": "time_saved_and_followup_clarity"},
    "GROWTH_RESEARCH": {"value_hypothesis": "repeat_business_and_contribution_insight"},
    "TEAM_RESEARCH": {"value_hypothesis": "multi_role_governance_and_workflow_audit"},
}
NON_OPERATIONAL = {
    "source_review_only": True,
    "operational_status": "NO_GO",
    "foundation_verified": "3/9",
    "real_customer_data": False,
    "consent_verified_for_real_people": False,
    "credentials_read": False,
    "outbound_messages": 0,
    "provider_calls": 0,
    "social_posts_published": 0,
    "customer_orders_mutated": 0,
    "payments_or_subscriptions_charged": 0,
    "database_writes": 0,
    "customer_execution_enabled": False,
}


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("ascii")).hexdigest()


def _provider_contracts() -> list[dict[str, Any]]:
    """Contracts describe future consented permissions, not active connections."""
    return [
        {
            "provider": provider,
            "kind": kind,
            "proposed_scopes": list(scopes),
            "connection_status": "DISABLED_REQUIRE_AUTHORIZATION",
            "credential_value": None,
            "webhook_receiver_active": False,
            "api_endpoint_active": False,
            "can_send_or_publish": False,
            "requires_separate_tenant_authentication": True,
            "requires_verifiable_consent_and_unsubscribe": kind == "CUSTOMER_MESSAGING",
            "checkout_reminders": "PROVIDER_OWNED" if provider == "SELAR" else "NOT_APPLICABLE",
        }
        for provider, (kind, scopes) in sorted(PROVIDERS.items())
    ]


def _economic_summary(workspace: dict) -> dict[str, Any]:
    products = {p["product_id"]: p for p in workspace["products"]}
    gross = sum(products[o["product_id"]]["unit_price_demo_credits"] * o["units"]
                for o in workspace["orders"])
    direct = sum(products[o["product_id"]]["variable_cost_demo_credits"] * o["units"]
                 for o in workspace["orders"])
    marketing = workspace["marketing_spend_demo_credits"]
    modeled = gross - direct - marketing
    target = workspace["goal_target_demo_credits"]
    journey_counts: dict[str, int] = {}
    for order in workspace["orders"]:
        journey_counts[order["journey_id"]] = journey_counts.get(order["journey_id"], 0) + 1
    return {
        "currency": "DEMO_CREDITS",
        "gross_sales": gross,
        "variable_cost": direct,
        "marketing_spend": marketing,
        "modeled_contribution_after_marketing": modeled,
        "monthly_contribution_target": target,
        "contribution_shortfall": max(0, target - modeled),
        "completed_orders": len(workspace["orders"]),
        "repeat_orders": sum(max(0, x - 1) for x in journey_counts.values()),
        "net_profit_verified": False,
        "incremental_revenue_proven": False,
        "true_conversion_rate_computable": False,  # no measured visitor denominator
        "customer_lifetime_value_verified": False,
    }


def build_growth_work_plan(raw: bytes, *, goal: str = "CONTRIBUTION",
                           workspace: str = "all") -> dict[str, Any]:
    """Create review plans from invented, allowlisted inputs only."""
    doc = parse_growth_fixture(raw)  # validates ALL workspaces before filtering
    _require(type(goal) is str and goal in GOALS, "Unknown/unauthorized business goal")
    from .synthetic_growth_autopilot import WORKSPACES
    _require(type(workspace) is str and workspace in (set(WORKSPACES) | {"all"}),
             "Unknown workspace")
    results = []
    for group in doc["workspaces"]:
        if workspace != "all" and group["workspace"] != workspace:
            continue
        proposals = []
        for event in group["events"]:
            event_kind = event["event_type"]
            consent = event["consent_status"] == "SYNTHETIC_OPTED_IN"
            if event_kind == "CHECKOUT_ABANDONED":
                state = "SUPPRESSED_PROVIDER_OWNS"
                decision = "Use provider-owned native reminder; MetaAutomate must not duplicate"
            elif not consent:
                state = "SUPPRESSED_CONSENT_UNVERIFIED"
                decision = "No contact until actual tenant consent is verifiable"
            elif event_kind not in GOAL_EVENTS[goal]:
                state = "DEFERRED_NOT_GOAL_RELEVANT"
                decision = "Event is valid but not selected for this business goal"
            else:
                state = "PROPOSED_HUMAN_REVIEW_ONLY"
                decision = "Requires separate human approval and live authorization before execution"
            plan_id = _digest({"workspace": group["workspace"], "event": event["event_id"],
                               "goal": goal, "state": state})[:24]
            proposals.append({
                "plan_id": plan_id,
                "source_event": event["event_id"],
                "event_kind": event_kind,
                "goal": goal,
                "state": state,
                "review_reason": decision,
                "actual_customer_consent_verified": False,
                "approval_recorded": False,
                "execution_allowed": False,
                "provider_request_sent": False,
                "contact_address": None,
                "destination_account": None,
            })
        # Pure deterministic ordering. No timestamp, contact, task queue or mutation.
        assert len(set(p["plan_id"] for p in proposals)) == len(proposals)
        counts: dict[str, int] = {}
        for p in proposals:
            counts[p["state"]] = counts.get(p["state"], 0) + 1
        results.append({
            "workspace": group["workspace"],
            "goal": goal,
            "financial_summary": _economic_summary(group),
            "workflow_proposals": proposals,
            "workflow_counts": counts,
            "ready_to_execute": 0,
            "externally_delivered": 0,
            "causal_attribution": "UNPROVEN",
            "operational_status": "NO_GO",
        })
    report: dict[str, Any] = {
        "schema_version": 1,
        "classification": "SYNTHETIC_SOURCE_REVIEW",
        "module": "P2-03j_BUSINESS_GROWTH_AUTOMATION",
        "goal": goal,
        "workspaces": results,
        "integration_contracts": _provider_contracts(),
        "subscription_research": {
            "plans": [
                {"plan": key, **value, "billing_live": False, "price_committed": False,
                 "entitlement_active": False, "monetization_claim_validated": False}
                for key, value in PLAN_ARCHETYPES.items()
            ],
            "required_business_evidence": [
                "verified_minutes_saved",
                "approved_and_delivered_actions",
                "controlled_incremental_contribution_after_all_costs",
                "consent_opt_out_compliance",
                "customer_willingness_to_pay",
                "support_cost_and_retention",
            ],
            "checkout_enabled": False,
            "billing_provider_enabled": False,
        },
        "non_operational_controls": dict(NON_OPERATIONAL),
        "fixture_sha256": sha256(raw).hexdigest(),
    }
    report["evidence_sha256"] = _digest(report)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    _require(len(encoded) <= MAX_REPORT_BYTES, "Source report exceeds bound")
    return report


def build_committed_growth_work_plan(*, goal: str = "CONTRIBUTION",
                                     workspace: str = "all") -> dict[str, Any]:
    return build_growth_work_plan(FIXTURE.read_bytes(), goal=goal, workspace=workspace)
