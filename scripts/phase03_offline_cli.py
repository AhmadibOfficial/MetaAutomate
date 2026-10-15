#!/usr/bin/env python3
"""P3-01 developer CLI: local contract discovery, denied previews and DEMO analytics.

No network, real credentials, customer payloads, production authorization,
app HTTP routes, environment secrets, writes or execution capabilities.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.phase03_integration_safety import (  # noqa: E402
    OfflineIntegratedInput, OfflineIntegrationDenied,
    run_offline_integration, audit_offline_contracts,
)
from app.phase03_capability_planning import (  # noqa: E402
    DemoPlanningRequest, TARGETS, create_denied_plan, inspect_denied_plan,
    OfflinePlanDenied,
)
from app.phase03_execution_rehearsal import (  # noqa: E402
    DemoExecutionAttempt, DemoExecutionAudit, ExecutionAttemptDenied,
)
from app.phase03_developer_tools import (  # noqa: E402
    OfflineDeveloperDenied, OfflineToolInvocation, run_offline_tool,
    source_spec, offline_developer_doctor,
)
from app.phase03_business_analytics import (  # noqa: E402
    DemoAnalyticsDenied, demo_business_fixture, analyze_demo_business,
    simulate_demo_increment,
)
from app.phase03_outcome_verification import (  # noqa: E402
    DemoEvidenceRejected, make_demo_no_dispatch, make_demo_readback,
    verify_demo_negative_outcome,
)
from app.phase03_intelligent_ecosystem import (  # noqa: E402
    CapabilityDenied, ContractRejected, DemoCapabilityIntent,
    OfflineCapabilityPreview, aggregate_synthetic_denials,
    validate_phase03_manifest,
)

CONTRACT = ROOT / "contracts/intelligent/v1/capabilities.json"
DOMAIN = ROOT / "contracts/domains/v1/operations.json"
DEMO_TENANT = UUID("00000000-0000-4000-8000-000000000003")
SCENARIO_OPERATIONS = (
    "business.lead-intake.validate.v1",
    "business.crm.sync-proposal.v1",
    "business.inventory.stock-preview.v1",
    "business.finance.reconciliation-proposal.v1",
)


def _manifest() -> tuple[dict[str, object], ...]:
    try:
        current = json.loads(CONTRACT.read_text(encoding="utf-8"))
        original = json.loads(DOMAIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractRejected("Cannot load offline contracts") from exc
    return validate_phase03_manifest(current, original)


def _intent(operation: str, request_id: str) -> DemoCapabilityIntent:
    scenario_by_op = {
        "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
        "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
        "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
        "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
    }
    if operation not in scenario_by_op:
        raise CapabilityDenied("Unknown offline operation")
    return DemoCapabilityIntent(
        tenant_id=DEMO_TENANT,
        actor_label="DEMO-ACTOR-DEVELOPER",
        request_id=request_id,
        operation_id=operation,
        scenario=scenario_by_op[operation],
        logical_tick=100,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("catalog", help="Show draft capabilities only")
    preview = sub.add_parser("preview", help="Generate a denied offline preview")
    preview.add_argument("operation_id", help="Exact draft operation ID")
    preview.add_argument(
        "--request-id", default="DEMO-REQ-CLI-001",
        help="Invented DEMO-REQ-* only",
    )
    sub.add_parser("demo-analytics", help="Aggregate invented denied previews")
    plan = sub.add_parser("plan", help="Return denied source-only capability plan")
    plan.add_argument("operation_id", help="Existing draft operation only")
    plan.add_argument("--resource-version", type=int, default=1)
    plan.add_argument("--request-id", default="DEMO-REQ-CLI-PLAN-001")
    verify = sub.add_parser("verify-denial", help="Locally compare invented no-dispatch and unchanged-version DEMO fixtures; no provider access")
    verify.add_argument("operation_id", help="Existing draft operation only")
    verify.add_argument("--request-id", default="DEMO-REQ-CLI-VERIFY-001")
    verify.add_argument("--simulated-observed-version", type=int, default=1)
    sub.add_parser(
        "business-demo", help="Aggregate invented DEMO lead, order, cost and stock metrics"
    )
    scenario = sub.add_parser(
        "scenario-demo", help="Best-case fictional order/cost arithmetic, never forecast"
    )
    scenario.add_argument("--extra-orders", type=int, default=5)
    scenario.add_argument("--extra-marketing-minor", type=int, default=10_000)
    sub.add_parser("dev-spec", help="Print the local-only versioned tool spec; no endpoint")
    sub.add_parser("dev-doctor", help="Check pinned Phase 03 source contracts, not deployment")
    sdk = sub.add_parser("sdk-demo", help="Invoke one typed offline-only SDK tool")
    sdk.add_argument("tool", choices=[
        "capability-preview", "denied-plan", "negative-proof",
        "business-metrics", "business-scenario",
    ])
    sdk.add_argument("--operation-id", default="")
    sdk.add_argument("--request-id", default="DEMO-REQ-SDK-001")
    sdk.add_argument("--resource-version", type=int, default=1)
    sdk.add_argument("--observed-version", type=int, default=1)
    sdk.add_argument("--extra-orders", type=int, default=5)
    sdk.add_argument("--extra-marketing-minor", type=int, default=10_000)
    ex = sub.add_parser(
        "execution-rehearsal", help="Locally REJECT an invented capability; no effects"
    )
    ex.add_argument("operation_id", help="Exact existing draft operation")
    ex.add_argument("--request-id", default="DEMO-REQ-CLI-REHEARSAL-001")
    ex.add_argument("--observed-version", type=int, default=1)
    ex.add_argument("--reviewer-count", type=int, choices=[0, 1, 2], default=0)
    ex.add_argument("--observed-tick", type=int, default=101)
    sub.add_parser(
        "ecosystem-check",
        help="Audit eight local source contracts and run all four DENY-only DEMO capabilities",
    )
    integrated = sub.add_parser(
        "integration-demo", help="One cross-module synthetic DENY rehearsal"
    )
    integrated.add_argument("operation_id")
    integrated.add_argument("--observed-version", type=int, default=1)
    integrated.add_argument("--observed-tick", type=int, default=101)
    integrated.add_argument("--reviewer-count", type=int, choices=[0,1,2], default=0)
    integrated.add_argument("--demo-analytics", action="store_true")
    args = parser.parse_args(argv)
    try:
        operations = _manifest()
        if args.action == "ecosystem-check":
            validation = audit_offline_contracts(ROOT)
            reports = [
                run_offline_integration(OfflineIntegratedInput(
                    tenant_id=DEMO_TENANT,
                    operation_id=operation,
                    request_id=f"DEMO-REQ-P307-CHECK-{i:03}",
                    attempt_id=f"DEMO-ATTEMPT-P307-CHECK-{i:03}",
                ))
                for i, operation in enumerate(sorted(SCENARIO_OPERATIONS), start=1)
            ]
            if not all(
                x.decision == "DENY" and x.denial_receipt_consistent
                and x.denied_plan_consistent and x.audited_denial_consistent
                and not x.business_effect_performed and not x.release_authorized
                for x in reports
            ):
                raise OfflineIntegrationDenied("Source DENY contract mismatch")
            result = {
                "contract_audit": asdict(validation),
                "synthetic_operations_checked": len(reports),
                "synthetic_denials": len(reports),
                "external_operations_performed": 0,
                "decision": "DENY",
                "release_authorized": False,
            }
        elif args.action == "integration-demo":
            reviewer_labels = (
                "DEMO-REVIEWER-ALPHA", "DEMO-REVIEWER-BETA",
            )[:args.reviewer_count]
            report = run_offline_integration(OfflineIntegratedInput(
                tenant_id=DEMO_TENANT,
                operation_id=args.operation_id,
                observed_resource_version=args.observed_version,
                observed_tick=args.observed_tick,
                reviewer_labels=reviewer_labels,
                attach_synthetic_analytics=args.demo_analytics,
            ))
            result = asdict(report)
        elif args.action == "catalog":
            result = {
                "mode": "OFFLINE_DESIGN_ONLY",
                "decision": "DENY",
                "operation_count": len(operations),
                "operations": operations,
                "execution_available": False,
            }
        elif args.action == "preview":
            intent = _intent(args.operation_id, args.request_id)
            receipt = OfflineCapabilityPreview().inspect_once(intent)
            result = asdict(receipt)
            result.pop("tenant_id")
            result["receipt_scope"] = "UNTRUSTED_DEMO_CHECKSUM_ONLY"
        elif args.action == "plan":
            intent = _intent(args.operation_id, args.request_id)
            denied = OfflineCapabilityPreview().inspect_once(intent)
            request = DemoPlanningRequest(
                intent=intent,
                denial_receipt=denied,
                target_label=TARGETS[intent.operation_id],
                expected_resource_version=args.resource_version,
                requested_tick=intent.logical_tick,
            )
            plan = create_denied_plan(request)
            verdict = inspect_denied_plan(plan, request, observed_tick=101)
            result = asdict(plan)
            result.pop("tenant_id")
            result["synthetic_integrity_consistent"] = verdict.synthetic_integrity_consistent
            result["execution_authorized"] = False
        elif args.action == "verify-denial":
            intent = _intent(args.operation_id, args.request_id)
            denied = OfflineCapabilityPreview().inspect_once(intent)
            request = DemoPlanningRequest(
                intent=intent, denial_receipt=denied,
                target_label=TARGETS[intent.operation_id],
                expected_resource_version=1,
                requested_tick=intent.logical_tick,
            )
            plan = create_denied_plan(request)
            event = make_demo_no_dispatch(
                plan, request, event_id="DEMO-EVENT-CLI-NO-DISPATCH",
                observed_tick=101,
            )
            readback = make_demo_readback(
                plan, request, observed_tick=101,
                observed_version=args.simulated_observed_version,
            )
            report = verify_demo_negative_outcome(
                plan, request, event, readback, observed_tick=102,
            )
            result = asdict(report)
            result.pop("tenant_id")
            result["evidence_scope"] = "INVENTED_UNTRUSTED_FIXTURES_ONLY"
        elif args.action == "execution-rehearsal":
            intent = _intent(args.operation_id, args.request_id)
            denied = OfflineCapabilityPreview().inspect_once(intent)
            request = DemoPlanningRequest(
                intent=intent, denial_receipt=denied,
                target_label=TARGETS[intent.operation_id],
                expected_resource_version=1, requested_tick=intent.logical_tick,
            )
            plan = create_denied_plan(request)
            labels = ("DEMO-REVIEWER-ONE", "DEMO-REVIEWER-TWO")[:args.reviewer_count]
            attempt = DemoExecutionAttempt(
                plan=plan, source_request=request,
                attempt_id="DEMO-ATTEMPT-CLI-HALT-001",
                observed_tick=args.observed_tick,
                expected_resource_version=args.observed_version,
                reviewer_labels=labels,
            )
            decision, audit = DemoExecutionAudit().reject_once(attempt)
            result = {
                "rejection": asdict(decision),
                "demo_audit": asdict(audit),
                "evidence_scope": "UNAUTHENTICATED_VOLATILE_DEMO_ONLY",
            }
            result["rejection"].pop("tenant_id")
            result["demo_audit"].pop("tenant_id")
        elif args.action == "dev-spec":
            offline_developer_doctor(ROOT)
            result = source_spec()
        elif args.action == "dev-doctor":
            result = offline_developer_doctor(ROOT)
        elif args.action == "sdk-demo":
            tool_request = OfflineToolInvocation(
                action=args.tool,
                operation_id=args.operation_id,
                request_id=args.request_id,
                resource_version=args.resource_version,
                observed_version=args.observed_version,
                extra_orders=args.extra_orders,
                extra_marketing_minor=args.extra_marketing_minor,
            )
            result = asdict(run_offline_tool(tool_request))
        elif args.action == "business-demo":
            samples = demo_business_fixture(DEMO_TENANT)
            report = analyze_demo_business(DEMO_TENANT, samples)
            result = asdict(report)
        elif args.action == "scenario-demo":
            sample = demo_business_fixture(DEMO_TENANT)[-1]
            report = simulate_demo_increment(
                DEMO_TENANT, sample, extra_paid_orders=args.extra_orders,
                extra_marketing_cost_minor=args.extra_marketing_minor,
            )
            result = asdict(report)
        else:
            gate = OfflineCapabilityPreview()
            intent_a = _intent(
                "business.inventory.stock-preview.v1", "DEMO-REQ-CLI-001",
            )
            intent_b = _intent(
                "business.finance.reconciliation-proposal.v1", "DEMO-REQ-CLI-002",
            )
            report = aggregate_synthetic_denials(
                DEMO_TENANT,
                ((intent_a, gate.inspect_once(intent_a)),
                 (intent_b, gate.inspect_once(intent_b))),
            )
            result = asdict(report)
    except (ContractRejected, CapabilityDenied, OfflinePlanDenied, DemoEvidenceRejected, DemoAnalyticsDenied, OfflineDeveloperDenied, ExecutionAttemptDenied, OfflineIntegrationDenied, ValueError) as exc:
        print(f"PHASE03_RESULT=DENY: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
