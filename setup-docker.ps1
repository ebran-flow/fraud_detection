# PowerShell Docker Setup Script
# Optimized for i5-12400 + 32GB RAM

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Fraud Detection Docker Setup (PowerShell)" -ForegroundColor Green
Write-Host "System: i5-12400 + Ryzen 6700XT + 32GB RAM" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if Docker is installed
try {
    $null = docker --version
    Write-Host "[OK] Docker found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker not found. Please install Docker Desktop:" -ForegroundColor Red
    Write-Host "  https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Docker Compose is available
try {
    $null = docker compose version
    Write-Host "[OK] Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker Compose not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Copy environment file
Write-Host "Setting up environment configuration..." -ForegroundColor Cyan
if (-not (Test-Path "backend\.env")) {
    Copy-Item ".env.docker" "backend\.env"
    Write-Host "[OK] Created backend\.env from .env.docker" -ForegroundColor Green
} else {
    Write-Host "[WARNING] backend\.env already exists, skipping" -ForegroundColor Yellow
}
Write-Host ""

# Create necessary directories
Write-Host "Creating directories..." -ForegroundColor Cyan
$dirs = @(
    "backend\uploads",
    "backend\logs",
    "docs\data\UATL\extracted",
    "docs\data\UMTN\extracted"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "[OK] Directories created" -ForegroundColor Green
Write-Host ""

# Check if init.sql exists
if (-not (Test-Path "backend\init.sql")) {
    Write-Host "[WARNING] backend\init.sql not found" -ForegroundColor Yellow
    Write-Host "  The database will start without initial schema" -ForegroundColor Yellow
    Write-Host ""
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Cyan
docker compose down 2>$null
Write-Host ""

# Build images
Write-Host "Building Docker images..." -ForegroundColor Cyan
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to build Docker images" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Images built successfully" -ForegroundColor Green
Write-Host ""

# Start services
Write-Host "Starting services..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start services" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Wait for MySQL to be ready
Write-Host "Waiting for MySQL to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 15
Write-Host ""

# Check service health
Write-Host "Checking service health..." -ForegroundColor Cyan
Write-Host ""

$mysqlStatus = docker compose ps mysql | Select-String "Up"
if ($mysqlStatus) {
    Write-Host "[OK] MySQL is running" -ForegroundColor Green
} else {
    Write-Host "[ERROR] MySQL failed to start" -ForegroundColor Red
    Write-Host ""
    Write-Host "Logs:" -ForegroundColor Yellow
    docker compose logs mysql
    Read-Host "Press Enter to exit"
    exit 1
}

$backendStatus = docker compose ps backend | Select-String "Up"
if ($backendStatus) {
    Write-Host "[OK] Backend is running" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Backend failed to start" -ForegroundColor Red
    Write-Host ""
    Write-Host "Logs:" -ForegroundColor Yellow
    docker compose logs backend
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  - MySQL:   http://localhost:3307"
Write-Host "  - Backend: http://localhost:8501"
Write-Host "  - UI:      http://localhost:8501"
Write-Host ""
Write-Host "Default credentials:" -ForegroundColor Cyan
Write-Host "  - MySQL root password: password"
Write-Host "  - MySQL user: fraud_user / fraud_pass"
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  - View logs:        docker compose logs -f"
Write-Host "  - Stop services:    docker compose down"
Write-Host "  - Restart services: docker compose restart"
Write-Host "  - Enter backend:    docker compose exec backend bash"
Write-Host "  - Enter MySQL:      docker compose exec mysql mysql -u root -ppassword fraud_detection"
Write-Host ""
Write-Host "To import statements in parallel:" -ForegroundColor Cyan
Write-Host "  1. Place files in docs\data\UATL\extracted\ or docs\data\UMTN\extracted\"
Write-Host "  2. Use the parallel import API endpoint or run:"
Write-Host "     docker compose exec backend python process_parallel.py --workers 8"
Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8501"
Write-Host ""
Read-Host "Press Enter to exit"
