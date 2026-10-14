"""Phase 02: authenticated domain integration discovery and fail-closed admission.

Source-only contracts. Every capability is a DRAFT and every connector is
UNBOUND. Evaluating an admission policy NEVER invokes a connector, reads business
records, queues a job, updates capability states, or grants execution rights.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.authn import TenantSession, get_tenant_session, require_role

router = APIRouter(prefix="/v1/domain-integrations", tags=["phase02-domain-integrations"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]

# A reviewed source manifest, intentionally immutable at runtime. These IDs
# correspond to legacy globally DRAFT capability definitions, not tenant grants.
CONTRACT_VERSION = "1.0.0"
DOMAIN_OPERATIONS = (
    {
        "operation_id": "business.lead-intake.validate.v1",
        "capability_id": "BIZ-002",
        "domain": "business",
        "effect": "validate_only",
        "required_scope": "business.leads.preview",
        "risk": "low",
        "approval_required": False,
    },
    {
        "operation_id": "business.crm.sync-proposal.v1",
        "capability_id": "BIZ-006",
        "domain": "business",
        "effect": "propose_write",
        "required_scope": "business.crm.write",
        "risk": "moderate",
        "approval_required": True,
    },
    {
        "operation_id": "business.inventory.stock-preview.v1",
        "capability_id": "BIZ-011",
        "domain": "business",
        "effect": "read_external",
        "required_scope": "business.inventory.read",
        "risk": "moderate",
        "approval_required": False,
    },
    {
        "operation_id": "business.finance.reconciliation-proposal.v1",
        "capability_id": "BIZ-012",
        "domain": "business",
        "effect": "propose_write",
        "required_scope": "business.finance.write",
        "risk": "high",
        "approval_required": True,
    },
)

INDEX = {operation["operation_id"]: operation for operation in DOMAIN_OPERATIONS}
assert len(INDEX) == len(DOMAIN_OPERATIONS), "Duplicate domain operation ID"


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str = Field(
        min_length=5,
        max_length=100,
        pattern=r"^[a-z][a-z0-9.-]+\.v[1-9][0-9]*$",
    )
    correlation_id: UUID | None = None


def policy_preview(operation_id: str, *, role: str) -> dict:
    """Pure, deterministic policy simulation; not a grant or execution plan."""
    operation = INDEX.get(operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="Unknown domain operation")
    if role not in {"OWNER", "ADMIN", "OPERATOR"}:
        raise HTTPException(status_code=403, detail="Insufficient domain preview permissions")

    # There is no enabled adapter, verified provider identity or per-product
    # scope issuance in the current platform. Never trust any client claims of
    # approval, scopes, tenant, product or connector readiness.
    deny = [
        "capability_not_active",
        "connector_not_bound",
        "product_scope_not_issued",
        "staging_identity_not_verified",
    ]
    if operation["approval_required"]:
        deny.append("specific_action_approval_not_verified")
    return {
        "contract_version": CONTRACT_VERSION,
        "operation_id": operation_id,
        "capability_id": operation["capability_id"],
        "effect": operation["effect"],
        "required_scope": operation["required_scope"],
        "approval_required": operation["approval_required"],
        "decision": "DENY",
        "reasons": deny,
        "executed": False,
        "data_accessed": False,
        "connector_called": False,
    }


@router.get("/contracts")
def list_domain_contracts(session: Session):
    # Existing authn establishes organization/user identity. VIEWER may browse
    # these public-to-tenant design declarations, but never authorize previews.
    if session.principal.role not in {"OWNER", "ADMIN", "OPERATOR", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Unrecognized organization role")
    return {
        "contract_version": CONTRACT_VERSION,
        "product": "metaautomate",
        "lifecycle": "draft",
        "execution_available": False,
        "operations": [
            {**contract, "lifecycle": "draft", "connector_state": "unbound",
             "execution_available": False}
            for contract in DOMAIN_OPERATIONS
        ],
    }


@router.post("/preview")
def preview_domain_operation(payload: PreviewRequest, session: Session):
    # No organization, actor, roles, scopes or approval fields are accepted.
    # Server-side principal always controls this authorization decision.
    require_role(session, {"OWNER", "ADMIN", "OPERATOR"})
    decision = policy_preview(payload.operation_id, role=session.principal.role)
    return {**decision,
            "correlation_id": str(payload.correlation_id) if payload.correlation_id else None}
