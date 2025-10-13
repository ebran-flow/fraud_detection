#!/bin/bash
# ============================================================
# MySQL Backup Script (Cross-Platform Compatible)
# Works with MySQL running in Docker on Windows/Linux/Mac
# Cross MySQL version compatible (5.7, 8.0+)
# Reads credentials from .env file
# ============================================================

set -e  # Exit on error

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Configuration (with defaults from .env)
DOCKER_CONTAINER="${DOCKER_CONTAINER:-mysql-fraud-detection}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3307}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-root}"
DB_NAME="${DB_NAME:-fraud_detection}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}MySQL Backup Script - Cross-Platform Compatible${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}Database:${NC} ${DB_NAME}"
echo -e "${YELLOW}Backup File:${NC} ${BACKUP_FILE}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER}$"; then
    echo -e "${YELLOW}Warning: Container '${DOCKER_CONTAINER}' not found${NC}"
    echo -e "${YELLOW}Attempting direct connection to MySQL...${NC}"
    USE_DOCKER=false
else
    USE_DOCKER=true
fi

# Perform backup
echo -e "${GREEN}Starting backup...${NC}"

if [ "$USE_DOCKER" = true ]; then
    # Backup via Docker exec
    docker exec ${DOCKER_CONTAINER} mysqldump \
        --host=${DB_HOST} \
        --port=3306 \
        --user=${DB_USER} \
        --password=${DB_PASSWORD} \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --default-character-set=utf8mb4 \
        --set-charset \
        --no-tablespaces \
        --column-statistics=0 \
        --skip-comments \
        --compact \
        --skip-lock-tables \
        ${DB_NAME} > "${BACKUP_FILE}"
else
    # Direct connection (for local MySQL or port-forwarded Docker)
    mysqldump \
        --host=${DB_HOST} \
        --port=${DB_PORT} \
        --user=${DB_USER} \
        --password=${DB_PASSWORD} \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --default-character-set=utf8mb4 \
        --set-charset \
        --no-tablespaces \
        --column-statistics=0 \
        --skip-comments \
        --compact \
        --skip-lock-tables \
        ${DB_NAME} > "${BACKUP_FILE}"
fi

# Check if backup was successful
if [ $? -eq 0 ] && [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo ""
    echo -e "${GREEN}✓ Backup completed successfully!${NC}"
    echo -e "${GREEN}  File: ${BACKUP_FILE}${NC}"
    echo -e "${GREEN}  Size: ${BACKUP_SIZE}${NC}"

    # Compress backup (optional)
    echo ""
    read -p "Compress backup with gzip? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Compressing backup...${NC}"
        gzip "${BACKUP_FILE}"
        COMPRESSED_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(du -h "${COMPRESSED_FILE}" | cut -f1)
        echo -e "${GREEN}✓ Compressed: ${COMPRESSED_FILE} (${COMPRESSED_SIZE})${NC}"
    fi

    # List recent backups
    echo ""
    echo -e "${GREEN}Recent backups:${NC}"
    ls -lh "${BACKUP_DIR}" | tail -n 5

else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Backup completed successfully!${NC}"
echo -e "${GREEN}============================================================${NC}"
