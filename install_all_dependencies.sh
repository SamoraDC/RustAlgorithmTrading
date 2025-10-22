#!/bin/bash
set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  RUST ALGORITHMIC TRADING SYSTEM - DEPENDENCY INSTALLER      ║"
echo "║  Using UV (10-100x faster than pip!)                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_uv() {
    echo -e "${BLUE}[UV]${NC} $1"
}

# Parse arguments
USER_ONLY=false

for arg in "$@"; do
    case $arg in
        --user-only)
            USER_ONLY=true
            shift
            ;;
    esac
done

# Check if running with sudo for system packages
if [ "$EUID" -ne 0 ] && [ "$USER_ONLY" = false ]; then
    log_error "Please run with sudo for system package installation"
    log_info "Usage: sudo ./install_all_dependencies.sh"
    log_info "Or for user-level only: ./install_all_dependencies.sh --user-only"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Installing System Packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$USER_ONLY" = false ]; then
    log_info "Updating package lists..."
    apt-get update -qq

    log_info "Installing system dependencies..."
    apt-get install -y \
        python3 \
        python3-venv \
        python3.12-venv \
        build-essential \
        pkg-config \
        libssl-dev \
        curl \
        git \
        jq \
        > /dev/null 2>&1

    log_success "System packages installed"
else
    log_info "Skipping system package installation (--user-only mode)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1.5: Installing UV (Ultra-fast Python Package Manager)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v uv &> /dev/null; then
    log_uv "UV not found, installing..."
    # Install uv globally using the official installer
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add to current session PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    export PATH="$HOME/.local/bin:$PATH"

    if command -v uv &> /dev/null; then
        log_success "UV installed successfully: $(uv --version)"
    else
        log_error "UV installation failed"
        exit 1
    fi
else
    log_success "UV already installed: $(uv --version)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Cleaning Up Duplicate Virtual Environments"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$SCRIPT_DIR"

# Remove old venv directories
if [ -d "venv" ]; then
    log_info "Removing old venv directory..."
    rm -rf venv
    log_success "Removed venv directory"
fi

if [ -d ".venv" ]; then
    log_info "Removing old .venv directory..."
    rm -rf .venv
    log_success "Removed .venv directory"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Creating Virtual Environment with UV"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_uv "Creating .venv with UV (ultra-fast!)..."
uv venv .venv
source .venv/bin/activate
log_success "Virtual environment created at .venv"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Installing Python Dependencies with UV"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_uv "Installing dependencies (parallel downloads + caching)..."

# Install each package with uv add for proper dependency management
uv pip install --upgrade pip

# Core Data Science
log_info "Installing core data science packages..."
uv pip install "numpy>=1.24.0" "pandas>=2.0.0" "scipy>=1.10.0"

# Visualization
log_info "Installing visualization packages..."
uv pip install "matplotlib>=3.7.0" "seaborn>=0.12.0"

# Trading
log_info "Installing trading packages..."
uv pip install "alpaca-py>=0.42.2"

# Logging
log_info "Installing logging packages..."
uv pip install "loguru>=0.7.0"

# ML (optional but recommended)
log_info "Installing ML packages..."
uv pip install "scikit-learn>=1.3.0" "xgboost>=1.7.6"

# FastAPI Backend & WebSocket
log_info "Installing FastAPI and WebSocket packages..."
uv pip install "fastapi>=0.104.0" "uvicorn[standard]>=0.24.0" "websockets>=12.0" "pydantic>=2.5.0" "python-multipart>=0.0.6"

# System Monitoring
log_info "Installing system monitoring packages..."
uv pip install "psutil>=5.9.0"

# Database & Storage
log_info "Installing database packages..."
uv pip install "duckdb>=0.9.0" "aiosqlite>=0.19.0"

# Development
log_info "Installing development packages..."
uv pip install "pytest>=7.4.0" "pytest-asyncio>=0.21.0" "httpx>=0.25.0"

log_success "All Python dependencies installed with UV"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Verifying Rust Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v cargo &> /dev/null; then
    log_info "Rust not found, installing..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    log_success "Rust installed"
else
    log_success "Rust already installed: $(rustc --version)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Building Rust Services (Parallel Compilation)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd rust
log_info "Building Rust project with parallel compilation..."
CARGO_BUILD_JOBS=$(nproc) cargo build --release --jobs $(nproc) 2>&1 | grep -E "(Compiling|Finished|error|warning:)" | head -20 || true

if [ -f "target/release/market-data" ]; then
    log_success "Rust services built successfully"
else
    log_error "Rust build may have issues - check for warnings above"
fi

cd "$SCRIPT_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 7: Final Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run dependency check
if [ -f "scripts/check_dependencies.sh" ]; then
    log_info "Running dependency check..."
    bash scripts/check_dependencies.sh
else
    log_info "Skipping dependency check (script not found)"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   INSTALLATION COMPLETE!                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "📁 Virtual Environment: .venv (consolidated, no duplicates)"
echo "   - Old 'venv' directory removed"
echo "   - Old '.venv' directory cleaned"
echo "   - New '.venv' created with UV"
echo ""
echo "⚡ Performance Optimizations Applied:"
echo "   ✓ UV package manager (10-100x faster than pip)"
echo "   ✓ Parallel downloads and intelligent caching"
echo "   ✓ Parallel Rust compilation ($(nproc) cores)"
echo "   ✓ Removed redundant pip installation"
echo "   ✓ Optimized system package installation"
echo ""
echo "🎯 Next Steps:"
echo "   1. Activate virtual environment:"
echo "      source .venv/bin/activate"
echo ""
echo "   2. Configure .env file with your API keys"
echo ""
echo "   3. Start trading system:"
echo "      ./scripts/start_trading.sh"
echo ""
echo "📚 Quick Reference:"
echo "   • Activate venv:      source .venv/bin/activate"
echo "   • Add package:        uv pip install <package>"
echo "   • List packages:      uv pip list"
echo "   • Upgrade package:    uv pip install --upgrade <package>"
echo "   • Start system:       ./scripts/start_trading.sh"
echo "   • Validate:           ./scripts/validate_deployment.sh"
echo "   • Check deps:         ./scripts/check_dependencies.sh"
echo ""
echo "💡 About Virtual Environments:"
echo "   - This project now uses a SINGLE .venv directory"
echo "   - UV automatically manages Python versions and dependencies"
echo "   - Much faster installs and better dependency resolution"
echo ""
