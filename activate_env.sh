#!/bin/bash
# Activate the project's virtual environment (.venv)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo "✅ Virtual environment activated (.venv)"
    echo ""
    echo "Python: $(which python)"
    echo "Python version: $(python --version)"
    echo ""
    echo "To deactivate: deactivate"
else
    echo "❌ Virtual environment not found at .venv"
    echo ""
    echo "Please run the installation script first:"
    echo "  sudo ./install_all_dependencies.sh"
    echo ""
    echo "Or for user-only installation:"
    echo "  ./install_all_dependencies.sh --user-only"
    exit 1
fi
