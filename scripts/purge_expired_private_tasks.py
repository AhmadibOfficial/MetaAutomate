#!/usr/bin/env python3
"""Operator-only expired private-result cleanup. Dry-run is the default.

Never use the restricted API runtime database role. The operator explicitly
approves cleanup against a dedicated maintenance database URL. No background
task is configured just by committing this file.
"""
from __future__ import annotations
import argparse
import os
import sys
from urllib.parse import urlsplit

import psycopg

def main(argv=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--execute",action="store_true",
                   help="Actually delete expired rows with a separate maintenance identity")
    p.add_argument("--max-rows",type=int,default=500)
    args=p.parse_args(argv)
    if not 1<=args.max_rows<=1000:
        p.error("--max-rows must be 1–1000")
    url=os.environ.get("MAT_PRIVATE_TASK_MAINTENANCE_DSN","")
    parts=urlsplit(url)
    if (not url or not parts.scheme.startswith("postgres") or not parts.hostname or
        parts.username in (None,"metaautomate_runtime") or
        os.environ.get("MAT_PRIVATE_TASK_RETENTION_APPROVED")!="1"):
        print("HOLD: dedicated approved database maintenance identity required",
              file=sys.stderr)
        return 2
    if args.execute and os.environ.get("MAT_PRIVATE_TASK_PURGE_APPROVED")!="1":
        print("HOLD: operator has not authorized expiration deletion",file=sys.stderr)
        return 2
    try:
        with psycopg.connect(url,connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user")
                active=cur.fetchone()[0]
                if active=="metaautomate_runtime":
                    raise RuntimeError("API runtime role cannot delete task results")
                if args.execute:
                    cur.execute(
                        "WITH expired AS (SELECT id FROM private_execution_results "
                        "WHERE expires_at < clock_timestamp() ORDER BY expires_at "
                        "LIMIT %s FOR UPDATE SKIP LOCKED) "
                        "DELETE FROM private_execution_results a "
                        "USING expired e WHERE a.id=e.id RETURNING a.id",
                        (args.max_rows,),
                    )
                    print(f"Expired private artifacts purged: {len(cur.fetchall())}")
                else:
                    cur.execute(
                        "SELECT count(*) FROM private_execution_results "
                        "WHERE expires_at < clock_timestamp()"
                    )
                    print(f"DRY RUN: expired private artifacts: {cur.fetchone()[0]}")
    except (psycopg.Error,RuntimeError) as exc:
        print(f"HOLD: maintenance database unavailable or unauthorized: {type(exc).__name__}",
              file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
