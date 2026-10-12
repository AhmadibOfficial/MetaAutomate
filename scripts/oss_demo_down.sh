#!/usr/bin/env bash
# Only stops the separate OSS contributor demo; retains its PostgreSQL volume.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV="$PWD/examples/oss-demo/.env"
if [[ ! -f "$ENV" ]]; then echo "No demo environment found."; exit 0; fi
docker compose --project-name metaautomate-oss-demo \
  --env-file "$ENV" -f "$PWD/examples/oss-demo/compose.yaml" down
echo "Contributor demo stopped. Database volume and credentials preserved."
