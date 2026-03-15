#!/bin/sh
# API entrypoint — run migrations then start the server
# Equivalent to sports-data-admin's api-entrypoint.sh

set -e

echo "=== Fin Data Admin API Entrypoint ==="

# Run database migrations if alembic is available
if [ -f "alembic.ini" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete."
else
    echo "No alembic.ini found, skipping migrations."
fi

# Start the FastAPI server
echo "Starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS:-2}" --log-level "${LOG_LEVEL:-info}"
