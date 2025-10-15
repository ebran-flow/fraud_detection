#!/bin/bash
################################################################################
# Generate Backup Manifest
# Creates metadata file describing what's in the backup
################################################################################

set -euo pipefail

# Parameters
BACKUP_DIR="$1"
BACKUP_TYPE="$2"  # "full" or "incremental"
MANIFEST_FILE="$BACKUP_DIR/BACKUP_MANIFEST.txt"

# Load credentials
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_ROOT/.env.xtrabackup" ]; then
    source "$PROJECT_ROOT/.env.xtrabackup"
else
    echo "Error: .env.xtrabackup not found"
    exit 1
fi

echo "Generating backup manifest..."

# Create manifest
cat > "$MANIFEST_FILE" <<EOF
================================================================================
XTRABACKUP BACKUP MANIFEST
================================================================================

Backup Information:
-------------------
Backup Type:        $BACKUP_TYPE
Backup Date:        $(date '+%Y-%m-%d %H:%M:%S %Z')
Backup Directory:   $BACKUP_DIR
Backup Size:        $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "Calculating...")

MySQL Connection:
-----------------
Host:               ${BACKUP_DB_HOST}
Port:               ${BACKUP_DB_PORT}
Database:           ${BACKUP_DB_NAME}

Git Information:
----------------
EOF

# Add git info if available
cd "$PROJECT_ROOT"
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Git Commit:         $(git rev-parse HEAD 2>/dev/null || echo 'N/A')" >> "$MANIFEST_FILE"
    echo "Git Branch:         $(git branch --show-current 2>/dev/null || echo 'N/A')" >> "$MANIFEST_FILE"
    echo "Git Status:         $(git status --short 2>/dev/null | wc -l) file(s) modified" >> "$MANIFEST_FILE"
else
    echo "Git Commit:         N/A (not a git repository)" >> "$MANIFEST_FILE"
fi

# Add database statistics
cat >> "$MANIFEST_FILE" <<EOF

Database Statistics:
--------------------
EOF

mysql -h "${BACKUP_DB_HOST}" -P "${BACKUP_DB_PORT}" -u "${BACKUP_DB_USER}" -p"${BACKUP_DB_PASSWORD}" "${BACKUP_DB_NAME}" -N -B <<'SQL' >> "$MANIFEST_FILE" 2>/dev/null

SELECT CONCAT('Total Statements:   ', FORMAT(SUM(num_rows), 0))
FROM metadata;

SELECT CONCAT('Total Metadata:     ', FORMAT(COUNT(*), 0), ' records')
FROM metadata;

SELECT CONCAT('Total Summary:      ', FORMAT(COUNT(*), 0), ' records')
FROM summary;

SELECT CONCAT('UATL Raw:           ', FORMAT(COUNT(*), 0), ' rows')
FROM uatl_raw_statements;

SELECT CONCAT('UATL Processed:     ', FORMAT(COUNT(*), 0), ' rows')
FROM uatl_processed_statements;

SELECT CONCAT('UMTN Raw:           ', FORMAT(COUNT(*), 0), ' rows')
FROM umtn_raw_statements;

SELECT CONCAT('UMTN Processed:     ', FORMAT(COUNT(*), 0), ' rows')
FROM umtn_processed_statements;

SQL

# Add schema information
cat >> "$MANIFEST_FILE" <<EOF

Schema Objects:
---------------
EOF

mysql -h "${BACKUP_DB_HOST}" -P "${BACKUP_DB_PORT}" -u "${BACKUP_DB_USER}" -p"${BACKUP_DB_PASSWORD}" "${BACKUP_DB_NAME}" -N -B <<'SQL' >> "$MANIFEST_FILE" 2>/dev/null

SELECT CONCAT('Tables:             ', COUNT(*))
FROM information_schema.tables
WHERE table_schema = 'fraud_detection' AND table_type = 'BASE TABLE';

SELECT CONCAT('Views:              ', COUNT(*))
FROM information_schema.tables
WHERE table_schema = 'fraud_detection' AND table_type = 'VIEW';

SQL

# Add recent migrations/changes
cat >> "$MANIFEST_FILE" <<EOF

Recent Schema Changes:
----------------------
EOF

mysql -h "${BACKUP_DB_HOST}" -P "${BACKUP_DB_PORT}" -u "${BACKUP_DB_USER}" -p"${BACKUP_DB_PASSWORD}" "${BACKUP_DB_NAME}" -N -B <<'SQL' >> "$MANIFEST_FILE" 2>/dev/null

-- Check for key columns added in recent updates
SELECT CONCAT('✓ metadata.header_rows_count: ',
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END)
FROM information_schema.columns
WHERE table_schema = 'fraud_detection'
  AND table_name = 'metadata'
  AND column_name = 'header_rows_count'
LIMIT 1;

SELECT CONCAT('✓ summary.missing_days_detected: ',
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END)
FROM information_schema.columns
WHERE table_schema = 'fraud_detection'
  AND table_name = 'summary'
  AND column_name = 'missing_days_detected'
LIMIT 1;

SELECT CONCAT('✓ uatl_raw_statements.amount_raw: ',
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END)
FROM information_schema.columns
WHERE table_schema = 'fraud_detection'
  AND table_name = 'uatl_raw_statements'
  AND column_name = 'amount_raw'
LIMIT 1;

SELECT CONCAT('✓ uatl_raw_statements.fee_raw: ',
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END)
FROM information_schema.columns
WHERE table_schema = 'fraud_detection'
  AND table_name = 'uatl_raw_statements'
  AND column_name = 'fee_raw'
LIMIT 1;

SELECT CONCAT('✓ unified_statements view: ',
    CASE WHEN table_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END)
FROM information_schema.tables
WHERE table_schema = 'fraud_detection'
  AND table_name = 'unified_statements'
  AND table_type = 'VIEW'
LIMIT 1;

SQL

# Add data quality metrics
cat >> "$MANIFEST_FILE" <<EOF

Data Quality Metrics:
---------------------
EOF

mysql -h "${BACKUP_DB_HOST}" -P "${BACKUP_DB_PORT}" -u "${BACKUP_DB_USER}" -p"${BACKUP_DB_PASSWORD}" "${BACKUP_DB_NAME}" -N -B <<'SQL' >> "$MANIFEST_FILE" 2>/dev/null

SELECT CONCAT('Statements with Quality Issues:     ',
    FORMAT(SUM(CASE WHEN quality_issues_count > 0 THEN 1 ELSE 0 END), 0))
FROM metadata;

SELECT CONCAT('Statements with Header Manipulation: ',
    FORMAT(SUM(CASE WHEN header_rows_count > 0 THEN 1 ELSE 0 END), 0))
FROM metadata
WHERE header_rows_count IS NOT NULL;

SELECT CONCAT('Statements with Missing Days:        ',
    FORMAT(SUM(missing_days_detected), 0))
FROM summary
WHERE missing_days_detected IS NOT NULL;

SELECT CONCAT('Balance Match Success:               ',
    FORMAT(SUM(CASE WHEN balance_match = 'Success' THEN 1 ELSE 0 END), 0))
FROM summary;

SELECT CONCAT('Balance Match Failed:                ',
    FORMAT(SUM(CASE WHEN balance_match = 'Failed' THEN 1 ELSE 0 END), 0))
FROM summary;

SQL

# Add timestamp ranges
cat >> "$MANIFEST_FILE" <<EOF

Data Timeline:
--------------
EOF

mysql -h "${BACKUP_DB_HOST}" -P "${BACKUP_DB_PORT}" -u "${BACKUP_DB_USER}" -p"${BACKUP_DB_PASSWORD}" "${BACKUP_DB_NAME}" -N -B <<'SQL' >> "$MANIFEST_FILE" 2>/dev/null

SELECT CONCAT('Earliest Statement:  ', DATE_FORMAT(MIN(start_date), '%Y-%m-%d'))
FROM metadata
WHERE start_date IS NOT NULL;

SELECT CONCAT('Latest Statement:    ', DATE_FORMAT(MAX(end_date), '%Y-%m-%d'))
FROM metadata
WHERE end_date IS NOT NULL;

SELECT CONCAT('Most Recent Import:  ', DATE_FORMAT(MAX(created_at), '%Y-%m-%d %H:%i'))
FROM metadata;

SQL

# Add backup notes section
cat >> "$MANIFEST_FILE" <<EOF

================================================================================
BACKUP DESCRIPTION:
================================================================================

EOF

# Check if notes file exists (will be created by interactive prompt)
NOTES_FILE="$BACKUP_DIR/BACKUP_NOTES.txt"
if [ -f "$NOTES_FILE" ]; then
    cat "$NOTES_FILE" >> "$MANIFEST_FILE"
else
    echo "(No description provided)" >> "$MANIFEST_FILE"
fi

cat >> "$MANIFEST_FILE" <<EOF

================================================================================
End of Manifest
================================================================================
EOF

echo "✓ Manifest generated: $MANIFEST_FILE"

exit 0
