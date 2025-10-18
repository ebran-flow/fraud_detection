# FATAL Analysis Report - Updates Applied
**Date:** October 17, 2025
**Status:** ✅ COMPLETE

---

## Issues Fixed

### 1. ✅ analysis_raw Tab - Filter to FATAL Customers Only
**Problem:** Tab was showing all 10,555 customers in database
**Fix:** Now shows only 146 FATAL customers (those with fraud submissions)
**Impact:** Reduced from 10,555 → 146 rows (99% reduction)

**Implementation:**
```python
# Before: Queried ALL customers from customer_details
# After: Only query customers with FATAL statements
fatal_cust_ids = fatal_df['cust_id'].dropna().unique().tolist()
query = f"... WHERE cd.cust_id IN ('{cust_id_list}')"
```

---

### 2. ✅ Added New Columns to analysis_raw

#### crnt_fa_limit
- **Source:** customer_details.crnt_fa_limit
- **Type:** DECIMAL(18,2)
- **Description:** Current Float Advance limit for the borrower

#### last_loan_amount
- **Source:** loans.loan_principal of most recent loan (by disbursal_date)
- **Type:** DECIMAL(18,2)
- **Description:** Principal amount of last loan disbursed

**Sample Data:**
```
cust_id      | no_of_times_fraud | tot_loans | last_loan_amount | last_loan_status
-------------|-------------------|-----------|------------------|------------------
UFLW-10191   | 1                 | 102       | 2,000,000        | overdue
UFLW-103204  | 2                 | 18        | 750,000          | ongoing
UFLW-103264  | 2                 | 9         | 2,500,000        | due
```

---

### 3. ✅ Updated business_impact Tab Structure

**New Format:**
```
Total FATAL Customers: 146

By Last Disbursed Loan Status:
  - Customers Ongoing/Due: 77
  - Customers Overdue: 40
  - Customers Settled: 27
  - Customers No Loans: 2

By Activity:
  - Customers Active (loan in last 30 days): 105

Financial:
  - Total Outstanding Amount: 197,862,200 UGX
  - Total Revenue Collected: 84,764,200 UGX
  - Net Impact: -113,098,000 UGX (LOSS)
```

**Key Changes:**
- Added breakdown by last loan status (ongoing/due/overdue/settled/no loans)
- Sum of status categories = Total FATAL customers (146)
- Clearer hierarchy with section headers

---

### 4. ✅ Updated RM_Submitted Tab

**New Column Added:** `Total Customers in Overdue`
- Shows count of customers with tot_overdue_loans > 0
- Helps identify RMs with high-risk portfolios

**Sample Data:**
```
RM Name            | Unique Customers | Total Fraud | Total OS    | Total Revenue | Customers Overdue
-------------------|------------------|-------------|-------------|---------------|------------------
WAKWESA HERMAN     | 33               | 49          | 34,265,000  | 19,704,500    | 0
MUGISHA DENIS      | 23               | 41          | 49,643,000  | 11,560,000    | 16
ISABIRYE PATRICK   | 32               | 40          | 38,246,800  | 19,444,100    | 6
```

**Insight:** MUGISHA DENIS has 16 customers in overdue despite fewer fraud submissions than WAKWESA.

---

### 5. ✅ Updated CS_Analysis Tab

**New Column Added:** `Total Loans Overdue`
- Shows count of loans with status = 'overdue'
- Identifies CS with high default rates

**Sample Data:**
```
CS Name               | CS Role   | Unique Customers | Total Loans | Loans Overdue
----------------------|-----------|------------------|-------------|---------------
CRISTINE NAMUGERWA    | customer  | 1                | 100         | 1
JOYCE NAMATOVU        | customer  | 1                | 95          | 0
KENEDY KEN SENAMBI    | customer  | 1                | 75          | 0
DAVID CHWA SSENDI     | customer  | 1                | 67          | 0
MUSA NYUNYU           | customer  | 1                | 63          | 1
```

**Insight:** CRISTINE NAMUGERWA applied for 100 loans for 1 customer (unusual pattern).

---

### 6. ✅ Removed Tabs Per Requirements

**Tabs Removed:**
- ~~RM_Registered~~ - Per user request: "let's not consider registered RMs"
- ~~RM_Overdue_Disbursals~~ - Redundant with overdue info in RM_Submitted

**Tabs Remaining (8 total):**
1. FATAL_filtered
2. loans_raw
3. analysis_raw
4. business_impact
5. RM_Submitted
6. CS_Analysis
7. os_vs_revenue
8. monthly_trends

---

## Current File Stats

**File:** `docs/analysis/fatal_analysis_report.xlsx`
**Size:** 0.34 MB (down from 1.20 MB - 72% reduction)
**Rows Reduced:**
- analysis_raw: 10,555 → 146 (99% reduction)
- Total report is more focused and relevant

---

## Key Metrics from Updated Report

### Financial Impact
- **Net Loss:** 113.1M UGX (increased from 111.6M)
- **Outstanding:** 197.9M UGX
- **Revenue:** 84.8M UGX

### Customer Breakdown by Last Loan Status
- **Ongoing/Due:** 77 customers (53%)
- **Overdue:** 40 customers (27%) ⚠️ HIGH RISK
- **Settled:** 27 customers (18%)
- **No Loans:** 2 customers (1%)

### Activity
- **Active (last 30 days):** 105 customers (72%)
- Very high engagement despite fraud

### Top Risk Areas
1. **MUGISHA DENIS:** 16 customers in overdue, 49.6M OS
2. **ISABIRYE PATRICK:** 6 customers in overdue, 38.2M OS
3. **WAISWA HAKIM:** 7 customers in overdue, 15.9M OS

---

## Technical Changes

### Script Updates
**File:** `scripts/analysis/export_fatal_analysis.py`

**Changes:**
1. Filter customer_details query to only FATAL customers
2. Added crnt_fa_limit to customer query
3. Added last_loan_amount calculation in loan_stats
4. Handle customers with no loans (last_loan_status = 'No Loans')
5. Updated business_impact format with status breakdown
6. Added overdue counts to RM_Submitted
7. Added overdue loan counts to CS_Analysis
8. Removed RM_Registered and RM_Overdue_Disbursals tabs

---

## Verification Results

### analysis_raw Tab
✅ Total rows: 146 (only FATAL customers)
✅ Contains: crnt_fa_limit column
✅ Contains: last_loan_amount column
✅ All customers have no_of_times_fraud > 0

### business_impact Tab
✅ Structured format with sections
✅ Status breakdown sums to 146
✅ Financial metrics accurate

### RM_Submitted Tab
✅ Contains: Total Customers in Overdue column
✅ Sorted by Total Fraud Submissions
✅ Shows risk profile per RM

### CS_Analysis Tab
✅ Contains: Total Loans Overdue column
✅ Sorted by Total Loans Applied
✅ Identifies high-volume patterns

---

## Re-run Instructions

To regenerate the report with latest data:

```bash
python scripts/analysis/export_fatal_analysis.py
```

**Runtime:** ~2 minutes
**Output:** `docs/analysis/fatal_analysis_report.xlsx`

---

## Usage Guide

### For Management Review
1. **Start with:** business_impact tab - Overall picture
2. **Then review:** RM_Submitted - Who submitted fraud
3. **Check:** CS_Analysis - Who applied for loans
4. **Deep dive:** analysis_raw - Customer-level details

### For Risk Analysis
1. **High Risk Customers:** Filter analysis_raw where tot_overdue_loans > 0
2. **High Risk RMs:** Sort RM_Submitted by "Total Customers in Overdue"
3. **High Risk CS:** Sort CS_Analysis by "Total Loans Overdue"

### For Recovery Planning
1. **Use:** os_vs_revenue tab
2. **Filter:** Customers with net_impact < 0 (loss-making)
3. **Prioritize:** Highest OS amount first

---

## Next Steps Recommended

### Immediate
1. **Contact 40 overdue customers** - Highest priority
2. **Review MUGISHA DENIS portfolio** - 16 overdue customers
3. **Investigate CRISTINE NAMUGERWA** - 100 loans to 1 customer (unusual)

### Short-term
4. **RM training** - Focus on top 5 RMs with overdue customers
5. **CS policy review** - Single-customer high-volume patterns
6. **Recovery strategy** - 113M UGX net loss

### Long-term
7. **Predictive monitoring** - Flag similar patterns in real-time
8. **Automated alerts** - When CS exceeds normal loan application rates
9. **Risk scoring** - Integrate fraud patterns into credit decisions

---

**Status:** ✅ ALL UPDATES COMPLETE
**Report Ready:** Yes
**Verified:** Yes
