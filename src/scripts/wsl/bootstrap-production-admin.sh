#!/usr/bin/env bash
# Create first production admin user inside web-app container.
# Example (from repo root): bash src/scripts/wsl/bootstrap-production-admin.sh 51705 橋爪 良典
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <username> <last-name> <first-name>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

if [ ! -f docker-compose.production.yaml ]; then
  echo "ERROR: docker-compose.production.yaml not found in ${ROOT}" >&2
  exit 1
fi

docker compose -f docker-compose.production.yaml --env-file .env.production exec web-app \
  bash -lc "cd /django_app/src && python manage.py bootstrap_production_admin --username \"$1\" --last-name \"$2\" --first-name \"$3\""
