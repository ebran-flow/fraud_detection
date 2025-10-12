# UI Fields Display Fix

**Date:** October 11, 2025
**Issue:** Balance Match and Verification Reason columns not shown in UI

## Problem

The statements table was only showing **Metadata** fields, but `balance_match`, `verification_status`, and `verification_reason` are stored in the **Summary** table, not the Metadata table.

## Root Cause

### Data Model Architecture

The system has two separate tables:

1. **Metadata Table** - Created during upload/parsing:
   - run_id, acc_number, acc_prvdr_code
   - num_rows, pdf_format
   - stmt_opening_balance, stmt_closing_balance
   - created_at

2. **Summary Table** - Created during processing:
   - run_id
   - balance_match (Success/Failed)
   - verification_status (PASS/FAIL/WARNING)
   - verification_reason (detailed explanation)
   - calculated_closing_balance
   - credits, debits, fees

### The Issue

The UI endpoint (`/api/v1/ui/statements-table`) was only querying the **Metadata** table and passing it to the template, so the Summary fields were never available for display.

## Solution

### 1. Updated Backend API (`backend/app/api/v1/ui.py`)

**Added Summary join:**
```python
# Import Summary model
from ...models.summary import Summary

# In get_statements_table():
# Enrich metadata with summary data
enriched_statements = []
for metadata in metadata_list:
    # Get summary for this run_id
    summary = crud.get_summary_by_run_id(db, metadata.run_id)

    # Create enriched object with both metadata and summary data
    stmt_data = {
        # Metadata fields
        'run_id': metadata.run_id,
        'acc_number': metadata.acc_number,
        'acc_prvdr_code': metadata.acc_prvdr_code,
        'rm_name': metadata.rm_name,
        'num_rows': metadata.num_rows,
        'pdf_format': metadata.pdf_format,
        'stmt_opening_balance': metadata.stmt_opening_balance,
        'stmt_closing_balance': metadata.stmt_closing_balance,
        'created_at': metadata.created_at,
        # Summary fields (NEW)
        'balance_match': summary.balance_match if summary else None,
        'verification_status': summary.verification_status if summary else None,
        'verification_reason': summary.verification_reason if summary else None,
        'calculated_closing_balance': summary.calculated_closing_balance if summary else None,
    }
    enriched_statements.append(stmt_data)
```

### 2. Updated Template (`backend/app/templates/statements_table.html`)

**Added two new columns:**

#### A. Balance Match Column
```html
<th>Balance Match</th>

<!-- In tbody: -->
<td>
    {% if stmt.balance_match == 'Success' %}
        <span class="badge bg-green">Success</span>
    {% elif stmt.balance_match == 'Failed' %}
        <span class="badge bg-red">Failed</span>
    {% else %}
        <span class="text-gray">Not Processed</span>
    {% endif %}
</td>
```

#### B. Verification Column (with tooltip)
```html
<th>Verification</th>

<!-- In tbody: -->
<td title="{{ stmt.verification_reason }}">
    {% if stmt.verification_status == 'PASS' %}
        <span class="badge bg-green">PASS</span>
    {% elif stmt.verification_status == 'FAIL' %}
        <span class="badge bg-red">FAIL</span>
    {% elif stmt.verification_status == 'WARNING' %}
        <span class="badge bg-yellow">WARNING</span>
    {% else %}
        <span class="text-gray">-</span>
    {% endif %}
</td>
```

**Updated colspan:**
Changed from `colspan="10"` to `colspan="12"` in the "No statements found" row.

## Changes Summary

### Files Modified:

1. **`backend/app/api/v1/ui.py`**
   - Added `Summary` model import
   - Enriched metadata with summary data in `get_statements_table()`
   - Now passes both Metadata and Summary fields to template

2. **`backend/app/templates/statements_table.html`**
   - Added "Balance Match" column header
   - Added "Verification" column header
   - Added Balance Match display with green/red badges
   - Added Verification Status display with color-coded badges
   - Added tooltip on Verification column showing full `verification_reason`
   - Updated colspan from 10 to 12

## UI Display

### Balance Match Column
- **Green "Success"** - Balance calculation matches statement
- **Red "Failed"** - Balance calculation doesn't match
- **Gray "Not Processed"** - Statement uploaded but not processed yet

### Verification Column
- **Green "PASS"** - Balance matches and no duplicates
- **Red "FAIL"** - Balance mismatch or critical errors
- **Yellow "WARNING"** - Found duplicate transactions or minor issues
- **Gray "-"** - Not processed yet

### Tooltip (hover over Verification)
Shows the full `verification_reason`:
- "Balance matches and no duplicates detected"
- "Balance mismatch: calculated=1050000.00, statement=1049950.00"
- "Found 3 duplicate transactions"

## Data Flow

### Before Fix:
```
Database:
├── Metadata (has: run_id, balances, etc.)
└── Summary (has: balance_match, verification_reason) ← NOT USED

UI Endpoint:
└── Query Metadata only → Pass to template

Template:
└── Show Metadata fields only (no balance_match, no verification)
```

### After Fix:
```
Database:
├── Metadata (has: run_id, balances, etc.)
└── Summary (has: balance_match, verification_reason)

UI Endpoint:
├── Query Metadata
├── For each metadata, query Summary ← NEW
└── Merge both → Pass to template

Template:
└── Show both Metadata AND Summary fields ← NEW COLUMNS
```

## Performance Note

The current implementation queries Summary individually for each metadata row:
```python
for metadata in metadata_list:
    summary = crud.get_summary_by_run_id(db, metadata.run_id)  # N+1 queries
```

**For Future Optimization:**
Consider using a LEFT JOIN or batch query to get all summaries at once:
```python
# More efficient approach (future improvement):
summaries = db.query(Summary).filter(
    Summary.run_id.in_([m.run_id for m in metadata_list])
).all()
summary_dict = {s.run_id: s for s in summaries}
```

For now, the current implementation works fine for typical page sizes (50 rows).

## Testing

```bash
✅ UI endpoint imports successfully
✅ App imports successfully
✅ All UI changes ready to test!
```

## User Testing Required

1. **Start the server:**
   ```bash
   ./start.sh
   ```

2. **View statements list** - Navigate to main page

3. **Verify new columns appear:**
   - ✅ "Balance Match" column with Success/Failed badges
   - ✅ "Verification" column with PASS/FAIL/WARNING badges
   - ✅ Hover over Verification to see tooltip with detailed reason

4. **Process a statement** - Upload and process a PDF

5. **Verify values update:**
   - ✅ Balance Match shows Success or Failed
   - ✅ Verification shows correct status
   - ✅ Tooltip shows detailed reason

## Expected Results

For processed statements, you should now see:
- Statement Balance: 1050000.00
- Balance Match: **Success** (green badge)
- Verification: **PASS** (green badge)
- Hover tooltip: "Balance matches and no duplicates detected"

Or if there are issues:
- Statement Balance: 1050000.00
- Balance Match: **Failed** (red badge)
- Verification: **FAIL** (red badge)
- Hover tooltip: "Balance mismatch: calculated=1050000.00, statement=1049950.00"
