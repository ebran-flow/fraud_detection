# Implicit Fees Update - All Airtel Formats

## Overview
Updated implicit fees calculation (`calculate_implicit_fees_format1`) to apply to **ALL Airtel formats** (Format 1 and Format 2), not just Format 1.

## What are Implicit Fees?

Implicit fees are transaction costs that are **not shown in the fee column** but must be accounted for in balance calculations:

### 1. IND02 Commission (0.5%)
- **Transaction Type:** IND02 transactions (not IND01)
- **Fee:** 0.5% of transaction amount
- **Impact:** Reduces balance

### 2. Merchant Payment Cashback (4%)
- **Transaction Type:** "Merchant Payment Other Single Step"
- **Cashback:** 4% of transaction amount
- **Impact:** Increases balance

## Changes Made

### Before (Format 2 ignored implicit fees)
```python
# Format 2 functions did NOT account for implicit fees
def calculate_opening_balance_format2(first_balance, first_amount):
    return first_balance - first_amount  # Missing implicit fees!

def apply_transaction_format2(balance, amount):
    return balance + amount  # Missing implicit fees!
```

### After (All Airtel formats include implicit fees)
```python
# Format 2 now includes implicit fees calculation
def calculate_opening_balance_format2(first_balance, first_amount, first_description=''):
    additional_fee = calculate_implicit_fees_format1(first_amount, first_description)
    return first_balance - first_amount - additional_fee

def apply_transaction_format2(balance, amount, description=''):
    additional_fee = calculate_implicit_fees_format1(amount, description)
    return balance + amount - additional_fee
```

## Files Modified

### 1. `/app/services/balance_utils.py`
**Lines 170-195:** Updated `calculate_opening_balance_format2()`
- Added `first_description` parameter
- Calls `calculate_implicit_fees_format1()` for IND02 and Merchant Payment detection
- Applies implicit fees to opening balance calculation

**Lines 198-223:** Updated `apply_transaction_format2()`
- Added `description` parameter
- Calls `calculate_implicit_fees_format1()` for IND02 and Merchant Payment detection
- Applies implicit fees to running balance calculation

### 2. `/app/services/processor.py`
**Line 314:** Updated `calculate_opening_balance_format2()` call
```python
# Before
opening_balance = calculate_opening_balance_format2(first_balance, first_amount)

# After
opening_balance = calculate_opening_balance_format2(first_balance, first_amount, first_description)
```

**Line 368:** Updated `apply_transaction_format2()` call
```python
# Before
running_balance = apply_transaction_format2(running_balance, amount)

# After
running_balance = apply_transaction_format2(running_balance, amount, description)
```

## Impact

### Balance Calculation Accuracy
✅ **Format 1 (PDF/CSV):** Already had implicit fees - no change
✅ **Format 2 (PDF/CSV):** Now correctly accounts for implicit fees

### Affected Transactions
All Airtel Format 2 statements with:
- IND02 transactions (0.5% commission)
- "Merchant Payment Other Single Step" (4% cashback)

### Expected Results
- **IND02 transactions:** Balance will be 0.5% lower than before (fees now accounted for)
- **Merchant Payment:** Balance will be 4% higher than before (cashback now accounted for)
- **Better balance match:** Calculated balances will more closely match statement balances

## Testing

### Test Case 1: IND02 Transaction (Format 2)
```
Description: "IND02 Transfer"
Amount: -10,000 UGX (debit)
Previous Balance: 100,000 UGX

Old Calculation: 100,000 + (-10,000) = 90,000 UGX
New Calculation: 100,000 + (-10,000) - 50 = 89,950 UGX ✅ (0.5% commission)
```

### Test Case 2: Merchant Payment (Format 2)
```
Description: "Merchant Payment Other Single Step"
Amount: -5,000 UGX (debit)
Previous Balance: 50,000 UGX

Old Calculation: 50,000 + (-5,000) = 45,000 UGX
New Calculation: 50,000 + (-5,000) - (-200) = 45,200 UGX ✅ (4% cashback)
```

## Migration Notes

### Reprocessing Required
If you have **already processed** Format 2 statements, you should **reprocess them** to apply implicit fees:

```bash
# Reprocess all Format 2 statements
python process_statements_parallel.py --workers 8 --force
```

### Expected Changes
After reprocessing Format 2 statements:
- `verification_status` may change from FAIL → PASS
- `balance_match` may improve
- `calculated_running_balance` will be more accurate

## Backwards Compatibility

✅ **Format 1 statements:** No change in behavior
✅ **MTN statements:** Not affected (uses separate logic)
✅ **Function signatures:** Backward compatible (description parameter is optional with default='')

## Code Reference

### Implicit Fees Calculation Function
Located in: `/app/services/balance_utils.py:16-44`

```python
def calculate_implicit_fees_format1(amount: float, description: str) -> float:
    """
    Calculate implicit fees and cashbacks for Airtel transactions.

    Returns:
        float: Additional fee (positive = deduct, negative = add cashback)
    """
    additional_fee = 0.0

    # IND02: 0.5% commission
    if description and 'IND02' in description.upper() and 'IND01' not in description.upper():
        additional_fee += abs(amount) * 0.005

    # Merchant Payment Other Single Step: 4% cashback
    if description and 'MERCHANT PAYMENT OTHER SINGLE STEP' in description.upper():
        cashback = abs(amount) * 0.04
        additional_fee -= cashback

    return additional_fee
```

## Related Documentation

- Balance Utilities: `/app/services/balance_utils.py`
- Processor Logic: `/app/services/processor.py`
- Quality Tracking: `/docs/migrations/QUALITY_TRACKING_MIGRATION.md`

---

**Updated:** 2025-10-13
**Applies to:** All Airtel (UATL) statements, Format 1 and Format 2
