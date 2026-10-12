#!/usr/bin/env bash
# Transactional local-only migration 009; preserves existing data and backups.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d postgres
check="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate \
  -c "SELECT to_regclass('public.capability_executions') IS NOT NULL;")"
if [[ "$check" != "t" ]]; then
  echo "ERROR: migrations 001-008 not installed. No migration attempted." >&2
  exit 1
fi
already="$(docker compose exec -T postgres psql -X -A -t -U metaautomate -d metaautomate \
  -c "SELECT to_regclass('public.api_access_tokens') IS NOT NULL;")"
if [[ "$already" == "t" ]]; then
  echo "Migration 009 already installed. No database change."
  exit 0
fi
mkdir -p "$HOME/metaautomate-db-backups"
backup="$HOME/metaautomate-db-backups/before-ops-009-$(date +%Y%m%d_%H%M%S).dump"
echo "Creating local database backup: $backup"
docker compose exec -T postgres pg_dump -Fc -U metaautomate -d metaautomate > "$backup"
test -s "$backup"
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate \
  < database/migrations/009_objective_operations.sql
echo "PASS: objective operations schema installed; no previous tables dropped"
