# Airtel Statement Fraud Detection

Python scripts and Streamlit UI for parsing, validating, and analyzing Airtel Money statements.

## Features

✅ **PDF Parsing**: Extract transaction data from Airtel statement PDFs
✅ **Balance Verification**: Verify computed balance matches statement closing balance
✅ **Metadata Extraction**: Extract PDF metadata (title, author, creator, dates)
✅ **RM Enrichment**: Merge with mapper.csv to add RM details
✅ **Web UI**: Interactive Streamlit interface for processing statements
✅ **CSV Export**: Download results as CSV for further analysis

## Project Structure

```
fraud_detection/
├── statements/              # Raw Airtel statement PDFs
├── uploaded_pdfs/           # Temporarily uploaded PDFs from UI
├── results/                 # Generated summary CSVs
├── mapper.csv               # Mapping table (run_id → acc_number, RM info)
├── fraud.py                 # Utility functions (metadata extraction)
├── uatl_export.py           # Reference PDF parsing logic
├── process_statements.py    # CLI script to process PDFs
├── app.py                   # Streamlit web UI
├── run_app.sh              # Script to launch Streamlit
├── context.txt             # Requirements for process_statements.py
├── ui_context.txt          # Requirements for Streamlit UI
└── README.md               # This file
```

## Installation

Use the project's virtual environment (venv already has all dependencies):

```bash
source /home/ebran/Developer/projects/data_score_factors/venv/bin/activate
```

## Usage

### Option 1: Command Line (Batch Processing)

Process all PDFs in the `statements/` folder:

```bash
/home/ebran/Developer/projects/data_score_factors/venv/bin/python fraud_detection/process_statements.py
```

Output: `results/balance_summary.csv`

### Option 2: Streamlit Web UI (Interactive)

Launch the web interface:

```bash
./fraud_detection/run_app.sh
```

Or manually:

```bash
cd /home/ebran/Developer/projects/data_score_factors
/home/ebran/Developer/projects/data_score_factors/venv/bin/streamlit run fraud_detection/app.py
```

Then open your browser to: `http://localhost:8501`

#### UI Features:
1. **Upload**: Upload one or multiple PDF statements
2. **Process**: Click "Process Statements" to analyze
3. **Review**: View summary table with balance verification
4. **Download**: Export results as timestamped CSV

## Balance Verification Formula

```python
closing_balance = opening_balance + credits - debits
```

**Note**: Fees are already included in transaction amounts for Airtel statements.

## Output Columns

The generated CSV includes:

| Column | Description |
|--------|-------------|
| run_id | Request ID from mapper |
| rm_name | Relationship Manager name |
| account_number | Airtel mobile number |
| file_name | Original PDF filename |
| balance_match | "Success" or "Failed" |
| opening_balance | Starting balance |
| credits | Total credit transactions |
| debits | Total debit transactions |
| fees | Total fees charged |
| charges | Additional charges (if any) |
| closing_balance | Ending balance from statement |
| title | PDF title metadata |
| author | PDF author metadata |
| creator | PDF creator software |
| producer | PDF producer |
| created_at | PDF creation timestamp |
| modified_at | PDF modification timestamp |
| error | Error message (if failed) |

## Technical Details

### Date Format Handling

The parser handles Airtel's date formats:
- `%d-%m-%y %I:%M %p` (e.g., "31-08-25 11:14 PM")
- `%d-%m-%y %H:%M` (e.g., "31-08-25 23:14")

**Important**: Uses `%I` for 12-hour format to correctly parse AM/PM.

### Data Types

- **Dates**: `datetime` objects
- **Amounts**: `float` (cleaned from comma-separated strings)
- **Text**: `str` (trimmed)

## Future Enhancements

- [ ] Commission disbursement handling
- [ ] Same-time transaction logic
- [ ] Failed transaction filtering
- [ ] Transaction reversal detection
- [ ] Multiple Airtel format support
- [ ] Enhanced error reporting

## Troubleshooting

### Balance Mismatch

If balance verification fails:
1. Check if all transactions are included
2. Verify date parsing (AM/PM issues)
3. Inspect the PDF for non-standard formats

### Missing RM Data

If `run_id` or `rm_name` are empty:
- Ensure `mapper.csv` contains the account number
- Check account number extraction from PDF

### Import Errors

Always use the venv Python:
```bash
/home/ebran/Developer/projects/data_score_factors/venv/bin/python
```

## Dependencies

- pdfplumber
- pandas
- streamlit
- numpy
- logging

All installed in the project venv.
