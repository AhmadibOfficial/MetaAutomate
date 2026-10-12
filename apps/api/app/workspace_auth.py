"""Browser identity: local-only access keys or external verified OpenID Connect.

OIDC mode requires a configured HTTPS identity provider. ID tokens are validated
by Authlib before exact issuer+subject matching to a provisioned DB identity.
OIDC mode never accepts local developer access keys.
"""
import hashlib
import os
import secrets

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import OAuthError

router = APIRouter(prefix="/v1/workspace", tags=["workspace"])
SESSION_COOKIE = "mat_workspace"
CSRF_COOKIE = "mat_csrf"
LOCAL_MAX_AGE = 8 * 60 * 60
OIDC_MAX_AGE = 60 * 60
oauth = OAuth()


def auth_mode() -> str:
    mode = os.environ.get("WORKSPACE_AUTH_MODE", "dev_key")
    if mode not in ("dev_key", "oidc"):
        raise RuntimeError("WORKSPACE_AUTH_MODE must be dev_key or oidc")
    return mode


if auth_mode() == "oidc":
    issuer = os.environ.get("OIDC_ISSUER", "").rstrip("/")
    if issuer.startswith("https://"):
        oauth.register(
            "meta_idp",
            client_id=os.environ.get("OIDC_CLIENT_ID", ""),
            client_secret=os.environ.get("OIDC_CLIENT_SECRET", ""),
            server_metadata_url=issuer + "/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email"},
        )


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_key: str = Field(min_length=35, max_length=160)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _secure() -> bool:
    return os.environ.get("WORKSPACE_COOKIE_SECURE", "0") == "1"


def _origin_allowed(request: Request) -> None:
    expected = os.environ.get("WORKSPACE_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
    if request.headers.get("origin") != expected:
        raise HTTPException(status_code=403, detail="Invalid workspace request origin")


def _connection():
    url = os.environ.get("APP_DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="Workspace authentication not configured")
    try:
        return psycopg.connect(url, connect_timeout=5, row_factory=dict_row)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Workspace database unavailable") from None


def _cookie_session(response: Response, session_secret: str,
                    csrf_secret: str, max_age: int) -> None:
    kwargs = {"path": "/", "max_age": max_age,
              "secure": _secure(), "samesite": "strict"}
    response.set_cookie(SESSION_COOKIE, session_secret, httponly=True, **kwargs)
    response.set_cookie(CSRF_COOKIE, csrf_secret, httponly=False, **kwargs)


@router.get("/config")
def browser_config():
    mode = auth_mode()
    return {"mode": mode,
            "label": "Organization SSO" if mode == "oidc" else "Local development",
            "execution_allowed": False}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    if auth_mode() != "dev_key":
        raise HTTPException(status_code=404, detail="Development login is disabled")
    _origin_allowed(request)
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
    _cookie_session(response, session_secret, csrf_secret, LOCAL_MAX_AGE)
    return {
        "organization_id": str(principal["organization_id"]),
        "user_id": str(principal["user_id"]),
        "role": principal["member_role"],
        "execution_allowed": False,
    }


@router.get("/oidc/login")
async def oidc_login(request: Request):
    if auth_mode() != "oidc":
        raise HTTPException(status_code=404, detail="SSO not configured")
    provider = oauth.create_client("meta_idp")
    return await provider.authorize_redirect(request, os.environ["OIDC_REDIRECT_URI"])


@router.get("/oidc/callback", name="oidc_callback")
async def oidc_callback(request: Request):
    if auth_mode() != "oidc":
        raise HTTPException(status_code=404, detail="SSO not configured")
    provider = oauth.create_client("meta_idp")
    try:
        tokens = await provider.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=401, detail="Identity provider sign-in failed") from None
    userinfo = tokens.get("userinfo") or {}
    issuer = str(userinfo.get("iss", ""))
    subject = str(userinfo.get("sub", ""))
    configured = os.environ["OIDC_ISSUER"].rstrip("/")
    if (not tokens.get("id_token") or issuer != configured
            or not subject or len(subject) > 512):
        raise HTTPException(status_code=401, detail="Verified OIDC identity required")

    session_secret = secrets.token_urlsafe(36)
    csrf_secret = secrets.token_urlsafe(32)
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT organization_id, user_id, member_role "
                "FROM app.create_oidc_workspace_session(%s,%s,%s,%s)",
                (issuer, _digest(subject), _digest(session_secret), _digest(csrf_secret)),
            )
            principal = cur.fetchone()
    if not principal:
        raise HTTPException(status_code=403, detail="SSO account not authorized for MetaAutomate")
    response = RedirectResponse(url="/", status_code=303)
    _cookie_session(response, session_secret, csrf_secret, OIDC_MAX_AGE)
    return response


@router.get("/session")
def session(request: Request):
    from app.authn import principal_for_browser
    with principal_for_browser(request, csrf_required=False) as tenant:
        principal = tenant.principal
        return {
            "organization_id": str(principal.organization_id),
            "user_id": str(principal.user_id),
            "role": principal.role,
            "execution_allowed": False,
        }


@router.post("/logout")
def logout(request: Request, response: Response):
    _origin_allowed(request)
    from app.authn import principal_for_browser
    with principal_for_browser(request, csrf_required=True) as tenant:
        raw = request.cookies.get(SESSION_COOKIE, "")
        with tenant.conn.cursor() as cur:
            cur.execute("SELECT app.revoke_workspace_session(%s)", (_digest(raw),))
    response.delete_cookie(SESSION_COOKIE, path="/", secure=_secure(), samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=_secure(), samesite="strict")
    return {"signed_out": True}
