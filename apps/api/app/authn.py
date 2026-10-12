"""Restricted, organization-bound objective authentication.

Development API bearer tokens and browser sessions share the same tenant
transaction lifetime; no client-supplied organization or user IDs are trusted.
"""
import hashlib
import hmac
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from fastapi import Header, HTTPException, Request


@dataclass(frozen=True)
class Principal:
    organization_id: UUID
    user_id: UUID
    role: str


@dataclass
class TenantSession:
    conn: psycopg.Connection
    principal: Principal


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _database_url() -> str:
    url = os.environ.get("APP_DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="Restricted database connection not configured")
    return url


@contextmanager
def _authenticated_session(query: str, params: tuple) -> Iterator[TenantSession]:
    try:
        with psycopg.connect(_database_url(), connect_timeout=5, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                record = cur.fetchone()
            if not record:
                raise HTTPException(status_code=401, detail="Session expired or unauthorized")
            yield TenantSession(
                conn=conn,
                principal=Principal(
                    organization_id=record["organization_id"],
                    user_id=record["user_id"],
                    role=record["member_role"],
                ),
            )
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Objective operations database unavailable") from None


def _safe_secret(value: str) -> bool:
    return 35 <= len(value) <= 160 and value.isascii() and re.fullmatch(r"[A-Za-z0-9_-]+", value) is not None


@contextmanager
def principal_for_browser(request: Request, *, csrf_required: bool) -> Iterator[TenantSession]:
    session_cookie = request.cookies.get("mat_workspace", "")
    if not _safe_secret(session_cookie):
        raise HTTPException(status_code=401, detail="Workspace sign-in required")
    csrf_digest = None
    if csrf_required:
        expected_origin = os.getenv("WORKSPACE_ORIGIN", "http://127.0.0.1:8000")
        if request.headers.get("origin") != expected_origin:
            raise HTTPException(status_code=403, detail="Invalid workspace request origin")
        header = request.headers.get("x-csrf-token", "")
        cookie = request.cookies.get("mat_csrf", "")
        if not _safe_secret(header) or not hmac.compare_digest(header, cookie):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        csrf_digest = _digest(header)
    with _authenticated_session(
        "SELECT organization_id, user_id, member_role "
        "FROM app.authenticate_workspace_session(%s,%s)",
        (_digest(session_cookie), csrf_digest),
    ) as session:
        yield session


def get_tenant_session(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Iterator[TenantSession]:
    if authorization is not None:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        token = authorization[7:]
        if not token.startswith("mat_dev_") or not _safe_secret(token):
            raise HTTPException(status_code=401, detail="Invalid API token")
        with _authenticated_session(
            "SELECT organization_id, user_id, member_role "
            "FROM app.authenticate_api_token(%s)", (_digest(token),)
        ) as tenant:
            yield tenant
        return
    with principal_for_browser(
        request, csrf_required=request.method.upper() not in ("GET", "HEAD", "OPTIONS")
    ) as tenant:
        yield tenant


def require_role(session: TenantSession, allowed: set[str]) -> None:
    if session.principal.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient organization permissions")
