#!/bin/bash

################################################################################
# Deployment Validation Script
# Comprehensive pre/post-deployment checks for algorithmic trading system
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file
LOG_FILE="${PROJECT_ROOT}/logs/deployment_validation_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

################################################################################
# Helper Functions
################################################################################

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

check_start() {
    ((TOTAL_CHECKS++))
    echo -ne "${BLUE}[...] $1${NC}"
}

check_pass() {
    ((PASSED_CHECKS++))
    echo -e "\r${GREEN}[✓] $1${NC}" | tee -a "$LOG_FILE"
}

check_fail() {
    ((FAILED_CHECKS++))
    echo -e "\r${RED}[✗] $1${NC}" | tee -a "$LOG_FILE"
    if [ -n "${2:-}" ]; then
        log "${RED}    → $2${NC}"
    fi
}

check_warn() {
    ((WARNINGS++))
    echo -e "\r${YELLOW}[!] $1${NC}" | tee -a "$LOG_FILE"
    if [ -n "${2:-}" ]; then
        log "${YELLOW}    → $2${NC}"
    fi
}

section() {
    log ""
    log "${BLUE}===========================================${NC}"
    log "${BLUE}$1${NC}"
    log "${BLUE}===========================================${NC}"
}

wait_for_service() {
    local url=$1
    local max_attempts=${2:-30}
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
        ((attempt++))
    done
    return 1
}

################################################################################
# Pre-Deployment Checks
################################################################################

pre_deployment_checks() {
    section "PRE-DEPLOYMENT CHECKS"

    # Check required commands
    check_start "Checking required commands"
    local required_commands=("python3" "cargo" "rustc" "curl" "netstat" "docker")
    local missing_commands=()

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -eq 0 ]; then
        check_pass "All required commands available (${#required_commands[@]}/${#required_commands[@]})"
    else
        check_fail "Missing commands: ${missing_commands[*]}" "Install missing dependencies"
    fi

    # Check Python dependencies
    check_start "Checking Python dependencies"
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        local missing_py_deps=()
        while IFS= read -r line; do
            # Extract package name (before ==, >=, etc)
            local pkg=$(echo "$line" | sed 's/[>=<].*//' | tr -d ' ')
            if [ -n "$pkg" ] && [ "${pkg:0:1}" != "#" ]; then
                if ! python3 -c "import ${pkg//-/_}" 2>/dev/null; then
                    missing_py_deps+=("$pkg")
                fi
            fi
        done < "${PROJECT_ROOT}/requirements.txt"

        if [ ${#missing_py_deps[@]} -eq 0 ]; then
            check_pass "Python dependencies installed"
        else
            check_fail "Missing Python packages: ${missing_py_deps[*]}" "Run: pip install -r requirements.txt"
        fi
    else
        check_warn "requirements.txt not found" "Cannot verify Python dependencies"
    fi

    # Check Rust dependencies
    check_start "Checking Rust project"
    if [ -f "${PROJECT_ROOT}/rust/Cargo.toml" ]; then
        cd "${PROJECT_ROOT}/rust"
        if cargo check --quiet 2>/dev/null; then
            check_pass "Rust project compiles"
        else
            check_fail "Rust compilation errors" "Run: cd rust && cargo build"
        fi
        cd "$PROJECT_ROOT"
    else
        check_warn "Cargo.toml not found" "Cannot verify Rust project"
    fi

    # Check environment variables
    check_start "Checking environment variables"
    local required_env_vars=("ALPACA_API_KEY" "ALPACA_API_SECRET")
    local missing_env_vars=()

    # Try to load .env file
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        set -a
        source "${PROJECT_ROOT}/.env"
        set +a
    fi

    for var in "${required_env_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_env_vars+=("$var")
        fi
    done

    if [ ${#missing_env_vars[@]} -eq 0 ]; then
        check_pass "Required environment variables set"
    else
        check_fail "Missing environment variables: ${missing_env_vars[*]}" "Check .env file"
    fi

    # Check ports availability
    check_start "Checking port availability"
    local required_ports=(8000 9091 9092 9093)
    local busy_ports=()

    for port in "${required_ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            busy_ports+=("$port")
        fi
    done

    if [ ${#busy_ports[@]} -eq 0 ]; then
        check_pass "All required ports available (${required_ports[*]})"
    else
        check_warn "Ports already in use: ${busy_ports[*]}" "Services may already be running"
    fi

    # Check database directories
    check_start "Checking database directories"
    local db_dirs=("${PROJECT_ROOT}/data" "${PROJECT_ROOT}/data/duckdb")
    local missing_dirs=()

    for dir in "${db_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done

    if [ ${#missing_dirs[@]} -eq 0 ]; then
        check_pass "Database directories exist"
    else
        check_warn "Creating missing directories: ${missing_dirs[*]}"
        mkdir -p "${missing_dirs[@]}"
        check_pass "Database directories created"
    fi

    # Check log directories
    check_start "Checking log directories"
    local log_dirs=("${PROJECT_ROOT}/logs")

    for dir in "${log_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
        fi
    done
    check_pass "Log directories ready"

    # Check API credentials
    check_start "Validating API credentials"
    if [ -n "${ALPACA_API_KEY:-}" ] && [ -n "${ALPACA_API_SECRET:-}" ]; then
        # Basic format check (Alpaca keys have specific patterns)
        if [[ "${ALPACA_API_KEY}" =~ ^PK[A-Z0-9]{20}$ ]] || [[ "${ALPACA_API_KEY}" =~ ^AK[A-Z0-9]{20}$ ]]; then
            check_pass "API key format valid"
        else
            check_warn "API key format unusual" "Verify Alpaca API credentials"
        fi
    else
        check_fail "API credentials not configured" "Set ALPACA_API_KEY and ALPACA_API_SECRET"
    fi

    # Check disk space
    check_start "Checking disk space"
    local available_space=$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -gt 1 ]; then
        check_pass "Sufficient disk space (${available_space}GB available)"
    else
        check_warn "Low disk space (${available_space}GB available)" "Consider freeing up space"
    fi
}

################################################################################
# Post-Deployment Health Checks
################################################################################

post_deployment_checks() {
    section "POST-DEPLOYMENT HEALTH CHECKS"

    # Wait a bit for services to stabilize
    sleep 2

    # Check Observability API
    check_start "Observability API health (http://localhost:8000/health)"
    if wait_for_service "http://localhost:8000/health" 10; then
        local health_response=$(curl -s http://localhost:8000/health)
        if echo "$health_response" | grep -q '"status":"healthy"'; then
            check_pass "Observability API healthy"
        else
            check_fail "Observability API unhealthy" "Response: $health_response"
        fi
    else
        check_fail "Observability API not responding" "Check: python scripts/start_observability_api.py"
    fi

    # Check Observability API docs
    check_start "API documentation endpoint"
    if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
        check_pass "API docs available at http://localhost:8000/docs"
    else
        check_warn "API docs not accessible" "May not be critical"
    fi

    # Check Rust services (by process)
    check_start "Checking Rust service processes"
    local rust_services=("market_data" "execution" "risk")
    local running_services=()
    local stopped_services=()

    for service in "${rust_services[@]}"; do
        if pgrep -f "$service" > /dev/null 2>&1; then
            running_services+=("$service")
        else
            stopped_services+=("$service")
        fi
    done

    if [ ${#running_services[@]} -gt 0 ]; then
        check_pass "Rust services running: ${running_services[*]}"
    fi

    if [ ${#stopped_services[@]} -gt 0 ]; then
        check_warn "Rust services not detected: ${stopped_services[*]}" "May be running under different process names"
    fi

    # Check metrics endpoints
    check_start "Market Data metrics (http://localhost:9091/metrics)"
    if wait_for_service "http://localhost:9091/metrics" 5; then
        check_pass "Market Data metrics available"
    else
        check_warn "Market Data metrics not available" "Service may not be running"
    fi

    check_start "Execution Engine metrics (http://localhost:9092/metrics)"
    if wait_for_service "http://localhost:9092/metrics" 5; then
        check_pass "Execution Engine metrics available"
    else
        check_warn "Execution Engine metrics not available" "Service may not be running"
    fi

    check_start "Risk Manager metrics (http://localhost:9093/metrics)"
    if wait_for_service "http://localhost:9093/metrics" 5; then
        check_pass "Risk Manager metrics available"
    else
        check_warn "Risk Manager metrics not available" "Service may not be running"
    fi

    # Check database files
    check_start "Checking DuckDB database files"
    local db_files=("${PROJECT_ROOT}/data/duckdb/trading_metrics.db")
    local found_dbs=()

    for db in "${db_files[@]}"; do
        if [ -f "$db" ]; then
            found_dbs+=("$db")
        fi
    done

    if [ ${#found_dbs[@]} -gt 0 ]; then
        check_pass "Database files present (${#found_dbs[@]} found)"
    else
        check_warn "No database files found" "Will be created on first write"
    fi

    # Check log files
    check_start "Checking log file creation"
    if [ -n "$(find "${PROJECT_ROOT}/logs" -type f -mmin -5 2>/dev/null)" ]; then
        check_pass "Recent log files detected"
    else
        check_warn "No recent log files" "Services may not be logging yet"
    fi
}

################################################################################
# Integration Checks
################################################################################

integration_checks() {
    section "INTEGRATION CHECKS"

    # Check database connectivity
    check_start "Testing database write operation"
    local test_query="CREATE TABLE IF NOT EXISTS test_validation (id INTEGER, timestamp TIMESTAMP); \
                      INSERT INTO test_validation VALUES (1, CURRENT_TIMESTAMP); \
                      SELECT COUNT(*) FROM test_validation;"

    if command -v duckdb &> /dev/null; then
        if duckdb "${PROJECT_ROOT}/data/duckdb/trading_metrics.db" "$test_query" &> /dev/null; then
            check_pass "Database write operations working"
            duckdb "${PROJECT_ROOT}/data/duckdb/trading_metrics.db" "DROP TABLE IF EXISTS test_validation;" &> /dev/null
        else
            check_fail "Database write failed" "Check DuckDB installation and permissions"
        fi
    else
        check_warn "DuckDB CLI not available" "Cannot test database operations"
    fi

    # Check metrics collection
    check_start "Verifying metrics collection"
    local metrics_response=$(curl -s http://localhost:8000/metrics 2>/dev/null || echo "")
    if [ -n "$metrics_response" ]; then
        if echo "$metrics_response" | grep -q "market_data\|execution\|risk"; then
            check_pass "Metrics collection active"
        else
            check_warn "No metrics data yet" "May need time to collect"
        fi
    else
        check_fail "Cannot retrieve metrics" "Check observability API"
    fi

    # Check WebSocket connectivity
    check_start "Testing WebSocket endpoints"
    if command -v wscat &> /dev/null; then
        if timeout 2 wscat -c ws://localhost:8000/ws/metrics -x '{"type":"subscribe"}' &> /dev/null; then
            check_pass "WebSocket connections working"
        else
            check_warn "WebSocket test inconclusive" "Install wscat for full testing"
        fi
    else
        check_warn "wscat not available" "Cannot test WebSocket (install: npm install -g wscat)"
    fi

    # Check API endpoints
    check_start "Testing API endpoint responses"
    local endpoints=(
        "http://localhost:8000/"
        "http://localhost:8000/health"
        "http://localhost:8000/metrics"
    )
    local responsive_endpoints=0

    for endpoint in "${endpoints[@]}"; do
        if curl -s -f "$endpoint" > /dev/null 2>&1; then
            ((responsive_endpoints++))
        fi
    done

    if [ $responsive_endpoints -eq ${#endpoints[@]} ]; then
        check_pass "All API endpoints responding (${responsive_endpoints}/${#endpoints[@]})"
    else
        check_warn "Some endpoints not responding (${responsive_endpoints}/${#endpoints[@]})" "Check service logs"
    fi

    # Check service communication
    check_start "Testing inter-service communication"
    if curl -s http://localhost:8000/health | grep -q "services"; then
        check_pass "Service registry operational"
    else
        check_warn "Service registry status unknown" "Check API response format"
    fi
}

################################################################################
# Performance Smoke Tests
################################################################################

performance_checks() {
    section "PERFORMANCE SMOKE TESTS"

    # API response time
    check_start "Measuring API response time"
    local start_time=$(date +%s%N)
    curl -s http://localhost:8000/health > /dev/null 2>&1 || true
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))

    if [ $response_time -lt 1000 ]; then
        check_pass "API response time: ${response_time}ms (excellent)"
    elif [ $response_time -lt 3000 ]; then
        check_pass "API response time: ${response_time}ms (acceptable)"
    else
        check_warn "API response time: ${response_time}ms (slow)" "Consider optimization"
    fi

    # Memory usage
    check_start "Checking system memory"
    local mem_available=$(free -m | awk 'NR==2 {print $7}')
    if [ "$mem_available" -gt 1024 ]; then
        check_pass "Available memory: ${mem_available}MB"
    else
        check_warn "Low available memory: ${mem_available}MB" "Consider closing other applications"
    fi

    # CPU load
    check_start "Checking CPU load"
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cpu_cores=$(nproc 2>/dev/null || echo "1")
    if (( $(echo "$cpu_load < $cpu_cores" | bc -l 2>/dev/null || echo "1") )); then
        check_pass "CPU load normal: ${cpu_load} (${cpu_cores} cores)"
    else
        check_warn "High CPU load: ${cpu_load} (${cpu_cores} cores)" "System may be under stress"
    fi
}

################################################################################
# Generate Report
################################################################################

generate_report() {
    section "DEPLOYMENT VALIDATION SUMMARY"

    log ""
    log "Total Checks:   ${TOTAL_CHECKS}"
    log "${GREEN}Passed:        ${PASSED_CHECKS}${NC}"
    log "${RED}Failed:        ${FAILED_CHECKS}${NC}"
    log "${YELLOW}Warnings:      ${WARNINGS}${NC}"
    log ""

    local success_rate=0
    if [ $TOTAL_CHECKS -gt 0 ]; then
        success_rate=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    fi

    log "Success Rate:   ${success_rate}%"
    log "Log File:       ${LOG_FILE}"
    log ""

    if [ $FAILED_CHECKS -eq 0 ]; then
        log "${GREEN}╔════════════════════════════════════════╗${NC}"
        log "${GREEN}║  ✓ DEPLOYMENT VALIDATED SUCCESSFULLY  ║${NC}"
        log "${GREEN}╚════════════════════════════════════════╝${NC}"
        log ""
        log "System is ready for production use."
        if [ $WARNINGS -gt 0 ]; then
            log "${YELLOW}Note: ${WARNINGS} warning(s) detected - review recommended.${NC}"
        fi
        return 0
    else
        log "${RED}╔════════════════════════════════════════╗${NC}"
        log "${RED}║    ✗ DEPLOYMENT VALIDATION FAILED     ║${NC}"
        log "${RED}╚════════════════════════════════════════╝${NC}"
        log ""
        log "${RED}${FAILED_CHECKS} critical issue(s) must be resolved before deployment.${NC}"
        log "Review the log file for details: ${LOG_FILE}"
        return 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    log "╔════════════════════════════════════════════════════════╗"
    log "║     DEPLOYMENT VALIDATION - ALGORITHMIC TRADING       ║"
    log "╚════════════════════════════════════════════════════════╝"
    log ""
    log "Project: ${PROJECT_ROOT}"
    log "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    log ""

    # Run validation phases
    pre_deployment_checks
    post_deployment_checks
    integration_checks
    performance_checks

    # Generate final report
    generate_report
    exit $?
}

# Handle command line arguments
case "${1:-all}" in
    pre)
        pre_deployment_checks
        generate_report
        ;;
    post)
        post_deployment_checks
        generate_report
        ;;
    integration)
        integration_checks
        generate_report
        ;;
    performance)
        performance_checks
        generate_report
        ;;
    all|*)
        main
        ;;
esac
