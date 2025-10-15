# Scripts Directory

This directory contains all analysis, testing, migration, and utility scripts for the fraud detection system.

## Folder Structure

```
scripts/
├── analysis/          # Production analysis and fraud detection scripts
├── migration/         # Database schema and migration scripts
├── test/              # Testing and debugging scripts
└── utils/             # Reusable utility scripts
```

## 📊 analysis/

Production-ready scripts for fraud detection analysis and database updates.

### Main Analysis Scripts
- **`scan_header_manipulation.py`** - Scan PDFs for header row manipulation (Format 2 only)
  - Detects headers mixed in transaction data
  - Outputs to JSON for manual verification
  - ~4 statements/sec on 10,557 statements (45 mins)

- **`extract_additional_metrics.py`** - Extract fraud detection metrics
  - Transaction ID integrity (gaps, duplicates)
  - Balance jumps (>50% changes)
  - Timestamp anomalies (same-second, non-chronological)
  - Amount patterns (round numbers, Benford's Law)
  - PDF metadata validation

### Database Update Scripts
- **`update_header_rows_count.py`** - Update header_rows_count in metadata table
- **`update_header_rows_count_fast.py`** - Fast version using pypdfium2 (32x faster)
- **`update_header_rows_suspicious.py`** - Update only suspicious statements

**Usage:**
```bash
# Scan for header manipulation (Format 2 only)
python scripts/analysis/scan_header_manipulation.py

# Extract additional fraud metrics
python scripts/analysis/extract_additional_metrics.py
```

## 🧪 test/

Testing and debugging scripts for development and verification.

### Comparison & Performance Tests
- **`compare_all_pdf_libs.py`** - Benchmark PDF libraries (pdfplumber vs PyMuPDF vs pypdfium2)
- **`compare_pdf_speed.py`** - Speed comparison between PDF libraries
- **`compare_pdf_speed_v2.py`** - Enhanced speed comparison
- **`compare_pages.py`** - Compare clean vs manipulated page structures

### Validation Tests
- **`check_balance_match.py`** - Verify no false positives on balance_match='Success'
- **`test_additional_metrics.py`** - Test metrics extraction on sample statements
- **`test_pymupdf_layout.py`** - Test PyMuPDF layout extraction
- **`test_single_pdf.py`** - Debug single PDF processing

### Debugging Tools
- **`debug_pdf_text.py`** - Debug PDF text extraction
- **`check_page_lines.py`** - Analyze page line structure

**Usage:**
```bash
# Run performance comparison
python scripts/test/compare_all_pdf_libs.py

# Test on random samples
python scripts/test/test_additional_metrics.py
```

## 🗄️ migration/

Database schema and migration files.

- **`create_all_tables.sql`** - Complete CREATE TABLE statements for all tables and views
  - Includes all recent columns (header_rows_count, missing_days_detected, etc.)
  - Ready for fresh database setup

- **`database_schema.txt`** - Human-readable database schema documentation
  - All table structures with types, keys, indexes
  - View definitions

**Usage:**
```bash
# Create fresh database (WARNING: drops existing database)
mysql -u root -p < scripts/migration/create_all_tables.sql
```

## 🔧 utils/

Reusable utility scripts for data conversion and helpers.

- **`convert_results_to_csv.py`** - Convert header manipulation JSON results to CSV
- **`convert_additional_metrics_to_csv.py`** - Convert additional metrics JSON to CSV

**Usage:**
```bash
# Convert header manipulation results to CSV
python scripts/utils/convert_results_to_csv.py

# Convert additional metrics to CSV
python scripts/utils/convert_additional_metrics_to_csv.py
```

## Key Findings & Metrics

### Header Manipulation Detection
- **Total Format 2 Statements Scanned:** 10,557
- **Manipulated:** 126 (1.2%)
- **Clean:** 10,431 (98.8%)
- **Detection Method:** Headers appearing in transaction data instead of at top of page

### Additional Fraud Metrics
Based on test samples, fraudulent statements show:
- **Duplicate Transaction IDs:** 100% of tested fraudulent statements had duplicates
- **Balance Jumps:** Up to 318,000% single-transaction balance changes
- **Same-Second Transactions:** Correlates perfectly with duplicate transaction IDs
- **Round Numbers:** 98-99% of amounts (may be normal for mobile money)

### Performance Benchmarks (88-page PDF)
- **pdfplumber:** 41s (baseline, accurate)
- **PyMuPDF:** 0.5s (78x faster, but inaccurate - cell-by-cell extraction)
- **pypdfium2:** 1.22s (32x faster, 100% accurate) ✅ **RECOMMENDED**

## Output Files

Results are saved to the backend root directory:
- `header_manipulation_results.json` - Full header manipulation scan results
- `header_manipulation_results.csv` - CSV version for Excel review
- `additional_metrics_results.json` - Full additional metrics results
- `additional_metrics_results.csv` - CSV version for Excel review
- `header_scan_full.log` - Full scan log

## Development Notes

### Why pypdfium2?
- 32x faster than pdfplumber
- 100% accuracy (same results as pdfplumber)
- Preserves table structure (unlike PyMuPDF)

### Format 1 vs Format 2
- **Format 1:** Airtel statements with summary section (email, customer name, etc.)
- **Format 2:** Airtel statements without summary section
- **Header manipulation check:** Only run on Format 2 (Format 1 has different structure)

### Column Additions (Oct 13-14, 2025)
- `metadata.header_rows_count` - Count of header rows in transaction data
- `metadata.quality_issues_count` - Count of data quality issues
- `summary.missing_days_detected` - Boolean flag for timeline gaps
- `summary.gap_related_balance_changes` - Count of gap-related balance issues
- `uatl_raw_statements.amount_raw` - Original amount before cleaning
- `uatl_raw_statements.fee_raw` - Original fee before cleaning
- `umtn_raw_statements.fee_raw` - Original fee before cleaning

## Contributing

When adding new scripts:
1. **analysis/** - Production fraud detection and database updates
2. **test/** - Development testing and debugging
3. **migration/** - Database schema changes
4. **utils/** - Reusable helper functions

Follow naming conventions:
- Analysis: `scan_*.py`, `extract_*.py`, `update_*.py`
- Tests: `test_*.py`, `check_*.py`, `compare_*.py`, `debug_*.py`
- Utils: `convert_*.py`, `*_helper.py`
- Migrations: `*.sql`, `*_schema.txt`
