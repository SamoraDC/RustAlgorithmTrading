#!/bin/bash
################################################################################
# SIMPLE START SCRIPT - ONE COMMAND TO RULE THEM ALL
#
# This script starts the entire autonomous trading system with one command.
# It handles everything automatically:
# - Environment setup
# - Backtesting
# - Validation
# - Paper trading
#
# Usage: ./scripts/start_trading.sh
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   RUST ALGORITHMIC TRADING SYSTEM                            ║
║   Autonomous Trading Pipeline                                 ║
║                                                               ║
║   🤖 Backtesting → Simulation → Paper Trading                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
echo -e "${GREEN}Starting autonomous trading system...${NC}"
echo ""

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/../.env" ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "Please create .env file with your Alpaca credentials:"
    echo ""
    echo "ALPACA_API_KEY=your_api_key_here"
    echo "ALPACA_SECRET_KEY=your_secret_key_here"
    echo "ALPACA_PAPER=true"
    echo ""
    exit 1
fi

# Run the autonomous system in full mode
exec "$SCRIPT_DIR/autonomous_trading_system.sh" --mode=full
