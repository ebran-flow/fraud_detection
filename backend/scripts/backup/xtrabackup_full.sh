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

# Load backup credentials from separate config file
if [ -f "$PROJECT_ROOT/.env.xtrabackup" ]; then
    source "$PROJECT_ROOT/.env.xtrabackup"
else
    echo "Error: .env.xtrabackup file not found at $PROJECT_ROOT/.env.xtrabackup"
    echo "Please create .env.xtrabackup with backup credentials"
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

# Prompt for backup description (optional)
echo "Please describe what's included in this backup (or press Enter to skip):"
echo "Examples:"
echo "  - After importing remaining Airtel/MTN statements"
echo "  - Added unified_statements view"
echo "  - Applied schema updates: header_rows_count, amount_raw, fee_raw"
echo "  - Post-restore baseline with all tables"
echo ""
read -p "Description: " BACKUP_DESCRIPTION

# Save description if provided
if [ -n "$BACKUP_DESCRIPTION" ]; then
    echo "📝 Backup description: $BACKUP_DESCRIPTION" | tee -a "$LOG_FILE"
    echo ""
fi

# Check if xtrabackup is installed
if ! command -v xtrabackup &> /dev/null; then
    echo "Error: xtrabackup is not installed" | tee -a "$LOG_FILE"
    echo "Please run: sudo apt-get install percona-xtrabackup-82" | tee -a "$LOG_FILE"
    exit 1
fi

# Verify XtraBackup version
XTRABACKUP_VERSION=$(xtrabackup --version 2>&1 | grep -oP 'xtrabackup version \K[0-9.]+')
echo "XtraBackup version: $XTRABACKUP_VERSION" | tee -a "$LOG_FILE"

# Check if MySQL is accessible (using credentials from .env.xtrabackup)
if ! mysql -h "${BACKUP_DB_HOST}" -P "${BACKUP_DB_PORT}" -u "${BACKUP_DB_USER}" -p"${BACKUP_DB_PASSWORD}" -e "SELECT 1" &> /dev/null; then
    echo "Error: Cannot connect to MySQL database" | tee -a "$LOG_FILE"
    echo "Host: ${BACKUP_DB_HOST}:${BACKUP_DB_PORT}, User: ${BACKUP_DB_USER}" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Connected to MySQL: ${BACKUP_DB_HOST}:${BACKUP_DB_PORT} as ${BACKUP_DB_USER}" | tee -a "$LOG_FILE"

# Perform full backup
echo "Creating full backup to: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# XtraBackup needs sudo to access MySQL data directory
sudo xtrabackup --backup \
    --host="${BACKUP_DB_HOST}" \
    --port="${BACKUP_DB_PORT}" \
    --user="${BACKUP_DB_USER}" \
    --password="${BACKUP_DB_PASSWORD}" \
    --databases="${BACKUP_DB_NAME}" \
    --target-dir="$BACKUP_DIR" \
    --parallel=${BACKUP_PARALLEL_THREADS:-4} \
    --compress \
    --compress-threads=${BACKUP_COMPRESS_THREADS:-4} 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    # Fix ownership of backup directory (created by sudo)
    sudo chown -R $USER:$USER "$BACKUP_DIR"

    # Save backup description to notes file
    if [ -n "$BACKUP_DESCRIPTION" ]; then
        echo "$BACKUP_DESCRIPTION" > "$BACKUP_DIR/BACKUP_NOTES.txt"
    fi

    # Generate backup manifest
    echo "" | tee -a "$LOG_FILE"
    echo "Generating backup manifest..." | tee -a "$LOG_FILE"
    "$SCRIPT_DIR/generate_backup_manifest.sh" "$BACKUP_DIR" "full" 2>&1 | tee -a "$LOG_FILE"

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

    # Clean up old full backups (use retention setting from config)
    cd "$FULL_BACKUP_DIR"
    RETENTION=$((${FULL_BACKUP_RETENTION:-4} + 1))
    ls -t | grep "^full_" | tail -n +$RETENTION | xargs -r rm -rf
    echo "Cleaned up old backups (keeping last ${FULL_BACKUP_RETENTION:-4})" | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Full Backup Failed" | tee -a "$LOG_FILE"
    echo "Check log file: $LOG_FILE" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    exit 1
fi
