#!/usr/bin/env python3
"""P2-060/P2-061 offline source checks with read-only checkout protection.

GitHub-hosted Actions may be blocked by account billing. This script produces
developer-local evidence only. It does NOT replace independent GitHub checks,
authenticated browser acceptance, production release approval, or a security audit.
Never merges, deploys, migrates, modifies project code, or touches cloud services.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TEST_FILES = (
    "tests/test_p2_061_secure_data_lab.py",
    "tests/test_p2_061_data_api_admission.py",
    "tests/test_p2_061_private_vault_ui.py",
    "tests/test_p2_061_offline_runner.py",
)
SOURCE_FILES = (
    "apps/api/app/secure_inventory_lab.py",
    "apps/api/app/secure_data_lab_api.py",
    "apps/api/app/main.py",
    "apps/api/app/workspace_auth.py",
)
NODE_FILES = (
    "apps/web/assets/app.js",
    "apps/site/assets/campaign-engine.js",
    "apps/site/assets/campaign-workbench.js",
)
CAMPAIGN_TEST = "tests/campaign_engine.test.cjs"
GATE = "LOCAL_SOURCE_CHECK_ONLY"


def command(args: list[str], *, timeout: int = 120) -> dict:
    started = time.monotonic()
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTEST_ADDOPTS"] = "-p no:cacheprovider"
    environment["MAT_DATA_LAB_ENABLED"] = "0"
    environment["MAT_PILOT_OUTCOMES_ENABLED"] = "0"
    try:
        proc = subprocess.run(
            args, cwd=ROOT, env=environment,
            text=True, capture_output=True, check=False, timeout=timeout,
        )
        return {"status": "PASS" if proc.returncode == 0 else "FAIL",
                "exit_code": proc.returncode, "seconds": round(time.monotonic()-started, 3),
                "output_tail": (proc.stdout + "\n" + proc.stderr)[-1600:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "BLOCKED", "exit_code": None,
                "seconds": round(time.monotonic()-started, 3),
                "output_tail": str(exc)[:350]}


def _git(*args: str) -> str:
    run = subprocess.run(["git", *args], cwd=ROOT, check=True,
                         text=True, capture_output=True, timeout=15)
    return run.stdout.strip()


def validate_source() -> dict:
    try:
        for name in SOURCE_FILES:
            path = ROOT / name
            compile(path.read_bytes(), str(path), "exec")
        return {"status": "PASS", "exit_code": 0,
                "output_tail": "Compiled four Python sources in memory (no .pyc files)"}
    except (OSError, SyntaxError, UnicodeError) as exc:
        return {"status": "FAIL", "exit_code": 1, "output_tail": str(exc)[:350]}


def generate_report() -> dict:
    report: dict = {
        "gate": GATE, "github_ci_verified": False,
        "merge_approved": False, "deployment_approved": False,
        "tenant_data_used": "SYNTHETIC_TEST_FIXTURES_ONLY",
        "tests": {},
    }
    try:
        if Path(_git("rev-parse", "--show-toplevel")).resolve() != ROOT.resolve():
            raise ValueError("Repository root does not match source file root")
        report["commit"] = _git("rev-parse", "HEAD")
        report["branch"] = _git("branch", "--show-current")
        before = _git("status", "--porcelain=v1", "--untracked-files=all")
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        report.update(result="BLOCKED", reason="Could not verify local repository: " + str(exc)[:250])
        return report
    if before:
        report.update(result="BLOCKED", reason="Working tree contains existing changes; no validation commands executed")
        return report
    required = (*SOURCE_FILES, *TEST_FILES, *NODE_FILES, CAMPAIGN_TEST)
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        report.update(result="BLOCKED", reason="Expected source files missing",
                      missing=missing)
        return report
    report["tests"]["python_compile"] = validate_source()
    report["tests"]["private_data_lab"] = command([
        sys.executable, "-m", "pytest", "-q", *TEST_FILES], timeout=120)
    if shutil.which("node"):
        for source in NODE_FILES:
            report["tests"]["javascript_syntax:" + source] = command(
                ["node", "--check", source], timeout=15)
        report["tests"]["p2_060_campaign_engine"] = command(
            ["node", "--test", CAMPAIGN_TEST], timeout=30)
    else:
        report["tests"]["node_runtime"] = {
            "status": "BLOCKED", "exit_code": None,
            "output_tail": "Node.js unavailable; JavaScript and campaign tests not run"}
    try:
        after = _git("status", "--porcelain=v1", "--untracked-files=all")
        report["working_tree_unchanged"] = before == after
    except (OSError, subprocess.CalledProcessError):
        report["working_tree_unchanged"] = False
    ok = (report["working_tree_unchanged"] and
          all(test["status"] == "PASS" for test in report["tests"].values()))
    report["result"] = "LOCAL_TESTS_PASS" if ok else "BLOCKED_OR_FAILED"
    report["remaining_release_gates"] = [
        "GitHub-hosted CI blocked by account billing/spending limit until resolved",
        "Independent authenticated private API and browser acceptance",
        "Real OIDC/MFA, forced PostgreSQL RLS, managed keys and restoration tests",
        "Independent merge and deployment authorization",
    ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path,
                        help="Optional JSON evidence file OUTSIDE the repository")
    args = parser.parse_args()
    result = generate_report()
    report = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(report)
    if args.report is not None:
        path = args.report.expanduser().resolve()
        if path.is_relative_to(ROOT.resolve()):
            print("Refusing to write evidence inside the source repository", file=sys.stderr)
            return 2
        if not path.parent.is_dir() or path.is_symlink():
            print("Evidence parent missing or file is a symlink", file=sys.stderr)
            return 2
        if path.exists():
            print("Evidence file already exists; refusing overwrite", file=sys.stderr)
            return 2
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(report)
    return 0 if result.get("result") == "LOCAL_TESTS_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
