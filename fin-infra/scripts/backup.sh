#!/bin/bash
# Database backup script
# Usage: ./backup.sh [output_dir]
#
# Creates a timestamped pg_dump of the findata database.

set -euo pipefail

OUTPUT_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="findata_backup_${TIMESTAMP}.sql.gz"

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-findata}"
DB_USER="${POSTGRES_USER:-postgres}"

mkdir -p "$OUTPUT_DIR"

echo "Backing up ${DB_NAME}@${DB_HOST}:${DB_PORT}..."

PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --format=plain \
    | gzip > "${OUTPUT_DIR}/${FILENAME}"

echo "Backup saved to ${OUTPUT_DIR}/${FILENAME}"
echo "Size: $(du -h "${OUTPUT_DIR}/${FILENAME}" | cut -f1)"

# Keep only last 7 backups
cd "$OUTPUT_DIR"
ls -1t findata_backup_*.sql.gz | tail -n +8 | xargs rm -f 2>/dev/null || true
echo "Old backups cleaned (keeping last 7)."
