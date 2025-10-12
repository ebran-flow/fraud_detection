#!/bin/bash
# Migration Script: Laptop to PC
# Step-by-step guide with commands to migrate fraud detection database

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "Fraud Detection Database Migration"
echo "From: Laptop → To: PC"
echo "==========================================${NC}"
echo ""

# Configuration
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="fraud_detection_backup_${BACKUP_DATE}.sql"
BACKUP_COMPRESSED="fraud_detection_backup_${BACKUP_DATE}.sql.gz"

echo -e "${YELLOW}Step 1: Export Database from Laptop${NC}"
echo "======================================"
echo ""
echo "Run these commands ON YOUR LAPTOP:"
echo ""
echo -e "${GREEN}# Option 1: Regular dump (smaller databases < 1GB)${NC}"
echo "mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \\"
echo "  --single-transaction \\"
echo "  --routines \\"
echo "  --triggers \\"
echo "  --events \\"
echo "  fraud_detection > ${BACKUP_FILE}"
echo ""
echo -e "${GREEN}# Option 2: Compressed dump (recommended for large databases)${NC}"
echo "mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \\"
echo "  --single-transaction \\"
echo "  --routines \\"
echo "  --triggers \\"
echo "  --events \\"
echo "  fraud_detection | gzip > ${BACKUP_COMPRESSED}"
echo ""
echo -e "${YELLOW}Press Enter when dump is complete on laptop...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 2: Get Database Statistics${NC}"
echo "======================================"
echo ""
echo "Run this ON YOUR LAPTOP to see what you're migrating:"
echo ""
echo -e "${GREEN}mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection << 'EOF'
SELECT
  TABLE_NAME,
  TABLE_ROWS as 'Rows',
  ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as 'Size_MB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'fraud_detection'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
EOF${NC}"
echo ""
echo -e "${YELLOW}Press Enter to continue...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 3: Transfer Backup File to PC${NC}"
echo "======================================"
echo ""
echo "Choose your transfer method:"
echo ""
echo "Option A: USB Drive"
echo "-----------------"
echo "1. Insert USB drive"
echo "2. Copy file to USB:"
echo "   cp ${BACKUP_FILE} /media/usb/"
echo "3. Eject USB, plug into PC"
echo "4. Copy from USB to PC:"
echo "   cp /media/usb/${BACKUP_FILE} ~/Developer/projects/airtel_fraud_detection/"
echo ""
echo "Option B: Network Transfer (if both on same network)"
echo "---------------------------------------------------"
echo "ON PC - Start SSH server:"
echo "   sudo systemctl start sshd"
echo ""
echo "ON LAPTOP - Transfer file:"
echo "   scp ${BACKUP_FILE} ebran@PC_IP_ADDRESS:~/Developer/projects/airtel_fraud_detection/"
echo ""
echo "Option C: Cloud Storage (Dropbox/Google Drive)"
echo "---------------------------------------------"
echo "1. Upload from laptop to cloud"
echo "2. Download on PC to ~/Developer/projects/airtel_fraud_detection/"
echo ""
echo -e "${YELLOW}Press Enter when file is on PC...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 4: Setup Docker on PC${NC}"
echo "======================================"
echo ""
echo "Run these commands ON PC:"
echo ""
echo -e "${GREEN}cd ~/Developer/projects/airtel_fraud_detection
./setup-docker.sh${NC}"
echo ""
echo -e "${YELLOW}This will:${NC}"
echo "  ✓ Start MySQL container"
echo "  ✓ Start Backend container"
echo "  ✓ Create empty fraud_detection database"
echo ""
echo -e "${YELLOW}Press Enter when Docker setup is complete...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 5: Import Database to PC${NC}"
echo "======================================"
echo ""
echo "Choose based on your backup format:"
echo ""
echo -e "${GREEN}# Option 1: Regular .sql file${NC}"
echo "docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < ${BACKUP_FILE}"
echo ""
echo -e "${GREEN}# Option 2: Compressed .sql.gz file${NC}"
echo "gunzip < ${BACKUP_COMPRESSED} | docker-compose exec -T mysql mysql -u root -ppassword fraud_detection"
echo ""
echo -e "${YELLOW}This may take several minutes for large databases...${NC}"
echo ""
echo -e "${YELLOW}Press Enter when import is complete...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 6: Apply Collation Fix${NC}"
echo "======================================"
echo ""
echo "Apply the collation fix to avoid errors:"
echo ""
echo -e "${GREEN}docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < backend/migrations/fix_collation.sql${NC}"
echo ""
echo -e "${YELLOW}Press Enter when fix is applied...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 7: Verify Migration${NC}"
echo "======================================"
echo ""
echo "Run verification checks:"
echo ""
echo -e "${GREEN}docker-compose exec mysql mysql -u root -ppassword fraud_detection << 'EOF'
-- Check table counts
SELECT
  'metadata' as table_name,
  COUNT(*) as row_count
FROM metadata
UNION ALL
SELECT 'uatl_raw_statements', COUNT(*) FROM uatl_raw_statements
UNION ALL
SELECT 'umtn_raw_statements', COUNT(*) FROM umtn_raw_statements
UNION ALL
SELECT 'uatl_processed_statements', COUNT(*) FROM uatl_processed_statements
UNION ALL
SELECT 'umtn_processed_statements', COUNT(*) FROM umtn_processed_statements
UNION ALL
SELECT 'summary', COUNT(*) FROM summary;

-- Check database size
SELECT
  TABLE_NAME,
  TABLE_ROWS,
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as Size_MB
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'fraud_detection'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;

-- Test unified_statements view
SELECT status, COUNT(*) as count
FROM unified_statements
GROUP BY status;
EOF${NC}"
echo ""
echo -e "${YELLOW}Press Enter when verification is complete...${NC}"
read -p ""

echo ""
echo -e "${YELLOW}Step 8: Test Application${NC}"
echo "======================================"
echo ""
echo "Test the web interface:"
echo ""
echo "1. Open browser: http://localhost:8501"
echo "2. Check if statements are visible"
echo "3. Try filtering by status"
echo "4. Check a few statement details"
echo ""
echo -e "${YELLOW}Press Enter when testing is complete...${NC}"
read -p ""

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration Complete!"
echo "==========================================${NC}"
echo ""
echo "Summary:"
echo "--------"
echo "✓ Database exported from laptop"
echo "✓ File transferred to PC"
echo "✓ Docker setup completed"
echo "✓ Database imported to PC"
echo "✓ Collation fix applied"
echo "✓ Migration verified"
echo "✓ Application tested"
echo ""
echo "Next steps:"
echo "-----------"
echo "1. Keep laptop backup file safe (for rollback if needed)"
echo "2. Start using PC for imports:"
echo "   docker-compose exec backend python process_parallel.py --workers 8"
echo "3. Monitor performance:"
echo "   docker stats"
echo ""
echo "Useful commands:"
echo "----------------"
echo "# Start services"
echo "docker-compose up -d"
echo ""
echo "# Stop services"
echo "docker-compose down"
echo ""
echo "# View logs"
echo "docker-compose logs -f backend"
echo ""
echo "# Backup on PC (for future)"
echo "docker-compose exec mysql mysqldump -u root -ppassword fraud_detection | gzip > backup_pc_\$(date +%Y%m%d).sql.gz"
echo ""
