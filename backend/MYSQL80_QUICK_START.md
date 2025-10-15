# MySQL 8.0 Local Setup - Quick Start Guide

## Overview

This guide sets up MySQL 8.0 locally for XtraBackup compatibility, solving the MySQL 8.2 + XtraBackup incompatibility issue.

## Why This Approach?

**Problem:**
- Docker MySQL 8.2 → XtraBackup 8.0 ❌ (incompatible)
- XtraBackup 8.2 → Not available in Docker/APT repos ❌

**Solution:**
- Local MySQL 8.0 → XtraBackup 8.0 ✅ (fully compatible)
- Incremental backups ✅
- Point-in-time recovery ✅

## 3-Step Installation

### Step 1: Install MySQL 8.0 (5 minutes)

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
sudo bash install_mysql80_local.sh
```

This will:
- Download and install MySQL 8.0
- Start MySQL service
- Create fraud_detection database
- Configure MySQL on port 3306

### Step 2: Restore Database (2-3 hours)

```bash
bash restore_to_local_mysql.sh
```

This will restore all 8 tables from your backups:
- metadata (quick)
- summary (quick)
- uatl_raw_statements (6.9GB - ~30 min)
- uatl_processed_statements (7.1GB - ~30 min)
- umtn_raw_statements (7.3GB - ~30 min)
- umtn_processed_statements (6.9GB - ~30 min)
- uatl_balance_issues (quick)
- umtn_balance_issues (quick)

### Step 3: Install XtraBackup (5 minutes)

```bash
sudo bash install_xtrabackup.sh
```

This will:
- Install Percona XtraBackup 8.0
- Create backup directories
- Test XtraBackup connection
- Verify everything works

## Configuration

### Both MySQL Instances Running

You can run both simultaneously:

```
Docker MySQL 8.2:  127.0.0.1:3307 (production)
Local MySQL 8.0:   127.0.0.1:3306 (backups)
```

### Application Configuration

Update `.env` to use local MySQL:

```bash
DB_HOST=127.0.0.1
DB_PORT=3306          # Changed from 3307
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=fraud_detection
```

## Post-Installation

### Apply Schema Updates

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
mysql -u root -p fraud_detection < scripts/migration/post_restore_updates.sql
```

### Take First Backup

```bash
./scripts/backup/xtrabackup_full.sh
```

Expected time: ~10 minutes
Expected size: ~10-15 GB (compressed)

### Verify Backup

```bash
ls -lh ../backups/xtrabackup/full/
```

## Automated Backups

Set up cron jobs:

```bash
crontab -e
```

Add:

```cron
# Full backup every Sunday at 2 AM
0 2 * * 0 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_full.sh

# Incremental backup Mon-Sat at 2 AM
0 2 * * 1-6 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_incremental.sh

# Cleanup old backups Sunday at 3 AM
0 3 * * 0 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_cleanup.sh
```

## Timeline

| Step | Time | Status |
|------|------|--------|
| Install MySQL 8.0 | 5 min | ⏳ Ready to run |
| Restore database | 2-3 hours | ⏳ Ready to run |
| Install XtraBackup | 5 min | ⏳ Ready to run |
| Take first backup | 10 min | ⏳ After restore |
| **Total** | **3-3.5 hours** | |

## Disk Space

- MySQL 8.0: ~500 MB
- fraud_detection: ~30 GB
- XtraBackup backups: ~70 GB
- **Total: ~100 GB**

## Scripts Created

```
backend/
├── install_mysql80_local.sh     # Step 1: Install MySQL 8.0
├── restore_to_local_mysql.sh    # Step 2: Restore database
├── install_xtrabackup.sh        # Step 3: Install XtraBackup
├── MYSQL80_LOCAL_SETUP.md       # Detailed guide
└── MYSQL80_QUICK_START.md       # This file
```

## Troubleshooting

### MySQL won't start

```bash
sudo systemctl status mysql
sudo journalctl -xeu mysql
```

### Restore fails

Check MySQL is running:
```bash
sudo systemctl start mysql
mysql -u root -p -e "SELECT 1"
```

### XtraBackup fails

Verify MySQL 8.0:
```bash
mysql --version
# Should show: mysql  Ver 8.0.x
```

## Ready to Start?

Run the first command:

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
sudo bash install_mysql80_local.sh
```

Then follow the on-screen instructions!
