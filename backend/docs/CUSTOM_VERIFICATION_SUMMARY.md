# Custom Verification System - Summary Report
**Date:** October 17, 2025
**Scope:** UATL (Airtel Uganda) Statements
**Total Statements Analyzed:** 12,405

---

## Executive Summary

Implemented a metadata-based verification system that classifies statements into 4 levels:
- **NO_ISSUES**: Verified statements with no fraud indicators (17.4%)
- **WARNING**: Minor concerns requiring review
- **CRITICAL**: Significant anomalies requiring investigation (0.0%)
- **FATAL**: Strong fraud indicators requiring immediate action (2.3%)
- **UNCLASSIFIED**: Statements not matching any defined patterns (80.2%)

### Key Findings

1. **286 FATAL cases identified (2.3%)**
   - 204 cases: Microsoft Word-edited statements
   - 75 cases: Qt 4.8.7 PDFs modified post-creation
   - 7 cases: Microsoft Excel-edited statements

2. **2,164 NO_ISSUES statements verified (17.4%)**
   - 96.9% have successful balance matches
   - Valid Airtel-generated PDFs and CSVs
   - Balance discrepancies minimal (avg 0.05%)

3. **9,953 UNCLASSIFIED statements (80.2%)**
   - Do not match defined metadata patterns
   - Require additional metric-based analysis
   - Average balance diff: 4.88%

---

## Classification Methodology

### Format 1 (PDF) - 6 Combinations

#### Combination 1: Valid Airtel PDFs → NO_ISSUES
- meta_title = "PDF Template"
- meta_author = "N/A"
- meta_producer = "Qt 4.8.7"
- meta_created_at NOT NULL
- meta_modified_at NULL
- **Result:** 1,771 statements verified

#### Combination 2: Valid Airtel CSVs → NO_ISSUES
- meta_title = "Airtel Money CSV Statement"
- meta_author = "Airtel"
- meta_producer = "CSV Export"
- **Result:** Minimal cases (CSVs rare in this dataset)

#### Combination 3: Samsung Electronics → CRITICAL
- meta_producer = "Samsung Electronics"
- **Criteria:** balance_diff_change_ratio > 10%
- **Result:** 2 statements flagged

#### Combination 4: USER + Microsoft Word → FATAL
- meta_title = "PDF Template"
- meta_author = "USER"
- meta_producer contains "Microsoft" or "Word" or "Qt 4.8.7"
- meta_modified_at NOT NULL
- **Result:** 79 statements flagged

#### Combination 5: PDFium with Success → NO_ISSUES
- meta_producer = "PDFium"
- balance_match = "Success"
- **Result:** Verified statements

#### Combination 6: Modified Qt 4.8.7 → FATAL (NEW)
- meta_title = "PDF Template"
- meta_producer = "Qt 4.8.7"
- meta_modified_at NOT NULL (post-creation modification)
- **Result:** 53 statements flagged (appears genuine but modified)

### Format 2 (PDF) - 3 Combinations

#### Combination 1: Header Manipulation → FATAL
- header_row_manipulation_count > 0
- **Excluding:** run_id = '678fbedd976c7'
- **Result:** 129 statements (31-50+ manipulations show avg 83% balance diff)

#### Combination 2: Microsoft Office Editing → FATAL
- meta_producer contains "Microsoft Word" or "Microsoft Excel"
- **Result:** 78 statements flagged

#### Combination 3: Balance Match Success → NO_ISSUES
- balance_match = "Success"
- **Result:** 393 statements verified

### Override Rule
**balance_match = "Success" → NO_ISSUES** (overrides all other checks)
- Applied to 2,096 statements
- Ensures verified statements are not flagged due to metadata anomalies

---

## Detailed Statistics

### 1. Verification Distribution by Format

| Format   | Verification   | Count | Avg Balance Diff |
|----------|----------------|------:|----------------:|
| format_1 | FATAL          |    79 |         74.80% |
| format_1 | CRITICAL       |     2 |         65.75% |
| format_1 | NO_ISSUES      | 1,771 |          0.05% |
| format_2 | FATAL          |   207 |         54.41% |
| format_2 | NO_ISSUES      |   393 |          0.01% |
| format_2 | UNCLASSIFIED   | 9,953 |          4.88% |

### 2. FATAL Cases - Producer Breakdown

| Producer                              | Count | Avg Balance Diff |
|---------------------------------------|------:|----------------:|
| Microsoft® Word 2013                  |   204 |         53.96% |
| Qt 4.8.7 (modified)                   |    75 |         78.09% |
| Microsoft® Word for Microsoft 365     |     3 |          7.43% |
| Microsoft® Excel® 2010                |     2 |         87.27% |
| Microsoft® Excel® 2016                |     1 |         23.35% |
| MicrosoftÂ® Word 2013                 |     1 |         87.19% |

### 3. Header Manipulation Impact (Format 2)

| Manipulation Range | Verification   | Count | Avg Balance Diff |
|-------------------|----------------|------:|----------------:|
| 0 (None)          | UNCLASSIFIED   | 9,952 |          4.88% |
| 0 (None)          | FATAL          |    78 |         30.03% |
| 0 (None)          | NO_ISSUES      |   393 |          0.01% |
| 1-10 times        | FATAL          |     9 |         21.10% |
| 11-30 times       | FATAL          |     8 |         51.64% |
| 31-50 times       | FATAL          |    93 |         83.28% |
| 50+ times         | FATAL          |    19 |         30.16% |

**Insight:** Heavy header manipulation (31-50 times) correlates with 83% average balance discrepancy.

### 4. Balance Match Success Rate

| Verification | Balance Match | Count | Percentage |
|-------------|---------------|------:|----------:|
| NO_ISSUES   | Success       | 2,096 |     96.9% |
| NO_ISSUES   | Failed        |    68 |      3.1% |
| CRITICAL    | Failed        |     2 |    100.0% |
| FATAL       | Failed        |   286 |    100.0% |

**Insight:** All FATAL and CRITICAL cases have failed balance matches. NO_ISSUES has 96.9% success rate.

---

## Sample FATAL Cases

### Case 1: Heavy Header Manipulation
- **Run ID:** 67d197a6b0ad0
- **Producer:** Microsoft® Word 2013
- **Author:** AIRTEL UGANDA
- **Header Manipulations:** 36 times
- **Balance Diff:** 31.03%
- **Reason:** Header was intentionally manipulated

### Case 2: Modified Qt 4.8.7 PDF (Combination 6)
- **Run ID:** 68e63232510ac
- **Producer:** Qt 4.8.7
- **Author:** N/A
- **Created:** 2025-10-08 10:48:22
- **Modified:** 2025-10-08 12:34:24 (~2 hours later)
- **Balance Diff:** 89.34%
- **Reason:** PDF Template with Qt 4.8.7 but modified after creation

### Case 3: Microsoft Word Editing
- **Run ID:** 67f40a7e73bf4
- **Producer:** Microsoft® Word 2013
- **Author:** AIRTEL UGANDA
- **Balance Diff:** 21.93%
- **Reason:** Statement was edited using Microsoft Word and converted to PDF

---

## Implementation Details

### Database Schema
- **Table:** `summary`
- **Columns Added:**
  - `custom_verification` VARCHAR(50) - Verification level
  - `flag_level` VARCHAR(50) - Deprecated (superseded by custom_verification)
  - `flag_reason` TEXT - Detailed explanation

### View Integration
- **View:** `unified_statements`
- **Columns:**
  - `custom_verification` - Shows NO_ISSUES if balance_match = Success (override rule)
  - `custom_verification_reason` - Detailed reason for classification

### Script
- **Location:** `scripts/analysis/apply_custom_verification.py`
- **Execution Time:** ~2 minutes for 12,405 statements
- **Usage:**
  ```bash
  python scripts/analysis/apply_custom_verification.py          # Apply
  python scripts/analysis/apply_custom_verification.py --dry-run # Preview
  ```

---

## Recommendations

### Immediate Actions
1. **Investigate 286 FATAL cases** - Focus on:
   - Microsoft Word/Excel edited statements (204 cases)
   - Modified Qt 4.8.7 PDFs (75 cases)
   - High balance discrepancies (>50%)

2. **Review 2 CRITICAL cases** - Samsung Electronics producer with high balance diff ratio

3. **Export FATAL cases** - For detailed manual review and customer follow-up

### Next Steps
1. **Classify 9,953 UNCLASSIFIED statements (80.2%)**
   - Use additional metrics: balance_diff_changes, gap_related_balance_changes
   - Implement quality_issues_count threshold checks
   - Add duplicate_count analysis with context

2. **Develop AI-based flagging** - In separate `claude_flagging` column
   - Multi-metric analysis
   - Pattern detection across related statements
   - Risk scoring model

3. **Customer relationship analysis**
   - Join with customer_details table
   - Identify repeat offenders
   - Correlate with borrower risk categories and default rates

4. **RM performance analysis**
   - Track FATAL cases by RM
   - Identify training needs
   - Strengthen verification processes

---

## Query Examples

### Get all FATAL cases with details
```sql
SELECT
    run_id,
    acc_number,
    custom_verification,
    custom_verification_reason,
    balance_diff_change_ratio,
    meta_producer,
    header_row_manipulation_count,
    submitted_date,
    rm_name
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND custom_verification = 'FATAL'
ORDER BY balance_diff_change_ratio DESC;
```

### Get verification summary by RM
```sql
SELECT
    rm_name,
    custom_verification,
    COUNT(*) as count,
    AVG(balance_diff_change_ratio) as avg_balance_diff
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND custom_verification IS NOT NULL
GROUP BY rm_name, custom_verification
ORDER BY rm_name,
    CASE custom_verification
        WHEN 'FATAL' THEN 1
        WHEN 'CRITICAL' THEN 2
        WHEN 'NO_ISSUES' THEN 3
        ELSE 4
    END;
```

### Get statements needing additional analysis
```sql
SELECT
    run_id,
    acc_number,
    balance_diff_change_ratio,
    gap_related_balance_changes,
    duplicate_count,
    quality_issues_count,
    meta_producer
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND custom_verification IS NULL
    AND balance_match = 'Failed'
ORDER BY balance_diff_change_ratio DESC
LIMIT 100;
```

---

## Files Reference

- **Requirements:** `docs/prompts/Suspicious statements flagging logic.md`
- **Migration:** `migrations/add_custom_verification_column.sql`
- **View Update:** `migrations/add_custom_verification_to_unified_view.sql`
- **Script:** `scripts/analysis/apply_custom_verification.py`
- **Instructions:** `docs/UPDATE_UNIFIED_VIEW_INSTRUCTIONS.md`

---

**Report Generated:** 2025-10-17
**System:** Custom Verification Module v1.0
**Status:** ✓ Operational and integrated with unified_statements view
