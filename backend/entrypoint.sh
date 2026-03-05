#!/bin/bash
# =============================================================================
# InHealth Django Entrypoint
# Runs migrate_schemas before starting the server so tenant schema tables
# are always up-to-date on every container start / redeploy.
# =============================================================================

set -e

echo "[entrypoint] Running migrate_schemas..."
python manage.py migrate_schemas --verbosity 1

echo "[entrypoint] Starting server..."
exec "$@"
