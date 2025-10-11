# Airtel Fraud Detection System - Detailed Technical Documentation

## Tech Stack Overview

### Core Technologies

```
┌─────────────────────────────────────────────────────────────────┐
│                        TECH STACK                                │
├─────────────────────────────────────────────────────────────────┤
│ Frontend/UI:      Streamlit 1.x                                  │
│ Backend Logic:    Python 3.10                                    │
│ PDF Processing:   pdfplumber                                     │
│ Data Processing:  pandas, numpy                                  │
│ Storage:          CSV files (flat file database)                │
│ Hashing:          hashlib (MD5)                                  │
│ Date/Time:        datetime, pandas.Timestamp                     │
│ Database Access:  SQLAlchemy (for mapper.py only)               │
│ Web Server:       Built-in Streamlit server                      │
├─────────────────────────────────────────────────────────────────┤
│ Optional:                                                        │
│ Google Sheets:    gspread, google-auth                          │
│ Visualization:    streamlit charts                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## UI Sections Breakdown

### 1. **Header Section** (Lines 454-464)
```python
st.title("🔍 Airtel Statement Fraud Detection")
st.markdown("Upload Airtel statement PDFs...")
```

**Tech:**
- `st.title()` - Renders H1 title
- `st.markdown()` - Supports markdown formatting
- Shows count of existing statements from CSV

**Behavior:**
```
IF balance_summary.csv exists:
    Display: "📊 {count} statement(s) in database"
ELSE:
    No message shown
```

---

### 2. **Checkbox Section** (Lines 466-475)
```python
st.subheader("⚙️ Select Checks to Perform")
col1, col2 = st.columns(2)
with col1:
    check_metadata = st.checkbox("📋 Metadata Extraction", value=True)
with col2:
    check_balance = st.checkbox("💰 Balance Summary & Duplicate Detection", value=True)
check_duplicates = check_balance  # Tied together
```

**Tech:**
- `st.columns(2)` - Creates 2-column layout
- `st.checkbox()` - Boolean input widget
- `value=True` - Default checked state
- `help="..."` - Tooltip on hover

**Checkbox Options:**

| Checkbox | What It Does | Dependencies |
|----------|-------------|--------------|
| **📋 Metadata Extraction** | Extracts PDF metadata (author, dates, creator, producer) | None |
| **💰 Balance Summary & Duplicate Detection** | Calculates running balance, detects duplicates, verifies closing balance | Always includes duplicate detection |

**Important:** Duplicate detection is NOT a separate checkbox - it's automatically done when balance summary is checked.

**Code Logic:**
```python
check_duplicates = check_balance  # Line 475
# This means: duplicate detection = ON when balance summary = ON
```

---

### 3. **File Upload Section** (Lines 477-486)
```python
uploaded_files = st.file_uploader(
    "Upload PDF Statement(s)",
    type=['pdf'],
    accept_multiple_files=True,
    help="Upload one or more Airtel statement PDFs"
)
```

**Tech:**
- `st.file_uploader()` - File upload widget
- `type=['pdf']` - Restricts to PDF only
- `accept_multiple_files=True` - Allows batch upload
- Returns: List of `UploadedFile` objects (in-memory file buffers)

**File Storage Flow:**
```
User uploads PDF
    ↓
Streamlit stores in memory (UploadedFile object)
    ↓
app.py saves to: uploaded_pdfs/{filename}.pdf (Line 77-79)
    ↓
Process from disk (not from memory)
    ↓
Keep in uploaded_pdfs/ for reference
```

---

### 4. **Processing Button & Results** (Lines 488-660)

#### 4A. Process Button (Lines 489-497)
```python
if st.button("🚀 Process Statements", type="primary"):
    with st.spinner("Processing statements..."):
        result_df, newly_processed, skipped = process_uploaded_pdfs(...)
```

**Tech:**
- `st.button()` - Clickable button widget
- `type="primary"` - Blue prominent button style
- `st.spinner()` - Shows loading animation during processing
- Returns: Boolean (True when clicked)

**Processing Logic:**
```python
def process_uploaded_pdfs(uploaded_files, existing_df, checks...):
    for each file:
        Extract run_id from filename
        Check if already processed with requested checks
        IF already processed:
            Skip file (add to skipped list)
        ELSE:
            Process file (add to newly_processed list)
            Save to detailed_sheets/

    Combine new + existing results
    Update balance_summary.csv
    Return: (result_df, newly_processed, skipped)
```

**Skip Logic** (Lines 284-301):
```python
# Check if already processed with ALL requested checks
balance_done = not check_balance OR record has balance_match
metadata_done = not check_metadata OR record has title
duplicates_done = not check_duplicates OR record has duplicate_count

IF balance_done AND metadata_done AND duplicates_done:
    SKIP (already fully processed)
ELSE:
    REPROCESS
```

---

#### 4B. Summary Statistics (Lines 506-519)
```python
col1, col2, col3, col4 = st.columns(4)
st.metric("Total Statements", len(result_df))
st.metric("Balance Match Success", success_count)
st.metric("Balance Match Failed", failed_count)
st.metric("Total Duplicates", int(total_dupes))
```

**Tech:**
- `st.columns(4)` - 4-column grid layout
- `st.metric()` - Card-style metric display with label and value
- Auto-calculates from result_df

---

#### 4C. Results Table (Lines 522-600)

**Column Ordering** (Lines 528-538):
```python
column_order = [
    'run_id', 'rm_name', 'account_number', 'file_name',
    'balance_match', 'verification_status', 'verification_reason',
    'sheet_row_count', 'duplicate_count', 'balance_diff_changes', 'balance_diff_change_ratio',
    'calculated_closing_balance', 'stmt_closing_balance',
    'opening_balance', 'credits', 'debits', 'fees', 'charges',
    'detailed_csv', 'sheet_md5',
    'title', 'author', 'has_author', 'creator', 'producer',
    'created_at', 'modified_at', 'has_modified_at',
    'error'
]
```

**Styling Logic** (Lines 551-596):
```python
# Highlight newly processed rows (yellow background)
lambda row: ['background-color: #fff3cd' if newly_processed else '']

# Color code balance_match column
highlight_balance_match(val):
    'Success' → Green (#d4edda)
    'Failed' → Red (#f8d7da)

# Color code verification_status column
highlight_verification_status(val):
    'Verified' → Green (#d4edda)
    'Needs Additional Verification' → Yellow (#fff3cd)
    'Failed Verification' → Red (#f8d7da)

# Color code duplicate_count column
highlight_duplicate_count(val):
    0 → Green (#d4edda)
    >0 → Red (#f8d7da)
```

**Tech:**
- `styled_df = display_df.style.apply()` - Pandas Styler API
- `.applymap()` - Apply function to each cell
- CSS-like color codes in RGB hex
- `st.dataframe()` - Interactive sortable table widget

---

#### 4D. Download Section (Lines 602-650)

**Tech:**
- `st.download_button()` - Triggers file download
- `data=csv` - In-memory CSV string
- `mime="text/csv"` - Sets HTTP content type
- No actual file created on server (streaming download)

**Download Options:**

1. **Summary CSV** (Left column)
   - Downloads current results table
   - Filename: `balance_summary_YYYYMMDD_HHMMSS.csv`
   - Source: In-memory DataFrame → CSV string

2. **Detailed Sheets** (Right column)
   - Dropdown selector: Shows all processed files
   - Reads from: `detailed_sheets/{run_id}_detailed.csv`
   - Filename: `{run_id}_detailed.csv`
   - Source: File on disk

---

### 5. **Existing Results Display** (Lines 661-821)

**Trigger:** Shown when NO new files uploaded BUT balance_summary.csv exists

**Behavior Difference:**

| Scenario | Upload Section | Checkboxes | Process Button | Results Table | Download Section |
|----------|---------------|-----------|----------------|---------------|------------------|
| **No upload, CSV exists** | Empty | Visible | Hidden | Shows all from CSV | **Static** (always visible) |
| **Files uploaded** | Shows files | Visible | Visible | Shows after process | Dynamic (after process) |
| **No upload, no CSV** | Empty | Visible | Hidden | Hidden | Hidden |

**Static Download Section** (Lines 748-821):
```python
# ALWAYS visible when existing_results is not empty
st.subheader("📥 Download Options")

# Left: Summary CSV
IF balance_summary.csv exists:
    Show download button
ELSE:
    Show info: "No summary available yet"

# Right: Detailed sheets
IF detailed_sheets/ has files:
    Show dropdown + download button
    Scan folder for all *_detailed.csv files
ELSE:
    Show info: "No detailed sheets available yet"
```

---

### 6. **Clear Database Section** (Lines 823-863)

**Tech:**
- `st.session_state` - Streamlit's session storage (preserves state across reruns)
- `st.rerun()` - Refreshes the entire app

**Flow:**
```
Initial state: confirm_clear = False
    ↓
Click "🗑️ Clear All Database"
    ↓
Set confirm_clear = True + st.rerun()
    ↓
Show warning: "⚠️ This will permanently delete ALL records!"
    ↓
Two buttons appear:
    - "✅ Yes, Delete All"  → Creates empty CSV + rerun
    - "❌ Cancel"           → Set confirm_clear = False + rerun
```

**Deletion Logic** (Lines 836-849):
```python
# Creates EMPTY CSV with column headers
empty_df = pd.DataFrame(columns=[...all columns...])
empty_df.to_csv(csv_path, index=False)
```

**Important:** This only clears `balance_summary.csv`, NOT the detailed sheets in `detailed_sheets/` folder!

---

## CSV "Database" Structure

### Why CSV Instead of Real Database?

**Advantages:**
- ✅ Simple - No DB setup required
- ✅ Portable - Copy folder = copy database
- ✅ Human-readable - Open in Excel/Google Sheets
- ✅ Version control friendly (can track in git)
- ✅ No connection/authentication issues

**Disadvantages:**
- ❌ No concurrent writes (single user only)
- ❌ No ACID guarantees
- ❌ Full file rewrite on every update
- ❌ No indexing (slow for large datasets)
- ❌ No relationships (just flat files)

### File Structure

```
fraud_detection/
├── results/
│   └── balance_summary.csv          ← Main "database" (metadata)
└── detailed_sheets/
    ├── {run_id}_detailed.csv        ← Transaction-level data (1 file per statement)
    ├── 68b5699446f1e_detailed.csv
    ├── 68b58b4ecd86e_detailed.csv
    └── ...
```

### Database Operations

#### CREATE (Insert New Record)
```python
# Line 331-333
new_df = pd.DataFrame(summaries)
combined_df = pd.concat([existing_df, new_df])
save_results(combined_df)  # Writes entire CSV
```

#### READ (Load Records)
```python
# Line 44-53
def load_existing_results():
    csv_path = os.path.join(RESULTS_PATH, 'balance_summary.csv')
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()
```

#### UPDATE (Modify Existing Record)
```python
# Line 316-321
combined_df = pd.concat([existing_df, new_df], ignore_index=True)
# Drop duplicates, keep='last' means newest version wins
combined_df = combined_df.drop_duplicates(subset=['run_id'], keep='last')
save_results(combined_df)
```

#### DELETE (Clear All)
```python
# Line 838-849
empty_df = pd.DataFrame(columns=[...])
empty_df.to_csv(csv_path, index=False)
```

**Note:** There is NO DELETE for individual records - only "clear all"

---

## Detailed Sheets Storage

### Structure

Each processed statement gets its own CSV file:

```
detailed_sheets/
├── {run_id}_detailed.csv           ← Naming pattern
│   ├── txn_id
│   ├── txn_date
│   ├── description
│   ├── amount
│   ├── balance (from PDF)
│   ├── calculated_running_balance (our calculation)
│   ├── balance_diff
│   ├── is_duplicate
│   ├── is_special_txn
│   └── ... (14 columns total)
```

### Why Separate Files?

1. **Performance:** Don't load 3000+ rows into main UI table
2. **Scalability:** Main summary = lightweight, detailed sheets = heavy
3. **On-demand:** Only load detailed sheet when user downloads it
4. **Organization:** One statement = one file (easy to find/manage)

### File Naming Convention

```
{run_id}_detailed.csv

Example:
68b5699446f1e_detailed.csv
    ↓
run_id: 68b5699446f1e
PDF file: 68b5699446f1e.pdf
```

### Lifecycle

```
Upload PDF
    ↓
Process (calculate_running_balance)
    ↓
Save: detailed_sheets/{run_id}_detailed.csv  (Line 179-181)
    ↓
Calculate MD5 hash                            (Line 186-189)
    ↓
Store filename + hash in balance_summary.csv
    ↓
User can download via dropdown
```

---

## State Management & UI Behavior

### Upload vs No Upload Behavior

#### Scenario 1: Files Uploaded
```
UI Components Visible:
✅ Header with DB count
✅ Checkboxes
✅ File uploader (shows upload count)
✅ Process button
❌ Existing results table (hidden until after processing)
❌ Download section (hidden until after processing)

After clicking Process:
✅ Processing summary (newly processed / skipped counts)
✅ Summary metrics (4 columns)
✅ Results table (with new rows highlighted)
✅ Download buttons (dynamic - based on processed files)
✅ Error section (if any errors)
```

#### Scenario 2: No Upload, CSV Exists
```
UI Components Visible:
✅ Header with DB count
✅ Checkboxes (inactive - no files to process)
✅ File uploader (empty state)
❌ Process button (hidden - nothing to process)
✅ Existing results table (all records from CSV)
✅ Summary metrics (3 columns instead of 4)
✅ Download section (STATIC - always visible)
✅ Clear database section
```

#### Scenario 3: No Upload, No CSV
```
UI Components Visible:
✅ Header (no DB count)
✅ Checkboxes
✅ File uploader (empty state)
❌ Everything else hidden
✅ Info message: "👆 Please upload PDF statement(s) to begin"
```

### Session State Variables

```python
st.session_state.confirm_clear  # Boolean for delete confirmation
# No other session state used (stateless design)
```

**Why Stateless?**
- Streamlit reruns entire script on every interaction
- No need to persist uploaded files (saved to disk immediately)
- Results always loaded fresh from CSV
- Simplifies logic (no state sync issues)

---

## Processing Pipeline Deep Dive

### Single File Processing (process_single_pdf)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. SAVE UPLOADED FILE TO DISK                                   │
│    uploaded_pdfs/{filename}.pdf                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. EXTRACT DATA FROM PDF (process_statements.py)                │
│    • Detect format (1 or 2)                                     │
│    • Parse transactions table                                   │
│    • Return: (DataFrame, account_number)                        │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. CALCULATE RUNNING BALANCE (process_statements.py)            │
│    • Smart same-timestamp ordering                              │
│    • Mark special transactions                                  │
│    • Mark duplicates                                            │
│    • Calculate balance_diff per row                             │
│    • Track balance_diff change count                            │
│    • Return: DataFrame with 14 columns                          │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. SAVE DETAILED SHEET                                          │
│    detailed_sheets/{run_id}_detailed.csv                        │
│    • Calculate MD5 hash                                         │
│    • Calculate row count                                        │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. COMPUTE SUMMARY STATISTICS (if balance check enabled)        │
│    • Opening balance                                            │
│    • Total credits/debits                                       │
│    • Closing balance (calculated vs statement)                  │
│    • Balance match status                                       │
│    • Verification status (based on change ratio)                │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. EXTRACT METADATA (if metadata check enabled)                 │
│    • PDF author, title, creator, producer                       │
│    • Creation/modification dates                                │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. RETURN SUMMARY DICT                                          │
│    Contains all fields for balance_summary.csv row              │
└─────────────────────────────────────────────────────────────────┘
```

### Batch Processing (process_uploaded_pdfs)

```
Load existing balance_summary.csv
    ↓
For each uploaded file:
    ├─ Extract run_id from filename
    ├─ Check if already processed (with requested checks)
    │   ├─ YES → Add to skipped list
    │   └─ NO  → Process → Add to newly_processed list
    └─ Continue
    ↓
Combine new + existing results (update duplicates)
    ↓
Save updated balance_summary.csv
    ↓
Return: (result_df, newly_processed, skipped)
```

---

## Database Clearing Mechanism

### What Gets Cleared

```python
# Line 838-849
empty_df = pd.DataFrame(columns=[...all 28 columns...])
empty_df.to_csv(csv_path, index=False)
```

**Result:**
```csv
run_id,rm_name,account_number,file_name,...
(no data rows - only headers)
```

### What DOES NOT Get Cleared

1. **Detailed sheets** - Files in `detailed_sheets/` remain untouched
2. **Uploaded PDFs** - Files in `uploaded_pdfs/` remain untouched
3. **Batch results** - Files in `batch_results/` remain untouched

### Why This Design?

- **Safety:** Detailed data preserved (can regenerate summary)
- **Audit Trail:** Original PDFs kept for reference
- **Selective Clearing:** Only clear high-level index, not raw data

### Manual Full Cleanup

```bash
# Clear summary
rm fraud_detection/results/balance_summary.csv

# Clear detailed sheets
rm -rf fraud_detection/detailed_sheets/*.csv

# Clear uploaded PDFs
rm -rf fraud_detection/uploaded_pdfs/*.pdf

# Clear batch results
rm -rf fraud_detection/batch_results/*.csv
```

---

## Download Mechanisms

### Download Button Tech

```python
st.download_button(
    label="📄 Download Summary CSV",
    data=csv_string,              # In-memory string
    file_name="output.csv",       # Suggested filename
    mime="text/csv",              # HTTP content type
    help="...",                   # Tooltip
    use_container_width=True,     # Full width button
    key="unique_key"              # Widget identifier
)
```

**How It Works:**
1. User clicks button
2. Browser triggers download (via Streamlit JavaScript)
3. Data streamed from Python → Browser
4. No file created on server
5. User's browser saves file to Downloads folder

### Summary CSV Download

**Source:** In-memory DataFrame
```python
csv = display_df.to_csv(index=False)  # Line 609
# Converts DataFrame to CSV string in memory
```

**Filename Format:**
```
balance_summary_20251011_023045.csv
                ^^^^^^^^ YYYYMMDD_HHMMSS
```

### Detailed Sheet Download

**Source:** File on disk
```python
detailed_csv_path = os.path.join(DETAILED_SHEETS_PATH, detailed_csv_name)
with open(detailed_csv_path, 'r') as f:
    detailed_csv_data = f.read()  # Line 638-639
# Reads entire file into string
```

**Filename:** Preserved from disk (`{run_id}_detailed.csv`)

---

## Column Definitions

### balance_summary.csv Columns

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| `run_id` | string | Unique statement ID | Filename (without .pdf) |
| `rm_name` | string | Relationship Manager name | mapper.csv (if available) |
| `account_number` | string | Airtel account number | Extracted from PDF |
| `file_name` | string | PDF filename | Upload name |
| `balance_match` | string | Success/Failed | Comparison of calculated vs statement |
| `verification_status` | string | Verified/Needs Additional Verification/Failed | Based on change ratio |
| `verification_reason` | string | Explanation text | Generated based on status |
| `sheet_row_count` | integer | Number of transactions | len(detailed_df) |
| `duplicate_count` | integer | Duplicate transactions | Sum of is_duplicate |
| `balance_diff_changes` | integer | Times balance_diff changed | Max of change_count column |
| `balance_diff_change_ratio` | float | changes / total rows | Calculated ratio |
| `calculated_closing_balance` | float | Our calculated final balance | From calculate_running_balance() |
| `stmt_closing_balance` | float | PDF statement final balance | Last row balance from PDF |
| `opening_balance` | float | Starting balance | Back-calculated from first txn |
| `credits` | float | Total credits | Sum of credit transactions |
| `debits` | float | Total debits | Sum of debit transactions |
| `fees` | float | Total fees | Sum of fee column |
| `charges` | float | Total charges | Currently always 0 |
| `detailed_csv` | string | Detailed sheet filename | {run_id}_detailed.csv |
| `sheet_md5` | string | MD5 hash of detailed CSV | Hex digest |
| `title` | string | PDF title metadata | From PDF metadata |
| `author` | string | PDF author metadata | From PDF metadata |
| `has_author` | string | Yes/No | Indicates if author field exists |
| `creator` | string | PDF creator software | From PDF metadata |
| `producer` | string | PDF producer software | From PDF metadata |
| `created_at` | string | PDF creation date | Parsed from metadata |
| `modified_at` | string | PDF modification date | Parsed from metadata |
| `has_modified_at` | string | Yes/No | Indicates if modified date exists |
| `error` | string | Error message if failed | Exception string or empty |

### {run_id}_detailed.csv Columns

| Column | Type | Description |
|--------|------|-------------|
| `txn_id` | string | Transaction ID from PDF |
| `txn_date` | datetime | Transaction timestamp |
| `description` | string | Transaction description |
| `status` | string | Transaction status |
| `amount` | float | Transaction amount |
| `txn_direction` | string | Credit/Debit (Format 1 only) |
| `fee` | float | Transaction fee |
| `balance` | float | Balance from PDF statement |
| `pdf_format` | integer | 1 or 2 |
| `is_duplicate` | boolean | True if duplicate |
| `is_special_txn` | boolean | True if special handling |
| `special_txn_type` | string | Commission/Deallocation/etc |
| `calculated_running_balance` | float | Our calculated balance |
| `balance_diff` | float | statement - calculated |
| `balance_diff_change_count` | integer | Cumulative change count |

---

## Performance Characteristics

### Processing Speed
- **Single statement (1000 rows):** ~2-3 seconds
- **Single statement (3000 rows):** ~10-15 seconds
- **Batch (100 statements):** ~30-40 minutes

### File Sizes
- **balance_summary.csv:** ~10-20 KB per 100 records
- **Detailed sheet:** ~100-500 KB per statement (varies by row count)
- **Uploaded PDF:** Varies (typically 500 KB - 2 MB)

### Scalability Limits
- **Max CSV rows:** ~10,000 statements before UI becomes slow
- **Max detailed sheet rows:** No hard limit (tested up to 5000 rows)
- **Concurrent users:** 1 (CSV write conflicts with multiple users)

---

## Error Handling

### PDF Processing Errors
```python
# Line 247-272
except Exception as e:
    return {
        'run_id': ...,
        'error': str(e),
        'balance_match': 'Failed',
        # ... all other fields set to default values
    }
```

**Result:** Record added to CSV with error message in `error` column

### File Not Found
```python
# Line 88-94
if df.empty:
    return {'error': 'No transactions found'}
```

### Database Load Errors
```python
# Line 48-52
try:
    return pd.read_csv(csv_path)
except Exception as e:
    logger.error(f"Error loading: {e}")
    return pd.DataFrame()  # Return empty, don't crash
```

---

## Summary

The Airtel Fraud Detection System is a **Streamlit-based web application** that uses **CSV files as a flat-file database** to store processing results. The UI is divided into distinct sections that behave differently based on whether files are uploaded and whether existing data exists in the database.

**Key Design Decisions:**
1. **Stateless UI:** Entire app reruns on every interaction
2. **CSV Storage:** Simple, portable, human-readable
3. **Separate Detailed Sheets:** Main table = lightweight index, detailed data = separate files
4. **Skip Logic:** Avoids reprocessing already-analyzed statements
5. **DRY Principle:** All core logic in process_statements.py, UI just calls functions

**Storage Architecture:**
- `balance_summary.csv` = Main database (metadata/summary)
- `detailed_sheets/` = Transaction-level data (1 file per statement)
- `uploaded_pdfs/` = Original PDFs (for reference)
- `batch_results/` = Batch processing logs

This architecture prioritizes **simplicity** and **maintainability** over enterprise features like concurrent access or complex querying.
