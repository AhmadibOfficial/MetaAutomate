#!/usr/bin/env python3
"""Transactional and repeatable import of the 33 DRAFT catalog entries.

Does NOT activate any capability, grant permissions, or enable executions.
"""

import argparse
import csv
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

import psycopg

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "docs" / "registry" / "capabilities.csv"
REQUIRED = {"capability_id", "name", "domain", "release", "priority", "lifecycle_status"}
VALID_DOMAINS = {"CORE", "BIZ", "PER", "CRE", "SPEC"}
VALID_RELEASES = {"R1", "R2", "R3", "R4"}
VALID_PRIORITIES = {"P0", "P1", "P2"}


def read_capabilities(path: Path = CSV_PATH) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("Missing required columns in capability CSV")
        rows = list(reader)
    seen: set[str] = set()
    for row in rows:
        cap_id = row["capability_id"]
        if not re.fullmatch(r"[A-Z]+-[0-9]{3}", cap_id):
            raise ValueError(f"Invalid capability id: {cap_id!r}")
        if cap_id in seen:
            raise ValueError(f"Duplicate capability id: {cap_id}")
        seen.add(cap_id)
        if row["domain"] not in VALID_DOMAINS or row["release"] not in VALID_RELEASES:
            raise ValueError(f"Invalid domain/release for: {cap_id}")
        if row["priority"] not in VALID_PRIORITIES or row["lifecycle_status"] != "DRAFT":
            raise ValueError(f"Only draft CSV catalog entries may be seeded: {cap_id}")
        if len(row["name"].strip()) < 3:
            raise ValueError(f"Invalid name for: {cap_id}")
    if not rows:
        raise ValueError("Empty capability catalog")
    return rows


def with_database(base_url: str, database: str | None) -> str:
    if not database:
        return base_url
    if not re.fullmatch(r"[a-z][a-z0-9_]*", database):
        raise ValueError("Unsafe database name")
    parts = urlsplit(base_url)
    if parts.scheme not in ("postgres", "postgresql") or not parts.hostname:
        raise ValueError("Expected PostgreSQL DATABASE_URL")
    return urlunsplit(parts._replace(path="/" + database))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", help="Optional existing database name (for isolated testing)")
    args = parser.parse_args()
    rows = read_capabilities()
    db_url = with_database(os.environ["DATABASE_URL"], args.database)
    with psycopg.connect(db_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """INSERT INTO capability_definitions
                       (capability_id, name, domain, release, priority, lifecycle_status, is_enabled)
                       VALUES (%s, %s, %s, %s, %s, 'DRAFT', false)
                       ON CONFLICT (capability_id) DO UPDATE SET
                           name = EXCLUDED.name, domain = EXCLUDED.domain,
                           release = EXCLUDED.release, priority = EXCLUDED.priority""",
                    (row["capability_id"], row["name"], row["domain"],
                     row["release"], row["priority"]),
                )
                # Placeholder only: no contract supplied by the CSV. Not current or runnable.
                cur.execute(
                    """INSERT INTO capability_versions
                       (capability_id, version, version_state, contract, is_current)
                       VALUES (%s, '0.1.0', 'DRAFT', NULL, false)
                       ON CONFLICT (capability_id, version) DO NOTHING""",
                    (row["capability_id"],),
                )
    print(f"Seeded/updated {len(rows)} DRAFT capabilities (no capabilities activated).")


if __name__ == "__main__":
    main()
