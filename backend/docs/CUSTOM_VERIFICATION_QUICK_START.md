# Custom Verification System - Quick Start Guide

## Overview
The custom verification system automatically classifies Airtel statements into fraud risk levels based on PDF metadata patterns.

**Verification Levels:**
- 🟢 **NO_ISSUES** - Verified statements, safe to process
- 🟡 **WARNING** - Minor concerns, review recommended
- 🟠 **CRITICAL** - Significant anomalies, investigation required
- 🔴 **FATAL** - Strong fraud indicators, immediate action needed

---

## Quick Access: View Verification Status

### Option 1: Web Interface (Recommended)
Access the unified_statements view through your database client with this filter:
```sql
SELECT * FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
ORDER BY custom_verification, balance_diff_change_ratio DESC;
```

### Option 2: Export Data Files
Pre-generated CSV files available in `docs/data/`:
- **Flagged cases:** `flagged_statements_fatal_critical.csv` (288 records)
- **Verified cases:** `verified_statements_no_issues.csv` (2,164 records)

---

## Common Queries

### 1. Get All FATAL Cases
```sql
SELECT
    run_id,
    acc_number,
    custom_verification_reason,
    balance_diff_change_ratio,
    meta_producer,
    submitted_date,
    rm_name,
    summary_customer_name,
    summary_mobile_number
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND custom_verification = 'FATAL'
ORDER BY balance_diff_change_ratio DESC;
```

### 2. Check Specific Statement
```sql
SELECT
    run_id,
    custom_verification,
    custom_verification_reason,
    balance_match,
    balance_diff_change_ratio,
    meta_producer,
    meta_created_at,
    meta_modified_at,
    header_row_manipulation_count
FROM unified_statements
WHERE run_id = 'YOUR_RUN_ID_HERE';
```

### 3. Get Verification Summary
```sql
SELECT
    custom_verification,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage,
    ROUND(AVG(balance_diff_change_ratio) * 100, 2) as avg_balance_diff
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
GROUP BY custom_verification
ORDER BY
    CASE custom_verification
        WHEN 'FATAL' THEN 1
        WHEN 'CRITICAL' THEN 2
        WHEN 'NO_ISSUES' THEN 3
        ELSE 4
    END;
```

### 4. Get RM Performance Report
```sql
SELECT
    rm_name,
    SUM(CASE WHEN custom_verification = 'FATAL' THEN 1 ELSE 0 END) as fatal_count,
    SUM(CASE WHEN custom_verification = 'NO_ISSUES' THEN 1 ELSE 0 END) as verified_count,
    COUNT(*) as total_statements,
    ROUND(SUM(CASE WHEN custom_verification = 'FATAL' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as fatal_rate
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND rm_name IS NOT NULL
GROUP BY rm_name
HAVING total_statements >= 10
ORDER BY fatal_count DESC;
```

### 5. Get Recent Flagged Cases
```sql
SELECT
    run_id,
    acc_number,
    custom_verification,
    custom_verification_reason,
    submitted_date,
    rm_name
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND custom_verification IN ('FATAL', 'CRITICAL')
    AND submitted_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY submitted_date DESC;
```

### 6. Get Statements Needing Additional Review
```sql
SELECT
    run_id,
    acc_number,
    balance_diff_change_ratio,
    gap_related_balance_changes,
    duplicate_count,
    quality_issues_count,
    meta_producer,
    rm_name
FROM unified_statements
WHERE acc_prvdr_code = 'UATL'
    AND custom_verification IS NULL
    AND balance_match = 'Failed'
    AND balance_diff_change_ratio > 0.05
ORDER BY balance_diff_change_ratio DESC
LIMIT 100;
```

---

## Running Classification

### Manual Classification Run
To re-run classification after updates:
```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
python scripts/analysis/apply_custom_verification.py
```

### Dry Run (Preview Only)
To preview classification without updating database:
```bash
python scripts/analysis/apply_custom_verification.py --dry-run
```

**Execution Time:** ~2 minutes for 12,405 statements

---

## Understanding Fraud Patterns

### Pattern 1: Microsoft Office Editing (Most Common)
**Indicators:**
- meta_producer contains "Microsoft® Word" or "Microsoft® Excel"
- Often combined with header_row_manipulation_count > 0

**Example:**
```
Producer: Microsoft® Word 2013
Author: AIRTEL UGANDA or USER
Created: 2025-03-12 17:00:46
Modified: 2025-03-12 17:00:46
Header Manipulations: 36 times
Balance Diff: 31.03%
```

**Action:** Contact customer immediately, verify original statement

---

### Pattern 2: Modified Qt 4.8.7 PDFs (Sophisticated)
**Indicators:**
- meta_producer = "Qt 4.8.7" (genuine Airtel producer)
- meta_modified_at is NOT NULL (modified after creation)
- High balance discrepancy

**Example:**
```
Producer: Qt 4.8.7
Author: N/A
Created: 2025-10-08 10:48:22
Modified: 2025-10-08 12:34:24 (2 hours later!)
Balance Diff: 89.34%
```

**Action:** Urgent review - sophisticated fraud attempt designed to look genuine

---

### Pattern 3: Header Row Manipulation
**Indicators:**
- header_row_manipulation_count > 0
- Format 2 statements
- Often combined with Microsoft Office producer

**Severity Levels:**
- 1-10 manipulations: Minor concern
- 11-30 manipulations: Moderate concern
- 31-50 manipulations: High concern (83% avg balance diff)
- 50+ manipulations: Severe manipulation

**Example:**
```
Header Manipulations: 46 times
Producer: Microsoft® Word 2013
Balance Diff: 29.34%
```

**Action:** Review for inserted rows between transactions

---

## Verification Override Rule

**Rule:** If `balance_match = 'Success'`, statement is automatically classified as `NO_ISSUES` regardless of metadata.

**Rationale:** Successfully verified balance calculations override metadata concerns. Even if metadata shows anomalies, if the numbers add up correctly, the statement is considered valid.

**Example:**
```sql
-- Statement has suspicious metadata but balance matches
Summary Table: custom_verification = NULL or FATAL
Balance Match: Success
View Output: custom_verification = NO_ISSUES
Reason: "Balance verification successful"
```

---

## Quick Decision Guide

### For RMs Submitting Statements

**Before Submission:**
1. Check PDF producer in document properties
2. Reject if shows Microsoft Word/Excel
3. Verify no modification timestamp
4. Check for unusual header rows

**After Flagged:**
1. Contact customer immediately
2. Request original statement from Airtel
3. Compare with submitted version
4. Document findings

---

### For Reviewers

**FATAL Case:**
1. Immediate investigation required
2. Freeze disbursement pending verification
3. Contact customer and RM
4. Document response
5. Escalate if customer confirms fraud

**CRITICAL Case:**
1. Review within 24 hours
2. Check additional metrics
3. Compare with previous statements
4. Consult supervisor if uncertain

**NO_ISSUES Case:**
1. Safe to proceed
2. Standard processing
3. No additional review needed

**UNCLASSIFIED Case:**
1. Check balance_diff_change_ratio
2. If < 5%: Likely genuine, proceed
3. If > 10%: Manual review recommended
4. If > 50%: Treat as CRITICAL

---

## Integration with Customer Details

### Check Fraud History for Customer
```sql
SELECT
    u.run_id,
    u.submitted_date,
    u.custom_verification,
    cd.borrower_biz_name,
    cd.tot_loans,
    cd.tot_default_loans,
    cd.risk_category
FROM unified_statements u
LEFT JOIN customer_details cd ON u.run_id = cd.run_id
WHERE u.acc_number = 'CUSTOMER_ACC_NUMBER'
ORDER BY u.submitted_date DESC;
```

### High-Risk Borrowers with Fraud History
```sql
SELECT
    cd.borrower_biz_name,
    cd.cust_id,
    COUNT(CASE WHEN u.custom_verification = 'FATAL' THEN 1 END) as fatal_count,
    cd.tot_loans,
    cd.tot_default_loans,
    cd.risk_category,
    cd.current_fa_limit
FROM customer_details cd
INNER JOIN unified_statements u ON cd.run_id = u.run_id
WHERE u.custom_verification = 'FATAL'
GROUP BY cd.borrower_biz_name, cd.cust_id, cd.tot_loans, cd.tot_default_loans,
         cd.risk_category, cd.current_fa_limit
HAVING fatal_count >= 2
ORDER BY fatal_count DESC, cd.tot_default_loans DESC;
```

---

## Troubleshooting

### Issue: Column not found
**Problem:** custom_verification column doesn't exist in unified_statements view
**Solution:** Apply migration:
```bash
mysql -u root -p fraud_detection < migrations/add_custom_verification_to_unified_view.sql
```

### Issue: Outdated classifications
**Problem:** New statements not classified
**Solution:** Run classification script:
```bash
python scripts/analysis/apply_custom_verification.py
```

### Issue: Can't update view
**Problem:** Permission denied when updating view
**Solution:** Use xtrabackup credentials (root user) from `.env.xtrabackup`

---

## Key Metrics

### Current Statistics (as of Oct 17, 2025)
- Total UATL Statements: 12,405
- FATAL: 286 (2.3%)
- CRITICAL: 2 (0.0%)
- NO_ISSUES: 2,164 (17.4%)
- UNCLASSIFIED: 9,953 (80.2%)

### Top Fraud Patterns
1. Microsoft Office editing: 211 cases (73.8% of FATAL)
2. Modified Qt PDFs: 75 cases (26.2% of FATAL)
3. Heavy header manipulation: 130 cases (45.3% of FATAL)

### High-Risk RMs (Top 3)
1. MUGISHA DENIS: 58 FATAL cases (80.7% avg balance diff)
2. WAKWESA HERMAN: 57 FATAL cases (40.3% avg balance diff)
3. ISABIRYE PATRICK: 54 FATAL cases (48.9% avg balance diff)

---

## Resources

### Documentation
- **Executive Summary:** `docs/EXECUTIVE_SUMMARY_CUSTOM_VERIFICATION.md`
- **Detailed Report:** `docs/CUSTOM_VERIFICATION_SUMMARY.md`
- **Requirements:** `docs/prompts/Suspicious statements flagging logic.md`

### Data Files
- **Flagged Cases:** `docs/data/flagged_statements_fatal_critical.csv`
- **Verified Cases:** `docs/data/verified_statements_no_issues.csv`

### Scripts
- **Classification:** `scripts/analysis/apply_custom_verification.py`
- **Migrations:** `migrations/add_custom_verification_column.sql`

---

## Support

**Technical Issues:** Backend Development Team
**Process Questions:** Fraud Detection Team
**Escalations:** Risk Management

**Last Updated:** October 17, 2025
