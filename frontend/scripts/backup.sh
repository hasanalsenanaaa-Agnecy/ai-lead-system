#!/bin/bash
# Database Backup Script
# Usage: ./backup.sh [daily|weekly|monthly]

set -e

# Configuration
BACKUP_TYPE="${1:-daily}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ai-lead-system}"
RETENTION_DAYS_DAILY=7
RETENTION_DAYS_WEEKLY=30
RETENTION_DAYS_MONTHLY=365

# Database connection (from environment or defaults)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ai_leads}"
DB_USER="${DB_USER:-postgres}"

# Create backup directory structure
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/monthly"

# Generate backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_TYPE}/backup_${TIMESTAMP}.sql.gz"

echo "Starting $BACKUP_TYPE backup..."
echo "Database: $DB_NAME"
echo "Output: $BACKUP_FILE"

# Create backup using pg_dump
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --verbose \
    2>/dev/null | gzip > "$BACKUP_FILE"

# Verify backup
if [ -s "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup created successfully: $BACKUP_SIZE"
else
    echo "✗ Backup failed or empty"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Create checksum
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"

# Cleanup old backups based on type
cleanup_old_backups() {
    local dir="$1"
    local days="$2"
    echo "Cleaning up backups older than $days days in $dir..."
    find "$dir" -name "backup_*.sql.gz*" -mtime +"$days" -delete 2>/dev/null || true
}

case "$BACKUP_TYPE" in
    daily)
        cleanup_old_backups "$BACKUP_DIR/daily" $RETENTION_DAYS_DAILY
        ;;
    weekly)
        cleanup_old_backups "$BACKUP_DIR/weekly" $RETENTION_DAYS_WEEKLY
        ;;
    monthly)
        cleanup_old_backups "$BACKUP_DIR/monthly" $RETENTION_DAYS_MONTHLY
        ;;
esac

# List recent backups
echo ""
echo "Recent $BACKUP_TYPE backups:"
ls -lh "$BACKUP_DIR/$BACKUP_TYPE" | tail -5

echo ""
echo "Backup complete!"
