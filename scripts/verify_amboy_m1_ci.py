#!/usr/bin/env python3
"""AMBOY M1 end-to-end verification on GitHub's disposable PostgreSQL ONLY."""
import hashlib
import os
import secrets
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

# This test INSERTs tenants, sessions, audit rows and quota records.
# A spoofable GITHUB_ACTIONS flag or matching local DB name alone is NOT a
# sufficient safety boundary. Refuse all non-exact disposable CI connection
# targets, including the owner's Kali development database on port 5433.
if not (os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("CI") == "true"
        and os.environ.get("GITHUB_REPOSITORY") == "AhmadibOfficial/MetaAutomate"
        and os.environ.get("GITHUB_RUN_ID", "").isdigit()):
    raise SystemExit("REFUSED: AMBOY M1 mutation test requires the verified CI runner")
if os.environ.get("DATABASE_URL") != (
        "postgresql://metaautomate:ci_only_password@localhost:5432/metaautomate"
    ) or os.environ.get("APP_DATABASE_URL") != (
        "postgresql://metaautomate_runtime:ci_runtime_password@localhost:5432/metaautomate"
    ):
    raise SystemExit("REFUSED: AMBOY M1 integration targets only disposable CI PostgreSQL")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
from app.main import app  # noqa: E402


def identity(cur, org, role):
    cur.execute(
        "INSERT INTO users(email,display_name) VALUES(%s,%s) RETURNING id",
        (uuid4().hex + "@example.invalid", "AMBOY CI " + role),
    )
    user = cur.fetchone()[0]
    cur.execute("SELECT app.set_context(%s,%s)", (org, user))
    cur.execute(
        "INSERT INTO organization_memberships(organization_id,user_id,role,status) "
        "VALUES(%s,%s,%s,'ACTIVE')", (org, user, role),
    )
    token = "mat_dev_" + secrets.token_urlsafe(32)
    cur.execute(
        "INSERT INTO api_access_tokens "
        "(organization_id,user_id,token_sha256,label,expires_at) "
        "VALUES(%s,%s,%s,'AMBOY ephemeral CI',now()+interval '1 day')",
        (org, user, hashlib.sha256(token.encode("ascii")).hexdigest()),
    )
    return {"organization_id": org, "user_id": user, "token": token}


def status(response, expected):
    assert response.status_code == expected, (
        expected, response.status_code, response.text[:500],
    )
    return response.json()


def main():
    os.environ.pop("AMBOY_M1_ENABLED", None)
    admin = os.environ["DATABASE_URL"]
    runtime = os.environ["APP_DATABASE_URL"]
    people = {}
    with psycopg.connect(admin) as conn:
        with conn.cursor() as cur:
            for group, roles in (("one", ["OWNER", "VIEWER"]), ("two", ["OWNER"])):
                cur.execute(
                    "INSERT INTO organizations(slug,name) VALUES(%s,%s) RETURNING id",
                    ("amboy-" + uuid4().hex, "AMBOY CI " + group),
                )
                org = cur.fetchone()[0]
                for role in roles:
                    people[group + "-" + role] = identity(cur, org, role)

    client = TestClient(app)
    user_a = people["one-OWNER"]
    user_b = people["two-OWNER"]
    viewer = people["one-VIEWER"]
    headers = lambda person: {"Authorization": "Bearer " + person["token"]}
    initial = {
        "client_request_id": str(uuid4()),
        "message": "Please explain the options for streamlining our operations.",
        "requested_mode": "answer",
    }

    status(client.post("/v1/amboy/turn", json=initial, headers=headers(user_a)), 404)
    os.environ["AMBOY_M1_ENABLED"] = "1"
    status(client.post("/v1/amboy/turn", json=initial), 401)
    status(client.post("/v1/amboy/turn", json=initial, headers=headers(viewer)), 403)
    status(client.post("/v1/amboy/turn", json=dict(initial, organization_id=str(user_b["organization_id"]),
                                                     product="onecall"), headers=headers(user_a)), 422)
    status(client.post("/v1/amboy/turn", json=dict(initial,
        context_hint={"surface": "onecall_app"}), headers=headers(user_a)), 403)
    status(client.post("/v1/amboy/turn", json=dict(initial,
        context_hint={"surface": "metaautomate_workspace", "resource_id": str(uuid4())}),
        headers=headers(user_a)), 403)
    status(client.post("/v1/amboy/turn", json=dict(initial, message="   "),
        headers=headers(user_a)), 422)
    status(client.post("/v1/amboy/turn", json=dict(initial,
        requested_mode="arbitrary_code"), headers=headers(user_a)), 422)
    status(client.get("/v1/onecall/amboy", headers=headers(user_a)), 404)

    first = status(client.post("/v1/amboy/turn", json=initial, headers=headers(user_a)), 200)
    assert first["status"] == "unsupported" and first["execution_performed"] is False
    assert first["reply"] and first["evidence_refs"][0].startswith("amboy:m1:")
    receipt_id = first["evidence_refs"][0].rsplit(":", 1)[1]
    assert status(client.post("/v1/amboy/turn", json=initial, headers=headers(user_a)), 200) == first
    status(client.post("/v1/amboy/turn", json=dict(initial,
        message="Tampered with same request ID"), headers=headers(user_a)), 409)

    # The same client UUID in two organizations cannot expose or reuse A's receipt.
    other = status(client.post("/v1/amboy/turn", json=initial, headers=headers(user_b)), 200)
    assert other["evidence_refs"] != first["evidence_refs"]
    assert other["conversation_id"] != first["conversation_id"]

    # The gateway records a constrained, non-executing receipt for all modes.
    for i in range(9):
        p = {**initial, "client_request_id": str(uuid4()), "message": f"Dry-run {i}"}
        if i == 0:
            p["requested_mode"] = "propose_action"
        rsp = status(client.post("/v1/amboy/turn", json=p, headers=headers(user_a)), 200)
        assert rsp["status"] == "unsupported" and rsp["execution_performed"] is False

    status(client.post("/v1/amboy/turn", json={
        **initial, "client_request_id": str(uuid4()), "message": "Over quota"
    }, headers=headers(user_a)), 429)
    # A replay of an accepted request is free and remains reproducible.
    assert status(client.post("/v1/amboy/turn", json=initial, headers=headers(user_a)), 200) == first

    with psycopg.connect(admin) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM amboy_m1_requests WHERE organization_id=%s",
                        (user_a["organization_id"],))
            assert cur.fetchone()[0] == 10
            cur.execute("SELECT count(*) FROM amboy_m1_requests WHERE organization_id=%s",
                        (user_b["organization_id"],))
            assert cur.fetchone()[0] == 1
            cur.execute(
                "SELECT request_count FROM amboy_m1_quotas "
                "WHERE organization_id=%s AND actor_user_id=%s",
                (user_a["organization_id"], user_a["user_id"]),
            )
            assert cur.fetchone()[0] == 10
            cur.execute(
                "SELECT count(*) FROM audit_events WHERE organization_id=%s "
                "AND action='AMBOY_M1_NO_MODEL'",
                (user_a["organization_id"],),
            )
            assert cur.fetchone()[0] == 10
            cur.execute(
                "SELECT payload_sha256 FROM amboy_m1_requests WHERE id=%s", (receipt_id,),
            )
            digest = cur.fetchone()[0]
            assert len(digest) == 64 and initial["message"] not in digest
            for table in ("tool_calls", "agent_runs", "capability_executions"):
                cur.execute("SELECT count(*) FROM " + table)
                assert cur.fetchone()[0] == 0, table
            # FORCE RLS applies even to the owner role; establish the same
            # tenant context before proving the append-only trigger runs.
            cur.execute("SELECT app.set_context(%s,%s)",
                        (user_a["organization_id"], user_a["user_id"]))
            try:
                cur.execute("UPDATE amboy_m1_requests SET outcome='unsupported' WHERE id=%s",
                            (receipt_id,))
            except psycopg.errors.RaiseException:
                conn.rollback()
            else:
                raise AssertionError("Immutable AMBOY M1 receipt was modified")

    with psycopg.connect(runtime) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM amboy_m1_requests")
            assert cur.fetchone()[0] == 0, "Tenant RLS leaked rows without a session"
            cur.execute(
                "SELECT has_table_privilege('metaautomate_runtime',"
                "'amboy_m1_requests','UPDATE')"
            )
            assert cur.fetchone()[0] is False

    # Even the restricted runtime role must not reset a consumed quota window.
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM app.authenticate_api_token(%s)",
                        (hashlib.sha256(user_a["token"].encode("ascii")).hexdigest(),))
            assert cur.fetchone()
            try:
                cur.execute(
                    "UPDATE amboy_m1_quotas SET request_count=1 "
                    "WHERE organization_id=%s AND actor_user_id=%s",
                    (user_a["organization_id"], user_a["user_id"]),
                )
            except psycopg.errors.RaiseException:
                conn.rollback()
            else:
                raise AssertionError("Restricted role reset the hourly quota")

    with psycopg.connect(admin) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE api_access_tokens SET revoked_at=now() WHERE user_id=%s",
                        (user_a["user_id"],))
    status(client.post("/v1/amboy/turn", json=initial, headers=headers(user_a)), 401)
    print("PASS: AMBOY M1 opt-in, separate tenant identity, role boundary, privacy,"
          " atomic hourly quotas, idempotent receipts, immutable audit, revocation,"
          " and no model/tool/OneCall execution")


if __name__ == "__main__":
    main()
