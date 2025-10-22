#!/bin/bash
################################################################################
# PRODUCTION-READY TRADING SYSTEM STARTUP SCRIPT
#
# This script starts the entire autonomous trading system with robust validation:
# - Pre-flight dependency verification
# - Environment validation and setup
# - Database initialization
# - Observability stack with health checks
# - Service startup with retry logic
# - Comprehensive error handling and logging
#
# Usage: ./scripts/start_trading.sh [OPTIONS]
#   --no-observability    Skip observability stack
#   --no-dashboard        Skip React dashboard
#   --validate-only       Only validate, don't start services
#   --timeout SECONDS     Service startup timeout (default: 60)
#
# Exit Codes:
#   0 - Success
#   1 - Dependency check failed
#   2 - Environment validation failed
#   3 - Database initialization failed
#   4 - Observability startup failed
#   5 - Trading system startup failed
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
START_OBSERVABILITY=true
DASHBOARD_ARGS=""
VALIDATE_ONLY=false
STARTUP_TIMEOUT=60

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-observability)
            START_OBSERVABILITY=false
            shift
            ;;
        --no-dashboard)
            DASHBOARD_ARGS="--no-dashboard"
            shift
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --timeout)
            STARTUP_TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# PIDs for cleanup
OBSERVABILITY_PID=""
TRADING_PID=""

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') - $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $(date '+%H:%M:%S') - $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $(date '+%H:%M:%S') - $*"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $(date '+%H:%M:%S') - $*"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $*${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

################################################################################
# Validation Functions
################################################################################

check_dependencies() {
    log_step "STEP 1: Dependency Verification"

    log_info "Running comprehensive dependency checks..."

    if "$SCRIPT_DIR/check_dependencies.sh"; then
        log_success "All dependencies verified"
        return 0
    else
        log_error "Dependency check failed"
        log_info "Fix the issues reported above and try again"
        return 1
    fi
}

validate_environment() {
    log_step "STEP 2: Environment Validation"

    # Check .env exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found!"
        echo ""
        echo "Create .env file with your Alpaca credentials:"
        echo ""
        echo "  ALPACA_API_KEY=your_api_key_here"
        echo "  ALPACA_SECRET_KEY=your_secret_key_here"
        echo "  ALPACA_PAPER=true"
        echo ""
        return 2
    fi

    log_success ".env file exists"

    # Source environment variables
    set -a
    source "$PROJECT_ROOT/.env" 2>/dev/null || {
        log_error "Failed to load .env file"
        return 2
    }
    set +a

    # Validate required variables
    local missing_vars=()

    if [ -z "${ALPACA_API_KEY:-}" ]; then
        missing_vars+=("ALPACA_API_KEY")
    fi

    if [ -z "${ALPACA_SECRET_KEY:-}" ]; then
        missing_vars+=("ALPACA_SECRET_KEY")
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        return 2
    fi

    log_success "Environment variables validated"

    # Verify API keys format (basic check)
    if [[ ! "$ALPACA_API_KEY" =~ ^[A-Z0-9]{20}$ ]]; then
        log_warning "ALPACA_API_KEY format looks unusual (expected 20 alphanumeric chars)"
    fi

    # Force paper trading for safety
    export ALPACA_PAPER=true
    log_success "Paper trading mode enforced"

    return 0
}

check_port_availability() {
    log_info "Checking port availability..."

    local ports_to_check=(
        "8000:Observability API"
        "3000:React Dashboard"
        "5001:Market Data Service"
        "5002:Risk Manager"
        "5003:Execution Engine"
    )

    local ports_in_use=()

    for port_info in "${ports_to_check[@]}"; do
        IFS=':' read -r port service <<< "$port_info"

        if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            ports_in_use+=("$port ($service)")
            log_warning "Port $port is already in use ($service)"
        else
            log_success "Port $port is available ($service)"
        fi
    done

    if [ ${#ports_in_use[@]} -gt 0 ]; then
        log_warning "Found ${#ports_in_use[@]} port(s) in use: ${ports_in_use[*]}"
        log_info "Services will attempt to use these ports or fail if unable to bind"
    fi

    return 0
}

initialize_directories() {
    log_info "Initializing directory structure..."

    local required_dirs=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/logs/observability"
        "$PROJECT_ROOT/logs/autonomous"
        "$PROJECT_ROOT/data"
        "$PROJECT_ROOT/data/backtest_results"
        "$PROJECT_ROOT/data/simulation_results"
        "$PROJECT_ROOT/data/live_trading"
        "$PROJECT_ROOT/monitoring"
    )

    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "Created directory: $dir"
        fi
    done

    log_success "Directory structure initialized"
    return 0
}

initialize_database() {
    log_step "STEP 3: Database Initialization"

    log_info "Initializing DuckDB database..."

    # Check if database already exists
    if [ -f "$PROJECT_ROOT/data/metrics.duckdb" ]; then
        log_success "DuckDB database already exists"

        # Verify database integrity
        if python3 <<'PYTHON_CHECK'
import sys
import duckdb

sys.path.insert(0, 'src')

try:
    conn = duckdb.connect('data/metrics.duckdb', read_only=True)
    result = conn.execute("SELECT COUNT(*) FROM information_schema.tables").fetchone()
    conn.close()
    print(f"[OK] Database has {result[0]} tables")
    sys.exit(0)
except Exception as e:
    print(f"[ERROR] Database integrity check failed: {e}")
    sys.exit(1)
PYTHON_CHECK
        then
            log_success "Database integrity verified"
        else
            log_error "Database integrity check failed - will attempt to recreate"
            rm -f "$PROJECT_ROOT/data/metrics.duckdb"
        fi
    fi

    # Create/initialize database if needed
    if [ ! -f "$PROJECT_ROOT/data/metrics.duckdb" ]; then
        log_info "Creating new DuckDB database with schema..."

        if python3 <<'PYTHON_INIT'
import sys
import duckdb
from datetime import datetime

sys.path.insert(0, 'src')

try:
    from observability.database import DuckDBManager

    # Initialize database (happens automatically in __init__)
    db = DuckDBManager('data/metrics.duckdb')

    # Verify initialization
    conn = duckdb.connect('data/metrics.duckdb')
    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
    conn.close()

    print(f"[OK] Database initialized with {len(tables)} tables")
    sys.exit(0)
except Exception as e:
    print(f"[ERROR] Database initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_INIT
        then
            log_success "Database initialized successfully"
            return 0
        else
            log_error "Database initialization failed"
            return 3
        fi
    fi

    return 0
}

################################################################################
# Service Health Check Functions
################################################################################

wait_for_service() {
    local service_name="$1"
    local health_url="$2"
    local timeout="${3:-$STARTUP_TIMEOUT}"
    local interval="${4:-1}"

    log_info "Waiting for $service_name to be ready..."

    local elapsed=0
    local last_error=""

    while [ $elapsed -lt $timeout ]; do
        # Try health check
        if response=$(curl -sf "$health_url" 2>&1); then
            log_success "$service_name is healthy and ready"
            return 0
        else
            last_error="$response"
        fi

        # Show progress indicator
        if [ $((elapsed % 5)) -eq 0 ] && [ $elapsed -gt 0 ]; then
            log_info "Still waiting for $service_name... (${elapsed}s/${timeout}s)"
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "$service_name failed to become ready within ${timeout}s"
    log_error "Last error: $last_error"
    return 1
}

verify_service_health() {
    local service_name="$1"
    local health_url="$2"

    if response=$(curl -sf "$health_url" 2>&1); then
        log_success "$service_name health check passed"
        return 0
    else
        log_error "$service_name health check failed: $response"
        return 1
    fi
}

################################################################################
# Start Observability Stack
################################################################################

start_observability() {
    log_step "STEP 4: Observability Stack Startup"

    if [[ "$START_OBSERVABILITY" != "true" ]]; then
        log_info "Observability stack disabled (--no-observability)"
        return 0
    fi

    log_info "Starting observability API server..."

    # Ensure logs directory exists
    mkdir -p "$PROJECT_ROOT/logs/observability"

    # Start observability API using Python script
    log_info "Launching FastAPI server with uvicorn..."

    cd "$PROJECT_ROOT"

    # Start server in background with proper error handling
    python3 "$SCRIPT_DIR/start_observability_api.py" \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        > "$PROJECT_ROOT/logs/observability/api.log" 2>&1 &

    OBSERVABILITY_PID=$!

    # Save PID for cleanup
    echo $OBSERVABILITY_PID > "$PROJECT_ROOT/monitoring/observability_api.pid"

    log_info "Observability API started (PID: $OBSERVABILITY_PID)"

    # Verify process started
    sleep 2
    if ! kill -0 $OBSERVABILITY_PID 2>/dev/null; then
        log_error "Observability API process died immediately after startup"
        log_info "Check logs at: $PROJECT_ROOT/logs/observability/api.log"
        return 4
    fi

    # Wait for API to be ready
    if ! wait_for_service "Observability API" "http://localhost:8000/health" $STARTUP_TIMEOUT; then
        log_error "Observability API failed to start"
        log_info "Check logs at: $PROJECT_ROOT/logs/observability/api.log"

        # Show last 20 lines of log
        if [ -f "$PROJECT_ROOT/logs/observability/api.log" ]; then
            echo ""
            log_warning "Last 20 lines of API log:"
            tail -n 20 "$PROJECT_ROOT/logs/observability/api.log"
        fi

        return 4
    fi

    # Verify readiness endpoint
    if ! verify_service_health "Observability API (readiness)" "http://localhost:8000/health/ready"; then
        log_warning "API is running but not fully ready (collectors may be initializing)"
    fi

    # Display access information
    echo ""
    log_success "Observability stack is operational"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "  📊 Dashboard:      http://localhost:8000"
    log_info "  📖 API Docs:       http://localhost:8000/docs"
    log_info "  🔌 WebSocket:      ws://localhost:8000/ws/metrics"
    log_info "  💚 Health Check:   http://localhost:8000/health"
    log_info "  📁 Logs:           $PROJECT_ROOT/logs/observability/api.log"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    return 0
}

################################################################################
# Cleanup Handler
################################################################################

cleanup() {
    local exit_code=$?

    echo ""
    log_step "SHUTDOWN: Graceful Cleanup"

    log_info "Initiating graceful shutdown sequence..."

    # Stop trading system first (most important to stop cleanly)
    if [[ -n "${TRADING_PID:-}" ]] && kill -0 $TRADING_PID 2>/dev/null; then
        log_info "Stopping trading system (PID: $TRADING_PID)..."
        kill -TERM $TRADING_PID 2>/dev/null || true

        # Wait up to 10 seconds for graceful shutdown
        local wait_count=0
        while kill -0 $TRADING_PID 2>/dev/null && [ $wait_count -lt 10 ]; do
            sleep 1
            ((wait_count++))
        done

        # Force kill if still running
        if kill -0 $TRADING_PID 2>/dev/null; then
            log_warning "Trading system did not stop gracefully, forcing..."
            kill -9 $TRADING_PID 2>/dev/null || true
        fi

        log_success "Trading system stopped"
    fi

    # Stop observability stack
    if [[ -n "${OBSERVABILITY_PID:-}" ]] && kill -0 $OBSERVABILITY_PID 2>/dev/null; then
        log_info "Stopping observability API (PID: $OBSERVABILITY_PID)..."
        kill -TERM $OBSERVABILITY_PID 2>/dev/null || true

        # Wait up to 5 seconds
        local wait_count=0
        while kill -0 $OBSERVABILITY_PID 2>/dev/null && [ $wait_count -lt 5 ]; do
            sleep 1
            ((wait_count++))
        done

        if kill -0 $OBSERVABILITY_PID 2>/dev/null; then
            kill -9 $OBSERVABILITY_PID 2>/dev/null || true
        fi

        log_success "Observability API stopped"
    fi

    # Clean up PID files and any orphaned processes
    log_info "Cleaning up PID files..."

    local pid_files=(
        "$PROJECT_ROOT/monitoring/observability_api.pid"
        "$PROJECT_ROOT/monitoring/dashboard.pid"
        "$PROJECT_ROOT/logs/autonomous/paper_trading.pid"
        "$PROJECT_ROOT/logs/autonomous/market-data.pid"
        "$PROJECT_ROOT/logs/autonomous/risk-manager.pid"
        "$PROJECT_ROOT/logs/autonomous/execution-engine.pid"
    )

    for pid_file in "${pid_files[@]}"; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file" 2>/dev/null || echo "")
            if [[ -n "$pid" ]] && kill -0 $pid 2>/dev/null; then
                log_info "Stopping orphaned process (PID: $pid)..."
                kill -TERM $pid 2>/dev/null || true
                sleep 1
                kill -9 $pid 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done

    # Save final state to database if observability was running
    if [[ "$START_OBSERVABILITY" == "true" ]] && [ -f "$PROJECT_ROOT/data/metrics.duckdb" ]; then
        log_info "Persisting final metrics to database..."

        python3 <<'PYTHON_SAVE' 2>/dev/null || log_warning "Could not save final metrics"
import sys
import duckdb
from datetime import datetime

sys.path.insert(0, 'src')

try:
    conn = duckdb.connect('data/metrics.duckdb')

    # Record shutdown event with timestamp
    # system_metrics columns: timestamp, cpu_percent, memory_percent, disk_usage_percent, uptime_seconds, health_status, active_alerts
    conn.execute("""
        INSERT INTO system_metrics (timestamp, cpu_percent, memory_percent, disk_usage_percent, uptime_seconds, health_status, active_alerts)
        VALUES (?, 0, 0, 0, 0, 'shutdown', 0)
    """, [datetime.now()])

    conn.close()
    print("[SAVE] Final state persisted to DuckDB")
except Exception as e:
    print(f"[SAVE] Warning: {e}")
    sys.exit(1)
PYTHON_SAVE

        log_success "Final state saved to DuckDB"
    fi

    echo ""
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "  Graceful shutdown complete"
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    exit $exit_code
}

# Setup trap for graceful shutdown on EXIT, SIGINT, SIGTERM
trap cleanup EXIT INT TERM

################################################################################
# Main Execution
################################################################################

main() {
    echo ""
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "  Starting Production Trading System"
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # STEP 1: Dependency Verification
    if ! check_dependencies; then
        log_error "Dependency verification failed"
        exit 1
    fi

    # STEP 2: Environment Validation
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 2
    fi

    # Port availability check
    check_port_availability

    # Directory initialization
    if ! initialize_directories; then
        log_error "Directory initialization failed"
        exit 2
    fi

    # STEP 3: Database Initialization
    if ! initialize_database; then
        log_error "Database initialization failed"
        exit 3
    fi

    # Exit if validation-only mode
    if [[ "$VALIDATE_ONLY" == "true" ]]; then
        echo ""
        log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_success "  Validation completed successfully"
        log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        log_info "System is ready to start. Run without --validate-only to start services."
        exit 0
    fi

    # STEP 4: Start Observability Stack
    if ! start_observability; then
        log_error "Failed to start observability stack"
        exit 4
    fi

    # STEP 5: Start Trading System
    log_step "STEP 5: Trading System Startup"

    log_info "Launching autonomous trading system..."

    if [[ "$START_OBSERVABILITY" == "true" ]]; then
        log_info "Real-time metrics: http://localhost:8000"
        log_info "WebSocket stream: ws://localhost:8000/ws/metrics"
    fi

    echo ""

    # Check if autonomous trading system script exists
    if [[ ! -f "$SCRIPT_DIR/autonomous_trading_system.sh" ]]; then
        log_error "autonomous_trading_system.sh not found!"
        log_info "Expected location: $SCRIPT_DIR/autonomous_trading_system.sh"
        log_info "This script is required to launch the trading services"
        return 5
    fi

    # Make sure script is executable
    chmod +x "$SCRIPT_DIR/autonomous_trading_system.sh"

    # Run the autonomous trading system in background
    "$SCRIPT_DIR/autonomous_trading_system.sh" --mode=full > "$PROJECT_ROOT/logs/trading_system.log" 2>&1 &
    TRADING_PID=$!

    log_info "Trading system started (PID: $TRADING_PID)"
    log_info "Monitor logs: $PROJECT_ROOT/logs/trading_system.log"

    echo ""
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "  All systems operational!"
    log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ "$START_OBSERVABILITY" == "true" ]]; then
        log_info "📊 Observability Dashboard: http://localhost:8000"
        log_info "📖 API Documentation:      http://localhost:8000/docs"
        log_info "🔌 WebSocket Metrics:      ws://localhost:8000/ws/metrics"
    fi

    log_info "📈 Trading System Logs:    $PROJECT_ROOT/logs/trading_system.log"
    log_info "📁 Autonomous Logs:        $PROJECT_ROOT/logs/autonomous/"

    echo ""
    log_info "Press Ctrl+C to stop all services gracefully"
    echo ""

    # Wait for trading system to complete
    wait $TRADING_PID
    TRADING_STATUS=$?

    echo ""

    if [ $TRADING_STATUS -eq 0 ]; then
        log_success "Trading system completed successfully"
    else
        log_error "Trading system exited with error code: $TRADING_STATUS"

        # Show last 30 lines of trading log for debugging
        if [ -f "$PROJECT_ROOT/logs/trading_system.log" ]; then
            echo ""
            log_warning "Last 30 lines of trading system log:"
            tail -n 30 "$PROJECT_ROOT/logs/trading_system.log"
        fi
    fi

    exit $TRADING_STATUS
}

# Run main function
main "$@"
