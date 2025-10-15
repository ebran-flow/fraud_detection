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

# Load credentials from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
else
    echo "Error: .env file not found at $SCRIPT_DIR/.env"
    exit 1
fi

echo "Setting root password from .env..."
echo "  User: ${DB_USER}"
echo "  Password: ${DB_PASSWORD}"
echo ""

# Connect using sudo (works with auth_socket) and change authentication
mysql <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
FLUSH PRIVILEGES;
SELECT user, host, plugin FROM mysql.user WHERE user='root';
EOF

echo ""
echo "========================================================================"
echo "✅ MySQL Root Authentication Fixed!"
echo "========================================================================"
echo ""
echo "You can now connect with credentials from .env:"
echo "  Username: ${DB_USER}"
echo "  Password: ${DB_PASSWORD}"
echo "  Host: ${DB_HOST}"
echo "  Port: ${DB_PORT}"
echo ""
echo "Test connection:"
echo "  mysql -h ${DB_HOST} -P ${DB_PORT} -u ${DB_USER} -p${DB_PASSWORD} -e \"SELECT 1\""
echo ""

exit 0
