"""Regression guards for owner-controlled local Operational Core database upgrades."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=(ROOT/"scripts/db_upgrade_local.sh").read_text()

def test_backup_is_restricted_and_readable_before_migration():
    for s in ("umask 077", 'if [[ -L "$backup_dir" ]]', 'mkdir -p -m 700 "$backup_dir"',
              'backup="$(mktemp ', "pg_dump -Fc", "pg_restore --list",
              "trap cleanup_backup ERR"):
        assert s in script
    assert script.index("pg_restore --list") < script.index('echo "Applying migration 011')

def test_does_not_destroy_old_database_or_rotate_login():
    for forbidden in ("docker compose down -v", "workspace_init.sh", "bootstrap_workspace.py",
                      "database/migrations/001_"):
        assert forbidden not in script
    for expected in ("009_objective_operations.sql", "010_workspace_sessions.sql",
                     "011_operational_assessments.sql"):
        assert expected in script

def test_production_staging_release_is_gated():
    document=(ROOT/"docs/deployment/OPERATIONAL_CORE_PRIVATE_STAGING.md").read_text()
    for requirement in ("NO-GO", "OIDC", "network-level", "Restore drill",
                        "No external customer access"):
        assert requirement in document
