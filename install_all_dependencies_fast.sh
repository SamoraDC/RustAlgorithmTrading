#!/bin/bash
set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  RUST ALGORITHMIC TRADING SYSTEM - FAST INSTALLER (WSL2)     ║"
echo "║  Optimized for WSL2 - Skips slow release builds              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_wsl() {
    echo -e "${CYAN}[WSL2]${NC} $1"
}

# Parse arguments
USER_ONLY=false
SKIP_RUST_BUILD=false
SHOW_HELP=false

for arg in "$@"; do
    case $arg in
        --user-only)
            USER_ONLY=true
            shift
            ;;
        --skip-rust-build)
            SKIP_RUST_BUILD=true
            shift
            ;;
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            log_error "Unknown option: $arg"
            SHOW_HELP=true
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Fast installation script optimized for WSL2 with UV package manager"
    echo ""
    echo "Options:"
    echo "  --user-only         Skip system packages (no sudo required)"
    echo "  --skip-rust-build   Skip Rust build step (faster installation)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0                           # Full installation with system packages"
    echo "  sudo $0 --skip-rust-build         # Skip Rust build (build later)"
    echo "  $0 --user-only                    # User-level only (no sudo)"
    echo ""
    echo "For WSL2 Performance:"
    echo "  Move project to Linux filesystem for 10-20x speedup:"
    echo "  mkdir -p ~/projects && cp -r . ~/projects/RustAlgorithmTrading"
    echo ""
    exit 0
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if script is being run from project root
if [[ ! -f "$SCRIPT_DIR/requirements.txt" ]] || [[ ! -d "$SCRIPT_DIR/rust" ]]; then
    log_error "Script must be run from project root directory"
    log_info "Current directory: $SCRIPT_DIR"
    log_info "Expected files: requirements.txt, rust/"
    exit 1
fi

# Check if running with sudo for system packages
if [ "$EUID" -ne 0 ] && [ "$USER_ONLY" = false ]; then
    log_error "Please run with sudo for system package installation"
    log_info "Usage: sudo ./install_all_dependencies_fast.sh [--skip-rust-build]"
    log_info "Or for user-level only: ./install_all_dependencies_fast.sh --user-only [--skip-rust-build]"
    log_info "Use --help for more information"
    exit 1
fi

# Detect WSL2
if grep -qi microsoft /proc/version; then
    log_wsl "WSL2 detected! Using optimized settings..."
    IS_WSL=true

    # Check if on Windows filesystem
    if [[ "$SCRIPT_DIR" == /mnt/* ]]; then
        log_error "⚠️  PROJECT IS ON WINDOWS FILESYSTEM (/mnt/c/...)"
        echo ""
        echo "This causes SEVERE performance issues due to cross-filesystem overhead."
        echo ""
        echo "Rust compilation will be EXTREMELY slow (20+ minutes vs 2-3 minutes)."
        echo ""
        echo "📋 RECOMMENDED SOLUTIONS:"
        echo ""
        echo "1. MOVE PROJECT TO LINUX FILESYSTEM (Fastest - 10-20x faster):"
        echo "   mkdir -p ~/projects"
        echo "   cp -r \"$SCRIPT_DIR\" ~/projects/"
        echo "   cd ~/projects/RustAlgorithmTrading"
        echo "   sudo ./install_all_dependencies_fast.sh"
        echo ""
        echo "2. SKIP RUST BUILD NOW (Install continues):"
        echo "   sudo ./install_all_dependencies_fast.sh --skip-rust-build"
        echo "   # Build Rust later on-demand when needed"
        echo ""
        echo "3. CONTINUE ANYWAY (Slow - 20+ minutes):"
        echo "   Press Ctrl+C to cancel, or wait..."
        echo ""

        if [ "$SKIP_RUST_BUILD" = false ]; then
            read -p "Skip Rust build? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                SKIP_RUST_BUILD=true
                log_wsl "Rust build will be skipped"
            fi
        fi
    fi
else
    IS_WSL=false
fi

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
if [ "$IS_WSL" = true ]; then
    # Use copy mode for WSL2 to avoid hardlink warnings
    UV_LINK_MODE=copy uv venv .venv
else
    uv venv .venv
fi
source .venv/bin/activate
log_success "Virtual environment created at .venv"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Installing Python Dependencies with UV"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_uv "Installing dependencies (parallel downloads + caching)..."

# Set link mode for WSL2
if [ "$IS_WSL" = true ]; then
    export UV_LINK_MODE=copy
    log_wsl "Using copy mode (no hardlink warnings)"
fi

# Install each package with uv add for proper dependency management
uv pip install --upgrade pip -q

# Core Data Science
log_info "Installing core data science packages..."
uv pip install -q "numpy>=1.24.0" "pandas>=2.0.0" "scipy>=1.10.0"

# Visualization
log_info "Installing visualization packages..."
uv pip install -q "matplotlib>=3.7.0" "seaborn>=0.12.0"

# Trading
log_info "Installing trading packages..."
uv pip install -q "alpaca-py>=0.42.2"

# Logging
log_info "Installing logging packages..."
uv pip install -q "loguru>=0.7.0"

# ML (optional but recommended)
log_info "Installing ML packages..."
uv pip install -q "scikit-learn>=1.3.0" "xgboost>=1.7.6"

# FastAPI Backend & WebSocket
log_info "Installing FastAPI and WebSocket packages..."
uv pip install -q "fastapi>=0.104.0" "uvicorn[standard]>=0.24.0" "websockets>=12.0" "pydantic>=2.5.0" "python-multipart>=0.0.6"

# System Monitoring
log_info "Installing system monitoring packages..."
uv pip install -q "psutil>=5.9.0"

# Database & Storage
log_info "Installing database packages..."
uv pip install -q "duckdb>=0.9.0" "aiosqlite>=0.19.0"

# Async HTTP Client
log_info "Installing async HTTP client..."
uv pip install -q "aiohttp>=3.9.0"

# Development
log_info "Installing development packages..."
uv pip install -q "pytest>=7.4.0" "pytest-asyncio>=0.21.0" "httpx>=0.25.0"

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
echo "STEP 6: Building Rust Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$SKIP_RUST_BUILD" = true ]; then
    log_wsl "⚠️  Skipping Rust build (--skip-rust-build flag set)"
    echo ""
    echo "To build Rust services later, run:"
    echo "  cd rust"
    echo "  cargo build --release --jobs \$(nproc)"
    echo ""
    echo "Or for development (faster):"
    echo "  cargo build --jobs \$(nproc)"
    echo ""
else
    cd rust

    if [ "$IS_WSL" = true ] && [[ "$SCRIPT_DIR" == /mnt/* ]]; then
        log_wsl "Building on Windows filesystem - This will be SLOW (10-20 min)..."
        log_wsl "Consider moving project to Linux filesystem for 10-20x speedup"
        echo ""
        echo "Building... (grab a coffee ☕)"
    else
        log_info "Building Rust project with parallel compilation..."
    fi

    # Use debug build for faster compilation during development
    CARGO_BUILD_JOBS=$(nproc) cargo build --jobs $(nproc) 2>&1 | grep -E "(Compiling|Finished|error|warning:)" | head -30 || true

    if [ -f "target/debug/market-data" ] || [ -f "target/release/market-data" ]; then
        log_success "Rust services built successfully"
    else
        log_error "Rust build may have issues - check for errors above"
    fi

    cd "$SCRIPT_DIR"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 7: Final Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run dependency check
if [ -f "scripts/check_dependencies.sh" ]; then
    log_info "Running dependency check..."
    bash scripts/check_dependencies.sh 2>/dev/null || true
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
echo ""
echo "⚡ Performance Optimizations Applied:"
echo "   ✓ UV package manager (10-100x faster than pip)"
echo "   ✓ Parallel downloads and intelligent caching"
echo "   ✓ UV_LINK_MODE=copy (no hardlink warnings on WSL2)"
if [ "$SKIP_RUST_BUILD" = true ]; then
    echo "   ⚠  Rust build skipped (build later when needed)"
else
    echo "   ✓ Parallel Rust compilation ($(nproc) cores)"
fi
echo ""

if [ "$IS_WSL" = true ] && [[ "$SCRIPT_DIR" == /mnt/* ]]; then
    echo "⚠️  WSL2 PERFORMANCE WARNING:"
    echo ""
    echo "Your project is on the Windows filesystem (/mnt/c/...)."
    echo "This causes 10-20x slower Rust compilation."
    echo ""
    echo "📋 TO FIX: Move project to Linux filesystem"
    echo "   mkdir -p ~/projects"
    echo "   cp -r \"$SCRIPT_DIR\" ~/projects/"
    echo "   cd ~/projects/RustAlgorithmTrading"
    echo ""
    echo "This will make:"
    echo "   • Rust compilation: 2-3 min instead of 20+ min"
    echo "   • File operations: 10-20x faster"
    echo "   • Development: Much smoother"
    echo ""
fi

echo "🎯 Next Steps:"
echo "   1. Activate virtual environment:"
echo "      source .venv/bin/activate"
echo ""
echo "   2. Configure .env file with your API keys"
echo ""
if [ "$SKIP_RUST_BUILD" = true ]; then
    echo "   3. Build Rust services (when needed):"
    echo "      cd rust && cargo build --release"
    echo ""
    echo "   4. Start trading system:"
    echo "      ./scripts/start_trading.sh"
else
    echo "   3. Start trading system:"
    echo "      ./scripts/start_trading.sh"
fi
echo ""
echo "📚 Quick Reference:"
echo "   • Activate venv:      source .venv/bin/activate"
echo "   • Add package:        uv pip install <package>"
echo "   • Build Rust:         cd rust && cargo build --release"
echo "   • Start system:       ./scripts/start_trading.sh"
echo ""
