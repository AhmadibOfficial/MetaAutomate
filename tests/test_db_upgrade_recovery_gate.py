"""Guardrails for a human-approved local PostgreSQL upgrade.

These tests do not run a real migration. A PostgreSQL restore rehearsal remains
mandatory before any owner-authorized upgrade.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "db_upgrade_local.sh"


def test_no_authorization_exits_before_docker():
    result = subprocess.run(
        ["bash", str(SCRIPT)], input="CANCEL\n", text=True,
        capture_output=True, timeout=10, cwd=ROOT
    )
    assert result.returncode != 0
    assert "Cancelled before any Docker/database commands" in result.stderr


def test_backup_restored_before_any_schema_changes():
    script = SCRIPT.read_text(encoding="utf-8")
    archive = script.index("pg_dump -Fc")
    listing = script.index("pg_restore --list")
    restore = script.index("pg_restore --exit-on-error")
    compare = script.index('if [[ "$source_counts" != "$restored_counts" ]]')
    migration = script.index("Applying migration 009")
    assert archive < listing < restore < compare < migration
    assert "trap cleanup_restore EXIT" in script
    assert "dropdb -U metaautomate" in script


def test_local_only_gate_and_migration_scope():
    script = SCRIPT.read_text(encoding="utf-8")
    assert "UPGRADE LOCAL" in script
    assert "DOCKER_HOST" in script and "DOCKER_CONTEXT" in script
    assert "unix://*" in script
    for version in ("009_objective_operations", "010_workspace_sessions", "011_operational_assessments"):
        assert version + ".sql" in script
    assert "docker compose down -v" not in script
    assert "workspace-init" not in script
    assert "has_table_privilege" in script
    assert "trg_digital_assessments_no_update" in script
    assert "trg_digital_assessments_no_delete" in script


def test_readonly_preflight_rejects_remote_override():
    script = ROOT / "scripts" / "db_preflight_readonly.sh"
    import os
    environment = dict(os.environ)
    environment["DOCKER_HOST"] = "ssh://invalid.example"
    result = subprocess.run(
        ["bash", str(script)], cwd=ROOT, env=environment,
        text=True, capture_output=True, timeout=10
    )
    assert result.returncode != 0
    assert "Docker/Compose target overrides" in result.stderr


def test_readonly_preflight_contains_no_db_mutations():
    script = (ROOT / "scripts" / "db_preflight_readonly.sh").read_text(encoding="utf-8")
    assert "docker compose ps -q postgres" in script
    assert "SELECT current_database()" in script
    assert "SELECT count(*)" in script
    for forbidden in ("docker compose up ", "createdb ", "dropdb ", "pg_dump ", "pg_restore ", "ALTER TABLE ", "INSERT INTO "):
        assert forbidden not in script
