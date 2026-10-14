"""Phase 02 contract/admission tests. No cloud, customers, model or DB writes."""
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.authn import Principal, TenantSession, get_tenant_session
from app.domain_integrations import (
    DOMAIN_OPERATIONS, INDEX, policy_preview, router
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts/domains/v1/operations.json"


def client_for_role(role: str):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_tenant_session] = lambda: TenantSession(
        conn=None,
        principal=Principal(organization_id=uuid4(), user_id=uuid4(), role=role),
    )
    return TestClient(app)


def test_manifest_matches_real_endpoint_contract_and_remains_draft():
    manifest = json.loads(CONTRACTS.read_text())
    assert manifest["product"] == "metaautomate"
    assert manifest["default_policy"] == "DENY"
    assert manifest["lifecycle"] == "draft"
    assert manifest["adapter_state"] == "unbound"
    assert manifest["external_access"] is False
    assert manifest["contract_version"] == "1.0.0"
    assert manifest["operations"] == list(DOMAIN_OPERATIONS)
    assert len(INDEX) == 4
    assert {v["capability_id"] for v in DOMAIN_OPERATIONS} == {
        "BIZ-002", "BIZ-006", "BIZ-011", "BIZ-012"
    }
    assert {v["risk"] for v in DOMAIN_OPERATIONS} == {"low", "moderate", "high"}


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "OPERATOR", "VIEWER"])
def test_authenticated_members_can_inspect_draft_catalog(role):
    with client_for_role(role) as client:
        response = client.get("/v1/domain-integrations/contracts")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == "metaautomate"
    assert body["execution_available"] is False
    assert len(body["operations"]) == 4
    assert all(item["connector_state"] == "unbound"
               and item["lifecycle"] == "draft"
               and item["execution_available"] is False
               for item in body["operations"])


@pytest.mark.parametrize("role", ["OWNER", "ADMIN", "OPERATOR"])
@pytest.mark.parametrize("operation_id", list(INDEX))
def test_every_draft_operation_is_denied_without_external_effects(role, operation_id):
    with client_for_role(role) as client:
        response = client.post("/v1/domain-integrations/preview", json={
            "operation_id": operation_id, "correlation_id": str(uuid4())
        })
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "DENY"
    assert body["executed"] is False
    assert body["connector_called"] is False
    assert body["data_accessed"] is False
    assert "capability_not_active" in body["reasons"]
    assert "connector_not_bound" in body["reasons"]
    assert "product_scope_not_issued" in body["reasons"]
    assert "staging_identity_not_verified" in body["reasons"]
    if INDEX[operation_id]["approval_required"]:
        assert "specific_action_approval_not_verified" in body["reasons"]


def test_viewer_may_read_but_cannot_request_admission_preview():
    with client_for_role("VIEWER") as client:
        response = client.post("/v1/domain-integrations/preview", json={
            "operation_id": "business.lead-intake.validate.v1"
        })
    assert response.status_code == 403


def test_unauthenticated_clients_never_see_contracts_or_preview():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        for path, method in [
            ("/v1/domain-integrations/contracts", "get"),
            ("/v1/domain-integrations/preview", "post"),
        ]:
            response = getattr(client, method)(
                path, headers={"Authorization": "Bearer invalid-token"},
                **({"json": {"operation_id": "business.lead-intake.validate.v1"}}
                   if method == "post" else {}),
            )
            assert response.status_code == 401


@pytest.mark.parametrize("bad_field", [
    "organization_id", "tenant_id", "product", "user_id", "actor_id",
    "scope", "scopes", "role", "approval_reference", "connector_url",
    "connector_token", "api_key", "payload"
])
def test_client_cannot_supply_authority_approval_or_data(bad_field):
    with client_for_role("OWNER") as client:
        response = client.post("/v1/domain-integrations/preview", json={
            "operation_id": "business.crm.sync-proposal.v1",
            bad_field: "forged-client-claim",
        })
    assert response.status_code == 422


def test_unknown_operation_never_falls_through_to_connector():
    with client_for_role("ADMIN") as client:
        response = client.post("/v1/domain-integrations/preview", json={
            "operation_id": "business.unknown.execute.v1"
        })
    assert response.status_code == 404


def test_direct_policy_is_deny_only_and_role_protected():
    for operation_id in INDEX:
        assert policy_preview(operation_id, role="OWNER")["decision"] == "DENY"
    with pytest.raises(Exception) as exc:
        policy_preview("business.lead-intake.validate.v1", role="VIEWER")
    assert getattr(exc.value, "status_code", None) == 403
