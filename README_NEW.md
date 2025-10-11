# Airtel Fraud Detection System v2.0

A modernized fraud detection system for Airtel mobile money statements with FastAPI backend and HTMX frontend.

## Features

- **PDF Upload & Parsing**: Upload Airtel statement PDFs (Format 1 & 2), automatically parse and store in database
- **Duplicate Detection**: Automatically detect duplicate transactions
- **Balance Verification**: Calculate running balance and compare with statement balance
- **Fraud Detection**: Identify special transactions (Commission Disbursements, Reversals, etc.)
- **Multi-format Support**: Handles both Airtel statement formats seamlessly
- **Export Functionality**: Download processed statements and summaries as CSV or Excel
- **Batch Processing**: Process multiple statements at once
- **Web Interface**: Modern, responsive HTMX-based UI
- **REST API**: Full REST API for integration

## Architecture

### Backend (FastAPI)
- **Database**: MySQL (connects to existing instance on port 3307)
- **ORM**: SQLAlchemy for database operations
- **API**: RESTful API with automatic OpenAPI documentation
- **Services**: Modular service layer (parser, processor, mapper, export)
- **Models**: 4 main tables (raw_statements, metadata, processed_statements, summary)

### Frontend (HTMX)
- **No Build Step**: Pure HTML with HTMX for dynamic updates
- **Tailwind CSS**: Modern, responsive styling
- **Single Page App**: Dashboard with table view and action buttons

## Prerequisites

- Python 3.10 or higher
- MySQL 8.0+ (running on port 3307)
- Existing PDF parsing logic from `process_statements.py` and `fraud.py`
- `mapper.csv` file for mapping run_ids to account details

## Quick Start

### 1. Setup

```bash
# Run setup script
./setup.sh

# This will:
# - Create virtual environment
# - Install dependencies
# - Create .env file from template
# - Create necessary directories
```

### 2. Configure Database

Edit `.env` file with your database credentials:

```bash
DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=fraud_detection
```

### 3. Initialize Database

```bash
# Run the SQL schema to create tables
mysql -u root -p -P 3307 < backend/schema.sql

# Or if you're connecting from within Docker:
docker exec -i your_mysql_container mysql -u root -p -P 3307 < backend/schema.sql
```

### 4. Start Application

```bash
# Single command to start everything
./start.sh
```

The application will be available at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## Usage

### Web Interface

1. **Upload PDFs**: Click "Upload PDF" button and select one or more PDF files
2. **Process Statements**: Select statements from the table and click "Process Selected"
3. **Download Results**: Click "Download Processed" or "Download Summary" to export data
4. **Delete Data**: Select statements and choose to delete processed data or all data

### API Endpoints

#### Upload PDFs
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@statement1.pdf" \
  -F "files=@statement2.pdf"
```

#### Process Statements
```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["68babf7f23139", "68bacafe8a1b7"]}'
```

#### List Statements
```bash
curl "http://localhost:8000/api/v1/list?page=1&page_size=50"
```

#### Download Processed Data (CSV)
```bash
curl "http://localhost:8000/api/v1/download/processed?format=csv" \
  -o processed_statements.csv
```

#### Download Summary (Excel)
```bash
curl "http://localhost:8000/api/v1/download/summary?format=excel" \
  -o summary.xlsx
```

#### Delete Processed Data Only
```bash
curl -X POST "http://localhost:8000/api/v1/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["68babf7f23139"],
    "delete_all": false,
    "confirm": true
  }'
```

#### Delete All Data
```bash
curl -X POST "http://localhost:8000/api/v1/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["68babf7f23139"],
    "delete_all": true,
    "confirm": true
  }'
```

## Project Structure

```
airtel_fraud_detection/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── upload.py      # PDF upload endpoint
│   │   │       ├── process.py     # Processing endpoint
│   │   │       ├── download.py    # Export endpoints
│   │   │       ├── delete.py      # Deletion endpoint
│   │   │       ├── statements.py  # List endpoint
│   │   │       ├── status.py      # Health check
│   │   │       └── ui.py          # HTMX HTML endpoints
│   │   ├── models/               # SQLAlchemy models
│   │   │   ├── raw.py
│   │   │   ├── metadata.py
│   │   │   ├── processed.py
│   │   │   └── summary.py
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/             # Business logic
│   │   │   ├── db.py            # Database connection
│   │   │   ├── crud.py          # CRUD operations (DRY)
│   │   │   ├── parser.py        # PDF parsing wrapper
│   │   │   ├── processor.py     # Balance verification
│   │   │   ├── mapper.py        # Mapper.csv loader
│   │   │   └── export.py        # CSV/Excel export
│   │   ├── templates/           # HTMX templates
│   │   │   ├── index.html
│   │   │   └── statements_table.html
│   │   ├── static/              # CSS/JS (if needed)
│   │   ├── config.py            # Configuration
│   │   └── main.py              # FastAPI app
│   ├── schema.sql               # Database schema
│   └── requirements.txt         # Python dependencies
├── uploaded_pdfs/               # Uploaded PDF storage
├── mapper.csv                   # Run ID mapping
├── process_statements.py        # Existing parsing logic (reused)
├── fraud.py                     # Existing metadata logic (reused)
├── .env                         # Environment variables
├── .env.example                 # Environment template
├── setup.sh                     # Setup script
├── start.sh                     # Startup script
└── README_NEW.md                # This file
```

## Database Schema

### 1. raw_statements
Stores minimally processed transactions from PDF parsing
- Unique constraint on (run_id, txn_id)
- Indexes on acc_number and run_id

### 2. metadata
Document-level and parsing-related info (one row per run_id)
- Contains PDF metadata, balances, and mapper data
- Unique constraint on run_id

### 3. processed_statements
Adds processing-level information:
- Duplicate detection flags
- Special transaction types
- Calculated running balance
- Balance differences

### 4. summary
Final verification summary per run_id:
- Balance match status
- Verification status and reason
- Credits, debits, fees totals
- Duplicate counts

## Key Features & Business Rules

### PDF Parsing
- **Format 1**: Traditional format with Credit/Debit column
- **Format 2**: USER STATEMENT format with signed amounts
- Automatically detects format and applies correct parsing logic

### Duplicate Detection
- Detects duplicates based on: transaction date + amount + description
- Marks first occurrence as original, subsequent as duplicates

### Balance Verification
- Calculates running balance from transactions
- Compares with statement balance at each step
- Tracks balance difference changes for fraud detection

### Special Transactions (Format 2)
- **Commission Disbursement**: Balance restart point
- **Deallocation Transfer**: Balance restart point
- **Transaction Reversal**: Balance restart point
- **Rollback**: Balance restart point

### Segmented Balance Calculation
For Format 2, balance calculation restarts after special transactions, ensuring accurate verification.

## DRY Principles

The codebase follows DRY (Don't Repeat Yourself) principles:

- **CRUD Operations**: Centralized in `services/crud.py`
- **Database Connection**: Single connection manager in `services/db.py`
- **PDF Parsing**: Reuses existing `process_statements.py` logic
- **Metadata Extraction**: Reuses existing `fraud.py` logic
- **Export Logic**: Shared export functions in `services/export.py`

## Extending the System

### Adding New Providers
1. Update parser service to handle new format
2. Add provider code to mapper.csv
3. Update metadata model if needed

### Adding New Endpoints
1. Create new router in `backend/app/api/v1/`
2. Register in `main.py`
3. Add schemas in `schemas/`

### Custom Processing Logic
- Extend `processor.py` with new validation functions
- Add new columns to processed_statements table
- Update summary generation logic

## Troubleshooting

### Database Connection Issues
```bash
# Check MySQL is running
mysql -u root -p -P 3307 -e "SELECT 1"

# Verify .env configuration
cat .env
```

### PDF Parsing Errors
- Ensure PDF is valid Airtel format
- Check file permissions on uploaded_pdfs/
- Review logs for specific error messages

### Import Errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r backend/requirements.txt
```

## Development

### Running in Development Mode
```bash
# Start with auto-reload
source venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

### Logs
Application logs are printed to console. Adjust log level in `.env`:
```bash
LOG_LEVEL=DEBUG  # For verbose logging
```

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Environment Variables
Set these in production:
- `DB_PASSWORD`: Secure database password
- `LOG_LEVEL`: Set to `WARNING` or `ERROR`
- Adjust CORS settings in `main.py`

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Migration from Streamlit

This version replaces the Streamlit app (`app.py`) with a modern FastAPI backend and HTMX frontend.

**Key Differences:**
- ✅ No direct PDF processing - all data stored in database
- ✅ RESTful API for programmatic access
- ✅ Persistent storage with MySQL
- ✅ Batch operations support
- ✅ Better separation of concerns (services layer)
- ✅ Automatic duplicate prevention (run_id check)
- ✅ DRY principles throughout

**Preserved Functionality:**
- ✅ All PDF parsing logic unchanged
- ✅ Balance verification logic unchanged
- ✅ Format 1 & 2 support unchanged
- ✅ Metadata extraction unchanged
- ✅ Mapper integration unchanged

## License

[Your License Here]

## Support

For issues or questions, please contact the development team or create an issue in the project repository.
