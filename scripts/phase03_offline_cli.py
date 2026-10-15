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

from app.phase03_capability_planning import (  # noqa: E402
    DemoPlanningRequest, TARGETS, create_denied_plan, inspect_denied_plan,
    OfflinePlanDenied,
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
    args = parser.parse_args(argv)
    try:
        operations = _manifest()
        if args.action == "catalog":
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
    except (ContractRejected, CapabilityDenied, OfflinePlanDenied, DemoEvidenceRejected, ValueError) as exc:
        print(f"PHASE03_RESULT=DENY: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
