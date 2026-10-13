#!/usr/bin/env python3
"""Operational Core assessment integration on disposable CI database only."""
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
from app.assessment_engine import QUESTIONS  # noqa: E402
from seed_registry import with_database  # noqa: E402


def require_status(response, status):
    assert response.status_code == status, (status, response.status_code, response.text[:500])
    return response.json()


def make_actor(cur, org, name, role):
    cur.execute(
        "INSERT INTO users(email,display_name) VALUES(%s,%s) RETURNING id",
        (uuid4().hex + "@example.invalid", name),
    )
    user = cur.fetchone()[0]
    cur.execute("SELECT app.set_context(%s,%s)", (org, user))
    cur.execute(
        "INSERT INTO organization_memberships(organization_id,user_id,role) VALUES(%s,%s,%s)",
        (org, user, role),
    )
    token = "mat_dev_" + secrets.token_urlsafe(32)
    cur.execute(
        "INSERT INTO api_access_tokens(organization_id,user_id,token_sha256,label,expires_at) "
        "VALUES(%s,%s,%s,%s,now()+interval '1 day')",
        (org, user, hashlib.sha256(token.encode("ascii")).hexdigest(), name),
    )
    return {"org": org, "user": user, "token": token}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    name = parser.parse_args().database
    assert name.startswith(("metaautomate_ci_", "metaautomate_test_")) or (
        name == "metaautomate" and os.getenv("GITHUB_ACTIONS") == "true"
    ), "Assessment test must never mutate a user's main database"
    admin_url = with_database(os.environ["DATABASE_URL"], name)
    runtime_url = with_database(os.environ["APP_DATABASE_URL"], name)
    os.environ["APP_DATABASE_URL"] = runtime_url
    people = {}
    with psycopg.connect(admin_url) as conn:
        with conn.cursor() as cur:
            for slug, actors in (
                ("assessment-one", [("owner", "OWNER"), ("viewer", "VIEWER")]),
                ("assessment-two", [("other_owner", "OWNER")]),
            ):
                cur.execute("INSERT INTO organizations(slug,name) VALUES(%s,%s) RETURNING id",
                            ("test-" + uuid4().hex, slug))
                org = cur.fetchone()[0]
                for who, role in actors:
                    people[who] = make_actor(cur, org, who, role)

    client = TestClient(app)
    headers = lambda who, key="assessment-int-test-0001": {
        "Authorization": "Bearer " + people[who]["token"],
        "Idempotency-Key": key,
        "X-Assessment-Consent": "generate-report",
    }
    payload = {
        "business_label": "Example Services Company",
        "objective": "Identify process bottlenecks and improve business efficiency",
        "answers": [{"question_id": q["id"], "score": 3 if q["domain"] != "SEC" else 1}
                    for q in QUESTIONS],
    }
    require_status(client.get("/v1/assessments/questions"), 401)
    require_status(client.get("/v1/assessments/questions",headers=headers("owner")), 200)
    require_status(client.post("/v1/assessments",json=payload), 401)
    require_status(client.post("/v1/assessments",json=payload,headers=headers("viewer")), 403)
    no_consent = headers("owner")
    no_consent.pop("X-Assessment-Consent")
    require_status(client.post("/v1/assessments",json=payload,headers=no_consent), 403)
    no_key = headers("owner")
    no_key.pop("Idempotency-Key")
    require_status(client.post("/v1/assessments",json=payload,headers=no_key), 422)
    forged = dict(payload, organization_id=str(people["other_owner"]["org"]))
    require_status(client.post("/v1/assessments",json=forged,headers=headers("owner")), 422)
    missing = dict(payload, answers=payload["answers"][:-1])
    require_status(client.post("/v1/assessments",json=missing,headers=headers("owner")), 422)

    created = require_status(client.post("/v1/assessments",json=payload,headers=headers("owner")), 201)
    assert created["status"] == "COMPLETED"
    assert created["verification_status"] == "CALCULATION_VERIFIED"
    assert created["external_actions_executed"] is False
    assert created["report"]["external_actions_executed"] is False
    assert created["report"]["prioritized_actions"][0]["domain"] == "SEC"
    assert len(created["report"]["domain_results"]) == 5
    # Replays are idempotent and do not append a second audit event.
    replay = require_status(client.post("/v1/assessments",json=payload,headers=headers("owner")), 201)
    assert replay["assessment_id"] == created["assessment_id"]
    altered = dict(payload, answers=[dict(a) for a in payload["answers"]])
    altered["answers"][0]["score"] = 0
    require_status(client.post("/v1/assessments",json=altered,headers=headers("owner")), 409)

    rid = created["assessment_id"]
    own = require_status(client.get("/v1/assessments/" + rid,headers=headers("owner")), 200)
    assert own["receipt"]["report_sha256"] == created["receipt"]["report_sha256"]
    # A viewer in this organization can read reports, never generate them.
    shared = require_status(client.get("/v1/assessments/" + rid,headers=headers("viewer")), 200)
    assert shared["assessment_id"] == rid
    assert len(require_status(client.get("/v1/assessments",headers=headers("owner")), 200)["items"]) == 1
    assert len(require_status(client.get("/v1/assessments",headers=headers("other_owner")), 200)["items"]) == 0
    require_status(client.get("/v1/assessments/" + rid,headers=headers("other_owner")), 404)

    # The same idempotency key is independently scoped per organization.
    second = require_status(client.post("/v1/assessments",json=payload,headers=headers("other_owner")), 201)
    assert second["assessment_id"] != rid

    with psycopg.connect(admin_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM digital_assessments WHERE organization_id=%s",
                (people["owner"]["org"],)
            )
            assert cur.fetchone()[0] == 1
            cur.execute(
                "SELECT count(*) FROM audit_events WHERE organization_id=%s "
                "AND entity_type='ASSESSMENT' AND entity_id=%s",
                (people["owner"]["org"], rid)
            )
            assert cur.fetchone()[0] == 1
            for table in ("capability_executions", "agent_runs", "tool_calls"):
                cur.execute("SELECT count(*) FROM " + table)
                assert cur.fetchone()[0] == 0, table

    # Direct runtime modification must be refused, even for the same tenant.
    with psycopg.connect(runtime_url) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE digital_assessments SET report='{}'::jsonb WHERE id=%s", (rid,))
        except psycopg.errors.InsufficientPrivilege:
            conn.rollback()
        else:
            raise AssertionError("Runtime role must not update immutable reports")

    # Revoking a development token invalidates subsequent reads.
    with psycopg.connect(admin_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE api_access_tokens SET revoked_at=now() WHERE user_id=%s",
                        (people["owner"]["user"],))
    require_status(client.get("/v1/assessments/" + rid,headers=headers("owner")), 401)
    print("PASS: full deterministic assessment, tenant isolation, user authorization,"
          " evidence integrity, audit, idempotency, revocation and no external work")


if __name__ == "__main__":
    main()
