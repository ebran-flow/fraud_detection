#!/bin/bash
################################################################################
# List All Backups with Descriptions
# Shows all full and incremental backups with their manifest info
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup"

echo "================================================================================"
echo "XTRABACKUP INVENTORY"
echo "================================================================================"
echo ""

# Function to extract key info from manifest
show_backup_info() {
    local backup_dir=$1
    local backup_type=$2
    local manifest="$backup_dir/BACKUP_MANIFEST.txt"

    if [ ! -f "$manifest" ]; then
        echo "  📝 No manifest found"
        return
    fi

    # Extract key information
    local backup_date=$(grep "Backup Date:" "$manifest" | cut -d':' -f2- | xargs)
    local backup_size=$(grep "Backup Size:" "$manifest" | cut -d':' -f2- | xargs)
    local git_commit=$(grep "Git Commit:" "$manifest" | cut -d':' -f2- | xargs | cut -c1-8)
    local total_statements=$(grep "Total Statements:" "$manifest" | cut -d':' -f2- | xargs)

    echo "  📅 Date: $backup_date"
    echo "  💾 Size: $backup_size"
    echo "  📊 Statements: $total_statements"
    echo "  🔗 Git: $git_commit"

    # Extract description
    local description=$(awk '/BACKUP DESCRIPTION:/,/End of Manifest/' "$manifest" | \
        grep -v "BACKUP DESCRIPTION:" | \
        grep -v "End of Manifest" | \
        grep -v "^===" | \
        grep -v "^$" | \
        head -5)

    if [ -n "$description" ] && [ "$description" != "(No description provided)" ]; then
        echo "  📝 Description:"
        echo "$description" | sed 's/^/     /'
    fi
}

# List full backups
echo "FULL BACKUPS:"
echo "-------------"
if [ -d "$BACKUP_BASE_DIR/full" ]; then
    full_count=0
    for backup in $(ls -td "$BACKUP_BASE_DIR/full"/full_* 2>/dev/null); do
        if [ -d "$backup" ]; then
            full_count=$((full_count + 1))
            backup_name=$(basename "$backup")
            echo ""
            echo "[$full_count] $backup_name"
            show_backup_info "$backup" "full"
        fi
    done

    if [ $full_count -eq 0 ]; then
        echo ""
        echo "  No full backups found"
    fi
else
    echo ""
    echo "  No full backup directory found"
fi

echo ""
echo "================================================================================"
echo ""

# List incremental backups
echo "INCREMENTAL BACKUPS:"
echo "--------------------"
if [ -d "$BACKUP_BASE_DIR/incremental" ]; then
    inc_count=0
    for backup in $(ls -td "$BACKUP_BASE_DIR/incremental"/inc_* 2>/dev/null); do
        if [ -d "$backup" ]; then
            inc_count=$((inc_count + 1))
            backup_name=$(basename "$backup")
            echo ""
            echo "[$inc_count] $backup_name"
            show_backup_info "$backup" "incremental"
        fi
    done

    if [ $inc_count -eq 0 ]; then
        echo ""
        echo "  No incremental backups found"
    fi
else
    echo ""
    echo "  No incremental backup directory found"
fi

echo ""
echo "================================================================================"
echo ""

# Show backup chain
echo "BACKUP CHAIN:"
echo "-------------"
if [ -f "$BACKUP_BASE_DIR/base_dir.txt" ]; then
    base_dir=$(cat "$BACKUP_BASE_DIR/base_dir.txt")
    echo "Current base for next incremental: $(basename "$base_dir")"
else
    echo "No backup chain established yet"
fi

echo ""

# Show summary statistics
echo "SUMMARY:"
echo "--------"
full_size=0
inc_size=0

if [ -d "$BACKUP_BASE_DIR/full" ]; then
    full_size=$(du -sh "$BACKUP_BASE_DIR/full" 2>/dev/null | cut -f1)
fi

if [ -d "$BACKUP_BASE_DIR/incremental" ]; then
    inc_size=$(du -sh "$BACKUP_BASE_DIR/incremental" 2>/dev/null | cut -f1)
fi

echo "Full backups total size:         $full_size"
echo "Incremental backups total size:  $inc_size"
echo ""
echo "================================================================================"

exit 0
