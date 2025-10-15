# XtraBackup Scripts

Automated backup and restore scripts for the fraud_detection database using Percona XtraBackup.

## Quick Start

### 1. Install XtraBackup 8.2 (First Time Only)

**Easy installation (recommended):**
```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
sudo bash XTRABACKUP_INSTALL.sh
```

**Manual installation:**
```bash
curl -O https://repo.percona.com/apt/percona-release_latest.generic_all.deb
sudo apt install -y ./percona-release_latest.generic_all.deb
sudo percona-release enable-only ps-82 release
sudo percona-release enable tools release
sudo apt-get update
sudo apt-get install -y percona-xtrabackup-82
```

Verify installation:
```bash
xtrabackup --version
# Should show: xtrabackup version 8.2.x
```

### 2. Take Your First Full Backup

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
./scripts/backup/xtrabackup_full.sh
```

This will create a compressed backup in `../backups/xtrabackup/full/`

### 3. Take Incremental Backups

After you have a full backup, you can take incremental backups:

```bash
./scripts/backup/xtrabackup_incremental.sh
```

This will create an incremental backup in `../backups/xtrabackup/incremental/`

## Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `xtrabackup_full.sh` | Full database backup | Weekly (Sunday) or before major changes |
| `xtrabackup_incremental.sh` | Incremental backup | Daily (Mon-Sat) |
| `xtrabackup_restore.sh` | Restore database | When disaster recovery is needed |
| `xtrabackup_cleanup.sh` | Clean old backups | Weekly (Sunday) after full backup |

## Typical Backup Schedule

Set up cron jobs for automated backups:

```bash
crontab -e
```

Add:
```cron
# Full backup every Sunday at 2 AM
0 2 * * 0 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_full.sh >> /home/ebran/Developer/projects/airtel_fraud_detection/backend/logs/backup_full.log 2>&1

# Incremental backup every day (Mon-Sat) at 2 AM
0 2 * * 1-6 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_incremental.sh >> /home/ebran/Developer/projects/airtel_fraud_detection/backend/logs/backup_incremental.log 2>&1

# Clean old backups every Sunday at 3 AM
0 3 * * 0 /home/ebran/Developer/projects/airtel_fraud_detection/backend/scripts/backup/xtrabackup_cleanup.sh >> /home/ebran/Developer/projects/airtel_fraud_detection/backend/logs/backup_cleanup.log 2>&1
```

## Disaster Recovery

If database is lost or corrupted:

1. **Stop application** (prevent new writes)

2. **Run restore script:**
   ```bash
   ./scripts/backup/xtrabackup_restore.sh
   ```

   This will:
   - Stop MySQL container
   - Backup current data directory (just in case)
   - Restore from latest full backup
   - Apply all incremental backups
   - Start MySQL container
   - Verify database integrity

3. **Apply post-restore updates:**
   ```bash
   mysql -h 127.0.0.1 -P 3307 -u root -p$(grep DB_PASSWORD .env | cut -d '=' -f2) fraud_detection < scripts/migration/post_restore_updates.sql
   ```

4. **Follow POST_RESTORE_CHECKLIST.md** for remaining steps

## Backup Strategy

### Full Backup
- **Frequency:** Weekly (Sunday)
- **Time:** ~5-10 minutes
- **Size:** ~10-15 GB (compressed)
- **Retention:** Last 4 weeks

### Incremental Backup
- **Frequency:** Daily (Mon-Sat)
- **Time:** ~1-2 minutes
- **Size:** ~500 MB - 2 GB per day
- **Retention:** 7 days

### Total Storage
- Full backups: ~60 GB (4 weeks × 15 GB)
- Incremental: ~10 GB (7 days × 1.5 GB average)
- **Total: ~70 GB**

## Monitoring

Check backup status:

```bash
# List backups
ls -lth ../backups/xtrabackup/full/ | head -5
ls -lth ../backups/xtrabackup/incremental/ | head -10

# Check backup logs
tail -50 logs/backup_full.log
tail -50 logs/backup_incremental.log

# Check disk usage
du -sh ../backups/xtrabackup/
```

## Comparison: mysqldump vs XtraBackup

| Feature | mysqldump (old) | XtraBackup (new) |
|---------|----------------|------------------|
| Backup time | ~30 min | ~10 min |
| Restore time | ~40 min per table | ~15 min total |
| Incremental | No | Yes |
| Compression | Yes | Yes |
| Hot backup | No (locks) | Yes (no locks) |
| Point-in-time | No | Yes |

## Troubleshooting

### xtrabackup command not found
```bash
sudo apt-get install percona-xtrabackup-80
```

### Can't connect to MySQL
```bash
# Check MySQL container is running
docker ps | grep mysql

# Check port is accessible
netstat -tlnp | grep 3307
```

### No space left on device
```bash
# Clean old backups
./scripts/backup/xtrabackup_cleanup.sh

# Check disk usage
df -h
```

### Restore failed
Check logs:
```bash
ls -lth logs/restore_*.log | head -1
tail -100 logs/restore_<timestamp>.log
```

## Important Notes

1. **Always test restore** on a test environment first
2. **Full backup before major changes** (schema migrations, bulk updates)
3. **Monitor disk space** - backups require significant storage
4. **Secure backup files** - they contain sensitive data
5. **Verify backups regularly** - corrupt backups are useless

## See Also

- [XTRABACKUP_SETUP.md](../../XTRABACKUP_SETUP.md) - Detailed setup guide
- [POST_RESTORE_CHECKLIST.md](../../POST_RESTORE_CHECKLIST.md) - Steps after restore
- [Percona XtraBackup Documentation](https://docs.percona.com/percona-xtrabackup/8.0/)
