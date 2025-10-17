# Update unified_statements View - Instructions

## Summary

The `custom_verification` column has been added to the `summary` table and needs to be included in the `unified_statements` view.

## Special Logic

The view includes this logic for `custom_verification`:
```sql
CASE
    WHEN s.balance_match = 'Success' THEN 'NO_ISSUES'
    ELSE s.custom_verification
END AS custom_verification
```

This means:
- If balance matched successfully → Always show "NO_ISSUES"
- Otherwise → Show the metadata-based custom_verification value

## How to Apply

### Option 1: Using MySQL Command Line (Root User)

```bash
mysql -u root -p fraud_detection < migrations/add_custom_verification_to_unified_view.sql
```

### Option 2: Using Python with xtrabackup credentials

```bash
python3 -c "
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

# Load xtrabackup credentials (root user)
load_dotenv(Path('.env.xtrabackup'))

engine = create_engine(
    f\"mysql+pymysql://{os.getenv('BACKUP_DB_USER')}:{os.getenv('BACKUP_DB_PASSWORD')}@{os.getenv('BACKUP_DB_HOST')}:{os.getenv('BACKUP_DB_PORT')}/{os.getenv('BACKUP_DB_NAME')}\"
)

# Read SQL file
with open('migrations/add_custom_verification_to_unified_view.sql', 'r') as f:
    sql_content = f.read()

# Execute (simplified - just the CREATE OR REPLACE part)
with engine.connect() as conn:
    # Extract just the CREATE OR REPLACE VIEW statement
    start = sql_content.find('CREATE OR REPLACE VIEW')
    end = sql_content.find('ORDER BY m.created_at DESC;') + len('ORDER BY m.created_at DESC;')
    view_sql = sql_content[start:end]

    conn.execute(text(view_sql))
    conn.commit()
    print('✓ View updated successfully')
"
```

### Option 3: Manual SQL Execution

Connect as root user and paste the CREATE OR REPLACE VIEW statement from:
`migrations/add_custom_verification_to_unified_view.sql`

## Verification

After updating, verify the column is available:

```sql
-- Check column exists
DESCRIBE unified_statements;

-- Check custom_verification values
SELECT
    custom_verification,
    COUNT(*) as count
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
GROUP BY custom_verification;
```

Expected results:
- NO_ISSUES: Should be much higher (all successful balance matches + metadata-verified)
- FATAL: 233
- CRITICAL: 2
- NULL: Unclassified with failed balance matches

## Why Root/Admin Access is Needed

The `CREATE OR REPLACE VIEW` command internally performs a DROP VIEW, which requires elevated privileges. The standard `fraud_user` only has SELECT, INSERT, UPDATE privileges.

## Files

- **SQL Migration:** `migrations/add_custom_verification_to_unified_view.sql`
- **Full View with Customer Details:** `migrations/update_unified_view_with_customer_details.sql` (includes customer_details join - for future)
