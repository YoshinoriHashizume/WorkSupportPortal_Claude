#!/bin/sh
set -e

if [ "$AUTH_DEV_MODE" = "true" ]; then
  echo "ERROR: AUTH_DEV_MODE must not be true in production." >&2
  exit 1
fi

if [ -z "$DATABASE_URL" ]; then
  if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "ERROR: POSTGRES_PASSWORD must be set in .env.production." >&2
    exit 1
  fi
  export DATABASE_URL="postgresql://${POSTGRES_USER:-worksupportportal}:${POSTGRES_PASSWORD}@django_postgres:5432/${POSTGRES_DB:-worksupportportal}"
fi

python manage.py migrate --noinput
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:3000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT_SECONDS:-120}"
