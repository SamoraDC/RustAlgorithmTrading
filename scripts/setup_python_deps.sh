#!/bin/bash
################################################################################
# Python Dependencies Setup with UV
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Installing Python dependencies with uv...${NC}"
echo ""

cd "$PROJECT_ROOT"

# Core packages
echo -e "${BLUE}[1/3]${NC} Installing core data science packages..."
uv add numpy pandas scipy matplotlib seaborn

# Trading packages
echo -e "${BLUE}[2/3]${NC} Installing trading packages..."
uv add alpaca-py loguru

# ML packages (optional)
echo -e "${BLUE}[3/3]${NC} Installing ML packages..."
uv add scikit-learn xgboost --optional

echo ""
echo -e "${GREEN}✓ All Python dependencies installed!${NC}"
echo ""
echo "You can now run:"
echo "  ${YELLOW}./scripts/start_trading.sh${NC}"
