# Migration Guide - Airtel Fraud Detection

This document describes the migration of the fraud_detection project from the `data_score_factors` project to a standalone `airtel_fraud_detection` project.

## Migration Summary

**Date:** October 11, 2025
**From:** `/home/ebran/Developer/projects/data_score_factors/fraud_detection/`
**To:** `/home/ebran/Developer/projects/airtel_fraud_detection/`

## What Changed

### 1. New Standalone Project Structure

```
OLD: data_score_factors/fraud_detection/
NEW: airtel_fraud_detection/
```

### 2. Centralized Configuration

**NEW FILE:** `config.py`

All hardcoded paths have been replaced with imports from `config.py`:

```python
# OLD (app.py)
UPLOADED_PDF_PATH = "/home/ebran/Developer/projects/data_score_factors/fraud_detection/uploaded_pdfs/"

# NEW (app.py)
from config import UPLOADED_PDF_PATH
```

**Benefits:**
- Single place to update paths
- Environment variable support
- Easy deployment to different environments

### 3. Updated Files

#### config.py (NEW)
- Centralizes all path configurations
- Auto-creates directories
- Supports environment variables
- Default archive path still points to data_score_factors (configurable)

#### app.py
- Imports paths from `config.py`
- Google credentials path from config
- No other functional changes

#### batch_process_statements.py
- Imports paths from `config.py`
- No other functional changes

#### mapper.py
- Imports path from `config.py`
- Added fallback import for `helpers.py` from data_score_factors
- Clear error message if helpers not found

### 4. New Project Files

#### requirements.txt (NEW)
- Lists all Python dependencies
- Versioned dependencies
- Optional dependencies marked

#### .gitignore (NEW)
- Excludes data files (PDFs, CSVs)
- Excludes sensitive files (credentials, mapper.csv)
- Excludes Python cache and backup files
- Keeps directory structure with .gitkeep files

#### README.md (UPDATED)
- Comprehensive installation guide
- Usage instructions for UI and batch processing
- Configuration guide
- Troubleshooting section
- Architecture overview

#### MIGRATION_GUIDE.md (NEW - this file)
- Documents the migration process
- Breaking changes and fixes

## Breaking Changes

### 1. Archive Directory Path

**Impact:** Batch processing and external archive access

**OLD:** Hardcoded in each file
```python
STATEMENTS_DIR = "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL_extracted"
```

**NEW:** Configurable in `config.py`
```python
STATEMENTS_ARCHIVE_DIR = os.environ.get(
    "AIRTEL_ARCHIVE_DIR",
    "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL_extracted"
)
```

**Fix:**
- Default still points to old location (no immediate action needed)
- To customize: Set environment variable `AIRTEL_ARCHIVE_DIR`
- Or edit `config.py` line 26

### 2. Mapper.py Database Helper

**Impact:** `mapper.py` script only

**OLD:** Direct import
```python
from helpers import connect_to_database_engine
```

**NEW:** Path-based import with error handling
```python
sys.path.insert(0, '../data_score_factors')
from helpers import connect_to_database_engine
```

**Fix:**
- Ensure `data_score_factors` project exists in parent directory
- Or update the path in `mapper.py` line 6

### 3. Google Credentials Path

**Impact:** Google Sheets export feature only

**OLD:** Relative path
```python
credentials_file = os.path.join(os.path.dirname(__file__), 'google_credentials.json')
```

**NEW:** From config
```python
from config import GOOGLE_CREDENTIALS_FILE
credentials_file = GOOGLE_CREDENTIALS_FILE
```

**Fix:**
- No action needed if credentials file is in project root
- Path is `airtel_fraud_detection/google_credentials.json`

## Migration Steps (If Needed)

If you need to migrate existing data from old location:

### 1. Move Data Files

```bash
# Copy balance summary
cp data_score_factors/fraud_detection/results/balance_summary.csv \
   airtel_fraud_detection/results/

# Copy detailed sheets
cp data_score_factors/fraud_detection/detailed_sheets/*.csv \
   airtel_fraud_detection/detailed_sheets/

# Copy mapper
cp data_score_factors/fraud_detection/mapper.csv \
   airtel_fraud_detection/
```

### 2. Update Archive Path (Optional)

If you want to move the archive to the new project:

```bash
# Create archive directory
mkdir -p airtel_fraud_detection/archive

# Copy statements
cp -r data_score_factors/DATA/archive/UATL_extracted \
      airtel_fraud_detection/archive/

# Update config.py
# Change line 26 to: os.path.join(PROJECT_ROOT, "archive", "UATL_extracted")
```

### 3. Setup Virtual Environment

```bash
cd airtel_fraud_detection
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Test

```bash
# Test UI
streamlit run app.py

# Test batch processing
python batch_process_statements.py --help
```

## Verification Checklist

After migration, verify:

- [ ] Streamlit UI launches successfully
- [ ] Can upload and process a PDF
- [ ] Results appear in `results/balance_summary.csv`
- [ ] Detailed sheets saved to `detailed_sheets/`
- [ ] Download buttons work
- [ ] Batch processing can locate archive statements
- [ ] Mapper.py can access helpers module
- [ ] No hardcoded paths in error messages

## Rollback

If needed, the old project location is untouched:

```bash
cd data_score_factors/fraud_detection
streamlit run app.py  # Old installation still works
```

## Future Considerations

### Complete Independence

To make the project fully independent from `data_score_factors`:

1. **Copy helpers.py:**
   ```bash
   cp ../data_score_factors/helpers.py .
   ```

2. **Update mapper.py:**
   ```python
   from helpers import connect_to_database_engine  # Local import
   ```

3. **Move archive:**
   ```bash
   mkdir archive
   # Move or symlink UATL_extracted
   ```

### Deployment

For production deployment:

1. Set environment variables:
   ```bash
   export AIRTEL_ARCHIVE_DIR="/production/archive/path"
   ```

2. Use systemd or supervisor to run Streamlit:
   ```bash
   streamlit run app.py --server.port 8501
   ```

3. Setup nginx reverse proxy (optional)

## Notes

- **Original project preserved:** All files in `data_score_factors/fraud_detection/` remain unchanged
- **Data continuity:** Existing results and detailed sheets copied to new location
- **No data loss:** Migration is non-destructive
- **Backward compatible:** Default paths still reference old archive location

## Support

For migration issues:
1. Check error messages for path-related issues
2. Verify `config.py` settings
3. Ensure virtual environment activated
4. Check file permissions on data directories

---

**Migration completed successfully!** ✅

The Airtel Fraud Detection System is now a standalone project with improved configuration management and documentation.
