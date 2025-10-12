# SQL Import Troubleshooting Guide

## Method 1: Copy File into Container (Most Reliable)

This method avoids Windows pipe issues:

```powershell
# 1. Copy SQL file into container
docker cp backup.sql fraud_detection_mysql:/tmp/backup.sql

# 2. Import from inside container
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "source /tmp/backup.sql"

# OR run mysql interactively
docker compose exec mysql bash
mysql -u root -ppassword fraud_detection
source /tmp/backup.sql
exit
```

## Method 2: Direct Import (Single Command)

```powershell
# Using docker exec (more reliable than compose)
Get-Content backup.sql | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection

# OR with docker compose
type backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection
```

## Method 3: Split Large Files

If file is too large (>1GB):

```powershell
# Split into smaller chunks
$content = Get-Content backup.sql
$chunkSize = 10000
$chunks = [Math]::Ceiling($content.Count / $chunkSize)

for ($i = 0; $i -lt $chunks; $i++) {
    $start = $i * $chunkSize
    $end = [Math]::Min(($i + 1) * $chunkSize - 1, $content.Count - 1)
    $content[$start..$end] | Out-File "backup_part_$i.sql" -Encoding UTF8
}

# Import each chunk
Get-ChildItem backup_part_*.sql | ForEach-Object {
    Write-Host "Importing $($_.Name)..."
    Get-Content $_.FullName | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection
}
```

## Method 4: Using Volume Mount

```powershell
# 1. Stop containers
docker compose down

# 2. Edit docker-compose.yml, add volume to mysql service:
#   volumes:
#     - mysql_data:/var/lib/mysql
#     - ./:/host:ro

# 3. Start containers
docker compose up -d

# 4. Import
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "source /host/backup.sql"
```

## Method 5: Compressed File Import

If you have a .gz file:

```powershell
# Option A: Extract first, then import
7z x backup.sql.gz
Get-Content backup.sql | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection

# Option B: Stream decompression (requires 7z in container)
7z x -so backup.sql.gz | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection
```

## Common Issues and Solutions

### Issue 1: "ERROR 2006: MySQL server has gone away"

**Cause:** Import timeout or max_allowed_packet too small

**Solution:**
```powershell
# Increase timeouts
docker compose exec mysql mysql -u root -ppassword -e "
SET GLOBAL max_allowed_packet=1073741824;
SET GLOBAL net_read_timeout=600;
SET GLOBAL net_write_timeout=600;
"

# Then retry import
```

### Issue 2: Character encoding errors

**Cause:** Windows encoding vs UTF-8

**Solution:**
```powershell
# Re-save file with UTF-8 encoding
Get-Content backup.sql | Out-File backup_utf8.sql -Encoding UTF8

# Import UTF-8 file
Get-Content backup_utf8.sql | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection
```

### Issue 3: "Database doesn't exist"

**Cause:** Database not created yet

**Solution:**
```powershell
# Create database first
docker compose exec mysql mysql -u root -ppassword -e "
CREATE DATABASE IF NOT EXISTS fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

# Then import
```

### Issue 4: "Access denied"

**Cause:** Wrong credentials

**Solution:**
```powershell
# Check what's in docker-compose.yml
docker compose exec mysql mysql -u root -ppassword
# If this doesn't work, password might be different

# Reset password if needed
docker compose down
# Remove .env and recreate from .env.docker
docker compose up -d
```

### Issue 5: File path issues

**Cause:** Windows path with spaces or special characters

**Solution:**
```powershell
# Use full path in quotes
Get-Content "C:\Users\YourName\path with spaces\backup.sql" | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection

# Or copy to project folder first
Copy-Item "path\to\backup.sql" .\backup.sql
Get-Content backup.sql | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection
```

### Issue 6: PowerShell hangs/freezes

**Cause:** Large file buffering in memory

**Solution:** Use CMD instead of PowerShell:
```cmd
cd C:\path\to\project
type backup.sql | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection
```

## Recommended Approach (Step-by-Step)

### Step 1: Verify MySQL is Running

```powershell
docker compose ps mysql
# Should show "Up (healthy)"
```

### Step 2: Verify Database Exists

```powershell
docker compose exec mysql mysql -u root -ppassword -e "SHOW DATABASES;"
# Should list "fraud_detection"
```

### Step 3: Check File Size

```powershell
Get-Item backup.sql | Select-Object Name, Length

# If > 1GB, use Method 1 (copy into container)
# If < 1GB, Method 2 should work
```

### Step 4: Import Using Best Method

**For files < 500MB:**
```powershell
type backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection
```

**For files > 500MB (recommended):**
```powershell
# Copy into container
docker cp backup.sql fraud_detection_mysql:/tmp/backup.sql

# Import from inside
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "source /tmp/backup.sql"
```

### Step 5: Monitor Progress

In another PowerShell window:
```powershell
# Watch table row counts
while ($true) {
    docker compose exec mysql mysql -u root -ppassword fraud_detection -e "
      SELECT TABLE_NAME, TABLE_ROWS
      FROM information_schema.TABLES
      WHERE TABLE_SCHEMA='fraud_detection'
      ORDER BY TABLE_ROWS DESC
      LIMIT 5;
    "
    Start-Sleep 5
}
```

### Step 6: Verify Import

```powershell
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT
  'metadata' as tbl, COUNT(*) as count FROM metadata
UNION ALL
SELECT 'uatl_raw', COUNT(*) FROM uatl_raw_statements
UNION ALL
SELECT 'summary', COUNT(*) FROM summary;
"
```

## If Nothing Works

### Nuclear Option: Import via MySQL Dump Inside Container

```powershell
# 1. Stop and remove everything
docker compose down -v

# 2. Copy backup to easily accessible location
Copy-Item backup.sql C:\temp\backup.sql

# 3. Edit docker-compose.yml, add under mysql volumes:
#   - C:\temp:/imports:ro

# 4. Start fresh
docker compose up -d
Start-Sleep 15

# 5. Import from mounted volume
docker compose exec mysql mysql -u root -ppassword fraud_detection < /imports/backup.sql
```

## Alternative: Manual Table by Table

If bulk import fails, import table by table:

```powershell
# Extract just one table from dump
Select-String -Path backup.sql -Pattern "CREATE TABLE.*metadata" -Context 0,100 | Out-File metadata.sql
Select-String -Path backup.sql -Pattern "INSERT INTO.*metadata" | Out-File -Append metadata.sql

# Import just that table
Get-Content metadata.sql | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection

# Repeat for other tables
```
