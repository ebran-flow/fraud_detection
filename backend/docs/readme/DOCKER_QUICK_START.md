# Docker Quick Start Guide

## 🚀 One-Command Setup

```bash
./setup-docker.sh
```

## 📊 Access Points

- **Web UI**: http://localhost:8501
- **API Docs**: http://localhost:8501/docs
- **MySQL**: localhost:3307

## 🔑 Default Credentials

- MySQL root: `password`
- MySQL user: `fraud_user` / `fraud_pass`

## 📁 File Locations

```
/home/ebran/Developer/projects/airtel_fraud_detection/
├── docker-compose.yml          # Service configuration
├── .env.docker                 # Environment template
├── backend/
│   ├── .env                   # Active environment (created by setup)
│   ├── Dockerfile             # Backend image
│   ├── uploads/               # Uploaded statements
│   └── logs/                  # Application logs
└── docs/data/
    ├── UATL/extracted/        # Airtel statements
    └── UMTN/extracted/        # MTN statements
```

## 🔄 Common Commands

### Service Management

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View status
docker-compose ps

# View logs
docker-compose logs -f
```

### Parallel Import (CLI)

```bash
# Enter backend container
docker-compose exec backend bash

# Import with 8 workers (recommended for i5-12400)
python process_parallel.py --workers 8

# Import specific month
python process_parallel.py --workers 8 --month 2025-10

# Dry run
python process_parallel.py --workers 8 --dry-run
```

### Parallel Import (API)

```bash
# Import directory
curl -X POST "http://localhost:8501/api/v1/batch-import-directory" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/app/uploads/batch1",
    "provider_code": "UATL",
    "num_workers": 8
  }'

# Get optimal worker count
curl "http://localhost:8501/api/v1/optimal-workers"
```

### Database Operations

```bash
# MySQL shell
docker-compose exec mysql mysql -u root -ppassword fraud_detection

# Backup
docker-compose exec mysql mysqldump -u root -ppassword fraud_detection > backup.sql

# Restore
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < backup.sql

# Check tables
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "SHOW TABLES"
```

### Monitoring

```bash
# Resource usage
docker stats

# Backend logs
docker-compose logs -f backend

# MySQL logs
docker-compose logs -f mysql

# Disk usage
docker system df
```

### Troubleshooting

```bash
# Rebuild services
docker-compose down
docker-compose build
docker-compose up -d

# Clear everything (including data)
docker-compose down -v
docker system prune -a

# Check port conflicts
sudo lsof -i :8501
sudo lsof -i :3307
```

## ⚙️ Performance Tuning

### Adjust Worker Counts (backend/.env)

```bash
# For faster imports (more CPU usage)
PARALLEL_IMPORT_WORKERS=10

# For stability (less CPU usage)
PARALLEL_IMPORT_WORKERS=4

# After changing, restart
docker-compose restart backend
```

### Increase MySQL Memory (docker-compose.yml)

```yaml
mysql:
  command: --innodb_buffer_pool_size=4G  # Change from 2G to 4G
```

## 📈 Expected Performance

**Import Speed (i5-12400, 8 workers):**
- ~3-5 statements/second (mixed sizes)
- ~15,000-25,000 transactions/minute

**Processing Speed:**
- Format 1: ~500-1000 txns/second
- Format 2: ~2000-5000 txns/second

## 🐛 Common Issues

### "Port already in use"

```bash
# Check what's using the port
sudo lsof -i :8501

# Change port in docker-compose.yml
ports:
  - "8502:8501"  # Change 8501 to 8502
```

### "MySQL connection failed"

```bash
# Wait for MySQL to fully start
docker-compose logs mysql | grep "ready for connections"

# Restart MySQL
docker-compose restart mysql
```

### "Out of memory"

```bash
# Reduce workers in backend/.env
PARALLEL_IMPORT_WORKERS=4
UVICORN_WORKERS=2

# Restart
docker-compose restart backend
```

### "Slow performance"

```bash
# Check CPU/memory
docker stats

# Check disk I/O
docker exec backend df -h

# Reduce worker count or increase buffer pool
```

## 📚 Full Documentation

See `DOCKER_DEPLOYMENT.md` for complete guide including:
- Architecture details
- Security considerations
- Advanced configuration
- Migration guide
- Production deployment

## 🎯 Quick Test

After setup, verify everything works:

```bash
# 1. Check services are running
docker-compose ps

# 2. Test API
curl http://localhost:8501/api/health

# 3. Test database
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT 1"

# 4. Test parallel import
docker-compose exec backend python -c "from app.services.parallel_importer import get_optimal_worker_count; print(f'Optimal workers: {get_optimal_worker_count()}')"
```

Expected output:
```
✅ All services running
✅ API: {"status":"healthy","app":"Fraud Detection System","version":"1.0.0"}
✅ Database: 1
✅ Optimal workers: 8
```

## 🆘 Need Help?

1. Check logs: `docker-compose logs -f`
2. Check status: `docker-compose ps`
3. View docs: http://localhost:8501/docs
4. Full guide: `DOCKER_DEPLOYMENT.md`
