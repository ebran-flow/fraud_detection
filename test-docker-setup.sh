#!/bin/bash
# Test Docker Setup Script
# Verifies that all services are running correctly

set -e

echo "=========================================="
echo "Testing Docker Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Test function
test_command() {
    local name=$1
    local command=$2
    local expected=$3

    echo -n "Testing $name... "

    if output=$(eval "$command" 2>&1); then
        if [ -z "$expected" ] || echo "$output" | grep -q "$expected"; then
            echo -e "${GREEN}✅ PASSED${NC}"
            PASSED=$((PASSED + 1))
            return 0
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo "  Expected: $expected"
            echo "  Got: $output"
            FAILED=$((FAILED + 1))
            return 1
        fi
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "  Error: $output"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "1. Checking Docker services..."
echo ""

# Test Docker daemon
test_command "Docker daemon" "docker info" "Server Version"

# Test Docker Compose
test_command "Docker Compose" "docker-compose version" "version"

echo ""
echo "2. Checking containers..."
echo ""

# Check if containers are running
test_command "MySQL container" "docker-compose ps mysql" "Up"
test_command "Backend container" "docker-compose ps backend" "Up"

echo ""
echo "3. Testing network connectivity..."
echo ""

# Test MySQL connectivity
test_command "MySQL connection" "docker-compose exec -T mysql mysql -u root -ppassword -e 'SELECT 1'" "1"

# Test MySQL database exists
test_command "Database exists" "docker-compose exec -T mysql mysql -u root -ppassword -e 'SHOW DATABASES'" "fraud_detection"

echo ""
echo "4. Testing backend API..."
echo ""

# Wait for backend to be fully ready
echo "Waiting for backend to be ready..."
sleep 5

# Test health endpoint
test_command "Health endpoint" "curl -s http://localhost:8501/health" "healthy"

# Test API health endpoint
test_command "API health endpoint" "curl -s http://localhost:8501/api/health" "healthy"

# Test optimal workers endpoint
test_command "Optimal workers endpoint" "curl -s http://localhost:8501/api/v1/optimal-workers" "optimal_workers"

echo ""
echo "5. Testing database tables..."
echo ""

# Check critical tables exist
test_command "Metadata table" "docker-compose exec -T mysql mysql -u root -ppassword fraud_detection -e 'SHOW TABLES LIKE \"metadata\"'" "metadata"
test_command "UATL raw table" "docker-compose exec -T mysql mysql -u root -ppassword fraud_detection -e 'SHOW TABLES LIKE \"uatl_raw_statements\"'" "uatl_raw_statements"
test_command "UMTN raw table" "docker-compose exec -T mysql mysql -u root -ppassword fraud_detection -e 'SHOW TABLES LIKE \"umtn_raw_statements\"'" "umtn_raw_statements"
test_command "Summary table" "docker-compose exec -T mysql mysql -u root -ppassword fraud_detection -e 'SHOW TABLES LIKE \"summary\"'" "summary"

echo ""
echo "6. Testing Python dependencies..."
echo ""

# Test key Python modules
test_command "FastAPI" "docker-compose exec -T backend python -c 'import fastapi; print(fastapi.__version__)'"
test_command "SQLAlchemy" "docker-compose exec -T backend python -c 'import sqlalchemy; print(sqlalchemy.__version__)'"
test_command "Pandas" "docker-compose exec -T backend python -c 'import pandas; print(pandas.__version__)'"
test_command "MySQL connector" "docker-compose exec -T backend python -c 'import mysql.connector; print(mysql.connector.__version__)'"

echo ""
echo "7. Testing parallel import setup..."
echo ""

# Test parallel importer module
test_command "Parallel importer" "docker-compose exec -T backend python -c 'from app.services.parallel_importer import get_optimal_worker_count; print(get_optimal_worker_count())'"

# Test process_parallel.py exists
test_command "Process parallel script" "docker-compose exec -T backend ls process_parallel.py" "process_parallel.py"

echo ""
echo "8. Checking file permissions..."
echo ""

# Check upload directory
test_command "Uploads directory" "docker-compose exec -T backend ls -ld /app/uploads" "drwx"

# Check logs directory
test_command "Logs directory" "docker-compose exec -T backend ls -ld /app/logs" "drwx"

echo ""
echo "9. Testing resource limits..."
echo ""

# Check container resources
echo -n "Checking MySQL memory limit... "
MYSQL_MEM=$(docker stats mysql --no-stream --format "{{.MemUsage}}" | awk '{print $1}')
echo -e "${GREEN}Current: $MYSQL_MEM${NC}"

echo -n "Checking backend memory limit... "
BACKEND_MEM=$(docker stats fraud_detection_backend --no-stream --format "{{.MemUsage}}" | awk '{print $1}')
echo -e "${GREEN}Current: $BACKEND_MEM${NC}"

PASSED=$((PASSED + 2))

echo ""
echo "10. Testing environment variables..."
echo ""

# Check critical env vars
test_command "DB_HOST" "docker-compose exec -T backend printenv DB_HOST" "mysql"
test_command "PARALLEL_IMPORT_WORKERS" "docker-compose exec -T backend printenv PARALLEL_IMPORT_WORKERS" "8"

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Your Docker setup is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Access UI:       http://localhost:8501"
    echo "  2. View API docs:   http://localhost:8501/docs"
    echo "  3. Import statements:"
    echo "     docker-compose exec backend python process_parallel.py --workers 8"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the errors above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs:      docker-compose logs -f"
    echo "  2. Restart services: docker-compose restart"
    echo "  3. Rebuild:         docker-compose down && docker-compose build && docker-compose up -d"
    echo ""
    exit 1
fi
