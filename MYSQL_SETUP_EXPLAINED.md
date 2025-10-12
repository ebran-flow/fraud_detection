# MySQL Setup - Fully Automated

## TL;DR - Yes, MySQL is Handled Automatically! ✅

When you run `setup-docker.bat` or `setup-docker.ps1`, Docker automatically:

1. ✅ Downloads MySQL 8.0
2. ✅ Creates MySQL container
3. ✅ Creates `fraud_detection` database
4. ✅ Creates all tables from `backend/init.sql`
5. ✅ Sets up users and permissions
6. ✅ Configures for optimal performance

**You don't need to install MySQL separately on Windows!**

## What Happens During Setup

### Step 1: Docker Downloads MySQL Image

```
Pulling mysql:8.0... (~500MB, first time only)
✓ Image downloaded
```

### Step 2: Docker Creates MySQL Container

```yaml
# From docker-compose.yml
mysql:
  image: mysql:8.0
  environment:
    MYSQL_ROOT_PASSWORD: password
    MYSQL_DATABASE: fraud_detection  # ← Database created automatically
    MYSQL_USER: fraud_user
    MYSQL_PASSWORD: fraud_pass
```

### Step 3: Docker Runs init.sql Automatically

```yaml
volumes:
  - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```

**Magic!** Any `.sql` file in `/docker-entrypoint-initdb.d/` runs automatically on first startup.

### Step 4: Tables Are Created

`backend/init.sql` contains complete schema:
- ✅ `metadata` table
- ✅ `uatl_raw_statements` table
- ✅ `umtn_raw_statements` table
- ✅ `uatl_processed_statements` table
- ✅ `umtn_processed_statements` table
- ✅ `summary` table
- ✅ `unified_statements` view
- ✅ All indexes and constraints

### Step 5: MySQL is Ready!

```
MySQL container is healthy ✓
Database: fraud_detection
Tables: All created
Ready for import!
```

## Two Scenarios

### Scenario A: Migrating from Laptop (Most Common)

**You have existing data to migrate:**

```powershell
# 1. Setup Docker (creates empty database with tables)
.\setup-docker.ps1

# 2. Import your backup (overwrites empty tables with your data)
Get-Content backup.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection

# 3. Apply collation fix
Get-Content backend\migrations\fix_collation.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection
```

**Result:**
- ✅ MySQL running in Docker
- ✅ All tables exist
- ✅ All your data imported
- ✅ Views working correctly

### Scenario B: Fresh Installation (No Existing Data)

**Starting from scratch:**

```powershell
# 1. Setup Docker (creates database with empty tables)
.\setup-docker.ps1

# That's it! Tables are ready for use.
```

**Result:**
- ✅ MySQL running in Docker
- ✅ All tables exist (empty)
- ✅ Ready to start importing statements

## MySQL Configuration (Optimized)

```yaml
command:
  --default-authentication-plugin=mysql_native_password
  --max_allowed_packet=256M              # Large packets for imports
  --innodb_buffer_pool_size=2G           # 2GB cache (adjust if needed)
```

**Performance settings for your 32GB RAM PC:**
- Buffer pool: 2GB (can increase to 4GB if needed)
- Max packet: 256MB (handles large imports)
- Native password: Compatible with all clients

## Connection Details

**From your PC (Windows):**
```
Host: localhost (or 127.0.0.1)
Port: 3307
User: root
Password: password

OR

User: fraud_user
Password: fraud_pass
Database: fraud_detection
```

**From inside Docker containers:**
```
Host: mysql
Port: 3306
User: fraud_user
Password: fraud_pass
Database: fraud_detection
```

## Accessing MySQL

### From Windows (MySQL Client)

If you have MySQL client installed on Windows:
```cmd
mysql -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection
```

### Via Docker (Recommended)

```powershell
# MySQL shell
docker compose exec mysql mysql -u root -ppassword fraud_detection

# Or bash first, then mysql
docker compose exec mysql bash
mysql -u root -ppassword fraud_detection
```

### From Backend Container

```powershell
docker compose exec backend bash
# Inside container:
python -c "from app.services.db import SessionLocal; db = SessionLocal(); print('Connected!')"
```

## Data Persistence

**Your data is safe!** Even if you stop/restart Docker:

```yaml
volumes:
  mysql_data:/var/lib/mysql  # Persistent volume
```

**Data survives:**
- ✅ `docker compose down` (stops containers)
- ✅ `docker compose restart`
- ✅ Computer restart
- ✅ Docker Desktop restart

**Data is lost only if:**
- ❌ `docker compose down -v` (removes volumes)
- ❌ `docker volume rm mysql_data`

## Common Questions

### Q: Do I need to install MySQL on Windows?

**A: NO!** Docker provides MySQL. Your Windows PC doesn't need MySQL installed.

### Q: What if I already have MySQL on Windows?

**A: No conflict!** Docker MySQL runs on port **3307**, Windows MySQL typically uses **3306**. They don't interfere.

### Q: Can I use MySQL Workbench?

**A: Yes!** Connect to:
- Host: `localhost`
- Port: `3307`
- User: `root`
- Password: `password`

### Q: Where is the database file stored?

**A: Docker volume** (managed by Docker)
```powershell
# View volume location
docker volume inspect airtel_fraud_detection_mysql_data
```

### Q: How do I backup?

**A: Use mysqldump via Docker:**
```powershell
docker compose exec mysql mysqldump -u root -ppassword fraud_detection > backup_$(Get-Date -Format "yyyyMMdd").sql
```

### Q: How do I reset everything?

**A: Remove volume and restart:**
```powershell
docker compose down -v
docker compose up -d
# Fresh database with empty tables
```

### Q: Can I increase buffer pool size?

**A: Yes!** Edit `docker-compose.yml`:
```yaml
command: --innodb_buffer_pool_size=4G  # Change from 2G to 4G
```
Then restart:
```powershell
docker compose restart mysql
```

## Verify MySQL Setup

### Check MySQL is Running

```powershell
docker compose ps mysql
```

Expected:
```
NAME                    STATUS
fraud_detection_mysql   Up (healthy)
```

### Check Database Exists

```powershell
docker compose exec mysql mysql -u root -ppassword -e "SHOW DATABASES;"
```

Expected:
```
+--------------------+
| Database           |
+--------------------+
| fraud_detection    |
| information_schema |
| mysql              |
| performance_schema |
| sys                |
+--------------------+
```

### Check Tables Exist

```powershell
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SHOW TABLES;"
```

Expected:
```
+----------------------------------+
| Tables_in_fraud_detection        |
+----------------------------------+
| metadata                         |
| summary                          |
| uatl_processed_statements        |
| uatl_raw_statements              |
| umtn_processed_statements        |
| umtn_raw_statements              |
| unified_statements               |
+----------------------------------+
```

### Check Table Structure

```powershell
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "DESCRIBE metadata;"
```

### Test Connection from Backend

```powershell
docker compose exec backend python -c "
from app.services.db import SessionLocal
db = SessionLocal()
result = db.execute('SELECT COUNT(*) FROM metadata').scalar()
print(f'Connected! Metadata count: {result}')
db.close()
"
```

## Troubleshooting

### Issue: MySQL container won't start

```powershell
# Check logs
docker compose logs mysql

# Common causes:
# 1. Port 3307 in use
netstat -ano | findstr :3307

# 2. Corrupted volume (reset)
docker compose down -v
docker compose up -d
```

### Issue: "Access denied" errors

```powershell
# Check user/password
docker compose exec mysql mysql -u root -ppassword

# If that works, check app user
docker compose exec mysql mysql -u fraud_user -pfraud_pass fraud_detection
```

### Issue: init.sql didn't run

```powershell
# Check if file exists
ls backend\init.sql

# Check if volume is mounted
docker compose exec mysql ls -l /docker-entrypoint-initdb.d/

# Force re-initialization (removes data!)
docker compose down -v
docker compose up -d
```

### Issue: Tables don't exist

```powershell
# Run init.sql manually
Get-Content backend\init.sql | docker compose exec -T mysql mysql -u root -ppassword fraud_detection

# Or copy and execute
docker compose cp backend\init.sql mysql:/tmp/
docker compose exec mysql mysql -u root -ppassword fraud_detection < /tmp/init.sql
```

## Advanced: Custom MySQL Configuration

Create `mysql.cnf`:

```ini
[mysqld]
# Performance
innodb_buffer_pool_size=4G
max_allowed_packet=512M
innodb_log_file_size=512M

# Character sets
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci

# Connections
max_connections=200
```

Update `docker-compose.yml`:

```yaml
mysql:
  volumes:
    - mysql_data:/var/lib/mysql
    - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    - ./mysql.cnf:/etc/mysql/conf.d/custom.cnf:ro  # Add this
```

Restart MySQL:
```powershell
docker compose restart mysql
```

## Summary

✅ **MySQL is 100% automated**
- No manual installation needed
- No manual database creation
- No manual table creation
- No manual configuration

✅ **Everything handled by Docker**
- Download MySQL image
- Create container
- Initialize database
- Create all tables
- Configure settings

✅ **Two workflows supported**
- Migration: Import existing data
- Fresh start: Use empty tables

✅ **Data is persistent**
- Survives restarts
- Backed by Docker volume
- Easy to backup/restore

**Just run the setup script and you're done!** 🎉
