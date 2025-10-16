# Implicit Fee/Commission Detection

## Problem

Not all Airtel statements apply implicit fees/commissions inline. Some statements handle these separately (separate transactions or commission wallets). Our code was applying them to ALL statements, causing balance mismatches.

**Two types of implicit adjustments:**
1. **Merchant Payment Other Single Step:** 4% cashback (reduces balance impact)
2. **IND02 transactions:** 0.5% commission (increases balance impact)

## Solution

### 1. Detection Functions

**Cashback Detection:**
`detect_uses_implicit_cashback(transactions, max_test=5)` in `balance_utils.py`
- Tests first 3-5 "Merchant Payment Other Single Step" transactions
- Calculates balance WITH and WITHOUT 4% cashback
- Whichever matches the stated balance better gets a vote
- Majority vote determines the result

**IND02 Commission Detection:**
`detect_uses_implicit_ind02_commission(transactions, max_test=5)` in `balance_utils.py`
- Tests first 3-5 IND02 transactions
- Calculates balance WITH and WITHOUT 0.5% commission
- Whichever matches the stated balance better gets a vote
- Majority vote determines the result

### 2. Database Columns

- `metadata.uses_implicit_cashback` (BOOLEAN, DEFAULT TRUE)
- `metadata.uses_implicit_ind02_commission` (BOOLEAN, DEFAULT TRUE)

Store whether each statement uses these implicit adjustments.

### 3. Updated Function

`calculate_implicit_fees_format1(amount, description, apply_cashback=True, apply_ind02_commission=True)`

Now accepts both parameters to control whether each implicit adjustment is applied.

## Usage

### During Statement Processing

```python
from app.services.balance_utils import (
    detect_uses_implicit_cashback,
    detect_uses_implicit_ind02_commission
)

# Load transactions into list of dicts
transactions = [...]  # Each with amount, fee, balance, description

# Detect if statement uses implicit adjustments
uses_cashback = detect_uses_implicit_cashback(transactions)
uses_ind02_commission = detect_uses_implicit_ind02_commission(transactions)

# Store in metadata
metadata.uses_implicit_cashback = uses_cashback
metadata.uses_implicit_ind02_commission = uses_ind02_commission

# Use during balance calculation
implicit_fee = calculate_implicit_fees_format1(
    amount,
    description,
    apply_cashback=uses_cashback,
    apply_ind02_commission=uses_ind02_commission
)
```

### Updating Existing Statements

Run the detection script to scan and update all existing statements:

```bash
python scripts/analysis/update_implicit_cashback_flags.py
```

## Examples

**Statement 687a321075c82 (Merchant Payment Cashback):**
- Transaction 118805162338: -1000, fee 55, Merchant Payment Other Single Step
- WITH 4% cashback: balance diff = 95 (WRONG)
- WITHOUT cashback: balance diff = 55 (CORRECT)
- Result: `uses_implicit_cashback = False`

**Statement 6890c041aceeb (IND02 Commission):**
- Transaction 123140466278: 155000, fee 330, Received From IND02
- WITH 0.5% commission: balance diff = 330 (CORRECT)
- WITHOUT commission: balance diff = 1105 (WRONG)
- Result: `uses_implicit_ind02_commission = True`
- Note: Has BOTH explicit fee (330) AND implicit commission (0.5% of amount)

## Testing

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
python -m pytest tests/test_implicit_cashback_detection.py -v
```
