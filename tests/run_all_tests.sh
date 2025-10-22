#!/bin/bash
################################################################################
# Comprehensive Test Suite Runner
#
# Runs all test categories and generates comprehensive report
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/tests/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create report directory
mkdir -p "$REPORT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}COMPREHENSIVE TEST SUITE${NC}"
echo -e "${BLUE}========================================${NC}"

# Test results tracking
UNIT_TESTS_PASSED=0
INTEGRATION_TESTS_PASSED=0
EDGE_CASE_TESTS_PASSED=0
PERFORMANCE_TESTS_PASSED=0

# Run unit tests
echo -e "\n${YELLOW}Running Unit Tests...${NC}"
if uv run pytest "$SCRIPT_DIR/unit/" -v --tb=short --junitxml="$REPORT_DIR/unit_tests_$TIMESTAMP.xml" 2>&1 | tee "$REPORT_DIR/unit_tests_$TIMESTAMP.log"; then
    echo -e "${GREEN}✓ Unit Tests PASSED${NC}"
    UNIT_TESTS_PASSED=1
else
    echo -e "${RED}✗ Unit Tests FAILED${NC}"
fi

# Run integration tests
echo -e "\n${YELLOW}Running Integration Tests...${NC}"
if uv run pytest "$SCRIPT_DIR/integration/" -v --tb=short --junitxml="$REPORT_DIR/integration_tests_$TIMESTAMP.xml" 2>&1 | tee "$REPORT_DIR/integration_tests_$TIMESTAMP.log"; then
    echo -e "${GREEN}✓ Integration Tests PASSED${NC}"
    INTEGRATION_TESTS_PASSED=1
else
    echo -e "${RED}✗ Integration Tests FAILED${NC}"
fi

# Run edge case tests
echo -e "\n${YELLOW}Running Edge Case Tests...${NC}"
if uv run pytest "$SCRIPT_DIR/edge_cases/" -v --tb=short --junitxml="$REPORT_DIR/edge_case_tests_$TIMESTAMP.xml" 2>&1 | tee "$REPORT_DIR/edge_case_tests_$TIMESTAMP.log"; then
    echo -e "${GREEN}✓ Edge Case Tests PASSED${NC}"
    EDGE_CASE_TESTS_PASSED=1
else
    echo -e "${RED}✗ Edge Case Tests FAILED${NC}"
fi

# Run performance tests
echo -e "\n${YELLOW}Running Performance Tests...${NC}"
if uv run pytest "$SCRIPT_DIR/performance/" -v -s --tb=short --junitxml="$REPORT_DIR/performance_tests_$TIMESTAMP.xml" 2>&1 | tee "$REPORT_DIR/performance_tests_$TIMESTAMP.log"; then
    echo -e "${GREEN}✓ Performance Tests PASSED${NC}"
    PERFORMANCE_TESTS_PASSED=1
else
    echo -e "${RED}✗ Performance Tests FAILED${NC}"
fi

# Generate summary report
SUMMARY_FILE="$REPORT_DIR/summary_$TIMESTAMP.txt"

cat > "$SUMMARY_FILE" <<EOF
================================================================================
TEST EXECUTION SUMMARY
================================================================================
Timestamp: $(date '+%Y-%m-%d %H:%M:%S')

Test Results:
  Unit Tests:        $([ $UNIT_TESTS_PASSED -eq 1 ] && echo "PASSED ✓" || echo "FAILED ✗")
  Integration Tests: $([ $INTEGRATION_TESTS_PASSED -eq 1 ] && echo "PASSED ✓" || echo "FAILED ✗")
  Edge Case Tests:   $([ $EDGE_CASE_TESTS_PASSED -eq 1 ] && echo "PASSED ✓" || echo "FAILED ✗")
  Performance Tests: $([ $PERFORMANCE_TESTS_PASSED -eq 1 ] && echo "PASSED ✓" || echo "FAILED ✗")

Overall Status: $([ $((UNIT_TESTS_PASSED + INTEGRATION_TESTS_PASSED + EDGE_CASE_TESTS_PASSED + PERFORMANCE_TESTS_PASSED)) -eq 4 ] && echo "ALL PASSED ✓" || echo "SOME FAILED ✗")

Report Location: $REPORT_DIR

Test Logs:
  - Unit Tests:        $REPORT_DIR/unit_tests_$TIMESTAMP.log
  - Integration Tests: $REPORT_DIR/integration_tests_$TIMESTAMP.log
  - Edge Cases:        $REPORT_DIR/edge_case_tests_$TIMESTAMP.log
  - Performance:       $REPORT_DIR/performance_tests_$TIMESTAMP.log

================================================================================
EOF

# Display summary
cat "$SUMMARY_FILE"

# Exit with appropriate code
TOTAL_PASSED=$((UNIT_TESTS_PASSED + INTEGRATION_TESTS_PASSED + EDGE_CASE_TESTS_PASSED + PERFORMANCE_TESTS_PASSED))

if [ $TOTAL_PASSED -eq 4 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}ALL TESTS PASSED ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}SOME TESTS FAILED ✗${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
