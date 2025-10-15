# PyPDFium2 Migration Testing Plan

## Current Situation

- **This laptop:** Has `temp_fraud_detection` database (empty), no `fraud_detection` database
- **Main laptop:** Has `fraud_detection` database with all imported data
- **Goal:** Test if pypdfium2 can replace pdfplumber to speed up PDF imports

## Speed Comparison (From Previous Tests)

| Library | Speed (88-page PDF) | Accuracy | Notes |
|---------|---------------------|----------|-------|
| pdfplumber | 41s | 100% | Current system (table extraction) |
| PyMuPDF | 0.5s (78x faster) | 0% | Inaccurate (cell-by-cell extraction) |
| pypdfium2 | 1.22s (32x faster) | 100% | Fast & accurate (text extraction only) |

## Challenge

**pypdfium2 does NOT have table extraction** like pdfplumber's `extract_tables()`.
- pdfplumber: Has `page.extract_tables()` - extracts structured table data
- pypdfium2: Only has `page.get_textpage().get_text_range()` - extracts plain text

For Airtel PDF parsing, we NEED table structure to extract transactions correctly.

## Two Approaches

### Option 1: Hybrid Approach (Recommended)
Use pypdfium2 for fast operations, pdfplumber only for table extraction:
- **Metadata extraction:** pypdfium2 (faster)
- **Format detection:** pypdfium2 text extraction (faster)
- **Table extraction:** pdfplumber (only for transaction data)
- **Header manipulation detection:** pypdfium2 (32x faster, already proven)

**Expected speedup:** 20-30% (not 32x, since table extraction is still pdfplumber)

### Option 2: Alternative Table Extraction
Research alternative table extraction libraries:
- **camelot-py:** Table extraction from PDFs
- **tabula-py:** Java-based table extraction
- **pdfminer.six + custom logic:** Lower-level parsing

**Risk:** May require significant code rewrite, uncertain accuracy

## Recommended Next Steps

### Step 1: Baseline Current System (On Main Laptop)
```bash
# On main laptop with fraud_detection database
python scripts/test/test_pdf_import_speed.py --sample-size 20
```

This will show:
- Current average time per PDF
- Estimated time to import all 12,412 Airtel PDFs
- Identify if PDF parsing is actually the bottleneck

### Step 2: Profile the Bottleneck
Before switching libraries, identify where time is spent:
- PDF parsing (pdfplumber)
- Database inserts
- Data validation/cleaning
- Balance calculations

### Step 3: If PDF Parsing is Bottleneck, Test Hybrid
Create `pdf_utils_pypdfium2.py` with hybrid approach:
```python
# Fast operations with pypdfium2
def detect_pdf_format_fast(pdf_path):
    pdf = pdfium.PdfDocument(pdf_path)
    text = pdf[0].get_textpage().get_text_range()
    return 2 if 'USER STATEMENT' in text else 1

def extract_metadata_fast(pdf_path):
    pdf = pdfium.PdfDocument(pdf_path)
    return pdf.get_metadata_dict()

# Keep pdfplumber for table extraction
def extract_tables(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        # ... existing table extraction logic
```

### Step 4: A/B Test
Import 100 PDFs with both methods:
1. Original pdfplumber
2. Hybrid pypdfium2/pdfplumber

Compare:
- Speed
- Data accuracy (transaction counts, balances)
- Memory usage

## Files Created

### Temp Database Setup
- ✅ `scripts/migration/create_temp_database.py` - Creates temp_fraud_detection
- ✅ Database created with tables: metadata, summary, uatl_raw_statements, etc.

### Testing Scripts
- ✅ `scripts/test/test_pdf_import_speed.py` - Benchmark current system
- ⏳ `scripts/test/test_hybrid_parser.py` - TO BE CREATED
- ⏳ `scripts/analysis/import_with_pypdfium2.py` - TO BE CREATED

## What Needs to Happen

### On This Laptop (Testing Environment)
1. ⏳ Create hybrid parser (pypdfium2 + pdfplumber)
2. ⏳ Import sample of Airtel PDFs to temp_fraud_detection
3. ⏳ Export temp_fraud_detection for comparison

### On Main Laptop (Production Environment)
1. ⏳ Import temp_fraud_detection as temp database
2. ⏳ Run comparison query:
```sql
-- Compare transaction counts
SELECT
    'fraud_detection' as source,
    COUNT(*) as total,
    COUNT(DISTINCT run_id) as statements,
    MIN(txn_date) as earliest,
    MAX(txn_date) as latest
FROM fraud_detection.uatl_raw_statements
UNION ALL
SELECT
    'temp_fraud_detection' as source,
    COUNT(*) as total,
    COUNT(DISTINCT run_id) as statements,
    MIN(txn_date) as earliest,
    MAX(txn_date) as latest
FROM temp_fraud_detection.uatl_raw_statements;

-- Find differences
SELECT COALESCE(f.run_id, t.run_id) as run_id,
       f.txn_count as fraud_detection_count,
       t.txn_count as temp_fraud_detection_count,
       ABS(f.txn_count - t.txn_count) as difference
FROM (
    SELECT run_id, COUNT(*) as txn_count
    FROM fraud_detection.uatl_raw_statements
    GROUP BY run_id
) f
FULL OUTER JOIN (
    SELECT run_id, COUNT(*) as txn_count
    FROM temp_fraud_detection.uatl_raw_statements
    GROUP BY run_id
) t ON f.run_id = t.run_id
WHERE f.txn_count != t.txn_count OR f.txn_count IS NULL OR t.txn_count IS NULL;
```

## Decision Criteria

**Switch to pypdfium2 IF:**
- ✅ Speed improvement > 25%
- ✅ Data accuracy = 100%
- ✅ No increase in memory usage
- ✅ Code complexity remains manageable

**Stick with pdfplumber IF:**
- Current speed is acceptable (<5 hours for full dataset)
- Bottleneck is NOT in PDF parsing
- pypdfium2 hybrid doesn't provide significant speedup

## Reality Check

From our header manipulation scan:
- Scanned 10,557 PDFs in 45 minutes using pypdfium2
- Speed: 3.91 PDFs/second
- For full 12,412 Airtel PDFs: ~53 minutes

But that was just text extraction for header detection, NOT full table extraction for transactions.

**Key Question:** How long does current pdfplumber-based import take for all 12,412 PDFs?
- If it's < 3 hours: Probably not worth the migration risk
- If it's > 10 hours: Definitely worth investigating pypdfium2 hybrid

## Recommendation

1. **First:** Run baseline test on main laptop to see current import speed
2. **Then:** If it's slow (>5 hours), proceed with hybrid approach
3. **Finally:** Test on sample, compare results, decide

**Do NOT blindly migrate without knowing if it's actually a problem!**
