# Exposure & Utilization Tab - Summary
**Date:** October 17, 2025
**Status:** ✅ ADDED

---

## Overview

Added new **exposure_utilization** tab to the FATAL analysis report showing total loan exposure breakdown by status, activity, and payment behavior.

---

## Key Metrics

### Total Exposure
**3.43 Billion UGX** (sum of all loans disbursed to 146 FATAL customers)

---

## Breakdown Analysis

### 1. By Last Loan Status

| Category | Amount (UGX) | Percentage | Count |
|----------|-------------|-----------|-------|
| **Ongoing/Due** | 2,080,250,000 | 60.6% | 77 customers |
| **Overdue** | 973,500,000 | 28.4% ⚠️ | 40 customers |
| **Settled** | 376,750,000 | 11.0% | 27 customers |
| **No Loans** | 0 | 0.0% | 2 customers |

**Insight:**
- **60.6%** of exposure is in ongoing/due loans (active business)
- **28.4%** is overdue (973M UGX at risk) ⚠️
- Only **11%** has been settled

---

### 2. By Activity (Last 30 Days)

| Category | Amount (UGX) | Percentage | Count |
|----------|-------------|-----------|-------|
| **Active Customers** | 2,801,500,000 | 81.7% | 105 customers |
| **Inactive Customers** | 629,000,000 | 18.3% | 41 customers |

**Insight:**
- **81.7%** of exposure is with active customers (took loans in last 30 days)
- High engagement despite fraud origins
- Active customers represent 2.8B UGX in total loans disbursed

---

### 3. Historical Payment Behavior

| Category | Amount (UGX) | Percentage |
|----------|-------------|-----------|
| **Paid On Time** (≤1 day late) | 3,104,750,000 | 97.0% |
| **Paid Late** (>1 day late) | 96,750,000 | 3.0% |

**Insight:**
- **97%** of loan amounts were paid on time historically
- Only **3%** paid late (96.8M UGX)
- Excellent payment discipline despite fraudulent entry

---

## Critical Findings

### 🚨 HIGH RISK
1. **973M UGX in overdue loans** (28.4% of total exposure)
   - 40 customers currently overdue
   - Immediate collection action required

### ⚠️ MEDIUM RISK
2. **2.08B UGX in ongoing/due loans** (60.6% of exposure)
   - 77 customers with active loans
   - Monitor closely to prevent default

### ✅ POSITIVE INDICATORS
3. **97% on-time payment rate** historically
   - Suggests genuine businesses despite fraud
   - Not typical "take money and run" scenario

4. **81.7% active engagement**
   - 105 customers took loans in last 30 days
   - Strong business relationship despite fraud origins

---

## Implications

### For Risk Management
- **Focus on 973M UGX overdue exposure** (40 customers)
- Not a credit risk issue - payment behavior is excellent
- Primary concern is entry fraud, not default risk

### For Business Strategy
- **2.8B active customer base** worth preserving
- Consider:
  - Enhanced verification for new loans
  - Grandfather existing good customers
  - Tiered approach based on payment history

### For Recovery
- **Prioritize overdue collection** (973M UGX)
- **Maintain relationship** with on-time payers (3.1B historical)
- **Separate fraud investigation** from credit decisions

---

## Comparison with Previous Metrics

### Outstanding vs Total Exposure
- **Total Exposure:** 3.43B UGX (all loans ever disbursed)
- **Current Outstanding:** 197.9M UGX (only unpaid amount)
- **Paid/Settled:** 3.23B UGX (94.2% already recovered)

**Key Insight:** Most exposure has already been recovered! Current OS is only 5.8% of total exposure.

### Net Impact Refined
- **Total Disbursed:** 3.43B UGX
- **Revenue Collected:** 84.8M UGX (fees)
- **Principal Recovered:** 3.23B UGX (94.2%)
- **Still Outstanding:** 197.9M UGX
- **Net Position:** Mostly recovered, fee revenue secured

---

## Exposure by Customer Segment

From the data, we can infer:

### High Exposure Customers (Ongoing/Due - 2.08B)
- Average: ~27M UGX per customer
- Status: Active, current loans
- Action: Monitor payment behavior

### High Risk Customers (Overdue - 973M)
- Average: ~24M UGX per customer
- Status: Currently overdue
- Action: Immediate collection, escalation

### Settled Customers (377M)
- Average: ~14M UGX per customer
- Status: All loans repaid
- Action: Safe for future lending

---

## Tab Structure

**Columns:**
1. **category** - Breakdown category
2. **amount_ugx** - Total loan amount in UGX
3. **percentage** - Percentage of total exposure

**Sections:**
1. Total exposure
2. By last loan status (ongoing/due/overdue/settled/no loans)
3. By activity (active vs inactive in last 30 days)
4. Historical payment behavior (on-time vs late)

---

## Usage Guide

### For Executive Review
1. **Start here** for overall exposure picture
2. **Focus on:** Overdue amount (973M UGX)
3. **Good news:** 97% historical on-time payment

### For Risk Committee
1. **Total exposure:** 3.43B UGX
2. **At risk:** 28.4% (overdue customers)
3. **Recovery rate:** 94.2% (most already paid back)

### For Collections Team
1. **Priority:** 973M UGX overdue exposure
2. **40 customers** to contact
3. **Historical behavior:** 97% on-time (likely recoverable)

---

## Technical Implementation

### Data Sources
- **analysis_raw:** Customer-level aggregations (tot_loans, last_loan_status, days_since_last_loan)
- **loans_raw:** Individual loan records (loan_principal, overdue_days_calc, paid_date)

### Calculations

**Total Exposure per Customer:**
```python
total_disbursed = loans_df.groupby('cust_id')['loan_principal'].sum()
```

**By Last Loan Status:**
```python
exposure_ongoing = customers[customers['last_loan_status'].isin(['ongoing', 'due'])]['total_disbursed'].sum()
```

**Historical Payment:**
```python
ontime_amount = paid_loans[paid_loans['overdue_days_calc'] <= 1]['loan_principal'].sum()
late_amount = paid_loans[paid_loans['overdue_days_calc'] > 1]['loan_principal'].sum()
```

---

## File Location

**Report:** `docs/analysis/fatal_analysis_report.xlsx`
**Tab:** `exposure_utilization` (Tab 9)
**Script:** `scripts/analysis/export_fatal_analysis.py`

---

## Next Steps

### Immediate
1. **Review 973M UGX overdue exposure** - 40 customers
2. **Validate exposure calculations** with finance team
3. **Share with risk committee** for policy decisions

### Short-term
4. **Segment customers** by exposure level (high/medium/low)
5. **Develop recovery strategy** for overdue segment
6. **Create monitoring dashboard** for exposure trends

### Long-term
7. **Track exposure over time** (monthly snapshots)
8. **Correlate exposure with fraud patterns**
9. **Refine lending policies** based on findings

---

## Key Takeaways

✅ **Total exposure is manageable** at 3.43B UGX
✅ **94.2% already recovered** (3.23B paid back)
✅ **97% on-time payment** shows good credit quality
⚠️ **28.4% currently overdue** needs immediate attention
⚠️ **40 customers at risk** (973M UGX)

**Conclusion:** Despite fraud entry, these are generally good customers with excellent payment behavior. Focus on collection of overdue amounts while maintaining business relationships with on-time payers.

---

**Status:** ✅ COMPLETE
**Report Updated:** Yes
**Tab Position:** 9 of 9
**Ready for Use:** Yes
