"""P3-05 offline developer SDK: typed DEMO tools with no execution transport.

Do not use in production. A returned negative result only describes static,
locally generated test data. This SDK has no HTTP, database, provider access,
network, credentials, shell execution, customer data or grant issuance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from re import fullmatch
from uuid import UUID

from app.phase03_intelligent_ecosystem import (
    CapabilityDenied, DemoCapabilityIntent, OfflineCapabilityPreview,
    OPERATION_SPECS, validate_phase03_manifest,
)
from app.phase03_capability_planning import (
    DemoPlanningRequest, TARGETS, create_denied_plan, inspect_denied_plan,
)
from app.phase03_outcome_verification import (
    make_demo_no_dispatch, make_demo_readback, verify_demo_negative_outcome,
)
from app.phase03_business_analytics import (
    analyze_demo_business, demo_business_fixture, simulate_demo_increment,
)

ROOT = Path(__file__).resolve().parents[3]
DEMO_TENANT = UUID("00000000-0000-4000-8000-000000000003")
ACTOR = "DEMO-ACTOR-DEVELOPER-SDK"
SDK_REQUEST_ID = "DEMO-REQ-SDK-001"
DEMO_TICK = 100
DEMO_EVIDENCE_ID = "DEMO-EVENT-SDK-NO-DISPATCH"
ACTION_FIELDS = (
    ("capability-preview", True, ("operation_id", "request_id")),
    ("denied-plan", True, ("operation_id", "request_id", "resource_version")),
    ("negative-proof", True, ("operation_id", "request_id", "observed_version")),
    ("business-metrics", False, ()),
    ("business-scenario", False, ("extra_orders", "extra_marketing_minor")),
)
SCENARIOS = {
    "business.lead-intake.validate.v1": "DEMO-LEAD-VALIDATION",
    "business.crm.sync-proposal.v1": "DEMO-CRM-PROPOSAL",
    "business.inventory.stock-preview.v1": "DEMO-STOCK-CHECK",
    "business.finance.reconciliation-proposal.v1": "DEMO-RECONCILIATION",
}


class OfflineDeveloperDenied(ValueError):
    """Untrusted input does not describe a supported local DEMO tool."""


def _deny() -> None:
    raise OfflineDeveloperDenied("Developer tool denied: local synthetic use only")


@dataclass(frozen=True)
class OfflineToolInvocation:
    action: str
    operation_id: str = ""
    request_id: str = SDK_REQUEST_ID
    resource_version: int = 1
    observed_version: int = 1
    extra_orders: int = 5
    extra_marketing_minor: int = 10_000


@dataclass(frozen=True)
class OfflineToolResponse:
    action: str
    payload: dict[str, object]
    decision: str = "DENY"
    environment: str = "OFFLINE_DEMO_ONLY"
    executed: bool = False
    external_provider_called: bool = False
    user_authenticated: bool = False
    scope_verified: bool = False
    real_value_measured: bool = False
    release_authorized: bool = False


def source_spec() -> dict[str, object]:
    """Versioned local Python tool contract, NOT OpenAPI or remote MCP tools."""
    return {
        "schema_version": 1, "phase": "03", "milestone": "P3-05",
        "kind": "LOCAL_PYTHON_ONLY", "transport": "NONE",
        "base_url": None, "default_decision": "DENY",
        "external_provider_access_enabled": False,
        "external_write_enabled": False,
        "customer_data_access_enabled": False,
        "model_tool_invocation_enabled": False,
        "production_ready": False,
        "phase02_operational_go": False,
        "operations": sorted(OPERATION_SPECS),
        "actions": [
            {"action": action, "operation_required": required,
             "argument_names": list(fields), "effect": "DENY_ONLY"}
            for action, required, fields in ACTION_FIELDS
        ],
    }


def _same_typed_structure(left: object, right: object) -> bool:
    # JSON comparison alone would regard 0 == False as True.
    if type(left) is not type(right):
        return False
    if type(right) is dict:
        return (
            left.keys() == right.keys()
            and all(_same_typed_structure(left[k], right[k]) for k in right)
        )
    if type(right) is list:
        return len(left) == len(right) and all(
            _same_typed_structure(a, b) for a, b in zip(left, right)
        )
    return left == right


def validate_source_spec(candidate: object) -> None:
    if not _same_typed_structure(candidate, source_spec()):
        raise OfflineDeveloperDenied("Developer source contract mismatch or unsafe change")


def _check(request: OfflineToolInvocation) -> None:
    if type(request) is not OfflineToolInvocation:
        _deny()
    if (type(request.action) is not str
            or request.action not in {a for a, _, _ in ACTION_FIELDS}
            or type(request.request_id) is not str
            or fullmatch(r"DEMO-REQ-[A-Z0-9-]{3,48}", request.request_id) is None
            or type(request.resource_version) is not int
            or not 1 <= request.resource_version <= 1000
            or type(request.observed_version) is not int
            or not 0 <= request.observed_version <= 1000
            or type(request.extra_orders) is not int
            or not 0 <= request.extra_orders <= 100
            or type(request.extra_marketing_minor) is not int
            or not 0 <= request.extra_marketing_minor <= 100_000_000):
        _deny()
    operations = {"capability-preview", "denied-plan", "negative-proof"}
    if request.action in operations:
        if type(request.operation_id) is not str or request.operation_id not in OPERATION_SPECS:
            _deny()
        if request.extra_orders != 5 or request.extra_marketing_minor != 10_000:
            _deny()
        if request.action != "denied-plan" and request.resource_version != 1:
            _deny()
        if request.action != "negative-proof" and request.observed_version != 1:
            _deny()
    else:
        if (request.operation_id != ""
                or request.request_id != SDK_REQUEST_ID
                or request.resource_version != 1 or request.observed_version != 1):
            _deny()
        if request.action == "business-metrics" and (
            request.extra_orders != 5 or request.extra_marketing_minor != 10_000
        ):
            _deny()


def _base_intent(req: OfflineToolInvocation) -> DemoCapabilityIntent:
    return DemoCapabilityIntent(
        tenant_id=DEMO_TENANT, actor_label=ACTOR,
        request_id=req.request_id, operation_id=req.operation_id,
        scenario=SCENARIOS[req.operation_id], logical_tick=DEMO_TICK,
    )


def _planning_request(
    intent: DemoCapabilityIntent, receipt: object, *,
    resource_version: int,
) -> DemoPlanningRequest:
    return DemoPlanningRequest(
        intent=intent, denial_receipt=receipt,
        target_label=TARGETS[intent.operation_id],
        expected_resource_version=resource_version,
        requested_tick=DEMO_TICK,
    )


def run_offline_tool(request: OfflineToolInvocation) -> OfflineToolResponse:
    """Local only. Dispatch is to pure DEMO functions; never to business APIs."""
    _check(request)
    if request.action in {"capability-preview", "denied-plan", "negative-proof"}:
        intent = _base_intent(request)
        denied = OfflineCapabilityPreview().inspect_once(intent)
        if request.action == "capability-preview":
            data = asdict(denied)
        else:
            planner = _planning_request(
                intent, denied, resource_version=request.resource_version,
            )
            plan = create_denied_plan(planner)
            if request.action == "denied-plan":
                data = asdict(plan)
                result = inspect_denied_plan(plan, planner, observed_tick=101)
                data["synthetic_integrity_consistent"] = (
                    result.synthetic_integrity_consistent
                )
            else:
                event = make_demo_no_dispatch(
                    plan, planner, event_id=DEMO_EVIDENCE_ID, observed_tick=101,
                )
                snapshot = make_demo_readback(
                    plan, planner, observed_tick=101,
                    observed_version=request.observed_version,
                )
                data = asdict(verify_demo_negative_outcome(
                    plan, planner, event, snapshot, observed_tick=102,
                ))
    elif request.action == "business-metrics":
        data = asdict(analyze_demo_business(
            DEMO_TENANT, demo_business_fixture(DEMO_TENANT),
        ))
    else:
        data = asdict(simulate_demo_increment(
            DEMO_TENANT, demo_business_fixture(DEMO_TENANT)[-1],
            extra_paid_orders=request.extra_orders,
            extra_marketing_cost_minor=request.extra_marketing_minor,
        ))
    data.pop("tenant_id", None)
    if data.get("decision") != "DENY":
        _deny()
    # Return a structured negative report, never an authorization object.
    return OfflineToolResponse(action=request.action, payload=data)


def offline_developer_doctor(root: Path = ROOT) -> dict[str, object]:
    """Source-only preflight, intentionally not an operations readiness test."""
    if type(root) is not Path:
        _deny()
    paths = {
        "developer": "contracts/intelligent/v1/developer_tools.json",
        "capabilities": "contracts/intelligent/v1/capabilities.json",
        "domain": "contracts/domains/v1/operations.json",
        "planning": "contracts/intelligent/v1/planning.json",
        "outcome": "contracts/intelligent/v1/outcome_verification.json",
        "analytics": "contracts/intelligent/v1/business_analytics.json",
    }
    try:
        inputs = {
            k: json.loads((root / p).read_text(encoding="utf-8"))
            for k, p in paths.items()
        }
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise OfflineDeveloperDenied("Required local source contract missing/invalid") from exc
    validate_source_spec(inputs["developer"])
    validate_phase03_manifest(inputs["capabilities"], inputs["domain"])
    restrictions = (
        (inputs["planning"], "trusted_execution_authorization_available"),
        (inputs["planning"], "external_reads_performed"),
        (inputs["planning"], "external_writes_performed"),
        (inputs["outcome"], "external_receipt_trust_available"),
        (inputs["outcome"], "live_provider_readback_enabled"),
        (inputs["analytics"], "real_revenue_measured"),
        (inputs["analytics"], "customer_data_used"),
        (inputs["analytics"], "live_execution_authorized"),
    )
    if (any(type(m) is not dict or m.get(field) is not False
            for m, field in restrictions)
            or inputs["planning"].get("default_decision") != "DENY"
            or inputs["outcome"].get("release_decision") != "NO_GO"
            or inputs["analytics"].get("decision") != "DENY"):
        raise OfflineDeveloperDenied("Phase 03 predecessor trust gate unexpectedly enabled")
    return {
        "status": "SOURCE_CONTRACTS_VALIDATED_NOT_RELEASE_APPROVED",
        "source_contracts_checked": len(paths),
        "action_count": len(ACTION_FIELDS),
        "operation_count": len(OPERATION_SPECS),
        "decision": "DENY",
        "real_environment_checked": False,
        "source_compatible": True,
        "execution_available": False,
        "customer_access_available": False,
        "release_authorized": False,
    }
