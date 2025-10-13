# MySQL Backup - Quick Start Guide

## TL;DR

**Linux/Mac:**
```bash
./backup_mysql.sh
```

**Windows:**
```cmd
backup_mysql.bat
```

**Any Platform (Python):**
```bash
python3 backup_mysql.py
```

## What Makes These Scripts Special

✅ **Cross-version compatible**: Works with MySQL 5.7, 8.0, 8.1+
✅ **Cross-platform**: Windows, Linux, Mac
✅ **No charset errors**: Proper UTF-8 handling
✅ **No import errors**: Removes version-specific SQL
✅ **Docker-aware**: Auto-detects Docker or native MySQL

## Configuration

**No configuration needed!** Scripts automatically read from `.env` file:

```bash
# .env file
DB_HOST=127.0.0.1
DB_PORT=3307
DB_USER=root
DB_PASSWORD=password
DB_NAME=fraud_detection
DOCKER_CONTAINER=mysql-fraud-detection  # Optional
```

All credentials are securely stored in `.env` (not committed to git).

## Output

Backups saved to: `./backups/{DB_NAME}_backup_YYYYMMDD_HHMMSS.sql`

Example:
```
backups/fraud_detection_backup_20251013_153012.sql
```

## Restore Backup

```bash
# Via Docker
docker exec -i mysql-fraud-detection mysql -u root -ppassword fraud_detection < backups/fraud_detection_backup_20251013_153012.sql

# Direct connection
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection < backups/fraud_detection_backup_20251013_153012.sql
```

## Key Compatibility Flags

These flags prevent the errors you saw yesterday:

- `--default-character-set=utf8mb4` → No charset errors
- `--column-statistics=0` → MySQL 8.0+ compatibility
- `--skip-comments` → No version conflicts
- `--no-tablespaces` → No permission errors
- `--single-transaction` → Consistent snapshot

## Troubleshooting

**Problem**: "Docker container not found"
**Solution**: Update `DOCKER_CONTAINER` name in script

**Problem**: "Can't connect to MySQL"
**Solution**: Check if MySQL/Docker is running

**Problem**: "mysqldump: command not found"
**Solution**: Use Docker mode or install mysql-client

## Need More Info?

See `BACKUP_README.md` for full documentation.
