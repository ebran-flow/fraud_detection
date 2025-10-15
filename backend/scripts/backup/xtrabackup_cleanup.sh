#!/bin/bash
################################################################################
# XtraBackup Cleanup Script
# Removes old backups according to retention policy
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"
FULL_BACKUP_DIR="$BACKUP_BASE_DIR/full"
INCREMENTAL_BACKUP_DIR="$BACKUP_BASE_DIR/incremental"
LOG_DIR="$PROJECT_ROOT/logs"

# Retention policy
KEEP_FULL_BACKUPS=4      # Keep last 4 full backups (monthly rotation)
KEEP_INCREMENTAL_DAYS=7  # Keep incremental backups for 7 days

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup_cleanup_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG_FILE"
echo "XtraBackup Cleanup" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Cleanup old full backups
if [ -d "$FULL_BACKUP_DIR" ]; then
    echo "Cleaning up old full backups..." | tee -a "$LOG_FILE"
    echo "Retention policy: Keep last $KEEP_FULL_BACKUPS full backups" | tee -a "$LOG_FILE"

    FULL_COUNT=$(ls -1d "$FULL_BACKUP_DIR"/full_* 2>/dev/null | wc -l)
    echo "Current full backups: $FULL_COUNT" | tee -a "$LOG_FILE"

    if [ "$FULL_COUNT" -gt "$KEEP_FULL_BACKUPS" ]; then
        TO_DELETE=$((FULL_COUNT - KEEP_FULL_BACKUPS))
        echo "Deleting $TO_DELETE old full backup(s)..." | tee -a "$LOG_FILE"

        cd "$FULL_BACKUP_DIR"
        ls -td full_* | tail -n "+$((KEEP_FULL_BACKUPS + 1))" | while read -r backup; do
            SIZE=$(du -sh "$backup" | cut -f1)
            echo "  Removing: $backup (Size: $SIZE)" | tee -a "$LOG_FILE"
            rm -rf "$backup"
        done

        NEW_COUNT=$(ls -1d "$FULL_BACKUP_DIR"/full_* 2>/dev/null | wc -l)
        echo "Remaining full backups: $NEW_COUNT" | tee -a "$LOG_FILE"
    else
        echo "No full backups to delete" | tee -a "$LOG_FILE"
    fi
else
    echo "Full backup directory not found: $FULL_BACKUP_DIR" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

# Cleanup old incremental backups
if [ -d "$INCREMENTAL_BACKUP_DIR" ]; then
    echo "Cleaning up old incremental backups..." | tee -a "$LOG_FILE"
    echo "Retention policy: Keep incremental backups for $KEEP_INCREMENTAL_DAYS days" | tee -a "$LOG_FILE"

    INC_COUNT=$(ls -1d "$INCREMENTAL_BACKUP_DIR"/inc_* 2>/dev/null | wc -l)
    echo "Current incremental backups: $INC_COUNT" | tee -a "$LOG_FILE"

    if [ "$INC_COUNT" -gt 0 ]; then
        cd "$INCREMENTAL_BACKUP_DIR"
        DELETED=0
        find . -maxdepth 1 -type d -name "inc_*" -mtime +$KEEP_INCREMENTAL_DAYS | while read -r backup; do
            SIZE=$(du -sh "$backup" | cut -f1)
            echo "  Removing: $backup (Size: $SIZE)" | tee -a "$LOG_FILE"
            rm -rf "$backup"
            DELETED=$((DELETED + 1))
        done

        NEW_INC_COUNT=$(ls -1d "$INCREMENTAL_BACKUP_DIR"/inc_* 2>/dev/null | wc -l)
        echo "Remaining incremental backups: $NEW_INC_COUNT" | tee -a "$LOG_FILE"
    else
        echo "No incremental backups to delete" | tee -a "$LOG_FILE"
    fi
else
    echo "Incremental backup directory not found: $INCREMENTAL_BACKUP_DIR" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"

# Calculate total backup size
if [ -d "$BACKUP_BASE_DIR" ]; then
    TOTAL_SIZE=$(du -sh "$BACKUP_BASE_DIR" | cut -f1)
    echo "Total backup size: $TOTAL_SIZE" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Cleanup Completed" | tee -a "$LOG_FILE"
echo "Completed: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

exit 0
