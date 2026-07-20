#!/usr/bin/env bash
# Start production stack from repo root (Ubuntu / WSL2).
# Example (from repo root): bash src/scripts/wsl/start-production.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

if [ ! -f docker-compose.production.yaml ]; then
  echo "ERROR: docker-compose.production.yaml not found in ${ROOT}" >&2
  exit 1
fi

if [ ! -f .env.production ]; then
  if [ -f .env.production.example ]; then
    cp .env.production.example .env.production
    echo "Created .env.production from template."
    echo "Edit .env.production (POSTGRES_PASSWORD, SECRET_KEY, ORACLE_PASSWORD) then re-run." >&2
    exit 1
  fi
  echo "ERROR: .env.production is missing." >&2
  exit 1
fi

if grep -q '^POSTGRES_PASSWORD=$' .env.production || grep -q '^POSTGRES_PASSWORD=change-me' .env.production || grep -q '^POSTGRES_PASSWORD=<強力なパスワードを設定>$' .env.production; then
  echo "ERROR: Set POSTGRES_PASSWORD in .env.production (not empty / not placeholder)." >&2
  exit 1
fi

docker compose -f docker-compose.production.yaml --env-file .env.production up -d --build "$@"
