#!/bin/bash
################################################################################
# Restore Database to Local MySQL 8.0
# Restores fraud_detection database from Docker MySQL backups
################################################################################

set -euo pipefail

BACKUP_DIR="/home/ebran/Developer/projects/airtel_fraud_detection/backups/tables"

echo "========================================================================"
echo "Restore fraud_detection Database to Local MySQL 8.0"
echo "========================================================================"
echo ""

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Check if MySQL is running
if ! systemctl is-active --quiet mysql; then
    echo "Error: MySQL service is not running"
    echo "Start it with: sudo systemctl start mysql"
    exit 1
fi

# Get MySQL credentials
echo "Please enter MySQL root password:"
read -sp "Password: " MYSQL_PASSWORD
echo ""

# Test MySQL connection
if ! mysql -u root -p"$MYSQL_PASSWORD" -e "SELECT 1" &> /dev/null; then
    echo "Error: Cannot connect to MySQL. Please check your password."
    exit 1
fi

echo "✅ MySQL connection successful"
echo ""

# Check if database exists
DB_EXISTS=$(mysql -u root -p"$MYSQL_PASSWORD" -e "SHOW DATABASES LIKE 'fraud_detection'" -sN)
if [ -z "$DB_EXISTS" ]; then
    echo "Creating fraud_detection database..."
    mysql -u root -p"$MYSQL_PASSWORD" -e "CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    echo "✅ Database created"
else
    echo "✅ fraud_detection database exists"
fi

echo ""
echo "========================================================================"
echo "Starting Table Imports"
echo "========================================================================"
echo ""

# Count total files
TOTAL_FILES=8
CURRENT=0

# Import function
import_table() {
    local file=$1
    local table_name=$2
    local size=$3

    CURRENT=$((CURRENT + 1))

    if [ ! -f "$BACKUP_DIR/$file" ]; then
        echo "⚠️  [$CURRENT/$TOTAL_FILES] Skipping $table_name - file not found"
        return
    fi

    echo "[$CURRENT/$TOTAL_FILES] Importing $table_name ($size)..."
    echo "  File: $file"
    echo "  Started: $(date)"

    START_TIME=$(date +%s)
    mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < "$BACKUP_DIR/$file" 2>&1 | grep -v "Warning: Using a password" || true
    END_TIME=$(date +%s)

    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    echo "  ✅ Completed in ${MINUTES}m ${SECONDS}s"
    echo ""
}

# Import tables in order
import_table "fraud_detection_metadata.sql" "metadata" "small"
import_table "fraud_detection_summary.sql" "summary" "small"
import_table "fraud_detection_uatl_raw_statements.sql" "uatl_raw_statements" "6.9GB"
import_table "fraud_detection_uatl_processed_statements.sql" "uatl_processed_statements" "7.1GB"
import_table "fraud_detection_umtn_raw_statements.sql" "umtn_raw_statements" "7.3GB"
import_table "fraud_detection_umtn_processed_statements.sql" "umtn_processed_statements" "6.9GB"
import_table "fraud_detection_uatl_balance_issues.sql" "uatl_balance_issues" "small"
import_table "fraud_detection_umtn_balance_issues.sql" "umtn_balance_issues" "small"

echo "========================================================================"
echo "Verifying Database"
echo "========================================================================"
echo ""

# Get row counts
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection <<EOF
SELECT
    'metadata' as table_name,
    COUNT(*) as row_count
FROM metadata
UNION ALL
SELECT 'summary', COUNT(*) FROM summary
UNION ALL
SELECT 'uatl_raw_statements', COUNT(*) FROM uatl_raw_statements
UNION ALL
SELECT 'uatl_processed_statements', COUNT(*) FROM uatl_processed_statements
UNION ALL
SELECT 'umtn_raw_statements', COUNT(*) FROM umtn_raw_statements
UNION ALL
SELECT 'umtn_processed_statements', COUNT(*) FROM umtn_processed_statements;
EOF

echo ""
echo "========================================================================"
echo "✅ Database Restore Complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Apply schema updates:"
echo "   cd /home/ebran/Developer/projects/airtel_fraud_detection/backend"
echo "   mysql -u root -p fraud_detection < scripts/migration/post_restore_updates.sql"
echo ""
echo "2. Install XtraBackup:"
echo "   sudo bash install_xtrabackup.sh"
echo ""
echo "3. Take first backup:"
echo "   ./scripts/backup/xtrabackup_full.sh"
echo ""

exit 0
