#!/usr/bin/env python3
"""CI-only: validate opt-in local bootstrap credentials and CSRF enforcement."""
import os
from pathlib import Path
import stat
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get("GITHUB_ACTIONS")!="true":
    raise RuntimeError("Bootstrap verification may only run on ephemeral GitHub CI")

env=ROOT/".env"
key_file=ROOT/".workspace-access-key"
assert env.exists() and key_file.exists()
assert stat.S_IMODE(env.stat().st_mode)==0o600
assert stat.S_IMODE(key_file.stat().st_mode)==0o600
settings=dict(line.split("=",1) for line in env.read_text().splitlines() if "=" in line)
os.environ["APP_DATABASE_URL"]=settings["APP_DATABASE_URL"]
os.environ["WORKSPACE_ORIGIN"]="http://127.0.0.1:8000"
key=key_file.read_text().strip()
assert key.startswith("mat_dev_")

example={
    "title":"Verify local workspace bootstrap",
    "description":"Testing the browser authentication boundary",
    "success_criteria":[{"metric":"successful plans","target":"1","timeframe_days":30}],
    "constraints":["No external execution"],
    "requested_capability_ids":["BIZ-003","BIZ-005"]
}
origin={"Origin":"http://127.0.0.1:8000"}
with TestClient(app) as client:
    unauth=client.get("/v1/workspace/session")
    assert unauth.status_code==401
    login=client.post("/v1/workspace/login",json={"access_key":key},headers=origin)
    assert login.status_code==200,login.text
    assert login.json()["role"]=="OWNER"
    assert any("httponly" in header.lower() for header in login.headers.get_list("set-cookie"))
    assert client.get("/v1/workspace/session").status_code==200
    csrf=client.cookies.get("mat_csrf")
    assert csrf

    headers={"Idempotency-Key":str(uuid4())}
    assert client.post("/v1/objective-operations",json=example,headers={**headers,**origin}).status_code==403
    assert client.post("/v1/objective-operations",json=example,headers={
        **headers,"Origin":"http://attacker.invalid","X-CSRF-Token":csrf
    }).status_code==403
    result=client.post("/v1/objective-operations",json=example,headers={
        **headers,**origin,"X-CSRF-Token":csrf
    })
    assert result.status_code==201,result.text
    assert result.json()["execution_allowed"] is False
    assert client.post("/v1/workspace/logout",json={},headers={
        **origin,"X-CSRF-Token":csrf
    }).status_code==200
    assert client.get("/v1/workspace/session").status_code==401
print("PASS: one-command bootstrap, restricted login, HttpOnly sessions, CSRF, persisted objective, logout")
