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



def require_context(cursor, expected_org=None, expected_user=None):
    """Inspect real transaction-local tenant settings in ephemeral PostgreSQL.

    A rejected identity must leave neither the org nor the user context set,
    even after a previously successful authentication in the same transaction.
    """
    cursor.execute(
        "SELECT current_setting('app.organization_id', true),"
        " current_setting('app.user_id', true)"
    )
    actual_org, actual_user = cursor.fetchone()
    if expected_org is None:
        require(actual_org in (None, "") and actual_user in (None, ""),
                "Rejected identity left a transaction-scoped tenant context")
    else:
        require((actual_org, actual_user)
                == (str(expected_org), str(expected_user)),
                "Authenticated identity has an incorrect tenant context")

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
            require(identity and identity[0]==org and identity[1]==user
                    and identity[2]=="OWNER", "Valid OIDC tenant binding failed")
            require_context(c, org, user)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone()[0]==org, "Valid OIDC session failed")
            require_context(c, org, user)

            # Every denial starts after a successful tenant binding in the
            # SAME transaction. A stale app.organization_id would be unsafe.
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,hashlib.sha256(b"bad-csrf").hexdigest()))
            require(c.fetchone() is None, "Wrong CSRF was authenticated")
            require_context(c)

            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (ISSUER,hashlib.sha256(b"unapproved-subject").hexdigest(),
                       hashlib.sha256(b"unused-session").hexdigest(),csrf_hash))
            require(c.fetchone() is None, "Unprovisioned subject was admitted")
            require_context(c)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      ("0"*64, csrf_hash))
            require(c.fetchone() is None, "Unknown session was authenticated")
            require_context(c)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone()[0]==org, "Valid session did not recover after denial")
            require_context(c, org, user)

    # Real PostgreSQL membership revocation/reinstatement: disposable CI only.
    with psycopg.connect(admin) as conn:
        with conn.cursor() as c:
            c.execute("SELECT app.set_context(%s,%s)", (org,user))
            c.execute("UPDATE organization_memberships SET status='SUSPENDED' "
                      "WHERE organization_id=%s AND user_id=%s", (org,user))
            require(c.rowcount==1, "Synthetic membership suspension failed")
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone() is None, "Suspended membership retained access")
            require_context(c)
            # Creation with a known signed and provisioned subject must also fail.
            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (ISSUER,DIGEST,hashlib.sha256(b"suspended-attempt").hexdigest(),
                       csrf_hash))
            require(c.fetchone() is None, "Suspended member created a session")
            require_context(c)

    with psycopg.connect(admin) as conn:
        with conn.cursor() as c:
            c.execute("SELECT app.set_context(%s,%s)", (org,user))
            c.execute("UPDATE organization_memberships SET status='ACTIVE' "
                      "WHERE organization_id=%s AND user_id=%s", (org,user))
            require(c.rowcount==1, "Synthetic membership restoration failed")

    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone()[0]==org, "Restored member did not recover access")
            require_context(c, org, user)
            c.execute("SELECT app.revoke_workspace_session(%s)", (session_hash,))
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone() is None, "Revoked session retained access")
            require_context(c)

    # Separate valid second session proves identity revocation independently of
    # the explicit session revocation tested above.
    second_hash=hashlib.sha256(secrets.token_bytes(36)).hexdigest()
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (ISSUER,DIGEST,second_hash,csrf_hash))
            require(c.fetchone()[0]==org, "Second disposable identity admission failed")
            require_context(c, org, user)

    with psycopg.connect(admin) as conn:
        with conn.cursor() as c:
            c.execute("UPDATE oidc_identities SET status='REVOKED',revoked_at=now() WHERE id=%s",
                      (identity_id,))
            require(c.rowcount==1, "Synthetic identity revocation failed")
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (second_hash,csrf_hash))
            require(c.fetchone() is None, "Revoked OIDC identity retained access")
            require_context(c)

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
    print("PASS: disposable OIDC identity, CSRF denial, tenant-context clearing, membership/session/identity revocation and private startup checks")


if __name__ == "__main__":
    main()
