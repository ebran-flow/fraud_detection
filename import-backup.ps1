# Simple SQL Import Script for Windows
# Usage: .\import-backup.ps1 backup.sql

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "SQL Backup Import to Docker MySQL" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if backup file exists
if (-not (Test-Path $BackupFile)) {
    Write-Host "[ERROR] Backup file not found: $BackupFile" -ForegroundColor Red
    Write-Host "Please provide the correct path to your .sql file" -ForegroundColor Yellow
    exit 1
}

$fileSize = (Get-Item $BackupFile).Length / 1MB
Write-Host "Backup file: $BackupFile" -ForegroundColor Cyan
Write-Host "File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    $null = docker ps 2>&1
} catch {
    Write-Host "[ERROR] Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Check if MySQL container is running
$mysqlRunning = docker compose ps mysql 2>&1 | Select-String "Up"
if (-not $mysqlRunning) {
    Write-Host "[ERROR] MySQL container is not running" -ForegroundColor Red
    Write-Host "Please run: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Docker and MySQL container are running" -ForegroundColor Green
Write-Host ""

# Method selection based on file size
if ($fileSize -lt 500) {
    $method = "stream"
    Write-Host "Using streaming method (file < 500MB)" -ForegroundColor Cyan
} else {
    $method = "copy"
    Write-Host "Using copy method (file >= 500MB, more reliable)" -ForegroundColor Cyan
}
Write-Host ""

# Verify database exists
Write-Host "Verifying database exists..." -ForegroundColor Cyan
try {
    $dbCheck = docker compose exec -T mysql mysql -u root -ppassword -e "SHOW DATABASES LIKE 'fraud_detection'" 2>&1
    if ($dbCheck -match "fraud_detection") {
        Write-Host "[OK] Database 'fraud_detection' exists" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Database doesn't exist, creating..." -ForegroundColor Yellow
        docker compose exec -T mysql mysql -u root -ppassword -e "CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        Write-Host "[OK] Database created" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] Cannot connect to MySQL" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host ""

# Increase MySQL timeouts
Write-Host "Configuring MySQL for import..." -ForegroundColor Cyan
docker compose exec -T mysql mysql -u root -ppassword -e "
SET GLOBAL max_allowed_packet=1073741824;
SET GLOBAL net_read_timeout=3600;
SET GLOBAL net_write_timeout=3600;
SET GLOBAL wait_timeout=3600;
" 2>&1 | Out-Null
Write-Host "[OK] MySQL configured" -ForegroundColor Green
Write-Host ""

# Import based on method
Write-Host "Starting import..." -ForegroundColor Cyan
Write-Host "This may take several minutes for large files..." -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

if ($method -eq "copy") {
    # Copy file into container
    Write-Host "Step 1/2: Copying file to container..." -ForegroundColor Cyan
    docker cp $BackupFile fraud_detection_mysql:/tmp/backup.sql
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to copy file to container" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] File copied" -ForegroundColor Green
    Write-Host ""

    # Import from inside container
    Write-Host "Step 2/2: Importing from container..." -ForegroundColor Cyan
    docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/backup.sql"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Import failed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
        Write-Host "1. Check MySQL logs: docker compose logs mysql" -ForegroundColor Yellow
        Write-Host "2. Try manually: docker compose exec mysql bash" -ForegroundColor Yellow
        Write-Host "   Then: mysql -u root -ppassword fraud_detection < /tmp/backup.sql" -ForegroundColor Yellow
        exit 1
    }

    # Cleanup
    Write-Host "Cleaning up..." -ForegroundColor Cyan
    docker compose exec mysql rm /tmp/backup.sql 2>&1 | Out-Null

} else {
    # Stream method
    Write-Host "Streaming file to MySQL..." -ForegroundColor Cyan

    # Use type command (more reliable than Get-Content for large files)
    cmd /c "type `"$BackupFile`" | docker exec -i fraud_detection_mysql mysql -u root -ppassword fraud_detection"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Import failed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Try the copy method instead:" -ForegroundColor Yellow
        Write-Host "  docker cp $BackupFile fraud_detection_mysql:/tmp/backup.sql" -ForegroundColor Yellow
        Write-Host "  docker compose exec mysql mysql -u root -ppassword fraud_detection < /tmp/backup.sql" -ForegroundColor Yellow
        exit 1
    }
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "[OK] Import completed in $($duration.ToString('mm\:ss'))" -ForegroundColor Green
Write-Host ""

# Verify import
Write-Host "Verifying import..." -ForegroundColor Cyan
$tables = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "
SELECT
  TABLE_NAME,
  TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA='fraud_detection'
  AND TABLE_TYPE='BASE TABLE'
ORDER BY TABLE_ROWS DESC;
" 2>&1

Write-Host ""
Write-Host "Tables imported:" -ForegroundColor Green
Write-Host $tables
Write-Host ""

# Check for common tables
$metadataCount = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) as count FROM metadata" 2>&1 | Select-String "count" -Context 0,1
$rawCount = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) as count FROM uatl_raw_statements" 2>&1 | Select-String "count" -Context 0,1

Write-Host "Quick verification:" -ForegroundColor Cyan
Write-Host $metadataCount
Write-Host $rawCount
Write-Host ""

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Import Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Apply collation fix:" -ForegroundColor White
Write-Host "   Get-Content backend\migrations\fix_collation.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Test the application:" -ForegroundColor White
Write-Host "   Start-Process http://localhost:8501" -ForegroundColor Yellow
Write-Host ""
