"""Tenant-scoped development bearer authentication and transaction lifetime.

API credentials are opaque, high-entropy tokens stored as SHA-256 digests.
The app uses a restricted PostgreSQL LOGIN role via APP_DATABASE_URL.
This is a local engineering milestone, not a complete public identity platform.
"""
import hashlib
import os
from dataclasses import dataclass
from typing import Annotated, Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from fastapi import Header, HTTPException


@dataclass(frozen=True)
class Principal:
    organization_id: UUID
    user_id: UUID
    role: str


@dataclass
class TenantSession:
    conn: psycopg.Connection
    principal: Principal


def get_tenant_session(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Iterator[TenantSession]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization[7:]
    if (len(token) < 35 or len(token) > 160 or not token.startswith("mat_dev_")
            or not token.isascii()):
        raise HTTPException(status_code=401, detail="Invalid API token")

    db_url = os.environ.get("APP_DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="Restricted database connection not configured")

    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    try:
        with psycopg.connect(db_url, connect_timeout=5, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT organization_id, user_id, member_role "
                    "FROM app.authenticate_api_token(%s)", (digest,)
                )
                record = cur.fetchone()
            if not record:
                raise HTTPException(status_code=401, detail="Expired, revoked, or invalid API token")
            principal = Principal(
                organization_id=record["organization_id"],
                user_id=record["user_id"],
                role=record["member_role"],
            )
            yield TenantSession(conn=conn, principal=principal)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Objective operations database unavailable") from None


def require_role(session: TenantSession, allowed: set[str]) -> None:
    if session.principal.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient organization permissions")
