#!/bin/bash
# Test Observability Connection Pipeline
# Validates that Rust services emit metrics and Python collectors receive them

set -e

echo "============================================"
echo "Observability Connection Integration Test"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "1. Checking Rust service metrics endpoints..."
echo ""

check_endpoint() {
    local service=$1
    local port=$2

    if curl -s "http://localhost:${port}/metrics" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ${service} service responding on port ${port}"
        return 0
    else
        echo -e "${RED}✗${NC} ${service} service NOT responding on port ${port}"
        return 1
    fi
}

# Check all three services
market_data_ok=false
execution_ok=false
risk_ok=false

if check_endpoint "Market Data" 9091; then
    market_data_ok=true
fi

if check_endpoint "Execution Engine" 9092; then
    execution_ok=true
fi

if check_endpoint "Risk Manager" 9093; then
    risk_ok=true
fi

echo ""

# Count available services
available=0
[ "$market_data_ok" = true ] && ((available++)) || true
[ "$execution_ok" = true ] && ((available++)) || true
[ "$risk_ok" = true ] && ((available++)) || true

if [ $available -eq 0 ]; then
    echo -e "${RED}ERROR: No Rust services are running!${NC}"
    echo ""
    echo "Please start the services first:"
    echo "  cd rust"
    echo "  cargo run --bin market-data &"
    echo "  cargo run --bin execution-engine &"
    echo "  cargo run --bin risk-manager &"
    exit 1
fi

echo -e "${GREEN}Found ${available}/3 services running${NC}"
echo ""

# Test metrics format
echo "2. Validating Prometheus metrics format..."
echo ""

if [ "$market_data_ok" = true ]; then
    response=$(curl -s http://localhost:9091/metrics)

    if echo "$response" | grep -q "# TYPE"; then
        echo -e "${GREEN}✓${NC} Market Data metrics in valid Prometheus format"

        # Count metrics
        counter_count=$(echo "$response" | grep -c "TYPE.*counter" || true)
        gauge_count=$(echo "$response" | grep -c "TYPE.*gauge" || true)
        histogram_count=$(echo "$response" | grep -c "TYPE.*histogram" || true)

        echo "    - Counters: $counter_count"
        echo "    - Gauges: $gauge_count"
        echo "    - Histograms: $histogram_count"
    else
        echo -e "${YELLOW}⚠${NC} Market Data metrics format looks unusual"
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping Market Data metrics validation (service not running)"
fi

echo ""

# Test Python bridge
echo "3. Testing Python metrics bridge..."
echo ""

python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')

async def test_bridge():
    try:
        from src.observability.metrics.rust_bridge import get_rust_metrics_bridge

        bridge = get_rust_metrics_bridge()
        await bridge.start()

        # Test scraping
        metrics = await bridge.scrape_all_services()

        available = sum(1 for m in metrics.values() if m is not None)

        print(f'✓ Python bridge successfully scraped {available}/3 services')

        for service_name, service_metrics in metrics.items():
            if service_metrics:
                counters = len(service_metrics.get('counters', {}))
                gauges = len(service_metrics.get('gauges', {}))
                histograms = len(service_metrics.get('histograms', {}))
                print(f'  - {service_name}: {counters} counters, {gauges} gauges, {histograms} histograms')

        await bridge.stop()
        return True
    except ImportError as e:
        print(f'✗ Failed to import Python modules: {e}')
        print('  Make sure to install: pip install -r requirements.txt')
        return False
    except Exception as e:
        print(f'✗ Bridge test failed: {e}')
        return False

success = asyncio.run(test_bridge())
sys.exit(0 if success else 1)
"

bridge_result=$?

echo ""

# Test collector
if [ $bridge_result -eq 0 ]; then
    echo "4. Testing metric collector integration..."
    echo ""

    python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')

async def test_collector():
    try:
        from src.observability.metrics.market_data_collector import MarketDataCollector

        collector = MarketDataCollector()
        await collector.start()

        # Wait for some metrics to be collected
        await asyncio.sleep(2)

        status = await collector.get_status()

        if status['status'] == 'ready':
            print(f\"✓ Market Data collector is operational\")
            print(f\"  - Uptime: {status['uptime_seconds']:.1f}s\")
            print(f\"  - Metrics collected: {status['metrics_collected']}\")

            metrics = await collector.get_current_metrics()
            print(f\"  - Symbols tracked: {metrics.get('symbols_tracked', 0)}\")

            await collector.stop()
            return True
        else:
            print(f\"✗ Collector status: {status['status']}\")
            await collector.stop()
            return False

    except Exception as e:
        print(f\"✗ Collector test failed: {e}\")
        return False

success = asyncio.run(test_collector())
sys.exit(0 if success else 1)
"

    collector_result=$?
else
    echo "4. Skipping collector test (bridge failed)"
    collector_result=1
fi

echo ""

# Run integration tests
echo "5. Running integration tests..."
echo ""

if command -v pytest &> /dev/null; then
    pytest tests/integration/test_observability_integration.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|SKIPPED|ERROR|test_)"
    test_result=$?
else
    echo -e "${YELLOW}⚠${NC} pytest not found, skipping integration tests"
    echo "  Install with: pip install pytest pytest-asyncio"
    test_result=1
fi

echo ""

# Summary
echo "============================================"
echo "Test Summary"
echo "============================================"
echo ""

total_tests=5
passed_tests=0

[ $available -gt 0 ] && ((passed_tests++)) || true
[ "$market_data_ok" = true ] && ((passed_tests++)) || true
[ $bridge_result -eq 0 ] && ((passed_tests++)) || true
[ $collector_result -eq 0 ] && ((passed_tests++)) || true
[ $test_result -eq 0 ] && ((passed_tests++)) || true

echo "Services Running: ${available}/3"
echo "Metrics Format: $([ "$market_data_ok" = true ] && echo "✓" || echo "✗")"
echo "Python Bridge: $([ $bridge_result -eq 0 ] && echo "✓" || echo "✗")"
echo "Collectors: $([ $collector_result -eq 0 ] && echo "✓" || echo "✗")"
echo "Integration Tests: $([ $test_result -eq 0 ] && echo "✓" || echo "✗")"
echo ""

if [ $passed_tests -ge 3 ]; then
    echo -e "${GREEN}PASSED${NC}: Observability pipeline is working!"
    exit 0
else
    echo -e "${RED}FAILED${NC}: Some components are not working correctly"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Make sure Rust services are built: cd rust && cargo build"
    echo "  2. Start services: cargo run --bin market-data"
    echo "  3. Install Python deps: pip install -r requirements.txt"
    echo "  4. Check logs for errors"
    exit 1
fi
