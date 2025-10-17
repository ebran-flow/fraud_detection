# Customer Details Migration

## Overview

This document describes the migration from mapper.csv to the customer_details table for managing customer and borrower information linked to statement requests.

## What Was Done

### 1. Created customer_details Table

**File:** `migrations/create_customer_details_table.sql`

The table includes:
- Statement request identifiers (run_id, stmt_request_id)
- Account information (acc_number, alt_acc_num, acc_prvdr_code)
- RM who created the request
- Entity chain resolution (direct_entity → customer_statement → final_entity)
- Customer ID (cust_id) linking to borrowers
- Lead details (if entity is lead)
- Reassessment details (if entity is reassessment_result)
- Borrower details (business name, loans, limits, risk, status, KYC, etc.)
- Relationship managers (registered RM, current RM)

**Status:** ✅ Table created and populated with 22,638 records (70.2% with cust_id, 69.0% with borrower details)

### 2. Created Population Script

**File:** `scripts/migration/populate_customer_details.py`

Features:
- Reads customer_details_full.csv export
- Converts pandas values to database-compatible formats
- Batch insertion with REPLACE INTO for handling duplicates
- Verification and statistics reporting

**Usage:**
```bash
python scripts/migration/populate_customer_details.py
python scripts/migration/populate_customer_details.py --csv-file custom_export.csv
python scripts/migration/populate_customer_details.py --verify-only
```

**Status:** ✅ Successfully populated 22,638 records

### 3. Created Customer Details Service

**File:** `app/services/customer_details.py`

Features:
- `get_customer_details_by_run_id()` - Fetch from local table
- `fetch_customer_details_from_flow_api()` - Fetch from FLOW_API database
- `store_customer_details()` - Store in local table
- `get_or_fetch_customer_details()` - Main function: local first, fetch if missing
- `enrich_metadata_with_customer_details()` - Replaces `enrich_metadata_with_mapper()`

**Status:** ✅ Implemented and integrated

### 4. Updated Mapper Service

**File:** `app/services/mapper.py`

Changes:
- Added `USE_CUSTOMER_DETAILS_TABLE` flag (default: True)
- `get_mapping_by_run_id()` now tries customer_details table first, then falls back to CSV
- `enrich_metadata_with_mapper()` now adds `cust_id` to metadata if available
- Returns additional fields from customer_details (cust_id, borrower_biz_name)
- Handles both date and datetime objects for created_date
- Seamless fallback to mapper.csv if table query fails

**Status:** ✅ Updated with automatic fallback

### 5. Updated Import Pipeline

**File:** `import_airtel_parallel.py`

Changes:
- Simplified to just use `enrich_metadata_with_mapper()`
- No need to explicitly call customer_details service (handled by mapper)
- Automatic fetch from customer_details table
- Automatic fallback to mapper.csv if needed

**Status:** ✅ Simplified and streamlined

### 6. Updated Unified View

**File:** `migrations/update_unified_view_with_customer_details.sql`

Adds customer and borrower columns to unified_statements view:

**Customer identification:**
- cust_id
- final_entity_type
- final_entity_id

**Lead information:**
- lead_id, lead_mobile, lead_biz_name
- lead_first_name, lead_last_name
- lead_location, lead_territory
- lead_status, lead_type, lead_date

**Reassessment information:**
- reassessment_id
- reassessment_status, reassessment_type

**Borrower information:**
- borrower_id, borrower_biz_name, borrower_reg_date
- tot_loans, tot_default_loans
- current_fa_limit, previous_fa_limit
- borrower_kyc_status, borrower_activity_status
- borrower_profile_status, borrower_fa_status
- borrower_status, risk_category

**RM information:**
- registered_rm_name
- current_rm_name

**Account information:**
- account_holder_name
- acc_ownership

**Status:** ⚠️ SQL file created, but needs admin privileges to apply (DROP VIEW permission required)

## What Needs Admin Action

### Apply Unified View Update

The `fraud_user` database user doesn't have `DROP VIEW` permission. You need to run this with admin credentials:

```bash
mysql -u root -p -h localhost fraud_detection < migrations/update_unified_view_with_customer_details.sql
```

Or using a script:
```bash
python scripts/migration/update_unified_view.py
```

Make sure to use admin credentials in `.env` temporarily or run with root MySQL user.

## Migration Benefits

### Before (mapper.csv):
- ❌ Limited to basic fields (run_id, acc_number, rm_name, provider, status)
- ❌ No customer/borrower context
- ❌ No loan history or risk information
- ❌ CSV file requires manual updates
- ❌ No automatic sync with FLOW_API

### After (customer_details table):
- ✅ Comprehensive customer and borrower information
- ✅ Loan history (tot_loans, tot_default_loans)
- ✅ Risk assessment (risk_category, borrower_status)
- ✅ KYC and FA status
- ✅ Current and previous limits
- ✅ Automatic fetch from FLOW_API for new statements
- ✅ Available in unified_statements view for easy querying
- ✅ Full entity chain resolution (customer_statement → lead/reassessment → borrower)

## Usage Examples

### 1. Query Flagged Statements with Borrower Context

```sql
SELECT
    run_id,
    acc_number,
    status,
    verification_status,
    -- Borrower context
    borrower_biz_name,
    tot_loans,
    tot_default_loans,
    risk_category,
    current_fa_limit,
    borrower_status,
    -- Quality metrics
    duplicate_count,
    quality_issues_count
FROM unified_statements
WHERE status IN ('FLAGGED', 'VERIFICATION_FAILED')
    AND cust_id IS NOT NULL
ORDER BY tot_default_loans DESC, risk_category DESC
LIMIT 20;
```

### 2. Get Customer Details Programmatically

```python
from app.services.customer_details import get_or_fetch_customer_details

# Get details for a run_id (fetches from FLOW_API if not in local table)
details = get_or_fetch_customer_details('68e92f3cbd39c')

print(f"Customer ID: {details['cust_id']}")
print(f"Business: {details['borrower_biz_name']}")
print(f"Total Loans: {details['tot_loans']}")
print(f"Risk: {details['risk_category']}")
```

### 3. Enrich Metadata During Import

```python
from app.services.customer_details import enrich_metadata_with_customer_details

# This automatically happens in import_airtel_parallel.py
metadata = enrich_metadata_with_customer_details(metadata, run_id)
```

## Statistics

**Current Coverage (as of 2025-10-17):**
- Total statements: 22,638
- With cust_id: 15,881 (70.2%)
- With borrower_id: 15,626 (69.0%)
- UATL: 13,579 (60.0%)
- UMTN: 9,059 (40.0%)

**Entity Distribution:**
- Direct entities: lead (54.4%), reassessment_result (31.3%), customer_statement (14.4%)
- Final entities: lead (63.7%), reassessment_result (36.3%)

## Files Created/Modified

### New Files:
1. `migrations/create_customer_details_table.sql` - Table schema
2. `migrations/update_unified_view_with_customer_details.sql` - Updated view
3. `scripts/migration/populate_customer_details.py` - Population script
4. `scripts/migration/update_unified_view.py` - View update script
5. `app/services/customer_details.py` - Customer details service
6. `docs/CUSTOMER_DETAILS_MIGRATION.md` - This document

### Modified Files:
1. `import_airtel_parallel.py` - Simplified to use mapper service only
2. `app/services/mapper.py` - Updated to use customer_details table as primary source

### Existing Files (No Change Required):
1. `docs/data/statements/mapper.csv` - Automatically used as fallback if table query fails

## Next Steps

1. **Apply unified view update** (requires admin privileges)
   ```bash
   mysql -u root -p fraud_detection < migrations/update_unified_view_with_customer_details.sql
   ```

2. **Test unified view** with borrower details:
   ```bash
   mysql -u fraud_user -p fraud_detection -e "SELECT run_id, borrower_biz_name, tot_loans, risk_category FROM unified_statements WHERE cust_id IS NOT NULL LIMIT 5;"
   ```

3. **Test import pipeline** with new customer_details integration:
   ```bash
   python import_airtel_parallel.py --workers 4 --dry-run
   ```

4. **Develop flagging logic** using the new borrower metrics from `docs/FLAGGING_METRICS.md`

5. **Optional:** Archive mapper.csv once fully migrated and tested

## Rollback Plan

If issues arise:

1. **Keep using mapper.csv:** The import pipeline has a fallback to mapper.csv
2. **Remove customer_details enrichment:** Comment out line in `import_airtel_parallel.py`:
   ```python
   # metadata = enrich_metadata_with_customer_details(metadata, run_id)
   ```
3. **Restore original unified view:** Run `migrations/update_unified_view_comprehensive.sql`

## Support

For questions or issues:
- Check logs: `import_airtel_parallel.log`
- Verify table: `python scripts/migration/populate_customer_details.py --verify-only`
- Test FLOW_API connection: `python scripts/analysis/export_customer_details.py --analyze-only`
