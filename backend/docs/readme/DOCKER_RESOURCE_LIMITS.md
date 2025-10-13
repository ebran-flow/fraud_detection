# Docker Resource Limits

Resource limits optimized for 32GB RAM system with i5-12400 (6 cores / 12 threads).

## Current Limits

### MySQL Container
- **CPU:** 8 cores (max), 4 cores (reserved)
- **Memory:** 10GB (max), 4GB (reserved)
- **Buffer Pool:** 4GB (optimized for large imports)
- **Max Connections:** 300
- **Max Packet Size:** 512MB

### Backend Container
- **CPU:** 8 cores (max), 2 cores (reserved)
- **Memory:** 12GB (max), 4GB (reserved)
- **Uvicorn Workers:** 1 (minimal - parallel script uses direct DB access)
- **Parallel Import Workers:** 6 (default, max 12)

## Parallel Processing Scripts

Scripts use **direct database connection** (bypasses FastAPI):

```bash
cd backend

# Default: 6 workers (recommended)
python process_parallel.py

# High performance: 8-10 workers
python process_parallel.py --workers 8

# Maximum: 12 workers (use with caution)
python process_parallel.py --workers 12
```

## Why These Limits?

1. **Direct DB access:** process_parallel.py connects directly to MySQL (no need for multiple uvicorn workers)
2. **Balanced allocation:** Uses ~22GB total, leaves 10GB for system and other apps
3. **Prevents container death:** Docker kills containers that exceed limits
4. **Stable processing:** 4-8 statements/sec with 6 workers

## Your Hardware

- **CPU:** i5-12400 (6 cores, 12 threads)
- **RAM:** 32GB
- **Allocation:**
  - MySQL: 10GB RAM, 8 CPUs
  - Backend: 12GB RAM, 8 CPUs (6 parallel workers + 1 uvicorn)
  - System: 10GB RAM, 4 threads remaining
  - **Total Docker:** 22GB RAM (69% utilization)

## Adjusting Limits

Edit `docker-compose.yml` to increase/decrease:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # Increase to '6' or '8' if stable
      memory: 4G     # Increase to 6G or 8G if needed
    reservations:
      cpus: '2'      # Minimum guaranteed
      memory: 2G     # Minimum guaranteed
```

After changing limits:
```bash
docker compose down
docker compose up -d
```

## Monitoring Resources

**Check container resource usage:**
```bash
docker stats
```

**Watch MySQL memory:**
```bash
docker compose exec mysql mysql -u root -ppassword -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"
```

**Check if container was killed (OOM):**
```bash
docker compose logs mysql | grep -i "killed"
dmesg | grep -i "killed"
```

## Troubleshooting

### Container still dying?

1. **Reduce workers:**
   ```bash
   python process_parallel.py --workers 4
   ```

2. **Check host memory:**
   ```bash
   free -h
   htop
   ```

3. **Process one month at a time:**
   ```bash
   python process_parallel.py --month 2025-09
   python process_parallel.py --month 2025-08
   ```

4. **Check if other applications are using RAM:**
   Close browser, IDE, or other heavy applications

### Want even more performance?

If system is stable for 10+ minutes, you can push harder:

1. **Increase to 10-12 workers:**
   ```bash
   python process_parallel.py --workers 10
   ```

2. **Increase MySQL buffer pool to 6GB:**
   Edit `docker-compose.yml`:
   ```yaml
   --innodb_buffer_pool_size=6G
   ```
   Then restart: `docker compose restart mysql`

3. **Monitor with `docker stats`** to ensure memory stays below 90%

## Recommended Workflow

```bash
# 1. Start containers with optimized resource limits
docker compose down
docker compose up -d

# 2. Wait for MySQL to be ready
docker compose logs -f mysql

# 3. Test with dry run first
cd backend
python process_parallel.py --dry-run

# 4. Run actual import (monitor in another terminal with: docker stats)
python process_parallel.py

# 5. If stable and you want more speed
python process_parallel.py --workers 8
```

## Key Metrics to Watch (docker stats)

- **Memory usage:** Should stay below 20GB total (MySQL + Backend)
- **CPU usage:** Will hit 600-800% with 6 workers (this is good!)
- **Swap usage:** Should remain at 0
- **Process speed:** 4-8 statements/sec with 6 workers
