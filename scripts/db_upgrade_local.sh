#!/usr/bin/env bash
set -euo pipefail
umask 077
printf 'LOCAL MetaAutomate DB upgrade (migrations 009–011). Type UPGRADE LOCAL to approve: '
read -r approval || approval=''
if [[ "$approval" != 'UPGRADE LOCAL' ]]; then
  echo 'Cancelled before any Docker/database commands.' >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  echo 'ERROR: missing local .env; refusing upgrade.' >&2; exit 1
fi
if [[ -n "${DOCKER_HOST:-}" || -n "${DOCKER_CONTEXT:-}" ]]; then
  echo 'ERROR: remote/overridden Docker contexts are not approved.' >&2; exit 1
fi
endpoint="$(docker context inspect --format '{{ (index .Endpoints "docker").Host }}')"
if [[ "$endpoint" != unix://* ]]; then
  echo 'ERROR: Docker endpoint is not a local Unix socket.' >&2; exit 1
fi
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
if [[ -L "$HOME/metaautomate-db-backups" ]]; then
  echo 'ERROR: backup directory must not be a symbolic link.' >&2; exit 1
fi
mkdir -p "$HOME/metaautomate-db-backups"
chmod 700 "$HOME/metaautomate-db-backups"
backup="$HOME/metaautomate-db-backups/before-operational-core-$(date +%Y%m%d_%H%M%S)-$.dump"
echo "Backing up existing database to $backup"
docker compose exec -T postgres pg_dump -Fc -U metaautomate -d metaautomate > "$backup"
test -s "$backup"
chmod 600 "$backup"
# A readable archive alone is insufficient: restore into a separate temporary
# LOCAL database and verify representative table counts before any migration.
docker compose exec -T postgres pg_restore --list < "$backup" > /dev/null
restore_db="metaautomate_restore_$(date +%s)_$"
restore_created=0
cleanup_restore() {
  if [[ "$restore_created" == '1' ]]; then
    docker compose exec -T postgres dropdb --if-exists --force -U metaautomate "$restore_db" ||
      echo "WARNING: temporary restore DB $restore_db needs manual cleanup" >&2
  fi
}
trap cleanup_restore EXIT
docker compose exec -T postgres createdb -T template0 -U metaautomate "$restore_db"
restore_created=1
docker compose exec -T postgres pg_restore --exit-on-error --no-owner --no-acl -U metaautomate -d "$restore_db" < "$backup"
source_counts="$(docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate -c "SELECT (SELECT count(*) FROM organizations)::text || ',' || (SELECT count(*) FROM capability_executions)::text;")"
restored_counts="$(docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 -U metaautomate -d "$restore_db" -c "SELECT (SELECT count(*) FROM organizations)::text || ',' || (SELECT count(*) FROM capability_executions)::text;")"
if [[ "$source_counts" != "$restored_counts" ]]; then
  echo 'ERROR: restore comparison failed; refusing migration.' >&2; exit 1
fi
docker compose exec -T postgres dropdb -U metaautomate "$restore_db"
restore_created=0
trap - EXIT
echo 'PASS: complete backup and temporary restore check.'
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
rls="$(docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate -c "SELECT relrowsecurity::text || ',' || relforcerowsecurity::text FROM pg_class WHERE oid='public.digital_assessments'::regclass;")"
if [[ "$rls" != 't,t' ]]; then
  echo 'ERROR: forced tenant RLS not enabled on digital_assessments.' >&2; exit 1
fi
permissions="$(docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate -c "SELECT has_table_privilege('metaautomate_runtime','public.digital_assessments','SELECT')::text || ',' || has_table_privilege('metaautomate_runtime','public.digital_assessments','INSERT')::text || ',' || has_table_privilege('metaautomate_runtime','public.digital_assessments','UPDATE')::text || ',' || has_table_privilege('metaautomate_runtime','public.digital_assessments','DELETE')::text;")"
if [[ "$permissions" != 't,t,f,f' ]]; then
  echo "ERROR: assessment table least-privilege grants failed: $permissions" >&2; exit 1
fi
immutability="$(docker compose exec -T postgres psql -X -A -t -v ON_ERROR_STOP=1 -U metaautomate -d metaautomate -c "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'public.digital_assessments'::regclass AND tgname IN ('trg_digital_assessments_no_update','trg_digital_assessments_no_delete') AND tgenabled <> 'D';")"
if [[ "$immutability" != '2' ]]; then
  echo 'ERROR: assessment mutation prevention triggers are absent or disabled.' >&2; exit 1
fi
echo "PASS: migrations installed, forced RLS checked. Backup retained at $backup"
echo 'NEXT: independently verify tenant isolation, runtime grants, audit and application browser flows before release.'
