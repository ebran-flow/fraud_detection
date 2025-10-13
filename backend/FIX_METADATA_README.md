# Metadata Repair Script

## Purpose

Ensures all metadata records have complete information by filling missing fields from:
- **mapper.csv** → `rm_name`, `submitted_date`
- **raw_statements tables** → `start_date`, `end_date`, `num_rows`, `first_balance`, `last_balance`

## Fields Repaired

| Field | Source | Description |
|-------|--------|-------------|
| `rm_name` | mapper.csv | Relationship Manager name |
| `submitted_date` | mapper.csv (created_date) | Statement submission date |
| `num_rows` | raw_statements | Number of transactions |
| `start_date` | raw_statements | First transaction date |
| `end_date` | raw_statements | Last transaction date |
| `first_balance` | raw_statements | Opening balance |
| `last_balance` | raw_statements | Closing balance |

## Usage

### Basic Run

```bash
python3 fix_metadata.py
```

### Dry-Run Mode (Preview Changes)

```bash
python3 fix_metadata.py --dry-run
# or
python3 fix_metadata.py -n
```

This shows what would be updated without making any changes to the database.

### What It Does

1. Connects to MySQL database
2. Finds metadata records with missing fields
3. Loads mapper.csv for RM names and submission dates
4. Queries raw_statements tables for transaction data
5. Updates metadata with found values
6. Shows summary and verification

### Example Output

```
============================================================
Metadata Repair Script
============================================================

Database: fraud_detection
Host: 127.0.0.1:3307
User: root

Loaded 1125 records from mapper.csv
Found 87 metadata records with missing fields

Found 87 records with missing fields

Proceed with repair? (y/n): y

Processing 64806f0e09bf6 (UATL)...
  Updating fields: rm_name, submitted_date, num_rows, start_date, end_date
  ✓ Updated 64806f0e09bf6

Processing 6476d2ce4ca78 (UATL)...
  Updating fields: start_date, end_date
  ✓ Updated 6476d2ce4ca78

...

============================================================
METADATA REPAIR SUMMARY
============================================================
Total records processed: 87
Records updated: 82
Records skipped (no data): 5
Errors: 0
============================================================

Sample of updated records:
------------------------------------------------------------
Run ID: 64806f0e09bf6
  Provider: UATL
  RM Name: John Doe
  Num Rows: 5843
  Date Range: 2025-02-01 to 2025-05-31
  Submitted: 2023-06-07

Done!
```

## Common Scenarios

### Scenario 1: Missing RM Names
**Problem**: `rm_name` is NULL
**Solution**: Script looks up run_id in mapper.csv and fills from `rm_name` column

### Scenario 2: Missing Date Ranges
**Problem**: `start_date` or `end_date` is NULL
**Solution**: Script queries raw_statements for MIN/MAX transaction dates

### Scenario 3: Missing Balance Values
**Problem**: `first_balance` or `last_balance` is NULL
**Solution**: Script queries raw_statements for first and last balance values

### Scenario 4: Missing Row Count
**Problem**: `num_rows` is NULL or incorrect
**Solution**: Script counts records in raw_statements

## Data Flow

```
metadata table (incomplete)
    ↓
fix_metadata.py
    ├─→ mapper.csv → rm_name, submitted_date
    └─→ uatl_raw_statements/umtn_raw_statements → dates, counts, balances
         ↓
metadata table (complete)
```

## Requirements

- Python 3.7+
- SQLAlchemy
- pandas
- pymysql
- python-dotenv

Install dependencies:
```bash
pip install sqlalchemy pandas pymysql python-dotenv
```

## Configuration

**No configuration needed!** Script automatically reads from `.env` file:

```bash
# .env file
DB_HOST=127.0.0.1
DB_PORT=3307
DB_USER=root
DB_PASSWORD=password
DB_NAME=fraud_detection
```

**Mapper CSV path** is automatically detected:
```
backend/docs/data/statements/mapper.csv
```

All credentials are securely stored in `.env` (not committed to git).

## Logs

Script creates `fix_metadata.log` with detailed information:

```bash
tail -f fix_metadata.log
```

## Safety Features

1. **Preview before update**: Shows how many records will be updated
2. **Confirmation prompt**: Asks for user confirmation
3. **Detailed logging**: Logs all operations to file and console
4. **No data deletion**: Only fills missing values, never overwrites existing data
5. **Transaction safety**: Each update is committed separately

## When to Run This Script

Run this script when:
- After bulk imports from mapper.csv
- After uploading new statements via web interface
- When you notice NULL values in metadata
- After database migration or restore
- Before running reports or analysis

## Verification Queries

Check for incomplete metadata:

```sql
-- Find records with missing fields
SELECT
    run_id,
    acc_prvdr_code,
    rm_name IS NULL as missing_rm,
    num_rows IS NULL as missing_rows,
    start_date IS NULL as missing_start,
    end_date IS NULL as missing_end,
    first_balance IS NULL as missing_first_bal,
    last_balance IS NULL as missing_last_bal,
    submitted_date IS NULL as missing_submitted
FROM metadata
WHERE
    rm_name IS NULL
    OR num_rows IS NULL
    OR start_date IS NULL
    OR end_date IS NULL
    OR first_balance IS NULL
    OR last_balance IS NULL
    OR submitted_date IS NULL;
```

Check data after repair:

```sql
-- Verify completeness
SELECT
    COUNT(*) as total_records,
    SUM(CASE WHEN rm_name IS NOT NULL THEN 1 ELSE 0 END) as has_rm_name,
    SUM(CASE WHEN num_rows IS NOT NULL THEN 1 ELSE 0 END) as has_num_rows,
    SUM(CASE WHEN start_date IS NOT NULL THEN 1 ELSE 0 END) as has_start_date,
    SUM(CASE WHEN end_date IS NOT NULL THEN 1 ELSE 0 END) as has_end_date,
    SUM(CASE WHEN first_balance IS NOT NULL THEN 1 ELSE 0 END) as has_first_balance,
    SUM(CASE WHEN last_balance IS NOT NULL THEN 1 ELSE 0 END) as has_last_balance,
    SUM(CASE WHEN submitted_date IS NOT NULL THEN 1 ELSE 0 END) as has_submitted_date
FROM metadata;
```

## Troubleshooting

### Error: "mapper.csv not found"
**Solution**: Make sure mapper.csv exists at:
```
backend/docs/data/statements/mapper.csv
```

### Error: "No data found in raw_statements"
**Problem**: Raw statements haven't been imported yet
**Solution**: Import raw statements first, then run this script

### Error: "Database connection failed"
**Solution**: Check MySQL is running and credentials are correct

### Warning: "No mapping found for run_id"
**Explanation**: This run_id doesn't exist in mapper.csv
**Impact**: `rm_name` and `submitted_date` won't be filled (other fields still work)

## Best Practices

1. **Run after imports**: Always run after bulk importing statements
2. **Check logs**: Review `fix_metadata.log` for any warnings
3. **Verify results**: Check a few records manually after running
4. **Backup first**: Take database backup before running on production
5. **Test on subset**: For large datasets, test on a few records first

## Integration with Other Scripts

This script complements:
- **import_airtel_parallel.py**: Run after UMTN imports
- **process_parallel.py**: Run after UATL processing
- **populate_metadata.py**: Alternative approach for specific fields

## Performance

- **Speed**: ~10-20 records per second
- **Memory**: Minimal (processes one record at a time)
- **Database load**: Low (simple SELECT/UPDATE queries)

For 1000 records: ~1-2 minutes

## Example Workflow

```bash
# 1. Import statements
python import_airtel_parallel.py

# 2. Process statements
python process_parallel.py

# 3. Fix any incomplete metadata
python fix_metadata.py

# 4. Verify results
mysql -h localhost -P 3307 -u root -proot airtel -e "
SELECT COUNT(*) as incomplete
FROM metadata
WHERE rm_name IS NULL OR num_rows IS NULL
"
```

---

**Created**: 2025-10-13
**Purpose**: Ensure metadata completeness
**Safe**: Only fills missing values, never overwrites existing data
