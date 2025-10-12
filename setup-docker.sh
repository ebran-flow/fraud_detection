#!/bin/bash
# Docker Setup Script for Fraud Detection System
# Optimized for i5-12400 (12 threads) + 32GB RAM

set -e

echo "=========================================="
echo "Fraud Detection Docker Setup"
echo "System: i5-12400 + Ryzen 6700XT + 32GB RAM"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first:"
    echo "   https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Copy environment file
echo "📝 Setting up environment configuration..."
if [ ! -f backend/.env ]; then
    cp .env.docker backend/.env
    echo "✅ Created backend/.env from .env.docker"
else
    echo "⚠️  backend/.env already exists, skipping"
fi
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/uploads
mkdir -p backend/logs
mkdir -p docs/data/UATL/extracted
mkdir -p docs/data/UMTN/extracted
echo "✅ Directories created"
echo ""

# Check if init.sql exists
if [ ! -f backend/init.sql ]; then
    echo "⚠️  WARNING: backend/init.sql not found"
    echo "   The database will start without initial schema"
    echo "   You may need to run migrations manually"
    echo ""
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true
echo ""

# Build images
echo "🏗️  Building Docker images..."
docker-compose build
echo "✅ Images built successfully"
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
echo ""

# Wait for MySQL to be ready
echo "⏳ Waiting for MySQL to be ready..."
sleep 15

# Check service health
echo "🔍 Checking service health..."
echo ""

if docker-compose ps | grep -q "mysql.*Up"; then
    echo "✅ MySQL is running"
else
    echo "❌ MySQL failed to start"
    docker-compose logs mysql
    exit 1
fi

if docker-compose ps | grep -q "backend.*Up"; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start"
    docker-compose logs backend
    exit 1
fi

echo ""
echo "=========================================="
echo "🎉 Setup Complete!"
echo "=========================================="
echo ""
echo "Services:"
echo "  - MySQL:   http://localhost:3307"
echo "  - Backend: http://localhost:8501"
echo "  - UI:      http://localhost:8501"
echo ""
echo "Default credentials:"
echo "  - MySQL root password: password"
echo "  - MySQL user: fraud_user / fraud_pass"
echo ""
echo "Useful commands:"
echo "  - View logs:        docker-compose logs -f"
echo "  - Stop services:    docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Enter backend:    docker-compose exec backend bash"
echo "  - Enter MySQL:      docker-compose exec mysql mysql -u root -ppassword fraud_detection"
echo ""
echo "To import statements in parallel:"
echo "  1. Place files in docs/data/UATL/extracted/ or docs/data/UMTN/extracted/"
echo "  2. Use the parallel import API endpoint or run:"
echo "     docker-compose exec backend python process_parallel.py --workers 8"
echo ""
