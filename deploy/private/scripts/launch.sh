#!/usr/bin/env bash
# One guarded INITIAL launch on a Linux VM already joined to Tailscale.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
ENV="$ROOT/deploy/private/.env"
STACK="$ROOT/deploy/private/compose.yaml"
if [[ ! -f "$ENV" ]]; then
  echo "ERROR: Copy deploy/private/.env.example into a private 0600 .env." >&2
  exit 1
fi
if [[ "$(stat -c %a "$ENV")" != "600" ]]; then
  echo "ERROR: deploy/private/.env must be chmod 600." >&2
  exit 1
fi
# Only source the administrator-maintained env file on the trusted VM.
set -a
source "$ENV"
set +a
for name in POSTGRES_ADMIN_PASSWORD APP_DB_PASSWORD OIDC_ISSUER OIDC_CLIENT_ID \
  OIDC_CLIENT_SECRET OIDC_REDIRECT_URI OIDC_STATE_SECRET WORKSPACE_ORIGIN \
  META_OWNER_SUBJECT META_OWNER_EMAIL META_ORG_SLUG; do
  if [[ -z "${!name:-}" || "${!name}" == REPLACE* ]]; then
    echo "ERROR: Missing or placeholder setting: $name" >&2
    exit 1
  fi
done
if [[ "$POSTGRES_ADMIN_PASSWORD" == "$APP_DB_PASSWORD" ]]; then
  echo "ERROR: Migration and runtime passwords must differ." >&2; exit 1
fi
if [[ ${#OIDC_STATE_SECRET} -lt 48 ]]; then
  echo "ERROR: OIDC_STATE_SECRET must be at least 48 characters." >&2; exit 1
fi
if [[ ! "$WORKSPACE_ORIGIN" =~ ^https://[a-z0-9.-]+\.ts\.net$ ]]; then
  echo "ERROR: WORKSPACE_ORIGIN must be a private HTTPS Tailscale DNS name." >&2; exit 1
fi
if [[ "$OIDC_REDIRECT_URI" != "$WORKSPACE_ORIGIN/v1/workspace/oidc/callback" ]]; then
  echo "ERROR: OIDC redirect must be the exact private workspace callback." >&2; exit 1
fi
if [[ "$OIDC_ISSUER" != https://* ]]; then
  echo "ERROR: OIDC issuer must use HTTPS." >&2; exit 1
fi
if ! command -v tailscale >/dev/null || ! tailscale status >/dev/null 2>&1; then
  echo "ERROR: Host must be signed into approved Tailscale tailnet." >&2; exit 1
fi
docker compose --env-file "$ENV" -f "$STACK" --profile admin config --quiet
echo
echo "Private initial deployment plan:"
echo "  Host: $WORKSPACE_ORIGIN"
echo "  Database: new isolated PostgreSQL volume"
echo "  Identity: OIDC only; owner identity provisioned explicitly"
echo "  Capabilities: DRAFT; execution disabled"
echo "  Infrastructure spending and tailnet access must already be approved."
printf 'Type PRIVATE-LAUNCH to initialize and enable private Tailscale Serve: '
read -r answer
if [[ "$answer" != "PRIVATE-LAUNCH" ]]; then
  echo "Cancelled without deployment."; exit 1
fi
docker compose --env-file "$ENV" -f "$STACK" up -d postgres
docker compose --env-file "$ENV" -f "$STACK" --profile admin run --rm migrator
docker compose --env-file "$ENV" -f "$STACK" --profile admin run --rm admin /opt/meta-scripts/seed_registry.py
docker compose --env-file "$ENV" -f "$STACK" --profile admin run --rm admin \
  /opt/meta-scripts/provision_oidc_identity.py \
  --issuer "$OIDC_ISSUER" --subject "$META_OWNER_SUBJECT" \
  --email "$META_OWNER_EMAIL" --organization "$META_ORG_SLUG" --role OWNER --approve
docker compose --env-file "$ENV" -f "$STACK" up -d api
for attempt in $(seq 1 35); do
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then break; fi
  sleep 2
done
curl --fail --silent http://127.0.0.1:8080/health >/dev/null
# Tailscale Serve is tailnet-only; never use Funnel for this release.
tailscale serve --bg 8080
echo "PRIVATE CLOUD WORKSPACE STARTED: $WORKSPACE_ORIGIN"
echo "Validate actual SSO login, restrictions and recovery-capable backups first."
