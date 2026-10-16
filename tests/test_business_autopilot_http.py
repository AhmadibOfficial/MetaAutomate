"""Loopback boundary and ephemeral demo handle checks, not tenant acceptance."""
import json

from fastapi.testclient import TestClient
import pytest

from app.business_autopilot_demo import create_demo_app

ORIGIN = "http://127.0.0.1:8090"
HEADERS = {"origin": ORIGIN, "x-metaautomate-demo": "1"}


def client(**kwargs):
    return TestClient(create_demo_app(), base_url=ORIGIN, client=kwargs.get("peer", ("127.0.0.1", 1234)))


def start(c, case="standard"):
    response = c.post("/demo/runs", json={"scenario_id": case}, headers=HEADERS)
    assert response.status_code == 200, response.text
    data = response.json()
    return {**HEADERS, "x-demo-run": data["run_token"]}, data["state"]


def action(c, headers, step, data=None):
    return c.post("/demo/actions/" + step, json=data or {}, headers=headers)


def complete(c, headers):
    assert action(c, headers, "assess").status_code == 200
    plan = action(c, headers, "plan").json()["plan"]
    assert action(c, headers, "review", {"plan_sha256": plan["plan_sha256"], "decision": "APPROVE", "simulation_only": True}).status_code == 200
    assert action(c, headers, "simulate").status_code == 200
    assert action(c, headers, "verify").status_code == 200


def test_full_http_flow_private_report_and_deleted_run():
    with client() as c:
        h, _ = start(c)
        assert c.get("/demo/report", headers=h).status_code == 409
        complete(c, h)
        response = c.get("/demo/report", headers=h)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert "attachment" in response.headers["Content-Disposition"]
        assert h["x-demo-run"] not in response.text
        assert response.json()["classification"] == "SYNTHETIC_DEMO_ONLY"
        assert c.delete("/demo/run", headers=h).status_code == 200
        assert c.get("/demo/run", headers=h).status_code == 404


def test_local_runs_separate_and_handles_not_guessable_or_global():
    with client() as c, client() as other:
        first, _ = start(c)
        second, _ = start(c)
        assert first["x-demo-run"] != second["x-demo-run"]
        assert len(first["x-demo-run"]) >= 40
        action(c, first, "assess")
        assert c.get("/demo/run", headers=second).json()["stage"] == "LOADED"
        assert other.get("/demo/run", headers=first).status_code == 404
        assert c.get("/demo/run").status_code == 404
        assert c.get("/demo/run", headers={**HEADERS, "x-demo-run":"forged"}).status_code == 404


@pytest.mark.parametrize("headers", [
    {}, {"origin": ORIGIN}, {"x-metaautomate-demo":"1"},
    {**HEADERS, "origin":"https://malicious.invalid"},
    {**HEADERS, "origin":"null"}, {**HEADERS, "host":"malicious.invalid"},
    {**HEADERS, "sec-fetch-site":"cross-site"}, {**HEADERS, "sec-fetch-site":"same-site"},
    {**HEADERS, "x-forwarded-for":"127.0.0.1"}, {**HEADERS, "forwarded":"for=127.0.0.1"},
    {**HEADERS, "x-tenant-id":"fake"}, {**HEADERS, "x-organization-id":"fake"},
])
def test_cross_origin_rebinding_and_forged_authority_denied(headers):
    with client() as c:
        r = c.post("/demo/runs", json={"scenario_id":"standard"}, headers=headers)
    assert r.status_code == 403


def test_external_peer_and_proxy_override_not_accepted():
    with client(peer=("203.0.113.5", 1234)) as c:
        assert c.get("/").status_code == 403
        assert c.post("/demo/runs", json={"scenario_id":"standard"}, headers=HEADERS).status_code == 403


@pytest.mark.parametrize("payload", [
    {"scenario_id":"standard", "role":"OWNER"}, {"scenario_id":"standard", "inventory":[]},
    {"scenario_id":"standard", "url":"https://provider.invalid"}, {"scenario_id":"../../.env"},
    {"scenario_id":True}, {"scenario_id":["standard"]}, {"scenario_id":{}}, {}, [], None,
])
def test_no_uploaded_data_free_text_or_client_role_accepted(payload):
    with client() as c:
        response = c.post("/demo/runs", content=json.dumps(payload),
                          headers={**HEADERS, "content-type":"application/json"})
    assert response.status_code == 422


@pytest.mark.parametrize("payload,status", [
    (b'{"scenario_id":"standard","scenario_id":"standard"}', 422),
    (b'{"scenario_id":NaN}', 422), (b" " * 4097, 413), (b"\xff", 422),
])
def test_strict_bounded_request_body(payload, status):
    with client() as c:
        response = c.post("/demo/runs", content=payload,
                          headers={**HEADERS, "content-type":"application/json"})
    assert response.status_code == status


def test_wrong_mime_query_and_unknown_paths_have_no_file_access():
    with client() as c:
        assert c.post("/demo/runs", content="scenario_id=standard", headers=HEADERS).status_code == 415
        assert c.get("/?file=../../.env").status_code == 403
        assert c.get("/contracts/demos/business-autopilot-v1.json").status_code == 404
        assert c.get("/v1/objective-operations").status_code == 404
        assert c.get("/openapi.json").status_code == 404
        assert c.get("/").headers["X-Frame-Options"] == "DENY"


def test_expired_runs_and_capacity_are_bounded(monkeypatch):
    monkeypatch.setattr("app.business_autopilot_demo.MAX_RUNS", 1)
    with client() as c:
        h, _ = start(c)
        assert c.post("/demo/runs", json={"scenario_id":"standard"}, headers=HEADERS).status_code == 429
        monkeypatch.setattr("app.business_autopilot_demo.TTL_SECONDS", 0)
        assert c.get("/demo/run", headers=h).status_code == 404
        assert c.post("/demo/runs", json={"scenario_id":"standard"}, headers=HEADERS).status_code == 200


def test_invalid_transition_and_extra_action_fields_preserve_state():
    with client() as c:
        h, before = start(c)
        assert action(c, h, "simulate").status_code == 409
        assert action(c, h, "assess", {"enable_live":True}).status_code == 422
        assert c.get("/demo/run", headers=h).json() == before


@pytest.mark.parametrize("port", [80, 0, 65536, "8090", True])
def test_no_unsafe_or_ambiguous_listener_port(port):
    with pytest.raises(ValueError):
        create_demo_app(port)
