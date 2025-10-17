# Customer Details Table - Quick Reference

## Summary

The `customer_details` table replaces `mapper.csv` as the source of customer and borrower information for statement requests. It provides comprehensive data from FLOW_API including borrower details, loan history, risk assessment, and KYC status.

## Quick Start

### 1. Table Already Created and Populated ✅

The table has been created with 22,638 records (70.2% with customer IDs).

### 2. Verify Table

```bash
python scripts/migration/populate_customer_details.py --verify-only
```

### 3. Test Integration

```python
from app.services.mapper import get_mapping_by_run_id

# This now automatically uses customer_details table
mapping = get_mapping_by_run_id('68e92f3cbd39c')
print(f"Customer ID: {mapping.get('cust_id')}")
print(f"Borrower: {mapping.get('borrower_biz_name')}")
```

### 4. Import Statements (Automatic)

```bash
# The import pipeline automatically uses customer_details table
python import_airtel_parallel.py --workers 4
```

## How It Works

### Data Flow

```
1. Import Pipeline calls enrich_metadata_with_mapper(metadata, run_id)
   ↓
2. mapper.py calls get_mapping_by_run_id(run_id)
   ↓
3. Tries customer_details table FIRST
   ↓
4. If not found, tries customer_details.get_customer_details_by_run_id()
   ↓
5. If still not found, falls back to mapper.csv
   ↓
6. Returns mapping with customer data
```

### For New Statements

If a run_id is not in the customer_details table:
1. Mapper service queries the table → NOT FOUND
2. Falls back to mapper.csv → Maybe found
3. For statements not in either source, you can manually trigger fetch:

```python
from app.services.customer_details import get_or_fetch_customer_details

# This will fetch from FLOW_API and store in customer_details table
details = get_or_fetch_customer_details('new_run_id', fetch_if_missing=True)
```

## Key Features

### Available Data (vs mapper.csv)

| Field | mapper.csv | customer_details |
|-------|-----------|------------------|
| run_id | ✅ | ✅ |
| acc_number | ✅ | ✅ |
| rm_name | ✅ | ✅ |
| acc_prvdr_code | ✅ | ✅ |
| cust_id | ❌ | ✅ |
| borrower_biz_name | ❌ | ✅ |
| tot_loans | ❌ | ✅ |
| tot_default_loans | ❌ | ✅ |
| risk_category | ❌ | ✅ |
| current_fa_limit | ❌ | ✅ |
| borrower_status | ❌ | ✅ |
| kyc_status | ❌ | ✅ |
| lead details | ❌ | ✅ |
| reassessment details | ❌ | ✅ |

### Automatic Fallback

The system is designed to gracefully degrade:
1. ✅ customer_details table (fastest, most complete)
2. ✅ mapper.csv (fallback, basic fields)
3. ✅ Parser data (last resort, minimal fields)

## Common Operations

### Check Coverage

```sql
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN cust_id IS NOT NULL THEN 1 ELSE 0 END) as with_cust_id,
    SUM(CASE WHEN borrower_id IS NOT NULL THEN 1 ELSE 0 END) as with_borrower
FROM customer_details;
```

### Find Statements Without Customer Details

```sql
SELECT m.run_id, m.acc_number, m.acc_prvdr_code
FROM metadata m
LEFT JOIN customer_details cd ON m.run_id = cd.run_id
WHERE cd.id IS NULL
LIMIT 100;
```

### Batch Fetch Missing Details

```python
from app.services.customer_details import batch_fetch_and_store

# Get run_ids without customer details
from sqlalchemy import create_engine, text
engine = get_fraud_db_engine()

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT m.run_id
        FROM metadata m
        LEFT JOIN customer_details cd ON m.run_id = cd.run_id
        WHERE cd.id IS NULL
        LIMIT 100
    """))
    run_ids = [row.run_id for row in result]

# Fetch and store
count = batch_fetch_and_store(run_ids)
print(f"Fetched {count} customer details from FLOW_API")
```

### Query Unified View with Borrower Details

**NOTE:** Requires applying the view update first (see below)

```sql
SELECT
    run_id,
    acc_number,
    status,
    borrower_biz_name,
    tot_loans,
    tot_default_loans,
    risk_category,
    current_fa_limit
FROM unified_statements
WHERE cust_id IS NOT NULL
    AND tot_loans > 10
ORDER BY tot_default_loans DESC
LIMIT 20;
```

## Pending Admin Action

### Update Unified View (Requires Admin Privileges)

The unified_statements view needs to be updated to include borrower details. This requires DROP VIEW permission:

```bash
# Using root or admin MySQL user
mysql -u root -p fraud_detection < migrations/update_unified_view_with_customer_details.sql
```

Or update .env temporarily with admin credentials and run:
```bash
python scripts/migration/update_unified_view.py
```

## Troubleshooting

### Mapper service returning None

Check if table has data:
```bash
python scripts/migration/populate_customer_details.py --verify-only
```

### Customer details not fetching from FLOW_API

Check FLOW_DB_* credentials in .env:
```bash
python scripts/analysis/export_customer_details.py --analyze-only
```

### Want to disable customer_details table temporarily

Edit `app/services/mapper.py`:
```python
USE_CUSTOMER_DETAILS_TABLE = False  # Change True to False
```

## Files Reference

- **Table schema:** `migrations/create_customer_details_table.sql`
- **Population script:** `scripts/migration/populate_customer_details.py`
- **Service module:** `app/services/customer_details.py`
- **Mapper integration:** `app/services/mapper.py`
- **View update:** `migrations/update_unified_view_with_customer_details.sql`
- **Full documentation:** `docs/CUSTOMER_DETAILS_MIGRATION.md`

## Statistics

- **Total records:** 22,638
- **With cust_id:** 15,881 (70.2%)
- **With borrower_id:** 15,626 (69.0%)
- **UATL:** 13,579 (60.0%)
- **UMTN:** 9,059 (40.0%)

## Support

For detailed migration information, see `docs/CUSTOMER_DETAILS_MIGRATION.md`
