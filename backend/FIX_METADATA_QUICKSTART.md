# Metadata Repair - Quick Start

## What It Does

Fills missing metadata fields from:
- **mapper.csv** → RM names, submission dates
- **raw_statements** → transaction dates, counts, balances

## Quick Commands

```bash
# Preview what would be updated (recommended first run)
python3 fix_metadata.py --dry-run

# Actually update the database
python3 fix_metadata.py

# Show help
python3 fix_metadata.py --help
```

## Fields Fixed

- ✅ `rm_name` - From mapper.csv
- ✅ `submitted_date` - From mapper.csv
- ✅ `num_rows` - Count from raw_statements
- ✅ `start_date` - MIN(txn_date) from raw_statements
- ✅ `end_date` - MAX(txn_date) from raw_statements
- ✅ `first_balance` - First transaction balance
- ✅ `last_balance` - Last transaction balance

## When to Use

Run this script when:
- After bulk imports
- When you see NULL values in metadata
- Before running reports
- After database restore

## Example Output

```
============================================================
Metadata Repair Script
============================================================

Database: fraud_detection
Host: 127.0.0.1:3307
User: root

Found 87 records with missing fields

Proceed with repair? (y/n): y

Processing 64806f0e09bf6 (UATL)...
  Would update fields: rm_name, submitted_date, num_rows
  ✓ Updated 64806f0e09bf6

============================================================
METADATA REPAIR SUMMARY
============================================================
Total records processed: 87
Records updated: 82
Records skipped (no data): 5
Errors: 0
============================================================
```

## Safety

- ✅ Dry-run mode available
- ✅ Confirmation prompt before updates
- ✅ Only fills NULL values (never overwrites)
- ✅ Detailed logging to `fix_metadata.log`

## Configuration

**No configuration needed!** Reads from `.env` file automatically:

```bash
# .env file
DB_HOST=127.0.0.1
DB_PORT=3307
DB_USER=root
DB_PASSWORD=password
DB_NAME=fraud_detection
```

## Requirements

```bash
pip install sqlalchemy pandas pymysql python-dotenv
```

## See Full Documentation

→ `FIX_METADATA_README.md` for complete guide
