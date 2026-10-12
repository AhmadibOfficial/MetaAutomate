#!/usr/bin/env python3
"""End-to-end tests on a disposable database, never the main database."""
import argparse
import hashlib
import os
import secrets
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
from app.main import app  # noqa: E402
from seed_registry import with_database  # noqa: E402

REQUEST = {
    "title": "Increase qualified appointments",
    "description": "Plan a permission-based pipeline",
    "success_criteria": [{"metric": "qualified appointments", "target": "20", "timeframe_days": 30}],
    "constraints": ["Contact consenting customers only"],
    "requested_capability_ids": ["BIZ-003", "BIZ-005"],
}


def check(response, status):
    assert response.status_code == status, (response.status_code, status, response.text[:600])
    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, help="Name of the disposable database to test")
    args = parser.parse_args()
    assert args.database.startswith(("metaautomate_ci_", "metaautomate_test_")) or (
        args.database == "metaautomate" and os.getenv("GITHUB_ACTIONS") == "true"
    ), "Tests must run only against an isolated database or ephemeral GitHub CI service"
    admin_url = with_database(os.environ["DATABASE_URL"], args.database)
    runtime_url = with_database(os.environ["APP_DATABASE_URL"], args.database)
    os.environ["APP_DATABASE_URL"] = runtime_url
    actors = {}
    with psycopg.connect(admin_url) as conn:
        with conn.cursor() as c:
            c.execute("SELECT rolsuper, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname='metaautomate_runtime'")
            assert c.fetchone() == (False, False, True)
            for org_name, names in (("one", ["owner", "viewer"]), ("two", ["second_owner"])):
                c.execute(
                    "INSERT INTO organizations(slug,name) VALUES(%s,%s) RETURNING id",
                    ("ci-" + uuid4().hex, "CI " + org_name),
                )
                org_id = c.fetchone()[0]
                for name in names:
                    c.execute(
                        "INSERT INTO users(email,display_name) VALUES(%s,%s) RETURNING id",
                        (uuid4().hex + "@example.invalid", name),
                    )
                    user_id = c.fetchone()[0]
                    c.execute(
                        "INSERT INTO organization_memberships(organization_id,user_id,role) VALUES(%s,%s,%s)",
                        (org_id, user_id, "VIEWER" if name == "viewer" else "OWNER"),
                    )
                    token = "mat_dev_" + secrets.token_urlsafe(32)
                    c.execute(
                        "INSERT INTO api_access_tokens(organization_id,user_id,token_sha256,label,expires_at) "
                        "VALUES(%s,%s,%s,%s,now()+interval '1 day')",
                        (org_id, user_id, hashlib.sha256(token.encode()).hexdigest(), name),
                    )
                    actors[name] = {"token": token, "organization_id": org_id, "user_id": user_id}
    with psycopg.connect(runtime_url) as conn:
        try:
            with conn.cursor() as c:
                c.execute("SELECT token_sha256 FROM api_access_tokens LIMIT 1")
            raise AssertionError("Restricted role must not read authentication records")
        except psycopg.errors.InsufficientPrivilege:
            conn.rollback()
    client = TestClient(app)
    auth = lambda name: {"Authorization": "Bearer " + actors[name]["token"]}
    headers = {**auth("owner"), "Idempotency-Key": "objective-ci-key-0001"}
    check(client.post("/v1/objective-operations", json=REQUEST), 401)
    check(client.post("/v1/objective-operations", json=REQUEST, headers={**auth("viewer"), "Idempotency-Key": "viewer-test-0001"}), 403)
    created = check(client.post("/v1/objective-operations", json=REQUEST, headers=headers), 201)
    assert created["persisted"] and not created["execution_allowed"] and created["plan_steps"] == 5
    assert check(client.post("/v1/objective-operations", json=REQUEST, headers=headers), 201) == created
    check(client.post("/v1/objective-operations", json={**REQUEST, "title": "Changed objective title"}, headers=headers), 409)
    oid = created["objective_id"]
    own = check(client.get("/v1/objective-operations/" + oid, headers=auth("owner")), 200)
    assert len(own["tasks"]) == 5 and own["review"]["status"] == "PENDING"
    assert own["workflow"]["state"] == "DRAFT"
    assert len(check(client.get("/v1/objective-operations", headers=auth("owner")), 200)["items"]) == 1
    assert len(check(client.get("/v1/objective-operations", headers=auth("second_owner")), 200)["items"]) == 0
    check(client.get("/v1/objective-operations/" + oid, headers=auth("second_owner")), 404)
    check(client.post("/v1/objective-operations/" + oid + "/review", json={"decision": "APPROVED", "reason": "Reviewed objective"}, headers=auth("viewer")), 403)
    checked = check(client.post("/v1/objective-operations/" + oid + "/review", json={"decision": "APPROVED", "reason": "Approved to plan only"}, headers=auth("owner")), 200)
    assert checked["review_status"] == "APPROVED" and not checked["execution_allowed"]
    check(client.post("/v1/objective-operations/" + oid + "/review", json={"decision": "APPROVED", "reason": "Approved to plan only"}, headers=auth("owner")), 409)
    with psycopg.connect(admin_url) as conn:
        with conn.cursor() as c:
            c.execute("SELECT count(*) FROM objectives WHERE organization_id=%s", (actors["owner"]["organization_id"],))
            assert c.fetchone()[0] == 1
            c.execute("SELECT count(*) FROM audit_events WHERE organization_id=%s AND entity_id=%s",
                      (actors["owner"]["organization_id"], oid))
            assert c.fetchone()[0] == 2
            c.execute("SELECT count(*) FROM capability_executions")
            assert c.fetchone()[0] == 0
            c.execute("UPDATE api_access_tokens SET revoked_at=now() WHERE user_id=%s", (actors["owner"]["user_id"],))
    check(client.get("/v1/objective-operations", headers=auth("owner")), 401)
    print("PASS: restricted role, bearer auth, tenant isolation, idempotency, graph, review, audit and revocation")


if __name__ == "__main__":
    main()
