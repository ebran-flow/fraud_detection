#!/bin/bash
################################################################################
# Create fraud_detection MySQL User for LOCAL MySQL 8.0
# Creates a user with full access except DROP privileges
################################################################################

set -euo pipefail

echo "========================================================================"
echo "Create fraud_detection User on LOCAL MySQL"
echo "========================================================================"
echo ""

# Load credentials from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
else
    echo "Error: .env file not found at $SCRIPT_DIR/.env"
    exit 1
fi

echo "Creating user from .env configuration:"
echo "  Host: ${DB_HOST}:${DB_PORT}"
echo "  User: ${DB_USER}"
echo "  Database: ${DB_NAME}"
echo ""

# Create user and grant privileges (connect as root with password from .env)
mysql -h "${DB_HOST}" -P "${DB_PORT}" -u root -p"${DB_PASSWORD}" <<EOF
-- Create user for both localhost and 127.0.0.1
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';

-- Grant all privileges EXCEPT DROP on fraud_detection database
GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX,
      CREATE VIEW, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE,
      REFERENCES, TRIGGER
ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';

GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX,
      CREATE VIEW, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE,
      REFERENCES, TRIGGER
ON ${DB_NAME}.* TO '${DB_USER}'@'127.0.0.1';

-- Flush privileges
FLUSH PRIVILEGES;

-- Show user privileges
SHOW GRANTS FOR '${DB_USER}'@'localhost';
EOF

echo ""
echo "========================================================================"
echo "✅ User Created from .env!"
echo "========================================================================"
echo ""
echo "User: ${DB_USER}"
echo "Password: ${DB_PASSWORD}"
echo "Host: ${DB_HOST}"
echo "Port: ${DB_PORT}"
echo "Database: ${DB_NAME}"
echo ""

exit 0
