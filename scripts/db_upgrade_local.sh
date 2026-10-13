#!/usr/bin/env bash
set -euo pipefail
# Owner-only file permissions from the instant the dump is created.
umask 077
cd "$(dirname "$0")/.."
docker compose up -d postgres
base="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regclass('public.capability_executions') IS NOT NULL;")"
if [[ "$base" != "t" ]]; then echo "ERROR: migrations 001-008 are missing. No changes made." >&2; exit 1; fi
one="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regclass('public.api_access_tokens') IS NOT NULL;")"
two="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regclass('public.workspace_sessions') IS NOT NULL;")"
three="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regclass('public.digital_assessments') IS NOT NULL;")"
if [[ "$one" != "t" && "$two" == "t" ]]; then echo "ERROR: migration order inconsistent." >&2; exit 1; fi
if [[ "$three" == "t" && ( "$one" != "t" || "$two" != "t" ) ]]; then
  echo "ERROR: assessment schema installed without required workspace migrations." >&2; exit 1
fi
if [[ "$one" == "t" && "$two" == "t" && "$three" == "t" ]]; then
  echo "Workspace and Operational Core schema already installed."; exit 0
fi
if [[ "$one" == "t" && "$three" != "t" ]]; then
  role="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regrole('metaautomate_runtime') IS NOT NULL;")"
  if [[ "$role" != "t" ]]; then
    echo "ERROR: restricted runtime role missing; stop instead of partial migration." >&2
    exit 1
  fi
fi
backup_dir="$HOME/metaautomate-db-backups"
if [[ -L "$backup_dir" ]]; then
  echo "ERROR: refusing symlink backup directory" >&2; exit 1
fi
mkdir -p -m 700 "$backup_dir"
chmod 700 "$backup_dir"
backup="$(mktemp "$backup_dir/before-operational-core-$(date +%Y%m%d_%H%M%S)_XXXXXXXX.dump")"
verified=0
cleanup_backup() {
  if [[ "$verified" != "1" ]]; then
    rm -f -- "$backup"
    echo "ERROR: backup validation failed; no migration started." >&2
  fi
}
trap cleanup_backup ERR
echo "Creating restricted backup before changing existing development data"
docker compose exec -T postgres pg_dump -Fc -U metaautomate -d metaautomate > "$backup"
test -s "$backup"
docker compose exec -T postgres pg_restore --list < "$backup" > /dev/null
verified=1
trap - ERR
echo "Backup can be listed by pg_restore: $backup"

if [[ "$one" != "t" ]]; then
  echo "Applying migration 009"
  docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate < database/migrations/009_objective_operations.sql
fi
if [[ "$two" != "t" ]]; then
  echo "Applying migration 010"
  docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate < database/migrations/010_workspace_sessions.sql
fi
if [[ "$three" != "t" ]]; then
  echo "Applying migration 011 — Operational Core assessment evidence"
  docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate < database/migrations/011_operational_assessments.sql
fi
echo "PASS: backed-up development schema upgraded to Operational Core v1 without replaying older migrations"
