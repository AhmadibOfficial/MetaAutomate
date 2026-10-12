#!/usr/bin/env python3
"""Explicit local bootstrap; secrets remain in ignored owner-readable files."""
import hashlib
import os
from pathlib import Path
import secrets
from urllib.parse import quote, urlsplit, urlunsplit
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]
ENV=ROOT/".env"
KEY=ROOT/".workspace-access-key"

def private_write(path, content):
    if path.is_symlink():
        raise RuntimeError("Refusing to write secret via symlink")
    tmp=path.with_name(path.name+".tmp")
    with open(tmp,"w",encoding="utf-8",opener=lambda p,f:os.open(p,f,0o600)) as out:
        out.write(content)
        out.flush()
        os.fsync(out.fileno())
    os.chmod(tmp,0o600)
    os.replace(tmp,path)
    os.chmod(path,0o600)

def main():
    admin_url=os.environ["DATABASE_URL"]
    parts=urlsplit(admin_url)
    if parts.hostname not in ("postgres","localhost","127.0.0.1") or parts.path!="/metaautomate":
        raise RuntimeError("Must use local MetaAutomate development database")
    password=secrets.token_urlsafe(36)
    access_key="mat_dev_"+secrets.token_urlsafe(32)
    with psycopg.connect(admin_url,connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.workspace_sessions')")
            if cur.fetchone()[0] is None:
                raise RuntimeError("Run migration 010 first")
            cur.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier("metaautomate_runtime"),sql.Literal(password)))
            cur.execute(
                "INSERT INTO organizations(slug,name) "
                "VALUES('metaautomate-local','MetaAutomate Local Development') "
                "ON CONFLICT(slug) DO UPDATE SET name=EXCLUDED.name RETURNING id")
            org=cur.fetchone()[0]
            cur.execute(
                "INSERT INTO users(email,display_name) "
                "VALUES('developer@metaautomate.local','Local Workspace Owner') "
                "ON CONFLICT(email) DO UPDATE SET display_name=EXCLUDED.display_name RETURNING id")
            user=cur.fetchone()[0]
            cur.execute("SELECT app.set_context(%s,%s)",(org,user))
            cur.execute(
                "INSERT INTO organization_memberships(organization_id,user_id,role,status) "
                "VALUES(%s,%s,'OWNER','ACTIVE') "
                "ON CONFLICT(organization_id,user_id) DO UPDATE SET role='OWNER',status='ACTIVE'",
                (org,user))
            cur.execute(
                "UPDATE api_access_tokens SET revoked_at=now() "
                "WHERE organization_id=%s AND user_id=%s AND label='local-workspace' "
                "AND revoked_at IS NULL",(org,user))
            cur.execute(
                "INSERT INTO api_access_tokens "
                "(organization_id,user_id,token_sha256,label,expires_at) "
                "VALUES(%s,%s,%s,'local-workspace',now()+interval '7 days')",
                (org,user,hashlib.sha256(access_key.encode("ascii")).hexdigest()))
    netloc="metaautomate_runtime:"+quote(password,safe="")+"@"+parts.hostname
    if parts.port: netloc+=":"+str(parts.port)
    runtime_url=urlunsplit(parts._replace(netloc=netloc))
    original=ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    lines=[line for line in original.splitlines()
           if not line.startswith(("APP_DATABASE_URL=","WORKSPACE_ORIGIN=","WORKSPACE_COOKIE_SECURE="))]
    lines.extend(["APP_DATABASE_URL="+runtime_url,
                  "WORKSPACE_ORIGIN=http://127.0.0.1:8000",
                  "WORKSPACE_COOKIE_SECURE=0"])
    private_write(ENV,"\n".join(lines)+"\n")
    private_write(KEY,access_key+"\n")
    print("PASS: local owner and restricted runtime identity created")
    print("Access key saved in .workspace-access-key; not printed")
    print("Restricted credentials saved in .env; not printed")
    print("Development key expires after seven days; repeating setup rotates it")

if __name__=="__main__":
    main()
