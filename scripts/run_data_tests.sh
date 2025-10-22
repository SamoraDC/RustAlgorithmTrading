#!/bin/bash

# Test runner script for data downloader validation
# Runs comprehensive test suite with coverage reporting

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Data Downloader Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Install with: pip install pytest pytest-cov pytest-mock"
    exit 1
fi

# Check if required dependencies are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
python -c "import pandas, numpy, alpaca" 2>/dev/null || {
    echo -e "${RED}Error: Required dependencies not found${NC}"
    echo "Install with: pip install -r requirements.txt"
    exit 1
}

echo -e "${GREEN}✓ Dependencies OK${NC}"
echo ""

# Run tests with different options based on arguments
case "${1:-all}" in
    "unit")
        echo "Running unit tests only..."
        pytest tests/test_data_downloader.py::TestAlpacaClient \
               tests/test_data_downloader.py::TestDataFetcher \
               tests/test_data_downloader.py::TestDataLoader \
               tests/test_data_downloader.py::TestDataValidation \
               -v --tb=short
        ;;

    "integration")
        echo "Running integration tests only..."
        pytest tests/test_data_downloader.py::TestIntegration \
               -v --tb=short
        ;;

    "performance")
        echo "Running performance tests only..."
        pytest tests/test_data_downloader.py::TestPerformance \
               -v --tb=short
        ;;

    "coverage")
        echo "Running all tests with coverage..."
        pytest tests/test_data_downloader.py \
               --cov=src.api.alpaca_client \
               --cov=src.data.fetcher \
               --cov=src.data.loader \
               --cov=src.backtesting.data_handler \
               --cov-report=html \
               --cov-report=term-missing \
               -v

        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    "quick")
        echo "Running quick smoke tests..."
        pytest tests/test_data_downloader.py \
               -v -x --tb=line \
               -k "test_client_initialization or test_save_and_load"
        ;;

    "all"|*)
        echo "Running all tests..."
        pytest tests/test_data_downloader.py -v --tb=short
        ;;
esac

EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi
echo "=========================================="

exit $EXIT_CODE
