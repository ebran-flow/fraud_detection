#!/bin/bash
################################################################################
# Percona XtraBackup 8.0 Installation Script
# For local MySQL 8.0 installation
################################################################################

set -euo pipefail

echo "========================================================================"
echo "Percona XtraBackup 8.0 Installation"
echo "========================================================================"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges."
    echo "Please run with: sudo bash $0"
    exit 1
fi

# Step 1: Download Percona repository package
echo "Step 1: Downloading Percona repository..."
cd /tmp
wget -q https://repo.percona.com/apt/percona-release_latest.$(lsb_release -sc)_all.deb

if [ $? -ne 0 ]; then
    echo "Error: Failed to download Percona repository package"
    exit 1
fi

# Step 2: Install Percona repository
echo ""
echo "Step 2: Installing Percona repository..."
dpkg -i percona-release_latest.$(lsb_release -sc)_all.deb

# Step 3: Enable tools repository
echo ""
echo "Step 3: Enabling Percona tools repository..."
percona-release enable-only tools release
apt-get update

# Step 4: Install XtraBackup 8.0
echo ""
echo "Step 4: Installing Percona XtraBackup 8.0..."
apt-get install -y percona-xtrabackup-80

if [ $? -ne 0 ]; then
    echo "Error: Failed to install percona-xtrabackup-80"
    exit 1
fi

# Step 5: Verify installation
echo ""
echo "Step 5: Verifying installation..."
XTRABACKUP_VERSION=$(xtrabackup --version 2>&1 | head -1)
echo "✅ Installed: $XTRABACKUP_VERSION"

# Step 6: Create backup directories
echo ""
echo "Step 6: Creating backup directories..."
BACKUP_DIR="/home/ebran/Developer/projects/airtel_fraud_detection/backups/xtrabackup"
mkdir -p "$BACKUP_DIR/full"
mkdir -p "$BACKUP_DIR/incremental"

ACTUAL_USER=${SUDO_USER:-$USER}
chown -R $ACTUAL_USER:$ACTUAL_USER "$BACKUP_DIR"
chmod 755 "$BACKUP_DIR"

echo "✅ Backup directories created: $BACKUP_DIR"

# Step 7: Test XtraBackup
echo ""
echo "Step 7: Testing XtraBackup connection..."
echo "Please enter MySQL root password:"

su - $ACTUAL_USER -c "
    read -sp 'MySQL root password: ' MYSQL_PASSWORD
    echo ''
    xtrabackup --backup \
        --user=root \
        --password=\"\password\" \
        --target-dir=/tmp/xtrabackup_test \
        &> /tmp/xtrabackup_test.log

    if [ \$? -eq 0 ]; then
        echo '✅ XtraBackup test successful!'
        rm -rf /tmp/xtrabackup_test /tmp/xtrabackup_test.log
    else
        echo '❌ XtraBackup test failed. Check /tmp/xtrabackup_test.log'
        cat /tmp/xtrabackup_test.log
    fi
"

# Clean up
rm -f /tmp/percona-release_latest.*.deb

echo ""
echo "========================================================================"
echo "✅ XtraBackup 8.0 Installation Complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Take your first full backup:"
echo "   cd /home/ebran/Developer/projects/airtel_fraud_detection/backend"
echo "   ./scripts/backup/xtrabackup_full.sh"
echo ""
echo "2. Set up automated backups:"
echo "   crontab -e"
echo "   # Add backup schedule from XTRABACKUP_SETUP.md"
echo ""

exit 0
