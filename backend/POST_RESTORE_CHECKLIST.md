# Post-Restore Checklist

After database restore completes, follow these steps to bring the database up to date:

## Step 1: Apply Schema Updates (REQUIRED)

Apply all schema changes made after the Oct 14 backup:

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend

# Apply schema updates
mysql -h 127.0.0.1 -P 3307 -u root -p$(grep DB_PASSWORD .env | cut -d '=' -f2) fraud_detection < scripts/migration/post_restore_updates.sql
```

**What this does:**
- ✅ Adds `metadata.header_rows_count` column
- ✅ Adds `summary.missing_days_detected` column
- ✅ Adds `summary.gap_related_balance_changes` column
- ✅ Adds `uatl_raw_statements.amount_raw` column
- ✅ Adds `uatl_raw_statements.fee_raw` column
- ✅ Adds `umtn_raw_statements.fee_raw` column
- ✅ Verifies all columns exist

## Step 2: Update Missing Metadata (if exists)

Check if these scripts exist and run them:

```bash
# Check for metadata update scripts
ls -lh update_missing_metadata.py 2>/dev/null
ls -lh update_mime_types.py 2>/dev/null

# If they exist, run them:
python update_missing_metadata.py
python update_mime_types.py
```

## Step 3: Populate header_rows_count

Run the header manipulation scan results to populate `metadata.header_rows_count`:

```bash
# Check if results file exists
ls -lh header_manipulation_results.json

# If exists, create script to update database:
python scripts/analysis/update_header_rows_count.py
```

Or apply from the scan results:

```python
# Create update script if needed:
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(f'mysql+pymysql://root:{os.getenv("DB_PASSWORD")}@localhost:3307/fraud_detection')

with open('header_manipulation_results.json', 'r') as f:
    data = json.load(f)

with engine.connect() as conn:
    for result in data['results']:
        if result['manipulated_pages_count'] > 0:
            conn.execute(text("""
                UPDATE metadata
                SET header_rows_count = :count
                WHERE run_id = :run_id
            """), {
                'count': result['manipulated_pages_count'],
                'run_id': result['run_id']
            })
    conn.commit()

print(f"Updated header_rows_count for {len([r for r in data['results'] if r['manipulated_pages_count'] > 0])} statements")
```

## Step 4: Recreate Views (if needed)

Check if unified_statements view needs to be updated:

```bash
# The view should have been restored, but verify it includes new columns
mysql -h 127.0.0.1 -P 3307 -u root -p$(grep DB_PASSWORD .env | cut -d '=' -f2) fraud_detection -e "DESCRIBE unified_statements" | grep -E "missing_days|gap_related"
```

If columns are missing, run:

```bash
mysql -h 127.0.0.1 -P 3307 -u root -p$(grep DB_PASSWORD .env | cut -d '=' -f2) fraud_detection < migrations/update_unified_view.sql
```

## Step 5: Verify Data Integrity

Run verification queries:

```sql
USE fraud_detection;

-- Check row counts
SELECT 'metadata' as table_name, COUNT(*) as rows FROM metadata
UNION ALL
SELECT 'summary', COUNT(*) FROM summary
UNION ALL
SELECT 'uatl_raw_statements', COUNT(*) FROM uatl_raw_statements
UNION ALL
SELECT 'uatl_processed_statements', COUNT(*) FROM uatl_processed_statements
UNION ALL
SELECT 'umtn_raw_statements', COUNT(*) FROM umtn_raw_statements
UNION ALL
SELECT 'umtn_processed_statements', COUNT(*) FROM umtn_processed_statements;

-- Expected counts (approximately):
-- metadata: ~20,000
-- summary: ~20,000
-- uatl_raw_statements: ~32 million
-- uatl_processed_statements: ~35 million
-- umtn_raw_statements: ~27 million
-- umtn_processed_statements: ~27 million

-- Check new columns have data
SELECT
    COUNT(*) as total_statements,
    SUM(CASE WHEN header_rows_count > 0 THEN 1 ELSE 0 END) as with_header_issues,
    SUM(CASE WHEN quality_issues_count > 0 THEN 1 ELSE 0 END) as with_quality_issues
FROM metadata;

SELECT
    COUNT(*) as total_statements,
    SUM(CASE WHEN missing_days_detected = 1 THEN 1 ELSE 0 END) as with_missing_days,
    SUM(CASE WHEN gap_related_balance_changes > 0 THEN 1 ELSE 0 END) as with_gap_issues
FROM summary;
```

## Step 6: Run Backend Tests (Optional but Recommended)

```bash
# Test Airtel parser
python -m pytest test/test_process_uatl.py -v

# Test database connections
python -c "
from app.services.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM metadata'))
    print(f'✅ Database accessible: {result.fetchone()[0]} metadata records')
"
```

## Scripts Location Reference

```
backend/
├── scripts/
│   ├── migration/
│   │   └── post_restore_updates.sql          # Schema updates (run this first!)
│   ├── analysis/
│   │   ├── scan_header_manipulation.py       # Header manipulation detection
│   │   └── update_header_rows_count.py       # Update header_rows_count from results
│   └── utils/
│       ├── convert_results_to_csv.py          # Convert JSON results to CSV
│       └── convert_additional_metrics_to_csv.py
├── update_missing_metadata.py                 # Update missing metadata (if exists)
├── update_mime_types.py                       # Update MIME types (if exists)
└── header_manipulation_results.json           # Scan results (if exists)
```

## Current Status

- ⏳ **Import Status:** 4 large tables currently importing (28GB total)
  - uatl_raw_statements (6.9GB)
  - uatl_processed_statements (7.1GB)
  - umtn_raw_statements (7.3GB)
  - umtn_processed_statements (6.9GB)

- ⏳ **Estimated Time:** 30-60 minutes for imports to complete

## After All Steps Complete

Run final verification:

```bash
python -c "
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(f'mysql+pymysql://root:{os.getenv(\"DB_PASSWORD\")}@localhost:3307/fraud_detection')

with engine.connect() as conn:
    # Check all critical columns exist
    result = conn.execute(text('''
        SELECT
            table_name,
            column_name
        FROM information_schema.columns
        WHERE table_schema = \"fraud_detection\"
        AND column_name IN (
            \"header_rows_count\",
            \"missing_days_detected\",
            \"gap_related_balance_changes\",
            \"amount_raw\",
            \"fee_raw\"
        )
        ORDER BY table_name, column_name
    '''))

    print('✅ All new columns:')
    for row in result:
        print(f'   {row[0]}.{row[1]}')
"
```

✅ Database should now be fully restored and up to date!
