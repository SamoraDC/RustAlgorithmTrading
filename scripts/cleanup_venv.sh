#!/bin/bash
# Cleanup duplicate virtual environments and consolidate to .venv

set -e

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

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        Virtual Environment Cleanup & Consolidation            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$SCRIPT_DIR"

# Check for duplicate venv directories
FOUND_VENV=false
FOUND_DOTVENV=false

if [ -d "venv" ]; then
    FOUND_VENV=true
    VENV_SIZE=$(du -sh venv 2>/dev/null | cut -f1)
    log_info "Found 'venv/' directory (size: $VENV_SIZE)"
fi

if [ -d ".venv" ]; then
    FOUND_DOTVENV=true
    DOTVENV_SIZE=$(du -sh .venv 2>/dev/null | cut -f1)
    log_info "Found '.venv/' directory (size: $DOTVENV_SIZE)"
fi

# If neither exists, exit
if [ "$FOUND_VENV" = false ] && [ "$FOUND_DOTVENV" = false ]; then
    log_info "No virtual environments found. Nothing to clean up."
    exit 0
fi

# If both exist, warn and ask for confirmation
if [ "$FOUND_VENV" = true ] && [ "$FOUND_DOTVENV" = true ]; then
    echo ""
    log_error "⚠️  DUPLICATE VIRTUAL ENVIRONMENTS DETECTED!"
    echo ""
    echo "This is wasting disk space and can cause confusion."
    echo ""
    echo "Found:"
    echo "  • venv/  - $VENV_SIZE"
    echo "  • .venv/ - $DOTVENV_SIZE"
    echo ""
    echo "Recommended action: Keep .venv and remove venv"
    echo ""

    read -p "Remove 'venv/' directory and keep '.venv/'? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing venv/ directory..."
        rm -rf venv
        log_success "Removed venv/ directory"
        log_success "Now using .venv exclusively"
    else
        log_info "Cleanup cancelled. Manual intervention required."
        exit 0
    fi
elif [ "$FOUND_VENV" = true ]; then
    # Only venv exists, rename to .venv
    echo ""
    log_info "Found only 'venv/' directory"
    log_info "Renaming to '.venv' (Python community standard)..."
    mv venv .venv
    log_success "Renamed venv to .venv"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║               Virtual Environment Cleanup Complete             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Using .venv exclusively"
echo ""
echo "To activate:"
echo "  source .venv/bin/activate"
echo ""
echo "To add packages:"
echo "  uv pip install <package-name>"
echo ""
