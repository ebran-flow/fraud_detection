# Scripts Updated to Use .env Credentials

All scripts now read database credentials from `/home/ebran/Developer/projects/airtel_fraud_detection/backend/.env`.

## Current .env Configuration

```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=fraud_user
DB_PASSWORD=fraud_password
DB_NAME=fraud_detection
```

## Updated Scripts

### 1. XtraBackup Scripts
**scripts/backup/xtrabackup_full.sh**
- ✅ Uses `${DB_HOST}`, `${DB_PORT}`, `${DB_USER}`, `${DB_PASSWORD}`, `${DB_NAME}` from .env
- ✅ Removed hardcoded values
- ✅ Added connection verification message

**scripts/backup/xtrabackup_incremental.sh**
- ✅ Uses `${DB_HOST}`, `${DB_PORT}`, `${DB_USER}`, `${DB_PASSWORD}`, `${DB_NAME}` from .env
- ✅ Removed hardcoded values
- ✅ Added connection info logging

**scripts/backup/xtrabackup_restore.sh**
- ✅ Uses `${DB_HOST}`, `${DB_PORT}`, `${DB_USER}`, `${DB_PASSWORD}`, `${DB_NAME}` from .env
- ✅ Changed from Docker MySQL to systemctl for local MySQL
- ✅ Removed hardcoded values

### 2. User Management Scripts
**fix_mysql_auth.sh**
- ✅ Sources .env file
- ✅ Uses `${DB_USER}` and `${DB_PASSWORD}` from .env
- ✅ Removed hardcoded "password"

**create_fraud_user_local.sh**
- ✅ Sources .env file
- ✅ Uses all DB_ variables from .env
- ✅ Creates user with credentials from .env
- ✅ Removed hardcoded "fraud_user" and "fraud_password"

**create_fraud_user.sh** (for Docker MySQL - port 3307)
- ⚠️ Still uses Docker MySQL settings (port 3307)
- Note: This script is for Docker MySQL, not local MySQL

### 3. Installation Scripts
**install_xtrabackup.sh**
- ✅ Sources .env file
- ✅ Uses all DB_ variables for XtraBackup test
- ✅ Removed hardcoded password "\password"

**restore_to_local_mysql.sh**
- ✅ Already uses .env (sources it at beginning)

**install_mysql80_local.sh**
- ℹ️ Interactive script - prompts for password during MySQL installation
- ℹ️ Creates database but doesn't set credentials (handled by MySQL installer)

## No Hardcoded Credentials

All scripts now pull credentials exclusively from `.env`:
- ❌ No hardcoded passwords
- ❌ No hardcoded usernames
- ❌ No hardcoded hosts/ports
- ✅ Single source of truth: `.env` file

## Testing Credentials

To test database connection with current .env:
```bash
mysql -h 127.0.0.1 -P 3306 -u fraud_user -pfraud_password fraud_detection -e "SELECT 1"
```

## Backup Commands

All backup scripts now use .env automatically:
```bash
# Full backup
./scripts/backup/xtrabackup_full.sh

# Incremental backup
./scripts/backup/xtrabackup_incremental.sh

# Restore
./scripts/backup/xtrabackup_restore.sh
```

## Security Note

The `.env` file contains sensitive credentials. Ensure:
- ✅ `.env` is in `.gitignore`
- ✅ File permissions: `chmod 600 .env`
- ✅ Only readable by owner

## Update Checklist

When changing database credentials:
1. Update `.env` file
2. No need to update any scripts (they read from .env automatically)
3. If changing user, run `bash create_fraud_user_local.sh` to create the new user
4. Test connection with new credentials

## Verification

To verify all scripts use .env:
```bash
# Check for hardcoded credentials (should return nothing)
grep -r "password.*=" scripts/ *.sh | grep -v ".env" | grep -v "PASSWORD="
```

All scripts updated: **2025-10-15**
