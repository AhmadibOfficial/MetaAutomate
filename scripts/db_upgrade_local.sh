#!/usr/bin/env bash
set -euo pipefail
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
mkdir -p "$HOME/metaautomate-db-backups"
backup="$HOME/metaautomate-db-backups/before-workspace-$(date +%Y%m%d_%H%M%S).dump"
echo "Backing up existing database to $backup"
docker compose exec -T postgres pg_dump -Fc -U metaautomate -d metaautomate > "$backup"
test -s "$backup"
chmod 600 "$backup"
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
