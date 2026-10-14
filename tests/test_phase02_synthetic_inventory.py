"""P2-03: subscription-free, local synthetic inventory proof with strict no-live-data boundary."""
import json
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.authn import Principal, TenantSession, get_tenant_session
from app.synthetic_inventory import (
    FIXTURE_PATH, render_synthetic_inventory, router,
)

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "/v1/domain-integrations/sandbox/inventory"


def local_app(*, org=None, role="OWNER", client_host="127.0.0.1"):
    app = FastAPI()
    app.include_router(router)
    org_id = org if org is not None else uuid4()
    app.dependency_overrides[get_tenant_session] = lambda: TenantSession(
        conn=None,
        principal=Principal(organization_id=org_id, user_id=uuid4(), role=role),
    )
    return TestClient(app, client=(client_host, 50400))


@pytest.fixture(autouse=True)
def safe_env(monkeypatch):
    monkeypatch.setenv("DOMAIN_SANDBOX_MODE", "local_synthetic")
    monkeypatch.setenv("WORKSPACE_AUTH_MODE", "dev_key")
    monkeypatch.setenv("WORKSPACE_ORIGIN", "http://127.0.0.1:8000")


def test_local_synthetic_inventory_is_deterministic_and_has_no_external_effects():
    org = uuid4()
    with local_app(org=org) as client:
        first = client.get(ENDPOINT)
        second = client.get(ENDPOINT)
    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    doc = first.json()
    assert doc["mode"] == "LOCAL_SYNTHETIC_SIMULATION"
    assert doc["capability_state"] == "draft"
    assert doc["connector_state"] == "unbound"
    assert doc["operation_id"] == "business.inventory.stock-preview.v1"
    assert doc["actual_business_data"] is False
    assert doc["simulation_only"] is True
    assert doc["execution_available"] is False
    assert doc["database_write_performed"] is False
    assert doc["external_request_performed"] is False
    assert doc["external_provider"] is None
    assert doc["totals"] == {
        "sku_count": 4,
        "below_threshold_count": 2,
        "units_on_hand": 219,
        "suggested_restock_units": 68,
    }
    assert doc["fixture_sha256"]
    assert len(doc["fixture_sha256"]) == 64
    assert all(item["sku"].startswith("DEMO-")
               and item["label"].startswith("Synthetic ") for item in doc["items"])


def test_tenants_are_namespaced_without_cross_tenant_readable_records():
    org_a, org_b = uuid4(), uuid4()
    with local_app(org=org_a) as client:
        a = client.get(ENDPOINT).json()
    with local_app(org=org_b) as client:
        b = client.get(ENDPOINT).json()
    assert a["tenant_demo_partition"] != b["tenant_demo_partition"]
    assert a["items"] == b["items"]  # both intentionally use invented fixture
    assert "organization_id" not in a
    assert "user_id" not in a
    assert "real_customer" not in json.dumps(a).lower()


@pytest.mark.parametrize("role", ["VIEWER", "GUEST", "UNKNOWN"])
def test_read_only_demo_requires_authorized_role(role):
    with local_app(role=role) as client:
        resp = client.get(ENDPOINT)
    assert resp.status_code == 403


@pytest.mark.parametrize("query", [
    "?organization_id=forged",
    "?tenant_id=forged",
    "?fixture_path=/etc/passwd",
    "?connector_url=https://untrusted.invalid",
    "?data_source=production",
    "?scope=business.inventory.read",
])
def test_no_client_supplied_authority_or_provider_routing(query):
    with local_app() as client:
        resp = client.get(ENDPOINT + query)
    assert resp.status_code == 422


@pytest.mark.parametrize("env", [
    {"DOMAIN_SANDBOX_MODE": "off"},
    {"DOMAIN_SANDBOX_MODE": "enabled"},
    {"WORKSPACE_AUTH_MODE": "oidc"},
    {"WORKSPACE_ORIGIN": "https://staging.example.invalid"},
    {"WORKSPACE_ORIGIN": "http://203.0.113.44:8000"},
    {"WORKSPACE_ORIGIN": "http://127.0.0.1:8000/path"},
    {"WORKSPACE_ORIGIN": "http://alice:pass@127.0.0.1:8000"},
])
def test_sandbox_denies_without_explicit_isolated_local_context(monkeypatch, env):
    for key, val in env.items():
        monkeypatch.setenv(key, val)
    with local_app() as client:
        resp = client.get(ENDPOINT)
    assert resp.status_code == 404


def test_remote_peer_not_accepted_even_when_env_is_enabled():
    with local_app(client_host="198.51.100.30") as client:
        resp = client.get(ENDPOINT)
    assert resp.status_code == 404


def test_invalid_fixture_is_not_treated_as_live_data():
    org = uuid4()
    source = json.loads(FIXTURE_PATH.read_text())
    source["items"][0]["on_hand_units"] = True
    with patch("app.synthetic_inventory.FIXTURE_PATH", FIXTURE_PATH.with_name("does-not-exist.json")):
        with pytest.raises(OSError):
            render_synthetic_inventory(org)
    with patch("pathlib.Path.read_bytes", return_value=json.dumps(source).encode()):
        with pytest.raises(ValueError, match="Invalid synthetic inventory item"):
            render_synthetic_inventory(org)


def test_existing_real_domain_operation_remains_deny_and_unbound():
    from app.domain_integrations import policy_preview
    decision = policy_preview("business.inventory.stock-preview.v1", role="OWNER")
    assert decision["decision"] == "DENY"
    assert decision["connector_called"] is False
    assert decision["data_accessed"] is False
    assert "connector_not_bound" in decision["reasons"]


def test_no_paid_sdk_or_production_credentials_in_sandbox():
    module_source = (ROOT / "apps/api/app/synthetic_inventory.py").read_text()
    assert "requests.get(" not in module_source
    assert "httpx." not in module_source
    assert "psycopg.connect(" not in module_source
    assert "aws_access_key" not in module_source.lower()
    source = json.loads(FIXTURE_PATH.read_text())
    assert source["classification"] == "SYNTHETIC_DEMO_ONLY"
    assert source["currency"] == "NONE"


def test_main_app_never_authenticates_fake_bearer_token():
    from app.main import app
    with TestClient(app, client=("127.0.0.1", 50666)) as client:
        resp = client.get(ENDPOINT, headers={
            "Authorization": "Bearer invalid-token"
        })
    assert resp.status_code == 401
    assert resp.headers["Cache-Control"] == "no-store"
