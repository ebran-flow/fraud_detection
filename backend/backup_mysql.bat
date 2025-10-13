@echo off
REM ============================================================
REM MySQL Backup Script for Windows (Docker Compatible)
REM Cross MySQL version compatible (5.7, 8.0+)
REM Reads credentials from .env file
REM ============================================================

setlocal enabledelayedexpansion

REM Load environment variables from .env file
if not exist .env (
    echo Error: .env file not found
    pause
    exit /b 1
)

REM Parse .env file (skip comments and empty lines)
for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
    set line=%%a
    if not "!line:~0,1!"=="#" (
        if not "%%a"=="" (
            set %%a=%%b
        )
    )
)

REM Configuration (with defaults from .env)
if not defined DOCKER_CONTAINER set DOCKER_CONTAINER=mysql-fraud-detection
if not defined DB_HOST set DB_HOST=localhost
if not defined DB_PORT set DB_PORT=3307
if not defined DB_USER set DB_USER=root
if not defined DB_PASSWORD set DB_PASSWORD=root
if not defined DB_NAME set DB_NAME=fraud_detection
set BACKUP_DIR=backups

REM Create timestamp (YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set BACKUP_FILE=%BACKUP_DIR%\%DB_NAME%_backup_%TIMESTAMP%.sql

echo ============================================================
echo MySQL Backup Script - Windows Docker Compatible
echo ============================================================
echo.
echo Database: %DB_NAME%
echo Backup File: %BACKUP_FILE%
echo.

REM Create backup directory if it doesn't exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running
    pause
    exit /b 1
)

REM Check if container exists
docker ps -a --format "{{.Names}}" | findstr /x "%DOCKER_CONTAINER%" >nul 2>&1
if errorlevel 1 (
    echo Warning: Container '%DOCKER_CONTAINER%' not found
    echo Attempting direct connection to MySQL...
    set USE_DOCKER=false
) else (
    set USE_DOCKER=true
)

REM Perform backup
echo Starting backup...
echo.

if "!USE_DOCKER!"=="true" (
    REM Backup via Docker exec
    docker exec %DOCKER_CONTAINER% mysqldump ^
        --host=%DB_HOST% ^
        --port=3306 ^
        --user=%DB_USER% ^
        --password=%DB_PASSWORD% ^
        --single-transaction ^
        --routines ^
        --triggers ^
        --events ^
        --default-character-set=utf8mb4 ^
        --set-charset ^
        --no-tablespaces ^
        --column-statistics=0 ^
        --skip-comments ^
        --compact ^
        --skip-lock-tables ^
        %DB_NAME% > "%BACKUP_FILE%"
) else (
    REM Direct connection (requires mysqldump in PATH)
    mysqldump ^
        --host=%DB_HOST% ^
        --port=%DB_PORT% ^
        --user=%DB_USER% ^
        --password=%DB_PASSWORD% ^
        --single-transaction ^
        --routines ^
        --triggers ^
        --events ^
        --default-character-set=utf8mb4 ^
        --set-charset ^
        --no-tablespaces ^
        --column-statistics=0 ^
        --skip-comments ^
        --compact ^
        --skip-lock-tables ^
        %DB_NAME% > "%BACKUP_FILE%"
)

REM Check if backup was successful
if exist "%BACKUP_FILE%" (
    echo.
    echo ✓ Backup completed successfully!
    echo   File: %BACKUP_FILE%

    REM Get file size
    for %%A in ("%BACKUP_FILE%") do set BACKUP_SIZE=%%~zA
    set /a BACKUP_SIZE_MB=!BACKUP_SIZE! / 1048576
    echo   Size: !BACKUP_SIZE_MB! MB

    REM List recent backups
    echo.
    echo Recent backups:
    dir /o-d "%BACKUP_DIR%\*.sql" | findstr "^[0-9]"

    echo.
    echo ============================================================
    echo Backup completed successfully!
    echo ============================================================
) else (
    echo.
    echo ✗ Backup failed!
    pause
    exit /b 1
)

pause
