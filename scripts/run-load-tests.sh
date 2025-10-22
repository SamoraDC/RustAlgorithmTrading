#!/bin/bash
# Run All Load Tests
# Executes comprehensive load testing suite against staging environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Load Testing Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if staging environment is running
echo -e "${YELLOW}Checking staging environment...${NC}"

if ! docker-compose -f "${DOCKER_DIR}/docker-compose.staging.yml" ps | grep -q "Up"; then
    echo -e "${RED}Error: Staging environment is not running${NC}"
    echo -e "${YELLOW}Start it with: ./scripts/deploy-staging.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Staging environment is running${NC}"
echo ""

# Get load tester container
LOAD_TESTER=$(docker-compose -f "${DOCKER_DIR}/docker-compose.staging.yml" ps -q load-tester)

if [ -z "$LOAD_TESTER" ]; then
    echo -e "${RED}Error: Load tester container not found${NC}"
    exit 1
fi

# Clear previous results
echo -e "${YELLOW}Clearing previous test results...${NC}"
rm -rf "${DOCKER_DIR}/load-test-results"/*
mkdir -p "${DOCKER_DIR}/load-test-results"
echo -e "${GREEN}✓ Results directory cleared${NC}"
echo ""

# Function to run a test
run_test() {
    local test_name=$1
    local test_script=$2
    local duration=${3:-300}

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Running: ${test_name}${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Duration: ${duration} seconds${NC}"
    echo -e "${YELLOW}Start time: $(date)${NC}"
    echo ""

    # Run the test
    docker exec -e LOAD_TEST_DURATION=${duration} "${LOAD_TESTER}" python "/tests/${test_script}"

    local exit_code=$?

    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ ${test_name} completed${NC}"
    else
        echo -e "${RED}✗ ${test_name} failed (exit code: ${exit_code})${NC}"
    fi
    echo ""

    return $exit_code
}

# Track test results
declare -a test_results
declare -a test_names

# Test 1: Market Data Flood Test
echo ""
test_names+=("Market Data Flood Test")
if run_test "Market Data Flood Test" "market_data_flood_test.py" 300; then
    test_results+=("PASS")
else
    test_results+=("FAIL")
fi

# Wait between tests
echo -e "${YELLOW}Waiting 30 seconds before next test...${NC}"
sleep 30

# Test 2: Order Stress Test
echo ""
test_names+=("Order Stress Test")
if run_test "Order Stress Test" "order_stress_test.py" 300; then
    test_results+=("PASS")
else
    test_results+=("FAIL")
fi

# Wait between tests
echo -e "${YELLOW}Waiting 30 seconds before next test...${NC}"
sleep 30

# Test 3: Database Throughput Test
echo ""
test_names+=("Database Throughput Test")
if run_test "Database Throughput Test" "database_throughput_test.py" 300; then
    test_results+=("PASS")
else
    test_results+=("FAIL")
fi

# Wait between tests
echo -e "${YELLOW}Waiting 30 seconds before next test...${NC}"
sleep 30

# Test 4: WebSocket Concurrency Test
echo ""
test_names+=("WebSocket Concurrency Test")
if run_test "WebSocket Concurrency Test" "websocket_concurrency_test.py" 300; then
    test_results+=("PASS")
else
    test_results+=("FAIL")
fi

# Print summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Load Testing Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

pass_count=0
fail_count=0

for i in "${!test_names[@]}"; do
    test_name="${test_names[$i]}"
    result="${test_results[$i]}"

    if [ "$result" = "PASS" ]; then
        echo -e "  ${GREEN}✓${NC} ${test_name}: ${GREEN}PASS${NC}"
        pass_count=$((pass_count + 1))
    else
        echo -e "  ${RED}✗${NC} ${test_name}: ${RED}FAIL${NC}"
        fail_count=$((fail_count + 1))
    fi
done

echo ""
echo -e "${BLUE}Results:${NC}"
echo -e "  Passed: ${GREEN}${pass_count}${NC}"
echo -e "  Failed: ${RED}${fail_count}${NC}"
echo -e "  Total:  $((pass_count + fail_count))"
echo ""

# Copy results from container
echo -e "${YELLOW}Copying test results...${NC}"
docker cp "${LOAD_TESTER}:/results/" "${DOCKER_DIR}/load-test-results/" 2>/dev/null || true
echo -e "${GREEN}✓ Results copied to ${DOCKER_DIR}/load-test-results/${NC}"
echo ""

# Generate combined report
REPORT_FILE="${DOCKER_DIR}/load-test-results/summary.txt"
echo "Load Testing Summary Report" > "${REPORT_FILE}"
echo "Generated: $(date)" >> "${REPORT_FILE}"
echo "========================================" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

for i in "${!test_names[@]}"; do
    echo "${test_names[$i]}: ${test_results[$i]}" >> "${REPORT_FILE}"
done

echo "" >> "${REPORT_FILE}"
echo "Passed: ${pass_count}" >> "${REPORT_FILE}"
echo "Failed: ${fail_count}" >> "${REPORT_FILE}"
echo "Total:  $((pass_count + fail_count))" >> "${REPORT_FILE}"

echo -e "${BLUE}Detailed Results:${NC}"
echo -e "  Summary:    ${DOCKER_DIR}/load-test-results/summary.txt"
echo -e "  Individual: ${DOCKER_DIR}/load-test-results/*.json"
echo ""

# Overall status
if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ALL TESTS PASSED ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ${fail_count} TEST(S) FAILED ✗${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
