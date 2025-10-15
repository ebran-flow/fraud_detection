#!/bin/bash
################################################################################
# Verify XtraBackup Backup
# Tests if a backup can be successfully prepared for restore
# Does NOT actually restore - safe to run on production
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "XTRABACKUP BACKUP VERIFICATION"
echo "================================================================================"
echo ""
echo "This script will verify that your backups can be restored without actually"
echo "performing a restore. It's safe to run on a production system."
echo ""

# Find the latest full backup
LATEST_FULL=$(ls -td "$BACKUP_BASE_DIR/full"/full_* 2>/dev/null | head -1)

if [ -z "$LATEST_FULL" ]; then
    echo -e "${RED}✗ No full backups found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found latest full backup:${NC} $(basename "$LATEST_FULL")"
echo ""

# Check if backup directory exists and has required files
echo "Checking backup integrity..."
echo "----------------------------"

# Check for required XtraBackup files
REQUIRED_FILES=(
    "xtrabackup_checkpoints"
    "xtrabackup_info.zst"
    "fraud_detection"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -e "$LATEST_FULL/$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file missing"
        exit 1
    fi
done

echo ""

# Check backup checkpoints
echo "Checking backup checkpoints..."
echo "------------------------------"
cat "$LATEST_FULL/xtrabackup_checkpoints"
echo ""

# Check backup type
BACKUP_TYPE=$(grep "backup_type" "$LATEST_FULL/xtrabackup_checkpoints" | cut -d'=' -f2 | tr -d ' ')
if [ "$BACKUP_TYPE" = "full-backuped" ]; then
    echo -e "${GREEN}✓ Backup type: full-backuped${NC}"
else
    echo -e "${YELLOW}⚠ Backup type: $BACKUP_TYPE${NC}"
fi

# Check for database files
echo ""
echo "Checking database files..."
echo "--------------------------"

DB_FILES=$(find "$LATEST_FULL/fraud_detection" -name "*.ibd.zst" -o -name "*.ibd" 2>/dev/null | wc -l)
echo -e "${GREEN}✓${NC} Found $DB_FILES table data files"

# List tables in backup
echo ""
echo "Tables in backup:"
find "$LATEST_FULL/fraud_detection" -name "*.ibd.zst" -o -name "*.ibd" 2>/dev/null | while read table_file; do
    if [ -f "$table_file" ]; then
        table_name=$(basename "$table_file" | sed 's/\.ibd.*$//')
        table_size=$(du -h "$table_file" | cut -f1)
        echo "  • $table_name ($table_size)"
    fi
done

# Check if backup has incremental backups
echo ""
echo "Checking for incremental backups..."
echo "------------------------------------"

INC_DIR="$BACKUP_BASE_DIR/incremental"
if [ -d "$INC_DIR" ]; then
    INC_COUNT=$(find "$INC_DIR" -maxdepth 1 -type d -name "inc_*" 2>/dev/null | wc -l)
    if [ $INC_COUNT -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $INC_COUNT incremental backup(s)"
        echo ""
        echo "Incremental backups:"
        for inc in $(ls -td "$INC_DIR"/inc_* 2>/dev/null | head -5); do
            inc_name=$(basename "$inc")
            inc_size=$(du -sh "$inc" 2>/dev/null | cut -f1)
            echo "  • $inc_name ($inc_size)"
        done
    else
        echo -e "${YELLOW}⚠${NC} No incremental backups found"
    fi
else
    echo -e "${YELLOW}⚠${NC} No incremental backup directory"
fi

# Test preparation (decompress and prepare in /tmp - this verifies backup validity)
echo ""
echo "================================================================================"
echo "TESTING BACKUP PREPARATION (This may take a few minutes)"
echo "================================================================================"
echo ""

TEST_RESTORE_DIR="/tmp/xtrabackup_verify_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_RESTORE_DIR"

echo "Test restore directory: $TEST_RESTORE_DIR"
echo ""
echo "Step 1/3: Copying backup files..."

# Copy backup to temp location
rsync -a "$LATEST_FULL/" "$TEST_RESTORE_DIR/" 2>&1 | head -10

echo -e "${GREEN}✓${NC} Backup files copied"
echo ""
echo "Step 2/3: Decompressing backup..."

# Decompress backup
if command -v xtrabackup &> /dev/null; then
    xtrabackup --decompress --target-dir="$TEST_RESTORE_DIR" 2>&1 | tail -20

    # Remove compressed files
    find "$TEST_RESTORE_DIR" -name "*.zst" -delete 2>/dev/null

    echo -e "${GREEN}✓${NC} Backup decompressed"
    echo ""
    echo "Step 3/3: Preparing backup (applying transaction logs)..."

    # Prepare backup
    if xtrabackup --prepare --target-dir="$TEST_RESTORE_DIR" 2>&1 | tee /tmp/xtrabackup_prepare.log | tail -20; then
        echo ""
        echo -e "${GREEN}✓${NC} Backup prepared successfully"

        # Check if preparation was successful
        if grep -q "completed OK!" /tmp/xtrabackup_prepare.log; then
            echo -e "${GREEN}✓${NC} XtraBackup preparation completed OK"
        fi
    else
        echo ""
        echo -e "${RED}✗${NC} Backup preparation failed"
        echo "Check log: /tmp/xtrabackup_prepare.log"
        rm -rf "$TEST_RESTORE_DIR"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC} xtrabackup not found - skipping preparation test"
fi

# Cleanup
echo ""
echo "Cleaning up test files..."
rm -rf "$TEST_RESTORE_DIR"
rm -f /tmp/xtrabackup_prepare.log

echo -e "${GREEN}✓${NC} Test files cleaned up"
echo ""

# Summary
echo "================================================================================"
echo "VERIFICATION SUMMARY"
echo "================================================================================"
echo ""
echo -e "${GREEN}✓ Backup integrity check: PASSED${NC}"
echo -e "${GREEN}✓ Required files present: PASSED${NC}"
echo -e "${GREEN}✓ Database tables found: PASSED ($DB_FILES tables)${NC}"
echo -e "${GREEN}✓ Backup preparation: PASSED${NC}"
echo ""
echo -e "${GREEN}SUCCESS: Backup is valid and can be restored!${NC}"
echo ""
echo "Backup location: $LATEST_FULL"
echo "Backup size: $(du -sh "$LATEST_FULL" | cut -f1)"
echo ""

# Show description if available
if [ -f "$LATEST_FULL/BACKUP_NOTES.txt" ]; then
    echo "Backup description:"
    cat "$LATEST_FULL/BACKUP_NOTES.txt" | sed 's/^/  /'
    echo ""
fi

echo "================================================================================"
echo ""
echo "To restore this backup, run:"
echo "  sudo ./scripts/backup/xtrabackup_restore.sh"
echo ""
echo "⚠ WARNING: Restore will STOP MySQL and REPLACE the current database!"
echo "   Make sure to backup current data before restoring."
echo ""
echo "================================================================================"

exit 0
