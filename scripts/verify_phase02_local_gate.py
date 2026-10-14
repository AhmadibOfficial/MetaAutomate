#!/usr/bin/env python3
"""One-command offline Kali acceptance for source-only Phase 02 branches.

Run AFTER a trusted `gh pr checkout N` to test all checked-out Phase 02
regressions without copying pytest options or using Docker/cloud services.
Does not fetch, merge, deploy, read secrets, touch business records or update PRs.
GitHub CI/review and production gates are separate.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYTEST_PREFIX = (
    "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--import-mode=importlib", "--tb=short",
)


class LocalGateError(RuntimeError):
    """Do not run the candidate suite with an unexpected checkout."""


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=True, capture_output=True, text=True, timeout=12,
        )
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired) as exc:
        raise LocalGateError("Git checkout inspection failed") from exc
    return result.stdout.strip()


def identify_checkout(expected_sha: str | None = None) -> tuple[str, str]:
    branch = _git("branch", "--show-current")
    sha = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=normal")
    if not branch.startswith("feat/p2-") or len(sha) != 40:
        raise LocalGateError("Not a named Phase 02 feature checkout")
    if status:
        raise LocalGateError(
            "Working tree is not clean; preserve local changes and retry"
        )
    if expected_sha is not None and sha != expected_sha:
        raise LocalGateError("HEAD does not match expected reviewed commit SHA")
    return branch, sha


def select_tests() -> tuple[Path, ...]:
    suites = tuple(sorted((ROOT / "tests").glob("test_phase02_*.py")))
    if not suites or any(not path.is_file() for path in suites):
        raise LocalGateError("No Phase 02 source regression files found")
    return suites


def run_local_gate(expected_sha: str | None = None) -> int:
    branch, sha = identify_checkout(expected_sha)
    suites = select_tests()
    print(f"PHASE02_LOCAL_HEAD={sha}", flush=True)
    print(f"PHASE02_BRANCH={branch}", flush=True)
    print(f"PHASE02_PYTHON={sys.version.split()[0]}", flush=True)
    print(f"PHASE02_SUITES={len(suites)}", flush=True)
    print("PHASE02_MODE=offline-source-tests; no merge/deploy/provisioning", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "apps/api")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, *PYTEST_PREFIX, *(str(x) for x in suites)]
    try:
        result = subprocess.run(
            command, cwd=ROOT, env=env, check=False, timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("PHASE02_RESULT=FAIL command unavailable or timed out", flush=True)
        return 2
    passed = result.returncode == 0
    print(f"PHASE02_RESULT={'PASS' if passed else 'FAIL'}", flush=True)
    print("PHASE01_FOUNDATION=3/9_NO_GO; INDEPENDENT_REVIEW=PENDING", flush=True)
    print("MERGE_PERMITTED=false; EXECUTION_AUTHORIZED=false", flush=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect-sha",
        help="optional exact reviewed head SHA; mismatch fails closed",
    )
    args = parser.parse_args()
    try:
        return run_local_gate(args.expect_sha)
    except LocalGateError as exc:
        print(f"PHASE02_RESULT=DENIED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
