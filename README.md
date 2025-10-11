# Airtel Fraud Detection System

A comprehensive system to verify Airtel Money business wallet statements by calculating running balances, detecting discrepancies, duplicates, and potential fraud indicators.

## Features

- ✅ **Automated Balance Verification** - Calculates row-by-row running balance and compares with statement
- ✅ **Smart Transaction Ordering** - Handles same-timestamp transactions using intelligent permutation testing
- ✅ **Duplicate Detection** - Identifies duplicate transactions automatically
- ✅ **Special Transaction Handling** - Properly processes Commission Disbursements, Deallocation, Rollbacks, Reversals
- ✅ **Two Format Support** - Handles both Format 1 (unsigned amounts) and Format 2 (signed amounts)
- ✅ **Batch Processing** - Process multiple statements automatically
- ✅ **Web UI** - User-friendly Streamlit interface
- ✅ **Data Integrity** - MD5 hashing and row count tracking

## Project Structure

```
airtel_fraud_detection/
├── config.py                      # Configuration (paths, settings)
├── process_statements.py          # Core processing engine
├── app.py                         # Streamlit web UI
├── batch_process_statements.py   # Batch processor
├── mapper.py                      # Database mapper generator
├── requirements.txt               # Python dependencies
├── README.md                      # This file
│
├── uploaded_pdfs/                 # UI uploads
├── results/
│   └── balance_summary.csv        # Main results database
├── detailed_sheets/               # Transaction-level CSVs
├── batch_results/                 # Batch processing reports
└── statements/                    # Test statements for development
```

## Installation

### 1. Clone/Copy Project

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Paths

Edit `config.py` to set your archive directory:

```python
# Update this to point to your Airtel statements archive
STATEMENTS_ARCHIVE_DIR = "/path/to/your/statements/archive"
```

Or set environment variable:

```bash
export AIRTEL_ARCHIVE_DIR="/path/to/your/statements/archive"
```

### 5. (Optional) Setup Google Sheets Integration

If you want to export to Google Sheets:

1. Create a Google Cloud project
2. Enable Google Sheets API and Google Drive API
3. Create service account and download credentials
4. Save as `google_credentials.json` in project root

See `GOOGLE_SHEETS_SETUP.md` for detailed instructions.

## Usage

### Web UI (Recommended)

```bash
streamlit run app.py
```

Then open browser to: `http://localhost:8501`

**Features:**
- Upload single or multiple PDFs
- Select checks to perform (Metadata, Balance Summary)
- View results with color-coded verification status
- Download summary CSV and detailed transaction sheets

### Batch Processing

Process all statements for a specific month:

```bash
python batch_process_statements.py 202509  # September 2025
```

**Features:**
- Processes all Airtel (UATL) statements from `mapper.csv`
- Skips already processed statements
- Updates `balance_summary.csv` incrementally
- Saves detailed sheets for each statement

### Generate Mapper CSV

Fetch statement metadata from database:

```bash
python mapper.py
```

**Requirements:**
- Access to the data_score_factors project (for `helpers.py`)
- Database connection configured in `helpers.py`

## Configuration

### config.py

Central configuration file for all paths:

```python
PROJECT_ROOT              # Auto-detected project root
UPLOADED_PDF_PATH         # Where UI uploads PDFs
RESULTS_PATH              # Where balance_summary.csv is stored
DETAILED_SHEETS_PATH      # Transaction-level CSV files
BATCH_RESULTS_PATH        # Batch processing results
STATEMENTS_PATH           # Test statements
MAPPER_CSV                # mapper.csv location
STATEMENTS_ARCHIVE_DIR    # External archive (configurable)
```

### Environment Variables

```bash
export AIRTEL_ARCHIVE_DIR="/path/to/archive"  # Override archive location
```

## Output Files

### balance_summary.csv

High-level summary with columns:
- `run_id`, `rm_name`, `account_number`, `file_name`
- `verification_status`, `verification_reason`, `balance_match`
- `sheet_row_count`, `duplicate_count`, `balance_diff_changes`
- `calculated_closing_balance`, `stmt_closing_balance`
- `opening_balance`, `credits`, `debits`, `fees`
- `detailed_csv`, `sheet_md5`
- PDF metadata fields

### Detailed Sheets

`detailed_sheets/{run_id}_detailed.csv` with columns:
- `txn_id`, `txn_date`, `description`, `status`
- `amount`, `txn_direction`, `fee`, `balance`
- `calculated_running_balance`, `balance_diff`
- `is_duplicate`, `is_special_txn`, `special_txn_type`
- `balance_diff_change_count`

## Verification Statuses

| Status | Meaning |
|--------|---------|
| ✅ **Verified** | Balance matches perfectly |
| ⚠️ **Needs Additional Verification** | Balance mismatch with <2% change ratio (likely Airtel-side issue) |
| ❌ **Failed Verification** | Balance mismatch with ≥2% change ratio (requires review) |
| 📄 **Statement Not Found** | PDF file not in archive |
| ⚠️ **Statement Read Failed** | Error processing PDF |

## Dependencies

- **pandas** - Data manipulation
- **pdfplumber** - PDF parsing
- **streamlit** - Web UI
- **SQLAlchemy** - Database access (for mapper.py)
- **gspread** - Google Sheets (optional)

See `requirements.txt` for full list.

## Architecture

### Core Components

1. **process_statements.py** - Single source of truth for all calculations
   - `extract_data_from_pdf()` - Parse PDF transactions
   - `calculate_running_balance()` - Calculate balance with smart ordering
   - `get_pdf_metadata()` - Extract PDF metadata

2. **app.py** - Streamlit web interface
   - File upload
   - Processing controls (checkboxes)
   - Results display with styling
   - Download options

3. **batch_process_statements.py** - Automated batch processing
   - Filters for Airtel (UATL) only
   - Skips processed statements
   - Incremental updates to CSV

### Data Flow

```
PDF Upload → Extract Data → Calculate Balance → Save Results
                ↓
        Two Formats Supported:
        - Format 1: Unsigned amounts
        - Format 2: Signed amounts
                ↓
        Smart Processing:
        - Same-timestamp ordering
        - Special transaction handling
        - Duplicate detection
                ↓
        Outputs:
        - balance_summary.csv (metadata)
        - detailed_sheets/*.csv (transactions)
```

## Advanced Features

### Same-Timestamp Transaction Ordering

When multiple transactions occur at the exact same timestamp, the system:
1. Groups transactions by timestamp
2. Tests all permutations (for groups ≤6)
3. Calculates running balance for each ordering
4. Picks the order where calculated balances match statement balances

### Special Transaction Handling

- **Deallocation/Rollback/Reversal/Failed** - Keep previous balance (no change)
- **Commission Disbursement** - Apply opposite logic (debit=add, credit=subtract)
- **Duplicates** - Keep previous balance

### Balance Diff Change Tracking

Tracks how many times the difference between calculated and statement balance changes:
- Low ratio (<2%) = Likely Airtel-side issue (missing transactions)
- High ratio (≥2%) = Calculation error requiring review

## Troubleshooting

### Import Error: helpers module not found

The `mapper.py` script requires access to `helpers.py` from the `data_score_factors` project:

```bash
# Ensure data_score_factors is in the parent directory
ls /home/ebran/Developer/projects/data_score_factors/helpers.py
```

### Statement Not Found

Ensure `STATEMENTS_ARCHIVE_DIR` in `config.py` points to the correct archive folder containing PDF files.

### Database Clear

To clear all processed statements from UI:
1. Open Streamlit UI
2. Scroll to bottom: "Clear All Database" section
3. Click "Clear All Database" → Confirm

**Note:** This only clears `balance_summary.csv`, not detailed sheets.

## Documentation

- **TECHNICAL_DOCUMENTATION.md** - Detailed technical breakdown
- **EDGE_CASE_ANALYSIS.md** - Analysis of failure patterns
- **GOOGLE_SHEETS_SETUP.md** - Google Sheets integration guide

## Contributing

When modifying the code:
1. Keep all core logic in `process_statements.py` (DRY principle)
2. Update `config.py` if adding new paths
3. Test with both Format 1 and Format 2 statements
4. Update documentation

## License

Internal use only.

## Support

For issues or questions, contact the development team.
# fraud_detection
