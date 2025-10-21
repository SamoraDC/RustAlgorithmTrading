#!/bin/bash
# Start all trading system services

set -e

# Source environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check environment
ENVIRONMENT=${TRADING_ENV:-development}
echo "Starting services in $ENVIRONMENT mode..."

# Select configuration
CONFIG_FILE="config/system.json"
if [ "$ENVIRONMENT" = "staging" ]; then
    CONFIG_FILE="config/system.staging.json"
elif [ "$ENVIRONMENT" = "production" ]; then
    CONFIG_FILE="config/system.production.json"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file $CONFIG_FILE not found"
    exit 1
fi

echo "Using configuration: $CONFIG_FILE"

# Create symlink for active config
ln -sf $(basename $CONFIG_FILE) config/system.json

# Build services
echo "Building services..."
cd rust
cargo build --release

# Start services in background
echo ""
echo "Starting Market Data Service..."
RUST_LOG=info ./target/release/market-data > logs/market-data.log 2>&1 &
MARKET_DATA_PID=$!
echo "  PID: $MARKET_DATA_PID"

sleep 2

echo "Starting Risk Manager..."
RUST_LOG=info ./target/release/risk-manager > logs/risk-manager.log 2>&1 &
RISK_MANAGER_PID=$!
echo "  PID: $RISK_MANAGER_PID"

sleep 2

echo "Starting Execution Engine..."
RUST_LOG=info ./target/release/execution-engine > logs/execution-engine.log 2>&1 &
EXECUTION_PID=$!
echo "  PID: $EXECUTION_PID"

sleep 2

echo "Starting Signal Bridge..."
RUST_LOG=info ./target/release/signal-bridge > logs/signal-bridge.log 2>&1 &
SIGNAL_BRIDGE_PID=$!
echo "  PID: $SIGNAL_BRIDGE_PID"

echo ""
echo "✅ All services started!"
echo ""
echo "PIDs:"
echo "  Market Data: $MARKET_DATA_PID"
echo "  Risk Manager: $RISK_MANAGER_PID"
echo "  Execution Engine: $EXECUTION_PID"
echo "  Signal Bridge: $SIGNAL_BRIDGE_PID"
echo ""
echo "Logs available in logs/"
echo ""
echo "To stop services, run: ./scripts/stop_services.sh"
