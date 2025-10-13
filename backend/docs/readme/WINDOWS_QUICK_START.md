# Windows Quick Start

## Prerequisites

1. Install **Docker Desktop**: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
2. Restart computer
3. Start Docker Desktop (wait for whale icon in system tray)

## Setup (Choose One)

### Option A: Batch File (Double-click)
```
setup-docker.bat
```

### Option B: PowerShell
```powershell
cd C:\path\to\airtel_fraud_detection
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup-docker.ps1
```

### Option C: Manual
```powershell
# Copy environment
Copy-Item .env.docker backend\.env

# Build and start
docker compose build
docker compose up -d

# Wait 15 seconds
Start-Sleep 15

# Check status
docker compose ps
```

## Migration from Laptop

### Export (On Laptop)
```bash
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
  --single-transaction --set-gtid-purged=OFF \
  fraud_detection > backup.sql
```

### Transfer
- Copy `backup.sql` to PC via USB or network

### Import (On PC)
```powershell
cd C:\path\to\airtel_fraud_detection

# Import
Get-Content backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection

# Fix collation
Get-Content backend\migrations\fix_collation.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection

# Verify
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='fraud_detection'"
```

## Daily Commands

```powershell
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f backend

# Enter backend
docker compose exec backend bash

# MySQL shell
docker compose exec mysql mysql -u root -ppassword fraud_detection

# Import statements (parallel)
docker compose exec backend python process_parallel.py --workers 8

# Monitor
docker stats

# Open UI
Start-Process http://localhost:8501
```

## Troubleshooting

### Docker not starting
1. Open Docker Desktop app
2. Check system tray for whale icon
3. Restart Docker Desktop if needed

### Port already in use
```powershell
# Check what's using port 8501
netstat -ano | findstr :8501

# Kill process (replace PID)
taskkill /PID <process_id> /F
```

### Slow performance
1. Docker Desktop → Settings → Resources
2. Increase Memory to 16-20GB
3. Increase CPUs to 8-10

### WSL2 issues
```powershell
# Install/update WSL2
wsl --update

# Restart
wsl --shutdown
# Restart Docker Desktop
```

## File Paths

### Windows
```
C:\Users\YourName\Developer\projects\airtel_fraud_detection\
├── setup-docker.bat
├── setup-docker.ps1
├── docker-compose.yml
└── backend\
```

### PowerShell
```powershell
cd C:\Users\YourName\Developer\projects\airtel_fraud_detection
```

### CMD
```cmd
cd C:\Users\YourName\Developer\projects\airtel_fraud_detection
```

## Access Points

- **Web UI**: http://localhost:8501
- **API Docs**: http://localhost:8501/docs
- **MySQL**: localhost:3307

## Performance

- **Memory**: 16-20GB (Docker Desktop settings)
- **CPUs**: 8-10 threads (Docker Desktop settings)
- **Workers**: 8 (parallel import)

**Expected**: 13,579 statements in ~45-60 minutes

## Full Guide

For detailed instructions: [WINDOWS_SETUP.md](WINDOWS_SETUP.md)

---

**Your system is ready!** 🚀
