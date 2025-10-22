#!/bin/bash
################################################################################
# DEPENDENCY CHECK SCRIPT
#
# Verifies all required dependencies for the observability stack:
# - Python packages (FastAPI, Uvicorn, DuckDB, SQLite, etc.)
# - Node.js and npm (for React dashboard)
# - System utilities (curl, jq)
# - Directory structure
#
# Usage: ./scripts/check_dependencies.sh
# Returns: 0 if all dependencies met, 1 otherwise
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0
REQUIRED_DEPS=0
REQUIRED_MET=0
OPTIONAL_DEPS=0
OPTIONAL_MET=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_success_required() {
    echo -e "${GREEN}[✓]${NC} $* ${BLUE}(required)${NC}"
    REQUIRED_MET=$((REQUIRED_MET + 1))
}

log_success_optional() {
    echo -e "${GREEN}[✓]${NC} $* ${BLUE}(optional)${NC}"
    OPTIONAL_MET=$((OPTIONAL_MET + 1))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $*"
    WARNINGS=$((WARNINGS + 1))
}

log_warning_optional() {
    echo -e "${YELLOW}[⚠]${NC} $* ${BLUE}(optional - not required)${NC}"
    WARNINGS=$((WARNINGS + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
    ERRORS=$((ERRORS + 1))
}

################################################################################
# System Command Checks
################################################################################

check_system_commands() {
    log_info "Checking system commands..."

    # Required commands
    local required_commands=("python3" "pip3" "cargo" "curl")
    REQUIRED_DEPS=$((REQUIRED_DEPS + ${#required_commands[@]}))

    for cmd in "${required_commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            log_success_required "$cmd is installed"
        else
            log_error "$cmd is NOT installed - REQUIRED for system operation"
        fi
    done

    echo ""
    log_info "Checking optional system commands..."

    # Optional but recommended commands
    local optional_commands=("node" "npm" "jq")
    OPTIONAL_DEPS=$((OPTIONAL_DEPS + ${#optional_commands[@]}))

    if command -v node &> /dev/null; then
        log_success_optional "Node.js is installed ($(node --version))"
    else
        log_warning_optional "Node.js is NOT installed - recommended for React dashboard"
    fi

    if command -v npm &> /dev/null; then
        log_success_optional "npm is installed ($(npm --version))"
    else
        log_warning_optional "npm is NOT installed - recommended for React dashboard"
    fi

    if command -v jq &> /dev/null; then
        log_success_optional "jq is installed - useful for JSON parsing"
    else
        log_warning_optional "jq is NOT installed - install for better JSON parsing capabilities"
    fi
}

################################################################################
# Python Environment Checks
################################################################################

check_python_environment() {
    log_info "Checking Python environment..."

    REQUIRED_DEPS=$((REQUIRED_DEPS + 1))

    # Python version
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local major_version=$(echo "$python_version" | cut -d'.' -f1)
    local minor_version=$(echo "$python_version" | cut -d'.' -f2)

    if [[ "$major_version" -ge 3 ]] && [[ "$minor_version" -ge 8 ]]; then
        log_success_required "Python $python_version (>= 3.8)"
    else
        log_error "Python $python_version is too old - Python >= 3.8 REQUIRED"
    fi

    echo ""
    log_info "Checking optional Python tools..."

    OPTIONAL_DEPS=$((OPTIONAL_DEPS + 1))

    # Check for uv (faster package manager)
    if command -v uv &> /dev/null; then
        log_success_optional "uv is installed ($(uv --version))"
    else
        log_warning_optional "uv is NOT installed - recommended for faster package management"
        log_info "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
}

################################################################################
# Python Package Checks
################################################################################

check_python_packages() {
    log_info "Checking required Python packages..."

    local required_packages=(
        "fastapi"
        "uvicorn"
        "websockets"
        "pydantic"
        "duckdb"
        "loguru"
        "psutil"
        "numpy"
        "pandas"
    )

    REQUIRED_DEPS=$((REQUIRED_DEPS + ${#required_packages[@]}))

    for package in "${required_packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            local version=$(python3 -c "import $package; print(getattr($package, '__version__', 'unknown'))" 2>/dev/null)
            log_success_required "$package is installed ($version)"
        else
            log_error "$package is NOT installed - REQUIRED Python package"
            log_info "Install with: pip3 install $package"
        fi
    done
}

################################################################################
# Directory Structure Checks
################################################################################

check_directory_structure() {
    log_info "Checking directory structure..."

    local required_dirs=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/data"
        "$PROJECT_ROOT/monitoring"
        "$PROJECT_ROOT/src/observability"
        "$PROJECT_ROOT/scripts"
    )

    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_success "Directory exists: $dir"
        else
            log_warning "Directory missing: $dir (will be created)"
            mkdir -p "$dir"
        fi
    done
}

################################################################################
# Configuration File Checks
################################################################################

check_configuration_files() {
    log_info "Checking configuration files..."

    # .env file
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        log_success ".env file exists"

        # Check for required variables
        if grep -q "ALPACA_API_KEY" "$PROJECT_ROOT/.env" && \
           grep -q "ALPACA_SECRET_KEY" "$PROJECT_ROOT/.env"; then
            log_success ".env contains required Alpaca credentials"
        else
            log_error ".env missing ALPACA_API_KEY or ALPACA_SECRET_KEY"
        fi
    else
        log_error ".env file NOT found"
        log_info "Create .env with: ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER=true"
    fi

    # Config files
    if [[ -f "$PROJECT_ROOT/config/system.json" ]]; then
        log_success "system.json exists"
    else
        log_warning "system.json NOT found (may be optional)"
    fi

    if [[ -f "$PROJECT_ROOT/config/risk_limits.toml" ]]; then
        log_success "risk_limits.toml exists"
    else
        log_warning "risk_limits.toml NOT found (may be optional)"
    fi
}

################################################################################
# Port Availability Checks
################################################################################

check_port_availability() {
    log_info "Checking port availability..."

    local required_ports=(
        "8000:Observability API"
        "3000:React Dashboard"
        "5001:Market Data Service"
        "5002:Risk Manager Service"
        "5003:Execution Engine Service"
    )

    for port_info in "${required_ports[@]}"; do
        IFS=':' read -r port service <<< "$port_info"

        if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warning "Port $port is IN USE ($service)"
            log_info "Kill with: lsof -ti:$port | xargs kill -9"
        else
            log_success "Port $port is available ($service)"
        fi
    done
}

################################################################################
# Rust Build Checks
################################################################################

check_rust_build() {
    log_info "Checking Rust build status..."

    if [[ ! -d "$PROJECT_ROOT/rust" ]]; then
        log_warning "Rust directory not found"
        return
    fi

    cd "$PROJECT_ROOT/rust"

    # Check if binaries exist
    local services=("market-data" "risk-manager" "execution-engine")

    for service in "${services[@]}"; do
        if [[ -f "target/release/$service" ]]; then
            log_success "Rust binary exists: $service"
        else
            log_warning "Rust binary NOT found: $service (will be built)"
        fi
    done

    cd "$PROJECT_ROOT"
}

################################################################################
# Dashboard Checks
################################################################################

check_dashboard() {
    log_info "Checking React dashboard..."

    if [[ -d "$PROJECT_ROOT/src/observability/dashboard" ]]; then
        log_success "Dashboard directory exists"

        if [[ -f "$PROJECT_ROOT/src/observability/dashboard/package.json" ]]; then
            log_success "package.json exists"

            if [[ -d "$PROJECT_ROOT/src/observability/dashboard/node_modules" ]]; then
                log_success "node_modules exists (dependencies installed)"
            else
                log_warning "node_modules NOT found (run: npm install)"
            fi
        else
            log_warning "package.json NOT found in dashboard"
        fi
    else
        log_warning "Dashboard directory NOT found (optional)"
    fi
}

################################################################################
# Database Checks
################################################################################

check_databases() {
    log_info "Checking database files..."

    # DuckDB
    if python3 -c "import duckdb" 2>/dev/null; then
        log_success "DuckDB Python package installed"

        if [[ -f "$PROJECT_ROOT/data/metrics.duckdb" ]]; then
            log_success "DuckDB database file exists"
        else
            log_warning "DuckDB database will be created on first run"
        fi
    else
        log_error "DuckDB NOT installed"
    fi

    # SQLite (usually built into Python)
    if python3 -c "import sqlite3" 2>/dev/null; then
        log_success "SQLite Python package available"
    else
        log_error "SQLite NOT available"
    fi
}

################################################################################
# Summary Report
################################################################################

print_summary() {
    echo ""
    echo "=========================================="
    echo "DEPENDENCY CHECK SUMMARY"
    echo "=========================================="
    echo ""

    # Required dependencies summary
    echo -e "${BLUE}Required Dependencies:${NC}"
    if [[ $REQUIRED_DEPS -gt 0 ]]; then
        if [[ $REQUIRED_MET -eq $REQUIRED_DEPS ]]; then
            echo -e "  ${GREEN}✓ All required dependencies met ($REQUIRED_MET/$REQUIRED_DEPS)${NC}"
        else
            echo -e "  ${RED}✗ Missing required dependencies ($REQUIRED_MET/$REQUIRED_DEPS met)${NC}"
        fi
    else
        echo -e "  ${BLUE}No required dependencies tracked${NC}"
    fi

    echo ""

    # Optional dependencies summary
    echo -e "${BLUE}Optional Dependencies:${NC}"
    if [[ $OPTIONAL_DEPS -gt 0 ]]; then
        local optional_missing=$((OPTIONAL_DEPS - OPTIONAL_MET))
        if [[ $OPTIONAL_MET -eq $OPTIONAL_DEPS ]]; then
            echo -e "  ${GREEN}✓ All optional dependencies met ($OPTIONAL_MET/$OPTIONAL_DEPS)${NC}"
        else
            echo -e "  ${YELLOW}⚠ $optional_missing optional dependencies missing ($OPTIONAL_MET/$OPTIONAL_DEPS met)${NC}"
            echo -e "  ${BLUE}These are recommended but not required for basic operation${NC}"
        fi
    else
        echo -e "  ${BLUE}No optional dependencies tracked${NC}"
    fi

    echo ""

    # Overall status
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✓ DEPENDENCY CHECK PASSED${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        if [[ $WARNINGS -gt 0 ]]; then
            echo ""
            echo -e "${YELLOW}Note: $WARNINGS optional dependencies missing (non-critical)${NC}"
        fi

        echo ""
        return 0
    else
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}✗ DEPENDENCY CHECK FAILED${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${RED}Errors: $ERRORS${NC}"
        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}Warnings: $WARNINGS (optional)${NC}"
        fi
        echo ""
        echo "Please fix the errors above before starting the system."
        echo ""
        return 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    echo "=========================================="
    echo "OBSERVABILITY STACK DEPENDENCY CHECK"
    echo "=========================================="
    echo ""

    check_system_commands
    echo ""

    check_python_environment
    echo ""

    check_python_packages
    echo ""

    check_directory_structure
    echo ""

    check_configuration_files
    echo ""

    check_port_availability
    echo ""

    check_rust_build
    echo ""

    check_dashboard
    echo ""

    check_databases
    echo ""

    print_summary
}

main "$@"
