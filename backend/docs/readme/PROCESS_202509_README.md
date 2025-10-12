# Process September 2025 Statements

Script to bulk upload and process all UATL statements from September 2025.

## What It Does

1. Reads `mapper.csv` and filters UATL statements from September 2025
2. Finds corresponding files in `docs/data/UATL/extracted/`
3. Uploads to database (parses and saves raw transactions)
4. Processes statements (duplicate detection, balance verification)
5. Skips already uploaded/processed statements

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
# Preview what will be done (no database changes)
python process_202509_statements.py --dry-run

# Upload and process all statements
python process_202509_statements.py

# Only upload (no processing)
python process_202509_statements.py --upload-only
```

## Output

```
======================================================================
PROCESS SEPTEMBER 2025 - LIVE
======================================================================

Reading mapper.csv...
Found 811 statements from September 2025

STEP 1: Uploading statements...

[1/811] 68b54f2cea2e2
  📄 68b54f2cea2e2.pdf
  ✅ Uploaded 245 transactions

[2/811] 68b5609553c2e
  📄 68b5609553c2e.csv
  ⏭️  Already uploaded

...

======================================================================
UPLOAD SUMMARY
======================================================================
Total:         811
✅ Uploaded:   650
⏭️  Skipped:    150
❌ Not found:  10
❌ Errors:     1
======================================================================

STEP 2: Processing 650 statements...

[1/650] 68b54f2cea2e2
  ✅ PASS | Success

...

======================================================================
PROCESSING SUMMARY
======================================================================
Total:         650
✅ Success:    645
❌ Errors:     5
======================================================================

Duration: 0:45:23
✅ Complete!
```

## Features

- ✅ Filters by month: September 2025 (`2025-09`)
- ✅ Skips already uploaded statements
- ✅ Skips already processed statements
- ✅ Uses same workflow as FastAPI backend
- ✅ Logs everything to `process_202509.log`
- ✅ Handles errors gracefully

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

## Notes

- Safe to run multiple times (idempotent)
- Creates detailed log file: `process_202509.log`
- Processing can take time for large batches (~1-2 seconds per statement)
- Failed statements are logged but don't stop the batch
