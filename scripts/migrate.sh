#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# These inherited SQL files are drafts; review them before production use.
for f in database/migrations/*.sql; do
  echo "Applying $f"
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-metaautomate}" -d "${POSTGRES_DB:-metaautomate}" < "$f"
done
