#!/bin/bash
################################################################################
# Fix MySQL Root Authentication
# Changes from auth_socket to password authentication
################################################################################

set -euo pipefail

echo "========================================================================"
echo "Fixing MySQL Root Authentication"
echo "========================================================================"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges."
    echo "Please run with: sudo bash $0"
    exit 1
fi

echo "Setting root password to 'password'..."
echo ""

# Connect using sudo (works with auth_socket) and change authentication
mysql <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
FLUSH PRIVILEGES;
SELECT user, host, plugin FROM mysql.user WHERE user='root';
EOF

echo ""
echo "========================================================================"
echo "✅ MySQL Root Authentication Fixed!"
echo "========================================================================"
echo ""
echo "You can now connect with:"
echo "  Username: root"
echo "  Password: password"
echo ""
echo "Test connection:"
echo "  mysql -u root -ppassword -e \"SELECT 1\""
echo ""

exit 0
