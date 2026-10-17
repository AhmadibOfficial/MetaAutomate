#!/usr/bin/env python3
"""Offline source-only evidence for P2-04q. Does NOT prove AI speech inference.

Works on the checked-out PRIVATE MetaAutomate repo; no model download,
network requests, GitHub branch-protection bypass, or automatic publishing.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys

TESTS = (
    "tests/test_p2_04p_creative_audio_assets.py",
    "tests/test_p2_04q_speech_offline.py",
    "tests/test_p2_04q_speech_authorization.py",
    "tests/test_p2_04q_speech_final_review.py",
    "tests/test_p2_04q_native_audio.py",
    "tests/test_p2_04q_operator_acceptance.py",
    "tests/test_p2_04q_review_signing.py",
    "tests/test_p2_04q_runtime_preflight.py",
)

def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def git(root: Path, *args: str) -> str:
    result = subprocess.run(("git", "-C", str(root), *args),
                            check=True, capture_output=True, text=True, timeout=15)
    return result.stdout.strip()

def private_output(folder: Path):
    if not folder.is_absolute() or folder.is_symlink():
        raise ValueError("Absolute private evidence directory required")
    if not folder.exists():
        folder.mkdir(mode=0o700)
    if (not folder.is_dir() or folder.resolve() != folder
        or stat.S_IMODE(folder.stat().st_mode) & 0o077):
        raise ValueError("Evidence directory must have 0700 permissions")

def run_gate(root: Path, expected_sha: str, folder: Path) -> dict:
    private_output(folder)
    record = {
        "schema_version": 1,
        "source": "LOCAL_OPERATOR_SOURCE_TEST_NOT_GITHUB_CI",
        "expected_commit_sha": expected_sha,
        "observed_commit_sha": None,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "tests_executed": False,
        "source_test_result": "HOLD_NOT_EXECUTED",
        "real_piper_inference_verified": False,
        "licensed_voice_rights_verified": False,
        "signed_human_review_observed": False,
        "github_required_checks_satisfied": False,
        "release_authorized": False,
    }
    log = ""
    try:
        if (type(expected_sha) is not str or len(expected_sha) != 40 or
            any(c not in "0123456789abcdef" for c in expected_sha)):
            raise ValueError("Expected exact lowercase 40-digit Git SHA")
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise ValueError("Absolute non-symlink source checkout required")
        root = root.resolve()
        head = git(root, "rev-parse", "HEAD")
        record["observed_commit_sha"] = head
        if head != expected_sha:
            raise ValueError("Checked-out SHA differs from the expected approved commit")
        if git(root, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("Tracked working copy dirty: cannot attribute tests to exact commit")
        paths = [root / p for p in TESTS]
        missing = [p.relative_to(root).as_posix() for p in paths if not p.is_file() or p.is_symlink()]
        if missing:
            raise ValueError("Speech test files unavailable: " + ", ".join(missing))
        record["test_file_sha256"] = {p.relative_to(root).as_posix(): sha(p) for p in paths}
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root / "apps" / "api")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in list(env):
            if key.startswith("MAT_SPEECH_") or key.startswith("MAT_CREATIVE_"):
                env.pop(key, None)
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS]
        result = subprocess.run(command, cwd=root, capture_output=True,
                                text=True, timeout=180, env=env)
        log = (result.stdout + "\n" + result.stderr)[:1_000_000]
        record["tests_executed"] = True
        record["test_exit_code"] = result.returncode
        record["source_test_result"] = (
            "SOURCE_TESTS_PASS_ONLY" if result.returncode == 0
            else "SOURCE_TESTS_FAILED")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        log = "HOLD: " + str(exc)
        record["hold_reason"] = str(exc)
    log_path = folder / "p2-04q-local-test.log"
    log_path.write_text(log, encoding="utf-8")
    log_path.chmod(0o600)
    record["test_log_sha256"] = sha(log_path)
    evidence = folder / "p2-04q-local-evidence.json"
    evidence.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    evidence.chmod(0o600)
    return record

def main() -> int:
    parser = argparse.ArgumentParser(description="Private P2-04q source-only local test evidence")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = run_gate(args.repo_root, args.expected_sha, args.evidence_dir)
    except (OSError, ValueError) as exc:
        parser.exit(2, "P2-04q local gate HOLD: " + str(exc) + "\n")
    print(json.dumps(record, sort_keys=True))
    return 0 if record["source_test_result"] == "SOURCE_TESTS_PASS_ONLY" else 2

if __name__ == "__main__":
    raise SystemExit(main())
