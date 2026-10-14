import os
from fastapi import FastAPI
import psycopg
from app.registry import router as capability_router
from app.objectives import router as objective_router
from app.objective_ops import router as objective_ops_router
from app.workspace_auth import router as workspace_auth_router
from app.assessments import router as assessment_router
from app.amboy_m1 import router as amboy_m1_router
from app.domain_integrations import router as domain_integrations_router
from app.synthetic_inventory import router as synthetic_inventory_router
from app.synthetic_inventory_import import router as synthetic_inventory_import_router
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from urllib.parse import urlsplit

_mode = os.environ.get("WORKSPACE_AUTH_MODE", "dev_key")
if _mode not in ("dev_key", "oidc"):
    raise RuntimeError("Unsupported workspace authentication mode")
if _mode == "oidc":
    for key in ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET",
                "OIDC_REDIRECT_URI", "OIDC_STATE_SECRET", "WORKSPACE_ORIGIN", "APP_DATABASE_URL"):
        if not os.environ.get(key):
            raise RuntimeError("Private OIDC configuration missing: " + key)
    origin = os.environ["WORKSPACE_ORIGIN"].rstrip("/")
    redirect = os.environ["OIDC_REDIRECT_URI"]
    issuer = os.environ["OIDC_ISSUER"]
    if any(urlsplit(value).scheme != "https" or not urlsplit(value).hostname
           for value in (origin, redirect, issuer)):
        raise RuntimeError("Private OIDC origin, callback and issuer must use HTTPS")
    if redirect != origin + "/v1/workspace/oidc/callback":
        raise RuntimeError("OIDC redirect must be the exact workspace callback")
    if os.environ.get("WORKSPACE_COOKIE_SECURE") != "1":
        raise RuntimeError("OIDC requires secure browser cookies")
    if len(os.environ["OIDC_STATE_SECRET"]) < 48:
        raise RuntimeError("Insufficient private OIDC state secret entropy")
    if os.environ.get("DATABASE_URL"):
        raise RuntimeError("Privileged DATABASE_URL prohibited in OIDC API runtime")
    if urlsplit(os.environ["APP_DATABASE_URL"]).username != "metaautomate_runtime":
        raise RuntimeError("OIDC API runtime must use the restricted database role")

app = FastAPI(title="MetaAutomate Objective Workspace API", version="0.6.0")
if _mode == "oidc":
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=os.environ["OIDC_STATE_SECRET"],
                       session_cookie="mat_oidc_state", max_age=600,
                       same_site="lax", https_only=True)
if _mode == "dev_key":
    app.include_router(capability_router)
    app.include_router(objective_router)
app.include_router(objective_ops_router)
app.include_router(workspace_auth_router)
app.include_router(assessment_router)
app.include_router(amboy_m1_router)
app.include_router(domain_integrations_router)
if _mode == "dev_key":
    app.include_router(synthetic_inventory_router)
    app.include_router(synthetic_inventory_import_router)


@app.middleware("http")
async def workspace_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; "
        "object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith(("/v1/workspace", "/v1/objective-operations", "/v1/assessments", "/v1/amboy", "/v1/domain-integrations")):
        response.headers["Cache-Control"] = "no-store"
    return response

WEB_ROOT = Path(os.environ.get("WORKSPACE_WEB_ROOT", str(Path(__file__).resolve().parents[2] / "web")))

if WEB_ROOT.is_dir():
    app.mount("/assets", StaticFiles(directory=str(WEB_ROOT / "assets")), name="web-assets")

    @app.get("/", include_in_schema=False)
    @app.get("/objectives/{objective_id}", include_in_schema=False)
    @app.get("/assessments", include_in_schema=False)
    @app.get("/assessments/{assessment_id}", include_in_schema=False)
    def workspace_app(objective_id: str | None = None):
        return FileResponse(WEB_ROOT / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "metaautomate-api"}


@app.get("/ready")
def ready():
    with psycopg.connect(os.environ["APP_DATABASE_URL"] if _mode == "oidc" else os.environ["DATABASE_URL"], connect_timeout=3) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    return {"status": "ready", "database": "connected"}
