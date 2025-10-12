#!/bin/bash
# Import only uatl_raw_statements table
# Much faster than full import

set -e

echo "=========================================="
echo "Import UATL Raw Statements Only"
echo "=========================================="
echo ""

BACKUP_FILE="backend/backup_clean.sql"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Extracting uatl_raw_statements from backup..."
echo ""

# Extract just the uatl_raw_statements table
grep -A 50 "CREATE TABLE \`uatl_raw_statements\`" "$BACKUP_FILE" > /tmp/uatl_only.sql
grep "INSERT INTO \`uatl_raw_statements\`" "$BACKUP_FILE" >> /tmp/uatl_only.sql

EXTRACTED_SIZE=$(du -h /tmp/uatl_only.sql | cut -f1)
echo "[OK] Extracted table definition and data: $EXTRACTED_SIZE"
echo ""

# Copy to container
echo "Copying to container..."
docker cp /tmp/uatl_only.sql fraud_detection_mysql:/tmp/uatl_only.sql
echo "[OK] File copied"
echo ""

# Import
echo "Importing uatl_raw_statements..."
START_TIME=$(date +%s)

docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/uatl_only.sql"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "[OK] Import completed in ${DURATION}s"
echo ""

# Cleanup
docker compose exec mysql rm /tmp/uatl_only.sql 2>&1 > /dev/null
rm /tmp/uatl_only.sql

# Verify
echo "Verifying import..."
ROW_COUNT=$(docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) FROM uatl_raw_statements" 2>&1 | tail -n 1)

echo "[OK] Imported $ROW_COUNT rows"
echo ""
echo "=========================================="
echo "Ready to process statements!"
echo "=========================================="
echo ""
