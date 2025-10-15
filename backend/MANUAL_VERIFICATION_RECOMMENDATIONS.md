# Manual Verification Recommendations
# Header Manipulation Scan Results

**Scan Date:** October 15, 2025
**Total Statements Scanned:** 10,557 (Format 2 UATL only)
**Manipulated Statements Found:** 126 (1.2%)

---

## Summary Statistics

- **Balance Match Failed:** 126 (100.0%)
- **Balance Match Success:** 0 (0.0%)
- **Average change_ratio:** 0.7149
- **Max change_ratio:** 0.9178
- **Min change_ratio:** 0.1489
- **Total duplicate transactions:** 9,958
- **Total quality issues:** 94

## Key Findings

✅ **Validation Successful:** 100% of manipulated statements have `balance_match='Failed'`
✅ **No False Positives:** 0 statements with `balance_match='Success'` were flagged
⚠️ **High Correlation:** Header manipulation strongly correlates with balance failures

---

## Priority 1: Highest Severity (Top 5)

These statements have the highest change_ratio (>0.90) and require immediate verification:

### 1. **Run ID: 68a6b12818ebb**
- **Account:** 702234867
- **Change Ratio:** 0.9178 (91.78% of balances wrong!)
- **Duplicates:** 77
- **Total Rows:** 2,421
- **Manipulated Pages:** 38 out of 94 pages (40%)
- **Severity:** CRITICAL
- **PDF Path:** Check database for pdf_path
- **Recommendation:**
  - Open PDF and verify pages 3-40 manually
  - Cross-check transaction IDs for duplicates
  - Look for gaps in transaction sequences

### 2. **Run ID: 68a6b2a0badaa**
- **Account:** 702234867 (SAME ACCOUNT AS #1)
- **Change Ratio:** 0.9178
- **Duplicates:** 77
- **Total Rows:** 2,421
- **Severity:** CRITICAL
- **Recommendation:**
  - This is the same account as #1 - likely multiple submissions
  - Check dates to see if these are duplicates or sequential fraud attempts

### 3. **Run ID: 683fe53535d3d**
- **Account:** 759376503
- **Change Ratio:** 0.9005
- **Duplicates:** 10
- **Total Rows:** 2,191
- **Manipulated Pages:** 29 out of total
- **Severity:** CRITICAL
- **Recommendation:**
  - Verify transaction continuity across pages
  - Check for missing transaction IDs (gaps indicate deletions)

### 4. **Run ID: 6874a61d1670f**
- **Account:** 749367753
- **Change Ratio:** 0.8996
- **Duplicates:** 11
- **Total Rows:** 2,191
- **Severity:** HIGH
- **Recommendation:**
  - Check PDF metadata (creation date vs statement period)
  - Look for font inconsistencies between pages

### 5. **Run ID: 686f86b24b644**
- **Account:** 749367753 (SAME ACCOUNT AS #4)
- **Change Ratio:** 0.8996
- **Duplicates:** 11
- **Total Rows:** 2,191
- **Severity:** HIGH
- **Recommendation:**
  - Pattern suggests systematic fraud on this account
  - Review all statements for this account

---

## Priority 2: Repeat Offenders (Top 5 Accounts)

Accounts with multiple manipulated statements - indicates systematic fraud:

### 1. **Account: 749367753** (6 statements)
- **Run IDs:** 686f9005e6ec3, 6874a61d1670f, 6858fe66d1674, 686f86b24b644, 686f90a8be15c, 686f9b6cd5497
- **Total Duplicates:** 462 across all statements
- **Average Change Ratio:** 0.7863
- **Recommendation:**
  - RED FLAG - 6 manipulated statements from same account
  - Escalate to fraud investigation team immediately
  - Review ALL statements from this account (not just flagged ones)

### 2. **Account: 740066114** (5 statements)
- **Total Duplicates:** 375
- **Average Change Ratio:** 0.8810
- **Recommendation:** High-priority investigation required

### 3. **Account: 743477442** (5 statements)
- **Total Duplicates:** 165
- **Average Change Ratio:** 0.8061
- **Recommendation:** High-priority investigation required

### 4. **Account: 752958062** (4 statements)
- **Total Duplicates:** 104
- **Average Change Ratio:** 0.8927
- **Recommendation:** Medium-priority investigation

### 5. **Account: 750335041** (4 statements)
- **Total Duplicates:** 352
- **Average Change Ratio:** 0.8787
- **Recommendation:** Medium-priority investigation

---

## Priority 3: Random Sample Verification (5 statements)

To validate the detection algorithm, manually verify these random samples:

### 1. **Run ID: 67d322713b2c7**
- **Change Ratio:** 0.8925
- **Manipulated Pages:** 35
- **Reason:** Large number of pages flagged - good test case

### 2. **Run ID: 6826d05aa24fb**
- **Change Ratio:** 0.8927
- **Manipulated Pages:** 29
- **Reason:** Mid-range change ratio

### 3. **Run ID: 682afeb0c727d**
- **Change Ratio:** Medium
- **Reason:** Test detection accuracy on mid-severity cases

### 4. **Run ID: 67fcf4202f992**
- **Change Ratio:** 0.1489 (LOWEST)
- **Reason:** Lowest change ratio - verify it's not a false positive

### 5. **Run ID: 6836dd3e1dc65**
- **Change Ratio:** Low-medium
- **Reason:** Recent submission date (check PDF metadata)

---

## Verification Checklist

For each statement you verify manually:

### Visual PDF Inspection
- [ ] Open the PDF in a viewer
- [ ] Check pages 2+ for header rows appearing mid-page
- [ ] Look for inconsistent page structures
- [ ] Verify transaction flow continuity
- [ ] Check for visual editing artifacts (copy-paste borders, alignment issues)

### Data Integrity Checks
- [ ] Verify no duplicate transaction IDs exist
- [ ] Check for gaps in transaction ID sequences
- [ ] Validate timestamps are chronological
- [ ] Confirm balance calculations manually for 5-10 transactions
- [ ] Check if summary balances match first/last transaction balances

### Metadata Analysis
- [ ] Check PDF creation date vs statement period (should be close)
- [ ] Verify PDF producer is "iText® 5.3.4" by "MOBIQUITY" (legitimate Airtel)
- [ ] Check if modification date differs from creation date (red flag)

### Cross-Reference
- [ ] Compare with other statements from same account
- [ ] Check if customer has history of suspicious activity
- [ ] Verify account details match customer records

---

## How to Access Statements

### Using CSV Export
```bash
python scripts/utils/convert_results_to_csv.py
# Opens: header_manipulation_results.csv in Excel
# Filter: is_manipulated = YES
```

### Using Database Query
```sql
SELECT
    m.run_id,
    m.acc_number,
    m.pdf_path,
    s.balance_match,
    s.balance_diff_change_ratio,
    s.duplicate_count
FROM metadata m
LEFT JOIN summary s ON m.run_id = s.run_id
WHERE m.run_id IN ('68a6b12818ebb', '68a6b2a0badaa', '683fe53535d3d')
ORDER BY s.balance_diff_change_ratio DESC;
```

### Using Python Script
```python
import json
with open('header_manipulation_results.json', 'r') as f:
    data = json.load(f)

# Find specific run_id
for result in data['results']:
    if result['run_id'] == '68a6b12818ebb':
        print(f"PDF Path: {result['pdf_path']}")
        print(f"Bad pages: {result['bad_pages']}")
```

---

## Expected Outcomes

### If Manipulation Confirmed:
1. Mark statement as fraudulent in database
2. Add to fraud case file for customer
3. Flag account for enhanced monitoring
4. Consider legal action if systematic fraud

### If False Positive:
1. Document why it was flagged incorrectly
2. Add to test cases for algorithm improvement
3. Check if format variation needs handling

---

## Next Steps

1. **Immediate (Today):**
   - Verify Priority 1 statements (5 statements)
   - Escalate accounts with 4+ manipulated statements

2. **This Week:**
   - Review all statements from Priority 2 accounts (23 statements)
   - Complete random sample verification (5 statements)

3. **This Month:**
   - Systematic review of remaining 93 statements
   - Generate fraud investigation reports
   - Update customer risk scores

---

## Contact

**Generated by:** Header Manipulation Detection System
**Script:** `scripts/analysis/scan_header_manipulation.py`
**Results:** `header_manipulation_results.json` and `.csv`
**Documentation:** `scripts/README.md`

---

## Full List of Manipulated Run IDs

For reference, here are all 126 manipulated run_ids (sorted by change_ratio descending):

```
68a6b12818ebb, 68a6b2a0badaa, 683fe53535d3d, 6874a61d1670f, 686f86b24b644,
686f9005e6ec3, 686f90a8be15c, 686f9b6cd5497, 6858fe66d1674, 687f5effa5288,
687893e5513ad, 68779e5a4744b, 6877a008ebbbf, 683802b110ba7, 683815bc12ce7,
68383f253f2b7, 6835701ad4a5e, 6828918934778, 6825b2c50cd59, 6826d05aa24fb,
6826f1885bcb8, 6826f188ccacc, 6826f49fdc822, 6815f94eb57bf, 6815fad130282,
68138bbe88ddb, 6807984f9d828, 67d322713b2c7, 680c90519a1c1, 67e1104a0b0ce,
... (126 total - see header_manipulation_results.csv for complete list)
```
