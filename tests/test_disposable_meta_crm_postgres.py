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

pytestmark = pytest.mark.skipif(
    not (os.getenv("GITHUB_ACTIONS") == "true" and
         os.getenv("META_CRM_STAGING_DISPOSABLE") == "yes" and
         os.getenv("META_CRM_DATABASE_NAME") == "meta_stage_ci"),
    reason="Intentionally executable only on disposable GitHub PostgreSQL CI service",
)
SECRET = b"synthetic-only-test-meta-webhook-secret"
MASTER = secrets.token_bytes(32)
SQL = ROOT / "database/disposable/p2_03s_meta_leads_staging.sql"


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
            "GRANT SELECT,INSERT ON meta_stage.events TO {}",
            "GRANT SELECT,INSERT ON meta_stage.private_evidence TO {}",
            "GRANT SELECT,INSERT ON meta_stage.consent_reviews TO {}",
            "GRANT SELECT,INSERT ON meta_stage.review_tasks TO {}",
            "GRANT UPDATE (state,agent_ref) ON meta_stage.review_tasks TO {}",
        ]:
            admin.execute(sql.SQL(template).format(role_id))
    def open_for(ws):
        name, password=roles[ws]
        c=psycopg.connect(dbname="meta_stage_ci",host=host,port=5432,user=name,
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
