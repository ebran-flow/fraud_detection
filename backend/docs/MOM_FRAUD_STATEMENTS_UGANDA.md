# Minutes of Meeting - Fraud Statements Analysis (Uganda)

**Date**: 2025-10-18
**Attendees**: Nitin, Praveen, Abhi, and team
**Topic**: Fraud Statements in Airtel Uganda

---

## Discussion Points

### 1. Airtel Statement Formats
- Discussed different statement formats in Airtel Uganda
- **Old formats**: format_2 (processed since 2023-05-31)
- **New format**: format_1 (started receiving from July 2025)

### 2. New Format Analysis (format_1)
- **Complete analysis performed** on new format submissions
- **Total submissions**: 1,850
- **Results**:
  - ✓ **79 confirmed as FATAL** (manipulated statements)
  - ✓ **1,771 confirmed as VALID** (genuine statements)
  - ✓ **0 unknown/unverified**

### 3. Key Findings - Fraud Submissions

**Top RMs submitting fraudulent statements:**
1. **Mugisha Denis**: 28 new format_1 submissions
2. **Herman (Wakwesa Herman)**: 21 new format_1 submissions

**Impact Summary:**
- 79 FATAL customers identified from new format
- Outstanding Amount (OS): 137.3M UGX
- Overdue Amount (OD): 88.6M UGX
- Net financial impact: -141M UGX

### 4. Report Tabs Referenced

**analysis_raw tab**:
- Contains detailed customer information for all 79 FATAL cases
- Includes fraud history, loan performance, payment behavior
- Shows RM involvement and customer lifecycle data

**RM_Submitted tab**:
- Groups OS and OD amounts by Relationship Manager
- Shows fraud submission counts per RM
- Highlights "New Submissions" column tracking format_1 submissions since July 2025
- Provides breakdown of customers in overdue by RM

---

## Actions Taken

### 1. Customer Restrictions Applied
All 146 FATAL customers have been restricted with the following controls:
- ❌ **Unable to apply for new loans**
- ❌ **Unable to request FA (Facility Amount) upgrade**
- ❌ **Unable to auto-upgrade after 5 on-time repayments**
- ❌ **Unable to initiate reassessment**

### 2. RM Account Restrictions
The following Relationship Managers have been restricted with the same controls:
1. **MUGISHA DENIS** - 28 new format_1 fraud submissions
2. **WAKWESA HERMAN** - 21 new format_1 fraud submissions
3. **WAISWA HAKIM**
4. **FRANCIS ARINAITWE**
5. **CHISTOPHER TWESIGE**

**Rationale**: These RMs have demonstrated patterns of submitting manipulated statements, posing significant risk to portfolio quality.

---

## How to Use analysis_raw Tab

The `analysis_raw` tab provides comprehensive customer-level intelligence for identifying fraud patterns:

**Key Columns for RM Analysis:**
- `rm_name`: Most frequent RM who submitted fraud statements for this customer
- `first_rm_name` / `last_rm_name`: Track RM changes over time
- `no_of_times_fraud`: Number of fraudulent submissions per customer
- `first_submitted_date` / `last_submitted_date`: Timeline of fraud activity

**Financial Impact Columns:**
- `tot_os_amount`: Outstanding amount (ongoing/due loans)
- `tot_od_amount`: Overdue amount (loans in default)
- `tot_revenue`: Total revenue collected from customer
- `last_loan_status`: Current loan state (overdue/ongoing/settled)

**Usage Example:**
Filter by `rm_name = "MUGISHA DENIS"` to see all 28 customers with fraudulent statements submitted by this RM, along with their current financial exposure and loan performance.

**Note**: Detailed analysis report is attached. Full comprehensive report with all tabs will be shared separately.

---

## Next Steps

- Monitor existing loan repayments from restricted customers
- Review old format (format_2) verification backlog (9,953 unknown statements)
- Continue surveillance on other RMs with fraud submissions
- Track effectiveness of restrictions applied

---

## Report Location
`/home/ebran/Developer/projects/airtel_fraud_detection/backend/docs/analysis/fatal_analysis_report.xlsx`

## Key Metrics Referenced
- Total FATAL customers: 146 (79 from new format, 67 from old format)
- Total fraud submissions: 286 statements
- Analysis period: July 2025 onwards for new format
