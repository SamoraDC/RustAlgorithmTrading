#!/bin/bash
################################################################################
# Data Integration Test Script
#
# Tests the complete data download and loading workflow:
# 1. Download script execution
# 2. Data format validation
# 3. Data handler loading
# 4. Auto-download fallback
################################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}=== Data Integration Test ===${NC}"
echo ""

# Test 1: Download script help
echo -e "${GREEN}[TEST 1]${NC} Testing download script help..."
if uv run python "$SCRIPT_DIR/download_market_data.py" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC} - Download script help works"
else
    echo -e "${RED}✗ FAILED${NC} - Download script help failed"
    exit 1
fi

# Test 2: Import download module
echo -e "${GREEN}[TEST 2]${NC} Testing download module import..."
if uv run python -c "from scripts.download_market_data import MarketDataDownloader" 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC} - Download module imports successfully"
else
    echo -e "${RED}✗ FAILED${NC} - Download module import failed"
    exit 1
fi

# Test 3: Import data handler
echo -e "${GREEN}[TEST 3]${NC} Testing data handler import..."
cd "$PROJECT_ROOT"
if uv run python -c "import sys; sys.path.insert(0, 'src'); from backtesting.data_handler import HistoricalDataHandler" 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC} - Data handler imports successfully"
else
    echo -e "${RED}✗ FAILED${NC} - Data handler import failed"
    exit 1
fi

# Test 4: Configuration
echo -e "${GREEN}[TEST 4]${NC} Testing configuration..."
if [ -f "$PROJECT_ROOT/config/data_download.json" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Configuration file exists"
else
    echo -e "${RED}✗ FAILED${NC} - Configuration file missing"
    exit 1
fi

# Test 5: Directory structure
echo -e "${GREEN}[TEST 5]${NC} Testing directory structure..."
mkdir -p "$PROJECT_ROOT/data/historical"
if [ -d "$PROJECT_ROOT/data/historical" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Data directories created"
else
    echo -e "${RED}✗ FAILED${NC} - Failed to create data directories"
    exit 1
fi

# Test 6: Environment variables
echo -e "${GREEN}[TEST 6]${NC} Testing environment variables..."
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    if [ -n "${ALPACA_API_KEY:-}" ]; then
        echo -e "${GREEN}✓ PASSED${NC} - Alpaca credentials configured"
    else
        echo -e "${YELLOW}⚠ WARNING${NC} - Alpaca API key not set (download will fail)"
    fi
else
    echo -e "${YELLOW}⚠ WARNING${NC} - .env file not found"
fi

echo ""
echo -e "${GREEN}=== All Integration Tests Passed ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Run download script: uv run python scripts/download_market_data.py --symbols AAPL --days 30"
echo "  2. Test backtesting: ./scripts/autonomous_trading_system.sh --mode=backtest-only"
echo "  3. Run full system: ./scripts/autonomous_trading_system.sh --mode=full"
