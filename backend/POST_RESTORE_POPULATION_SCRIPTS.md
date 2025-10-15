# Scripts to Populate Missing Columns After Restore

After restoring the database from Oct 14 backups, the following columns need to be populated with data:

## Overview of Missing Columns

| Column | Table | Purpose | Population Script |
|--------|-------|---------|-------------------|
| `header_rows_count` | metadata | Number of header rows found in PDF (manipulation detection) | Multiple scripts available |
| `missing_days_detected` | summary | Flag for date gaps in statements | Populated during processing |
| `gap_related_balance_changes` | summary | Balance changes during gaps | Populated during processing |
| `amount_raw` | uatl_raw_statements | Original amount before cleaning | Populated during import |
| `fee_raw` | uatl_raw_statements | Original fee before cleaning | Populated during import |
| `fee_raw` | umtn_raw_statements | Original fee before cleaning | Populated during import |

---

## 1. Header Row Count Scripts

These scripts scan PDFs and populate `metadata.header_rows_count`:

### A. scan_header_manipulation.py
**Location:** `scripts/analysis/scan_header_manipulation.py`

**Purpose:** Comprehensive scan of all Airtel Format 2 PDFs for header manipulation

**Usage:**
```bash
python scripts/analysis/scan_header_manipulation.py
```

**What it does:**
- Scans all Airtel Format 2 statements
- Detects header rows embedded in transaction data
- Outputs results to `header_manipulation_results.json`
- Use this to identify statements requiring manual review

**Output:** JSON file with detailed scan results

---

### B. update_header_rows_count.py
**Location:** `scripts/analysis/update_header_rows_count.py`

**Purpose:** Basic script to update `metadata.header_rows_count` from scan results

**Usage:**
```bash
python scripts/analysis/update_header_rows_count.py
```

**What it does:**
- Reads header scan results
- Updates `metadata.header_rows_count` for each statement
- Basic implementation for small datasets

---

### C. update_header_rows_count_fast.py (RECOMMENDED)
**Location:** `scripts/analysis/update_header_rows_count_fast.py`

**Purpose:** Optimized bulk update of `metadata.header_rows_count`

**Usage:**
```bash
python scripts/analysis/update_header_rows_count_fast.py
```

**What it does:**
- Uses bulk updates for better performance
- Processes large datasets efficiently
- Updates `metadata.header_rows_count` from scan results

**Recommended:** Use this for production database

---

### D. update_header_rows_suspicious.py
**Location:** `scripts/analysis/update_header_rows_suspicious.py`

**Purpose:** Mark statements with suspicious header patterns

**Usage:**
```bash
python scripts/analysis/update_header_rows_suspicious.py
```

**What it does:**
- Identifies statements with unusual header row patterns
- Updates `metadata.header_rows_count` for flagged statements
- Focuses on potentially manipulated statements

---

### E. extract_additional_metrics.py
**Location:** `scripts/analysis/extract_additional_metrics.py`

**Purpose:** Extract multiple metrics including header counts

**Usage:**
```bash
python scripts/analysis/extract_additional_metrics.py
```

**What it does:**
- Extracts header_rows_count along with other metrics
- More comprehensive analysis
- Can be used if other metrics are also needed

---

## 2. Gap Detection Columns

### missing_days_detected & gap_related_balance_changes

**Populated by:** `app/services/processor.py`

These columns are automatically populated during statement processing:

**Location:** `app/services/processor.py`

**When populated:** During the statement verification process

**Code references:**
- Gap detection logic in processor
- Automatically calculates missing days between transactions
- Counts balance changes during gap periods

**To repopulate:**
```bash
# Reprocess statements (this will recalculate gaps)
python -m app.services.processor
```

**Alternative:** These are calculated during normal processing, so if statements were already processed before Oct 14, the values should be in the backups. If they're missing, you need to reprocess those statements.

---

## 3. Raw Value Columns

### amount_raw, fee_raw (uatl_raw_statements & umtn_raw_statements)

**Populated by:** Parser modules during import

**Code references:**
- `app/services/parsers/uatl_parser.py` - Populates uatl_raw_statements.amount_raw and fee_raw
- `app/services/parsers/umtn_parser.py` - Populates umtn_raw_statements.fee_raw

**When populated:** During initial PDF parsing and import

**To repopulate:**
These values are stored during import. Since the database was restored from backups:
- If statements were imported BEFORE Oct 14 → These columns will be NULL (need reimport)
- If statements were imported AFTER Oct 14 → Data is lost (need reimport)

**Reimport process:**
1. Identify statements that need reimport
2. Delete and reimport those statements
3. Raw values will be captured during import

**Check for missing data:**
```sql
-- Check for NULL raw values
SELECT COUNT(*) FROM uatl_raw_statements WHERE amount_raw IS NULL;
SELECT COUNT(*) FROM uatl_raw_statements WHERE fee_raw IS NULL;
SELECT COUNT(*) FROM umtn_raw_statements WHERE fee_raw IS NULL;
```

---

## Recommended Execution Order

After running `post_restore_updates.sql` to add the columns:

### Step 1: Apply Schema Updates
```bash
source .env && mysql -h ${DB_HOST} -P ${DB_PORT} -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME} < scripts/migration/post_restore_updates.sql
```

### Step 2: Populate header_rows_count
```bash
# Option A: Scan and update (if scan results exist)
python scripts/analysis/update_header_rows_count_fast.py

# Option B: Re-scan all statements (if scan results don't exist)
python scripts/analysis/scan_header_manipulation.py
# Then run update script
python scripts/analysis/update_header_rows_count_fast.py
```

### Step 3: Verify Gap Columns
```sql
-- Check if gap data needs reprocessing
SELECT COUNT(*) FROM summary WHERE missing_days_detected IS NULL;
SELECT COUNT(*) FROM summary WHERE gap_related_balance_changes IS NULL;
```

If counts are high, statements may need reprocessing.

### Step 4: Check Raw Value Columns
```sql
-- Identify statements with missing raw values
SELECT run_id FROM uatl_raw_statements
WHERE amount_raw IS NULL OR fee_raw IS NULL
GROUP BY run_id;

SELECT run_id FROM umtn_raw_statements
WHERE fee_raw IS NULL
GROUP BY run_id;
```

If many statements are missing raw values, consider selective reimport.

---

## Verification Queries

After populating data:

```sql
-- Verify header_rows_count
SELECT
    COUNT(*) as total_statements,
    SUM(CASE WHEN header_rows_count > 0 THEN 1 ELSE 0 END) as with_headers,
    MAX(header_rows_count) as max_headers
FROM metadata
WHERE acc_prvdr_code = 'UATL' AND format = 'format_2';

-- Verify gap columns
SELECT
    COUNT(*) as total,
    SUM(missing_days_detected) as statements_with_gaps,
    SUM(gap_related_balance_changes) as total_gap_balance_changes
FROM summary;

-- Verify raw value columns
SELECT
    'uatl_raw - amount_raw' as column_name,
    COUNT(*) as total_rows,
    SUM(CASE WHEN amount_raw IS NOT NULL THEN 1 ELSE 0 END) as populated,
    SUM(CASE WHEN amount_raw IS NULL THEN 1 ELSE 0 END) as null_values
FROM uatl_raw_statements

UNION ALL

SELECT
    'uatl_raw - fee_raw',
    COUNT(*),
    SUM(CASE WHEN fee_raw IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN fee_raw IS NULL THEN 1 ELSE 0 END)
FROM uatl_raw_statements

UNION ALL

SELECT
    'umtn_raw - fee_raw',
    COUNT(*),
    SUM(CASE WHEN fee_raw IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN fee_raw IS NULL THEN 1 ELSE 0 END)
FROM umtn_raw_statements;
```

---

## Summary

**Quick Steps:**
1. ✅ Add columns: Run `post_restore_updates.sql`
2. ⏳ Populate header_rows_count: Run `update_header_rows_count_fast.py`
3. ℹ️ Gap columns: Auto-populated during processing (likely already have data)
4. ℹ️ Raw columns: Auto-populated during import (may need selective reimport)

**Most Important:** Focus on populating `header_rows_count` as it's critical for fraud detection.

---

Last updated: 2025-10-15
