"""Safety checks of a deliberately mutating CI integration script.

These tests do not connect to any PostgreSQL server.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_amboy_m1_ci.py"


def _refusal(env):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0, result.stdout
    assert "REFUSED" in result.stderr + result.stdout


def test_local_machine_refused_even_when_database_name_matches():
    env = os.environ.copy()
    for key in ("GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_REPOSITORY"):
        env.pop(key, None)
    env.update({
        "DATABASE_URL": "postgresql://metaautomate:example@127.0.0.1:5433/metaautomate",
        "APP_DATABASE_URL": "postgresql://metaautomate_runtime:example@127.0.0.1:5433/metaautomate",
    })
    _refusal(env)


def test_spoofed_ci_flags_cannot_accidentally_target_kali_database():
    env = os.environ.copy()
    env.update({
        "GITHUB_ACTIONS": "true",
        "CI": "true",
        "GITHUB_RUN_ID": "123456",
        "GITHUB_REPOSITORY": "AhmadibOfficial/MetaAutomate",
        "DATABASE_URL": "postgresql://metaautomate:example@127.0.0.1:5433/metaautomate",
        "APP_DATABASE_URL": "postgresql://metaautomate_runtime:example@127.0.0.1:5433/metaautomate",
    })
    _refusal(env)


def test_wrong_repository_cannot_use_standard_ci_connection_string():
    env = os.environ.copy()
    env.update({
        "GITHUB_ACTIONS": "true",
        "CI": "true",
        "GITHUB_RUN_ID": "123456",
        "GITHUB_REPOSITORY": "another-owner/unreviewed-fork",
        "DATABASE_URL": "postgresql://metaautomate:ci_only_password@localhost:5432/metaautomate",
        "APP_DATABASE_URL": "postgresql://metaautomate_runtime:ci_runtime_password@localhost:5432/metaautomate",
    })
    _refusal(env)
