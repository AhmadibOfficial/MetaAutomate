#!/usr/bin/env python3
"""End-to-end smoke test for the isolated Docker OSS contributor demo.

Run with the sandbox at http://127.0.0.1:18000. No database admin access needed.
Never prints developer access keys or private credentials.
"""
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, HTTPCookieProcessor, build_opener
from uuid import uuid4

BASE = "http://127.0.0.1:18000"
ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = ROOT / "examples" / "oss-demo" / ".workspace-access-key"


def main():
    assert KEY_FILE.is_file()
    assert (KEY_FILE.stat().st_mode & 0o777) == 0o600
    secret = KEY_FILE.read_text(encoding="utf-8").strip()
    assert secret.startswith("mat_dev_")
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))

    def request(method, path, data=None, headers=None, expected=200):
        raw = json.dumps(data).encode("utf-8") if data is not None else None
        request_headers = {"Accept": "application/json"}
        if raw is not None:
            request_headers.update({
                "Content-Type": "application/json",
                "Origin": BASE
            })
        if headers:
            request_headers.update(headers)
        req = Request(BASE+path, data=raw, method=method, headers=request_headers)
        try:
            with opener.open(req, timeout=15) as response:
                status = response.status
                body = response.read()
        except HTTPError as exc:
            status, body = exc.code, exc.read()
        assert status == expected, (path, status, expected, body[:250])
        if not body:
            return {}
        return json.loads(body.decode("utf-8")) if body.startswith(b"{") else {}

    assert request("GET","/health")["status"]=="ok"
    request("GET","/v1/workspace/session",expected=401)
    owner=request("POST","/v1/workspace/login",{"access_key":secret})
    assert owner["role"]=="OWNER" and owner["execution_allowed"] is False
    csrf=next(c.value for c in jar if c.name=="mat_csrf")
    assert csrf and any(c.name=="mat_workspace" for c in jar)
    assert request("GET","/v1/workspace/session")["role"]=="OWNER"
    payload={
        "title":"Test MetaAutomate Open Source Demo",
        "description":"Check objective planning, human review and reproducibility.",
        "success_criteria":[{"metric":"reviewed plans","target":"1","timeframe_days":30}],
        "constraints":["No outbound actions"],
        "requested_capability_ids":["BIZ-003","BIZ-005"]
    }
    headers={"X-CSRF-Token":csrf, "Idempotency-Key":str(uuid4())}
    created=request("POST","/v1/objective-operations",payload,headers,expected=201)
    assert created["plan_steps"]==5
    assert created["persisted"] and not created["execution_allowed"]
    oid=created["objective_id"]
    detail=request("GET","/v1/objective-operations/"+oid)
    assert len(detail["tasks"])==5
    assert detail["review"]["status"]=="PENDING"
    result=request("POST","/v1/objective-operations/"+oid+"/review",
                   {"decision":"APPROVED","reason":"Local demo test, planning only"},
                   {"X-CSRF-Token":csrf})
    assert result["review_status"]=="APPROVED" and result["execution_allowed"] is False
    persisted=request("GET","/v1/objective-operations/"+oid)
    assert persisted["review"]["status"]=="APPROVED"
    assert request("GET","/v1/objective-operations")["items"]
    request("POST","/v1/workspace/logout",{}, {"X-CSRF-Token":csrf})
    request("GET","/v1/workspace/session",expected=401)
    print("PASS: isolated open-source demo setup, login, saved work graph, approval, and logout")
    print("PASS: no cloud deployment or autonomous execution")


if __name__=="__main__":
    main()
