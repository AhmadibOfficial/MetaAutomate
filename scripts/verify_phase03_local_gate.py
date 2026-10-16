#!/usr/bin/env python3
"""One-command Phase 03 offline source regression; does not grant real execution.

Requires clean named P3 branch and exact SHA; never fetches, merges, deploys,
provisions infrastructure, contacts customers or uses real API credentials.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}\Z")


class SourceGateDenied(ValueError):
    """Local tree is not an accepted Phase 03 source checkout."""


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=True, capture_output=True, text=True, timeout=12,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise SourceGateDenied("Unable to inspect local Git checkout") from exc
    return result.stdout.strip()


def identify(expected: str) -> tuple[str, str]:
    if type(expected) is not str or SHA.fullmatch(expected) is None:
        raise SourceGateDenied("Exact 40-char expected SHA is required")
    branch = _git("branch", "--show-current")
    sha = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain", "--untracked-files=normal")
    if (
        not branch.startswith("feat/p3-")
        or SHA.fullmatch(sha) is None
        or sha != expected
        or dirty
    ):
        raise SourceGateDenied("Wrong Phase 03 branch/SHA or dirty local checkout")
    return branch, sha


def run_gate(expected: str) -> int:
    branch, sha = identify(expected)
    tests = sorted((ROOT / "tests").glob("test_phase03_*.py"))
    if not tests or any(not t.is_file() for t in tests):
        raise SourceGateDenied("No checked-out Phase 03 tests")
    print(f"PHASE03_LOCAL_HEAD={sha}", flush=True)
    print(f"PHASE03_BRANCH={branch}", flush=True)
    print(f"PHASE03_PYTHON={sys.version.split()[0]}", flush=True)
    print(f"PHASE03_SUITES={len(tests)}", flush=True)
    print("PHASE03_MODE=source-offline-deny; provider_call=false", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "apps/api")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--import-mode=importlib", "--tb=short", *map(str, tests)],
            env=env, cwd=ROOT, check=False, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("PHASE03_SOURCE_RESULT=FAIL", flush=True)
        return 2
    print(
        f"PHASE03_SOURCE_RESULT={'PASS' if result.returncode == 0 else 'FAIL'}",
        flush=True,
    )
    print("PHASE01_FOUNDATION=3/9_NO_GO; PHASE02_OPERATIONAL=NO_GO", flush=True)
    print("LIVE_EXECUTION_AUTHORIZED=false; MERGE_PERMITTED=false", flush=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-sha", required=True)
    args = parser.parse_args()
    try:
        return run_gate(args.expect_sha)
    except SourceGateDenied as exc:
        print(f"PHASE03_SOURCE_RESULT=DENIED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
