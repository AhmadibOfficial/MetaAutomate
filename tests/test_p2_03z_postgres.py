"""P2-03z: actual PostgreSQL16 + RLS integration, all tenant data fictional.

Runs only in ephemeral CI with dedicated DATABASE_URL and APP_DATABASE_URL.
Does not use the owner's database, permanent staging or any customer records.
"""
import os
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
import pytest
from fastapi import HTTPException

from app.authn import Principal,TenantSession
# These integration tests run only in the dedicated, freshly migrated CI instance.
# Global unit-test runs must not connect to or write into another database.
pytestmark=pytest.mark.skipif(
    os.environ.get("P2_03Z_CI_ONLY")!="1",
    reason="Requires isolated newly provisioned disposable P2-03z PostgreSQL fixture",
)

from app.pilot_outcomes import (
    OutcomePeriodInput,ReviewInput,submit_period,review_period,
    get_period,compare_periods,list_periods,
)


def sample(period_kind="BASELINE",**overrides):
    fields={
        "project_key":"pilotproject01",
        "period_kind":period_kind,
        "period_start":"2026-01-01" if period_kind=="BASELINE" else "2026-02-01",
        "period_end":"2026-01-30" if period_kind=="BASELINE" else "2026-03-02",
        "currency":"NGN",
        "gross_sales_minor":1_000_000 if period_kind=="BASELINE" else 1_100_000,
        "variable_cost_minor":300_000,
        "marketing_spend_minor":100_000,
        "processing_fees_minor":20_000,
        "fulfillment_cost_minor":20_000,
        "software_cost_minor":10_000,
        "refunds_minor":5_000,
        "completed_orders":40,
        "source_kind":"MANUAL_AGGREGATE",
        "source_sha256":"a"*64,
        "consent_sha256":"b"*64,
    }
    fields.update(overrides)
    return OutcomePeriodInput.model_validate(fields)


@pytest.fixture(scope="module")
def fixture():
    assert "P2_03Z_CI_ONLY" in os.environ
    assert os.environ.get("DATABASE_URL") and os.environ.get("APP_DATABASE_URL")
    tenant1=uuid4(); tenant2=uuid4()
    operator=uuid4(); owner=uuid4(); foreign=uuid4()
    with psycopg.connect(os.environ["DATABASE_URL"],row_factory=dict_row) as db:
        with db.cursor() as cur:
            for org,name in ((tenant1,"Pilot Academy"),(tenant2,"Pilot Bespoke")):
                cur.execute("INSERT INTO organizations(id,slug,name) "
                            "VALUES (%s,%s,%s)",
                            (org,"ci-"+str(org),name))
            for who,email in ((operator,"ciop"),(owner,"ciowner"),(foreign,"ciforeign")):
                cur.execute("INSERT INTO users(id,email) VALUES (%s,%s)",
                            (who,email+"-"+str(who)+"@example.invalid"))
            for org,who,role in ((tenant1,operator,"OPERATOR"),
                                 (tenant1,owner,"OWNER"),
                                 (tenant2,foreign,"OWNER")):
                # Existing tenant-write trigger also protects admin CI fixtures.
                cur.execute("SELECT set_config('app.organization_id',%s,true),"
                            "set_config('app.user_id',%s,true)",
                            (str(org),str(who)))
                cur.execute("INSERT INTO organization_memberships "
                            "(organization_id,user_id,role) VALUES(%s,%s,%s)",
                            (org,who,role))
    return {"org":tenant1,"other_org":tenant2,"operator":operator,
            "owner":owner,"other":foreign}


def session(tenant,who,role):
    conn=psycopg.connect(os.environ["APP_DATABASE_URL"],row_factory=dict_row)
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.organization_id',%s,true),"
                    "set_config('app.user_id',%s,true)",
                    (str(tenant),str(who)))
    return TenantSession(conn=conn,principal=Principal(tenant,who,role))


def close(session):
    session.conn.close()


def test_real_postgres_insert_review_compare_and_no_impact_claim(fixture):
    s=session(fixture["org"],fixture["operator"],"OPERATOR")
    try:
        base=submit_period(sample(),s,"base-idempotent-0001",
                           "authorized-aggregate-measurement")
        assert base["review_state"]=="PENDING_REVIEW"
        assert not base["human_consent_independently_verified"]
        assert base["measurements"]["contribution_after_identified_costs_minor"]==545000
        # A repeated *identical* request is idempotent.
        # Each authenticated request needs fresh transaction-local principal.
        with s.conn.cursor() as cur:
            cur.execute("SELECT set_config('app.organization_id',%s,true),"
                        "set_config('app.user_id',%s,true)",
                        (str(fixture["org"]),str(fixture["operator"])))
        again=submit_period(sample(),s,"base-idempotent-0001",
                            "authorized-aggregate-measurement")
        assert again["period_id"]==base["period_id"]
        with s.conn.cursor() as cur:
            cur.execute("SELECT set_config('app.organization_id',%s,true),"
                        "set_config('app.user_id',%s,true)",
                        (str(fixture["org"]),str(fixture["operator"])))
        with pytest.raises(HTTPException) as collision:
            submit_period(sample(gross_sales_minor=300),s,
                          "base-idempotent-0001","authorized-aggregate-measurement")
        assert collision.value.status_code==409
        s.conn.rollback()
    finally:close(s)

    s=session(fixture["org"],fixture["operator"],"OPERATOR")
    try:
        current=submit_period(sample("CURRENT"),s,
                              "cur-idempotent-0002",
                              "authorized-aggregate-measurement")
    finally:close(s)

    reviewer=session(fixture["org"],fixture["owner"],"OWNER")
    try:
        for receipt in (base,current):
            # Must reestablish tenant RLS context after each commit.
            with reviewer.conn.cursor() as cur:
                cur.execute("SELECT set_config('app.organization_id',%s,true),"
                            "set_config('app.user_id',%s,true)",
                            (str(fixture["org"]),str(fixture["owner"])))
            reviewed=review_period(
                receipt["period_id"],
                ReviewInput(decision="EVIDENCE_CHECKED",
                            reason="Fictional ledger totals checked by a different tester",
                            source_sha256_confirmed="a"*64),
                reviewer,
            )
            assert reviewed["review_state"]=="EVIDENCE_CHECKED"
            assert not reviewed["live_customer_impact_verified"]
        with reviewer.conn.cursor() as cur:
            cur.execute("SELECT set_config('app.organization_id',%s,true),"
                        "set_config('app.user_id',%s,true)",
                        (str(fixture["org"]),str(fixture["owner"])))
        report=compare_periods(base["period_id"],current["period_id"],reviewer)
        assert report["baseline_contribution_minor"]==545000
        assert report["descriptive_difference_minor"]==100000
        assert report["outcome_status"]=="REVIEWED_AGGREGATES_DESCRIPTIVE_ONLY"
        assert not report["financial_causation_attributed_to_metaautomate"]
        assert not report["net_profit_verified"]
        assert not report["source_documents_independently_authenticated"]
    finally:close(reviewer)

    # Foreign organization never sees either receipt, even by guessed UUID.
    outsider=session(fixture["other_org"],fixture["other"],"OWNER")
    try:
        with pytest.raises(HTTPException) as denied:
            get_period(base["period_id"],outsider)
        assert denied.value.status_code==404
        result=list_periods(outsider,20)
        assert result["items"]==[]
    finally:close(outsider)


def test_database_rejects_self_review_and_mutating_source(fixture):
    signer=session(fixture["org"],fixture["operator"],"OPERATOR")
    try:
        r=submit_period(sample(source_sha256="d"*64),signer,
                        "self-idempotent-0003","authorized-aggregate-measurement")
    finally:close(signer)
    own=session(fixture["org"],fixture["operator"],"OPERATOR")
    try:
        with pytest.raises(HTTPException) as deny:
            review_period(r["period_id"],
                ReviewInput(decision="EVIDENCE_CHECKED",
                            reason="Trying to review my own evidence is denied",
                            source_sha256_confirmed="d"*64),own)
        assert deny.value.status_code==403
        with own.conn.cursor() as c:
            with pytest.raises(psycopg.Error):
                c.execute(
                    "INSERT INTO pilot_outcome_reviews "
                    "(organization_id,period_id,reviewer_user_id,decision,reason,"
                    "source_sha256_confirmed,reviewer_receipt_sha256) "
                    "VALUES(%s,%s,%s,'EVIDENCE_CHECKED',%s,%s,%s)",
                    (fixture["org"],r["period_id"],fixture["operator"],
                     "Fake approval by same submitting operator", "d"*64,"e"*64))
        own.conn.rollback()
        with own.conn.cursor() as c:
            c.execute("SELECT set_config('app.organization_id',%s,true),"
                      "set_config('app.user_id',%s,true)",
                      (str(fixture["org"]),str(fixture["operator"])))
            with pytest.raises(psycopg.Error):
                c.execute("UPDATE pilot_outcome_periods SET gross_sales_minor=500 "
                          "WHERE id=%s",(r["period_id"],))
        own.conn.rollback()
    finally:close(own)


def test_sql_rls_and_role_denials(fixture):
    foreign=session(fixture["other_org"],fixture["other"],"OWNER")
    try:
        with foreign.conn.cursor() as cur:
            cur.execute("SELECT count(*) AS count FROM pilot_outcome_periods")
            assert cur.fetchone()["count"]==0
            with pytest.raises(psycopg.Error):
                cur.execute(
                    "INSERT INTO pilot_outcome_periods "
                    "(organization_id,project_key,period_kind,period_start,"
                    "period_end,currency,gross_sales_minor,variable_cost_minor,"
                    "marketing_spend_minor,processing_fees_minor,fulfillment_cost_minor,"
                    "software_cost_minor,refunds_minor,completed_orders,source_kind,"
                    "source_sha256,consent_sha256,input_sha256,request_key,submitted_by_user_id)"
                    " VALUES (%s,'pilotproject01','BASELINE','2026-01-01','2026-01-30',"
                    "'NGN',1,0,0,0,0,0,0,1,'MANUAL_AGGREGATE',%s,%s,%s,%s,%s)",
                    (fixture["org"],"a"*64,"b"*64,"c"*64,
                     "cross-tenant-0004",fixture["other"]),
                )
    finally:close(foreign)
