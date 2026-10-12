#!/usr/bin/env python3
"""Read-only development smoke test for the running MetaAutomate API."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("META_API_URL", "http://127.0.0.1:8000").rstrip("/")


def request(path, *, key=None, payload=None):
    headers = {}
    if key:
        headers["X-Registry-Key"] = key
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(
        BASE + path,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="GET" if payload is None else "POST",
    )
    with urlopen(req, timeout=10) as response:
        assert response.status == 200, (path, response.status)
        return json.load(response)


def local_key():
    file = ROOT / ".env"
    if not file.exists():
        raise RuntimeError("Missing .env: configure REGISTRY_READ_API_KEY locally")
    for line in file.read_text(encoding="utf-8").splitlines():
        if line.startswith("REGISTRY_READ_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"\'')
    raise RuntimeError("REGISTRY_READ_API_KEY is missing from .env")


def main():
    assert request("/health")["status"] == "ok"
    assert request("/ready")["status"] == "ready"
    key = local_key()
    assert key, "REGISTRY_READ_API_KEY is empty"
    catalog = request("/v1/capabilities?domain=CORE", key=key)
    assert catalog["total"] >= 2, "Registry catalog has not been seeded"
    preview = request(
        "/v1/objectives/preview", key=key,
        payload={
            "title": "Increase qualified customer appointments",
            "description": "Review the sales pipeline for the next month",
            "success_criteria": [
                {"metric": "qualified appointments", "target": "20", "timeframe_days": 30}
            ],
            "constraints": ["Only contact customers who opted in"],
            "requested_capability_ids": ["BIZ-003", "BIZ-005"],
        },
    )
    assert preview["mode"] == "PLAN_PREVIEW_ONLY"
    assert preview["execution_allowed"] is False
    assert preview["persisted"] is False
    assert len(preview["matched_capabilities"]) == 2
    assert len(preview["work_graph"]) == 5
    assert all(item["execution_ready"] is False for item in preview["matched_capabilities"])
    print("PASS: health, database readiness, capability catalog, and non-executing objective preview")


if __name__ == "__main__":
    main()
