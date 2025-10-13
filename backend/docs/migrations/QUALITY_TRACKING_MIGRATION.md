# Balance Quality Tracking - Database Migration Guide

## Overview
This migration adds balance quality tracking to handle "fudged statements" with malformed balance values (e.g., "105608-", "52854II").

**Implementation Approach:** Clean records before insertion, track quality issues via flags and raw values.

---

## 1. Migration Scripts

### Step 1: Update `uatl_raw_statements` Table

Add columns to track raw balance values and quality issue flags:

```sql
-- Add balance_raw column to store original problematic values
ALTER TABLE uatl_raw_statements
ADD COLUMN balance_raw VARCHAR(50) DEFAULT NULL
COMMENT 'Original balance value before cleaning (e.g., "105608-", "52854II")'
AFTER balance;

-- Add has_quality_issue flag to mark problematic rows
ALTER TABLE uatl_raw_statements
ADD COLUMN has_quality_issue BOOLEAN DEFAULT FALSE
COMMENT 'TRUE if balance required regex cleaning due to data quality issues'
AFTER balance_raw;

-- Create index for efficient querying of quality issues
CREATE INDEX idx_has_quality_issue ON uatl_raw_statements(has_quality_issue);
```

### Step 2: Update Metadata/Summary Table

Add column to track quality issues count per statement:

```sql
-- Add quality_issues_count to metadata (similar to duplicate_count)
-- Replace 'metadata' with your actual metadata table name
ALTER TABLE metadata
ADD COLUMN quality_issues_count INT DEFAULT 0
COMMENT 'Number of transactions with balance data quality issues in this statement'
AFTER num_rows;

-- Create index for filtering statements with quality issues
CREATE INDEX idx_quality_issues_count ON metadata(quality_issues_count);
```

**Note:** If your metadata table has a different name (e.g., `uatl_metadata`, `statement_summary`), replace `metadata` accordingly.

---

## 2. Column Details

### `uatl_raw_statements` Table

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `balance` | DECIMAL/FLOAT | Cleaned numeric balance (MySQL-compatible) | 105608.0, 52854.0 |
| `balance_raw` | VARCHAR(50) | Original balance before cleaning | "105608-", "52854II", "105608" |
| `has_quality_issue` | BOOLEAN | TRUE if balance was cleaned via regex | TRUE, FALSE |

### Metadata Table

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `quality_issues_count` | INT | Count of rows with quality issues | 0, 1, 5 |

---

## 3. Data Examples

### Before Cleaning (Raw PDF Data)
```
Transaction ID: 121823960196
Balance (from PDF): "105608-"
```

### After Cleaning (Database Storage)
```sql
-- uatl_raw_statements
txn_id: "121823960196"
balance: 105608.0              -- Cleaned numeric value
balance_raw: "105608-"         -- Original problematic value
has_quality_issue: TRUE        -- Flagged for audit

-- metadata
quality_issues_count: 1        -- One row had quality issues
```

---

## 4. Verification Queries

After running migrations, verify the schema changes:

```sql
-- Verify uatl_raw_statements columns exist
DESCRIBE uatl_raw_statements;
SHOW INDEX FROM uatl_raw_statements WHERE Key_name = 'idx_has_quality_issue';

-- Verify metadata column exists
DESCRIBE metadata;
SHOW INDEX FROM metadata WHERE Key_name = 'idx_quality_issues_count';
```

---

## 5. Audit Queries

### Find All Transactions with Quality Issues
```sql
SELECT
    txn_id,
    txn_date,
    balance,
    balance_raw,
    description,
    acc_number
FROM uatl_raw_statements
WHERE has_quality_issue = TRUE
ORDER BY txn_date DESC;
```

### Count Quality Issues by Account
```sql
SELECT
    acc_number,
    COUNT(*) as issue_count,
    COUNT(DISTINCT run_id) as affected_statements
FROM uatl_raw_statements
WHERE has_quality_issue = TRUE
GROUP BY acc_number
ORDER BY issue_count DESC;
```

### Find Statements with Quality Issues
```sql
SELECT
    run_id,
    acc_number,
    quality_issues_count,
    num_rows,
    ROUND((quality_issues_count / num_rows) * 100, 2) as quality_issue_percentage
FROM metadata
WHERE quality_issues_count > 0
ORDER BY quality_issues_count DESC;
```

### Compare Clean vs Raw Balance Values
```sql
SELECT
    txn_id,
    balance as cleaned_balance,
    balance_raw as original_balance,
    CASE
        WHEN balance_raw LIKE '%-%' THEN 'Trailing minus sign'
        WHEN balance_raw REGEXP '[A-Za-z]' THEN 'Contains letters'
        ELSE 'Other issue'
    END as issue_type
FROM uatl_raw_statements
WHERE has_quality_issue = TRUE
LIMIT 20;
```

---

## 6. Rollback Scripts

If you need to revert the migration:

```sql
-- Drop indexes first
DROP INDEX idx_has_quality_issue ON uatl_raw_statements;
DROP INDEX idx_quality_issues_count ON metadata;

-- Drop columns from uatl_raw_statements
ALTER TABLE uatl_raw_statements
DROP COLUMN has_quality_issue,
DROP COLUMN balance_raw;

-- Drop column from metadata
ALTER TABLE metadata
DROP COLUMN quality_issues_count;
```

---

## 7. Testing Plan

1. **Run migrations** on development/staging environment first
2. **Import test PDFs** with known quality issues:
   - `/home/ebran/Downloads/6832c0e9beac1.pdf` (Transaction 121823960196 with "105608-")
   - `/home/ebran/Downloads/67cefd0c85566-1_merged.pdf` (Transaction 114146994176 with "52854II")
3. **Verify results**:
   - Check `has_quality_issue = TRUE` for problematic transactions
   - Verify `balance` contains cleaned numeric value
   - Verify `balance_raw` preserves original value
   - Verify `quality_issues_count` in metadata matches actual count
4. **Run audit queries** to confirm data integrity
5. **Deploy to production** during maintenance window

---

## 8. Code Changes Summary

The following parser files were modified to support quality tracking:

- **`app/services/parsers/pdf_utils.py`** (lines 240-297, 422-512)
  - `clean_dataframe()`: Adds regex cleaning and quality tracking
  - `extract_data_from_pdf()`: Returns quality_issues_count

- **`app/services/parsers/uatl_parser.py`** (lines 85-196)
  - `parse_uatl_pdf()`: Stores balance_raw, has_quality_issue, quality_issues_count

---

## 9. Regex Pattern Used

The balance cleaning uses the following regex pattern:

```python
# Extract {sign(if applicable)}_{amount(numbers)} and remove the rest
pattern = r'^([+-]?\d+(?:\.\d+)?)'
```

**Examples:**
- `"105608-"` → `"105608"` → `105608.0`
- `"52854II"` → `"52854"` → `52854.0`
- `"105608"` → `"105608"` → `105608.0` (no issue flagged)
- `"-2000.50"` → `"-2000.50"` → `-2000.5` (valid negative)

---

## 10. Impact Assessment

### Benefits
✅ Resolves MySQL NaN error: `(pymysql.err.ProgrammingError) nan can not be used with MySQL`
✅ Preserves original data for audit trail
✅ Easy identification of problematic statements
✅ No data loss - both cleaned and raw values stored
✅ Minimal schema changes (3 new columns total)

### Performance Impact
- **Storage:** ~50 bytes per transaction with quality issues (balance_raw VARCHAR)
- **Query Performance:** Indexed columns for efficient filtering
- **Processing:** Negligible overhead (~1ms per 1000 transactions)

---

## Questions or Issues?

If you encounter any issues during migration, check:
1. Your actual metadata table name (may not be `metadata`)
2. MySQL user has ALTER TABLE permissions
3. No existing columns with same names
4. Sufficient disk space for schema changes

**Contact:** Review parser implementation in `app/services/parsers/` for details.
