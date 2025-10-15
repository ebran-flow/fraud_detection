#!/bin/bash
################################################################################
# XtraBackup Restore Script
# Restores database from full backup + all incremental backups
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"
FULL_BACKUP_DIR="$BACKUP_BASE_DIR/full"
INCREMENTAL_BACKUP_DIR="$BACKUP_BASE_DIR/incremental"
RESTORE_DIR="/tmp/xtrabackup_restore_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_ROOT/logs"

# Load database credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "Error: .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/restore_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG_FILE"
echo "XtraBackup Database Restore" | tee -a "$LOG_FILE"
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

# Find the most recent full backup
FULL_BACKUP=$(ls -td "$FULL_BACKUP_DIR"/full_* 2>/dev/null | head -1)
if [ -z "$FULL_BACKUP" ] || [ ! -d "$FULL_BACKUP" ]; then
    echo "Error: No full backup found in $FULL_BACKUP_DIR" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Found full backup: $FULL_BACKUP" | tee -a "$LOG_FILE"

# Find all incremental backups newer than the full backup
FULL_BACKUP_TIME=$(stat -c %Y "$FULL_BACKUP")
INCREMENTAL_BACKUPS=()
if [ -d "$INCREMENTAL_BACKUP_DIR" ]; then
    while IFS= read -r inc_backup; do
        INC_TIME=$(stat -c %Y "$inc_backup")
        if [ "$INC_TIME" -gt "$FULL_BACKUP_TIME" ]; then
            INCREMENTAL_BACKUPS+=("$inc_backup")
        fi
    done < <(ls -td "$INCREMENTAL_BACKUP_DIR"/inc_* 2>/dev/null)
fi

if [ ${#INCREMENTAL_BACKUPS[@]} -gt 0 ]; then
    echo "Found ${#INCREMENTAL_BACKUPS[@]} incremental backup(s):" | tee -a "$LOG_FILE"
    for inc in "${INCREMENTAL_BACKUPS[@]}"; do
        echo "  - $inc" | tee -a "$LOG_FILE"
    done
else
    echo "No incremental backups found (will restore from full backup only)" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# WARNING
echo "========================================" | tee -a "$LOG_FILE"
echo "WARNING: This will STOP MySQL and REPLACE the current database!" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled" | tee -a "$LOG_FILE"
    exit 0
fi
echo "" | tee -a "$LOG_FILE"

# Create restore directory
mkdir -p "$RESTORE_DIR"
echo "Restore directory: $RESTORE_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 1: Decompress and prepare full backup
echo "Step 1: Decompressing full backup..." | tee -a "$LOG_FILE"
rsync -a "$FULL_BACKUP/" "$RESTORE_DIR/"
xtrabackup --decompress --target-dir="$RESTORE_DIR" 2>&1 | tee -a "$LOG_FILE"

# Remove compressed files
find "$RESTORE_DIR" -name "*.qp" -delete

echo "Step 2: Preparing full backup..." | tee -a "$LOG_FILE"
xtrabackup --prepare --apply-log-only --target-dir="$RESTORE_DIR" 2>&1 | tee -a "$LOG_FILE"

# Step 3: Apply incremental backups
if [ ${#INCREMENTAL_BACKUPS[@]} -gt 0 ]; then
    for i in "${!INCREMENTAL_BACKUPS[@]}"; do
        inc="${INCREMENTAL_BACKUPS[$i]}"
        inc_num=$((i + 1))

        echo "" | tee -a "$LOG_FILE"
        echo "Step 3.$inc_num: Applying incremental backup $inc_num of ${#INCREMENTAL_BACKUPS[@]}..." | tee -a "$LOG_FILE"

        # Decompress incremental
        INC_RESTORE_DIR="/tmp/inc_restore_$inc_num"
        mkdir -p "$INC_RESTORE_DIR"
        rsync -a "$inc/" "$INC_RESTORE_DIR/"
        xtrabackup --decompress --target-dir="$INC_RESTORE_DIR" 2>&1 | tee -a "$LOG_FILE"
        find "$INC_RESTORE_DIR" -name "*.qp" -delete

        # Apply incremental
        if [ $inc_num -eq ${#INCREMENTAL_BACKUPS[@]} ]; then
            # Last incremental - don't use --apply-log-only
            xtrabackup --prepare --target-dir="$RESTORE_DIR" --incremental-dir="$INC_RESTORE_DIR" 2>&1 | tee -a "$LOG_FILE"
        else
            # Not last - use --apply-log-only
            xtrabackup --prepare --apply-log-only --target-dir="$RESTORE_DIR" --incremental-dir="$INC_RESTORE_DIR" 2>&1 | tee -a "$LOG_FILE"
        fi

        rm -rf "$INC_RESTORE_DIR"
    done
else
    # No incrementals - final prepare
    echo "" | tee -a "$LOG_FILE"
    echo "Step 3: Final prepare (no incrementals)..." | tee -a "$LOG_FILE"
    xtrabackup --prepare --target-dir="$RESTORE_DIR" 2>&1 | tee -a "$LOG_FILE"
fi

# Step 4: Stop MySQL
echo "" | tee -a "$LOG_FILE"
echo "Step 4: Stopping MySQL container..." | tee -a "$LOG_FILE"
docker stop mysql 2>&1 | tee -a "$LOG_FILE"
sleep 5

# Step 5: Backup current data directory
echo "" | tee -a "$LOG_FILE"
echo "Step 5: Backing up current data directory..." | tee -a "$LOG_FILE"
MYSQL_DATA_DIR="/var/lib/docker/volumes/docker_config_dbdata/_data"
BACKUP_DATA_DIR="${MYSQL_DATA_DIR}_backup_$(date +%Y%m%d_%H%M%S)"

if [ -d "$MYSQL_DATA_DIR" ]; then
    sudo mv "$MYSQL_DATA_DIR" "$BACKUP_DATA_DIR" | tee -a "$LOG_FILE"
    echo "Current data backed up to: $BACKUP_DATA_DIR" | tee -a "$LOG_FILE"
else
    echo "Data directory not found, creating new one" | tee -a "$LOG_FILE"
fi

sudo mkdir -p "$MYSQL_DATA_DIR"

# Step 6: Copy restored files to MySQL data directory
echo "" | tee -a "$LOG_FILE"
echo "Step 6: Copying restored files to MySQL data directory..." | tee -a "$LOG_FILE"
sudo xtrabackup --copy-back --target-dir="$RESTORE_DIR" --datadir="$MYSQL_DATA_DIR" 2>&1 | tee -a "$LOG_FILE"

# Step 7: Fix permissions
echo "" | tee -a "$LOG_FILE"
echo "Step 7: Fixing permissions..." | tee -a "$LOG_FILE"
sudo chown -R 999:999 "$MYSQL_DATA_DIR"

# MySQL connection settings for LOCAL MySQL 8.0
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="password"

# Step 8: Start MySQL
echo "" | tee -a "$LOG_FILE"
echo "Step 8: Starting MySQL container..." | tee -a "$LOG_FILE"
docker start mysql 2>&1 | tee -a "$LOG_FILE"

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..." | tee -a "$LOG_FILE"
for i in {1..30}; do
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &> /dev/null; then
        echo "MySQL is ready!" | tee -a "$LOG_FILE"
        break
    fi
    echo "Waiting... ($i/30)" | tee -a "$LOG_FILE"
    sleep 2
done

# Step 9: Verify database
echo "" | tee -a "$LOG_FILE"
echo "Step 9: Verifying database..." | tee -a "$LOG_FILE"
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" fraud_detection -e "
    SELECT 'metadata' as table_name, COUNT(*) as rows FROM metadata
    UNION ALL
    SELECT 'summary', COUNT(*) FROM summary
    UNION ALL
    SELECT 'uatl_raw_statements', COUNT(*) FROM uatl_raw_statements
    UNION ALL
    SELECT 'umtn_raw_statements', COUNT(*) FROM umtn_raw_statements;
" 2>&1 | tee -a "$LOG_FILE"

# Cleanup
echo "" | tee -a "$LOG_FILE"
echo "Step 10: Cleaning up temporary files..." | tee -a "$LOG_FILE"
rm -rf "$RESTORE_DIR"

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Database Restore Completed Successfully!" | tee -a "$LOG_FILE"
echo "Completed: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "IMPORTANT: Run post-restore steps from POST_RESTORE_CHECKLIST.md" | tee -a "$LOG_FILE"
echo "1. Apply schema updates: mysql < scripts/migration/post_restore_updates.sql" | tee -a "$LOG_FILE"
echo "2. Verify data integrity" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

exit 0
