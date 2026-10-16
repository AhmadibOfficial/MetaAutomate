#!/usr/bin/env python3
"""P2-04e: offline, ephemeral cross-PR synthetic test suite.

Loads four PINNED PR revisions using local git objects only. Copies 4 modules,
4 tests and main.py (from main) into TemporaryDirectory; runs pytest there.
NO cherry-pick, merge, writes to checkout, webhook, network, provider, tenant
session, queue, production DB, migration, worker or persistent artefacts.

This is a source-coexistence smoke test, NOT an end-to-end integration test
or a substitute for human review / branch protection. Only use trusted commits.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SCHEMA = "metaautomate.p2-04e.offline-cross-pr.v1"
MANIFEST = "contracts/engineering/p2_04e_offline_sources.json"
PINNED_BASE = "7144451b0ac37349c3e731bac76d14338280c42e"
PINNED = {
    32: (
        "2739ca4f9b4a6cd10ad556933b5f45ecab9a6c91",
        "apps/api/app/synthetic_delivery.py",
        "tests/test_phase02_delivery_rehearsal.py",
    ),
    33: (
        "bf6ec6d1a7538a3bb23d03961ef7379d89fc87e5",
        "apps/api/app/synthetic_webhook_proof.py",
        "tests/test_phase02_synthetic_webhook_proof.py",
    ),
    34: (
        "0b9556b84386e783da873f954e572338af3100c1",
        "apps/api/app/synthetic_incident_observability.py",
        "tests/test_phase02_synthetic_incident_observability.py",
    ),
    35: (
        "30a4608ffed00ce99926064315e657f0e8b581ee",
        "apps/api/app/synthetic_delivery_resilience.py",
        "tests/test_phase02_synthetic_delivery_resilience.py",
    ),
}
SHA = re.compile(r"[0-9a-f]{40}\Z")


class ConformanceError(ValueError):
    """Manifest or offline material invalid; do not run source tests."""


def validate_contract(doc: object) -> tuple[tuple[int, str, str, str], ...]:
    """Require exact approved PR SHAs/paths and fail closed on any drift."""
    if type(doc) is not dict or set(doc) != {
        "schema", "base", "source_only", "requires_independent_review",
        "phase01_verified_gates", "phase01_total_gates",
        "merge_permitted", "live_execution_permitted", "entries",
    }:
        raise ConformanceError("Manifest shape mismatch")
    if (doc["schema"] != SCHEMA or doc["source_only"] is not True
            or doc["requires_independent_review"] is not True
            or doc["phase01_verified_gates"] != 3
            or doc["phase01_total_gates"] != 9
            or doc["merge_permitted"] is not False
            or doc["live_execution_permitted"] is not False
            or doc["base"] != {
                "sha": PINNED_BASE,
                "main_path": "apps/api/app/main.py",
            }):
        raise ConformanceError("Release boundary or base commit mismatch")
    entries = doc["entries"]
    if type(entries) is not list or len(entries) != 4:
        raise ConformanceError("Exactly four isolated milestones are required")
    output: list[tuple[int, str, str, str]] = []
    for expected_pr, entry in zip(sorted(PINNED), entries):
        if type(entry) is not dict or set(entry) != {"pr", "sha", "module", "test"}:
            raise ConformanceError("Invalid milestone entry")
        expected = PINNED[expected_pr]
        if (type(entry["pr"]) is not int or entry["pr"] != expected_pr
                or type(entry["sha"]) is not str
                or SHA.fullmatch(entry["sha"]) is None
                or (entry["sha"], entry["module"], entry["test"]) != expected):
            raise ConformanceError("Milestone SHA/path mismatch")
        output.append((expected_pr, *expected))
    return tuple(output)


def _show(repo: Path, sha: str, file_path: str) -> bytes:
    """Read a path from a local immutable Git commit, never a remote URL."""
    cmd = ["git", "-C", str(repo), "show", f"{sha}:{file_path}"]
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, timeout=15,
        )
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired) as exc:
        raise ConformanceError(
            f"Missing local Git object {sha[:12]}:{file_path}. "
            "Fetch the PR branches using GitHub CLI first; do not use live services."
        ) from exc
    if not result.stdout or len(result.stdout) > 131_072:
        raise ConformanceError("Missing or unexpectedly large source file")
    return result.stdout


def run_offline(repo: Path, *, check_only: bool = False) -> int:
    doc = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
    rows = validate_contract(doc)
    origin = ("apps/api/app/main.py", _show(
        repo, PINNED_BASE, "apps/api/app/main.py"
    ))
    files: dict[str, bytes] = {origin[0]: origin[1]}
    for pr, sha, module, test in rows:
        files[module] = _show(repo, sha, module)
        files[test] = _show(repo, sha, test)
        # A synthetic module must not be mounted into the real API.
        module_name = Path(module).stem.encode("ascii")
        if module_name in origin[1]:
            raise ConformanceError(f"Unexpected API wiring for PR #{pr}")
    print("P2-04e offline snapshot: 4 isolated PR commits, 8 source/test files")
    print("No git merge, remote fetch, API, provider or database action")
    for pr, sha, _, _ in rows:
        print(f"  PR #{pr}: {sha}")
    if check_only:
        print("PASS: pinned sources available offline; tests not executed")
        return 0
    with tempfile.TemporaryDirectory(prefix="metaautomate-p2-04e-") as d:
        sandbox = Path(d)
        for path, content in files.items():
            target = sandbox / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(sandbox / "apps/api")
        cmd = [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "--import-mode=importlib",
            *(str(sandbox / row[3]) for row in rows),
        ]
        # Tests exercise only DEMO events; this subprocess runs from an
        # ephemeral directory and is NOT an OS sandbox or production approval.
        try:
            result = subprocess.run(
                cmd, cwd=sandbox, env=env, check=False, timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise ConformanceError("Offline synthetic test timeout")
        if result.returncode == 0:
            print("P2-04e source-coexistence smoke suite: PASS")
            print("Release gate: Phase 01 3/9 NO-GO; no merge approved")
        return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true",
                        help="validate local SHA objects and files; no pytest")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    try:
        return run_offline(repo, check_only=args.check_only)
    except (ConformanceError, OSError, json.JSONDecodeError) as exc:
        print(f"P2-04e DENIED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
