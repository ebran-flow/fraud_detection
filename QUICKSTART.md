# Quick Start Guide

Get the fraud detection system running in 5 minutes.

## Prerequisites

- MySQL running on port 3307
- Python 3.8+

## Setup Commands

```bash
# 1. Create database
mysql -h localhost -P 3307 -u root -p << 'EOF'
CREATE DATABASE IF NOT EXISTS fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit
EOF

# 2. Load schema
cd /home/ebran/Developer/projects/airtel_fraud_detection
mysql -h localhost -P 3307 -u root -p fraud_detection < backend/schema_v2_multitenancy.sql

# 3. Create .env file
cd backend
cat > .env << 'EOF'
DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=YOUR_PASSWORD_HERE
DB_NAME=fraud_detection
UPLOADED_PDF_PATH=../uploaded_pdfs
MAPPER_CSV=../mapper.csv
LOG_LEVEL=INFO
EOF

# ⚠️ Edit .env and replace YOUR_PASSWORD_HERE with your actual MySQL password
nano .env

# 4. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Create directories
cd ..
mkdir -p uploaded_pdfs backend/logs results detailed_sheets

# 6. Create empty mapper
touch mapper.csv
echo "run_id,acc_number,rm_name,acc_prvdr_code,status,lambda_status,created_date" > mapper.csv

# 7. Start the application
cd backend
./start.sh
```

## Test It Works

Open new terminal:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Open browser
# Visit: http://localhost:8000
```

## Upload Your First File

### Airtel PDF:
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "files=@/path/to/statement.pdf"
```

### MTN Excel:
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "files=@/path/to/statement.xlsx"
```

## Common Commands

```bash
# Start server
cd backend && ./start.sh

# Stop server
# Press CTRL+C

# View logs
tail -f backend/logs/app.log

# Check database
mysql -h localhost -P 3307 -u root -p fraud_detection -e "SHOW TABLES;"

# List uploaded files
curl http://localhost:8000/api/v1/list
```

## File Formats Supported

- **Airtel (UATL)**: PDF files → stored in `uatl_raw_statements`
- **MTN (UMTN)**: Excel/CSV files → stored in `umtn_raw_statements`

System automatically detects provider from file extension!

## Troubleshooting

**Can't connect to database?**
```bash
# Test MySQL connection
mysql -h localhost -P 3307 -u root -p

# Check Docker MySQL is running
docker ps | grep mysql
```

**Module not found?**
```bash
# Activate venv
cd backend
source venv/bin/activate

# Reinstall
pip install -r requirements.txt
```

**Tables don't exist?**
```bash
# Reload schema
mysql -h localhost -P 3307 -u root -p fraud_detection < backend/schema_v2_multitenancy.sql
```

## What You Get

✅ Multi-provider support (Airtel PDF + MTN Excel)
✅ Automatic provider detection
✅ Duplicate detection
✅ Balance verification
✅ Fraud detection
✅ CSV/Excel export
✅ REST API + Web UI

## Next Steps

See **SETUP_GUIDE.md** for detailed setup instructions and testing.
