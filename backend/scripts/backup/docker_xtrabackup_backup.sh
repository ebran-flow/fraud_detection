#!/bin/bash
################################################################################
# Docker-based XtraBackup Full Backup Script
# Runs XtraBackup in a container with access to MySQL data volume
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="$(cd "$PROJECT_ROOT/../backups" && pwd)/xtrabackup_docker"
LOG_DIR="$PROJECT_ROOT/logs"

# Docker configuration
MYSQL_CONTAINER="mysql"
MYSQL_DATA_VOLUME="docker_config_dbdata"
XTRABACKUP_IMAGE="percona/percona-xtrabackup:8.0"

# Ensure directories exist
mkdir -p "$BACKUP_BASE_DIR/full"
mkdir -p "$BACKUP_BASE_DIR/incremental"
mkdir -p "$LOG_DIR"

# Generate backup directory name with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/full/full_$TIMESTAMP"
LOG_FILE="$LOG_DIR/docker_xtrabackup_full_$TIMESTAMP.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Docker XtraBackup Full Backup" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Check if MySQL container is running
if ! docker ps --filter "name=$MYSQL_CONTAINER" --filter "status=running" | grep -q "$MYSQL_CONTAINER"; then
    echo "Error: MySQL container '$MYSQL_CONTAINER' is not running" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if data volume exists
if ! docker volume inspect "$MYSQL_DATA_VOLUME" &> /dev/null; then
    echo "Error: MySQL data volume '$MYSQL_DATA_VOLUME' not found" | tee -a "$LOG_FILE"
    exit 1
fi

# Pull XtraBackup image if not present
echo "Checking for XtraBackup Docker image..." | tee -a "$LOG_FILE"
if ! docker images "$XTRABACKUP_IMAGE" | grep -q "percona-xtrabackup"; then
    echo "Pulling XtraBackup image..." | tee -a "$LOG_FILE"
    docker pull "$XTRABACKUP_IMAGE" 2>&1 | tee -a "$LOG_FILE"
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "" | tee -a "$LOG_FILE"
echo "Backup configuration:" | tee -a "$LOG_FILE"
echo "  MySQL container: $MYSQL_CONTAINER" | tee -a "$LOG_FILE"
echo "  Data volume: $MYSQL_DATA_VOLUME" | tee -a "$LOG_FILE"
echo "  Backup location: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "  XtraBackup image: $XTRABACKUP_IMAGE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Get MySQL credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    MYSQL_USER="${DB_USER:-root}"
    MYSQL_PASSWORD="$DB_PASSWORD"
    MYSQL_PORT="${DB_PORT:-3307}"
else
    echo "Error: .env file not found" | tee -a "$LOG_FILE"
    exit 1
fi

# Perform backup using Docker
echo "Starting backup..." | tee -a "$LOG_FILE"

docker run --rm \
    --name xtrabackup_backup_$TIMESTAMP \
    --network container:$MYSQL_CONTAINER \
    -v "$MYSQL_DATA_VOLUME":/var/lib/mysql:ro \
    -v "$BACKUP_DIR":/backup \
    "$XTRABACKUP_IMAGE" \
    xtrabackup --backup \
    --host=127.0.0.1 \
    --port=3306 \
    --user=$MYSQL_USER \
    --password="$MYSQL_PASSWORD" \
    --datadir=/var/lib/mysql \
    --target-dir=/backup \
    --parallel=4 \
    --compress \
    --compress-threads=4 \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Backup Completed Successfully" | tee -a "$LOG_FILE"
    echo "Location: $BACKUP_DIR" | tee -a "$LOG_FILE"
    echo "Size: $(du -sh "$BACKUP_DIR" | cut -f1)" | tee -a "$LOG_FILE"
    echo "Completed: $(date)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"

    # Create marker for latest backup
    echo "$TIMESTAMP" > "$BACKUP_BASE_DIR/latest_full_backup.txt"
    echo "$BACKUP_DIR" > "$BACKUP_BASE_DIR/base_dir.txt"

    # Clean up old backups (keep last 4)
    cd "$BACKUP_BASE_DIR/full"
    ls -td full_* 2>/dev/null | tail -n +5 | xargs -r rm -rf
    echo "" | tee -a "$LOG_FILE"
    echo "Cleaned up old backups (keeping last 4)" | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Backup Failed" | tee -a "$LOG_FILE"
    echo "Check log file: $LOG_FILE" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    exit 1
fi
