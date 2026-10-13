#!/usr/bin/env python3
"""Ephemeral CI: optional private OIDC mapping and mode gates (no real IdP)."""
import hashlib
import os
import secrets
import subprocess
import sys
from uuid import uuid4
from pathlib import Path

import psycopg


ISSUER = "https://identity-ci.example.invalid/tenant"
SUBJECT = "verified-idp-subject-" + uuid4().hex
DIGEST = hashlib.sha256(SUBJECT.encode()).hexdigest()


def require(status, message):
    if not status:
        raise AssertionError(message)


def subprocess_config_check(env, should_start: bool):
    result = subprocess.run(
        [sys.executable, "-c",
         "from fastapi.testclient import TestClient; from app.main import app; "
         "client=TestClient(app);"
         "assert client.get('/v1/workspace/config').json()['mode']=='oidc';"
         "assert client.get('/v1/capabilities').status_code==404;"
         "assert client.get('/v1/objectives/preview').status_code==404;"
         "assert client.post('/v1/workspace/login',json={'access_key':'mat_dev_'+'X'*38}).status_code==404"],
        env=env, capture_output=True, text=True, timeout=20,
    )
    if should_start:
        assert result.returncode == 0, result.stderr[-1700:]
    else:
        assert result.returncode != 0, "OIDC mode must reject unsafe startup configuration"


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("OIDC integration tests require an ephemeral GitHub CI PostgreSQL service")
    admin=os.environ["DATABASE_URL"]
    runtime=os.environ["APP_DATABASE_URL"]
    token="opaque-session-"+secrets.token_urlsafe(36)
    csrf="csrf-"+secrets.token_urlsafe(36)
    session_hash=hashlib.sha256(token.encode()).hexdigest()
    csrf_hash=hashlib.sha256(csrf.encode()).hexdigest()

    with psycopg.connect(admin) as conn:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO organizations(slug,name) VALUES(%s,'CI OIDC Organization') RETURNING id",
                ("ci-oidc-"+uuid4().hex,),
            )
            org=c.fetchone()[0]
            c.execute(
                "INSERT INTO users(email,display_name) VALUES(%s,'OIDC CI Member') RETURNING id",
                ("ci-oidc-"+uuid4().hex+"@example.invalid",),
            )
            user=c.fetchone()[0]
            c.execute("SELECT app.set_context(%s,%s)",(org,user))
            c.execute(
                "INSERT INTO organization_memberships(organization_id,user_id,role,status) "
                "VALUES(%s,%s,'OWNER','ACTIVE')",(org,user),
            )
            c.execute(
                "INSERT INTO oidc_identities(organization_id,user_id,issuer,subject_sha256) "
                "VALUES(%s,%s,%s,%s) RETURNING id",(org,user,ISSUER,DIGEST),
            )
            identity_id=c.fetchone()[0]

    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            try:
                c.execute("SELECT subject_sha256 FROM oidc_identities LIMIT 1")
                raise AssertionError("Restricted role must not read identity directory")
            except psycopg.errors.InsufficientPrivilege:
                conn.rollback()

    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (ISSUER,DIGEST,session_hash,csrf_hash))
            identity=c.fetchone()
            assert identity and identity[0]==org and identity[1]==user and identity[2]=="OWNER"
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            assert c.fetchone()[0]==org
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,hashlib.sha256(b"bad-csrf").hexdigest()))
            assert c.fetchone() is None
            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (ISSUER,hashlib.sha256(b"unapproved-subject").hexdigest(),
                       hashlib.sha256(b"unused-session").hexdigest(),csrf_hash))
            assert c.fetchone() is None

    with psycopg.connect(admin) as conn:
        with conn.cursor() as c:
            c.execute("UPDATE oidc_identities SET status='REVOKED',revoked_at=now() WHERE id=%s",
                      (identity_id,))
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            assert c.fetchone() is None

    env=os.environ.copy()
    env.pop("DATABASE_URL",None)
    env.update({
        "WORKSPACE_AUTH_MODE":"oidc",
        "WORKSPACE_ORIGIN":"https://metaautomate-private.example.ts.net",
        "WORKSPACE_COOKIE_SECURE":"1",
        "OIDC_ISSUER":ISSUER,
        "OIDC_CLIENT_ID":"ci-client",
        "OIDC_CLIENT_SECRET":"ci-client-secret",
        "OIDC_REDIRECT_URI":"https://metaautomate-private.example.ts.net/v1/workspace/oidc/callback",
        "OIDC_STATE_SECRET":"ci-test-state-"+"X"*70,
        "APP_DATABASE_URL":runtime,
    })
    subprocess_config_check(env,True)
    broken=env.copy()
    broken.pop("OIDC_STATE_SECRET",None)
    subprocess_config_check(broken,False)
    broken=env.copy()
    broken["WORKSPACE_COOKIE_SECURE"]="0"
    subprocess_config_check(broken,False)
    broken=env.copy()
    broken["DATABASE_URL"]=admin
    subprocess_config_check(broken,False)
    print("PASS: OIDC tenant mapping, restricted grants, CSRF, revocation, SSO-only mode and fail-closed startup")


if __name__ == "__main__":
    main()
