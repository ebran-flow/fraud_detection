# Analysis Report Implementation Plan
**Date:** October 17, 2025
**Purpose:** Generate comprehensive fraud analysis reports with RM/CS involvement tracking

---

## Overview

Generate multi-tab Excel reports to:
1. Export all statements grouped by provider and format
2. Analyze FATAL cases with loan performance data
3. Identify RMs and CS (Customer Success) involved in fraud
4. Assess business impact and revenue loss

---

## Requirements Summary

### Input Data Sources
- **fraud_detection.unified_statements** - Statement data with custom_verification
- **fraud_detection.customer_details** - Customer and borrower information
- **flow_api.loans** - All loan records
- **flow_api.app_users** - User accounts (for CS identification)
- **flow_api.persons** - Person names (for CS and RM names)

### Output Files
1. **unified_statements_export.xlsx** - Base data export (All statements)
2. **fatal_analysis_report.xlsx** - FATAL-specific analysis with loans data

---

## Script 1: Export Unified Statements

### File: `scripts/analysis/export_unified_statements.py`

### Required Tabs

#### Tab 1-3: Statement Data by Format
- **UATL_format_1** - Airtel format_1 statements
- **UATL_format_2** - Airtel format_2 statements
- **UMTN_excel** - MTN excel statements

**Columns (from unified_statements):**
```
run_id, acc_number, acc_prvdr_code, format, mime,
submitted_date, start_date, end_date, rm_name,
custom_verification, custom_verification_reason,
balance_match, balance_diff_change_ratio,
stmt_opening_balance, stmt_closing_balance,
calculated_closing_balance, balance_diff_changes,
credits, debits, fees, charges,
duplicate_count, quality_issues_count,
header_row_manipulation_count, gap_related_balance_changes,
meta_title, meta_author, meta_producer,
meta_created_at, meta_modified_at,
summary_customer_name, summary_mobile_number,
cust_id, borrower_biz_name
```

#### Tab 4: Summary
**Columns:**
- format (format_1, format_2, excel)
- acc_prvdr_code (UATL, UMTN)
- custom_verification (NO_ISSUES, FATAL, CRITICAL, NULL)
- count
- avg_balance_diff_ratio
- total_credits
- total_debits

**SQL Query:**
```sql
SELECT
    format,
    acc_prvdr_code,
    custom_verification,
    COUNT(*) as count,
    ROUND(AVG(balance_diff_change_ratio) * 100, 2) as avg_balance_diff_pct,
    SUM(credits) as total_credits,
    SUM(debits) as total_debits
FROM unified_statements
WHERE acc_prvdr_code IN ('UATL', 'UMTN')
GROUP BY format, acc_prvdr_code, custom_verification
ORDER BY acc_prvdr_code, format,
    CASE custom_verification
        WHEN 'FATAL' THEN 1
        WHEN 'CRITICAL' THEN 2
        WHEN 'NO_ISSUES' THEN 3
        ELSE 4
    END;
```

### Implementation Steps
1. Query unified_statements grouped by (acc_prvdr_code, format)
2. Create Excel workbook using openpyxl
3. Write data to respective tabs
4. Generate summary tab with aggregations
5. Format columns (auto-width, headers, freeze panes)
6. Save to `docs/analysis/unified_statements_export.xlsx`

---

## Script 2: FATAL Analysis Report

### File: `scripts/analysis/export_fatal_analysis.py`

### Required Tabs

#### Tab 1: FATAL_filtered
All FATAL cases from UATL (format_1 and format_2)

**Source:** Filter unified_statements where:
- acc_prvdr_code = 'UATL'
- custom_verification = 'FATAL'
- format IN ('format_1', 'format_2')

**Columns:** Same as unified_statements tabs

---

#### Tab 2: loans_raw
All loans for customers who submitted FATAL statements

**Join Logic:**
```sql
SELECT DISTINCT cust_id
FROM unified_statements u
INNER JOIN customer_details cd ON u.run_id = cd.run_id
WHERE u.acc_prvdr_code = 'UATL'
  AND u.custom_verification = 'FATAL'
  AND cd.cust_id IS NOT NULL
```

**Loans Query:**
```sql
SELECT
    l.loan_doc_id,
    l.cust_id,
    l.biz_name,
    l.loan_principal,
    l.flow_fee,
    l.disbursal_date,
    l.due_date,
    l.paid_date,
    l.status,
    l.overdue_days,
    l.current_os_amount as os_amount,

    -- Derived: loan_applier_name
    CONCAT_WS(' ', p_applier.first_name, p_applier.middle_name, p_applier.last_name) as loan_applier_name,

    -- Derived: loan_applier_role
    au.role_codes as loan_applier_role,

    -- Already in loans table
    l.flow_rel_mgr_name

FROM flow_api.loans l
LEFT JOIN flow_api.app_users au ON l.loan_applied_by = au.id
LEFT JOIN flow_api.persons p_applier ON au.person_id = p_applier.id
WHERE l.cust_id IN (
    -- FATAL customers with cust_id
    SELECT DISTINCT cd.cust_id
    FROM fraud_detection.unified_statements u
    INNER JOIN fraud_detection.customer_details cd ON u.run_id = cd.run_id
    WHERE u.acc_prvdr_code = 'UATL'
      AND u.custom_verification = 'FATAL'
      AND cd.cust_id IS NOT NULL
)
ORDER BY l.cust_id, l.disbursal_date;
```

---

#### Tab 3: analysis_raw
Aggregated data by cust_id with fraud patterns and loan performance

**Aggregation Level:** One row per cust_id (not per run_id)

**Columns and Derivation:**

```python
# Fraud Submission Patterns (from unified_statements + mapper)
cust_id                   # from customer_details
first_rm_name             # RM who submitted first FATAL statement
last_rm_name              # RM who submitted last FATAL statement
rm_name                   # RM who submitted most FATAL statements (mode)
no_of_times_fraud         # COUNT of FATAL statements for this cust_id
first_submitted_date      # MIN(submitted_date) of FATAL statements
last_submitted_date       # MAX(submitted_date) of FATAL statements

# Borrower Info (from customer_details/borrowers)
registered_rm             # from customer_details.reg_rm_name
current_rm                # from customer_details.current_rm_name
reg_date                  # from customer_details.borrower_reg_date

# Loan Statistics (from loans_raw)
tot_loans                 # COUNT(*) from loans
first_loan_date           # MIN(disbursal_date)
last_loan_date            # MAX(disbursal_date)
days_since_last_loan      # DATEDIFF(NOW(), last_loan_date)

# Payment Performance (from loans_raw - PAID loans only)
tot_ontime_count          # COUNT where overdue_days <= 1 AND paid_date IS NOT NULL
tot_ontime_perc           # (tot_ontime_count / tot_paid_loans) * 100
tot_3_day_late_loans      # COUNT where overdue_days BETWEEN 2 AND 3 AND paid_date IS NOT NULL
tot_10_day_late_loans     # COUNT where overdue_days >= 10 AND paid_date IS NOT NULL

# Current Status (from loans_raw)
tot_overdue_loans         # COUNT where status = 'overdue'
last_loan_status          # status of loan with MAX(disbursal_date)
tot_os_amount             # SUM(current_os_amount) where status IN ('ongoing', 'overdue')

# Financial Impact (from loans_raw - PAID loans only)
tot_revenue               # SUM(flow_fee) where paid_date IS NOT NULL
```

**Implementation Query Structure:**
```sql
WITH fatal_customers AS (
    SELECT DISTINCT
        cd.cust_id,
        cd.borrower_biz_name,
        cd.reg_rm_name as registered_rm,
        cd.current_rm_name as current_rm,
        cd.borrower_reg_date as reg_date
    FROM unified_statements u
    INNER JOIN customer_details cd ON u.run_id = cd.run_id
    WHERE u.acc_prvdr_code = 'UATL'
      AND u.custom_verification = 'FATAL'
      AND cd.cust_id IS NOT NULL
),
fraud_submissions AS (
    SELECT
        cd.cust_id,
        u.run_id,
        u.submitted_date,
        u.rm_name
    FROM unified_statements u
    INNER JOIN customer_details cd ON u.run_id = cd.run_id
    WHERE u.acc_prvdr_code = 'UATL'
      AND u.custom_verification = 'FATAL'
      AND cd.cust_id IS NOT NULL
),
fraud_stats AS (
    SELECT
        cust_id,
        COUNT(*) as no_of_times_fraud,
        MIN(submitted_date) as first_submitted_date,
        MAX(submitted_date) as last_submitted_date,
        -- first_rm and last_rm need window functions
        (SELECT rm_name FROM fraud_submissions fs2
         WHERE fs2.cust_id = fs1.cust_id
         ORDER BY submitted_date ASC LIMIT 1) as first_rm_name,
        (SELECT rm_name FROM fraud_submissions fs2
         WHERE fs2.cust_id = fs1.cust_id
         ORDER BY submitted_date DESC LIMIT 1) as last_rm_name
    FROM fraud_submissions fs1
    GROUP BY cust_id
),
loan_stats AS (
    SELECT
        cust_id,
        COUNT(*) as tot_loans,
        MIN(disbursal_date) as first_loan_date,
        MAX(disbursal_date) as last_loan_date,
        DATEDIFF(NOW(), MAX(disbursal_date)) as days_since_last_loan,
        -- Payment performance (paid loans only)
        SUM(CASE WHEN paid_date IS NOT NULL AND overdue_days <= 1 THEN 1 ELSE 0 END) as tot_ontime_count,
        SUM(CASE WHEN paid_date IS NOT NULL THEN 1 ELSE 0 END) as tot_paid_loans,
        SUM(CASE WHEN paid_date IS NOT NULL AND overdue_days BETWEEN 2 AND 3 THEN 1 ELSE 0 END) as tot_3_day_late_loans,
        SUM(CASE WHEN paid_date IS NOT NULL AND overdue_days >= 10 THEN 1 ELSE 0 END) as tot_10_day_late_loans,
        -- Current status
        SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as tot_overdue_loans,
        SUM(CASE WHEN status IN ('ongoing', 'overdue') THEN current_os_amount ELSE 0 END) as tot_os_amount,
        -- Revenue (paid loans only)
        SUM(CASE WHEN paid_date IS NOT NULL THEN flow_fee ELSE 0 END) as tot_revenue
    FROM flow_api.loans
    WHERE cust_id IN (SELECT cust_id FROM fatal_customers)
    GROUP BY cust_id
)
SELECT
    fc.cust_id,
    fc.borrower_biz_name,
    fs.first_rm_name,
    fs.last_rm_name,
    -- Most frequent RM (mode) - needs separate calculation
    fs.no_of_times_fraud,
    fs.first_submitted_date,
    fs.last_submitted_date,
    fc.registered_rm,
    fc.current_rm,
    fc.reg_date,
    ls.tot_loans,
    ls.first_loan_date,
    ls.last_loan_date,
    ls.days_since_last_loan,
    ls.tot_ontime_count,
    ROUND(ls.tot_ontime_count * 100.0 / NULLIF(ls.tot_paid_loans, 0), 2) as tot_ontime_perc,
    ls.tot_3_day_late_loans,
    ls.tot_10_day_late_loans,
    ls.tot_overdue_loans,
    -- Last loan status - needs separate query
    ls.tot_os_amount,
    ls.tot_revenue
FROM fatal_customers fc
LEFT JOIN fraud_stats fs ON fc.cust_id = fs.cust_id
LEFT JOIN loan_stats ls ON fc.cust_id = ls.cust_id
ORDER BY fs.no_of_times_fraud DESC, ls.tot_os_amount DESC;
```

**Note:** Most frequent RM (mode) and last_loan_status need special handling in Python.

---

#### Tab 4-7: Summary Insights

##### Tab 4: Business Impact Analysis

**Insight:** "Is this affecting us?"

**Metrics:**
```sql
SELECT
    'Payment Performance' as category,
    SUM(CASE WHEN tot_ontime_count = tot_loans THEN 1 ELSE 0 END) as customers_paying_ontime,
    SUM(CASE WHEN tot_3_day_late_loans > 0 OR tot_10_day_late_loans > 0 THEN 1 ELSE 0 END) as customers_paying_late,
    SUM(CASE WHEN last_loan_status = 'ongoing' THEN 1 ELSE 0 END) as customers_currently_ongoing,
    SUM(CASE WHEN tot_overdue_loans > 0 THEN 1 ELSE 0 END) as customers_currently_overdue,
    SUM(tot_os_amount) as total_os_amount,
    SUM(CASE WHEN days_since_last_loan <= 30 THEN 1 ELSE 0 END) as customers_active_last_30_days
FROM analysis_raw;
```

##### Tab 5: RM/CS Involvement Analysis

**RM Analysis:**
```sql
-- RMs who submitted statements
SELECT
    rm_name,
    COUNT(DISTINCT cust_id) as unique_customers,
    SUM(no_of_times_fraud) as total_fraud_submissions,
    SUM(tot_os_amount) as total_os_amount,
    SUM(tot_revenue) as total_revenue
FROM analysis_raw
WHERE rm_name IS NOT NULL
GROUP BY rm_name
ORDER BY total_fraud_submissions DESC;

-- RMs who registered borrowers
SELECT
    registered_rm,
    COUNT(DISTINCT cust_id) as customers_registered,
    SUM(tot_os_amount) as total_os_amount
FROM analysis_raw
WHERE registered_rm IS NOT NULL
GROUP BY registered_rm
ORDER BY customers_registered DESC;

-- RMs during overdue loan disbursal (need loans_raw)
SELECT
    flow_rel_mgr_name,
    COUNT(*) as overdue_loan_disbursals,
    SUM(current_os_amount) as total_os_amount
FROM loans_raw
WHERE status = 'overdue'
GROUP BY flow_rel_mgr_name
ORDER BY overdue_loan_disbursals DESC;
```

**CS Analysis:**
```sql
-- CS who applied for loans
SELECT
    loan_applier_name,
    loan_applier_role,
    COUNT(DISTINCT cust_id) as unique_customers,
    COUNT(*) as total_loans_applied,
    SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue_loans
FROM loans_raw
WHERE loan_applier_name IS NOT NULL
GROUP BY loan_applier_name, loan_applier_role
ORDER BY total_loans_applied DESC;
```

##### Tab 6: OS Amount vs Revenue

```sql
SELECT
    cust_id,
    borrower_biz_name,
    tot_revenue,
    tot_os_amount,
    tot_os_amount - tot_revenue as net_impact,
    CASE
        WHEN tot_revenue > tot_os_amount THEN 'Profitable'
        WHEN tot_revenue < tot_os_amount THEN 'Loss'
        ELSE 'Break Even'
    END as status
FROM analysis_raw
ORDER BY net_impact ASC;
```

##### Tab 7: Monthly Trends

```sql
-- Fraud submissions by month
SELECT
    DATE_FORMAT(first_submitted_date, '%Y-%m') as month,
    COUNT(*) as fraud_submissions,
    COUNT(DISTINCT cust_id) as unique_customers
FROM analysis_raw
GROUP BY month
ORDER BY month DESC;

-- Also analyze by submission date from FATAL_filtered
SELECT
    DATE_FORMAT(submitted_date, '%Y-%m') as month,
    COUNT(*) as total_submissions,
    COUNT(DISTINCT cust_id) as unique_customers
FROM (
    SELECT u.submitted_date, cd.cust_id
    FROM unified_statements u
    INNER JOIN customer_details cd ON u.run_id = cd.run_id
    WHERE u.acc_prvdr_code = 'UATL'
      AND u.custom_verification = 'FATAL'
) fraud_by_month
GROUP BY month
ORDER BY month DESC;
```

---

## Implementation Details

### Script 1: export_unified_statements.py

**Key Functions:**
```python
def get_statements_by_format(engine, acc_prvdr_code, format_type):
    """Query unified_statements for specific provider and format."""
    pass

def create_summary_tab(engine):
    """Generate summary statistics grouped by format and verification."""
    pass

def export_to_excel(dataframes, output_file):
    """Export multiple dataframes to Excel with formatting."""
    pass
```

**Execution:**
```bash
python scripts/analysis/export_unified_statements.py
```

**Output:** `docs/analysis/unified_statements_export.xlsx`

---

### Script 2: export_fatal_analysis.py

**Key Functions:**
```python
def get_fatal_statements(engine):
    """Get all FATAL UATL statements."""
    pass

def get_fatal_customer_ids(engine):
    """Get cust_ids for FATAL customers."""
    pass

def get_loans_for_customers(engine, cust_ids):
    """Query loans with CS/RM derived fields."""
    pass

def aggregate_by_customer(fatal_df, loans_df):
    """Create analysis_raw with aggregations."""
    pass

def generate_business_impact(analysis_df):
    """Generate business impact summary."""
    pass

def generate_rm_cs_analysis(analysis_df, loans_df):
    """Generate RM and CS involvement analysis."""
    pass

def generate_os_vs_revenue(analysis_df):
    """Generate OS amount vs revenue analysis."""
    pass

def generate_monthly_trends(fatal_df):
    """Generate monthly fraud submission trends."""
    pass

def export_to_excel(dataframes, output_file):
    """Export all tabs to Excel."""
    pass
```

**Execution:**
```bash
python scripts/analysis/export_fatal_analysis.py
```

**Output:** `docs/analysis/fatal_analysis_report.xlsx`

---

## Data Quality Considerations

### Missing Data Handling
- **cust_id is NULL:** Some FATAL cases may not have borrower records
  - Solution: Exclude from loan analysis, note in summary
- **rm_name is NULL:** Some statements may lack RM information
  - Solution: Group as "Unknown RM" in analysis
- **loan_applier missing:** LEFT JOIN may result in NULL
  - Solution: Show as "Unknown CS"

### Edge Cases
- **Customers with no loans:** May have cust_id but no loans in system
  - Solution: Show 0 for loan metrics
- **Multiple RMs with same count:** Mode calculation for most frequent RM
  - Solution: Pick alphabetically first or show all
- **Loans without overdue_days:** Calculate if NULL
  - Solution: COALESCE(overdue_days, DATEDIFF(COALESCE(paid_date, NOW()), due_date))

---

## File Structure

```
backend/
├── scripts/
│   └── analysis/
│       ├── export_unified_statements.py      # Script 1
│       └── export_fatal_analysis.py          # Script 2
├── docs/
│   └── analysis/
│       ├── unified_statements_export.xlsx    # Output 1
│       └── fatal_analysis_report.xlsx        # Output 2
└── ANALYSIS_REPORT_IMPLEMENTATION_PLAN.md    # This file
```

---

## Dependencies

```python
# requirements
pandas
openpyxl
sqlalchemy
pymysql
python-dotenv
tqdm
```

---

## Testing Plan

### Script 1 Testing
1. Verify all tabs are created (UATL_format_1, UATL_format_2, UMTN_excel, Summary)
2. Check row counts match database queries
3. Validate summary aggregations
4. Test Excel formatting (auto-width, freeze panes)

### Script 2 Testing
1. Verify FATAL filtering is correct
2. Check loans_raw has CS and RM derived fields
3. Validate analysis_raw aggregations:
   - no_of_times_fraud matches FATAL count
   - tot_loans matches loans_raw count
   - Payment percentages are correct
4. Verify insight tabs have meaningful data
5. Test with customers who have:
   - No loans
   - No cust_id
   - Multiple submissions by different RMs

---

## Execution Order

1. Run Script 1 first (independent)
2. Run Script 2 (can use Script 1 output or query directly)
3. Review both Excel files
4. Share with stakeholders

---

## Success Criteria

✓ All required tabs are present
✓ Data matches source queries
✓ Aggregations are mathematically correct
✓ Excel files open without errors
✓ Insights are actionable and clear
✓ RM/CS lists are accurate
✓ Business impact metrics are realistic

---

**Status:** Ready for implementation
**Estimated Time:** 3-4 hours
**Priority:** High (EOD deadline)
