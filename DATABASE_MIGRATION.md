# Database Migration Guide: Single Schema ’ Multi-Provider Schema

This guide explains how to migrate from the old single-table schema to the new multi-provider schema with provider-specific tables.

## Overview

**Old Schema (v1):**
- Single `raw_statements` table with `acc_prvdr_code` column
- Single `processed_statements` table with `acc_prvdr_code` column
- Shared `metadata` and `summary` tables

**New Schema (v2):**
- Provider-specific raw tables: `uatl_raw_statements`, `umtn_raw_statements`
- Provider-specific processed tables: `uatl_processed_statements`, `umtn_processed_statements`
- Shared `metadata` and `summary` tables (unchanged)
- SQL views for unified queries: `all_raw_statements`, `all_processed_statements`

## Why Migrate?

1. **Different Schemas**: UMTN has 5 extra columns (commission tracking, float balance) that UATL doesn't have
2. **Different Balance Fields**: UATL uses `balance`, UMTN uses `float_balance`
3. **Different File Formats**: UATL uses PDF, UMTN uses Excel/CSV
4. **Better Performance**: Provider-specific tables avoid NULL columns and improve query performance
5. **Easier Maintenance**: Adding new providers doesn't affect existing provider schemas

## Prerequisites

Before starting the migration:

1. **Backup your database**
   ```bash
   mysqldump -h localhost -P 3307 -u root -p fraud_detection > backup_$(date +%Y%m%d).sql
   ```

2. **Stop the application**
   ```bash
   # Stop FastAPI server if running
   pkill -f uvicorn
   ```

3. **Note your current data counts**
   ```sql
   SELECT acc_prvdr_code, COUNT(*) FROM raw_statements GROUP BY acc_prvdr_code;
   SELECT acc_prvdr_code, COUNT(*) FROM processed_statements GROUP BY acc_prvdr_code;
   ```

## Migration Steps

### Step 1: Create New Schema

Run the new schema SQL file:

```bash
mysql -h localhost -P 3307 -u root -p fraud_detection < backend/schema_v2_multitenancy.sql
```

This creates:
- `uatl_raw_statements` and `uatl_processed_statements`
- `umtn_raw_statements` and `umtn_processed_statements`
- SQL views `all_raw_statements` and `all_processed_statements`

Note: `metadata` and `summary` tables already exist and won't be recreated.

### Step 2: Migrate Existing Data (If Any)

If you have existing data in the old `raw_statements` or `processed_statements` tables, migrate it to the new provider-specific tables.

#### Option A: Migrate UATL Data Only (Recommended)

If you only have UATL data so far:

```sql
-- Migrate raw statements
INSERT INTO uatl_raw_statements (
    run_id, acc_number, txn_id, txn_date, txn_type, description,
    from_acc, to_acc, status, txn_direction, amount, fee, balance, pdf_format
)
SELECT
    run_id, acc_number, txn_id, txn_date, txn_type, description,
    from_acc, to_acc, status, txn_direction, amount, fee, balance, pdf_format
FROM raw_statements
WHERE acc_prvdr_code = 'UATL';

-- Migrate processed statements
INSERT INTO uatl_processed_statements (
    raw_id, run_id, acc_number, txn_id, txn_date, txn_type, description,
    status, amount, fee, balance, is_duplicate, is_special_txn, special_txn_type,
    calculated_running_balance, balance_diff, balance_diff_change_count
)
SELECT
    raw_id, run_id, acc_number, txn_id, txn_date, txn_type, description,
    status, amount, fee, balance, is_duplicate, is_special_txn, special_txn_type,
    calculated_running_balance, balance_diff, balance_diff_change_count
FROM processed_statements
WHERE acc_prvdr_code = 'UATL';
```

#### Option B: Fresh Start (Clean Slate)

If you prefer to start fresh (no existing data to migrate):

```sql
-- Drop old tables if they exist
DROP TABLE IF EXISTS processed_statements;
DROP TABLE IF EXISTS raw_statements;
```

Then you can upload all PDFs/Excel files again through the new multi-provider upload endpoint.

### Step 3: Verify Migration

```sql
-- Check record counts
SELECT 'UATL Raw', COUNT(*) FROM uatl_raw_statements
UNION ALL
SELECT 'UMTN Raw', COUNT(*) FROM umtn_raw_statements
UNION ALL
SELECT 'UATL Processed', COUNT(*) FROM uatl_processed_statements
UNION ALL
SELECT 'UMTN Processed', COUNT(*) FROM umtn_processed_statements
UNION ALL
SELECT 'Metadata', COUNT(*) FROM metadata
UNION ALL
SELECT 'Summary', COUNT(*) FROM summary;

-- Test unified views
SELECT acc_prvdr_code, COUNT(*) FROM all_raw_statements GROUP BY acc_prvdr_code;
SELECT acc_prvdr_code, COUNT(*) FROM all_processed_statements GROUP BY acc_prvdr_code;
```

### Step 4: Update Application Code

The application code has already been updated to use the new schema. Key changes:

1. **Upload Endpoint**: Now detects provider from file extension (.pdf = UATL, .xlsx/.csv = UMTN)
2. **CRUD Service**: Uses factory pattern to route to correct provider tables
3. **Processor Service**: Handles different balance fields per provider
4. **Export Service**: Queries all provider tables and combines results

No code changes needed - the migration is complete!

### Step 5: Start Application

```bash
cd backend
./start.sh
```

The application will now:
- Accept both PDF files (UATL) and Excel/CSV files (UMTN)
- Automatically route data to correct provider-specific tables
- Support all existing operations (upload, process, export, delete)

## Testing the Migration

### Test 1: Upload UATL PDF

```bash
# Upload an existing UATL PDF
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "files=@/path/to/statement.pdf"
```

Expected: File uploaded to `uatl_raw_statements`

### Test 2: Upload UMTN Excel

```bash
# Upload a UMTN Excel file
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "files=@/path/to/statement.xlsx"
```

Expected: File uploaded to `umtn_raw_statements` with commission fields

### Test 3: Process Statements

```bash
# Process both providers
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["run_1", "run_2"]}'
```

Expected: Both UATL and UMTN statements processed correctly

### Test 4: Export Combined Data

```bash
# Export all processed statements (both providers)
curl "http://localhost:8000/api/v1/download/processed?format=csv" \
  --output all_statements.csv
```

Expected: CSV contains data from both UATL and UMTN with `acc_prvdr_code` column

## Rollback Plan

If you need to rollback to the old schema:

1. **Restore from backup**
   ```bash
   mysql -h localhost -P 3307 -u root -p fraud_detection < backup_YYYYMMDD.sql
   ```

2. **Checkout old code version**
   ```bash
   git checkout <previous_commit_hash>
   ```

3. **Restart application**

## Provider-Specific Differences

### UATL (Airtel)
- **File Format**: PDF
- **Balance Field**: `balance`
- **Transaction Direction**: Explicit `txn_direction` column (Credit/Debit)
- **Extra Fields**: `pdf_format`

### UMTN (MTN)
- **File Format**: Excel/CSV
- **Balance Field**: `float_balance` (agent's float balance)
- **Transaction Direction**: Inferred from amount sign (positive=credit, negative=debit)
- **Extra Fields**:
  - `commission_amount`
  - `tax`
  - `commission_receiving_no`
  - `commission_balance`
  - `float_balance`

## Adding a New Provider

To add a new provider (e.g., UVOD for Vodafone):

1. **Create provider-specific models**
   ```python
   # backend/app/models/providers/uvod.py
   class UVODRawStatement(Base):
       __tablename__ = 'uvod_raw_statements'
       # Define provider-specific fields
   ```

2. **Register in factory**
   ```python
   # backend/app/services/provider_factory.py
   PROVIDERS = {
       'UATL': {...},
       'UMTN': {...},
       'UVOD': {
           'name': 'Vodafone Uganda',
           'raw_model': UVODRawStatement,
           'processed_model': UVODProcessedStatement,
           'balance_field': 'balance',
           'supports_commission': False,
       }
   }
   ```

3. **Create parser**
   ```python
   # backend/app/services/parsers/uvod_parser.py
   def parse_uvod_pdf(file_path: str, run_id: str):
       # Provider-specific parsing logic
       pass
   ```

4. **Update mapper.csv**
   Add provider code entries for new provider accounts

## FAQ

**Q: Can I keep both old and new tables?**
A: Yes, but the application will only use the new provider-specific tables. Old tables can be kept for reference.

**Q: What if I have mixed data (some UATL, some UMTN)?**
A: Migrate UATL data to `uatl_*` tables and UMTN data to `umtn_*` tables separately using the provider-specific migration queries.

**Q: Will old API endpoints still work?**
A: Yes! All API endpoints have been updated to work transparently with the new schema. The changes are backward compatible.

**Q: How do I identify which provider a run_id belongs to?**
A: Check the `metadata` table - the `acc_prvdr_code` column indicates the provider for each run_id.

**Q: Can I upload both PDF and Excel for the same account?**
A: No - each account should use only one provider format. Use the mapper.csv to specify the correct provider per account.

## Support

If you encounter issues during migration:

1. Check application logs: `backend/logs/app.log`
2. Verify database connectivity: `mysql -h localhost -P 3307 -u root -p fraud_detection`
3. Review the error message and check which provider's table is affected
4. Consult the factory pattern code: `backend/app/services/provider_factory.py`

## Summary

 **Completed Steps:**
1.  Created provider-specific models (UATL, UMTN)
2.  Implemented factory pattern for dynamic model routing
3.  Created provider-specific parsers (PDF for UATL, Excel for UMTN)
4.  Updated all services (CRUD, processor, export)
5.  Updated all API endpoints
6.  Created new database schema with views

**What You Get:**
- Support for multiple mobile money providers
- Provider-specific table structures
- Unified API that works across all providers
- Automatic provider detection from file format
- SQL views for cross-provider queries
- Easy addition of new providers via factory pattern
