#!/bin/bash
# Validate configuration files

set -e

echo "Validating configuration files..."

# Check if config files exist
if [ ! -f "config/system.json" ]; then
    echo "ERROR: config/system.json not found"
    exit 1
fi

if [ ! -f "config/risk_limits.toml" ]; then
    echo "ERROR: config/risk_limits.toml not found"
    exit 1
fi

# Validate JSON syntax
echo "✓ Checking system.json..."
jq empty config/system.json 2>/dev/null || {
    echo "ERROR: Invalid JSON in config/system.json"
    exit 1
}

echo "✓ Checking system.staging.json..."
jq empty config/system.staging.json 2>/dev/null || {
    echo "ERROR: Invalid JSON in config/system.staging.json"
    exit 1
}

echo "✓ Checking system.production.json..."
jq empty config/system.production.json 2>/dev/null || {
    echo "ERROR: Invalid JSON in config/system.production.json"
    exit 1
}

# Check environment variables
echo "✓ Checking environment variables..."
if [ -z "$ALPACA_API_KEY" ]; then
    echo "WARNING: ALPACA_API_KEY not set"
fi

if [ -z "$ALPACA_SECRET_KEY" ]; then
    echo "WARNING: ALPACA_SECRET_KEY not set"
fi

echo ""
echo "✅ Configuration validation complete!"
echo ""

# Display configuration summary
echo "=== Development Configuration ==="
jq '.metadata.environment, .execution.paper_trading, .risk' config/system.json
echo ""

echo "=== Staging Configuration ==="
jq '.metadata.environment, .execution.paper_trading, .risk' config/system.staging.json
echo ""

echo "=== Production Configuration ==="
jq '.metadata.environment, .execution.paper_trading, .risk' config/system.production.json
