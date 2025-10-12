@echo off
REM Simple SQL Import Script for Windows (CMD)
REM Usage: import-backup.bat backup.sql

setlocal enabledelayedexpansion

if "%~1"=="" (
    echo [ERROR] Please provide backup file path
    echo Usage: import-backup.bat backup.sql
    pause
    exit /b 1
)

set BACKUP_FILE=%~1

echo ==========================================
echo SQL Backup Import to Docker MySQL
echo ==========================================
echo.

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

REM Check if Docker is running
docker ps >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop
    pause
    exit /b 1
)

REM Check if MySQL container is running
docker compose ps mysql | findstr "Up" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] MySQL container is not running
    echo Please run: docker compose up -d
    pause
    exit /b 1
)

echo [OK] Docker and MySQL container are running
echo.

REM Verify database exists
echo Verifying database exists...
docker compose exec -T mysql mysql -u root -ppassword -e "SHOW DATABASES LIKE 'fraud_detection'" | findstr "fraud_detection" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Database doesn't exist, creating...
    docker compose exec -T mysql mysql -u root -ppassword -e "CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    echo [OK] Database created
) else (
    echo [OK] Database 'fraud_detection' exists
)
echo.

REM Configure MySQL
echo Configuring MySQL for import...
docker compose exec -T mysql mysql -u root -ppassword -e "SET GLOBAL max_allowed_packet=1073741824; SET GLOBAL net_read_timeout=3600; SET GLOBAL net_write_timeout=3600;" >nul 2>&1
echo [OK] MySQL configured
echo.

REM Choose import method
echo Starting import...
echo This may take several minutes for large files...
echo.

REM Method: Copy into container (most reliable)
echo Step 1/2: Copying file to container...
docker cp "%BACKUP_FILE%" fraud_detection_mysql:/tmp/backup.sql
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to copy file to container
    pause
    exit /b 1
)
echo [OK] File copied
echo.

echo Step 2/2: Importing from container...
docker compose exec mysql bash -c "mysql -u root -ppassword fraud_detection < /tmp/backup.sql"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Import failed
    echo.
    echo Troubleshooting:
    echo 1. Check logs: docker compose logs mysql
    echo 2. Try manually: docker compose exec mysql bash
    echo    Then: mysql -u root -ppassword fraud_detection ^< /tmp/backup.sql
    pause
    exit /b 1
)

REM Cleanup
echo Cleaning up...
docker compose exec mysql rm /tmp/backup.sql >nul 2>&1

echo.
echo [OK] Import completed
echo.

REM Verify import
echo Verifying import...
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='fraud_detection' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_ROWS DESC;"
echo.

echo ==========================================
echo Import Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Apply collation fix:
echo    type backend\migrations\fix_collation.sql ^| docker compose exec -T mysql mysql -u root -ppassword fraud_detection
echo.
echo 2. Test the application:
echo    start http://localhost:8501
echo.
pause
