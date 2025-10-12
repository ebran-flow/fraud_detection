@echo off
REM Import Clean Backup to Docker MySQL
REM Usage: import-clean-backup.bat

setlocal enabledelayedexpansion

echo ==========================================
echo Import Clean Backup to Docker MySQL
echo ==========================================
echo.

set BACKUP_FILE=backend\backup_clean.sql

REM Check if backup file exists
if not exist "%BACKUP_FILE%" (
    echo [ERROR] Backup file not found: %BACKUP_FILE%
    pause
    exit /b 1
)

for %%A in ("%BACKUP_FILE%") do set FILE_SIZE=%%~zA
echo Backup file: %BACKUP_FILE%
echo File size: %FILE_SIZE% bytes
echo.

REM Check if MySQL container is running
docker compose ps mysql | findstr "Up" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] MySQL container is not running
    echo Please run: docker compose up -d
    pause
    exit /b 1
)

echo [OK] MySQL container is running
echo.

REM Configure MySQL
echo Configuring MySQL...
docker compose exec -T mysql mysql -u root -ppassword -e "SET GLOBAL max_allowed_packet=1073741824; SET GLOBAL net_read_timeout=3600; SET GLOBAL net_write_timeout=3600; SET GLOBAL wait_timeout=3600;" >nul 2>&1
echo [OK] MySQL configured
echo.

REM Copy file into container
echo Step 1/3: Copying file to container...
docker cp "%BACKUP_FILE%" fraud_detection_mysql:/tmp/backup.sql
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to copy file to container
    pause
    exit /b 1
)
echo [OK] File copied
echo.

REM Import
echo Step 2/3: Importing to database...
echo This may take several minutes...
echo.

docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/backup.sql"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Import failed
    pause
    exit /b 1
)

echo.
echo [OK] Import completed
echo.

REM Cleanup
echo Cleaning up...
docker compose exec mysql rm /tmp/backup.sql >nul 2>&1
echo.

REM Verify import
echo Step 3/3: Verifying import...
echo.

docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='fraud_detection' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_ROWS DESC;"

echo.
echo Quick verification:
docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) as metadata_count FROM metadata"
docker compose exec -T mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) as raw_count FROM uatl_raw_statements"

echo.
echo ==========================================
echo Import Complete!
echo ==========================================
echo.
echo Next step: Apply collation fix
echo   type backend\migrations\fix_collation.sql ^| docker compose exec -T mysql mysql -u root -ppassword fraud_detection
echo.
echo Then test with:
echo   docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT * FROM unified_statements WHERE status = 'FLAGGED' LIMIT 5;"
echo.
pause
