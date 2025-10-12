# Import Clean Backup to Docker MySQL
# Usage: .\import-clean-backup.ps1

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Import Clean Backup to Docker MySQL" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

$BackupFile = "backend\backup_clean.sql"

# Check if backup file exists
if (-not (Test-Path $BackupFile)) {
    Write-Host "[ERROR] Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

$fileSize = (Get-Item $BackupFile).Length / 1MB
Write-Host "Backup file: $BackupFile" -ForegroundColor Cyan
Write-Host "File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

# Check if MySQL container is running
$mysqlRunning = docker compose ps mysql 2>&1 | Select-String "Up"
if (-not $mysqlRunning) {
    Write-Host "[ERROR] MySQL container is not running" -ForegroundColor Red
    Write-Host "Please run: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] MySQL container is running" -ForegroundColor Green
Write-Host ""

# Configure MySQL for large import
Write-Host "Configuring MySQL..." -ForegroundColor Cyan
docker compose exec -T mysql mysql -u root -ppassword -e "
SET GLOBAL max_allowed_packet=1073741824;
SET GLOBAL net_read_timeout=3600;
SET GLOBAL net_write_timeout=3600;
SET GLOBAL wait_timeout=3600;
" 2>&1 | Out-Null

Write-Host "[OK] MySQL configured" -ForegroundColor Green
Write-Host ""

# Copy file into container
Write-Host "Step 1/3: Copying file to container..." -ForegroundColor Cyan
docker cp $BackupFile fraud_detection_mysql:/tmp/backup.sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to copy file to container" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] File copied" -ForegroundColor Green
Write-Host ""

# Import
Write-Host "Step 2/3: Importing to database..." -ForegroundColor Cyan
Write-Host "This may take several minutes..." -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/backup.sql"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Import failed" -ForegroundColor Red
    exit 1
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "[OK] Import completed in $($duration.ToString('mm\:ss'))" -ForegroundColor Green
Write-Host ""

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Cyan
docker compose exec mysql rm /tmp/backup.sql 2>&1 | Out-Null
Write-Host ""

# Verify import
Write-Host "Step 3/3: Verifying import..." -ForegroundColor Cyan
Write-Host ""

$tables = docker compose exec mysql mysql -u root -ppassword fraud_detection -e "
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA='fraud_detection' AND TABLE_TYPE='BASE TABLE'
ORDER BY TABLE_ROWS DESC;
" 2>&1

Write-Host $tables
Write-Host ""

# Quick row counts
Write-Host "Quick verification:" -ForegroundColor Cyan
$metadataCount = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) as count FROM metadata" 2>&1 | Select-String "count" -Context 0,1
$rawCount = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) as count FROM uatl_raw_statements" 2>&1 | Select-String "count" -Context 0,1

Write-Host $metadataCount
Write-Host $rawCount
Write-Host ""

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Import Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next step: Apply collation fix" -ForegroundColor Cyan
Write-Host "  Get-Content backend\migrations\fix_collation.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection" -ForegroundColor Yellow
Write-Host ""
Write-Host "Then test with:" -ForegroundColor Cyan
Write-Host "  docker compose exec mysql mysql -u root -ppassword fraud_detection -e `"SELECT * FROM unified_statements WHERE status = 'FLAGGED' LIMIT 5;`"" -ForegroundColor Yellow
Write-Host ""
