#!/bin/bash
################################################################################
# Create fraud_detection MySQL User for LOCAL MySQL 8.0
# Creates a user with full access except DROP privileges
################################################################################

set -euo pipefail

echo "========================================================================"
echo "Create fraud_detection User on LOCAL MySQL 8.0"
echo "========================================================================"
echo ""

MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="password"

NEW_USER="fraud_user"
NEW_PASSWORD="fraud_password"

echo "Creating user: $NEW_USER"
echo "Database: fraud_detection"
echo "Host: 127.0.0.1:3306 (Local MySQL 8.0)"
echo ""

# Create user and grant privileges
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" <<EOF
-- Create user for both localhost and 127.0.0.1
CREATE USER IF NOT EXISTS '$NEW_USER'@'localhost' IDENTIFIED BY '$NEW_PASSWORD';
CREATE USER IF NOT EXISTS '$NEW_USER'@'127.0.0.1' IDENTIFIED BY '$NEW_PASSWORD';

-- Grant all privileges EXCEPT DROP on fraud_detection database
GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX,
      CREATE VIEW, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE,
      REFERENCES, TRIGGER
ON fraud_detection.* TO '$NEW_USER'@'localhost';

GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX,
      CREATE VIEW, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE,
      REFERENCES, TRIGGER
ON fraud_detection.* TO '$NEW_USER'@'127.0.0.1';

-- Flush privileges
FLUSH PRIVILEGES;

-- Show user privileges
SHOW GRANTS FOR '$NEW_USER'@'localhost';
EOF

echo ""
echo "========================================================================"
echo "✅ User Created on Local MySQL 8.0!"
echo "========================================================================"
echo ""
echo "User: $NEW_USER"
echo "Password: $NEW_PASSWORD"
echo "Host: 127.0.0.1 or localhost"
echo "Port: 3306"
echo ""

exit 0
