#!/usr/bin/env python3
"""Destructive OneCall replay-integrity drill: disposable GitHub PostgreSQL ONLY."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import psycopg

ADMIN_DSN = "postgresql://metaautomate:ci_only_password@localhost:5432/metaautomate"
APP_DSN = "postgresql://metaautomate_runtime:ci_runtime_password@localhost:5432/metaautomate"

if not (
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("CI") == "true"
    and os.environ.get("GITHUB_REPOSITORY") == "AhmadibOfficial/MetaAutomate"
    and os.environ.get("GITHUB_RUN_ID", "").isdigit()
    and os.environ.get("DATABASE_URL") == ADMIN_DSN
    and os.environ.get("APP_DATABASE_URL") == APP_DSN
):
    raise SystemExit("REFUSED: replay drill restricted to exact disposable GitHub Actions DB")


def consume(jti, subject):
    with psycopg.connect(ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT app.consume_onecall_identity_test_jti(%s,%s,%s,%s,%s)",
            (jti, "https://onecall-identity.invalid", subject, 2,
             datetime.now(timezone.utc) + timedelta(seconds=45)),
        ).fetchone()[0]


def run():
    jti, subject = uuid4(), uuid4()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: consume(jti, subject), range(8)))
    assert results.count(True) == 1, results
    assert results.count(False) == 7, results

    with psycopg.connect(ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM onecall_identity_test_redemptions WHERE assertion_jti=%s",
                (jti,),
            )
            assert cur.fetchone()[0] == 1
            cur.execute(
                "SELECT outcome,count(*) FROM onecall_identity_test_events "
                "WHERE assertion_jti=%s GROUP BY outcome ORDER BY outcome", (jti,),
            )
            assert dict(cur.fetchall()) == {"FIRST_USE": 1, "REPLAY": 7}
            cur.execute(
                "SELECT count(*) FROM onecall_tenant_mapping_reviews "
                "WHERE review_state <> 'PENDING'"
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                "SELECT has_function_privilege('metaautomate_runtime', "
                "'app.consume_onecall_identity_test_jti(uuid,text,uuid,integer,timestamptz)',"
                "'EXECUTE')"
            )
            assert cur.fetchone()[0] is False
            try:
                cur.execute("UPDATE onecall_identity_test_events SET outcome='REPLAY' "
                            "WHERE assertion_jti=%s", (jti,))
            except psycopg.errors.RaiseException:
                conn.rollback()
            else:
                raise AssertionError("Append-only OneCall identity event modified")

    with psycopg.connect(APP_DSN) as conn:
        with conn.cursor() as cur:
            for table in ("onecall_identity_test_redemptions",
                          "onecall_identity_test_events",
                          "onecall_tenant_mapping_reviews"):
                assert not cur.execute(
                    "SELECT has_table_privilege('metaautomate_runtime',%s,'SELECT')",
                    (table,),
                ).fetchone()[0], table
    print("PASS: strict source-only OneCall JTI concurrency, immutable audit, "
          "tenant mapping NO-GO, and runtime access denial")


if __name__ == "__main__":
    run()
