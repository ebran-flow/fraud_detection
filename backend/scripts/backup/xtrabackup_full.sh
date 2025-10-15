#!/bin/bash
################################################################################
# XtraBackup Full Backup Script
# Creates a complete backup of the fraud_detection database
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"
FULL_BACKUP_DIR="$BACKUP_BASE_DIR/full"
LOG_DIR="$PROJECT_ROOT/logs"

# Load database credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "Error: .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

# Ensure directories exist
mkdir -p "$FULL_BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Generate backup directory name with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$FULL_BACKUP_DIR/full_$TIMESTAMP"
LOG_FILE="$LOG_DIR/backup_full_$TIMESTAMP.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "XtraBackup Full Backup" | tee -a "$LOG_FILE"
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

# Check if MySQL is accessible (using credentials from .env)
if ! mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT 1" &> /dev/null; then
    echo "Error: Cannot connect to MySQL database" | tee -a "$LOG_FILE"
    echo "Host: ${DB_HOST}:${DB_PORT}, User: ${DB_USER}" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Connected to MySQL: ${DB_HOST}:${DB_PORT} as ${DB_USER}" | tee -a "$LOG_FILE"

# Perform full backup
echo "Creating full backup to: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# XtraBackup needs sudo to access MySQL data directory
sudo xtrabackup --backup \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --user="${DB_USER}" \
    --password="${DB_PASSWORD}" \
    --databases="${DB_NAME}" \
    --target-dir="$BACKUP_DIR" \
    --parallel=4 \
    --compress \
    --compress-threads=4 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    # Fix ownership of backup directory (created by sudo)
    sudo chown -R $USER:$USER "$BACKUP_DIR"

    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Full Backup Completed Successfully" | tee -a "$LOG_FILE"
    echo "Location: $BACKUP_DIR" | tee -a "$LOG_FILE"
    echo "Size: $(du -sh "$BACKUP_DIR" | cut -f1)" | tee -a "$LOG_FILE"
    echo "Completed: $(date)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"

    # Create a marker file indicating this is the base for incremental backups
    echo "$TIMESTAMP" > "$FULL_BACKUP_DIR/latest_full_backup.txt"
    echo "$BACKUP_DIR" > "$BACKUP_BASE_DIR/base_dir.txt"

    # Clean up old full backups (keep last 4)
    cd "$FULL_BACKUP_DIR"
    ls -t | grep "^full_" | tail -n +5 | xargs -r rm -rf
    echo "Cleaned up old backups (keeping last 4)" | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Full Backup Failed" | tee -a "$LOG_FILE"
    echo "Check log file: $LOG_FILE" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    exit 1
fi
