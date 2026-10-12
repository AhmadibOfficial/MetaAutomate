import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import registry

client = TestClient(app)
KEY = "not-a-real-production-key"


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("REGISTRY_READ_API_KEY", KEY)


def test_requires_key():
    assert client.get("/v1/capabilities").status_code == 401
    assert client.get("/v1/capabilities", headers={"X-Registry-Key": "wrong"}).status_code == 401


def test_fails_closed_without_configured_key(monkeypatch):
    monkeypatch.delenv("REGISTRY_READ_API_KEY")
    r = client.get("/v1/capabilities", headers={"X-Registry-Key": KEY})
    assert r.status_code == 503


def test_filtered_list(monkeypatch):
    seen = []

    def fake_query(sql, params=(), *, single=False):
        seen.append((sql, params, single))
        if single:
            return {"total": 1}
        return [{"capability_id": "BIZ-001", "name": "Digital Transformation Assessment",
                 "domain": "BIZ", "release": "R1", "priority": "P0",
                 "lifecycle_status": "DRAFT", "is_enabled": False,
                 "version": "0.1.0", "version_state": "DRAFT",
                 "contract_provided": False, "catalog_ready": False}]

    monkeypatch.setattr(registry, "_query", fake_query)
    r = client.get("/v1/capabilities?domain=BIZ&release=R1&status=DRAFT&limit=10&offset=0",
                   headers={"X-Registry-Key": KEY})
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["catalog_ready"] is False
    assert seen[0][1] == ("BIZ", "R1", "DRAFT", 10, 0)
    assert seen[1][1] == ("BIZ", "R1", "DRAFT")


def test_filter_validation():
    r = client.get("/v1/capabilities?domain=INVALID", headers={"X-Registry-Key": KEY})
    assert r.status_code == 422


def test_missing_capability(monkeypatch):
    monkeypatch.setattr(registry, "_query", lambda *args, **kwargs: None)
    r = client.get("/v1/capabilities/CORE-999", headers={"X-Registry-Key": KEY})
    assert r.status_code == 404


def test_capability_detail(monkeypatch):
    def fake_query(sql, params=(), *, single=False):
        if single:
            return {"capability_id": "CORE-001", "name": "Objective Interpretation",
                    "catalog_ready": False}
        if "capability_dependencies" in sql:
            return [{"depends_on_capability_id": "CORE-002", "min_version": None}]
        return [{"permission_key": "objectives.read", "requires_approval": False}]

    monkeypatch.setattr(registry, "_query", fake_query)
    r = client.get("/v1/capabilities/CORE-001", headers={"X-Registry-Key": KEY})
    assert r.status_code == 200
    assert r.json()["dependencies"][0]["depends_on_capability_id"] == "CORE-002"
    assert r.json()["required_permissions"][0]["permission_key"] == "objectives.read"
