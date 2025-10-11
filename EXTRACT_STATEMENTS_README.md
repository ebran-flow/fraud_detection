# Extract Statements Script

Simple script to extract customer statements from compressed ZIP files.

## What It Does

1. Reads ZIP files from `docs/data/UATL/compressed/`
2. Extracts the first file from each ZIP
3. Detects format (PDF, CSV, XLSX) automatically
4. Saves to `docs/data/UATL/extracted/` with proper extension
5. Skips already extracted files

## Setup

```bash
source venv/bin/activate
pip install python-magic
```

## Usage

```bash
# Preview what will be extracted
python extract_statements.py --dry-run

# Extract all files
python extract_statements.py
```

## Example Output

```
======================================================================
EXTRACT STATEMENTS - LIVE
======================================================================

Found 3 files

[1/3] 682c8f6fcefaa
✅ Extracted: 682c8f6fcefaa.pdf
[2/3] 68aaa85ecf491.zip
✅ Extracted: 68aaa85ecf491.pdf
[3/3] 68b5609553c2e
✅ Extracted: 68b5609553c2e.csv

======================================================================
SUMMARY
======================================================================
Total files:       3
✅ Extracted:      3
⏭️  Already done:   0
❌ Errors:         0
Duration:          0:00:01
======================================================================
```

## File Naming

ZIP filename (without .zip) becomes the output filename:
- `682c8f6fcefaa` → `682c8f6fcefaa.pdf`
- `68aaa85ecf491.zip` → `68aaa85ecf491.pdf`
- `68b5609553c2e` → `68b5609553c2e.csv`

This filename becomes the `run_id` when uploading to the database.

## Notes

- Creates `extract_statements.log` with detailed logs
- Skips files already extracted (safe to run multiple times)
- Only extracts first file if ZIP contains multiple files
- Detects file type by content (not extension)
