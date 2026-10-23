"""P2-061 API admission negative cases, no live DB, account or network."""
from __future__ import annotations

import base64
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.secure_data_lab_api import _lab, router
from app.secure_inventory_lab import SecureInventoryLab


def make_request(*, host="127.0.0.1:8000", client="127.0.0.1", headers=None):
    entries = [(b"host", host.encode("ascii"))]
    for k, v in (headers or {}).items():
        entries.append((k.lower().encode("ascii"), v.encode("ascii")))
    return Request({"type": "http", "method": "GET", "scheme": "http",
                    "path": "/v1/data-lab/inventory", "query_string": b"",
                    "root_path": "", "headers": entries,
                    "client": (client, 16000), "server": ("127.0.0.1", 8000)})


def allowed_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MAT_DATA_LAB_ENABLED", "1")
    monkeypatch.setenv("MAT_DATA_LAB_ACK", "LOCAL_REHEARSAL_ONLY")
    monkeypatch.setenv("WORKSPACE_AUTH_MODE", "dev_key")
    monkeypatch.setenv("WORKSPACE_ORIGIN", "http://127.0.0.1:8000")
    monkeypatch.setenv("MAT_DATA_LAB_SQLITE", str(tmp_path / "lab.sqlite"))
    monkeypatch.setenv("MAT_DATA_LAB_KEY_B64",
                       base64.b64encode(b"K" * 32).decode("ascii"))


def test_disabled_by_default(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    monkeypatch.delenv("MAT_DATA_LAB_ENABLED")
    with pytest.raises(HTTPException) as e:
        _lab(make_request())
    assert e.value.status_code == 404


def test_explicit_acknowledgement_required(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    monkeypatch.setenv("MAT_DATA_LAB_ACK", "yes")
    with pytest.raises(HTTPException) as e:
        _lab(make_request())
    assert e.value.status_code == 404


def test_production_oidc_mode_denied(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_AUTH_MODE", "oidc")
    with pytest.raises(HTTPException) as e:
        _lab(make_request())
    assert e.value.status_code == 404


def test_nonloopback_origin_and_clients_denied(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WORKSPACE_ORIGIN", "https://metaautomate.onrender.com")
    with pytest.raises(HTTPException) as e:
        _lab(make_request())
    assert e.value.status_code == 403
    monkeypatch.setenv("WORKSPACE_ORIGIN", "http://127.0.0.1:8000")
    for request in (make_request(client="203.0.113.20"),
                    make_request(host="metaautomate.onrender.com"),
                    make_request(client="testclient")):
        with pytest.raises(HTTPException) as e:
            _lab(request)
        assert e.value.status_code == 403


def test_header_tenant_spoofing_denied(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as e:
        _lab(make_request(headers={"X-Tenant-Id": "my-other-tenant"}))
    assert e.value.status_code == 403


def test_missing_encryption_secret_fail_closed(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    monkeypatch.delenv("MAT_DATA_LAB_KEY_B64")
    with pytest.raises(HTTPException) as e:
        _lab(make_request())
    assert e.value.status_code == 503


def test_explicit_loopback_lab_can_be_constructed(monkeypatch, tmp_path):
    allowed_env(monkeypatch, tmp_path)
    assert isinstance(_lab(make_request()), SecureInventoryLab)


def test_api_has_no_publish_or_production_endpoints():
    paths = {route.path for route in router.routes}
    assert "/v1/data-lab/inventory" in paths
    assert "/v1/data-lab/audit" in paths
    assert all("publish" not in path and "activate" not in path for path in paths)
