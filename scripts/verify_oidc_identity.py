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

from oidc_ci_database_guard import require_ci_database_urls


ISSUER = "https://identity-ci.example.invalid/tenant"
SECOND_ISSUER = ISSUER + "/independent"
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
    # Check target before opening any connection or provisioning fixtures.
    require_ci_database_urls(admin, runtime)
    token="opaque-session-"+secrets.token_urlsafe(36)
    csrf="csrf-"+secrets.token_urlsafe(36)
    session_hash=hashlib.sha256(token.encode()).hexdigest()
    csrf_hash=hashlib.sha256(csrf.encode()).hexdigest()
    # A second wholly fictional tenant proves that CSRF/session hashes
    # cannot be swapped across provisioned organization identities.
    other_subject="verified-idp-other-"+uuid4().hex
    other_digest=hashlib.sha256(other_subject.encode()).hexdigest()
    other_session_hash=hashlib.sha256(secrets.token_bytes(36)).hexdigest()
    other_csrf_hash=hashlib.sha256(secrets.token_bytes(36)).hexdigest()
    issuer_session_hash=hashlib.sha256(secrets.token_bytes(36)).hexdigest()
    issuer_csrf_hash=hashlib.sha256(secrets.token_bytes(36)).hexdigest()

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
            c.execute(
                "INSERT INTO organizations(slug,name) "
                "VALUES(%s,'CI OIDC Second Organization') RETURNING id",
                ("ci-oidc-other-"+uuid4().hex,),
            )
            other_org=c.fetchone()[0]
            c.execute(
                "INSERT INTO users(email,display_name) "
                "VALUES(%s,'OIDC CI Second Member') RETURNING id",
                ("ci-oidc-other-"+uuid4().hex+"@example.invalid",),
            )
            other_user=c.fetchone()[0]
            c.execute("SELECT app.set_context(%s,%s)", (other_org,other_user))
            c.execute(
                "INSERT INTO organization_memberships(organization_id,user_id,role,status) "
                "VALUES(%s,%s,'OPERATOR','ACTIVE')",
                (other_org,other_user),
            )
            c.execute(
                "INSERT INTO oidc_identities(organization_id,user_id,issuer,subject_sha256) "
                "VALUES(%s,%s,%s,%s)",
                (other_org,other_user,ISSUER,other_digest),
            )
            # Same subject hash, distinct trusted issuer, distinct tenant.
            # Issuer+subject must be resolved together, never subject alone.
            c.execute(
                "INSERT INTO oidc_identities(organization_id,user_id,issuer,subject_sha256) "
                "VALUES(%s,%s,%s,%s)",
                (other_org,other_user,SECOND_ISSUER,DIGEST),
            )

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

            # NULL digests must fail as ordinary denials before the INSERT.
            # PostgreSQL three-valued OR would otherwise skip the validation
            # branch and raise a NOT NULL error rather than return no principal.
            # Rebind the valid identity after every denial in this transaction.
            for label, subject_digest, session_digest, csrf_digest in (
                ("subject", None, hashlib.sha256(b"unused-null-subject").hexdigest(), csrf_hash),
                ("session", DIGEST, None, csrf_hash),
                ("csrf", DIGEST, hashlib.sha256(b"unused-null-csrf").hexdigest(), None),
            ):
                c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                          (ISSUER, subject_digest, session_digest, csrf_digest))
                require(c.fetchone() is None, f"NULL OIDC {label} digest was admitted")
                require_context(c)
                c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                          (session_hash, csrf_hash))
                recovered = c.fetchone()
                require(recovered is not None and recovered[0] == org,
                        f"Valid session failed after NULL OIDC {label} denial")
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

    # Validate real session separation across two fictional organizations.
    # A successful A session followed by B admission must replace, not mix,
    # tenant context, and neither tenant may replay the other's CSRF hash.
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (ISSUER,other_digest,other_session_hash,other_csrf_hash))
            other_identity=c.fetchone()
            require(other_identity
                    and other_identity[0]==other_org
                    and other_identity[1]==other_user
                    and other_identity[2]=="OPERATOR",
                    "Second tenant must resolve only its own principal")
            require_context(c, other_org, other_user)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,other_csrf_hash))
            require(c.fetchone() is None, "Tenant B CSRF unlocked tenant A")
            require_context(c)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (other_session_hash,csrf_hash))
            require(c.fetchone() is None, "Tenant A CSRF unlocked tenant B")
            require_context(c)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone()[0]==org, "Tenant A session binding drifted")
            require_context(c, org, user)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (other_session_hash,other_csrf_hash))
            require(c.fetchone()[0]==other_org, "Tenant B session binding drifted")
            require_context(c, other_org, other_user)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone()[0]==org, "Tenant A could not be reselected")
            require_context(c, org, user)

            # Revocation is a privileged mutation: tenant A's authenticated
            # context must not be able to revoke tenant B's valid session.
            c.execute("SELECT app.revoke_workspace_session(%s)",
                      (other_session_hash,))
            require_context(c, org, user)
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (other_session_hash,other_csrf_hash))
            require(c.fetchone()[0]==other_org,
                    "Tenant A revoked tenant B's session")
            require_context(c, other_org, other_user)

    # A new restricted connection has no authenticated tenant context.
    # Supplying a known synthetic hash alone must never revoke a session.
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            require_context(c)
            c.execute("SELECT app.revoke_workspace_session(%s)",
                      (other_session_hash,))
            require_context(c)
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (other_session_hash,other_csrf_hash))
            require(c.fetchone()[0]==other_org,
                    "Unauthenticated runtime revoked tenant B's session")
            require_context(c, other_org, other_user)

    # The same opaque subject can exist under a different trusted issuer.
    # Only the full (issuer, subject) tuple identifies the intended tenant.
    with psycopg.connect(runtime) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (SECOND_ISSUER,DIGEST,issuer_session_hash,issuer_csrf_hash))
            cross_issuer_identity=c.fetchone()
            require(cross_issuer_identity
                    and cross_issuer_identity[0]==other_org
                    and cross_issuer_identity[1]==other_user
                    and cross_issuer_identity[2]=="OPERATOR",
                    "Same subject from second issuer resolved wrong tenant")
            require_context(c, other_org, other_user)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (issuer_session_hash,issuer_csrf_hash))
            require(c.fetchone()[0]==other_org,
                    "Second issuer session did not retain tenant B binding")
            require_context(c, other_org, other_user)

            c.execute("SELECT * FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                      (SECOND_ISSUER,other_digest,
                       hashlib.sha256(b"unknown-issuer-subject").hexdigest(),
                       issuer_csrf_hash))
            require(c.fetchone() is None,
                    "Issuer confusion admitted an unprovisioned subject")
            require_context(c)

            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (session_hash,csrf_hash))
            require(c.fetchone()[0]==org,
                    "Cross-issuer denial changed original tenant binding")
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
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (other_session_hash,other_csrf_hash))
            require(c.fetchone()[0]==other_org,
                    "Revoking tenant A identity unexpectedly revoked tenant B")
            require_context(c, other_org, other_user)
            c.execute("SELECT * FROM app.authenticate_workspace_session(%s,%s)",
                      (issuer_session_hash,issuer_csrf_hash))
            require(c.fetchone()[0]==other_org,
                    "Revoking issuer A identity invalidated issuer B identity")
            require_context(c, other_org, other_user)

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
    print("PASS: disposable two-tenant, cross-issuer OIDC isolation, CSRF denial, context clearing, membership/session/identity revocation and private startup checks")


if __name__ == "__main__":
    main()
