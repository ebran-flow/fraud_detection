#!/bin/bash
################################################################################
# MySQL 8.0 Local Installation Script
# Installs MySQL 8.0 locally for XtraBackup compatibility
################################################################################

set -euo pipefail

echo "========================================================================"
echo "MySQL 8.0 Local Installation"
echo "========================================================================"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges."
    echo "Please run with: sudo bash $0"
    exit 1
fi

# Get the actual user (not root when using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}

# Step 1: Download MySQL APT config
echo "Step 1: Downloading MySQL APT configuration..."
cd /tmp
wget -q https://dev.mysql.com/get/mysql-apt-config_0.8.29-1_all.deb

if [ $? -ne 0 ]; then
    echo "Error: Failed to download MySQL APT config"
    exit 1
fi

# Step 2: Configure MySQL repository
echo ""
echo "Step 2: Configuring MySQL repository..."
echo "IMPORTANT: In the next dialog:"
echo "  1. Select 'MySQL Server & Cluster'"
echo "  2. Choose 'mysql-8.0'"
echo "  3. Select 'Ok'"
echo ""
read -p "Press Enter to continue..."

DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.29-1_all.deb

# Step 3: Update package lists
echo ""
echo "Step 3: Updating package lists..."
apt-get update

# Step 4: Install MySQL 8.0
echo ""
echo "Step 4: Installing MySQL Server 8.0..."
echo "You will be prompted to set a root password."
echo ""

DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server-8.0

if [ $? -ne 0 ]; then
    echo "Error: Failed to install MySQL 8.0"
    exit 1
fi

# Step 5: Start MySQL service
echo ""
echo "Step 5: Starting MySQL service..."
systemctl start mysql
systemctl enable mysql

# Step 6: Verify installation
echo ""
echo "Step 6: Verifying installation..."
MYSQL_VERSION=$(mysql --version)
echo "Installed: $MYSQL_VERSION"

# Step 7: Create fraud_detection database
echo ""
echo "Step 7: Creating fraud_detection database..."
echo "Please enter the MySQL root password you just set:"

mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SELECT 'Database created successfully' AS status;
SHOW DATABASES LIKE 'fraud_detection';
EOF

echo ""
echo "========================================================================"
echo "✅ MySQL 8.0 Installation Complete!"
echo "========================================================================"
echo ""
echo "MySQL 8.0 is now running on:"
echo "  Host: 127.0.0.1"
echo "  Port: 3306"
echo "  Database: fraud_detection"
echo ""
echo "Next steps:"
echo "1. Restore database from backups"
echo "2. Install Percona XtraBackup 8.0"
echo "3. Set up automated backups"
echo ""
echo "Run the restore script:"
echo "  sudo bash restore_to_local_mysql.sh"
echo ""

exit 0
