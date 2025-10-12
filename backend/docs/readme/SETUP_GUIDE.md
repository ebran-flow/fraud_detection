# Complete Setup Guide - Airtel Fraud Detection System

This guide walks you through setting up the fraud detection system from scratch with multi-provider support (Airtel + MTN).

## Prerequisites

✅ MySQL running in Docker on port 3307
✅ Python 3.8 or higher
✅ Git (for version control)

## Step-by-Step Setup

### Step 1: Verify MySQL is Running

```bash
# Check if MySQL container is running
docker ps | grep mysql

# Test connection
mysql -h localhost -P 3307 -u root -p
# Enter your password when prompted
# If you can connect, type 'exit' to quit
```

### Step 2: Create Database

Connect to MySQL and create the database:

```bash
mysql -h localhost -P 3307 -u root -p
```

Then run these SQL commands:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Verify it was created
SHOW DATABASES;

-- Exit
exit;
```

### Step 3: Create Database Schema

Now load the multi-provider schema:

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection

# Load the schema
mysql -h localhost -P 3307 -u root -p fraud_detection < backend/schema_v2_multitenancy.sql
```

Enter your MySQL password when prompted.

**Verify the schema was created:**

```bash
mysql -h localhost -P 3307 -u root -p fraud_detection -e "SHOW TABLES;"
```

You should see:
```
+---------------------------+
| Tables_in_fraud_detection |
+---------------------------+
| metadata                  |
| summary                   |
| uatl_processed_statements |
| uatl_raw_statements       |
| umtn_processed_statements |
| umtn_raw_statements       |
+---------------------------+
```

### Step 4: Create .env File

Create a `.env` file in the `backend` directory:

```bash
cd backend
cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=fraud_detection

# Application Settings
UPLOADED_PDF_PATH=../uploaded_pdfs
MAPPER_CSV=../mapper.csv
LOG_LEVEL=INFO
EOF
```

**⚠️ IMPORTANT**: Replace `your_password_here` with your actual MySQL root password.

### Step 5: Create Required Directories

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection

# Create all necessary directories
mkdir -p backend/logs
mkdir -p uploaded_pdfs
mkdir -p results
mkdir -p detailed_sheets

# Verify
ls -la
```

### Step 6: Setup Python Virtual Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

This will install:
- FastAPI, uvicorn (web server)
- SQLAlchemy, pymysql (database)
- pandas, numpy (data processing)
- pdfplumber (PDF parsing)
- openpyxl (Excel support for MTN)
- jinja2 (templates)

**Wait for installation to complete** (may take 1-2 minutes).

### Step 7: Create Mapper File (Optional)

The mapper.csv file links run_ids to account details. Create a basic one:

```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection

cat > mapper.csv << 'EOF'
run_id,acc_number,rm_name,acc_prvdr_code,status,lambda_status,created_date
EOF
```

This creates an empty mapper. You can add entries later as needed.

### Step 8: Test Database Connection

```bash
cd backend
source venv/bin/activate

# Quick test
python3 << 'EOF'
from app.services.db import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM metadata"))
        print("✅ Database connection successful!")
        print(f"Metadata table has {result.scalar()} records")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
EOF
```

Expected output: `✅ Database connection successful!`

### Step 9: Start the Application

```bash
cd backend
source venv/bin/activate

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8501
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8501 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 10: Test the Application

Open a new terminal and test the API:

```bash
# Health check
curl http://localhost:8501/api/v1/health

# Should return: {"status":"ok"}

# System status
curl http://localhost:8501/api/v1/status

# Should return statistics about the database
```

### Step 11: Access the Web UI

Open your browser and go to:

```
http://localhost:8501/
```

You should see the fraud detection dashboard.

## Testing with Sample Data

### Test 1: Upload Airtel PDF

```bash
# Upload a PDF file (UATL)
curl -X POST "http://localhost:8501/api/v1/upload" \
  -F "files=@/path/to/your/statement.pdf"
```

Replace `/path/to/your/statement.pdf` with an actual PDF file path.

### Test 2: Upload MTN Excel

```bash
# Upload the MTN Excel file you shared earlier
curl -X POST "http://localhost:8501/api/v1/upload" \
  -F "files=@/home/ebran/Downloads/68b53484e2b54/1756705924.xlsx"
```

### Test 3: List Statements

```bash
curl "http://localhost:8501/api/v1/list?page=1&page_size=10"
```

### Test 4: Process Statements

```bash
# Get run_ids from the list response, then process
curl -X POST "http://localhost:8501/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{"run_ids": ["1756705924"]}'
```

### Test 5: Download Results

```bash
# Download as CSV
curl "http://localhost:8501/api/v1/download/processed?format=csv" \
  --output results.csv

# Download as Excel
curl "http://localhost:8501/api/v1/download/processed?format=excel" \
  --output results.xlsx
```

## Verify Multi-Provider Setup

Check that both provider tables exist:

```bash
mysql -h localhost -P 3307 -u root -p fraud_detection << 'EOF'
-- Check UATL tables
SELECT COUNT(*) as uatl_raw_count FROM uatl_raw_statements;
SELECT COUNT(*) as uatl_processed_count FROM uatl_processed_statements;

-- Check UMTN tables
SELECT COUNT(*) as umtn_raw_count FROM umtn_raw_statements;
SELECT COUNT(*) as umtn_processed_count FROM umtn_processed_statements;

-- Check metadata (shared)
SELECT acc_prvdr_code, COUNT(*) as count
FROM metadata
GROUP BY acc_prvdr_code;
EOF
```

## Directory Structure After Setup

```
airtel_fraud_detection/
├── backend/
│   ├── venv/                  # Virtual environment
│   ├── app/                   # Application code
│   ├── .env                   # Database credentials
│   ├── requirements.txt       # Dependencies
│   ├── schema_v2_multitenancy.sql  # Database schema
│   ├── logs/                  # Application logs
│   └── start.sh              # Startup script
├── uploaded_pdfs/            # Uploaded files stored here
├── results/                  # CSV results (if using old system)
├── detailed_sheets/          # Detailed sheets (if using old system)
├── mapper.csv               # Account mapping
└── DATABASE_MIGRATION.md    # Migration guide
```

## Troubleshooting

### Issue: "Can't connect to MySQL server"

**Solution:**
```bash
# Check if MySQL is running
docker ps | grep mysql

# If not running, start it
docker start <mysql_container_id>

# Check port 3307 is exposed
docker port <mysql_container_id>
```

### Issue: "Access denied for user 'root'@'localhost'"

**Solution:**
- Double-check password in `backend/.env`
- Test connection manually: `mysql -h localhost -P 3307 -u root -p`

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```bash
# Make sure virtual environment is activated
cd backend
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Table doesn't exist"

**Solution:**
```bash
# Reload the schema
mysql -h localhost -P 3307 -u root -p fraud_detection < backend/schema_v2_multitenancy.sql
```

### Issue: "Port 8501 already in use"

**Solution:**
```bash
# Find process using port 8501
lsof -i :8501

# Kill it
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

## Next Steps

1. ✅ **Add mapper entries** - Create entries in `mapper.csv` for your accounts
2. ✅ **Upload statements** - Start uploading PDF (Airtel) or Excel (MTN) files
3. ✅ **Process data** - Run processing on uploaded statements
4. ✅ **Export results** - Download processed data as CSV or Excel

## Starting and Stopping

**To start the application:**
```bash
cd /home/ebran/Developer/projects/airtel_fraud_detection/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8501
```

**To stop:**
- Press `CTRL+C` in the terminal running uvicorn

**Alternative - Use the startup script:**
```bash
cd backend
chmod +x start.sh
./start.sh
```

## Configuration

### Database Connection

Edit `backend/.env` to change database settings:

```env
DB_HOST=localhost        # MySQL host
DB_PORT=3307            # MySQL port
DB_USER=root            # MySQL user
DB_PASSWORD=yourpass    # MySQL password
DB_NAME=fraud_detection # Database name
```

### File Upload Path

Edit `backend/.env` to change upload directory:

```env
UPLOADED_PDF_PATH=/custom/path/to/uploads
```

### Mapper CSV Path

Edit `backend/.env` to change mapper location:

```env
MAPPER_CSV=/custom/path/to/mapper.csv
```

## API Documentation

Once the server is running, visit:

```
http://localhost:8501/docs
```

This shows interactive API documentation (Swagger UI) where you can test all endpoints.

## Support

If you encounter any issues:

1. Check logs: `backend/logs/app.log`
2. Check database: `mysql -h localhost -P 3307 -u root -p fraud_detection`
3. Check API docs: `http://localhost:8501/docs`
4. Verify `.env` file has correct credentials

## Success Checklist

- [ ] MySQL running on port 3307
- [ ] Database `fraud_detection` created
- [ ] Tables created (6 tables: uatl_*, umtn_*, metadata, summary)
- [ ] `.env` file created with correct password
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] Application starts without errors
- [ ] Health check returns `{"status":"ok"}`
- [ ] Web UI accessible at http://localhost:8501
- [ ] Can upload files successfully
- [ ] Can process and export data

---

**Setup Complete!** 🎉

Your multi-provider fraud detection system is ready to process both Airtel (PDF) and MTN (Excel) statements.
