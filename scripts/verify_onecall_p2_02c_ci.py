#!/usr/bin/env python3
"""P2-02c destructive concurrency rehearsal: exact disposable GitHub CI DB ONLY."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import psycopg

ADMIN = "postgresql://metaautomate:ci_only_password@localhost:5432/metaautomate"
RUNTIME = "postgresql://metaautomate_runtime:ci_runtime_password@localhost:5432/metaautomate"
if not (
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("CI") == "true"
    and os.environ.get("GITHUB_REPOSITORY") == "AhmadibOfficial/MetaAutomate"
    and os.environ.get("GITHUB_RUN_ID", "").isdigit()
    and os.environ.get("DATABASE_URL") == ADMIN
    and os.environ.get("APP_DATABASE_URL") == RUNTIME
):
    raise SystemExit("REFUSED: M2M replay test is restricted to the exact disposable CI database")


def redeem(assertion_id, proof_id):
    at_time = datetime.now(timezone.utc)
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT app.consume_onecall_m2m_identity_test_pair("
            "%s,%s,%s,%s,%s,%s,%s,%s)",
            (assertion_id, proof_id, "https://onecall-identity.invalid",
             SUBJECT, 4, at_time + timedelta(seconds=55),
             "https://onecall-service.invalid", at_time + timedelta(seconds=25))
        ).fetchone()[0]


SUBJECT = uuid4()


def main():
    aid, pid = uuid4(), uuid4()
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: redeem(aid, pid), range(8)))
    assert outcomes.count(True) == 1 and outcomes.count(False) == 7, outcomes
    # A different proof cannot reuse the original assertion, nor vice versa.
    assert redeem(aid, uuid4()) is False
    assert redeem(uuid4(), pid) is False

    with psycopg.connect(ADMIN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM onecall_identity_test_redemptions "
                        "WHERE assertion_jti=%s", (aid,))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT count(*) FROM onecall_m2m_test_proof_redemptions "
                        "WHERE proof_jti=%s AND assertion_jti=%s", (pid, aid))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT outcome,count(*) FROM onecall_m2m_test_events "
                        "WHERE assertion_jti=%s AND proof_jti=%s GROUP BY outcome",
                        (aid, pid))
            assert dict(cur.fetchall()) == {"FIRST_USE": 1, "REPLAY": 7}
            cur.execute("SELECT count(*) FROM onecall_identity_test_redemptions "
                        "WHERE assertion_jti=%s", (aid,))
            assert cur.fetchone()[0] == 1
            for table in ("onecall_m2m_test_proof_redemptions",
                          "onecall_m2m_test_events"):
                cur.execute("SELECT has_table_privilege('metaautomate_runtime',%s,'SELECT')",
                            (table,))
                assert cur.fetchone()[0] is False
            cur.execute(
                "SELECT has_function_privilege('metaautomate_runtime',"
                "'app.consume_onecall_m2m_identity_test_pair(uuid,uuid,text,uuid,"
                "integer,timestamptz,text,timestamptz)','EXECUTE')")
            assert cur.fetchone()[0] is False

    with psycopg.connect(ADMIN) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("UPDATE onecall_m2m_test_events SET outcome='REPLAY'"
                            " WHERE assertion_jti=%s", (aid,))
            except psycopg.errors.RaiseException:
                conn.rollback()
            else:
                raise AssertionError("M2M event evidence was mutable")
    print("PASS: 8 concurrent M2M pair redemptions -> 1 accept, 7 deny; "
          "immutable audit; no runtime access; no identity grant.")


if __name__ == "__main__":
    main()
