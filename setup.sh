#!/bin/bash
# Setup script for Airtel Fraud Detection System

set -e

echo "🔧 Setting up Airtel Fraud Detection System..."

# Check Python version
echo "🐍 Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
echo "📥 Installing backend dependencies..."
pip install -r backend/requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your database credentials"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploaded_pdfs
mkdir -p results
mkdir -p detailed_sheets
mkdir -p batch_results
mkdir -p statements

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Run the SQL schema: mysql -u root -p -P 3307 < backend/schema.sql"
echo "3. Start the application: ./start.sh"
echo ""
