#!/bin/bash
# Database Restore Script
# Usage: ./restore.sh <backup_file.sql.gz>

set -e

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    BACKUP_DIR="${BACKUP_DIR:-/var/backups/ai-lead-system}"
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f | sort -r | head -10
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Database connection
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ai_leads}"
DB_USER="${DB_USER:-postgres}"

echo "==================================="
echo "DATABASE RESTORE"
echo "==================================="
echo "Backup file: $BACKUP_FILE"
echo "Target database: $DB_NAME"
echo ""

# Verify checksum if available
if [ -f "${BACKUP_FILE}.sha256" ]; then
    echo "Verifying checksum..."
    if sha256sum -c "${BACKUP_FILE}.sha256" > /dev/null 2>&1; then
        echo "✓ Checksum verified"
    else
        echo "✗ Checksum verification failed!"
        exit 1
    fi
fi

# Confirm restore
read -p "WARNING: This will overwrite the current database. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."

# Drop existing connections
echo "Terminating existing connections..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

# Drop and recreate database
echo "Recreating database..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" \
    > /dev/null 2>&1

PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d postgres \
    -c "CREATE DATABASE $DB_NAME;" \
    > /dev/null 2>&1

# Restore from backup
echo "Restoring data..."
gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    > /dev/null 2>&1

# Verify restore
echo "Verifying restore..."
TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo ""
echo "==================================="
echo "✓ Restore completed successfully!"
echo "Tables restored: $TABLE_COUNT"
echo "==================================="
