#!/bin/bash
################################################################################
# QUICK SETUP SCRIPT
#
# This script sets up everything needed to run the autonomous trading system
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RUST ALGORITHMIC TRADING SYSTEM - SETUP                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Create directories
echo -e "${BLUE}[1/6]${NC} Creating directories..."
mkdir -p "$PROJECT_ROOT/logs/autonomous"
mkdir -p "$PROJECT_ROOT/data/backtest_results"
mkdir -p "$PROJECT_ROOT/data/simulation_results"
mkdir -p "$PROJECT_ROOT/data/live_trading"
echo -e "${GREEN}✓${NC} Directories created"
echo ""

# 2. Check Python
echo -e "${BLUE}[2/6]${NC} Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python3 not found. Please install Python 3.11+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
echo ""

# 3. Check Rust
echo -e "${BLUE}[3/6]${NC} Checking Rust..."
if ! command -v cargo &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Rust not found. Installing..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi
RUST_VERSION=$(rustc --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} Rust $RUST_VERSION found"
echo ""

# 4. Install Python dependencies (optional, for backtesting)
echo -e "${BLUE}[4/6]${NC} Checking Python dependencies..."
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo -e "${YELLOW}⚠${NC} Installing Python dependencies (this may take a few minutes)..."
    python3 -m pip install --user -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1 || true
    echo -e "${GREEN}✓${NC} Python dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} requirements.txt not found, skipping Python dependencies"
fi
echo ""

# 5. Check .env file
echo -e "${BLUE}[5/6]${NC} Checking .env file..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}⚠${NC} .env file not found. Creating template..."
    cat > "$PROJECT_ROOT/.env" << 'EOF'
# Alpaca API Credentials (Paper Trading)
# Get your keys from: https://alpaca.markets/

ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true
EOF
    echo -e "${YELLOW}⚠${NC} Please edit .env and add your Alpaca API credentials!"
    echo -e "${YELLOW}⚠${NC} Get free paper trading keys from: https://alpaca.markets/"
    echo ""
else
    # Check if credentials are set
    source "$PROJECT_ROOT/.env"
    if [ "${ALPACA_API_KEY:-}" = "your_api_key_here" ] || [ -z "${ALPACA_API_KEY:-}" ]; then
        echo -e "${RED}✗${NC} .env file exists but ALPACA_API_KEY not set"
        echo -e "${YELLOW}⚠${NC} Please edit .env and add your Alpaca API credentials"
        echo ""
    else
        echo -e "${GREEN}✓${NC} .env file configured"
        echo ""
    fi
fi

# 6. Build Rust services
echo -e "${BLUE}[6/6]${NC} Building Rust services (this may take a few minutes)..."
cd "$PROJECT_ROOT/rust"
if cargo build --release --workspace 2>&1 | grep -q "Finished"; then
    echo -e "${GREEN}✓${NC} Rust services built successfully"
else
    echo -e "${YELLOW}⚠${NC} Rust build encountered some issues, but may still work"
fi
cd "$PROJECT_ROOT"
echo ""

# Summary
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  SETUP COMPLETE!                                              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Edit .env file with your Alpaca credentials (if not done)"
echo "   ${YELLOW}nano .env${NC}"
echo ""
echo "2. Start the autonomous trading system:"
echo "   ${YELLOW}./scripts/start_trading.sh${NC}"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "   - Quick Start: QUICK_START.md"
echo "   - Full Guide: docs/AUTONOMOUS_SYSTEM_GUIDE.md"
echo ""
