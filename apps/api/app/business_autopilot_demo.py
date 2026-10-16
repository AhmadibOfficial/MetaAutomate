"""Standalone loopback-only demo host. Not mounted in app.main or deploy images.

Run handles separate ephemeral browser demonstrations, not authenticated tenants.
No shared workspace sessions, cookies, customer records or DB access are used.
"""
from __future__ import annotations

import secrets
from threading import Lock
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.business_autopilot import DemoConflict, DemoRun, ROOT, SCENARIOS, strict_json

MAX_RUNS = 32
TTL_SECONDS = 1800
WEB = ROOT / "apps/web/autopilot-demo"
STATIC = {"/": ("index.html", "text/html"),
          "/demo.css": ("demo.css", "text/css"),
          "/demo.js": ("demo.js", "text/javascript")}


def create_demo_app(port: int = 8090) -> FastAPI:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Choose a local demo port between 1024 and 65535")
    origin = f"http://127.0.0.1:{port}"
    app = FastAPI(title="MetaAutomate synthetic demonstration", docs_url=None,
                  redoc_url=None, openapi_url=None)
    runs: dict[str, tuple[float, DemoRun]] = {}
    lock = Lock()

    def purge():
        now = time.monotonic()
        for token in list(runs):
            if now - runs[token][0] >= TTL_SECONDS:
                del runs[token]

    def run_for(request: Request) -> DemoRun:
        purge()
        handles = request.headers.getlist("x-demo-run")
        if len(handles) != 1 or handles[0] not in runs:
            raise HTTPException(404, "Demo expired or unavailable. Start a new demonstration.")
        return runs[handles[0]][1]

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        peer = request.client.host if request.client else ""
        headers = request.headers
        blocked = (
            peer != "127.0.0.1" or headers.getlist("host") != [f"127.0.0.1:{port}"]
            or request.url.query
            or headers.get("sec-fetch-site", "same-origin") not in {"none", "same-origin"}
            or ("origin" in headers and headers.getlist("origin") != [origin])
            or any(key in headers for key in ("forwarded", "x-forwarded-for", "x-forwarded-host",
                "x-forwarded-proto", "x-tenant-id", "x-organization-id", "x-provider-key"))
            or (request.method not in {"GET", "HEAD"} and (
                headers.getlist("origin") != [origin]
                or headers.getlist("x-metaautomate-demo") != ["1"]))
        )
        response = JSONResponse({"detail": "Use the direct loopback demonstration origin."},
                                status_code=403) if blocked else await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})
        return response

    async def document(request: Request) -> dict:
        if request.headers.get("content-type", "").lower() != "application/json":
            raise HTTPException(415, "Use application/json")
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > 4096:
                raise HTTPException(413, "Demo request too large")
            raw.extend(chunk)
        try:
            doc = strict_json(bytes(raw))
        except (ValueError, TypeError):
            raise HTTPException(422, "Invalid demo JSON") from None
        if type(doc) is not dict:
            raise HTTPException(422, "Use a demo JSON object")
        return doc

    @app.get("/")
    @app.get("/demo.css")
    @app.get("/demo.js")
    def static(request: Request):
        filename, mime = STATIC[request.url.path]
        return FileResponse(WEB / filename, media_type=mime)

    @app.post("/demo/runs")
    async def start(request: Request):
        doc = await document(request)
        if set(doc) != {"scenario_id"} or doc["scenario_id"] not in SCENARIOS:
            raise HTTPException(422, "Choose a known synthetic scenario; no other input is accepted.")
        with lock:
            purge()
            if len(runs) >= MAX_RUNS:
                raise HTTPException(429, "Local demo capacity reached. Close old runs or restart the host.")
            token = secrets.token_urlsafe(32)
            run = DemoRun(doc["scenario_id"])
            runs[token] = (time.monotonic(), run)
            return {"run_token": token, "state": run.snapshot()}

    @app.get("/demo/run")
    def current(request: Request):
        with lock:
            return run_for(request).snapshot()

    @app.delete("/demo/run")
    def remove(request: Request):
        with lock:
            run_for(request)
            del runs[request.headers["x-demo-run"]]
            return {"removed": True}

    @app.post("/demo/actions/{action}")
    async def action(action: str, request: Request):
        doc = await document(request)
        fields = {"plan_sha256", "decision", "simulation_only"} if action == "review" else set()
        if set(doc) != fields:
            raise HTTPException(422, "Unexpected demo action input")
        if action == "review" and (type(doc["plan_sha256"]) is not str
                or type(doc["decision"]) is not str or doc["simulation_only"] is not True):
            raise HTTPException(422, "An explicit simulation-only review is required")
        if action not in {"assess", "plan", "review", "simulate", "verify"}:
            raise HTTPException(404, "Unknown demo action")
        with lock:
            run = run_for(request)
            try:
                if action == "review":
                    run.decide(**doc)
                else:
                    {"assess": run.assess, "plan": run.make_plan,
                     "simulate": run.simulate, "verify": run.verify}[action]()
            except DemoConflict as exc:
                raise HTTPException(409, str(exc)) from None
            return run.snapshot()

    @app.get("/demo/report")
    def export(request: Request):
        with lock:
            run = run_for(request)
            if run.stage != "VERIFIED":
                raise HTTPException(409, "Verify the synthetic demonstration before downloading evidence.")
            return JSONResponse(run.bundle(), headers={
                "Content-Disposition": 'attachment; filename="metaautomate-synthetic-evidence.json"'})

    return app
