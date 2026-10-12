#!/usr/bin/env bash
# Run Python tests and Registry SQL integration on a disposable local database.
set -euo pipefail
cd "$(dirname "$0")/.."

make validate

docker compose up -d postgres
DB="metaautomate_ci_$(date +%Y%m%d_%H%M%S)_$$"
CREATED=0
cleanup() {
  if [[ "$CREATED" == "1" ]]; then
    echo "Cleaning up isolated CI database: $DB"
    docker compose exec -T postgres dropdb --if-exists --force -U metaautomate "$DB" || true
  fi
}
trap cleanup EXIT

printf 'Creating isolated CI database: %s\n' "$DB"
docker compose exec -T postgres createdb -U metaautomate "$DB"
CREATED=1

for migration in database/migrations/00[1-8]_*.sql; do
  echo "Applying: $migration"
  docker compose exec -T postgres \
    psql -X -q -v ON_ERROR_STOP=1 -U metaautomate -d "$DB" < "$migration"
done

docker compose run --rm -T \
  -v "$PWD:/workspace:ro" -w /workspace \
  api python scripts/seed_registry.py --database "$DB"

docker compose exec -T postgres \
  psql -X -v ON_ERROR_STOP=1 -U metaautomate -d "$DB" \
  < tests/sql/registry_integration.sql

echo 'PASS: local CI-equivalent validation completed'
