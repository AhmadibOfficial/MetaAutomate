#!/usr/bin/env bash
# Contributor quickstart with a dedicated Docker Compose project, port and secrets.
# Never calls scripts/workspace_init.sh or touches the root .env.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
DEMO_DIR="$ROOT/examples/oss-demo"
ENV="$DEMO_DIR/.env"
KEY="$DEMO_DIR/.workspace-access-key"
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Engine and Compose v2 are required." >&2
  exit 1
fi
if [[ -L "$ENV" || -L "$KEY" ]]; then
  echo "ERROR: refusing to read demo credentials through symlinks." >&2
  exit 1
fi
if [[ ! -e "$ENV" && -e "$KEY" ]]; then
  echo "ERROR: demo access key exists but .env is missing. No changes made." >&2
  exit 1
fi
if [[ ! -e "$ENV" ]]; then
  python3 - <<'PY'
import os
from pathlib import Path
import secrets

directory=Path("examples/oss-demo")
token="mat_dev_"+secrets.token_urlsafe(32)
config={
    "DEMO_DB_PASSWORD":secrets.token_hex(32),
    "DEMO_RUNTIME_PASSWORD":secrets.token_hex(32),
    "DEMO_REGISTRY_KEY":secrets.token_urlsafe(32),
    "DEMO_ACCESS_KEY":token,
}
for path,data in (
    (directory/".env","".join(f"{k}={v}\n" for k,v in config.items())),
    (directory/".workspace-access-key",token+"\n"),
):
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as out:
        out.write(data)
print("Created isolated private demo credentials (not printed)")
PY
fi
if [[ ! -s "$ENV" || ! -s "$KEY" ]]; then
  echo "ERROR: demo credentials are incomplete; refusing database initialization." >&2
  exit 1
fi
if [[ "$(stat -c %a "$ENV")" != "600" || "$(stat -c %a "$KEY")" != "600" ]]; then
  echo "ERROR: demo credential files must have mode 0600." >&2
  exit 1
fi
COMPOSE=(docker compose --project-name metaautomate-oss-demo --env-file "$ENV" -f "$DEMO_DIR/compose.yaml")
"${COMPOSE[@]}" up -d postgres
existing="$("${COMPOSE[@]}" exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regclass('public.organizations') IS NOT NULL;")"
if [[ "$existing" != "t" && "$existing" != "f" ]]; then
  echo "ERROR: unexpected database response; refusing migrations." >&2
  exit 1
fi
if [[ "$existing" == "f" ]]; then
  echo "Initializing separate open-source demo database."
  for migration in database/migrations/*.sql; do
    echo "Applying $migration"
    "${COMPOSE[@]}" exec -T postgres psql -X -v ON_ERROR_STOP=1 \
      -U metaautomate -d metaautomate < "$migration"
  done
else
  complete="$("${COMPOSE[@]}" exec -T postgres psql -X -A -t -U metaautomate -d metaautomate -c "SELECT to_regclass('public.workspace_sessions') IS NOT NULL;")"
  if [[ "$complete" != "t" ]]; then
    echo "ERROR: demo schema incomplete; no migrations replayed." >&2
    exit 1
  fi
fi
"${COMPOSE[@]}" run --rm -T -v "$ROOT:/workspace:ro" -w /workspace \
  api python scripts/seed_registry.py
"${COMPOSE[@]}" --profile bootstrap run --rm -T init
"${COMPOSE[@]}" up -d --build api
for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:18000/health >/dev/null 2>&1; then
    echo "SUCCESS: http://127.0.0.1:18000/"
    echo "Private demo sign-in key is in: $KEY"
    echo "The existing Kali MetaAutomate project was not changed."
    exit 0
  fi
  sleep 2
done
echo "ERROR: demo API did not become healthy. See Compose logs." >&2
exit 1
