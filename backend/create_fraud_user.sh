#!/bin/bash
################################################################################
# Create fraud_detection MySQL User
# Creates a user with full access except DROP privileges
################################################################################

set -euo pipefail

echo "========================================================================"
echo "Create fraud_detection Database User"
echo "========================================================================"
echo ""

# Get current database password
DB_PASSWORD=$(grep DB_PASSWORD .env | cut -d '=' -f2)

# Prompt for new username and password
read -p "Enter new username [fraud_user]: " NEW_USER
NEW_USER=${NEW_USER:-fraud_user}

read -sp "Enter password for $NEW_USER: " NEW_PASSWORD
echo ""
read -sp "Confirm password: " NEW_PASSWORD_CONFIRM
echo ""

if [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
    echo "Error: Passwords do not match"
    exit 1
fi

echo ""
echo "Creating user: $NEW_USER"
echo "Database: fraud_detection"
echo "Host: 127.0.0.1 (Docker MySQL on port 3307)"
echo ""

# Create user and grant privileges
mysql -h 127.0.0.1 -P 3307 -u root -p"$DB_PASSWORD" <<EOF
-- Create user
CREATE USER IF NOT EXISTS '$NEW_USER'@'%' IDENTIFIED BY '$NEW_PASSWORD';

-- Grant all privileges EXCEPT DROP on fraud_detection database
GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX,
      CREATE VIEW, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE,
      REFERENCES, TRIGGER
ON fraud_detection.* TO '$NEW_USER'@'%';

-- Grant usage on the database
GRANT USAGE ON fraud_detection.* TO '$NEW_USER'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Show user privileges
SHOW GRANTS FOR '$NEW_USER'@'%';
EOF

echo ""
echo "========================================================================"
echo "✅ User Created Successfully!"
echo "========================================================================"
echo ""
echo "User: $NEW_USER"
echo "Password: $NEW_PASSWORD"
echo "Database: fraud_detection"
echo ""
echo "Permissions granted:"
echo "  ✅ SELECT, INSERT, UPDATE, DELETE (data operations)"
echo "  ✅ CREATE, ALTER (table modifications)"
echo "  ✅ INDEX (create/drop indexes)"
echo "  ✅ CREATE VIEW, SHOW VIEW"
echo "  ✅ CREATE/ALTER ROUTINE, EXECUTE (stored procedures)"
echo "  ✅ REFERENCES, TRIGGER"
echo "  ❌ DROP (tables/database) - NOT granted"
echo ""
echo "Update your .env file:"
echo "  DB_USER=$NEW_USER"
echo "  DB_PASSWORD=$NEW_PASSWORD"
echo ""

exit 0
