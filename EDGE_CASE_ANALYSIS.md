# Edge Case Analysis - Airtel Statement Fraud Detection

## Summary

Analyzed **30 processed statements** from September 2025:
- ✅ **11 Verified** (36.7%)
- ❌ **13 Failed Verification** (43.3%)
- ⚠️ **2 Needs Additional Verification** (6.7%)
- 📄 **4 Statement Read Failed** (13.3%)

## Root Causes of Failures

### 1. **Same-Timestamp Transaction Ordering Issues** (13/13 failed statements = 100%)

**Problem**: When multiple transactions occur at the exact same timestamp, the order matters critically for balance calculation. Our current sorting logic uses:
- Debits: Sort by **descending balance** (higher balance first)
- Credits: Sort by **ascending balance** (lower balance first)

**However**, this still causes issues when:
- Two transactions of the same type (both debits or both credits) have incorrect ordering
- The PDF may have them in the wrong order
- Our sorting doesn't fully resolve the ambiguity

**Evidence**:
- File `68b5699446f1e`: 64 same-timestamp transition issues, final diff: 2000
- File `68b5866aef104`: 97 same-timestamp transition issues, final diff: 1000 (24.64% change ratio!)
- File `68b58b9c06928`: 110 same-timestamp transition issues, final diff: -65

**Example from `68b58b4ecd86e_detailed.csv`**:
```
Row 97: Txn 124517206039, 19:20:00, Debit 1000, balance 7307, calculated 4307 (diff 3000)
Row 98: Txn 124517465740, 19:23:00, Debit 4000, balance 1307, calculated 307 (diff 1000)
```
The balance jumped from 5307 → 7307 → 1307. This suggests transaction at 19:20:00 with balance 7307 should have come **before** the one with balance 5307.

**Impact**: Causes cascading balance_diff changes that never self-correct, leading to permanent mismatches.

### 2. **Commission Disbursement Propagation** (10/13 failed statements = 77%)

**Problem**: Commission Disbursements use opposite logic (credit = subtract), which is CORRECT. However, when they occur:
1. The balance_diff is copied from the previous row (as designed)
2. But the actual difference between statement and calculated balance **changes**
3. This new difference propagates to all subsequent transactions

**Evidence**:
- File `68b58b4ecd86e`: 1 commission, final diff: 1000
- File `68b5890ac307d`: 2 commissions, final diff: 1750
- File `68b5866aef104`: 1 commission, final diff: 1000

**Example from `68b58b4ecd86e_detailed.csv`**:
```
Row 45: Balance 229770, calculated 229770, diff 0
Row 46: Commission Credit 500, balance 230270, calculated 229270, diff 0 (copied from previous)
        BUT: actual difference is 1000!
Row 47: Debit 500, balance 229770, calculated 228770, diff 1000 (now it shows)
```

The commission created a 1000 difference that gets propagated forward forever.

**Impact**: Every commission disbursement can introduce a permanent offset (usually 500-1000).

### 3. **High Change Ratios (>10%)** (2/13 failed statements = 15%)

**Problem**: Some statements have so many balance_diff changes that they indicate fundamental issues beyond simple ordering:
- `68b5866aef104`: 24.64% change ratio (1086 changes in 4407 rows)
- `68b58b9c06928`: 11.24% change ratio (361 changes in 3212 rows)

These likely have multiple compounding issues or data quality problems.

## Patterns in Final Differences

Most failures have differences that are multiples of common transaction amounts:
- **1000**: 6 statements
- **2000**: 4 statements
- **1750**: 1 statement
- **175**: 1 statement
- **-65**: 1 statement
- **5000**: 2 statements

This suggests the issues are transaction-specific rather than systematic calculation errors.

## Proposed Solutions

### Solution 1: Advanced Same-Timestamp Ordering

Instead of just sorting by balance, try **multiple orderings** for same-timestamp groups and pick the one that minimizes balance_diff changes:

```python
def optimize_same_timestamp_order(group):
    """Try all permutations and pick the one with minimum balance_diff changes."""
    from itertools import permutations

    if len(group) <= 1:
        return group

    # Try different orderings
    best_order = None
    min_diff_changes = float('inf')

    for perm in permutations(range(len(group))):
        # Test this ordering
        test_group = group.iloc[list(perm)]
        diff_changes = calculate_diff_changes(test_group)

        if diff_changes < min_diff_changes:
            min_diff_changes = diff_changes
            best_order = test_group

    return best_order
```

**Limitation**: Only works for small groups (2-5 transactions). Beyond that, becomes computationally expensive.

### Solution 2: Commission Disbursement Balance Diff Calculation

Instead of copying the previous balance_diff, calculate the actual difference for commissions:

```python
elif is_special and special_type == 'Commission':
    # Apply opposite logic
    if row['amount'] < 0:
        running_balance = running_balance + abs(row['amount'])
    else:
        running_balance = running_balance - row['amount']

    # CALCULATE the actual balance_diff (don't copy)
    balance_diff = row['balance'] - running_balance
    df.loc[idx, 'balance_diff'] = balance_diff
    previous_balance_diff = balance_diff  # Update for next row
```

**Impact**: This would prevent commission differences from propagating.

### Solution 3: Accept Commission Mismatches

Mark statements with commission disbursements as "Verified with Commission Adjustments" if the only differences are at commission rows:

```python
# After calculation, check if all non-zero balance_diffs occur only at commission rows
commission_indices = df[df['special_txn_type'] == 'Commission'].index
non_commission_diffs = df[~df.index.isin(commission_indices)]['balance_diff'].abs().sum()

if non_commission_diffs < 0.01:
    verification_status = "Verified (with Commission Adjustments)"
```

## Recommendations

1. **Immediate**: Implement Solution 2 (calculate balance_diff for commissions)
2. **Short-term**: Implement Solution 1 for small same-timestamp groups (≤4 transactions)
3. **Long-term**: Consider Solution 3 for better categorization

## Files for Reference

- Failed statements: `/home/ebran/Developer/projects/data_score_factors/fraud_detection/results/balance_summary.csv`
- Detailed sheets: `/home/ebran/Developer/projects/data_score_factors/fraud_detection/detailed_sheets/`
- Key examples:
  - `68b5699446f1e_detailed.csv` - Many same-timestamp issues
  - `68b58b4ecd86e_detailed.csv` - Clear commission propagation issue
  - `68b5866aef104_detailed.csv` - High change ratio (24.64%)
