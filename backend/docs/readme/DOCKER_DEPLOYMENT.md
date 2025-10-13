# Docker Deployment Guide

Complete guide for deploying the Airtel Fraud Detection System using Docker with optimized parallel processing.

## System Requirements

**Recommended Specifications:**
- CPU: Intel i5-12400 or equivalent (6+ cores, 12+ threads)
- GPU: AMD Ryzen 6700XT or equivalent (optional, for future ML features)
- RAM: 32GB
- Storage: 50GB+ SSD
- OS: Ubuntu 22.04 LTS / Windows 11 with WSL2 / macOS

**Software Requirements:**
- Docker 20.10+
- Docker Compose 2.0+

## Quick Start

### 1. Clone and Setup

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection
./setup-docker.sh
```

This script will:
- Check Docker installation
- Create necessary directories
- Copy environment configuration
- Build Docker images
- Start all services
- Verify health checks

### 2. Access Services

- **Web UI**: http://localhost:8501
- **API Documentation**: http://localhost:8501/docs
- **MySQL**: localhost:3307

**Default Credentials:**
- MySQL root: `password`
- MySQL user: `fraud_user` / `fraud_pass`

## Architecture

### Docker Services

```yaml
services:
  mysql:
    - Image: mysql:8.0
    - Port: 3307:3306
    - Volume: mysql_data (persistent)
    - Configuration:
      - max_allowed_packet: 256M
      - innodb_buffer_pool_size: 2G

  backend:
    - Python 3.11 + FastAPI + Uvicorn
    - Port: 8501:8501
    - Workers: 4 (Uvicorn)
    - Parallel Import Workers: 8
    - Volumes:
      - ./backend (code)
      - upload_data (persistent)
      - logs (persistent)
```

### Performance Tuning for i5-12400

**CPU Allocation (12 threads total):**
- Uvicorn workers: 4 threads (FastAPI web server)
- Parallel import workers: 8 threads (statement parsing)
- System/MySQL: 4+ threads (reserved)

**Memory Allocation:**
- MySQL InnoDB buffer pool: 2GB
- Python processes: ~10GB (8 workers × 1.25GB)
- System/Cache: Remaining RAM

**Database Connection Pool:**
- Pool size: 20 connections
- Max overflow: 10 connections

## Parallel Import

### Using the API

**Import Specific Files:**

```bash
curl -X POST "http://localhost:8501/api/v1/parallel-import" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {
        "file_path": "/app/uploads/statement1.pdf",
        "run_id": "abc123",
        "provider_code": "UATL"
      },
      {
        "file_path": "/app/uploads/statement2.pdf",
        "run_id": "def456",
        "provider_code": "UATL"
      }
    ],
    "num_workers": 8
  }'
```

**Import Entire Directory:**

```bash
curl -X POST "http://localhost:8501/api/v1/batch-import-directory" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/app/uploads/batch1",
    "provider_code": "UATL",
    "num_workers": 8
  }'
```

**Get Optimal Worker Count:**

```bash
curl "http://localhost:8501/api/v1/optimal-workers"
```

### Using the CLI Script

```bash
# Enter backend container
docker-compose exec backend bash

# Import all UATL statements with 8 workers
python process_parallel.py --workers 8

# Import specific month
python process_parallel.py --workers 8 --month 2025-10

# Dry run (preview only)
python process_parallel.py --workers 8 --dry-run
```

## Environment Configuration

Edit `backend/.env` to customize:

```bash
# Database
DB_HOST=mysql
DB_PORT=3306
DB_USER=fraud_user
DB_PASSWORD=fraud_pass
DB_NAME=fraud_detection

# Performance
PARALLEL_IMPORT_WORKERS=8  # Adjust based on CPU
UVICORN_WORKERS=4          # FastAPI workers
DB_POOL_SIZE=20            # Connection pool

# Application
APP_ENV=production
LOG_LEVEL=INFO
```

## Performance Benchmarks

### Expected Throughput (i5-12400 + 32GB RAM)

**Import Performance:**
- Small statements (100-500 txns): ~5-10 files/second
- Medium statements (500-2000 txns): ~2-5 files/second
- Large statements (2000+ txns): ~1-2 files/second

**Processing Performance:**
- Format 1 (with permutation optimization): ~500-1000 txns/second
- Format 2 (simple): ~2000-5000 txns/second
- MTN: ~2000-5000 txns/second

### Optimization Tips

1. **Increase Workers for Import-Heavy Workloads:**
   ```bash
   # Edit backend/.env
   PARALLEL_IMPORT_WORKERS=10

   # Restart backend
   docker-compose restart backend
   ```

2. **Increase MySQL Buffer Pool for Large Datasets:**
   ```yaml
   # Edit docker-compose.yml
   command: --innodb_buffer_pool_size=4G
   ```

3. **Use SSD Storage for Docker Volumes:**
   ```bash
   # Check current storage
   docker volume inspect airtel_fraud_detection_mysql_data
   ```

4. **Monitor Resource Usage:**
   ```bash
   # Watch container stats
   docker stats

   # View logs
   docker-compose logs -f backend
   docker-compose logs -f mysql
   ```

## Common Operations

### Start Services

```bash
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f mysql
```

### Restart Services

```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend
```

### Access Containers

```bash
# Backend shell
docker-compose exec backend bash

# MySQL shell
docker-compose exec mysql mysql -u root -ppassword fraud_detection
```

### Update Code

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Backup Database

```bash
# Export database
docker-compose exec mysql mysqldump -u root -ppassword fraud_detection > backup_$(date +%Y%m%d).sql

# Import database
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < backup.sql
```

### Clean Up

```bash
# Remove containers and networks (keeps volumes)
docker-compose down

# Remove everything including volumes
docker-compose down -v

# Remove unused Docker resources
docker system prune -a
```

## Troubleshooting

### MySQL Connection Issues

```bash
# Check MySQL is running
docker-compose ps mysql

# View MySQL logs
docker-compose logs mysql

# Restart MySQL
docker-compose restart mysql

# Connect to MySQL manually
docker-compose exec mysql mysql -u root -ppassword
```

### Backend Not Starting

```bash
# View backend logs
docker-compose logs backend

# Check if port 8501 is in use
sudo lsof -i :8501

# Rebuild backend
docker-compose build backend
docker-compose up -d backend
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce parallel workers in backend/.env
PARALLEL_IMPORT_WORKERS=4
UVICORN_WORKERS=2

# Restart
docker-compose restart backend
```

### Slow Performance

```bash
# Check CPU usage
docker stats

# Check disk I/O
docker exec backend df -h

# Monitor MySQL queries
docker-compose exec mysql mysql -u root -ppassword -e "SHOW PROCESSLIST"

# Increase buffer pool (docker-compose.yml)
command: --innodb_buffer_pool_size=4G
```

### Import Errors

```bash
# Check file permissions
docker-compose exec backend ls -la /app/uploads

# View import logs
docker-compose logs backend | grep "import"

# Run import manually with debug
docker-compose exec backend python process_parallel.py --workers 1 --dry-run
```

## Migration from Local Setup

### 1. Export Existing Database

```bash
# On local machine
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword fraud_detection > migration_backup.sql
```

### 2. Copy Files to Docker

```bash
# Copy statement files
cp -r /path/to/statements/* docs/data/UATL/extracted/
cp -r /path/to/mtn/* docs/data/UMTN/extracted/

# Copy mapper.csv
cp /path/to/mapper.csv docs/data/statements/mapper.csv
```

### 3. Import to Docker

```bash
# Start Docker services
./setup-docker.sh

# Import database
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < migration_backup.sql

# Verify
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) FROM metadata"
```

## Monitoring and Logs

### Application Logs

```bash
# Real-time logs
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Save logs to file
docker-compose logs backend > backend_logs.txt
```

### Database Logs

```bash
# MySQL general log
docker-compose exec mysql tail -f /var/log/mysql/error.log

# Query log
docker-compose exec mysql mysql -u root -ppassword -e "SHOW VARIABLES LIKE 'general_log%'"
```

### Resource Monitoring

```bash
# Real-time stats
docker stats

# Container disk usage
docker system df

# Volume sizes
docker volume ls
du -sh /var/lib/docker/volumes/airtel_fraud_detection_*
```

## Security Considerations

### Production Deployment

1. **Change Default Passwords:**
   ```bash
   # Edit backend/.env
   DB_PASSWORD=<strong-random-password>
   ```

2. **Restrict Network Access:**
   ```yaml
   # docker-compose.yml
   services:
     mysql:
       ports:
         - "127.0.0.1:3307:3306"  # Only localhost
   ```

3. **Use Secrets Management:**
   ```bash
   # Use Docker secrets instead of environment variables
   docker secret create db_password password.txt
   ```

4. **Enable SSL/TLS:**
   ```yaml
   # Add reverse proxy with SSL (nginx/traefik)
   ```

5. **Regular Backups:**
   ```bash
   # Setup cron job for daily backups
   0 2 * * * docker-compose exec mysql mysqldump -u root -ppassword fraud_detection > /backups/daily_$(date +\%Y\%m\%d).sql
   ```

## Advanced Configuration

### Custom MySQL Configuration

Create `mysql.cnf`:

```ini
[mysqld]
max_allowed_packet=256M
innodb_buffer_pool_size=4G
innodb_log_file_size=512M
innodb_flush_log_at_trx_commit=2
innodb_flush_method=O_DIRECT
query_cache_size=0
query_cache_type=0
```

Mount in `docker-compose.yml`:

```yaml
mysql:
  volumes:
    - ./mysql.cnf:/etc/mysql/conf.d/custom.cnf:ro
```

### Custom Python Configuration

Create `backend/gunicorn.conf.py` for production:

```python
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8501"
keepalive = 120
timeout = 300
graceful_timeout = 30
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- GitHub Issues: https://github.com/your-repo/issues
- Documentation: http://localhost:8501/docs
