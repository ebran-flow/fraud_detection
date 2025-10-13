# Transaction Reversal Handling

## Problem with Airtel Statements

**Airtel produces inconsistent statements where Transaction Reversals behave unpredictably:**
- Some reversals affect the balance
- Some reversals don't affect the balance
- **Within the SAME statement**, different reversals can behave differently

This inconsistency makes it impossible to create a blanket rule (format-based, date-based, or even per-statement detection).

## Solution: Treat as Normal Transactions

**Transaction Reversals are now treated as NORMAL transactions.**

They are processed exactly like any other transaction:
- Apply the reversal amount to the running balance
- Calculate balance differences normally
- No special detection or logic

### Transaction Processing Flow

```python
for transaction in statement:
    if transaction.type == 'Commission Disbursement':
        # Special handling: invert amount
        running_balance += -transaction.amount

    elif transaction.type in ['Deallocation Transfer', 'Rollback']:
        # Special handling: skip (don't affect balance)
        running_balance = running_balance

    elif transaction.type == 'Transaction Reversal':
        # NEW: Treat as NORMAL transaction
        running_balance = apply_transaction(running_balance, transaction)

    else:
        # Normal transaction
        running_balance = apply_transaction(running_balance, transaction)
```

## Special Transaction Types

| Type | Handling | Reason |
|------|----------|--------|
| **Commission Disbursement** | Invert amount | Moves money between wallets (Regular ↔ Commission) |
| **Deallocation Transfer** | Skip | Doesn't affect main balance |
| **Rollback** | Skip | Doesn't affect main balance |
| **Transaction Reversal** | **NORMAL** | **Inconsistent behavior - treat as normal** |

## Why This Approach?

### Attempted Solutions (Failed)

1. ❌ **Format-based:** "Reversals don't affect balance in Format X"
   - Failed: Both formats show inconsistent behavior

2. ❌ **Date-based:** "Reversals changed on date X"
   - Failed: Unknown exact date, and exceptions exist

3. ❌ **Per-statement detection:** "Detect if majority of reversals affect balance"
   - Failed: Within the same statement, some affect and some don't

### Current Solution (Works)

✅ **Treat as normal:** Apply all reversals to balance
- Simple and consistent
- No complex detection logic
- Works for most statements
- Balance differences will show where Airtel's data is wrong

## Impact

### Balance Matching

**Before (skipping reversals):**
```
Statement with 10 reversals:
- 7 reversals affect balance (applied by Airtel)
- 3 reversals don't affect balance (not applied by Airtel)

Our calculation: Skips all 10 reversals
Result: Balance mismatch ❌
```

**After (applying all reversals):**
```
Statement with 10 reversals:
- 7 reversals affect balance (applied by Airtel)
- 3 reversals don't affect balance (not applied by Airtel)

Our calculation: Applies all 10 reversals
Result: Balance mismatch for 3 transactions ❌

BUT: We can identify which 3 are problematic via balance_diff
```

### Verification Status

- Statements with consistent reversals: **PASS** ✅
- Statements with inconsistent reversals: **WARNING** or **FAIL** ⚠️
- Use `balance_diff` and `balance_diff_change_count` to identify problem transactions

## Code Changes

### Files Modified

**`/app/services/processor.py`**

**Lines 203-206:** Added Transaction Reversal detection
```python
# Mark Transaction Reversals for tracking
reversal_mask = df['description'].str.contains('Transaction Reversal', case=False, na=False)
df.loc[reversal_mask, 'is_special_txn'] = True
df.loc[reversal_mask, 'special_txn_type'] = 'Transaction Reversal'
```

**Lines 354-363:** Skip only Deallocation and Rollback
```python
# Only these special transactions are skipped:
elif row.get('is_special_txn', False) and row.get('special_txn_type') in ['Deallocation Transfer', 'Rollback']:
    # Don't update running_balance
```

**Lines 365-386:** Transaction Reversals fall through to normal processing
```python
else:
    # Normal transaction processing
    # Transaction Reversals are processed here now
    running_balance = apply_transaction(...)
```

## Identifying Problematic Statements

### Query for Reversals with Balance Issues

```sql
-- Find statements with Transaction Reversals and balance mismatches
SELECT
    s.run_id,
    s.acc_number,
    COUNT(p.id) as reversal_count,
    s.balance_diff_changes,
    s.verification_status
FROM summary s
JOIN uatl_processed_statements p ON s.run_id = p.run_id
WHERE p.special_txn_type = 'Transaction Reversal'
  AND s.balance_match = 'Failed'
GROUP BY s.run_id, s.acc_number, s.balance_diff_changes, s.verification_status
ORDER BY reversal_count DESC;
```

### Inspect Individual Reversal Transactions

```sql
-- See which specific reversals have balance issues
SELECT
    p.txn_id,
    p.txn_date,
    p.description,
    p.amount,
    p.balance,
    p.calculated_running_balance,
    p.balance_diff
FROM uatl_processed_statements p
WHERE p.special_txn_type = 'Transaction Reversal'
  AND ABS(p.balance_diff) > 0.01
ORDER BY p.txn_date DESC
LIMIT 50;
```

## Benefits of Simple Approach

✅ **No Complex Logic:** Easy to understand and maintain
✅ **Consistent Processing:** All reversals treated the same way
✅ **Tracks for Reporting:** Still marked as `special_txn_type = 'Transaction Reversal'`
✅ **Identifies Bad Data:** Balance differences show where Airtel's data is inconsistent
✅ **No False Negatives:** Doesn't skip reversals that should be applied

## Related Documentation

- **Implicit Fees:** `/docs/IMPLICIT_FEES_UPDATE.md`
- **Quality Tracking:** `/docs/migrations/QUALITY_TRACKING_MIGRATION.md`
- **Balance Utils:** `/app/services/balance_utils.py`
- **Processor:** `/app/services/processor.py`

---

**Updated:** 2025-10-13
**Decision:** Treat Transaction Reversals as normal transactions
**Reason:** Airtel's inconsistent behavior makes special handling impossible
