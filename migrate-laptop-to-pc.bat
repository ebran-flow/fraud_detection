@echo off
REM Migration Script: Laptop to PC (Windows)
REM Step-by-step guide to migrate fraud detection database

setlocal enabledelayedexpansion

echo ==========================================
echo Fraud Detection Database Migration
echo From: Laptop to PC (Windows)
echo ==========================================
echo.

set BACKUP_DATE=%date:~-4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DATE=%BACKUP_DATE: =0%
set BACKUP_FILE=fraud_detection_backup_%BACKUP_DATE%.sql
set BACKUP_COMPRESSED=fraud_detection_backup_%BACKUP_DATE%.sql.gz

echo Step 1: Export Database from Laptop
echo ======================================
echo.
echo Run these commands ON YOUR LAPTOP:
echo.
echo Option 1: Regular dump (smaller databases ^< 1GB)
echo mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword ^
echo   --single-transaction ^
echo   --set-gtid-purged=OFF ^
echo   fraud_detection ^> %BACKUP_FILE%
echo.
echo Option 2: Compressed dump (recommended - requires gzip)
echo mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword ^
echo   --single-transaction ^
echo   --set-gtid-purged=OFF ^
echo   fraud_detection ^| gzip ^> %BACKUP_COMPRESSED%
echo.
pause

echo.
echo Step 2: Transfer Backup File to PC
echo ======================================
echo.
echo Choose your transfer method:
echo.
echo Option A: USB Drive
echo   1. Copy file to USB drive
echo   2. Plug USB into PC
echo   3. Copy to project folder
echo.
echo Option B: Network Transfer
echo   Use file sharing or copy over network
echo.
echo Option C: Cloud Storage
echo   Upload from laptop, download on PC
echo.
pause

echo.
echo Step 3: Setup Docker on PC
echo ======================================
echo.
echo Run: setup-docker.bat or setup-docker.ps1
echo.
echo Press Enter after Docker setup is complete...
pause

echo.
echo Step 4: Import Database to PC
echo ======================================
echo.
echo Choose based on your backup format:
echo.
echo Option 1: Regular .sql file
echo docker compose exec -T mysql mysql -u root -ppassword fraud_detection ^< %BACKUP_FILE%
echo.
echo Option 2: Compressed .sql.gz file (requires gzip/7-zip)
echo 7z x -so %BACKUP_COMPRESSED% ^| docker compose exec -T mysql mysql -u root -ppassword fraud_detection
echo.
echo Press Enter after import is complete...
pause

echo.
echo Step 5: Apply Collation Fix
echo ======================================
echo.
echo docker compose exec -T mysql mysql -u root -ppassword fraud_detection ^< backend\migrations\fix_collation.sql
echo.
pause

echo.
echo Step 6: Verify Migration
echo ======================================
echo.
echo docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT 'metadata' as tbl, COUNT(*) FROM metadata UNION SELECT 'raw', COUNT(*) FROM uatl_raw_statements UNION SELECT 'processed', COUNT(*) FROM uatl_processed_statements UNION SELECT 'summary', COUNT(*) FROM summary;"
echo.
pause

echo.
echo Step 7: Test Application
echo ======================================
echo.
echo Open browser: http://localhost:8501
echo Test the UI and verify data
echo.
pause

echo.
echo ==========================================
echo Migration Complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Start importing: docker compose exec backend python process_parallel.py --workers 8
echo   2. Monitor: docker compose logs -f backend
echo.
pause
