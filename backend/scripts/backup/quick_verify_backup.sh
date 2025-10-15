#!/bin/bash
################################################################################
# Quick Backup Verification
# Quickly checks if backup structure is valid (doesn't decompress/prepare)
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"

echo "================================================================================"
echo "XTRABACKUP QUICK VERIFICATION"
echo "================================================================================"
echo ""

# Find the latest full backup
LATEST_FULL=$(ls -td "$BACKUP_BASE_DIR/full"/full_* 2>/dev/null | head -1)

if [ -z "$LATEST_FULL" ]; then
    echo "✗ No full backups found"
    exit 1
fi

echo "✓ Latest full backup: $(basename "$LATEST_FULL")"
echo "  Location: $LATEST_FULL"
echo "  Size: $(du -sh "$LATEST_FULL" | cut -f1)"
echo ""

# Check backup checkpoints
echo "Backup Checkpoints:"
echo "-------------------"
if [ -f "$LATEST_FULL/xtrabackup_checkpoints" ]; then
    cat "$LATEST_FULL/xtrabackup_checkpoints"
    echo ""

    BACKUP_TYPE=$(grep "backup_type" "$LATEST_FULL/xtrabackup_checkpoints" | cut -d'=' -f2 | tr -d ' ')
    if [ "$BACKUP_TYPE" = "full-backuped" ]; then
        echo "✓ Backup type: FULL"
    else
        echo "⚠ Backup type: $BACKUP_TYPE"
    fi
else
    echo "✗ Missing xtrabackup_checkpoints"
    exit 1
fi

echo ""

# Check required files
echo "Required Files:"
echo "---------------"
FILES_OK=true

for file in "xtrabackup_checkpoints" "xtrabackup_info.zst" "fraud_detection"; do
    if [ -e "$LATEST_FULL/$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file MISSING"
        FILES_OK=false
    fi
done

if [ "$FILES_OK" = false ]; then
    echo ""
    echo "✗ Backup is incomplete"
    exit 1
fi

echo ""

# Check tables
echo "Database Tables:"
echo "----------------"
TABLE_COUNT=0
EXPECTED_TABLES=("metadata" "summary" "uatl_raw_statements" "uatl_processed_statements" "umtn_raw_statements" "umtn_processed_statements")

for table in "${EXPECTED_TABLES[@]}"; do
    if ls "$LATEST_FULL/fraud_detection/${table}.ibd"* 1> /dev/null 2>&1; then
        size=$(du -h "$LATEST_FULL/fraud_detection/${table}.ibd"* 2>/dev/null | head -1 | cut -f1)
        echo "✓ $table ($size)"
        TABLE_COUNT=$((TABLE_COUNT + 1))
    else
        echo "✗ $table MISSING"
    fi
done

echo ""
echo "Found $TABLE_COUNT / ${#EXPECTED_TABLES[@]} expected tables"

if [ $TABLE_COUNT -lt ${#EXPECTED_TABLES[@]} ]; then
    echo "⚠ Some tables are missing!"
fi

echo ""

# Check if backup has description
echo "Backup Description:"
echo "-------------------"
if [ -f "$LATEST_FULL/BACKUP_NOTES.txt" ]; then
    cat "$LATEST_FULL/BACKUP_NOTES.txt"
else
    echo "(No description)"
fi

echo ""
echo "================================================================================"
echo "SUMMARY"
echo "================================================================================"
echo ""

if [ "$FILES_OK" = true ] && [ $TABLE_COUNT -eq ${#EXPECTED_TABLES[@]} ]; then
    echo "✓ Backup structure: VALID"
    echo "✓ All required files: PRESENT"
    echo "✓ All expected tables: FOUND"
    echo ""
    echo "SUCCESS: Backup appears valid and restorable!"
    echo ""
    echo "To perform full verification (decompress + prepare), run:"
    echo "  ./scripts/backup/verify_backup.sh"
    echo ""
    echo "To restore this backup, run:"
    echo "  sudo ./scripts/backup/xtrabackup_restore.sh"
    echo ""
    echo "⚠ WARNING: Restore will STOP MySQL and REPLACE the current database!"
else
    echo "✗ Backup verification FAILED"
    echo ""
    echo "Issues found:"
    if [ "$FILES_OK" != true ]; then
        echo "  - Missing required files"
    fi
    if [ $TABLE_COUNT -lt ${#EXPECTED_TABLES[@]} ]; then
        echo "  - Missing tables"
    fi
    exit 1
fi

echo "================================================================================"

exit 0
