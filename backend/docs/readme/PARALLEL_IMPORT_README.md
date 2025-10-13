# Parallel Import Scripts

Scripts for importing UATL and Airtel (UMTN) statements in parallel.

## Structure

```
backend/
  docs/
    data/
      statements/
        mapper.csv              # Master CSV with all run_ids
      UATL/
        extracted/              # UATL statement files (68xxxxx.pdf, .csv, etc)
        compressed/             # Compressed archives (optional)
      UMTN/
        extracted/              # Airtel statement files
        compressed/             # Compressed archives (optional)
```

## Scripts

Located in `backend/` folder:
- `backend/process_parallel.py` - UATL Import
- `backend/import_airtel_parallel.py` - Airtel Import

### 1. `process_parallel.py` - UATL Import
Import UATL (Vodafone) statements from mapper.csv

**Usage:**
```bash
cd backend

# Dry run (preview)
python process_parallel.py --workers 8 --dry-run

# Import all UATL statements
python process_parallel.py --workers 8

# Import specific month
python process_parallel.py --workers 8 --month 2025-09
```

### 2. `import_airtel_parallel.py` - Airtel Import
Import Airtel (UMTN) statements from mapper.csv

**Usage:**
```bash
cd backend

# Dry run (preview)
python import_airtel_parallel.py --workers 8 --dry-run

# Import all Airtel statements
python import_airtel_parallel.py --workers 8

# Import specific month
python import_airtel_parallel.py --workers 8 --month 2025-09
```

## Setup

1. **Place your statement files:**
   - UATL files → `backend/docs/data/UATL/extracted/`
   - Airtel files → `backend/docs/data/UMTN/extracted/`

2. **Ensure mapper.csv exists:**
   - Location: `backend/docs/data/statements/mapper.csv`
   - Should have columns: `run_id`, `acc_number`, `acc_prvdr_code`, `created_date`, etc.

3. **Run the import:**
   ```bash
   cd backend

   # For UATL
   python process_parallel.py --workers 8

   # For Airtel
   python import_airtel_parallel.py --workers 8
   ```

## Performance

- **Recommended workers for i5-12400:** 8-12 workers
- **Speed:** ~2-5 statements/second (depends on file size)
- **Logs:** Check `process_parallel.log` and `import_airtel_parallel.log`

## Notes

- Scripts automatically skip already imported run_ids
- Each worker has its own database session
- Progress is logged with ETA and speed tracking
- Safe to interrupt (Ctrl+C) and resume later
