#!/bin/sh
# Only initialize a NEW private PostgreSQL database; refuse existing tables.
set -eu
exists="$(psql -X -At -v ON_ERROR_STOP=1 -c "SELECT to_regclass('public.organizations') IS NOT NULL")"
if [ "$exists" = "t" ]; then
  echo "REFUSED: database is already initialized. Existing schemas require an approved migration." >&2
  exit 1
fi
for migration in /migrations/*.sql; do
  echo "Applying $migration"
  psql -X -v ON_ERROR_STOP=1 -f "$migration"
done
psql -X -v ON_ERROR_STOP=1 -v runtime_password="$APP_DB_PASSWORD" <<'SQL'
ALTER ROLE metaautomate_runtime LOGIN PASSWORD :'runtime_password';
SQL
echo "PASS: fresh database migrated and restricted runtime login provisioned"
