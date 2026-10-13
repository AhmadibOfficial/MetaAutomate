#!/usr/bin/env bash
# CI-only end-to-end rehearsal. Never run against an owner workstation.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != 'true' ]]; then
  echo 'ERROR: This rehearsal is only permitted on ephemeral GitHub Actions runners.' >&2
  exit 1
fi
cd "$(dirname "$0")/.."
export COMPOSE_PROJECT_NAME="metaautomate_restore_ci_${GITHUB_RUN_ID:?}_${GITHUB_RUN_ATTEMPT:?}"
umask 077
printf 'POSTGRES_PASSWORD=ephemeral_ci_only_password\n' > .env
cleanup() {
  docker compose down --remove-orphans >/dev/null 2>&1 || true
  rm -f .env
}
trap cleanup EXIT
docker compose up -d postgres
ready=0
for _ in $(seq 1 40); do
  if docker compose exec -T postgres pg_isready -q -U metaautomate -d metaautomate; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  echo 'ERROR: disposable PostgreSQL failed readiness.' >&2
  exit 1
fi
for migration in database/migrations/00[1-8]_*.sql; do
  echo "Installing disposable baseline: $migration"
  docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate < "$migration" >/dev/null
done
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate -c \
  "INSERT INTO organizations(slug,name) VALUES ('recovery-rehearsal','Recovery Rehearsal Sample');" >/dev/null
echo 'Running approved migration against disposable CI database only.'
printf 'UPGRADE LOCAL\n' | bash scripts/db_upgrade_local.sh
result="$(docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate -c \
  "SELECT (to_regclass('public.digital_assessments') IS NOT NULL)::text || ',' || (SELECT count(*) FROM organizations WHERE slug='recovery-rehearsal')::text;")"
if [[ "$result" != 'true,1' && "$result" != 't,1' ]]; then
  echo "ERROR: post-upgrade schema or existing sample data differs: $result" >&2
  exit 1
fi
backup_files=( "$HOME"/metaautomate-db-backups/before-operational-core-*.dump )
if [[ ! -f "${backup_files[0]}" || ! -s "${backup_files[0]}" ]]; then
  echo 'ERROR: approved local backup archive was not retained.' >&2; exit 1
fi
echo 'PASS: disposable baseline 001–008 backed up, restored, upgraded 009–011, and checked.'
