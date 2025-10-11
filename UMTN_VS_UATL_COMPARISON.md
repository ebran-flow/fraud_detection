# UMTN vs UATL Format Comparison

## Format Analysis Results

Based on actual data analysis:

### UATL (Airtel) Format
```
Transaction ID, Transaction Date, Description, Status,
Transaction Amount, Credit/Debit, Fee, Balance
```

**Key Characteristics:**
- 2 formats (Format 1 with Credit/Debit, Format 2 with signed amounts)
- Simple fee structure
- Has explicit status column (Success/Failed)
- Balance is the account balance

### UMTN (MTN) Format
```
Date/Time, Transaction ID, Transaction Type, Amount,
From Account, To Account, Fee, Commission Amount, TAX,
Commission Receiving No., Commission Balance, Float Balance
```

**Key Characteristics:**
- Always has signed amounts (negative = outgoing)
- **Commission tracking** (3 columns)
- **Tax tracking**
- **Float Balance** = running agent float balance
- **No explicit status** (all rows are successful)
- Transaction types: BILL PAYMENT, CASH_IN, CASH_OUT, TRANSFER, LOAN_REPAYMENT, DEBIT

## Field Mapping

| Purpose | UATL | UMTN |
|---------|------|------|
| Date | `txn_date` | `Date / Time` |
| Transaction ID | `txn_id` | `Transaction ID` |
| Description | `description` | `Transaction Type` + derived |
| Amount | `amount` | `Amount` (signed) |
| Fee | `fee` | `Fee` |
| Balance | `balance` | `Float Balance` ⭐ |
| Direction | `txn_direction` / sign | sign of `Amount` |
| Status | `status` | Always success (implicit) |
| From Account | `from_acc` (optional) | `From Account` (always) |
| To Account | `to_acc` (optional) | `To Account` (always) |
| **Commission** | ❌ N/A | ✅ `Commission Amount` |
| **Tax** | ❌ N/A | ✅ `TAX` |
| **Commission Balance** | ❌ N/A | ✅ `Commission Balance` |
| **Commission Number** | ❌ N/A | ✅ `Commission Receiving No.` |

## Why Separate Tables Are Necessary

### 1. Different Balance Semantics
- **UATL**: `balance` = customer account balance
- **UMTN**: `float_balance` = agent float balance (different meaning!)

### 2. Commission Tracking (UMTN-specific)
UMTN has 4 commission-related columns that don't exist in UATL:
- Commission Amount (the commission earned)
- Tax on commission
- Commission Receiving Number
- Commission Balance (running commission total)

### 3. Data Volume
- Sample UMTN statement: 1,592 transactions
- If in shared table: 1,592 rows × 5 NULL columns = 7,960 wasted cells

### 4. Query Complexity
**Bad** (single table):
```sql
-- Which balance to use???
SELECT COALESCE(balance, float_balance) as balance,
       COALESCE(commission_amount, 0) as commission
FROM raw_statements
WHERE acc_prvdr_code = ?
```

**Good** (separate tables):
```sql
-- UATL query - clean
SELECT balance, fee FROM uatl_raw_statements;

-- UMTN query - clean
SELECT float_balance as balance, commission_amount FROM umtn_raw_statements;
```

## Recommended Schema

### UATL Tables
```sql
CREATE TABLE uatl_raw_statements (
  id BIGINT PRIMARY KEY,
  run_id VARCHAR(64),
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  description TEXT,
  status VARCHAR(32),      -- Success/Failed
  txn_direction VARCHAR(16), -- Credit/Debit (Format 1)
  amount DECIMAL(18,2),    -- Signed for Format 2
  fee DECIMAL(18,2),
  balance DECIMAL(18,2),   -- Customer balance
  pdf_format TINYINT       -- 1 or 2
);
```

### UMTN Tables
```sql
CREATE TABLE umtn_raw_statements (
  id BIGINT PRIMARY KEY,
  run_id VARCHAR(64),
  acc_number VARCHAR(64),
  txn_id VARCHAR(128),
  txn_date DATETIME,
  txn_type VARCHAR(64),    -- BILL PAYMENT, CASH_IN, etc.
  amount DECIMAL(18,2),    -- Signed amount
  from_account VARCHAR(64),
  to_account VARCHAR(128),
  fee DECIMAL(18,2),
  commission_amount DECIMAL(18,2),  -- UMTN-specific
  tax DECIMAL(18,2),                -- UMTN-specific
  commission_receiving_no VARCHAR(64), -- UMTN-specific
  commission_balance DECIMAL(18,2), -- UMTN-specific
  float_balance DECIMAL(18,2)       -- Agent float balance ⭐
);
```

## Processing Logic Differences

### UATL Processing
```python
# Balance verification for UATL
def verify_uatl_balance(transactions):
    opening_balance = calculate_opening_balance(transactions[0])
    calculated_balance = opening_balance

    for txn in transactions:
        if txn.txn_direction == 'Credit':
            calculated_balance += txn.amount - txn.fee
        else:  # Debit
            calculated_balance -= txn.amount + txn.fee

        # Compare with statement balance
        balance_diff = calculated_balance - txn.balance
```

### UMTN Processing
```python
# Balance verification for UMTN
def verify_umtn_balance(transactions):
    opening_float = calculate_opening_float(transactions[0])
    calculated_float = opening_float

    for txn in transactions:
        # Amount is signed: negative = outgoing, positive = incoming
        calculated_float += txn.amount

        # Track commission separately
        if txn.commission_amount:
            calculated_float += txn.commission_amount
            # Verify commission balance
            expected_commission = prev_commission + txn.commission_amount - txn.tax

        # Compare with float balance
        balance_diff = calculated_float - txn.float_balance
```

## Migration Strategy

### Phase 1: Keep UATL as-is
- ✅ UATL already working with current schema
- ✅ No changes needed to existing code

### Phase 2: Add UMTN
1. Create `umtn_raw_statements` table
2. Create `umtn_processed_statements` table
3. Implement UMTN parser (Excel → database)
4. Implement UMTN processor (commission + float balance)
5. Update factory to route UMTN requests

### Phase 3: Unified Reporting
- Both providers write to shared `metadata` and `summary` tables
- Use views for cross-provider analytics
- Frontend shows both providers seamlessly

## Conclusion

**✅ Use provider-specific tables** because:
1. UMTN has 5 columns UATL doesn't need
2. Different balance semantics (account vs float)
3. Commission tracking is UMTN-specific
4. Cleaner code, better performance
5. Easy to extend per-provider features

**Implementation effort:**
- Schema: 2 extra tables (already designed)
- Code: Factory pattern (DRY, minimal duplication)
- Maintenance: Easier than managing NULL columns
