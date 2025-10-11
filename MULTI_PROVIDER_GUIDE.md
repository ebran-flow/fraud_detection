# Multi-Provider Architecture Guide

## Overview

The system uses a **single-table approach** for multiple providers (UATL, UMTN, etc.) instead of separate tables. This is the industry-standard pattern for scalable multi-tenant/multi-provider systems.

## Schema Design

### ✅ Current Approach: Single Tables + Provider Column

```sql
-- All providers share the same tables
raw_statements
  - acc_prvdr_code: 'UATL' | 'UMTN' | 'UMTN2' | etc.
  - acc_number
  - txn_id
  ...

processed_statements
  - acc_prvdr_code: 'UATL' | 'UMTN' | etc.
  - acc_number
  ...

metadata
  - acc_prvdr_code: 'UATL' | 'UMTN' | etc.
  ...

summary
  - acc_prvdr_code: 'UATL' | 'UMTN' | etc.
  ...
```

### Performance Optimization

Indexes are created on `acc_prvdr_code` for fast filtering:
```sql
INDEX idx_provider (acc_prvdr_code)
INDEX idx_provider_acc (acc_prvdr_code, acc_number)
```

## Adding New Providers

### Step 1: Add to mapper.csv

```csv
run_id,acc_number,alt_acc_num,acc_prvdr_code,status,object_key,lambda_status,rm_id,rm_name,created_date
68babf7f23139,256706015809,,UMTN,success,UMTN/68babf7f23139,score_calc_success,9252,EBRAN BRIGHT,2023-05-31
```

**That's it!** No code changes needed. The system will automatically:
1. Read provider code from mapper
2. Store in `acc_prvdr_code` column
3. Process transactions correctly

### Step 2: (Optional) Handle Provider-Specific Logic

If UMTN has different PDF formats or business rules:

```python
# backend/app/services/parser.py
def parse_pdf_file(pdf_path: str, run_id: str, provider_code: str = 'UATL'):
    """Parse PDF with provider-specific logic"""

    if provider_code == 'UMTN':
        # UMTN-specific parsing if needed
        df, acc_number = extract_umtn_data(pdf_path)
    else:
        # Default UATL parsing
        df, acc_number = extract_data_from_pdf(pdf_path)

    # Rest of processing...
```

## Filtering by Provider

### In API

**Get UATL statements only:**
```bash
curl "http://localhost:8000/api/v1/list?acc_prvdr_code=UATL"
```

**Get UMTN statements only:**
```bash
curl "http://localhost:8000/api/v1/list?acc_prvdr_code=UMTN"
```

**Download UATL processed statements:**
```bash
curl "http://localhost:8000/api/v1/download/processed?acc_prvdr_code=UATL" -o uatl_processed.csv
```

### In Database

**Query UATL transactions:**
```sql
SELECT * FROM raw_statements WHERE acc_prvdr_code = 'UATL';
```

**Query UMTN transactions:**
```sql
SELECT * FROM raw_statements WHERE acc_prvdr_code = 'UMTN';
```

**Compare providers:**
```sql
SELECT
    acc_prvdr_code,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN is_duplicate THEN 1 ELSE 0 END) as duplicates
FROM processed_statements
GROUP BY acc_prvdr_code;
```

### In Code (CRUD Service)

The CRUD service already supports provider filtering:

```python
from backend.app.services.crud import list_metadata_with_pagination

# Filter by provider
metadata_list, total = list_metadata_with_pagination(
    db,
    page=1,
    page_size=50,
    filters={'acc_prvdr_code': 'UMTN'}
)
```

## Cross-Provider Analytics

One of the major benefits of single-table design:

```sql
-- Compare fraud rates across providers
SELECT
    acc_prvdr_code as provider,
    COUNT(DISTINCT run_id) as total_statements,
    SUM(duplicate_count) as total_duplicates,
    AVG(balance_diff_change_ratio) as avg_fraud_score,
    SUM(CASE WHEN balance_match = 'Failed' THEN 1 ELSE 0 END) as failed_verifications
FROM summary
GROUP BY acc_prvdr_code;
```

```sql
-- Find accounts with both UATL and UMTN statements
SELECT
    acc_number,
    GROUP_CONCAT(DISTINCT acc_prvdr_code) as providers,
    COUNT(*) as statement_count
FROM metadata
GROUP BY acc_number
HAVING COUNT(DISTINCT acc_prvdr_code) > 1;
```

## Web UI Provider Filter

The web interface can be enhanced to filter by provider:

```html
<!-- Add provider filter dropdown -->
<select id="provider-filter" onchange="filterByProvider(this.value)">
    <option value="">All Providers</option>
    <option value="UATL">UATL - Airtel</option>
    <option value="UMTN">UMTN - MTN</option>
</select>

<script>
function filterByProvider(provider) {
    const url = provider
        ? `/api/v1/ui/statements-table?page=1&page_size=50&acc_prvdr_code=${provider}`
        : `/api/v1/ui/statements-table?page=1&page_size=50`;

    htmx.ajax('GET', url, {target: '#statements-table'});
}
</script>
```

## Provider-Specific Business Rules

### Format Detection

Both UATL and UMTN may have multiple formats. The existing logic handles this:

```python
# In process_statements.py - already supports Format 1 & 2
pdf_format = detect_pdf_format(page)  # Returns 1 or 2

if pdf_format == 1:
    # Format 1 logic (Credit/Debit column)
elif pdf_format == 2:
    # Format 2 logic (signed amounts)
```

### Special Transactions

Provider-specific special transaction detection:

```python
def detect_special_transactions(df: pd.DataFrame, provider_code: str) -> pd.DataFrame:
    """Detect special transactions with provider-specific rules"""

    df['is_special_txn'] = False
    df['special_txn_type'] = None

    if provider_code == 'UATL':
        # UATL-specific special transactions
        commission_mask = df['description'].str.contains('Commission', case=False, na=False)
        df.loc[commission_mask, 'is_special_txn'] = True
        df.loc[commission_mask, 'special_txn_type'] = 'Commission Disbursement'

    elif provider_code == 'UMTN':
        # UMTN-specific special transactions
        bundle_mask = df['description'].str.contains('Bundle', case=False, na=False)
        df.loc[bundle_mask, 'is_special_txn'] = True
        df.loc[bundle_mask, 'special_txn_type'] = 'Bundle Purchase'

    return df
```

## Migration Path

If you already have UATL data and want to add UMTN:

```sql
-- Step 1: Ensure all existing data has provider code
UPDATE raw_statements SET acc_prvdr_code = 'UATL' WHERE acc_prvdr_code IS NULL;
UPDATE processed_statements SET acc_prvdr_code = 'UATL' WHERE acc_prvdr_code IS NULL;
UPDATE metadata SET acc_prvdr_code = 'UATL' WHERE acc_prvdr_code IS NULL;
UPDATE summary SET acc_prvdr_code = 'UATL' WHERE acc_prvdr_code IS NULL;

-- Step 2: Add UMTN data via normal upload process
-- No additional steps needed!
```

## Why NOT Separate Tables?

### ❌ Separate Tables Approach (Don't do this)
```
uatl_raw_statements
uatl_processed_statements
umtn_raw_statements
umtn_processed_statements
```

**Problems:**
1. **Code Duplication**: Need separate models, services, endpoints for each provider
2. **Hard to Scale**: Adding provider #3 = 4 more tables + duplicate code
3. **Cross-Provider Queries**: Nightmare with UNION queries
4. **Maintenance**: Schema changes must be applied to ALL tables
5. **Reports**: Very difficult to generate unified reports
6. **Testing**: Must test each provider's code paths separately

### ✅ Single Table Approach (Current)
```
raw_statements (with acc_prvdr_code column)
processed_statements (with acc_prvdr_code column)
```

**Benefits:**
1. **Single Codebase**: One set of models/services handles all providers
2. **Easy to Scale**: Adding providers = just insert data
3. **Simple Queries**: `WHERE acc_prvdr_code = 'UMTN'`
4. **Easy Maintenance**: One schema change applies to all
5. **Unified Reports**: Natural cross-provider analytics
6. **Standard Pattern**: Industry best practice

## Performance Considerations

### Query Performance
With proper indexes, filtering by provider is very fast:
```sql
-- This uses idx_provider index - very fast
SELECT * FROM raw_statements WHERE acc_prvdr_code = 'UMTN';

-- This uses idx_provider_acc composite index - even faster
SELECT * FROM raw_statements
WHERE acc_prvdr_code = 'UMTN' AND acc_number = '256706015809';
```

### Table Partitioning (Optional for Large Scale)

If you reach millions of records, use MySQL partitioning:
```sql
ALTER TABLE raw_statements
PARTITION BY LIST COLUMNS(acc_prvdr_code) (
    PARTITION p_uatl VALUES IN ('UATL'),
    PARTITION p_umtn VALUES IN ('UMTN'),
    PARTITION p_other VALUES IN (NULL)
);
```

This gives you:
- Performance benefits of separate tables
- Simplicity of single table
- No code changes needed

## Summary

| Feature | Single Table | Separate Tables |
|---------|-------------|-----------------|
| Add new provider | ✅ No code changes | ❌ New tables + code |
| Cross-provider analytics | ✅ Simple SQL | ❌ Complex UNIONs |
| Code maintenance | ✅ DRY | ❌ Duplicated |
| Query performance | ✅ With indexes | ✅ Native |
| Scalability | ✅ Excellent | ❌ Poor |
| Industry standard | ✅ Yes | ❌ Anti-pattern |

**Recommendation: Use single-table approach (current implementation)**
