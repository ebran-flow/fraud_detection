# Quick Start Guide - 32GB RAM System

Optimized for your i5-12400 with 32GB RAM. **Direct DB access** (process_parallel.py bypasses FastAPI).

## 1. Start Docker

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection

# Start with optimized limits
docker compose down
docker compose up -d

# Wait for MySQL (takes ~15 seconds)
docker compose logs -f mysql
# Wait for "ready for connections" message, then Ctrl+C
```

## 2. Import UATL Statements

```bash
cd backend

# Default: 6 workers (recommended for stability)
python process_parallel.py

# Or specify workers
python process_parallel.py --workers 8

# Maximum: 12 workers (monitor with docker stats)
python process_parallel.py --workers 12
```

## 3. Monitor Progress

**In another terminal:**
```bash
# Watch resource usage
docker stats

# Check import log
tail -f backend/process_parallel.log
```

**Expected performance:**
- **Speed:** 4-8 statements/second with 6 workers
- **CPU:** 600-800% usage (this is normal for parallel processing)
- **Memory:** 16-20GB total (MySQL + Backend)
- **Time:** ~1000 statements = 2-4 minutes

## Resource Allocation (32GB RAM)

| Component | CPU | RAM | Purpose |
|-----------|-----|-----|---------|
| MySQL | 8 cores | 10GB | Database with 4GB buffer pool |
| Backend | 8 cores | 12GB | Python workers (6 parallel) |
| Uvicorn | 1 worker | - | Minimal (not used by parallel script) |
| System | 4 threads | 10GB | OS and other apps |
| **Total** | **12 threads** | **32GB** | Balanced allocation |

## Quick Commands

```bash
# Dry run (preview without importing)
python process_parallel.py --dry-run

# Import specific month
python process_parallel.py --month 2025-09

# Check what's been imported
docker compose exec mysql mysql -u root -ppassword fraud_detection -e "SELECT COUNT(*) FROM uatl_raw_statements"

# Restart if needed
docker compose restart
```

## Troubleshooting

**Container dies:**
```bash
# Reduce workers
python process_parallel.py --workers 4

# Check if other apps are using RAM
free -h
```

**Want more speed:**
```bash
# Push to 10-12 workers (monitor with docker stats)
python process_parallel.py --workers 10
```

**Check for errors:**
```bash
# MySQL logs
docker compose logs mysql --tail 100

# Import logs
cat backend/process_parallel.log | grep ERROR
```

## That's It!

You should see output like:
```
[1/1000] ✅ 68b5609553c2e - Uploaded 156 transactions | Speed: 6.50/s | ETA: 0.5h
[2/1000] ✅ 68b5866aef104 - Uploaded 243 transactions | Speed: 6.75/s | ETA: 0.5h
...
```

Monitor with `docker stats` and you're good to go!
