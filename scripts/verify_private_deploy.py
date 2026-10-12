#!/usr/bin/env python3
"""Validate private-cloud packaging without deploying or creating infrastructure."""
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
compose=ROOT/"deploy"/"private"/"compose.yaml"
example=ROOT/"deploy"/"private"/".env.example"
env=os.environ.copy()

result=subprocess.run(
    ["docker","compose","--env-file",str(example),"-f",str(compose),
     "--profile","admin","config","--format","json"],
    cwd=ROOT,capture_output=True,text=True,env=env,timeout=35,
)
if result.returncode!=0:
    raise AssertionError(result.stderr)
manifest=json.loads(result.stdout)
services=manifest["services"]
api=services["api"]
postgres=services["postgres"]
assert not postgres.get("ports"),"PostgreSQL must never expose a host listener"
ports=api.get("ports",[])
assert len(ports)==1
assert ports[0].get("host_ip")=="127.0.0.1" and ports[0].get("published")=="8080"
assert api["environment"]["WORKSPACE_AUTH_MODE"]=="oidc"
assert api["environment"]["WORKSPACE_COOKIE_SECURE"]=="1"
assert not api["environment"].get("DATABASE_URL"),"Migration administrator credential must not reach API"
assert api["read_only"] is True
assert api.get("user")=="10001:10001"
assert "ALL" in api.get("cap_drop",[])
assert not services["migrator"].get("ports")
assert "admin" in services["migrator"].get("profiles",[])
assert "admin" in services["admin"].get("profiles",[])
assert "DATABASE_URL" in services["admin"]["environment"]
print("PASS: cloud stack topology, localhost-only API, separate admin and restricted runtime roles")
