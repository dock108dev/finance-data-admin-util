#!/bin/bash
# Database restore script
# Usage: ./restore.sh <backup_file>
#
# Restores a findata database from a pg_dump backup.

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -1t backups/findata_backup_*.sql.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-findata}"
DB_USER="${POSTGRES_USER:-postgres}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will drop and recreate the '${DB_NAME}' database."
echo "Press Ctrl+C to cancel, or Enter to continue..."
read -r

echo "Restoring from ${BACKUP_FILE}..."

PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" dropdb \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    --if-exists "$DB_NAME"

PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" createdb \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    "$DB_NAME"

gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    -d "$DB_NAME" --quiet

echo "Restore complete."
