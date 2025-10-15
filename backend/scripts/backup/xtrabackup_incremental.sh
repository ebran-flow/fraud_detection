#!/bin/bash
################################################################################
# XtraBackup Incremental Backup Script
# Creates an incremental backup based on the last full or incremental backup
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"
FULL_BACKUP_DIR="$BACKUP_BASE_DIR/full"
INCREMENTAL_BACKUP_DIR="$BACKUP_BASE_DIR/incremental"
LOG_DIR="$PROJECT_ROOT/logs"

# Load database credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "Error: .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

# Ensure directories exist
mkdir -p "$INCREMENTAL_BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Generate backup directory name with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$INCREMENTAL_BACKUP_DIR/inc_$TIMESTAMP"
LOG_FILE="$LOG_DIR/backup_incremental_$TIMESTAMP.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "XtraBackup Incremental Backup" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Check if xtrabackup is installed
if ! command -v xtrabackup &> /dev/null; then
    echo "Error: xtrabackup is not installed" | tee -a "$LOG_FILE"
    echo "Please run: sudo apt-get install percona-xtrabackup-82" | tee -a "$LOG_FILE"
    exit 1
fi

# Verify XtraBackup version
XTRABACKUP_VERSION=$(xtrabackup --version 2>&1 | grep -oP 'xtrabackup version \K[0-9.]+')
echo "XtraBackup version: $XTRABACKUP_VERSION" | tee -a "$LOG_FILE"

# Find the base directory (last full backup or last incremental)
if [ -f "$BACKUP_BASE_DIR/base_dir.txt" ]; then
    BASE_DIR=$(cat "$BACKUP_BASE_DIR/base_dir.txt")
else
    # Find most recent full backup
    BASE_DIR=$(ls -td "$FULL_BACKUP_DIR"/full_* 2>/dev/null | head -1)
    if [ -z "$BASE_DIR" ]; then
        echo "Error: No full backup found. Please run xtrabackup_full.sh first." | tee -a "$LOG_FILE"
        exit 1
    fi
fi

# Find the most recent incremental backup if it exists
LATEST_INC=$(ls -td "$INCREMENTAL_BACKUP_DIR"/inc_* 2>/dev/null | head -1)
if [ -n "$LATEST_INC" ]; then
    BASE_DIR="$LATEST_INC"
    echo "Base backup: $BASE_DIR (incremental)" | tee -a "$LOG_FILE"
else
    echo "Base backup: $BASE_DIR (full)" | tee -a "$LOG_FILE"
fi

if [ ! -d "$BASE_DIR" ]; then
    echo "Error: Base backup directory not found: $BASE_DIR" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Creating incremental backup to: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "Using credentials from .env: ${DB_HOST}:${DB_PORT} as ${DB_USER}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Perform incremental backup (needs sudo to access MySQL data directory)
sudo xtrabackup --backup \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --user="${DB_USER}" \
    --password="${DB_PASSWORD}" \
    --databases="${DB_NAME}" \
    --target-dir="$BACKUP_DIR" \
    --incremental-basedir="$BASE_DIR" \
    --parallel=4 \
    --compress \
    --compress-threads=4 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    # Fix ownership of backup directory (created by sudo)
    sudo chown -R $USER:$USER "$BACKUP_DIR"

    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Incremental Backup Completed Successfully" | tee -a "$LOG_FILE"
    echo "Location: $BACKUP_DIR" | tee -a "$LOG_FILE"
    echo "Size: $(du -sh "$BACKUP_DIR" | cut -f1)" | tee -a "$LOG_FILE"
    echo "Completed: $(date)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"

    # Update base directory for next incremental
    echo "$BACKUP_DIR" > "$BACKUP_BASE_DIR/base_dir.txt"

    # Clean up old incremental backups (keep last 7 days)
    cd "$INCREMENTAL_BACKUP_DIR"
    find . -maxdepth 1 -type d -name "inc_*" -mtime +7 -exec rm -rf {} \;
    echo "Cleaned up incremental backups older than 7 days" | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Incremental Backup Failed" | tee -a "$LOG_FILE"
    echo "Check log file: $LOG_FILE" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    exit 1
fi
