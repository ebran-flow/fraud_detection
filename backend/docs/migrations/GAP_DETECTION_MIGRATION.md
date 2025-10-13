# Gap Detection Migration - Missing Transaction Days

## Overview

Add gap detection to identify statements with missing transaction days that cause balance calculation mismatches.

## Problem

**Incomplete statements:** Some PDF statements are missing transactions for certain date ranges, but the balance reflects those missing transactions. This causes:
- Running balance calculation to be incorrect
- Sudden balance_diff changes after date gaps
- Impossible to verify balance accuracy

### Example:
```
March 23: Balance = 551,515, balance_diff = 0 ✅
--- GAP: 7.7 days (March 24-30 missing) ---
March 31: Balance = 923,141, balance_diff = -721,626 ❌
```

## Solution

Track balance_diff changes that were caused by missing transaction days (date gaps >1 day).

## Migration

### Add Columns to Summary Table

```sql
-- Add missing_days_detected flag
ALTER TABLE summary
ADD COLUMN missing_days_detected BOOLEAN DEFAULT FALSE
COMMENT 'TRUE if balance_diff changes were caused by missing transaction days'
AFTER duplicate_count;

-- Add gap_related_balance_changes count
ALTER TABLE summary
ADD COLUMN gap_related_balance_changes INT DEFAULT 0
COMMENT 'Number of balance_diff changes caused by date gaps >1 day'
AFTER missing_days_detected;

-- Create index for filtering
CREATE INDEX idx_summary_missing_days ON summary(missing_days_detected);
```

### Verify Migration

```sql
-- Check columns exist
DESCRIBE summary;

-- Verify index
SHOW INDEX FROM summary WHERE Key_name = 'idx_summary_missing_days';
```

## Column Details

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `missing_days_detected` | BOOLEAN | TRUE if balance_diff changes were caused by date gaps | TRUE, FALSE |
| `gap_related_balance_changes` | INT | Count of balance_diff changes caused by gaps >1 day | 0, 3, 5 |

## Detection Logic

For each transaction:
1. Check if balance_diff changed from previous transaction
2. Check if there's a date gap >1 day before this transaction
3. If BOTH conditions true → increment gap_related_balance_changes

**Important:** Only counts gaps that AFFECTED balance calculation, not all date gaps.

### Example Statement Analysis

```
Total balance_diff changes: 8
Gap-related balance_diff changes: 3 (37.5%)
Non-gap related: 5 (62.5%)

missing_days_detected: TRUE
gap_related_balance_changes: 3
```

## Queries

### Find Statements with Missing Days

```sql
-- Statements with balance issues due to missing days
SELECT
    run_id,
    acc_number,
    gap_related_balance_changes,
    balance_diff_changes,
    balance_match,
    verification_status
FROM summary
WHERE missing_days_detected = TRUE
ORDER BY gap_related_balance_changes DESC;
```

### Gap Impact Analysis

```sql
-- Calculate percentage of balance issues due to gaps
SELECT
    COUNT(*) as total_statements,
    SUM(CASE WHEN missing_days_detected THEN 1 ELSE 0 END) as statements_with_gaps,
    ROUND(SUM(CASE WHEN missing_days_detected THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as gap_percentage,
    SUM(gap_related_balance_changes) as total_gap_related_changes,
    SUM(balance_diff_changes) as total_balance_changes
FROM summary
WHERE balance_match = 'Failed';
```

### Statements with High Gap Impact

```sql
-- Statements where most balance issues are gap-related
SELECT
    run_id,
    acc_number,
    gap_related_balance_changes,
    balance_diff_changes,
    ROUND(gap_related_balance_changes * 100.0 / balance_diff_changes, 1) as gap_percentage
FROM summary
WHERE missing_days_detected = TRUE
  AND balance_diff_changes > 0
ORDER BY gap_percentage DESC
LIMIT 20;
```

## Code Changes

### Files Modified

**`/app/services/processor.py`**

**Lines 398-443:** Added `detect_gap_related_balance_changes()` function
- Detects balance_diff changes preceded by date gaps >1 day
- Returns (missing_days_detected, gap_related_balance_changes)

**Lines 457-459:** Call detection function in `generate_summary()`
- Runs detection before creating summary
- Passes results to summary dictionary

**Lines 506-507:** Add fields to summary dictionary
- `missing_days_detected`: Boolean flag
- `gap_related_balance_changes`: Count

## Benefits

✅ **Identify Incomplete Statements:** Flag statements with missing transaction days
✅ **Quantify Impact:** Count how many balance issues are due to gaps
✅ **Better Analysis:** Distinguish between gap-related and other balance issues
✅ **Targeted Investigation:** Focus on statements with real data problems vs processing issues

## Expected Results

After reprocessing with gap detection:

### Statement Example
```
Run ID: 6476d2ce4ca78
Account: 753875842

Total transactions: 2,487
Balance_diff changes: 8
Gap-related changes: 3 (37.5%)

missing_days_detected: TRUE
gap_related_balance_changes: 3

Gaps detected:
1. March 23 → March 31 (7.7 days)
2. April 19 → April 21 (1.5 days)
3. April 24 → April 26 (1.4 days)
```

## Reprocessing

To apply gap detection to existing statements:

```bash
# Reprocess all statements
python process_statements_parallel.py --workers 8 --force
```

## Related Documentation

- **Quality Tracking:** `/docs/migrations/QUALITY_TRACKING_MIGRATION.md`
- **Processor:** `/app/services/processor.py`

---

**Created:** 2025-10-13
**Purpose:** Detect and track balance issues caused by missing transaction days
**Threshold:** Date gaps >1.0 days are considered significant
