#!/usr/bin/env python3
"""Idempotent isolated contributor demo bootstrap, run only in its one-off container."""
import hashlib
import os
from urllib.parse import urlsplit
from psycopg import connect, sql


def main():
    admin_url=os.environ["DATABASE_URL"]
    parts=urlsplit(admin_url)
    if parts.hostname!="postgres" or parts.path!="/metaautomate":
        raise RuntimeError("Expected isolated demo PostgreSQL service")
    password=os.environ["DEMO_RUNTIME_PASSWORD"]
    raw_token=os.environ["DEMO_ACCESS_KEY"]
    if not raw_token.startswith("mat_dev_") or len(raw_token)<35:
        raise RuntimeError("Invalid development demo token")
    if len(password)<30 or not all(c in "0123456789abcdef" for c in password):
        raise RuntimeError("Invalid randomly generated demo database password")
    digest=hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    with connect(admin_url,connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.workspace_sessions') IS NOT NULL")
            if not cur.fetchone()[0]:
                raise RuntimeError("Demo database migrations 001-010 must be installed first")
            cur.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier("metaautomate_runtime"),sql.Literal(password)))
            cur.execute(
                "INSERT INTO organizations(slug,name) "
                "VALUES('metaautomate-oss-demo','MetaAutomate Open Source Demo') "
                "ON CONFLICT(slug) DO UPDATE SET name=EXCLUDED.name RETURNING id"
            )
            org=cur.fetchone()[0]
            cur.execute(
                "INSERT INTO users(email,display_name) "
                "VALUES('oss-demo@metaautomate.invalid','Open Source Demo Owner') "
                "ON CONFLICT(email) DO UPDATE SET display_name=EXCLUDED.display_name RETURNING id"
            )
            user=cur.fetchone()[0]
            cur.execute("SELECT app.set_context(%s,%s)",(org,user))
            cur.execute(
                "INSERT INTO organization_memberships(organization_id,user_id,role,status) "
                "VALUES(%s,%s,'OWNER','ACTIVE') "
                "ON CONFLICT(organization_id,user_id) "
                "DO UPDATE SET role='OWNER',status='ACTIVE'",(org,user)
            )
            cur.execute(
                "SELECT organization_id=%s AND user_id=%s AND revoked_at IS NULL "
                "AND expires_at>now() FROM api_access_tokens WHERE token_sha256=%s",
                (org,user,digest)
            )
            existing=cur.fetchone()
            if existing is None:
                cur.execute(
                    "SELECT count(*) FROM api_access_tokens "
                    "WHERE organization_id=%s AND user_id=%s AND label='oss-demo-local'",
                    (org,user))
                if cur.fetchone()[0]:
                    raise RuntimeError(
                        "A previous demo credential exists. Refusing implicit rotation. "
                        "Consult docs/OPEN_SOURCE.md for safe reset."
                    )
                cur.execute(
                    "INSERT INTO api_access_tokens "
                    "(organization_id,user_id,token_sha256,label,expires_at) "
                    "VALUES(%s,%s,%s,'oss-demo-local',now()+interval '7 days')",
                    (org,user,digest)
                )
            elif not existing[0]:
                raise RuntimeError("Existing demo token expired/revoked or mismatched; not reactivated")
    print("PASS: isolated demo tenant, restricted SQL role and planning-only access initialized")


if __name__=="__main__":
    main()
