@echo off
REM Docker Setup Script for Windows
REM Optimized for i5-12400 + 32GB RAM

echo ==========================================
echo Fraud Detection Docker Setup (Windows)
echo System: i5-12400 + Ryzen 6700XT + 32GB RAM
echo ==========================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker not found. Please install Docker Desktop:
    echo   https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker compose version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker Compose not found. Please install Docker Desktop with Compose:
    echo   https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

echo [OK] Docker and Docker Compose found
echo.

REM Copy environment file
echo Setting up environment configuration...
if not exist backend\.env (
    copy .env.docker backend\.env >nul
    echo [OK] Created backend\.env from .env.docker
) else (
    echo [WARNING] backend\.env already exists, skipping
)
echo.

REM Create necessary directories
echo Creating directories...
if not exist backend\uploads mkdir backend\uploads
if not exist backend\logs mkdir backend\logs
if not exist docs\data\UATL\extracted mkdir docs\data\UATL\extracted
if not exist docs\data\UMTN\extracted mkdir docs\data\UMTN\extracted
echo [OK] Directories created
echo.

REM Check if init.sql exists
if not exist backend\init.sql (
    echo [WARNING] backend\init.sql not found
    echo   The database will start without initial schema
    echo   You may need to run migrations manually
    echo.
)

REM Stop any existing containers
echo Stopping existing containers...
docker compose down >nul 2>nul
echo.

REM Build images
echo Building Docker images...
docker compose build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to build Docker images
    pause
    exit /b 1
)
echo [OK] Images built successfully
echo.

REM Start services
echo Starting services...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)
echo.

REM Wait for MySQL to be ready
echo Waiting for MySQL to be ready...
timeout /t 15 /nobreak >nul
echo.

REM Check service health
echo Checking service health...
echo.

docker compose ps | findstr "mysql" | findstr "Up" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] MySQL is running
) else (
    echo [ERROR] MySQL failed to start
    echo.
    echo Logs:
    docker compose logs mysql
    pause
    exit /b 1
)

docker compose ps | findstr "backend" | findstr "Up" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend is running
) else (
    echo [ERROR] Backend failed to start
    echo.
    echo Logs:
    docker compose logs backend
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Services:
echo   - MySQL:   http://localhost:3307
echo   - Backend: http://localhost:8501
echo   - UI:      http://localhost:8501
echo.
echo Default credentials:
echo   - MySQL root password: password
echo   - MySQL user: fraud_user / fraud_pass
echo.
echo Useful commands:
echo   - View logs:        docker compose logs -f
echo   - Stop services:    docker compose down
echo   - Restart services: docker compose restart
echo   - Enter backend:    docker compose exec backend bash
echo   - Enter MySQL:      docker compose exec mysql mysql -u root -ppassword fraud_detection
echo.
echo To import statements in parallel:
echo   1. Place files in docs\data\UATL\extracted\ or docs\data\UMTN\extracted\
echo   2. Use the parallel import API endpoint or run:
echo      docker compose exec backend python process_parallel.py --workers 8
echo.
echo Open browser: http://localhost:8501
echo.
pause
