#!/bin/bash
# Startup script for Airtel Fraud Detection System

set -e

echo "🚀 Starting Airtel Fraud Detection System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your database credentials before running again."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check database connection
echo "🔍 Checking database connection..."
python -c "
from backend.app.services.db import engine
try:
    with engine.connect() as conn:
        print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    print('Please check your database configuration in .env')
    exit(1)
"

# Start the application
echo "🌐 Starting FastAPI server..."
echo "📍 Application will be available at: http://localhost:8000"
echo "📖 API documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
