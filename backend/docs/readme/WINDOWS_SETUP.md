# Windows Docker Setup Guide

Complete guide for setting up the Fraud Detection System on Windows with Docker Desktop.

## Prerequisites

### Required Software

1. **Windows 10/11 Pro, Enterprise, or Education** (64-bit)
   - Or Windows 10/11 Home with WSL2

2. **Docker Desktop for Windows**
   - Download: https://docs.docker.com/desktop/install/windows-install/
   - Minimum requirements:
     - 64-bit processor with SLAT
     - 4GB system RAM (you have 32GB ✓)
     - BIOS-level hardware virtualization enabled

3. **WSL2 (Windows Subsystem for Linux)**
   - Automatically installed with Docker Desktop
   - Or install manually: `wsl --install`

### Hardware (Your PC)

✅ CPU: i5-12400 (12 threads) - Perfect!
✅ RAM: 32GB - Excellent!
✅ GPU: Ryzen 6700XT - Great!
✅ Storage: SSD recommended

## Installation Steps

### Step 1: Install Docker Desktop

1. **Download Docker Desktop**
   ```
   https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
   ```

2. **Run installer**
   - Double-click `Docker Desktop Installer.exe`
   - Follow installation wizard
   - Enable WSL2 when prompted
   - Restart computer when installation completes

3. **Start Docker Desktop**
   - Search for "Docker Desktop" in Start menu
   - Launch the application
   - Wait for Docker engine to start (whale icon in system tray)

4. **Verify installation**
   ```powershell
   # Open PowerShell or Command Prompt
   docker --version
   docker compose version
   ```

   Expected output:
   ```
   Docker version 24.0.x, build xxxxx
   Docker Compose version v2.x.x
   ```

### Step 2: Clone/Copy Project Files

**Option A: If you have Git**
```powershell
cd C:\Users\YourUsername\Developer\projects
git clone <repository-url> airtel_fraud_detection
cd airtel_fraud_detection
```

**Option B: Copy from laptop**
```powershell
# Copy entire project folder to PC
# Destination: C:\Users\YourUsername\Developer\projects\airtel_fraud_detection
```

### Step 3: Run Setup

#### Option A: Using Batch File (Easiest)

```cmd
cd C:\Users\YourUsername\Developer\projects\airtel_fraud_detection
setup-docker.bat
```

Double-click `setup-docker.bat` in File Explorer works too!

#### Option B: Using PowerShell (Recommended)

```powershell
cd C:\Users\YourUsername\Developer\projects\airtel_fraud_detection
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup-docker.ps1
```

#### Option C: Manual Commands

```powershell
# 1. Copy environment file
Copy-Item .env.docker backend\.env

# 2. Create directories
New-Item -ItemType Directory -Force backend\uploads, backend\logs

# 3. Build and start
docker compose build
docker compose up -d

# 4. Wait for services (15 seconds)
Start-Sleep 15

# 5. Check status
docker compose ps
```

### Step 4: Verify Installation

1. **Check services are running**
   ```powershell
   docker compose ps
   ```

   Should show:
   ```
   NAME                          STATUS
   fraud_detection_backend       Up
   fraud_detection_mysql         Up (healthy)
   ```

2. **Test health endpoint**
   ```powershell
   curl http://localhost:8501/health
   ```

   Or open browser: http://localhost:8501

3. **Test MySQL connection**
   ```powershell
   docker compose exec mysql mysql -u root -ppassword -e "SELECT 1"
   ```

## Migration from Laptop

### Quick Migration Steps

1. **Export from laptop** (run on laptop)
   ```bash
   mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
     --single-transaction --set-gtid-purged=OFF \
     fraud_detection > backup.sql
   ```

2. **Transfer to PC**
   - Copy `backup.sql` to PC via USB/network
   - Place in project folder

3. **Import to PC** (run on PC)
   ```powershell
   cd C:\Users\YourUsername\Developer\projects\airtel_fraud_detection
   Get-Content backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection
   ```

4. **Apply collation fix**
   ```powershell
   Get-Content backend\migrations\fix_collation.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection
   ```

5. **Verify**
   ```powershell
   docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='fraud_detection'"
   ```

### Detailed Migration Guide

See: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) (commands adapted for Windows)

Or run interactive script:
```cmd
migrate-laptop-to-pc.bat
```

## Common Windows Issues

### Issue 1: "Docker daemon not running"

**Solution:**
1. Open Docker Desktop application
2. Wait for Docker Engine to start
3. Check system tray for whale icon
4. If stuck, restart Docker Desktop

### Issue 2: WSL2 not installed

**Solution:**
```powershell
# Run as Administrator
wsl --install
# Restart computer
```

### Issue 3: Virtualization not enabled

**Solution:**
1. Restart PC
2. Enter BIOS (usually F2, F10, or DEL during boot)
3. Enable "Intel VT-x" or "AMD-V"
4. Save and exit

### Issue 4: Port 3307 or 8501 already in use

**Check what's using the port:**
```powershell
netstat -ano | findstr :3307
netstat -ano | findstr :8501
```

**Solution A: Stop conflicting service**
```powershell
# If MySQL is running locally
Stop-Service MySQL80  # Adjust service name

# Or kill process
taskkill /PID <process_id> /F
```

**Solution B: Change ports in docker-compose.yml**
```yaml
services:
  mysql:
    ports:
      - "3308:3306"  # Change 3307 to 3308

  backend:
    ports:
      - "8502:8501"  # Change 8501 to 8502
```

### Issue 5: File permissions / Line endings

Windows uses CRLF, Linux uses LF. Docker needs LF.

**Solution:**
```powershell
# Install dos2unix (via Git Bash or WSL)
dos2unix setup-docker.sh
dos2unix backend/migrations/*.sql

# Or configure Git
git config --global core.autocrlf input
```

### Issue 6: Slow performance

**Solution:**
1. Ensure WSL2 backend is enabled (not Hyper-V)
   - Docker Desktop → Settings → General → Use WSL2
2. Increase Docker resources:
   - Docker Desktop → Settings → Resources
   - Memory: 16GB (half your RAM)
   - CPUs: 8-10 (leave 2-4 for system)
3. Store project files in WSL2 filesystem for better performance:
   ```powershell
   wsl
   cd ~
   # Work from here for best performance
   ```

## Windows-Specific Commands

### PowerShell Equivalents

| Linux/Bash | Windows PowerShell |
|------------|-------------------|
| `cat file.txt` | `Get-Content file.txt` |
| `ls -lh` | `Get-ChildItem` or `dir` |
| `cp file1 file2` | `Copy-Item file1 file2` |
| `mv file1 file2` | `Move-Item file1 file2` |
| `rm file` | `Remove-Item file` |
| `grep "text" file` | `Select-String "text" file` |
| `curl http://url` | `Invoke-WebRequest http://url` or `curl` |

### Import with PowerShell

```powershell
# Regular SQL file
Get-Content backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection

# Compressed (requires 7-Zip)
7z x -so backup.sql.gz | docker compose exec -T mysql mysql -u root -ppassword fraud_detection

# Or extract first, then import
7z e backup.sql.gz
Get-Content backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection
```

### Export with PowerShell

```powershell
# Export database
docker compose exec mysql mysqldump -u root -ppassword fraud_detection > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# Compress (requires 7-Zip)
7z a backup.sql.7z backup.sql
```

## File Paths in Windows

### Windows Paths
```
C:\Users\ebran\Developer\projects\airtel_fraud_detection\
├── docker-compose.yml
├── setup-docker.bat
├── setup-docker.ps1
├── backend\
│   ├── Dockerfile
│   ├── .env
│   └── app\
└── docs\data\
    ├── UATL\extracted\
    └── UMTN\extracted\
```

### In Docker Container (Linux paths)
```
/home/ebran/Developer/projects/airtel_fraud_detection/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   └── app/
└── docs/data/
```

### Path Conversion

| Windows | Docker Container |
|---------|-----------------|
| `C:\Users\ebran\...` | `/home/ebran/...` |
| `backend\uploads` | `backend/uploads` or `/app/uploads` |
| `docs\data\UATL` | `docs/data/UATL` |

## Daily Usage

### Start Services
```powershell
docker compose up -d
```

### Stop Services
```powershell
docker compose down
```

### View Logs
```powershell
docker compose logs -f backend
```

### Enter Backend Container
```powershell
docker compose exec backend bash
```

### Enter MySQL Shell
```powershell
docker compose exec mysql mysql -u root -ppassword fraud_detection
```

### Import Statements (Parallel)
```powershell
docker compose exec backend python process_parallel.py --workers 8
```

### Monitor Resources
```powershell
docker stats
```

### Open Web UI
```powershell
Start-Process http://localhost:8501
```

## Performance Tuning for Windows

### Docker Desktop Settings

1. **Resources** (Docker Desktop → Settings → Resources)
   - **Memory**: 16-20GB (out of your 32GB)
   - **CPUs**: 8-10 (out of 12 threads)
   - **Swap**: 4GB
   - **Disk image size**: 100GB

2. **WSL Integration** (Docker Desktop → Settings → Resources → WSL Integration)
   - Enable integration with your WSL2 distribution

3. **File Sharing** (if using bind mounts)
   - Docker Desktop → Settings → Resources → File Sharing
   - Add project directory

### Optimize WSL2

```powershell
# Create .wslconfig in C:\Users\YourUsername\
New-Item -Path $env:USERPROFILE -Name ".wslconfig" -ItemType File -Force

# Edit .wslconfig
notepad $env:USERPROFILE\.wslconfig
```

Add:
```ini
[wsl2]
memory=20GB
processors=10
swap=4GB
```

Restart WSL:
```powershell
wsl --shutdown
# Restart Docker Desktop
```

## Next Steps

1. ✅ Docker Desktop installed
2. ✅ Setup script run successfully
3. ✅ Services verified
4. 🔄 **Migrate database** (see MIGRATION_GUIDE.md)
5. 🔄 **Import statements** with parallel processing
6. 🔄 **Monitor performance**

## Useful Resources

- Docker Desktop docs: https://docs.docker.com/desktop/windows/
- WSL2 docs: https://docs.microsoft.com/en-us/windows/wsl/
- PowerShell docs: https://docs.microsoft.com/en-us/powershell/

## Support

### Check Status
```powershell
docker compose ps
docker compose logs backend
docker stats
```

### Restart Everything
```powershell
docker compose down
docker compose up -d
```

### Full Reset (if needed)
```powershell
docker compose down -v
docker system prune -a
# Re-run setup
.\setup-docker.ps1
```

---

**You're all set to run on Windows!** 🎉

The system will perform just as well on Windows with Docker Desktop + WSL2 as on native Linux. Your 13,579 statements will import in ~45-60 minutes with 8 parallel workers!
