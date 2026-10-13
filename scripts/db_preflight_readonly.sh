#!/usr/bin/env bash
# Read-only identity and schema check before human-approved migration.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -n "${DOCKER_HOST:-}" || -n "${DOCKER_CONTEXT:-}" || -n "${COMPOSE_FILE:-}" || -n "${COMPOSE_PROJECT_NAME:-}" ]]; then
  echo 'BLOCKED: Docker/Compose target overrides must be unset for this local preflight.' >&2
  exit 1
fi
if [[ ! -f .env || -L .env ]]; then
  echo 'BLOCKED: a real, private local .env file is required.' >&2
  exit 1
fi
endpoint="$(docker context inspect --format '{{ (index .Endpoints "docker").Host }}')"
if [[ "$endpoint" != unix://* ]]; then
  echo 'BLOCKED: Docker context is not a local Unix socket.' >&2
  exit 1
fi
if ! docker compose ps -q postgres | grep -q .; then
  echo 'BLOCKED: existing local PostgreSQL container is not running.' >&2
  exit 1
fi
sql() {
  docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 \
    -U metaautomate -d metaautomate -c "$1"
}
identity="$(sql 'SELECT current_database();')"
if [[ "$identity" != metaautomate ]]; then
  echo 'BLOCKED: unexpected database name.' >&2
  exit 1
fi
baseline="$(sql "SELECT (to_regclass('public.capability_executions') IS NOT NULL)::text;")"
if [[ "$baseline" != true && "$baseline" != t ]]; then
  echo 'BLOCKED: expected baseline migration 008 is missing.' >&2
  exit 1
fi
schema="$(sql "SELECT
  (to_regclass('public.api_access_tokens') IS NOT NULL)::int::text || ',' ||
  (to_regclass('public.workspace_sessions') IS NOT NULL)::int::text || ',' ||
  (to_regclass('public.digital_assessments') IS NOT NULL)::int::text;")"
organizations="$(sql 'SELECT count(*) FROM public.organizations;')"
capabilities="$(sql 'SELECT count(*) FROM public.capability_executions;')"
echo 'READ-ONLY LOCAL DB PREFLIGHT'
printf 'Database: %s\n' "$identity"
printf 'Migrations 009,010,011 installed (0=no, 1=yes): %s\n' "$schema"
printf 'Organization records: %s\n' "$organizations"
printf 'Execution ledger records: %s\n' "$capabilities"
echo 'No backup, migration, credential change, or container start was performed.'
echo 'Operator must still approve the separate backup/restore/migration command.'
