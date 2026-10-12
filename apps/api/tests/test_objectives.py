"""Objective Plan Preview: explicit, read-only and fail-closed contract tests."""

import pytest
from fastapi.testclient import TestClient

from app import objectives
from app.main import app

client = TestClient(app)
KEY = "example-development-key"
HEADERS = {"X-Registry-Key": KEY}
BASE = {
    "title": "Increase qualified customer appointments",
    "description": "Review the sales pipeline for the next month",
    "success_criteria": [{"metric": "qualified appointments", "target": "20", "timeframe_days": 30}],
    "constraints": ["Only contact customers who opted in"],
    "requested_capability_ids": ["BIZ-003", "BIZ-005"],
}


@pytest.fixture(autouse=True)
def guard_and_catalog(monkeypatch):
    monkeypatch.setenv("REGISTRY_READ_API_KEY", KEY)
    queries = []

    def fake_query(sql, params=(), *, single=False):
        queries.append(sql)
        assert sql.lstrip().upper().startswith("SELECT"), "Preview must never mutate database"
        if "FROM capability_definitions" in sql:
            return [
                {"capability_id": "BIZ-003", "name": "Lead Qualification", "domain": "BIZ",
                 "release": "R1", "lifecycle_status": "DRAFT", "is_enabled": False},
                {"capability_id": "BIZ-005", "name": "Appointment Booking", "domain": "BIZ",
                 "release": "R1", "lifecycle_status": "DRAFT", "is_enabled": False},
            ]
        if "FROM capability_dependencies" in sql:
            return [{"capability_id": "BIZ-005", "depends_on_capability_id": "BIZ-003"}]
        pytest.fail("Unexpected SQL query")

    monkeypatch.setattr(objectives.registry, "_query", fake_query)
    return queries


def test_preview_is_a_non_executing_graph():
    response = client.post("/v1/objectives/preview", json=BASE, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["execution_allowed"] is False
    assert data["persisted"] is False
    assert data["selection_method"] == "EXPLICIT_CAPABILITY_IDS"
    assert len(data["matched_capabilities"]) == 2
    assert all(not cap["execution_ready"] for cap in data["matched_capabilities"])
    assert [node["step_id"] for node in data["work_graph"]] == ["S1", "S2", "C1", "C2", "S3"]
    assert data["work_graph"][3]["depends_on"] == ["S2", "C1"]
    assert data["objective"]["success_criteria"][0]["timeframe_days"] == 30


def test_authentication_required():
    assert client.post("/v1/objectives/preview", json=BASE).status_code == 401
    assert client.post("/v1/objectives/preview", json=BASE,
                       headers={"X-Registry-Key": "wrong"}).status_code == 401


def test_fails_closed_without_auth_configuration(monkeypatch):
    monkeypatch.delenv("REGISTRY_READ_API_KEY")
    assert client.post("/v1/objectives/preview", json=BASE, headers=HEADERS).status_code == 503


def test_invalid_criteria_rejected():
    invalid = {**BASE, "success_criteria": []}
    assert client.post("/v1/objectives/preview", json=invalid, headers=HEADERS).status_code == 422


def test_unknown_capability_rejected():
    invalid = {**BASE, "requested_capability_ids": ["BIZ-003", "PER-999"]}
    response = client.post("/v1/objectives/preview", json=invalid, headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["detail"]["capability_ids"] == ["PER-999"]


def test_duplicate_capability_rejected():
    invalid = {**BASE, "requested_capability_ids": ["BIZ-003", "BIZ-003"]}
    assert client.post("/v1/objectives/preview", json=invalid, headers=HEADERS).status_code == 422


def test_only_whitelisted_fields_permitted():
    invalid = {**BASE, "organization_id": "11111111-1111-4111-8111-111111111111"}
    assert client.post("/v1/objectives/preview", json=invalid, headers=HEADERS).status_code == 422


def test_limit_constraints_and_capabilities():
    invalid = {**BASE, "constraints": ["x"]}
    assert client.post("/v1/objectives/preview", json=invalid, headers=HEADERS).status_code == 422
    invalid = {**BASE, "requested_capability_ids": [f"BIZ-{i:03d}" for i in range(1, 12)]}
    assert client.post("/v1/objectives/preview", json=invalid, headers=HEADERS).status_code == 422


def test_cyclic_dependencies_are_rejected(monkeypatch):
    original_query = objectives.registry._query

    def with_cycle(sql, params=(), *, single=False):
        if "FROM capability_dependencies" in sql:
            return [
                {"capability_id": "BIZ-003", "depends_on_capability_id": "BIZ-005"},
                {"capability_id": "BIZ-005", "depends_on_capability_id": "BIZ-003"},
            ]
        return original_query(sql, params, single=single)

    monkeypatch.setattr(objectives.registry, "_query", with_cycle)
    assert client.post("/v1/objectives/preview", json=BASE, headers=HEADERS).status_code == 422
