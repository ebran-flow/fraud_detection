#!/bin/bash
################################################################################
# Percona XtraBackup 8.2 Installation Script
# For Ubuntu with MySQL 8.2
################################################################################

set -euo pipefail

echo "========================================================================"
echo "Percona XtraBackup 8.2 Installation"
echo "========================================================================"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges."
    echo "Please run with: sudo bash $0"
    exit 1
fi

# Step 1: Download Percona repository package
echo "Step 1: Downloading Percona repository package..."
cd /tmp
curl -O https://repo.percona.com/apt/percona-release_latest.generic_all.deb

if [ $? -ne 0 ]; then
    echo "Error: Failed to download Percona repository package"
    exit 1
fi

# Step 2: Install Percona repository
echo ""
echo "Step 2: Installing Percona repository..."
apt install -y ./percona-release_latest.generic_all.deb

# Step 3: Enable Percona Server 8.2 and tools repositories
echo ""
echo "Step 3: Enabling Percona Server 8.2 repository..."
percona-release enable-only ps-82 release

echo "Enabling Percona tools repository..."
percona-release enable tools release

# Step 4: Update package lists
echo ""
echo "Step 4: Updating package lists..."
apt-get update

# Step 5: Install XtraBackup 8.2
echo ""
echo "Step 5: Installing Percona XtraBackup 8.2..."
apt-get install -y percona-xtrabackup-82

if [ $? -ne 0 ]; then
    echo "Error: Failed to install percona-xtrabackup-82"
    exit 1
fi

# Step 6: Verify installation
echo ""
echo "Step 6: Verifying installation..."
XTRABACKUP_VERSION=$(xtrabackup --version 2>&1 | head -1)

if [ $? -eq 0 ]; then
    echo "✅ XtraBackup installed successfully!"
    echo "Version: $XTRABACKUP_VERSION"
else
    echo "❌ XtraBackup installation failed"
    exit 1
fi

# Step 7: Clean up
echo ""
echo "Step 7: Cleaning up..."
rm -f /tmp/percona-release_latest.generic_all.deb

# Step 8: Create backup directories
echo ""
echo "Step 8: Creating backup directories..."
BACKUP_DIR="/home/ebran/Developer/projects/airtel_fraud_detection/backups/xtrabackup"
mkdir -p "$BACKUP_DIR/full"
mkdir -p "$BACKUP_DIR/incremental"

# Get the actual user (not root when using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
chown -R $ACTUAL_USER:$ACTUAL_USER "$BACKUP_DIR"
chmod 755 "$BACKUP_DIR"

echo "✅ Backup directories created: $BACKUP_DIR"

# Step 9: Test connection
echo ""
echo "Step 9: Testing XtraBackup connection to MySQL..."
echo "Please enter your MySQL root password when prompted:"

cd /home/ebran/Developer/projects/airtel_fraud_detection/backend

if [ -f .env ]; then
    source .env

    echo "Testing connection..."
    sudo -u $ACTUAL_USER xtrabackup --backup \
        --host=127.0.0.1 \
        --port=${DB_PORT:-3307} \
        --user=${DB_USER:-root} \
        --password="$DB_PASSWORD" \
        --target-dir=/tmp/xtrabackup_test \
        --databases="fraud_detection" 2>&1 | grep -E "(version|completed OK)"

    if [ $? -eq 0 ]; then
        echo "✅ XtraBackup can connect to MySQL successfully!"
        rm -rf /tmp/xtrabackup_test
    else
        echo "⚠️  XtraBackup connection test had issues. Check your MySQL credentials."
    fi
else
    echo "⚠️  .env file not found. Skipping connection test."
fi

echo ""
echo "========================================================================"
echo "✅ Installation Complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Review XTRABACKUP_SETUP.md for backup strategy"
echo "2. Take your first full backup:"
echo "   cd /home/ebran/Developer/projects/airtel_fraud_detection/backend"
echo "   ./scripts/backup/xtrabackup_full.sh"
echo ""
echo "3. Set up automated backups with cron (see XTRABACKUP_SETUP.md)"
echo ""

exit 0
