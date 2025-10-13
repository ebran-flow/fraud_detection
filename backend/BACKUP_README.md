# MySQL Backup Scripts - Cross-Platform & Cross-Version Compatible

## Overview

Three backup scripts for MySQL database running in Docker or standalone:
- **`backup_mysql.sh`** - Bash script (Linux/Mac/WSL)
- **`backup_mysql.bat`** - Batch script (Windows CMD)
- **`backup_mysql.py`** - Python script (Universal - All platforms)

## Features

✅ **Cross-Platform Compatible**: Works on Windows, Linux, Mac
✅ **Cross MySQL Version Compatible**: MySQL 5.7, 8.0, 8.1+
✅ **Docker & Standalone Support**: Works with Docker or native MySQL
✅ **Character Set Safe**: UTF-8/utf8mb4 support
✅ **No Version Conflicts**: Removes version-specific comments
✅ **Consistent Backups**: Uses `--single-transaction` for InnoDB
✅ **Complete Schema**: Includes triggers, routines, events

## Compatibility Features

The scripts use these mysqldump flags to ensure compatibility:

```bash
--single-transaction      # Consistent backup without locking tables
--routines                # Include stored procedures and functions
--triggers                # Include triggers
--events                  # Include scheduled events
--default-character-set=utf8mb4  # UTF-8 support
--set-charset             # Add SET NAMES to output
--no-tablespaces          # Avoid permission issues
--column-statistics=0     # MySQL 8.0+ compatibility
--skip-comments           # Remove version-specific comments
--compact                 # More compact output
--skip-lock-tables        # Don't lock tables during backup
```

## Configuration

**No manual configuration needed!** All scripts automatically read from `.env` file.

Your `.env` file should contain:

```bash
# Database Configuration (.env file)
DB_HOST=127.0.0.1
DB_PORT=3307
DB_USER=root
DB_PASSWORD=password
DB_NAME=fraud_detection

# Optional: Docker container name (defaults to mysql-fraud-detection)
DOCKER_CONTAINER=mysql-fraud-detection
```

**Security Note:** `.env` file is already in `.gitignore` - credentials are never committed to git.

### Custom Settings

To override default Docker container name, add to `.env`:
```bash
DOCKER_CONTAINER=your-container-name
```

## Usage

### Option 1: Bash Script (Linux/Mac/WSL)

```bash
# Make executable
chmod +x backup_mysql.sh

# Run backup
./backup_mysql.sh
```

### Option 2: Windows Batch Script

```cmd
# Double-click backup_mysql.bat
# Or run from Command Prompt:
backup_mysql.bat
```

### Option 3: Python Script (Universal)

```bash
# Linux/Mac
python3 backup_mysql.py

# Windows
python backup_mysql.py
```

## Docker Setup Detection

The scripts automatically detect your setup:

1. **Docker with named container**: Uses `docker exec` to run mysqldump inside container
2. **Port-forwarded MySQL**: Uses direct connection to localhost:3307
3. **Standalone MySQL**: Uses direct connection

## Backup Location

Backups are saved to `./backups/` directory with format `{DB_NAME}_backup_YYYYMMDD_HHMMSS.sql`:

```
backups/
├── fraud_detection_backup_20251013_141530.sql
├── fraud_detection_backup_20251013_150245.sql
└── fraud_detection_backup_20251013_153012.sql.gz
```

## Compression

All scripts support optional gzip compression:
- **Bash script**: Prompts after backup
- **Python script**: Prompts after backup
- **Windows batch**: Manual compression (see below)

### Manual Compression (Windows)

```cmd
# Install 7-Zip, then:
7z a airtel_backup.sql.gz airtel_backup.sql
```

## Restoring Backups

### From uncompressed backup:

```bash
# Via Docker
docker exec -i mysql-fraud-detection mysql -u root -ppassword fraud_detection < backups/fraud_detection_backup_20251013_141530.sql

# Direct connection
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection < backups/fraud_detection_backup_20251013_141530.sql
```

### From compressed backup:

```bash
# Via Docker
gunzip < backups/fraud_detection_backup_20251013_141530.sql.gz | docker exec -i mysql-fraud-detection mysql -u root -ppassword fraud_detection

# Direct connection
gunzip < backups/fraud_detection_backup_20251013_141530.sql.gz | mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection
```

### Windows (with 7-Zip):

```cmd
7z x backups\fraud_detection_backup_20251013_141530.sql.gz
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection < backups\fraud_detection_backup_20251013_141530.sql
```

## Why These Flags Matter

### `--single-transaction`
Creates consistent snapshot without locking tables (InnoDB only)

### `--default-character-set=utf8mb4`
Ensures proper UTF-8 encoding (4-byte Unicode support)

### `--no-tablespaces`
Prevents permission errors when importing on different systems

### `--column-statistics=0`
Removes MySQL 8.0+ specific statistics that cause errors in older versions

### `--skip-comments`
Removes server version comments that can cause compatibility issues

### `--compact`
Reduces output size by removing extra whitespace and comments

## Troubleshooting

### Error: "Unknown option '--column-statistics=0'"
You're using MySQL 5.7 or older. Edit the script and remove this line.

### Error: "Access denied for user"
Check your DB_USER and DB_PASSWORD in the configuration.

### Error: "Can't connect to MySQL server"
Check if MySQL/Docker is running and port number is correct.

### Error: "Docker container not found"
Update DOCKER_CONTAINER name in the configuration.

### Error: "mysqldump: not found" (Python/Bash direct mode)
Install MySQL client tools:
- **Ubuntu/Debian**: `sudo apt-get install mysql-client`
- **Mac**: `brew install mysql-client`
- **Windows**: Download from MySQL website or use Docker mode

## Best Practices

1. **Regular Backups**: Schedule daily backups using cron/Task Scheduler
2. **Test Restores**: Periodically test restoring backups to verify integrity
3. **Off-site Storage**: Copy backups to external storage or cloud
4. **Retention Policy**: Keep last 7 daily, 4 weekly, 12 monthly backups
5. **Compression**: Always compress large backups (>100MB)

## Automated Backups

### Linux/Mac (cron)

```bash
# Edit crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup_mysql.sh >> /var/log/mysql_backup.log 2>&1
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., Daily at 2:00 AM)
4. Action: Start a program
5. Program: `python` or `cmd.exe`
6. Arguments: `C:\path\to\backup_mysql.py` or `/c C:\path\to\backup_mysql.bat`

## File Sizes

Typical backup sizes for fraud_detection database:

- **Uncompressed**: ~50-200 MB (depends on data volume)
- **Compressed (gzip)**: ~10-40 MB
- **Compression ratio**: 5:1 to 10:1

## Security Notes

✅ **Credentials in .env**: Passwords are stored in `.env` file which is:
- Already in `.gitignore` (never committed to git)
- Separate from code (can be secured independently)
- Easy to rotate without changing scripts

**Recommended Permissions:**

```bash
# Linux/Mac: Restrict .env and script permissions
chmod 600 .env
chmod 700 backup_mysql.sh backup_mysql.py

# Windows: Right-click .env → Properties → Security → Advanced
# Remove all users except yourself
```

**Production Best Practices:**
- Use MySQL configuration file (`~/.my.cnf`) for credentials
- Store `.env` in secure location outside web root
- Use secret management tools (Vault, AWS Secrets Manager)
- Rotate passwords regularly

## Support

If you encounter issues:

1. Check MySQL/Docker logs
2. Verify database connection manually
3. Test mysqldump command directly
4. Check disk space in backup directory

---

**Created**: 2025-10-13
**Purpose**: Cross-platform, cross-version compatible MySQL backups
**Tested**: MySQL 5.7, 8.0, 8.1 on Windows/Linux/Mac with Docker
