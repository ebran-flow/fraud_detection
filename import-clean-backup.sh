#!/bin/bash
# Import Clean Backup to Docker MySQL
# Usage: ./import-clean-backup.sh

set -e

echo "=========================================="
echo "Import Clean Backup to Docker MySQL"
echo "=========================================="
echo ""

BACKUP_FILE="backend/backup_clean.sql"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Backup file not found: $BACKUP_FILE"
    exit 1
fi

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup file: $BACKUP_FILE"
echo "File size: $FILE_SIZE"
echo ""

# Check if MySQL container is running
if ! docker compose ps mysql | grep -q "Up"; then
    echo "[ERROR] MySQL container is not running"
    echo "Please run: docker compose up -d"
    exit 1
fi

echo "[OK] MySQL container is running"
echo ""

# Configure MySQL for large import
echo "Configuring MySQL..."
docker compose exec -T mysql mysql -u root -ppassword -e "
SET GLOBAL max_allowed_packet=1073741824;
SET GLOBAL net_read_timeout=3600;
SET GLOBAL net_write_timeout=3600;
SET GLOBAL wait_timeout=3600;
" 2>&1 | grep -v "password"

echo "[OK] MySQL configured"
echo ""

# Copy file into container
echo "Step 1/3: Copying file to container..."
docker cp "$BACKUP_FILE" fraud_detection_mysql:/tmp/backup.sql
echo "[OK] File copied"
echo ""

# Import
echo "Step 2/3: Importing to database..."
echo "This may take several minutes..."
echo ""

START_TIME=$(date +%s)

docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/backup.sql" 2>&1 | grep -v "password"

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Import failed"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "[OK] Import completed in ${DURATION}s"
echo ""

# Cleanup
echo "Cleaning up..."
docker compose exec mysql rm /tmp/backup.sql 2>&1 > /dev/null
echo ""

# Verify import
echo "Step 3/3: Verifying import..."
echo ""

docker compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA='fraud_detection' AND TABLE_TYPE='BASE TABLE'
ORDER BY TABLE_ROWS DESC;
" 2>&1 | grep -v "password"

echo ""
echo "=========================================="
echo "Import Complete!"
echo "=========================================="
echo ""
echo "Next step: Apply collation fix"
echo "  docker compose exec -T mysql mysql -u root -ppassword fraud_detection < backend/migrations/fix_collation.sql"
echo ""
