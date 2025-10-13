# Migration Quick Reference

## TL;DR

```bash
# === ON LAPTOP ===
# 1. Export database
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword \
  --single-transaction --set-gtid-purged=OFF \
  fraud_detection | gzip > fraud_detection_backup_$(date +%Y%m%d).sql.gz

# 2. Transfer to PC (USB or network)

# === ON PC ===
# 3. Setup Docker
cd ~/Developer/projects/airtel_fraud_detection
./setup-docker.sh

# 4. Import database
gunzip < fraud_detection_backup_20251012.sql.gz | \
  docker-compose exec -T mysql mysql -u root -ppassword fraud_detection

# 5. Fix collation
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < \
  backend/migrations/fix_collation.sql

# 6. Verify
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
  SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = 'fraud_detection' ORDER BY TABLE_ROWS DESC;
"

# 7. Test
open http://localhost:8501
```

## Quick Commands

### Export (Laptop)

```bash
# Compressed (recommended)
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword --single-transaction --set-gtid-purged=OFF fraud_detection | gzip > backup.sql.gz

# Regular
mysqldump -h 127.0.0.1 -P 3307 -u root -ppassword --single-transaction --set-gtid-purged=OFF fraud_detection > backup.sql
```

### Transfer

```bash
# USB
cp backup.sql.gz /media/$USER/USB_DRIVE/

# Network
scp backup.sql.gz ebran@PC_IP:~/Developer/projects/airtel_fraud_detection/
```

### Import (PC)

```bash
cd ~/Developer/projects/airtel_fraud_detection

# From .gz
gunzip < backup.sql.gz | docker-compose exec -T mysql mysql -u root -ppassword fraud_detection

# From .sql
docker-compose exec -T mysql mysql -u root -ppassword fraud_detection < backup.sql
```

### Verify (PC)

```bash
# Table counts
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
  SELECT 'metadata' as tbl, COUNT(*) FROM metadata
  UNION SELECT 'uatl_raw', COUNT(*) FROM uatl_raw_statements
  UNION SELECT 'uatl_processed', COUNT(*) FROM uatl_processed_statements
  UNION SELECT 'summary', COUNT(*) FROM summary;
"

# Test view (after collation fix)
docker-compose exec mysql mysql -u root -ppassword fraud_detection -e "
  SELECT status, COUNT(*) FROM unified_statements GROUP BY status;
"

# Test API
curl http://localhost:8501/health
```

## Troubleshooting

```bash
# Import failed? Check logs
docker-compose logs mysql | tail -100

# Restart MySQL
docker-compose restart mysql

# Drop and recreate database
docker-compose exec mysql mysql -u root -ppassword -e "
  DROP DATABASE IF EXISTS fraud_detection;
  CREATE DATABASE fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

# Check disk space
docker system df
df -h

# Check container status
docker-compose ps
docker stats
```

## Timing

- Export: 2-10 minutes (depending on size)
- Transfer: 1-15 minutes (depending on method)
- Docker setup: 3-5 minutes
- Import: 5-30 minutes (depending on size)
- Verify: 2-3 minutes
- **Total: 30-60 minutes**

## File Locations

```
Laptop:
  ~/fraud_detection_backup_YYYYMMDD.sql.gz (backup file)

PC:
  ~/Developer/projects/airtel_fraud_detection/  (project root)
  ~/Developer/projects/airtel_fraud_detection/fraud_detection_backup_YYYYMMDD.sql.gz (transferred backup)
```

## Size Estimates

**Backup file sizes** (with compression):

| Statements | Raw Size | Compressed |
|-----------|----------|------------|
| 100       | ~5 MB    | ~1 MB      |
| 1,000     | ~50 MB   | ~10 MB     |
| 10,000    | ~500 MB  | ~100 MB    |
| 50,000    | ~2.5 GB  | ~500 MB    |

## Full Guide

For detailed instructions, see: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

For interactive migration, run: `./migrate-laptop-to-pc.sh`
