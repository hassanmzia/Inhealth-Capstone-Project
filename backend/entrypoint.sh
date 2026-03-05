#!/bin/bash
# =============================================================================
# InHealth Django Entrypoint
# 1. makemigrations  – auto-creates missing migration files for all apps
# 2. migrate_schemas – applies migrations to public + all tenant schemas
# =============================================================================

set -e

echo "[entrypoint] Creating missing migrations..."
python manage.py makemigrations --no-input

echo "[entrypoint] Running migrate_schemas..."
python manage.py migrate_schemas --verbosity 1

echo "[entrypoint] Starting server..."
exec "$@"
