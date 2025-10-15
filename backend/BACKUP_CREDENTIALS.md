# Backup Credentials Configuration

## Overview

XtraBackup scripts use a **separate configuration file** (`.env.xtrabackup`) instead of the main `.env` file. This separation provides better security and privilege management.

---

## Why Separate Configuration?

### Security Reasons:
1. **Principle of Least Privilege**: Application uses restricted `fraud_user` account, backups need elevated privileges
2. **Separation of Concerns**: Backup operations vs application operations use different credentials
3. **Audit Trail**: Easier to track backup operations separately
4. **Protection**: Application cannot accidentally use root credentials for normal operations

### Practical Reasons:
1. **Different User Requirements**:
   - **Application (.env)**: Uses `fraud_user` with limited permissions (no DROP privileges)
   - **Backups (.env.xtrabackup)**: Uses `root` with full backup privileges

2. **XtraBackup Permissions**: Requires `RELOAD`, `LOCK TABLES`, `PROCESS`, `REPLICATION CLIENT` privileges

---

## Configuration Files

### 1. `.env` - Application Configuration
**Location:** `/home/ebran/Developer/projects/airtel_fraud_detection/backend/.env`

**Used by:**
- Application code
- API endpoints
- Data processing scripts
- Analysis scripts
- User creation scripts

**Current Configuration:**
```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=fraud_user
DB_PASSWORD=fraud_password
DB_NAME=fraud_detection
```

**Permissions:** Limited user (no DROP privileges)

---

### 2. `.env.xtrabackup` - Backup Configuration
**Location:** `/home/ebran/Developer/projects/airtel_fraud_detection/backend/.env.xtrabackup`

**Used by:**
- `scripts/backup/xtrabackup_full.sh`
- `scripts/backup/xtrabackup_incremental.sh`
- `scripts/backup/xtrabackup_restore.sh`

**Current Configuration:**
```bash
# MySQL Connection Settings
BACKUP_DB_HOST=127.0.0.1
BACKUP_DB_PORT=3306
BACKUP_DB_USER=root
BACKUP_DB_PASSWORD=password
BACKUP_DB_NAME=fraud_detection

# Backup Directory Configuration
BACKUP_BASE_DIR=/home/ebran/Developer/projects/airtel_fraud_detection/backups/xtrabackup

# Backup Retention Settings
FULL_BACKUP_RETENTION=4     # Keep last 4 full backups
INCREMENTAL_RETENTION_DAYS=7  # Keep incremental backups for 7 days

# Backup Performance Settings
BACKUP_PARALLEL_THREADS=4
BACKUP_COMPRESS_THREADS=4
```

**Permissions:** Full backup privileges (root user)

---

## Scripts Updated

All XtraBackup scripts now use `.env.xtrabackup`:

### ✅ Updated Scripts:
1. **xtrabackup_full.sh**
   - Sources `.env.xtrabackup` instead of `.env`
   - Uses `BACKUP_DB_*` variables
   - Uses configurable retention settings

2. **xtrabackup_incremental.sh**
   - Sources `.env.xtrabackup` instead of `.env`
   - Uses `BACKUP_DB_*` variables
   - Uses configurable retention settings

3. **xtrabackup_restore.sh**
   - Sources `.env.xtrabackup` instead of `.env`
   - Uses `BACKUP_DB_*` variables for restore operations

### ❌ Not Updated (Intentionally):
- All other scripts continue using `.env` (application credentials)

---

## Variable Mapping

| Purpose | .env | .env.xtrabackup |
|---------|------|-----------------|
| Host | `DB_HOST` | `BACKUP_DB_HOST` |
| Port | `DB_PORT` | `BACKUP_DB_PORT` |
| User | `DB_USER` | `BACKUP_DB_USER` |
| Password | `DB_PASSWORD` | `BACKUP_DB_PASSWORD` |
| Database | `DB_NAME` | `BACKUP_DB_NAME` |

---

## Usage Examples

### Full Backup
```bash
# Uses .env.xtrabackup automatically
./scripts/backup/xtrabackup_full.sh
```

**What happens:**
1. Script sources `.env.xtrabackup`
2. Connects as `root` user
3. Creates compressed backup
4. Cleans up old backups (keeps last 4)

### Incremental Backup
```bash
# Uses .env.xtrabackup automatically
./scripts/backup/xtrabackup_incremental.sh
```

**What happens:**
1. Script sources `.env.xtrabackup`
2. Connects as `root` user
3. Creates incremental backup based on last backup
4. Cleans up backups older than 7 days

### Restore
```bash
# Uses .env.xtrabackup automatically
./scripts/backup/xtrabackup_restore.sh
```

**What happens:**
1. Script sources `.env.xtrabackup`
2. Uses `root` credentials for restore
3. Stops MySQL, restores data, starts MySQL
4. Verifies restoration

---

## Security Best Practices

### File Permissions:
```bash
# Secure both .env files
chmod 600 .env
chmod 600 .env.xtrabackup
```

### Git Ignore:
Both files are in `.gitignore`:
```
.env
.env.xtrabackup
```

### Access Control:
- ✅ Only backup scripts can access `.env.xtrabackup`
- ✅ Application never sees root credentials
- ✅ fraud_user cannot drop tables/database
- ✅ root user only used for backups

---

## Modifying Credentials

### Changing Application Credentials:
Edit `.env` only - backup scripts unaffected:
```bash
vim .env
# Update DB_USER and DB_PASSWORD
# No need to touch .env.xtrabackup
```

### Changing Backup Credentials:
Edit `.env.xtrabackup` only - application unaffected:
```bash
vim .env.xtrabackup
# Update BACKUP_DB_USER and BACKUP_DB_PASSWORD
# No need to touch .env
```

### Changing Root Password:
If MySQL root password changes:
```bash
vim .env.xtrabackup
# Update BACKUP_DB_PASSWORD
```

---

## Backup Retention Configuration

Customize retention in `.env.xtrabackup`:

```bash
# Keep more full backups
FULL_BACKUP_RETENTION=7     # Keep last 7 full backups

# Keep incremental backups longer
INCREMENTAL_RETENTION_DAYS=14  # Keep for 14 days

# Adjust performance
BACKUP_PARALLEL_THREADS=8       # More threads for faster backup
BACKUP_COMPRESS_THREADS=8       # More compression threads
```

---

## Troubleshooting

### Error: Cannot connect to MySQL database
**Check:**
```bash
# Test connection with backup credentials
source .env.xtrabackup
mysql -h ${BACKUP_DB_HOST} -P ${BACKUP_DB_PORT} -u ${BACKUP_DB_USER} -p${BACKUP_DB_PASSWORD} -e "SELECT 1"
```

### Error: .env.xtrabackup file not found
**Solution:**
```bash
# Create from template
cp .env.xtrabackup.example .env.xtrabackup
# Edit with your credentials
vim .env.xtrabackup
```

### Permission Denied
**Solution:**
```bash
# XtraBackup needs sudo to access MySQL data directory
# Script will prompt for sudo password automatically
```

---

## Migration from Old Setup

If you have old scripts using `.env`:

1. ✅ **Already updated** - All XtraBackup scripts now use `.env.xtrabackup`
2. ✅ **Verified** - `.env` still used by application
3. ✅ **Secured** - `.env.xtrabackup` has 600 permissions
4. ✅ **Git Safe** - Both files in `.gitignore`

**No action needed!** 🎉

---

## Summary

| Aspect | .env | .env.xtrabackup |
|--------|------|-----------------|
| **Purpose** | Application operations | Backup operations only |
| **User** | fraud_user (limited) | root (full privileges) |
| **Used By** | App, API, scripts | XtraBackup scripts only |
| **Privileges** | No DROP | Full backup privileges |
| **Security** | Protected from drops | Protected from app misuse |

---

Last Updated: 2025-10-16
