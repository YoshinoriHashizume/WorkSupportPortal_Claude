#!/usr/bin/env bash
# Start production stack from repo root (Ubuntu / WSL2).
# Example: bash scripts/wsl/start-production.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f docker-compose.prod.yml ]; then
  echo "ERROR: docker-compose.prod.yml not found in ${ROOT}" >&2
  exit 1
fi

if [ ! -f .env.production ]; then
  if [ -f .env.production.example ]; then
    cp .env.production.example .env.production
    echo "Created .env.production from template."
    echo "Edit .env.production (POSTGRES_PASSWORD, DJANGO_SECRET_KEY, ORACLE_PASSWORD) then re-run." >&2
    exit 1
  fi
  echo "ERROR: .env.production is missing." >&2
  exit 1
fi

if grep -q '^POSTGRES_PASSWORD=$' .env.production || grep -q '^POSTGRES_PASSWORD=change-me' .env.production; then
  echo "ERROR: Set POSTGRES_PASSWORD in .env.production (not empty / not change-me)." >&2
  exit 1
fi

docker compose -f docker-compose.prod.yml up -d --build "$@"
