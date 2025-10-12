# Fix SQL Syntax Issues in Dump
# Handles: broken INSERT statements, line ending issues, extended inserts

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,

    [switch]$FixExtendedInserts
)

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Fix SQL Syntax Issues" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path $BackupFile)) {
    Write-Host "[ERROR] File not found: $BackupFile" -ForegroundColor Red
    exit 1
}

$fileSize = (Get-Item $BackupFile).Length / 1MB
Write-Host "Input file: $BackupFile" -ForegroundColor Cyan
Write-Host "File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

if ($fileSize -gt 500) {
    Write-Host "[WARNING] Large file detected ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Yellow
    Write-Host "This may take 10-15 minutes to process..." -ForegroundColor Yellow
    Write-Host ""
}

$fixedFile = [System.IO.Path]::GetFileNameWithoutExtension($BackupFile) + "_syntax_fixed.sql"

Write-Host "Processing SQL file..." -ForegroundColor Cyan
Write-Host ""

try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    # For large files, process line by line
    if ($fileSize -gt 100) {
        Write-Host "Using line-by-line processing (large file)..." -ForegroundColor Cyan

        $reader = [System.IO.StreamReader]::new($BackupFile, [System.Text.Encoding]::UTF8)
        $writer = [System.IO.StreamWriter]::new($fixedFile, $false, [System.Text.UTF8Encoding]::new($false))

        $lineCount = 0
        $fixCount = 0
        $inInsert = $false
        $insertBuffer = ""

        while ($null -ne ($line = $reader.ReadLine())) {
            $lineCount++

            if ($lineCount % 10000 -eq 0) {
                Write-Host "  Processed $lineCount lines..." -ForegroundColor Gray
            }

            # Fix line endings
            $line = $line.TrimEnd("`r")

            # Fix quote escaping
            $line = $line -replace "\\''", "''"
            $line = $line -replace "\\'", "''"

            # Check if this is an INSERT statement
            if ($line -match "^INSERT INTO") {
                if ($inInsert -and $insertBuffer) {
                    # Write previous INSERT
                    $writer.WriteLine($insertBuffer)
                    $insertBuffer = ""
                }
                $inInsert = $true
                $insertBuffer = $line
            }
            elseif ($inInsert) {
                # Continue building INSERT statement
                if ($line.TrimEnd() -match ";$") {
                    # End of INSERT
                    $insertBuffer += " " + $line
                    $writer.WriteLine($insertBuffer)
                    $insertBuffer = ""
                    $inInsert = $false
                }
                else {
                    # Middle of INSERT
                    $insertBuffer += " " + $line
                }
            }
            else {
                # Regular line (not INSERT)
                $writer.WriteLine($line)
            }
        }

        # Write any remaining INSERT
        if ($insertBuffer) {
            $writer.WriteLine($insertBuffer)
        }

        $reader.Close()
        $writer.Close()

    } else {
        # Small file - load into memory
        Write-Host "Loading entire file into memory..." -ForegroundColor Cyan

        $content = Get-Content $BackupFile -Raw -Encoding UTF8

        Write-Host "Fixing syntax issues..." -ForegroundColor Cyan

        # Fix line endings
        $content = $content -replace "`r`n", "`n"
        $content = $content -replace "`r", "`n"

        # Fix quote escaping
        $content = $content -replace "\\''", "''"
        $content = $content -replace "\\'", "''"
        $content = $content -replace '\\"', '"'

        # Fix broken INSERT statements (common pattern)
        # Look for lines that start with quotes but no INSERT
        $content = $content -replace "(?m)^'([^']+)'(?!.*INSERT)", "-- SKIPPED BROKEN LINE: '$1'"

        Write-Host "Saving fixed file..." -ForegroundColor Cyan
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($fixedFile, $content, $utf8NoBom)
    }

    $sw.Stop()

    $fixedSize = (Get-Item $fixedFile).Length / 1MB
    Write-Host ""
    Write-Host "[OK] Fixed file created: $fixedFile" -ForegroundColor Green
    Write-Host "Fixed file size: $([math]::Round($fixedSize, 2)) MB" -ForegroundColor Cyan
    Write-Host "Processing time: $($sw.Elapsed.ToString('mm\:ss'))" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "[ERROR] Failed to process file: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Import
Write-Host "Import the fixed file?" -ForegroundColor Yellow
Write-Host "Press Y to import now, or N to skip: " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -eq 'Y' -or $response -eq 'y') {
    Write-Host ""
    Write-Host "Importing to MySQL..." -ForegroundColor Cyan

    # Copy to container
    docker cp $fixedFile fraud_detection_mysql:/tmp/backup_fixed.sql

    # Import with error logging
    docker compose exec mysql bash -c "mysql -u root -ppassword --force fraud_detection < /tmp/backup_fixed.sql 2>&1 | tee /tmp/import.log"

    # Show summary
    Write-Host ""
    Write-Host "Checking import results..." -ForegroundColor Cyan
    docker compose exec mysql mysql -u root -ppassword fraud_detection -e "
    SELECT TABLE_NAME, TABLE_ROWS
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA='fraud_detection' AND TABLE_TYPE='BASE TABLE'
    ORDER BY TABLE_ROWS DESC;
    "

    # Cleanup
    docker compose exec mysql rm /tmp/backup_fixed.sql 2>&1 | Out-Null

    Write-Host ""
    Write-Host "[OK] Import complete" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Import skipped. To import manually:" -ForegroundColor Cyan
    Write-Host "  docker cp $fixedFile fraud_detection_mysql:/tmp/backup.sql" -ForegroundColor Yellow
    Write-Host "  docker compose exec mysql mysql -u root -ppassword --force fraud_detection -e 'source /tmp/backup.sql'" -ForegroundColor Yellow
}

Write-Host ""
