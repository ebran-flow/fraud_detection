# MySQL 8.0 Local Installation Guide

## Why Install MySQL 8.0 Locally?

Your current setup has MySQL 8.2 in Docker, which is incompatible with Percona XtraBackup 8.0. By installing MySQL 8.0 locally:

✅ Full XtraBackup 8.0 compatibility (incremental backups)
✅ Faster backups and restores
✅ Point-in-time recovery
✅ Direct access without Docker overhead

## Installation Steps

### Step 1: Install MySQL 8.0

```bash
# Add MySQL APT repository
wget https://dev.mysql.com/get/mysql-apt-config_0.8.29-1_all.deb
sudo dpkg -i mysql-apt-config_0.8.29-1_all.deb
# Select: MySQL Server & Cluster → mysql-8.0 → Ok

# Update and install
sudo apt-get update
sudo apt-get install -y mysql-server-8.0

# Verify installation
mysql --version
# Should show: mysql  Ver 8.0.x
```

### Step 2: Configure MySQL 8.0

```bash
# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure installation
sudo mysql_secure_installation
# Set root password
# Remove anonymous users: Yes
# Disallow root login remotely: No (we need it for localhost)
# Remove test database: Yes
# Reload privilege tables: Yes
```

### Step 3: Configure MySQL for Local Access

```bash
# Edit MySQL config
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Ensure these settings:
[mysqld]
port = 3306
bind-address = 127.0.0.1

# Restart MySQL
sudo systemctl restart mysql
```

### Step 4: Create Database and User

```bash
# Login to MySQL
sudo mysql -u root -p

# Create database
CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user (optional - or use root)
CREATE USER 'fraud_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON fraud_detection.* TO 'fraud_user'@'localhost';
FLUSH PRIVILEGES;

EXIT;
```

### Step 5: Restore Database from Docker Backup

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backups/tables

# Get MySQL root password
read -sp "Enter MySQL root password: " MYSQL_PASSWORD
echo

# Restore all tables (in order)
echo "Restoring metadata..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_metadata.sql

echo "Restoring summary..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_summary.sql

echo "Restoring uatl_raw_statements (6.9GB - ~30 min)..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_uatl_raw_statements.sql

echo "Restoring uatl_processed_statements (7.1GB - ~30 min)..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_uatl_processed_statements.sql

echo "Restoring umtn_raw_statements (7.3GB - ~30 min)..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_umtn_raw_statements.sql

echo "Restoring umtn_processed_statements (6.9GB - ~30 min)..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_umtn_processed_statements.sql

echo "Restoring uatl_balance_issues..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_uatl_balance_issues.sql

echo "Restoring umtn_balance_issues..."
mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < fraud_detection_umtn_balance_issues.sql

echo "✅ All tables restored!"
```

### Step 6: Apply Post-Restore Schema Updates

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend

mysql -u root -p"$MYSQL_PASSWORD" fraud_detection < scripts/migration/post_restore_updates.sql
```

### Step 7: Install Percona XtraBackup 8.0

```bash
# Install Percona repository
wget https://repo.percona.com/apt/percona-release_latest.$(lsb_release -sc)_all.deb
sudo dpkg -i percona-release_latest.$(lsb_release -sc)_all.deb

# Enable tools repository
sudo percona-release enable-only tools release
sudo apt-get update

# Install XtraBackup 8.0
sudo apt-get install -y percona-xtrabackup-80

# Verify installation
xtrabackup --version
# Should show: xtrabackup version 8.0.x
```

### Step 8: Test XtraBackup

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend

# Create test backup
xtrabackup --backup \
  --user=root \
  --password="$MYSQL_PASSWORD" \
  --target-dir=/tmp/xtrabackup_test

# If successful:
rm -rf /tmp/xtrabackup_test
echo "✅ XtraBackup working!"
```

## Configuration Files to Update

### Update .env file

```bash
# Edit .env
nano .env

# Update these values for local MySQL:
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=fraud_detection
```

## Running Both MySQL Instances

You can run both Docker MySQL 8.2 and local MySQL 8.0 simultaneously:

- **Docker MySQL 8.2:** Port 3307 (production/existing data)
- **Local MySQL 8.0:** Port 3306 (backups with XtraBackup)

## Backup Strategy with Local MySQL 8.0

Once setup is complete:

1. **Weekly full backup** (Sunday 2 AM):
   ```bash
   ./scripts/backup/xtrabackup_full.sh
   ```

2. **Daily incremental backup** (Mon-Sat 2 AM):
   ```bash
   ./scripts/backup/xtrabackup_incremental.sh
   ```

3. **Automated with cron:**
   ```cron
   0 2 * * 0 /path/to/xtrabackup_full.sh
   0 2 * * 1-6 /path/to/xtrabackup_incremental.sh
   ```

## Estimated Timeline

| Task | Time |
|------|------|
| Install MySQL 8.0 | 5 min |
| Configure MySQL | 5 min |
| Restore database | 2-3 hours |
| Install XtraBackup | 5 min |
| Test backup | 10 min |
| **Total** | **2.5-3.5 hours** |

## Disk Space Requirements

- MySQL 8.0 installation: ~500 MB
- fraud_detection database: ~30 GB
- XtraBackup backups: ~70 GB (full + incrementals)
- **Total:** ~100 GB

## Next Steps

1. Run installation script (automated)
2. Restore database from backups
3. Apply schema updates
4. Test XtraBackup
5. Set up automated backups

## Alternative: Script-Based Installation

I can create an automated installation script that handles all steps. Would you like me to create this?
