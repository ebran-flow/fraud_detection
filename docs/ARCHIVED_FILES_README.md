# Archived Files Documentation

**Archive Date:** 2025-10-11
**Archive File:** `archived_unused_files_20251011_210717.zip` (47KB)

## Purpose

This archive contains files and code that are no longer used in the current FastAPI + HTMX implementation of the multi-provider fraud detection system. These files were part of the original Streamlit-based application and the single-provider architecture.

## What Was Archived

### 1. Root Directory Files (Old Streamlit Application)

#### Main Application Files
- **app.py** - Original Streamlit application entry point (replaced by `backend/app/main.py` with FastAPI)
- **streamlit_ui.py** - Streamlit UI implementation (replaced by FastAPI + HTMX templates)
- **batch_process_statements.py** - Old batch processing script for statements
- **config.py** - Old configuration file (replaced by `backend/app/config.py`)

#### Parsing and Processing Files
- **fraud.py** - Old PDF metadata extraction (only used by archived parser.py)
- **process_statements.py** - Original PDF parsing logic (replaced by parsers in `backend/app/services/parsers/`)
- **mapper.py** - Old account mapper (replaced by `backend/app/services/mapper.py`)
- **uatl_export.py** - Old export script (replaced by `backend/app/services/export.py`)
- **generate_segmented_balance.py** - Old utility for segmented balance generation

#### Debug and Test Files
- **analyze_format2_issues.py** - Debugging script for Format 2 issues
- **debug_ampm.py** - AM/PM parsing debug script
- **debug_balance.py** - Balance calculation debug script
- **debug_find_txn.py** - Transaction search debug script
- **debug_format2_balance.py** - Format 2 balance debug script
- **debug_pages.py** - PDF page parsing debug script
- **debug_second_format.py** - Second format debug script
- **debug_statement.py** - Statement debug script
- **test_fix.py** - Test/fix utility script

### 2. Backend Service Files (Old Single-Provider Architecture)

Located in archive: `backend_services/`

- **crud.py** - Old CRUD service with single-provider architecture (replaced by `crud_v2.py` with multi-provider factory pattern)
- **parser.py** - Old PDF parser wrapper (replaced by provider-specific parsers in `backend/app/services/parsers/`)

## Why These Files Were Archived

### Migration from Streamlit to FastAPI + HTMX
The application was completely rewritten from a Streamlit-based UI to a FastAPI backend with HTMX frontend. All Streamlit-related files (`app.py`, `streamlit_ui.py`) became obsolete.

### Migration from Single-Provider to Multi-Provider Architecture
The original system only supported UATL (Airtel). The new system uses:
- **Factory Pattern** (`ProviderFactory`) for dynamic provider routing
- **Provider-Specific Models** (separate tables per provider: `uatl_raw_statements`, `umtn_raw_statements`, etc.)
- **crud_v2.py** replacing old `crud.py` with multi-provider support

### Consolidation of Parsing Logic
Old parsing files (`fraud.py`, `process_statements.py`, `parser.py`) were consolidated into:
- `backend/app/services/parsers/uatl_parser.py` - UATL PDF parsing
- `backend/app/services/parsers/uatl_csv_parser.py` - UATL CSV parsing
- `backend/app/services/parsers/umtn_parser.py` - UMTN parsing
- `backend/app/services/processor.py` - Centralized processing logic

### Debug Scripts No Longer Needed
All debug scripts were one-time use files for troubleshooting specific issues during development. These issues have been resolved and the scripts are no longer needed.

## Current Active Architecture

### Backend Structure (FastAPI)
```
backend/app/
├── api/v1/          # REST endpoints
├── models/          # Database models (multi-provider)
├── services/
│   ├── parsers/     # Provider-specific parsers
│   ├── processor.py # Processing logic with Format 1/2 support
│   ├── crud_v2.py   # Multi-provider CRUD
│   └── ...
└── templates/       # HTMX templates
```

### Key Features Retained and Improved
1. **Multi-Provider Support** - UATL (Airtel) and UMTN (MTN)
2. **Multiple Format Support** - Format 1 (CSV/PDF with Credit/Debit) and Format 2 (PDF with signed amounts)
3. **Duplicate Detection** - Based on txn_id + txn_date + amount + description
4. **Same-Timestamp Optimization** - Permutation testing for correct transaction order
5. **Running Balance Calculation** - Smart handling of signed/unsigned amounts with fees
6. **Provider Selection UI** - Explicit dropdown for provider selection

## How to Restore Archived Files (If Needed)

If you need to reference or restore any archived files:

```bash
# Extract the archive
unzip archived_unused_files_20251011_210717.zip

# View specific file
cat archived_unused_files/app.py

# Restore specific file (example)
cp archived_unused_files/debug_balance.py ./

# Remove extracted folder when done
rm -rf archived_unused_files/
```

## Important Notes

- **Do not restore these files** unless you have a specific reason to reference old implementation details
- The current system is fully functional without these files
- All functionality from archived files has been reimplemented in the new architecture
- These files are kept as backup/reference only

## Archive Contents Summary

**Total Files Archived:** 21 files
- 18 root directory files (Streamlit app + debug scripts)
- 2 backend service files (old CRUD + parser)
- 1 documentation file (this README)

**Archive Size:** 47KB (compressed)

---

*This archive was created as part of the codebase cleanup on October 11, 2025, following the successful migration to FastAPI + HTMX multi-provider architecture.*
