# Database Migration Guide: Laptop → PC

Complete step-by-step guide to migrate your fraud detection database from laptop to PC with Docker.

## Overview

**Source**: Laptop (MySQL on port 3307)
**Target**: PC (Docker MySQL on port 3307)
**Estimated time**: 30-60 minutes (depending on database size)

## Prerequisites

### On Laptop
- [ ] MySQL running with fraud detection database
- [ ] mysqldump available
- [ ] SSH or USB drive for transfer

### On PC
- [ ] Docker and Docker Compose installed
- [ ] At least 20GB free disk space
- [ ] Project files at `/home/ebran/Developer/projects/airtel_fraud_detection`

## Quick Start

```bash
# On PC
cd /home/ebran/Developer/projects/airtel_fraud_detection
./migrate-laptop-to-pc.sh
```

The script will guide you through each step interactively.

## Manual Step-by-Step Guide

### Step 1: Check Database Size (On Laptop)

First, see what you're migrating:

```bash
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection -e "
SELECT
  TABLE_NAME,
  TABLE_ROWS as 'Rows',
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as 'Size_MB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'fraud_detection'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
"
```

**Expected output example:**
```
TABLE_NAME                      Rows    Size_MB
uatl_raw_statements            45000    125.50
uatl_processed_statements      45000    98.30
metadata                        850      12.40
summary                         350      8.20
umtn_raw_statements            5000     15.60
...
```

### Step 2: Export Database (On Laptop)

#### Option A: Regular Dump (For databases < 1GB)

```bash
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --set-gtid-purged=OFF \
  fraud_detection > fraud_detection_backup_$(date +%Y%m%d).sql
```

**Flags explained:**
- `--single-transaction`: Consistent backup without locking tables
- `--routines`: Include stored procedures and functions
- `--triggers`: Include triggers
- `--events`: Include scheduled events
- `--set-gtid-purged=OFF`: Avoid GTID issues on restore

#### Option B: Compressed Dump (Recommended for large databases)

```bash
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --set-gtid-purged=OFF \
  fraud_detection | gzip > fraud_detection_backup_$(date +%Y%m%d).sql.gz
```

**Compression saves ~70-80% space!**

#### Option C: Exclude Large Temporary Tables (If any)

If you have temporary or log tables you don't need:

```bash
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --set-gtid-purged=OFF \
  --ignore-table=fraud_detection.temp_table \
  fraud_detection | gzip > fraud_detection_backup_$(date +%Y%m%d).sql.gz
```

#### Verify Backup File

```bash
# Check file size
ls -lh fraud_detection_backup_*.sql*

# For .sql file, check first few lines
head -20 fraud_detection_backup_*.sql

# For .gz file, check first few lines
gunzip < fraud_detection_backup_*.sql.gz | head -20
```

**Expected output should include:**
```sql
-- MySQL dump 10.13  Distrib 8.0.x, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: fraud_detection
-- Server version       8.0.x
```

### Step 3: Transfer Backup to PC

#### Option A: USB Drive (Most Reliable)

**On Laptop:**
```bash
# Find USB mount point
lsblk

# Copy to USB (adjust path based on lsblk output)
cp fraud_detection_backup_*.sql* /media/$USER/USB_DRIVE_NAME/

# Verify copy
ls -lh /media/$USER/USB_DRIVE_NAME/fraud_detection_backup_*

# Safely eject
sync
udisksctl unmount -b /dev/sdX1  # Replace sdX1 with your USB device
udisksctl power-off -b /dev/sdX
```

**On PC:**
```bash
# Insert USB, find mount point
lsblk

# Copy from USB
cp /media/$USER/USB_DRIVE_NAME/fraud_detection_backup_* ~/Developer/projects/airtel_fraud_detection/

# Verify
cd ~/Developer/projects/airtel_fraud_detection
ls -lh fraud_detection_backup_*
```

#### Option B: Network Transfer via SCP

**On PC (prepare to receive):**
```bash
# Find PC IP address
ip addr show | grep "inet " | grep -v 127.0.0.1

# Note the IP, e.g., 192.168.1.100

# Ensure SSH server is running
sudo systemctl status sshd
# If not running:
sudo systemctl start sshd
```

**On Laptop (send file):**
```bash
# Transfer file (replace PC_IP with actual IP)
scp fraud_detection_backup_*.sql* ebran@PC_IP:~/Developer/projects/airtel_fraud_detection/

# Example:
# scp fraud_detection_backup_20251012.sql.gz ebran@192.168.1.100:~/Developer/projects/airtel_fraud_detection/
```

#### Option C: Cloud Storage

**On Laptop:**
```bash
# Upload to Dropbox/Google Drive using web interface or CLI
# rclone copy fraud_detection_backup_*.sql* dropbox:/backups/
```

**On PC:**
```bash
# Download from cloud
cd ~/Developer/projects/airtel_fraud_detection
# Use web interface or CLI to download
```

### Step 4: Setup Docker on PC

```bash
cd ~/Developer/projects/airtel_fraud_detection

# Run setup script
./setup-docker.sh
```

**This will:**
1. Check Docker installation
2. Create necessary directories
3. Copy environment files
4. Build Docker images (~5 minutes)
5. Start MySQL and Backend containers
6. Create empty `fraud_detection` database

**Wait for:** "✅ Setup Complete!" message

**Verify services are running:**
```bash
docker-compose ps

# Expected output:
# NAME                          STATUS
# fraud_detection_backend       Up
# fraud_detection_mysql         Up (healthy)
```

### Step 5: Import Database to PC

#### Option A: Import Regular .sql File

```bash
cd ~/Developer/projects/airtel_fraud_detection

# Import (this may take 5-30 minutes depending on size)
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < fraud_detection_backup_20251012.sql

# Watch progress (in another terminal)
docker-compose logs -f mysql
```

#### Option B: Import Compressed .sql.gz File

```bash
cd ~/Developer/projects/airtel_fraud_detection

# Import compressed file
gunzip < fraud_detection_backup_20251012.sql.gz | docker-compose exec -T mysql mysql -u root -ppassword fraud_detection

# Watch progress (in another terminal)
docker-compose logs -f mysql
```

#### Monitor Import Progress

Open another terminal and watch:

```bash
# Method 1: Watch table row counts
watch -n 5 'docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
  SELECT TABLE_NAME, TABLE_ROWS
  FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = '\''fraud_detection'\''
  ORDER BY TABLE_ROWS DESC
  LIMIT 10;
"'

# Method 2: Watch database size
watch -n 5 'docker-compose exec mysql mysql -u root -ppassword -e "
  SELECT
    table_schema AS DB,
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS Size_MB
  FROM information_schema.tables
  WHERE table_schema = '\''fraud_detection'\''
  GROUP BY table_schema;
"'
```

**Expected import time:**
- Small DB (< 500MB): 2-5 minutes
- Medium DB (500MB-2GB): 5-15 minutes
- Large DB (2GB-5GB): 15-30 minutes

### Step 6: Apply Collation Fix

This fixes the "Illegal mix of collations" error:

```bash
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < backend/migrations/fix_collation.sql
```

**Expected output:**
```
mysql: [Warning] Using a password on the command line interface can be insecure.
```

(The warning is normal and harmless)

### Step 7: Verify Migration

#### Test 1: Check Table Counts

```bash
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
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
"
```

**Compare these counts with laptop counts!**

#### Test 2: Check Database Size

```bash
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT
  TABLE_NAME,
  TABLE_ROWS,
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as Size_MB
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'fraud_detection'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
"
```

#### Test 3: Test Unified View (Collation Fix)

```bash
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT status, COUNT(*) as count
FROM unified_statements
GROUP BY status;
"
```

**Should work without collation errors!**

#### Test 4: Test Specific Queries

```bash
# Test filtering by status
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT run_id, acc_number, status
FROM unified_statements
WHERE status = 'FLAGGED'
LIMIT 5;
"

# Test processing status
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT processing_status, COUNT(*) as count
FROM unified_statements
GROUP BY processing_status;
"
```

### Step 8: Test Application

#### Test Web Interface

```bash
# Check backend is running
curl http://localhost:8501/health

# Expected output:
# {"status":"healthy","app":"Fraud Detection System","version":"1.0.0"}
```

**Open browser:**
1. Go to: http://localhost:8501
2. Check if statements are visible
3. Try filtering by status
4. Click on a statement to see details
5. Test search functionality

#### Test API

```bash
# Get statement list
curl -s "http://localhost:8501/api/v1/unified-list?page=1&page_size=5" | python3 -m json.tool

# Get filter options
curl -s "http://localhost:8501/api/v1/filter-options" | python3 -m json.tool

# Test status filter
curl -s "http://localhost:8501/api/v1/unified-list?status=VERIFIED&page_size=5" | python3 -m json.tool
```

### Step 9: Cleanup (Optional)

#### On Laptop

Keep backup file safe for at least 1 week:

```bash
# Move to safe location
mkdir -p ~/backups/fraud_detection
mv fraud_detection_backup_*.sql* ~/backups/fraud_detection/

# Create a verification file
cd ~/backups/fraud_detection
ls -lh > backup_manifest_$(date +%Y%m%d).txt
```

#### On PC

Remove backup file after successful verification:

```bash
cd ~/Developer/projects/airtel_fraud_detection

# Keep it for a few days, then remove
# rm fraud_detection_backup_*.sql*
```

## Troubleshooting

### Issue: Import Fails with "Access Denied"

```bash
# Check MySQL is running
docker-compose ps mysql

# Check MySQL logs
docker-compose logs mysql | tail -50

# Try connecting manually
docker-compose exec mysql mysql -u root -ppassword

# If that works, retry import
```

### Issue: Import is Very Slow

```bash
# Check disk I/O
docker stats

# Check MySQL settings
docker-compose exec mysql mysql -u root -ppassword -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"

# Increase buffer pool (edit docker-compose.yml)
# command: --innodb_buffer_pool_size=4G

# Restart MySQL
docker-compose restart mysql
```

### Issue: "Table doesn't exist" After Import

```bash
# Check which tables were imported
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "SHOW TABLES;"

# Check for errors in import
# The import command should have shown errors - review them

# If needed, drop database and retry
docker-compose exec mysql mysql -u root -ppassword -e "
  DROP DATABASE IF EXISTS fraud_detection;
  CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

# Retry import
```

### Issue: Collation Errors Persist

```bash
# Re-apply collation fix
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < backend/migrations/fix_collation.sql

# Verify view exists
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "SHOW CREATE VIEW unified_statements\G"

# Test query
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
  SELECT status, COUNT(*) FROM unified_statements GROUP BY status;
"
```

### Issue: Application Shows No Data

```bash
# Check backend logs
docker-compose logs backend | tail -100

# Check database connection
docker-compose exec backend python -c "
from app.services.db import SessionLocal
db = SessionLocal()
print('Database connected:', db.bind.url)
db.close()
"

# Restart backend
docker-compose restart backend
```

## Rollback Plan

If migration fails and you need to go back to laptop:

1. **Laptop is unchanged** - your original database is still there
2. On PC, just stop Docker: `docker-compose down -v`
3. Continue using laptop
4. Try migration again later with fixes

## Post-Migration

### Update Laptop Backup Script

Keep taking backups from laptop until PC is fully tested:

```bash
# On laptop - create backup script
cat > ~/backup-fraud-detection.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups/fraud_detection
mkdir -p $BACKUP_DIR
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
  --single-transaction \
  fraud_detection | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz
echo "Backup complete: $(ls -lh $BACKUP_DIR/backup_*.sql.gz | tail -1)"
EOF

chmod +x ~/backup-fraud-detection.sh
```

### Setup PC Backup Script

Create regular backups on PC:

```bash
# On PC
cat > ~/backup-fraud-detection-docker.sh << 'EOF'
#!/bin/bash
cd ~/Developer/projects/airtel_fraud_detection
BACKUP_DIR=~/backups/fraud_detection_pc
mkdir -p $BACKUP_DIR
docker-compose exec mysql mysqldump -u root -ppassword fraud_detection | \
  gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz
echo "Backup complete: $(ls -lh $BACKUP_DIR/backup_*.sql.gz | tail -1)"
EOF

chmod +x ~/backup-fraud-detection-docker.sh
```

### Parallel Usage Period (Recommended)

For 1-2 weeks:
1. Use PC for new imports (faster!)
2. Keep laptop as backup
3. Compare results between both
4. Once confident, retire laptop

## Performance Comparison

**Import Speed Test:**

After migration, test parallel import on PC:

```bash
# Test with 8 workers (dry run first)
docker-compose exec backend python process_parallel.py --workers 8 --dry-run

# Run actual import
docker-compose exec backend python process_parallel.py --workers 8
```

**Expected speedup: 10-20x faster than laptop!**

## Summary Checklist

- [ ] Database exported from laptop
- [ ] Backup file transferred to PC
- [ ] Docker setup completed
- [ ] Database imported successfully
- [ ] Collation fix applied
- [ ] Table counts verified
- [ ] Web interface tested
- [ ] API endpoints tested
- [ ] Laptop backup kept safe
- [ ] PC backup script created

## Support

If you encounter issues:

1. Check `docker-compose logs -f`
2. Review this guide's troubleshooting section
3. Test each verification step
4. Keep laptop database untouched as fallback

---

**Migration Time Estimate**: 30-60 minutes total

**Good luck with your migration!** 🚀
