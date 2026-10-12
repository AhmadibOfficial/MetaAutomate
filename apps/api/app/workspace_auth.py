"""Local-only, tenant-aware browser session exchange.

A user enters a pre-provisioned high-entropy workspace key once in the browser.
No raw key or session secret is stored in PostgreSQL. Browser sessions use an
HttpOnly cookie, separate CSRF token, and are revoked server-side on logout.
"""
import hashlib
import os
import secrets

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter(prefix="/v1/workspace", tags=["workspace"])
SESSION_COOKIE = "mat_workspace"
CSRF_COOKIE = "mat_csrf"
MAX_AGE = 8 * 60 * 60


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_key: str = Field(min_length=35, max_length=160)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _secure() -> bool:
    return os.environ.get("WORKSPACE_COOKIE_SECURE", "0") == "1"


def _allowed_origin(request: Request):
    origin = request.headers.get("origin")
    allowed = os.environ.get("WORKSPACE_ORIGIN", "http://127.0.0.1:8000")
    if origin != allowed:
        raise HTTPException(status_code=403, detail="Invalid workspace request origin")


def _connection():
    url = os.environ.get("APP_DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="Workspace authentication not configured")
    try:
        return psycopg.connect(url, connect_timeout=5, row_factory=dict_row)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Workspace database unavailable") from None


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    _allowed_origin(request)
    key = payload.access_key
    if not key.isascii() or not key.startswith("mat_dev_"):
        raise HTTPException(status_code=401, detail="Invalid workspace access key")
    session_secret = secrets.token_urlsafe(36)
    csrf_secret = secrets.token_urlsafe(32)
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT organization_id, user_id, member_role "
                "FROM app.create_workspace_session(%s,%s,%s)",
                (_digest(key), _digest(session_secret), _digest(csrf_secret)),
            )
            principal = cur.fetchone()
    if not principal:
        raise HTTPException(status_code=401, detail="Invalid or expired workspace access key")
    cookie_args = {"path": "/", "max_age": MAX_AGE, "secure": _secure(), "samesite": "strict"}
    response.set_cookie(SESSION_COOKIE, session_secret, httponly=True, **cookie_args)
    response.set_cookie(CSRF_COOKIE, csrf_secret, httponly=False, **cookie_args)
    return {
        "organization_id": str(principal["organization_id"]),
        "user_id": str(principal["user_id"]),
        "role": principal["member_role"],
        "execution_allowed": False,
    }


@router.get("/session")
def session(request: Request):
    return _session_for_request(request)


def _session_for_request(request: Request):
    from app.authn import principal_for_browser
    with principal_for_browser(request, csrf_required=False) as session:
        principal = session.principal
        return {
            "organization_id": str(principal.organization_id),
            "user_id": str(principal.user_id),
            "role": principal.role,
            "execution_allowed": False,
        }


@router.post("/logout")
def logout(request: Request, response: Response):
    _allowed_origin(request)
    from app.authn import principal_for_browser
    with principal_for_browser(request, csrf_required=True) as tenant:
        raw = request.cookies.get(SESSION_COOKIE, "")
        with tenant.conn.cursor() as cur:
            cur.execute("SELECT app.revoke_workspace_session(%s)", (_digest(raw),))
    response.delete_cookie(SESSION_COOKIE, path="/", secure=_secure(), samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=_secure(), samesite="strict")
    return {"signed_out": True}
