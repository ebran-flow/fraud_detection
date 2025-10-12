# Process UATL Statements (All or By Month)

Script to bulk upload and process UATL statements from mapper.csv.

**Processes statements from latest to oldest (newest first).**

## What It Does

1. Reads `mapper.csv` and filters UATL statements
2. Sorts by date (newest first)
3. Finds corresponding files in `docs/data/UATL/extracted/`
4. Uploads to database (parses and saves raw transactions)
5. Processes statements (duplicate detection, balance verification)
6. Skips already uploaded/processed statements

## Prerequisites

```bash
# 1. Extract all compressed files first
python extract_statements.py

# 2. Start the database
docker-compose up -d  # or however you start your DB

# 3. Ensure backend dependencies are installed
source venv/bin/activate
pip install -r backend/requirements.txt
```

## Usage

```bash
# Process ALL UATL statements (latest to oldest)
python process_202509_statements.py

# Process only September 2025 statements
python process_202509_statements.py --month 2025-09

# Preview what will be done (no database changes)
python process_202509_statements.py --dry-run

# Preview specific month
python process_202509_statements.py --month 2025-09 --dry-run

# Only upload (no processing)
python process_202509_statements.py --upload-only

# Upload only for specific month
python process_202509_statements.py --month 2025-09 --upload-only
```

## Output

### Processing All Statements

```
======================================================================
PROCESS ALL UATL STATEMENTS - LIVE
======================================================================

Reading mapper.csv...
Found 15234 UATL statements (sorted newest first)
Date range: 2025-10-11 to 2023-05-31

STEP 1: Uploading statements...

[1/15234] 68b54f2cea2e2
  📄 68b54f2cea2e2.pdf
  ✅ Uploaded 245 transactions

[2/15234] 68b5609553c2e
  📄 68b5609553c2e.csv
  ⏭️  Already uploaded

...

======================================================================
UPLOAD SUMMARY
======================================================================
Total:         15234
✅ Uploaded:   12500
⏭️  Skipped:    2500
❌ Not found:  200
❌ Errors:     34
======================================================================

STEP 2: Processing 12500 statements...

[1/12500] 68b54f2cea2e2
  ✅ PASS | Success

...

======================================================================
PROCESSING SUMMARY
======================================================================
Total:         12500
✅ Success:    12450
❌ Errors:     50
======================================================================

Duration: 5:23:45
✅ Complete!
```

### Processing Specific Month

```
======================================================================
PROCESS 2025-09 UATL STATEMENTS - LIVE
======================================================================

Reading mapper.csv...
Found 811 statements from 2025-09 (sorted newest first)

STEP 1: Uploading statements...
...
```

## Features

- ✅ **Processes ALL UATL statements** or filters by month
- ✅ **Sorts newest first** (latest to oldest)
- ✅ Skips already uploaded statements
- ✅ Skips already processed statements
- ✅ Uses same workflow as FastAPI backend
- ✅ Logs everything to `process_202509.log`
- ✅ Handles errors gracefully
- ✅ Shows date range for all statements

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--month YYYY-MM` | Filter by specific month (e.g., `2025-09`) |
| `--dry-run` | Preview without making changes |
| `--upload-only` | Upload only, skip processing |

## Examples

```bash
# Process all 2025 statements
python process_202509_statements.py --month 2025

# Process October 2024
python process_202509_statements.py --month 2024-10

# Check what would be uploaded (all statements)
python process_202509_statements.py --dry-run

# Upload all without processing (faster)
python process_202509_statements.py --upload-only
```

## Workflow

The script follows the exact same workflow as the FastAPI upload and process endpoints:

1. **Upload Phase:**
   - Check if run_id already exists
   - Parse file using provider-specific parser
   - Enrich metadata with mapper.csv data
   - Save to database (metadata + raw transactions)

2. **Processing Phase:**
   - Detect duplicates
   - Calculate running balance
   - Verify balance matches
   - Generate summary with verification status

## Sorting Order

Statements are processed **from newest to oldest** (latest first):
- `2025-10-11` → `2025-10-10` → ... → `2023-05-31`

This ensures:
- Most recent statements are processed first
- You can interrupt and resume easily
- Latest data is available first

## Troubleshooting

### Database Connection Error

Make sure your database is running:
```bash
docker-compose up -d
# or
./start.sh  # if you have a startup script
```

### File Not Found

Extract compressed files first:
```bash
python extract_statements.py
```

### Already Processed

The script automatically skips statements already in the database. This is safe and expected.

## Performance Notes

- Processing ~1-2 seconds per statement
- Large batches (15,000+) can take several hours
- Safe to interrupt (Ctrl+C) and resume later
- Already processed statements are skipped

## Notes

- Safe to run multiple times (idempotent)
- Creates detailed log file: `process_202509.log`
- Failed statements are logged but don't stop the batch
- Shows total count and date range before starting
