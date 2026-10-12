#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "MetaAutomate local workspace initialization"
echo "This backs up and upgrades your existing local database and rotates local credentials."
if [[ ! -f .env ]]; then echo "ERROR: .env not found. No changes made." >&2; exit 1; fi
printf 'Type INIT to authorize local database migration and credential setup: '
read -r answer
if [[ "$answer" != "INIT" ]]; then echo "Cancelled."; exit 1; fi
bash scripts/db_upgrade_local.sh
docker compose build api
docker compose run --rm -T --user "$(id -u):$(id -g)" -v "$PWD:/workspace" -w /workspace api python scripts/bootstrap_workspace.py
docker compose up -d api
echo "Workspace: http://127.0.0.1:8000/"
echo "Use your private sign-in key from ~/metaautomate-github/.workspace-access-key"
