#!/bin/bash
################################################################################
# mydumper Full Backup Script
# Fast, parallel backup using mydumper (works with MySQL 8.2)
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/mydumper"
LOG_DIR="$PROJECT_ROOT/logs"

# Load database credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "Error: .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

# Ensure directories exist
mkdir -p "$BACKUP_BASE_DIR"
mkdir -p "$LOG_DIR"

# Generate backup directory name with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/backup_$TIMESTAMP"
LOG_FILE="$LOG_DIR/mydumper_backup_$TIMESTAMP.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "mydumper Database Backup" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Check if mydumper is installed
if ! command -v mydumper &> /dev/null; then
    echo "Error: mydumper is not installed" | tee -a "$LOG_FILE"
    echo "Please run: sudo apt-get install mydumper" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if MySQL is accessible
if ! mysql -h "${DB_HOST:-127.0.0.1}" -P "${DB_PORT:-3307}" -u "${DB_USER:-root}" -p"$DB_PASSWORD" -e "SELECT 1" &> /dev/null; then
    echo "Error: Cannot connect to MySQL database" | tee -a "$LOG_FILE"
    exit 1
fi

# Get database size before backup
DB_SIZE=$(mysql -h "${DB_HOST:-127.0.0.1}" -P "${DB_PORT:-3307}" -u "${DB_USER:-root}" -p"$DB_PASSWORD" -e "
    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024 / 1024, 2) as size_gb
    FROM information_schema.tables
    WHERE table_schema = 'fraud_detection'
" -sN)

echo "Database size: ${DB_SIZE}GB" | tee -a "$LOG_FILE"
echo "Backup directory: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Perform backup with mydumper
echo "Starting mydumper backup..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

mydumper \
    --host="${DB_HOST:-127.0.0.1}" \
    --port="${DB_PORT:-3307}" \
    --user="${DB_USER:-root}" \
    --password="$DB_PASSWORD" \
    --database=fraud_detection \
    --outputdir="$BACKUP_DIR" \
    --threads=4 \
    --compress \
    --build-empty-files \
    --long-query-guard=3600 \
    --trx-consistency-only \
    --verbose=3 \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Backup Completed Successfully" | tee -a "$LOG_FILE"
    echo "Location: $BACKUP_DIR" | tee -a "$LOG_FILE"

    # Calculate compressed backup size
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo "Backup size: $BACKUP_SIZE" | tee -a "$LOG_FILE"

    # Count files
    FILE_COUNT=$(find "$BACKUP_DIR" -type f | wc -l)
    echo "Files created: $FILE_COUNT" | tee -a "$LOG_FILE"

    echo "Completed: $(date)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"

    # Create a marker file for latest backup
    echo "$TIMESTAMP" > "$BACKUP_BASE_DIR/latest_backup.txt"
    echo "$BACKUP_DIR" > "$BACKUP_BASE_DIR/latest_backup_path.txt"

    # Clean up old backups (keep last 7)
    cd "$BACKUP_BASE_DIR"
    ls -td backup_* 2>/dev/null | tail -n +8 | xargs -r rm -rf

    REMAINING_BACKUPS=$(ls -1d backup_* 2>/dev/null | wc -l)
    echo "" | tee -a "$LOG_FILE"
    echo "Cleaned up old backups (keeping last 7)" | tee -a "$LOG_FILE"
    echo "Total backups: $REMAINING_BACKUPS" | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Backup Failed" | tee -a "$LOG_FILE"
    echo "Check log file: $LOG_FILE" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    exit 1
fi
