"""Disposable PostgreSQL 16 integration, actual login-role RLS, durable idempotency and AES-GCM.

Always refused outside ephemeral GitHub Actions service meta_stage_ci. Absolutely
no real personal records or production database are accessed.
"""
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
import base64
import subprocess
import time
from hashlib import sha256
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import psycopg
from psycopg import sql
import pytest
from cryptography.exceptions import InvalidTag

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.disposable_meta_crm import (
    TENANTS, scoped_tenant, store_inspected_events, list_review_tasks,
    store_private_evidence, read_private_evidence, assign_review_agent,
    record_consent_evidence,
)
from app.synthetic_meta_lead_federation import inspect_signed_meta_event
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.disposable_crm_authorization import AuthorizedMetaCRM, ISSUER, AUDIENCE
from app.disposable_audit_verification import verify_tenant_audit
from app.disposable_meta_crm import derive_ephemeral_tenant_key


pytestmark = pytest.mark.skipif(
    not (os.getenv("GITHUB_ACTIONS") == "true" and
         os.getenv("META_CRM_STAGING_DISPOSABLE") == "yes" and
         os.getenv("META_CRM_DATABASE_NAME") == "meta_stage_ci"),
    reason="Intentionally executable only on disposable GitHub PostgreSQL CI service",
)
SECRET = b"synthetic-only-test-meta-webhook-secret"
MASTER = secrets.token_bytes(32)
SQL = ROOT / "database/disposable/p2_03s_meta_leads_staging.sql"
AUDIT_SQL = ROOT / "database/disposable/p2_03t_meta_audit.sql"


def envelope(platform, account, event_id):
    if platform == "FACEBOOK":
        return {"object": "page", "entry": [{"id": account, "changes": [
            {"field": "leadgen", "value": {"leadgen_id": event_id,
                "form_id": "SIM-FORM-ACADEMY", "page_id": account}}]}]}
    if platform == "INSTAGRAM":
        return {"object": "instagram", "entry": [{"id": account,
            "messaging": [{"message": {"mid": event_id}}]}]}
    return {"object": "whatsapp_business_account", "entry": [{"id": account,
        "changes": [{"field": "messages", "value": {"messages": [{"id": event_id}]}}]}]}


def inspected(platform, account, event_id, workspace):
    body = json.dumps(envelope(platform, account, event_id),
                      sort_keys=True, separators=(",", ":")).encode()
    signature = "sha256=" + hmac.new(SECRET, body, "sha256").hexdigest()
    return inspect_signed_meta_event(body, signature, SECRET,
                                     expected_workspace=workspace)


@pytest.fixture(scope="module")
def stage():
    # Do not even attempt to connect unless explicit CI-only gating is present.
    if os.getenv("GITHUB_ACTIONS") != "true":
        pytest.skip("Disposable CI runner only")
    assert os.environ["META_CRM_STAGING_DISPOSABLE"] == "yes"
    assert os.environ["META_CRM_DATABASE_NAME"] == "meta_stage_ci"
    admin_url = os.environ["META_CRM_ADMIN_DATABASE_URL"]
    admin = psycopg.connect(admin_url, autocommit=True)
    assert admin.execute("SELECT current_database()").fetchone()[0] == "meta_stage_ci"
    assert admin.execute("SELECT current_setting('is_superuser')").fetchone()[0] == "on"
    admin.execute("SET metaautomate.disposable = 'yes'")
    admin.execute(SQL.read_text(encoding="utf-8"))
    admin.execute(AUDIT_SQL.read_text(encoding="utf-8"))
    host = "127.0.0.1"
    roles = {
        "academy_demo": ("meta_stage_login_academy", secrets.token_urlsafe(24)),
        "bespoke_demo": ("meta_stage_login_bespoke", secrets.token_urlsafe(24)),
    }
    for ws, (name, password) in roles.items():
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS").format(sql.Identifier(name), sql.Literal(password)),
        )
        admin.execute("INSERT INTO meta_stage.login_tenants(login_role,tenant_id)"
                      " VALUES (%s,%s)", (name,TENANTS[ws]))
        for platform, account in [
            ("FACEBOOK", "SIM-PAGE-ACADEMY" if ws=="academy_demo" else "SIM-PAGE-BESPOKE"),
            ("INSTAGRAM", "SIM-IG-ACADEMY" if ws=="academy_demo" else "SIM-IG-BESPOKE"),
            ("WHATSAPP", "SIM-WABA-ACADEMY" if ws=="academy_demo" else "SIM-WABA-BESPOKE"),
        ]:
            admin.execute("INSERT INTO meta_stage.accounts(tenant_id,platform,account_ref)"
                          " VALUES (%s,%s,%s)", (TENANTS[ws],platform,account))
        role_id=sql.Identifier(name)
        for template in [
            "GRANT USAGE ON SCHEMA meta_stage TO {}",
            "GRANT EXECUTE ON FUNCTION meta_stage.session_tenant() TO {}",
            "GRANT SELECT ON meta_stage.accounts TO {}",
            "GRANT SELECT ON meta_stage.audit_events TO {}",
            "GRANT SELECT,INSERT ON meta_stage.events TO {}",
            "GRANT SELECT,INSERT ON meta_stage.private_evidence TO {}",
            "GRANT SELECT,INSERT ON meta_stage.consent_reviews TO {}",
            "GRANT SELECT,INSERT ON meta_stage.review_tasks TO {}",
            "GRANT UPDATE (state,agent_ref) ON meta_stage.review_tasks TO {}",
        ]:
            admin.execute(sql.SQL(template).format(role_id))
    def open_for(ws, database="meta_stage_ci"):
        assert database in ("meta_stage_ci", "meta_stage_restore_ci")
        name, password=roles[ws]
        c=psycopg.connect(dbname=database,host=host,port=5432,user=name,
                          password=password,autocommit=True)
        assert c.execute("SELECT session_user").fetchone()[0] == name
        return c
    yield admin, open_for
    admin.close()


def test_authenticated_role_session_isolation_and_untrusted_guc(stage):
    admin, open_for=stage
    with open_for("academy_demo") as a, open_for("bespoke_demo") as b:
        assert scoped_tenant(a, "academy_demo")==TENANTS["academy_demo"]
        assert scoped_tenant(b, "bespoke_demo")==TENANTS["bespoke_demo"]
        assert a.execute("SELECT count(*) FROM meta_stage.accounts").fetchone()[0] == 3
        assert b.execute("SELECT count(*) FROM meta_stage.accounts").fetchone()[0] == 3
        a.execute("SELECT set_config(\'app.tenant_id\', %s, false)", (str(TENANTS["bespoke_demo"]),))
        assert scoped_tenant(a,"academy_demo")==TENANTS["academy_demo"]
        with pytest.raises(SyntheticGrowthError):
            scoped_tenant(a,"bespoke_demo")
        with pytest.raises(psycopg.Error):
            a.execute("SELECT * FROM meta_stage.login_tenants")
        with pytest.raises(psycopg.Error):
            a.execute("INSERT INTO meta_stage.events "
                "(tenant_id,platform,account_ref,event_ref,payload_sha256,event_kind) "
                "VALUES (%s,'FACEBOOK','SIM-PAGE-BESPOKE','SIM-FB-EVIL-01',%s,'leadgen')",
                (TENANTS["bespoke_demo"],"a"*64))
        with pytest.raises(psycopg.Error):
            a.execute("TRUNCATE meta_stage.events")
        with pytest.raises(psycopg.Error):
            a.execute("SET ROLE meta_stage_login_bespoke")


def test_persisted_signed_facebook_ingest_dedup_and_changed_payload_rejected(stage):
    _,open_for=stage
    receipt=inspected("FACEBOOK","SIM-PAGE-ACADEMY","SIM-FB-PERSIST-01","academy_demo")
    with open_for("academy_demo") as a:
        assert store_inspected_events(a,"academy_demo",receipt)==1
        assert store_inspected_events(a,"academy_demo",receipt)==0
    # The second authenticated connection proves durable DB persistence, not in-memory dedupe.
    with open_for("academy_demo") as a:
        tasks=list_review_tasks(a,"academy_demo")
        assert len(tasks)==1 and tasks[0]["platform"]=="FACEBOOK"
        assert tasks[0]["state"]=="HUMAN_REVIEW_REQUIRED"
        forged=dict(receipt)
        forged["raw_body_sha256"]="f"*64
        with pytest.raises(SyntheticGrowthError):
            store_inspected_events(a,"academy_demo",forged)
    with open_for("bespoke_demo") as b:
        assert list_review_tasks(b,"bespoke_demo")==[]
        with pytest.raises(SyntheticGrowthError):
            store_inspected_events(b,"bespoke_demo",receipt)


def test_real_database_rejects_cross_tenant_leakage_even_using_known_ids(stage):
    _,open_for=stage
    receipt=inspected("INSTAGRAM","SIM-IG-BESPOKE","SIM-IG-PERSIST-01","bespoke_demo")
    with open_for("bespoke_demo") as b:
        assert store_inspected_events(b,"bespoke_demo",receipt)==1
    with open_for("academy_demo") as a:
        # DB role cannot see another account's rows regardless of SQL query.
        assert a.execute("SELECT count(*) FROM meta_stage.events WHERE platform='INSTAGRAM'").fetchone()[0]==0
        assert a.execute("SELECT count(*) FROM meta_stage.review_tasks WHERE event_ref='SIM-IG-PERSIST-01'").fetchone()[0]==0


def test_aes_gcm_evidence_survives_connection_and_blocks_cross_tenant_reads(stage):
    _,open_for=stage
    with open_for("academy_demo") as a:
        digest=store_private_evidence(a,"academy_demo",MASTER,"FACEBOOK",
                                      "SIM-PAGE-ACADEMY","SIM-FB-PERSIST-01",
                                      b"SIMULATED:training-inquiry")
        assert len(digest)==64
        row=a.execute("SELECT nonce,ciphertext FROM meta_stage.private_evidence").fetchone()
        assert b"training-inquiry" not in bytes(row[1])
        assert len(bytes(row[0]))==12
    with open_for("academy_demo") as a:
        assert read_private_evidence(a,"academy_demo",MASTER,"FACEBOOK",
                 "SIM-PAGE-ACADEMY","SIM-FB-PERSIST-01")==b"SIMULATED:training-inquiry"
        with pytest.raises(InvalidTag):
            read_private_evidence(a,"academy_demo",secrets.token_bytes(32),
                  "FACEBOOK","SIM-PAGE-ACADEMY","SIM-FB-PERSIST-01")
    with open_for("bespoke_demo") as b:
        assert b.execute("SELECT count(*) FROM meta_stage.private_evidence").fetchone()[0]==0
        with pytest.raises(SyntheticGrowthError):
            read_private_evidence(b,"academy_demo",MASTER,"FACEBOOK",
                   "SIM-PAGE-ACADEMY","SIM-FB-PERSIST-01")


def test_db_human_review_and_append_only_consent_revocation(stage):
    _,open_for=stage
    with open_for("academy_demo") as a:
        assert assign_review_agent(a,"academy_demo","FACEBOOK",
                                   "SIM-FB-PERSIST-01","SIM-AGENT-01")
        assert not assign_review_agent(a,"academy_demo","FACEBOOK",
                                       "SIM-FB-PERSIST-01","SIM-AGENT-01")
        record_consent_evidence(a,"academy_demo","FACEBOOK","SIM-FB-PERSIST-01",
                                "MARKETING","DOCUMENTED_EXAMPLE","SIM-EVID-01",
                                "SIM-AGENT-01")
        record_consent_evidence(a,"academy_demo","FACEBOOK","SIM-FB-PERSIST-01",
                                "MARKETING","REVOKED_EXAMPLE","SIM-EVID-02",
                                "SIM-AGENT-01")
        with pytest.raises(SyntheticGrowthError):
            record_consent_evidence(a,"academy_demo","FACEBOOK","SIM-FB-PERSIST-01",
                                    "MARKETING","DOCUMENTED_EXAMPLE","SIM-EVID-03",
                                    "SIM-AGENT-01")
        # Even raw direct inserts are refused by the PostgreSQL trigger.
        with pytest.raises(psycopg.Error):
            a.execute("INSERT INTO meta_stage.consent_reviews "
                "(tenant_id,platform,account_ref,event_ref,purpose,reviewed_state,evidence_ref,actor_ref)"
                " VALUES (%s,'FACEBOOK','SIM-PAGE-ACADEMY','SIM-FB-PERSIST-01',"
                "'MARKETING','DOCUMENTED_EXAMPLE','SIM-EVID-04','SIM-AGENT-01')",
                (TENANTS["academy_demo"],))
        with pytest.raises(psycopg.Error):
            a.execute("UPDATE meta_stage.consent_reviews SET reviewed_state='DOCUMENTED_EXAMPLE'")
        with pytest.raises(psycopg.Error):
            a.execute("UPDATE meta_stage.review_tasks SET outbound_enabled=true")
        assert all(not x["outbound_enabled"] for x in list_review_tasks(a,"academy_demo"))


def test_permissions_and_real_authorization_remain_off(stage):
    admin,open_for=stage
    with open_for("academy_demo") as a:
        assert a.execute("SELECT bool_and(provider_verified = false) FROM meta_stage.accounts").fetchone()[0]
        assert a.execute("SELECT count(*) FROM meta_stage.consent_reviews").fetchone()[0]==2
        assert a.execute("SELECT count(*) FROM meta_stage.private_evidence").fetchone()[0]==1
    assert admin.execute(
        "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'meta_stage_login_%'"
        " AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole)"
    ).fetchone()[0]==0


# P2-03t tests: exercise working Ed25519 application checks against the
# independently authenticated, restricted PostgreSQL login.
def _actor_token(private_key, role="tenant_admin", workspace="academy_demo",
                 actor="SIM-ACTOR-01", expires_offset=120):
    now = int(time.time())
    claims = {
        "version": 1, "issuer": ISSUER, "audience": AUDIENCE,
        "workspace": workspace, "actor_ref": actor, "role": role,
        "issued_at": now-5, "expires_at": now+expires_offset,
        "token_ref": "SIM-TOKEN-STAGE-01",
    }
    payload=json.dumps(claims,separators=(",",":"),sort_keys=True).encode()
    encoded=base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    body="v1."+encoded
    signature=base64.urlsafe_b64encode(private_key.sign(body.encode())).rstrip(b"=").decode()
    return body+"."+signature


def test_application_actor_roles_deny_cross_tenant_and_privilege_escalation(stage):
    _,open_for=stage
    private=Ed25519PrivateKey.generate()
    key=private.public_key()
    with open_for("academy_demo") as a, open_for("bespoke_demo") as b:
        auditor=AuthorizedMetaCRM(a,_actor_token(private,"auditor"),key)
        assert isinstance(auditor.tasks(),list)
        assert auditor.audit_report()["entry_count"]>=1
        with pytest.raises(SyntheticGrowthError):
            auditor.assign("FACEBOOK","SIM-FB-PERSIST-01","SIM-AGENT-01")
        with pytest.raises(SyntheticGrowthError):
            auditor.protect_note(MASTER,"FACEBOOK","SIM-PAGE-ACADEMY",
                                 "SIM-FB-PERSIST-01",b"SIMULATED:prohibited")
        reviewer=AuthorizedMetaCRM(a,_actor_token(private,"reviewer"),key)
        assert isinstance(reviewer.tasks(),list)
        with pytest.raises(SyntheticGrowthError):
            reviewer.audit_report()
        with pytest.raises(SyntheticGrowthError):
            reviewer.review_consent("FACEBOOK","SIM-FB-PERSIST-01","MARKETING",
                                    "UNVERIFIED","SIM-EVID-NEW-01","SIM-AGENT-01")
        with pytest.raises(SyntheticGrowthError):
            AuthorizedMetaCRM(b,_actor_token(private,"tenant_admin",
                                                "academy_demo"),key)
        with pytest.raises(SyntheticGrowthError):
            AuthorizedMetaCRM(a,_actor_token(private,"tenant_admin",
                                                "bespoke_demo"),key)
        with pytest.raises(SyntheticGrowthError):
            AuthorizedMetaCRM(a,_actor_token(private,expires_offset=-1),key)


def test_only_authorized_signed_quality_checked_ingest_and_consent(stage):
    _,open_for=stage
    private=Ed25519PrivateKey.generate()
    with open_for("academy_demo") as a:
        admin=AuthorizedMetaCRM(a,_actor_token(private),private.public_key())
        event=envelope("FACEBOOK","SIM-PAGE-ACADEMY","SIM-FB-AUTH-01")
        raw=json.dumps(event,separators=(",",":"),sort_keys=True).encode()
        sig="sha256="+hmac.new(SECRET,raw,"sha256").hexdigest()
        assert admin.ingest_signed(raw,sig,SECRET)==1
        assert admin.ingest_signed(raw,sig,SECRET)==0
        assert admin.assign("FACEBOOK","SIM-FB-AUTH-01","SIM-AGENT-01")
        admin.review_consent("FACEBOOK","SIM-FB-AUTH-01","SERVICE",
                             "UNVERIFIED","SIM-EVID-AUTH-01","SIM-AGENT-01")
        with pytest.raises(SyntheticGrowthError):
            admin.review_consent("FACEBOOK","SIM-FB-AUTH-01","MARKETING",
                                 "DOCUMENTED_EXAMPLE","SIM-EVID-AUTH-02",
                                 "SIM-AGENT-99")
        with pytest.raises(SyntheticGrowthError):
            admin.ingest_signed(raw+b" ",sig,SECRET)
        assert any(x["event_ref"]=="SIM-FB-AUTH-01" for x in admin.tasks())
        assert admin.audit_report()["entry_count"]>=5


def test_hash_chain_commits_atomically_and_cannot_be_changed_by_login(stage):
    _,open_for=stage
    with open_for("academy_demo") as a, open_for("bespoke_demo") as b:
        report=verify_tenant_audit(a,"academy_demo")
        other=verify_tenant_audit(b,"bespoke_demo")
        assert report["entry_count"]>=7 and other["entry_count"]>=3
        assert report["head_sha256"]!=other["head_sha256"]
        assert verify_tenant_audit(a,"academy_demo",
                                   trusted_head=report["head_sha256"])==report
        with pytest.raises(SyntheticGrowthError):
            verify_tenant_audit(a,"academy_demo",trusted_head="f"*64)
        with pytest.raises(psycopg.Error):
            a.execute("UPDATE meta_stage.audit_events SET entry_sha256=%s",
                      ("0"*64,))
        with pytest.raises(psycopg.Error):
            a.execute("DELETE FROM meta_stage.audit_events")
        with pytest.raises(psycopg.Error):
            a.execute("INSERT INTO meta_stage.audit_events "
                      "(tenant_id,sequence_number,source_login,payload,"
                      "previous_sha256,entry_sha256) "
                      "VALUES (%s,9001,'fake','{}',%s,%s)",
                      (TENANTS["academy_demo"],"0"*64,"0"*64))
        # Attempting to read the other tenant's sequence by its UUID reveals nothing.
        assert a.execute(
            "SELECT count(*) FROM meta_stage.audit_events WHERE tenant_id=%s",
            (TENANTS["bespoke_demo"],),
        ).fetchone()[0]==0


def test_z_postgres_dump_restore_preserves_tenant_audit_and_encrypted_evidence(stage):
    """Recovery drill, synthetic only; archive not retained or uploaded."""
    admin,open_for=stage
    assert os.environ["GITHUB_ACTIONS"]=="true"
    assert os.environ["META_CRM_STAGING_DISPOSABLE"]=="yes"
    assert admin.execute("SELECT current_database()").fetchone()[0]=="meta_stage_ci"
    with open_for("academy_demo") as a, open_for("bespoke_demo") as b:
        before={
            "academy_demo":verify_tenant_audit(a,"academy_demo"),
            "bespoke_demo":verify_tenant_audit(b,"bespoke_demo"),
        }
        academy_events=a.execute("SELECT count(*) FROM meta_stage.events").fetchone()[0]
        bespoke_events=b.execute("SELECT count(*) FROM meta_stage.events").fetchone()[0]
    # Service container uses the already-downloaded official postgres:16 image.
    # No backup, secret, or database connection goes to external infrastructure.
    base=["docker","run","--rm","--network","host",
          "-e","PGPASSWORD=disposable_only_ci_password","postgres:16"]
    dump=subprocess.run(
        base+["pg_dump","-h","127.0.0.1","-U","meta_stage_admin",
              "-d","meta_stage_ci","--format=custom","--no-owner"],
        check=True,capture_output=True,timeout=100).stdout
    assert dump.startswith(b"PGDMP") and len(dump)>1000
    assert b"SIMULATED:training-inquiry" not in dump
    assert admin.execute(
        "SELECT 1 FROM pg_database WHERE datname='meta_stage_restore_ci'"
    ).fetchone() is None
    admin.execute("CREATE DATABASE meta_stage_restore_ci")
    subprocess.run(
        base+["pg_restore","-h","127.0.0.1","-U","meta_stage_admin",
              "-d","meta_stage_restore_ci","--no-owner","--exit-on-error"],
        input=dump,capture_output=True,check=True,timeout=100)
    # Authenticate the same two LOGIN roles to a *different*, recovered DB.
    # Verify that the restore did not weaken RLS, grant public access or rewrite
    # any committed audit sequence. Independently compare prior trusted heads.
    with open_for("academy_demo",database="meta_stage_restore_ci") as a, \
         open_for("bespoke_demo",database="meta_stage_restore_ci") as b:
        for ws,conn,count in (
            ("academy_demo",a,academy_events),
            ("bespoke_demo",b,bespoke_events),
        ):
            assert conn.execute(
                "SELECT count(*) FROM meta_stage.events"
            ).fetchone()[0]==count
            rows=conn.execute(
                "SELECT sequence_number,payload::text,previous_sha256,entry_sha256 "
                "FROM meta_stage.audit_events ORDER BY sequence_number"
            ).fetchall()
            predecessor="0"*64
            for seq,payload,prev,head in rows:
                assert seq>=1 and seq==rows.index((seq,payload,prev,head))+1
                assert prev==predecessor
                assert sha256((prev+":"+payload).encode("utf-8")).hexdigest()==head
                predecessor=head
            assert len(rows)==before[ws]["entry_count"]
            assert predecessor==before[ws]["head_sha256"]
        assert a.execute(
            "SELECT count(*) FROM meta_stage.events WHERE tenant_id=%s",
            (TENANTS["bespoke_demo"],),
        ).fetchone()[0]==0
        assert b.execute(
            "SELECT count(*) FROM meta_stage.audit_events WHERE tenant_id=%s",
            (TENANTS["academy_demo"],),
        ).fetchone()[0]==0
        row=a.execute(
            "SELECT nonce,ciphertext FROM meta_stage.private_evidence "
            "WHERE event_ref='SIM-FB-PERSIST-01'"
        ).fetchone()
        assert row is not None
        aad=(str(TENANTS["academy_demo"]) +
             "|FACEBOOK|SIM-PAGE-ACADEMY|SIM-FB-PERSIST-01").encode()
        recovered=AESGCM(derive_ephemeral_tenant_key(
            MASTER,TENANTS["academy_demo"])).decrypt(
                bytes(row[0]),bytes(row[1]),aad)
        assert recovered==b"SIMULATED:training-inquiry"
        with pytest.raises(psycopg.Error):
            a.execute("TRUNCATE meta_stage.audit_events")
