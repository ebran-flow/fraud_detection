# Comprehensive Flagging Metrics

## Overview
This document describes all available metrics that can be used to develop a statement flagging logic for fraud detection.

---

## 1. BALANCE VERIFICATION METRICS

### 1.1 Balance Match Status
**Field:** `summary.balance_match` (ENUM)
- **Values:** 'Passed', 'Failed'
- **Current Distribution:** 55.6% Failed
- **Description:** Indicates whether the calculated closing balance matches the statement's closing balance
- **Fraud Risk:** HIGH - Balance mismatches often indicate manipulation

### 1.2 Balance Difference Changes
**Field:** `summary.balance_diff_changes` (INTEGER)
- **Average:** 97.2 changes per statement
- **Max:** 6,449 changes
- **Description:** Number of times the balance difference changed between calculated and reported
- **Fraud Risk:** MEDIUM - High counts may indicate systematic manipulation

### 1.3 Balance Difference Change Ratio
**Field:** `summary.balance_diff_change_ratio` (FLOAT)
- **Average:** 0.0343 (3.43%)
- **Max:** 0.9968 (99.68%)
- **Description:** Ratio of balance difference changes to total transactions
- **Fraud Risk:** HIGH - Ratios >50% are extremely suspicious

### 1.4 Balance Comparison Values
**Fields:**
- `summary.summary_opening_balance` (DECIMAL) - From PDF summary section
- `summary.summary_closing_balance` (DECIMAL) - From PDF summary section
- `summary.first_balance` (DECIMAL) - From first transaction
- `summary.last_balance` (DECIMAL) - From last transaction
- `summary.calculated_closing_balance` (DECIMAL) - Opening + Credits - Debits
- **Fraud Risk:** HIGH - Discrepancies between these indicate tampering

---

## 2. QUALITY ISSUES METRICS

### 2.1 Quality Issues Count
**Field:** `metadata.quality_issues_count` (INTEGER)
- **Average:** 0.1 issues per statement
- **Max:** 553 issues
- **Current:** 0.3% of statements have quality issues
- **Description:** Count of data quality problems detected during parsing
- **Fraud Risk:** MEDIUM-HIGH - Multiple quality issues may indicate tampering

### 2.2 Has Quality Issue Flag (Transaction Level)
**Field:** `uatl_raw_statements.has_quality_issue` (TINYINT)
- **Description:** Boolean flag marking individual transactions with quality issues
- **Fraud Risk:** MEDIUM - Pattern of quality issues across transactions

### 2.3 Header Row Manipulation Count
**Field:** `metadata.header_row_manipulation_count` (INTEGER)
- **Average:** 0.3 manipulations per statement
- **Max:** 450 manipulations
- **Current:** 0.6% of statements have header manipulation
- **Description:** Number of times header rows were detected and manipulated in the data
- **Fraud Risk:** HIGH - Header manipulation often indicates data tampering

---

## 3. DUPLICATE DETECTION METRICS

### 3.1 Duplicate Count
**Field:** `summary.duplicate_count` (INTEGER)
- **Average:** 86.5 duplicates per statement
- **Max:** 13,292 duplicates
- **Current:** 43.4% of statements have duplicates
- **Description:** Number of duplicate transactions detected
- **Fraud Risk:** HIGH - Excessive duplicates can inflate transaction volumes

### 3.2 Is Duplicate Flag (Transaction Level)
**Field:** `uatl_processed_statements.is_duplicate` (TINYINT)
- **Description:** Boolean flag marking individual duplicate transactions
- **Fraud Risk:** HIGH - Pattern analysis of duplicates

---

## 4. GAP & CONTINUITY METRICS

### 4.1 Missing Days Detected
**Field:** `summary.missing_days_detected` (TINYINT)
- **Current:** 48.0% of statements have missing days
- **Description:** Boolean flag indicating gaps in transaction dates
- **Fraud Risk:** MEDIUM - Gaps may indicate selective deletion

### 4.2 Gap Related Balance Changes
**Field:** `summary.gap_related_balance_changes` (INTEGER)
- **Average:** 1.4 changes per statement
- **Max:** 24 changes
- **Description:** Number of balance changes occurring near detected date gaps
- **Fraud Risk:** MEDIUM-HIGH - Balance changes around gaps are suspicious

---

## 5. VERIFICATION STATUS METRICS

### 5.1 Verification Status
**Field:** `summary.verification_status` (VARCHAR)
- **Values:** 'PASS', 'WARNING', 'FAIL'
- **Current Distribution:**
  - PASS: 43.8%
  - WARNING: 0.6%
  - FAIL: 55.6%
- **Description:** Overall verification result
- **Fraud Risk:** Directly indicates fraud likelihood

### 5.2 Verification Reason
**Field:** `summary.verification_reason` (TEXT)
- **Description:** Detailed explanation of verification status
- **Fraud Risk:** Contains specific fraud indicators

---

## 6. FINANCIAL METRICS

### 6.1 Total Credits
**Field:** `summary.credits` (DECIMAL)
- **Description:** Sum of all credit transactions
- **Fraud Risk:** LOW - Used for pattern analysis

### 6.2 Total Debits
**Field:** `summary.debits` (DECIMAL)
- **Description:** Sum of all debit transactions
- **Fraud Risk:** LOW - Used for pattern analysis

### 6.3 Total Fees
**Field:** `summary.fees` (DECIMAL)
- **Description:** Sum of all fee transactions
- **Fraud Risk:** MEDIUM - Unusual fee patterns may indicate manipulation

### 6.4 Total Charges
**Field:** `summary.charges` (DECIMAL)
- **Description:** Sum of all charge transactions
- **Fraud Risk:** MEDIUM - Unusual charge patterns

### 6.5 Credit/Debit Ratio
**Calculated:** `credits / (credits + debits)`
- **Description:** Balance of incoming vs outgoing money
- **Fraud Risk:** MEDIUM - Extreme ratios (>95% or <5%) are suspicious

---

## 7. PARSING & DATA INTEGRITY METRICS

### 7.1 Parsing Status
**Field:** `metadata.parsing_status` (VARCHAR)
- **Values:** 'SUCCESS', 'FAILED'
- **Current:** 100% SUCCESS
- **Description:** Whether the PDF/CSV was successfully parsed
- **Fraud Risk:** HIGH - Parsing failures may indicate tampering

### 7.2 Parsing Error
**Field:** `metadata.parsing_error` (TEXT)
- **Description:** Error message if parsing failed
- **Fraud Risk:** HIGH - Error details may reveal manipulation

### 7.3 Transaction Status (Raw)
**Field:** `uatl_raw_statements.status` (VARCHAR)
- **Values:** 'COMPLETED', 'Transaction Successful', 'IN PROGRESS', etc.
- **Description:** Status from the original statement
- **Fraud Risk:** LOW - Baseline data

---

## 8. TRANSACTION-LEVEL METRICS

### 8.1 Balance Difference (Per Transaction)
**Field:** `uatl_processed_statements.balance_diff` (DECIMAL)
- **Description:** Difference between reported and calculated balance for each transaction
- **Fraud Risk:** HIGH - Non-zero values indicate discrepancies

### 8.2 Balance Difference Change Count (Per Transaction)
**Field:** `uatl_processed_statements.balance_diff_change_count` (INTEGER)
- **Description:** Cumulative count of balance difference changes up to this transaction
- **Fraud Risk:** MEDIUM - Tracks progression of manipulation

### 8.3 Calculated Running Balance
**Field:** `uatl_processed_statements.calculated_running_balance` (DECIMAL)
- **Description:** System-calculated running balance
- **Fraud Risk:** HIGH - Compare with reported balance to detect tampering

---

## 9. METADATA & DOCUMENT METRICS

### 9.1 Number of Rows
**Field:** `metadata.num_rows` (INTEGER)
- **Description:** Total number of transactions in statement
- **Fraud Risk:** LOW - Used for ratio calculations

### 9.2 Statement Period
**Fields:** `metadata.start_date`, `metadata.end_date`
- **Description:** Date range of the statement
- **Fraud Risk:** LOW - Used for time-based analysis

### 9.3 PDF Metadata
**Fields:** `meta_title`, `meta_author`, `meta_producer`, `meta_created_at`, `meta_modified_at`
- **Description:** PDF document metadata
- **Fraud Risk:** MEDIUM - Modified dates or suspicious producers indicate tampering

---

## 10. COMPOSITE/CALCULATED METRICS (TO BE DEVELOPED)

### 10.1 Fraud Risk Score
**Formula:** Weighted combination of all metrics
- Balance match failure: +50 points
- High duplicate ratio (>10%): +30 points
- Balance diff ratio >10%: +40 points
- Quality issues: +5 points each
- Header manipulation: +10 points each
- Missing days: +20 points
- Gap-related balance changes: +15 points each

### 10.2 Data Integrity Score
**Formula:** 100 - (quality_issues * 2) - (header_manipulation * 5) - (parsing_failed * 100)

### 10.3 Transaction Pattern Anomaly Score
**Factors:**
- Unusual credit/debit ratio
- Excessive duplicates
- Irregular transaction timing
- Amount distribution anomalies

---

## RECOMMENDED FLAGGING THRESHOLDS

### 🔴 CRITICAL (Auto-Flag)
- `balance_match = 'Failed'` AND `balance_diff_change_ratio > 0.50`
- `header_row_manipulation_count > 10`
- `balance_diff_changes > 500`
- `verification_status = 'FAIL'` AND `duplicate_count > 1000`

### 🟠 HIGH RISK (Review Required)
- `balance_match = 'Failed'` AND `duplicate_count > 500`
- `balance_diff_change_ratio > 0.20`
- `quality_issues_count > 50`
- `gap_related_balance_changes > 5`
- `verification_status = 'FAIL'`

### 🟡 MEDIUM RISK (Monitor)
- `balance_match = 'Failed'` AND `duplicate_count > 100`
- `duplicate_count > 200`
- `missing_days_detected = 1` AND `gap_related_balance_changes > 0`
- `verification_status = 'WARNING'`
- `quality_issues_count > 10`

### 🟢 LOW RISK (Clean)
- `verification_status = 'PASS'`
- `balance_match = 'Passed'`
- `duplicate_count < 50`
- `quality_issues_count = 0`
- `header_row_manipulation_count = 0`

---

## CURRENT SYSTEM STATUS

**Total Statements:** 20,156

**Distribution:**
- 🟢 Low Risk (VERIFIED): 8,833 (43.8%)
- 🟡 Medium Risk (WARNING): 123 (0.6%)
- 🔴 High Risk (FLAGGED): 11,199 (55.6%)

**Key Observations:**
1. 55.6% of statements have balance verification failures
2. 43.4% have duplicates (avg: 86.5 duplicates)
3. 48.0% have missing days detected
4. Only 0.3% have quality issues (but max is 553!)
5. Only 0.6% have header manipulation (but max is 450!)

**Recommendations:**
1. Implement tiered flagging based on multiple metrics
2. Use machine learning for pattern detection
3. Consider temporal patterns (modification dates)
4. Track fraud patterns across merchants/accounts
5. Implement real-time alerting for critical flags
