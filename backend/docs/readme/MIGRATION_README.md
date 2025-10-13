# Metadata Columns Migration

## Overview
This migration adds 6 new columns to the `metadata` table and populates them with data from existing sources.

## New Columns
1. **format** (VARCHAR(20)) - Statement format (format_1, format_2, excel)
2. **mime** (VARCHAR(50)) - MIME type (application/pdf, text/csv, etc.)
3. **submitted_date** (DATE) - From mapper.csv
4. **start_date** (DATE) - Minimum transaction date
5. **end_date** (DATE) - Maximum transaction date
6. **requestor** (VARCHAR(255)) - Email address (Airtel format 1 only)

## Running the Migration

### Simple Method (Recommended)
```bash
cd backend
python run_migration.py
```

This will:
1. Add all 6 columns to the metadata table
2. Populate `format` from `pdf_format` (format_1, format_2, excel)
3. Populate `mime` from file extensions in `pdf_path`
4. Populate `start_date` and `end_date` from raw_statements tables
5. Populate `submitted_date` from mapper.csv
6. Update the `unified_statements` view
7. Show verification statistics

## Data Population Details

### format
- UATL with pdf_format=1 → `format_1`
- UATL with pdf_format=2 → `format_2`
- UMTN → `excel`

### mime
- .pdf → `application/pdf`
- .csv → `text/csv`
- .xlsx → `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- .xls → `application/vnd.ms-excel`

### start_date and end_date
- Calculated from `MIN(txn_date)` and `MAX(txn_date)` in raw_statements
- Separate queries for UATL and UMTN tables

### submitted_date
- Loaded from mapper.csv matching by run_id
- Uses the `created_date` field

## After Migration

1. **Restart FastAPI server**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Test the UI**
   - Open http://localhost:8000
   - Verify new columns are visible
   - Test search and date filtering
   - Check pagination

3. **Drop pdf_format (Optional)**
   Once you've confirmed everything works:
   ```bash
   mysql -u root -p fraud_detection
   ```
   ```sql
   -- Verify data first
   SELECT COUNT(*) as total,
          SUM(CASE WHEN format IS NOT NULL THEN 1 ELSE 0 END) as has_format
   FROM metadata;

   -- If all looks good, drop pdf_format
   ALTER TABLE metadata DROP COLUMN pdf_format;
   ```

## Files Modified

### Backend Code
- `backend/app/models/metadata.py` - Added new columns to model
- `backend/app/services/mapper.py` - Enhanced to populate submitted_date
- `backend/app/services/processor.py` - Calculates start_date/end_date during processing
- `backend/app/services/crud_v2.py` - Added search and date filtering
- `backend/app/api/v1/upload.py` - Populates mime type
- `backend/app/api/v1/statements.py` - Updated queries with new columns
- `backend/app/services/parsers/*.py` - Extract format and requestor

### Frontend
- `backend/app/templates/index.html` - Added search, filters, pagination UI

### Migration Scripts
- `backend/run_migration.py` - Main migration runner
- `backend/migrations/add_metadata_columns.sql` - SQL for data population
- `backend/migrations/drop_pdf_format.sql` - Cleanup script for later

## Rollback (if needed)

If something goes wrong:
```sql
ALTER TABLE metadata
  DROP COLUMN format,
  DROP COLUMN mime,
  DROP COLUMN submitted_date,
  DROP COLUMN start_date,
  DROP COLUMN end_date,
  DROP COLUMN requestor;

DROP INDEX idx_submitted_date ON metadata;
```

Then restore the old unified_statements view from backup.
