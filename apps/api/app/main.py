import os
from fastapi import FastAPI
import psycopg
from app.registry import router as capability_router
from app.objectives import router as objective_router
from app.objective_ops import router as objective_ops_router
from app.workspace_auth import router as workspace_auth_router
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MetaAutomate MVP API", version="0.5.0")
app.include_router(capability_router)
app.include_router(objective_router)
app.include_router(objective_ops_router)
app.include_router(workspace_auth_router)

WEB_ROOT = Path(os.environ.get("WORKSPACE_WEB_ROOT", str(Path(__file__).resolve().parents[2] / "web")))

if WEB_ROOT.is_dir():
    app.mount("/assets", StaticFiles(directory=str(WEB_ROOT / "assets")), name="web-assets")

    @app.get("/", include_in_schema=False)
    @app.get("/objectives/{objective_id}", include_in_schema=False)
    def workspace_app(objective_id: str | None = None):
        return FileResponse(WEB_ROOT / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "metaautomate-api"}


@app.get("/ready")
def ready():
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    return {"status": "ready", "database": "connected"}
