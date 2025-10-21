#!/bin/bash
# Check health status of all services

echo "=== Trading System Health Check ==="
echo ""

# Check if services are running
check_process() {
    local name=$1
    if pgrep -f "$name" > /dev/null; then
        echo "✓ $name is running (PID: $(pgrep -f $name))"
        return 0
    else
        echo "✗ $name is NOT running"
        return 1
    fi
}

echo "Service Status:"
check_process "market-data"
check_process "risk-manager"
check_process "execution-engine"
check_process "signal-bridge"

echo ""
echo "Configuration:"
if [ -f "config/system.json" ]; then
    ENV=$(jq -r '.metadata.environment' config/system.json)
    PAPER=$(jq -r '.execution.paper_trading' config/system.json)
    echo "  Environment: $ENV"
    echo "  Paper Trading: $PAPER"
else
    echo "  ERROR: config/system.json not found"
fi

echo ""
echo "Environment Variables:"
echo "  ALPACA_API_KEY: ${ALPACA_API_KEY:0:10}..."
echo "  ALPACA_SECRET_KEY: ${ALPACA_SECRET_KEY:0:10}..."
echo "  ALPACA_BASE_URL: $ALPACA_BASE_URL"

echo ""
echo "Recent Logs:"
if [ -f "logs/market-data.log" ]; then
    echo "  Market Data (last 3 lines):"
    tail -3 logs/market-data.log | sed 's/^/    /'
fi

if [ -f "logs/risk-manager.log" ]; then
    echo "  Risk Manager (last 3 lines):"
    tail -3 logs/risk-manager.log | sed 's/^/    /'
fi
