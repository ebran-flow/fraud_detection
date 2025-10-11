#!/bin/bash

# Startup script for Airtel Fraud Detection System
# This script checks dependencies and starts the FastAPI server

set -e

echo "=€ Starting Airtel Fraud Detection System..."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if .env exists
if [ ! -f .env ]; then
    echo "L Error: .env file not found!"
    echo "Please create backend/.env with your database credentials."
    echo ""
    echo "Example:"
    echo "  DB_HOST=localhost"
    echo "  DB_PORT=3307"
    echo "  DB_USER=root"
    echo "  DB_PASSWORD=your_password"
    echo "  DB_NAME=fraud_detection"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "L Error: Virtual environment not found!"
    echo "Please run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "=æ Activating virtual environment..."
source venv/bin/activate

# Check if FastAPI is installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "L Error: FastAPI not installed!"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

# Check database connection
echo "= Checking database connection..."
python3 << 'EOF'
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database credentials
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3307')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

# Try to connect
try:
    from sqlalchemy import create_engine, text

    connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(" Database connection successful!")

except Exception as e:
    print(f"L Database connection failed: {e}")
    print("")
    print("Please check your .env file and ensure MySQL is running:")
    print(f"  mysql -h {DB_HOST} -P {DB_PORT} -u {DB_USER} -p {DB_NAME}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo " All checks passed!"
echo ""
echo "< Starting FastAPI server..."
echo "   URL: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
