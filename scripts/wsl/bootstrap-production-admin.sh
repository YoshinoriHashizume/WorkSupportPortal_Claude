#!/usr/bin/env bash
# Create first production admin user inside django_app container.
# Example: bash scripts/wsl/bootstrap-production-admin.sh 10001 橋爪 良典
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <username> <last-name> <first-name>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

docker compose -f docker-compose.prod.yml exec django_app \
  python manage.py bootstrap_production_admin \
  --username "$1" --last-name "$2" --first-name "$3"
