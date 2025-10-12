# Fix SQL Dump Encoding Issues and Import
# Handles: line endings, quote escaping, encoding issues

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Fix and Import SQL Backup" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path $BackupFile)) {
    Write-Host "[ERROR] File not found: $BackupFile" -ForegroundColor Red
    exit 1
}

$fileSize = (Get-Item $BackupFile).Length / 1MB
Write-Host "Original file: $BackupFile" -ForegroundColor Cyan
Write-Host "File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

# Create fixed filename
$fixedFile = [System.IO.Path]::GetFileNameWithoutExtension($BackupFile) + "_fixed.sql"

Write-Host "Fixing SQL file..." -ForegroundColor Cyan
Write-Host "This may take a few minutes for large files..." -ForegroundColor Yellow
Write-Host ""

try {
    # Read entire file
    Write-Host "Reading file..." -ForegroundColor Cyan
    $content = Get-Content $BackupFile -Raw -Encoding UTF8

    Write-Host "Original size: $($content.Length) characters" -ForegroundColor Gray

    # Fix common issues
    Write-Host "Fixing line endings..." -ForegroundColor Cyan
    $content = $content -replace "`r`n", "`n"

    Write-Host "Fixing escaped quotes..." -ForegroundColor Cyan
    # Fix \'' to ''
    $content = $content -replace "\\''", "''"
    # Fix \' to '
    $content = $content -replace "\\'", "'"
    # Fix \" to "
    $content = $content -replace '\\"', '"'

    Write-Host "Removing carriage returns..." -ForegroundColor Cyan
    $content = $content -replace "`r", ""

    Write-Host "Fixed size: $($content.Length) characters" -ForegroundColor Gray

    # Save with UTF-8 encoding (no BOM)
    Write-Host "Saving fixed file: $fixedFile" -ForegroundColor Cyan
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($fixedFile, $content, $utf8NoBom)

    $fixedSize = (Get-Item $fixedFile).Length / 1MB
    Write-Host "[OK] Fixed file created: $([math]::Round($fixedSize, 2)) MB" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host "[ERROR] Failed to fix file: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try alternative method:" -ForegroundColor Yellow
    Write-Host "  docker cp `"$BackupFile`" fraud_detection_mysql:/tmp/backup.sql" -ForegroundColor Yellow
    Write-Host "  docker compose exec mysql mysql -u root -ppassword --force fraud_detection -e 'source /tmp/backup.sql'" -ForegroundColor Yellow
    exit 1
}

# Now import the fixed file
Write-Host "Importing fixed file to MySQL..." -ForegroundColor Cyan
Write-Host ""

# Copy to container
Write-Host "Step 1/2: Copying to container..." -ForegroundColor Cyan
docker cp $fixedFile fraud_detection_mysql:/tmp/backup_fixed.sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to copy file to container" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] File copied" -ForegroundColor Green
Write-Host ""

# Import
Write-Host "Step 2/2: Importing to database..." -ForegroundColor Cyan
Write-Host "This may take several minutes..." -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

# Import with progress monitoring
docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/backup_fixed.sql 2>&1"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[WARNING] Import completed with errors" -ForegroundColor Yellow
    Write-Host "Checking if data was imported..." -ForegroundColor Cyan

    $count = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) FROM metadata" 2>&1
    if ($count -match "\d+") {
        Write-Host "[OK] Some data was imported successfully" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Import failed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Try manual import:" -ForegroundColor Yellow
        Write-Host "1. docker compose exec mysql bash" -ForegroundColor Yellow
        Write-Host "2. mysql -u root -ppassword fraud_detection" -ForegroundColor Yellow
        Write-Host "3. source /tmp/backup_fixed.sql;" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[OK] Import completed successfully" -ForegroundColor Green
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "Import duration: $($duration.ToString('mm\:ss'))" -ForegroundColor Cyan
Write-Host ""

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Cyan
docker compose exec mysql rm /tmp/backup_fixed.sql 2>&1 | Out-Null

# Verify
Write-Host "Verifying import..." -ForegroundColor Cyan
Write-Host ""

$tables = docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA='fraud_detection' AND TABLE_TYPE='BASE TABLE'
ORDER BY TABLE_ROWS DESC;
" 2>&1

Write-Host "Tables imported:" -ForegroundColor Green
Write-Host $tables
Write-Host ""

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Import Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next step: Apply collation fix" -ForegroundColor Cyan
Write-Host "  Get-Content backend\migrations\fix_collation.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection" -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: Fixed file saved as: $fixedFile" -ForegroundColor Gray
Write-Host "You can delete it after verification" -ForegroundColor Gray
Write-Host ""
