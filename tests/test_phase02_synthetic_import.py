"""P2-03b: validated synthetic file bytes, not a production business import."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.authn import Principal, TenantSession, get_tenant_session
from app.synthetic_inventory_import import (
    MAX_BYTES, parse_synthetic_inventory_bytes, router,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "contracts/domains/v1/fixtures"
URL = "/v1/domain-integrations/sandbox/inventory/import/"
HEADERS = {"x-metaautomate-demo-data": "SYNTHETIC_ONLY"}


def client_for(role="OWNER", org=None, peer="127.0.0.1"):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_tenant_session] = lambda: TenantSession(
        conn=None, principal=Principal(
            organization_id=org or uuid4(), user_id=uuid4(), role=role
        ))
    return TestClient(app, client=(peer, 50612))


@pytest.fixture(autouse=True)
def sandbox_environment(monkeypatch):
    monkeypatch.setenv("DOMAIN_SANDBOX_MODE", "local_synthetic")
    monkeypatch.setenv("WORKSPACE_AUTH_MODE", "dev_key")
    monkeypatch.setenv("WORKSPACE_ORIGIN", "http://127.0.0.1:8000")


def input_bytes(fmt):
    return (FIX / ("synthetic_inventory_import." + fmt)).read_bytes()


def send(client, fmt, data=None, *, headers=None, path=None):
    custom = dict(HEADERS)
    custom["Content-Type"] = "text/csv" if fmt == "csv" else "application/json"
    if headers:
        custom.update(headers)
    return client.post(path or URL + fmt, content=data if data is not None else input_bytes(fmt),
                       headers=custom)


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_import_valid_synthetic_file_and_no_effects(fmt):
    with client_for() as client:
        first = send(client, fmt)
        next_one = send(client, fmt)
    assert first.status_code == 200, first.text
    assert first.json() == next_one.json()
    data = first.json()
    assert data["mode"] == "LOCAL_SYNTHETIC_FILE_PREVIEW"
    assert data["format"] == fmt
    assert data["actual_business_data"] is False
    assert data["simulation_only"] is True
    assert data["execution_available"] is False
    assert data["persisted"] is False
    assert data["connector_state"] == "unbound"
    assert data["database_write_performed"] is False
    assert data["external_request_performed"] is False
    assert data["totals"] == {
        "sku_count": 4, "below_threshold_count": 2,
        "units_on_hand": 219, "suggested_restock_units": 68,
    }
    assert len(data["content_sha256"]) == 64
    assert all(row["sku"].startswith("DEMO-") for row in data["items"])


def test_csv_and_json_have_identical_stock_calculation():
    org = uuid4()
    with client_for(org=org) as client:
        csv_resp = send(client, "csv").json()
        json_resp = send(client, "json").json()
    assert csv_resp["totals"] == json_resp["totals"]
    assert csv_resp["items"] == json_resp["items"]
    assert csv_resp["tenant_demo_partition"] == json_resp["tenant_demo_partition"]


def test_server_derived_demo_partition_differs_per_organization():
    with client_for(org=uuid4()) as c:
        first = send(c, "json").json()
    with client_for(org=uuid4()) as c:
        second = send(c, "json").json()
    assert first["tenant_demo_partition"] != second["tenant_demo_partition"]
    assert first["items"] == second["items"]  # every tenant sees invented items
    assert "organization_id" not in first
    assert "tenant_id" not in first


@pytest.mark.parametrize("role", ["VIEWER", "GUEST", "UNKNOWN"])
def test_roles_without_preview_permission_rejected(role):
    with client_for(role=role) as client:
        resp = send(client, "json")
    assert resp.status_code == 403


@pytest.mark.parametrize(("key", "value"), [
    ("DOMAIN_SANDBOX_MODE", "off"),
    ("DOMAIN_SANDBOX_MODE", "enabled"),
    ("WORKSPACE_AUTH_MODE", "oidc"),
    ("WORKSPACE_ORIGIN", "https://staging.example.invalid"),
    ("WORKSPACE_ORIGIN", "http://203.0.113.5:8000"),
])
def test_disabled_and_non_local_environments_denied(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with client_for() as client:
        resp = send(client, "csv")
    assert resp.status_code == 404


def test_nonlocal_peer_denied():
    with client_for(peer="198.51.100.7") as client:
        resp = send(client, "csv")
    assert resp.status_code == 404


@pytest.mark.parametrize("header", [
    "x-tenant-id", "x-organization-id", "x-connector-url",
    "x-data-source", "x-filename", "x-file-path", "x-provider-key"
])
def test_client_authority_and_path_headers_rejected(header):
    with client_for() as client:
        resp = send(client, "json", headers={header: "forged"})
    assert resp.status_code == 422


@pytest.mark.parametrize("query", [
    "?tenant_id=1", "?organization_id=1", "?file=/etc/passwd",
    "?connector_url=https://example.invalid", "?import_real=true"
])
def test_no_query_authority(query):
    with client_for() as client:
        resp = send(client, "csv", path=URL + "csv" + query)
    assert resp.status_code == 422


@pytest.mark.parametrize(("fmt", "data"), [
    ("csv", b""),
    ("csv", b"\x00csv"),
    ("json", b"\x00json"),
    ("json", b'{"schema_version":1,"classification":"REAL","items":[]}'),
    ("json", b'{"schema_version":1,"classification":"SYNTHETIC_DEMO_ONLY","items":[],"tenant_id":"t"}'),
    ("json", b'{"schema_version":1,"schema_version":1,"classification":"SYNTHETIC_DEMO_ONLY","items":[]}'),
    ("json", b'{"schema_version":true,"classification":"SYNTHETIC_DEMO_ONLY","items":[]}'),
    ("json", b'{"schema_version":1,"classification":"SYNTHETIC_DEMO_ONLY","items":[{"sku":"REAL-1"}]}'),
    ("csv", b"sku,label,on_hand_units,reorder_threshold_units,target_units\nREAL-123,Synthetic item,1,2,3\n"),
    ("csv", b"sku,label,on_hand_units,reorder_threshold_units,target_units\nDEMO-ABC,=HYPERLINK,1,2,3\n"),
    ("csv", b"sku,label,on_hand_units,reorder_threshold_units,target_units\nDEMO-ABC,Synthetic item,1,2\n"),
    ("csv", b"sku,label,on_hand_units,reorder_threshold_units,target_units\nDEMO-ABC,Synthetic item,-1,2,3\n"),
    ("csv", b"sku,label,on_hand_units,reorder_threshold_units,target_units\nDEMO-ABC,Synthetic item,1,02,3\n"),
    ("csv", b"sku,label,on_hand_units,reorder_threshold_units,target_units\nDEMO-ABC,Synthetic item,1,2,1\n"),
])
def test_malformed_real_like_injection_and_noncanonical_data_rejected(fmt, data):
    with client_for() as client:
        resp = send(client, fmt, data=data)
    assert resp.status_code == 422, (fmt, resp.text)


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_rejects_file_too_large_and_does_not_echo_bytes(fmt):
    data = input_bytes(fmt) + b" " * (MAX_BYTES + 1)
    with client_for() as client:
        resp = send(client, fmt, data=data)
    assert resp.status_code == 413
    assert "DEMO-MAIZE-001" not in resp.text


def test_no_declaration_and_wrong_media_type():
    with client_for() as client:
        no_attest = send(client, "csv", headers={"x-metaautomate-demo-data": "LIVE_CUSTOMER"})
        wrong_mime = send(client, "csv", headers={"content-type": "application/octet-stream"})
        multipart = send(client, "csv", headers={"content-type": "multipart/form-data"})
    assert no_attest.status_code == 422
    assert wrong_mime.status_code == 415
    assert multipart.status_code == 415


def test_type_limits_duplicates_and_large_row_counts():
    dataset = json.loads(input_bytes("json"))
    dataset["items"] *= 6
    with client_for() as client:
        excess = send(client, "json", data=json.dumps(dataset).encode())
    assert excess.status_code == 422
    data2 = json.loads(input_bytes("json"))
    data2["items"].append(dict(data2["items"][0]))
    with client_for() as client:
        duplicate = send(client, "json", data=json.dumps(data2).encode())
    assert duplicate.status_code == 422
    data3 = json.loads(input_bytes("json"))
    data3["items"][0]["on_hand_units"] = True
    with client_for() as client:
        boolean = send(client, "json", data=json.dumps(data3).encode())
    assert boolean.status_code == 422


def test_primary_real_inventory_contract_still_denies():
    from app.domain_integrations import policy_preview
    result = policy_preview("business.inventory.stock-preview.v1", role="OWNER")
    assert result["decision"] == "DENY"
    assert result["connector_called"] is False
    assert result["data_accessed"] is False


def test_invalid_bearer_stays_unauthorized_and_no_store():
    from app.main import app
    with TestClient(app, client=("127.0.0.1", 50612)) as client:
        response = client.post(
            URL + "csv", content=input_bytes("csv"),
            headers={**HEADERS, "content-type": "text/csv",
                     "Authorization": "Bearer invalid-token"},
        )
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"


def test_parser_is_memory_only_and_import_not_enabled_for_oidc():
    from app.main import app
    src = (ROOT / "apps/api/app/synthetic_inventory_import.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "request.stream()" in src
    assert "async for chunk" in src
    assert "psycopg.connect(" not in src
    assert "requests.post(" not in src
    assert "httpx." not in src
    assert "UploadFile" not in src
    assert 'if _mode == "dev_key":' in main
    assert 'app.include_router(synthetic_inventory_import_router)' in main
