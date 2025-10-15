# Percona XtraBackup 8.2 Setup Guide

✅ **Updated for MySQL 8.2.0** - This guide uses Percona XtraBackup 8.2

## Why XtraBackup for Incremental Backups?

After the recent database incident, we need faster backup and restore capabilities:

| Method | Backup Time | Restore Time | Incremental | Storage Efficient |
|--------|-------------|--------------|-------------|-------------------|
| mysqldump (current) | ~30 min | ~40 min/table | No | No |
| XtraBackup | ~5-10 min | ~10-15 min | Yes | Yes |

**Key Benefits:**
- **Point-in-time recovery:** Restore to exact moment before data loss
- **Incremental backups:** Only backup changes since last backup
- **Fast restoration:** 3-4x faster than mysqldump
- **Hot backups:** No downtime during backup
- **Space efficient:** Incremental backups are much smaller

## Prerequisites

- Ubuntu 24.04 LTS
- Docker MySQL 8.2 running on port 3307
- Sudo access for installation
- ~50GB free space for backups

## Installation Steps

### Step 1: Install Percona XtraBackup 8.2

```bash
# Download and install Percona repository
curl -O https://repo.percona.com/apt/percona-release_latest.generic_all.deb
sudo apt install -y ./percona-release_latest.generic_all.deb

# Enable Percona Server 8.2 and tools repositories
sudo percona-release enable-only ps-82 release
sudo percona-release enable tools release
sudo apt-get update

# Install XtraBackup 8.2 (for MySQL 8.2)
sudo apt-get install -y percona-xtrabackup-82

# Verify installation
xtrabackup --version
# Should show: xtrabackup version 8.2.x

# Clean up
rm percona-release_latest.generic_all.deb
```

### Step 2: Configure Backup Directory

```bash
# Create backup directories
sudo mkdir -p /home/ebran/Developer/projects/airtel_fraud_detection/backups/xtrabackup/{full,incremental}
sudo chown -R $USER:$USER /home/ebran/Developer/projects/airtel_fraud_detection/backups/xtrabackup
chmod 755 /home/ebran/Developer/projects/airtel_fraud_detection/backups/xtrabackup
```

### Step 3: Create XtraBackup User (Optional but Recommended)

For security, create a dedicated MySQL user for backups:

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
source .env

mysql -h 127.0.0.1 -P 3307 -u root -p"$DB_PASSWORD" <<EOF
CREATE USER IF NOT EXISTS 'xtrabackup'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT RELOAD, PROCESS, LOCK TABLES, REPLICATION CLIENT, SUPER ON *.* TO 'xtrabackup'@'localhost';
GRANT BACKUP_ADMIN ON *.* TO 'xtrabackup'@'localhost';
FLUSH PRIVILEGES;
EOF
```

**Note:** Update your `.env` file with the xtrabackup user credentials if you choose to use it.

### Step 4: Test XtraBackup Connection

```bash
# Test connection to Docker MySQL
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
source .env

xtrabackup --backup \
  --host=127.0.0.1 \
  --port=3307 \
  --user=root \
  --password="$DB_PASSWORD" \
  --target-dir=/tmp/xtrabackup_test \
  --databases="fraud_detection"

# If successful, clean up test backup
rm -rf /tmp/xtrabackup_test
```

## Backup Strategy

### Full Backup (Weekly - Sunday)
- Complete backup of entire database
- Takes ~5-10 minutes for 28GB database
- Storage: ~28GB compressed

### Incremental Backup (Daily - Mon-Sat)
- Only backs up changes since last backup
- Takes ~1-2 minutes
- Storage: ~500MB-2GB per day (depending on activity)

### Backup Retention
- **Full backups:** Keep last 4 weeks (monthly rotation)
- **Incremental backups:** Keep last 7 days
- **Before major changes:** Always take full backup

## Automated Scripts

The following scripts have been created in `scripts/backup/`:

1. **`xtrabackup_full.sh`** - Full database backup
2. **`xtrabackup_incremental.sh`** - Incremental backup
3. **`xtrabackup_restore.sh`** - Restore from backups
4. **`xtrabackup_cleanup.sh`** - Clean old backups

## Usage

### Take Full Backup

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
./scripts/backup/xtrabackup_full.sh
```

### Take Incremental Backup

```bash
./scripts/backup/xtrabackup_incremental.sh
```

### Restore from Backup

```bash
# Restore latest full + all incremental backups
./scripts/backup/xtrabackup_restore.sh

# Restore specific backup
./scripts/backup/xtrabackup_restore.sh /path/to/backup
```

### List Available Backups

```bash
ls -lh ../backups/xtrabackup/full/
ls -lh ../backups/xtrabackup/incremental/
```

## Cron Automation

Add to crontab for automated backups:

```bash
crontab -e
```

Add these lines:

```cron
# Full backup every Sunday at 2 AM
0 2 * * 0 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_full.sh >> /home/ebran/Developer/projects/airtel_fraud_detection/backend/logs/backup_full.log 2>&1

# Incremental backup every day (Mon-Sat) at 2 AM
0 2 * * 1-6 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_incremental.sh >> /home/ebran/Developer/projects/airtel_fraud_detection/backend/logs/backup_incremental.log 2>&1

# Clean old backups every Sunday at 3 AM
0 3 * * 0 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_cleanup.sh >> /home/ebran/Developer/projects/airtel_fraud_detection/backend/logs/backup_cleanup.log 2>&1
```

## Disaster Recovery Example

**Scenario:** Database dropped at 4:00 PM on Wednesday

**Recovery steps:**

1. Stop database writes (stop application)
2. Run restore script:
   ```bash
   ./scripts/backup/xtrabackup_restore.sh
   ```
3. This will:
   - Restore Sunday's full backup
   - Apply Monday's incremental backup
   - Apply Tuesday's incremental backup
   - Apply Wednesday's incremental backup (up to 2 AM)
4. Data loss: Only 14 hours (2 AM - 4 PM)
5. Restore time: ~15 minutes (vs 2-3 hours with mysqldump)

**To minimize data loss further:**
- Run incremental backups more frequently (every 6 hours)
- Enable MySQL binary logs for point-in-time recovery

## Comparison: Before and After

### Before (Current System)
- **Backup:** mysqldump tables individually (~30 minutes)
- **Restore:** Import 4 large tables in parallel (~40 minutes)
- **Total downtime:** ~40 minutes
- **Data loss:** Depends on when last backup was taken
- **Storage:** ~28GB per backup

### After (With XtraBackup)
- **Backup:** Full backup once a week (~10 minutes)
- **Incremental:** Daily backups (~2 minutes)
- **Restore:** Single command (~15 minutes)
- **Total downtime:** ~15 minutes
- **Data loss:** Maximum 24 hours (or less with frequent incrementals)
- **Storage:** 28GB + ~10GB incremental per week = ~38GB

## Monitoring

Check backup status:

```bash
# Check last backup
ls -lth ../backups/xtrabackup/full/ | head -3
ls -lth ../backups/xtrabackup/incremental/ | head -10

# Check backup logs
tail -50 logs/backup_full.log
tail -50 logs/backup_incremental.log
```

## Troubleshooting

### Error: "xtrabackup: command not found"
- XtraBackup not installed. Run installation steps above.

### Error: "Access denied for user 'root'"
- Check DB_PASSWORD in .env file
- Verify MySQL is running: `docker ps | grep mysql`

### Error: "Can't connect to MySQL server"
- Check MySQL container: `docker ps | grep mysql`
- Verify port 3307 is exposed: `netstat -tlnp | grep 3307`

### Error: "No space left on device"
- Clean old backups: `./scripts/backup/xtrabackup_cleanup.sh`
- Check disk space: `df -h`

## Security Notes

- Backup files contain sensitive data
- Ensure backup directory has restricted permissions (755)
- Never commit backup scripts with hardcoded passwords
- Use .env file for credentials
- Consider encrypting backups for production environments

## Next Steps

1. **Run installation commands** (requires sudo)
2. **Test full backup** to verify setup
3. **Test incremental backup**
4. **Test restore** on a test database
5. **Set up cron jobs** for automation
6. **Document restore procedures** for team
