#!/bin/bash
# Stop all trading system services

echo "Stopping trading system services..."

# Find and kill processes
pkill -f "market-data" && echo "✓ Stopped Market Data Service" || true
pkill -f "risk-manager" && echo "✓ Stopped Risk Manager" || true
pkill -f "execution-engine" && echo "✓ Stopped Execution Engine" || true
pkill -f "signal-bridge" && echo "✓ Stopped Signal Bridge" || true

echo ""
echo "✅ All services stopped"
