#!/bin/bash
# Automated dependency installation script
# Supports: Ubuntu, WSL, macOS

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}\n"
}

# Detect platform
detect_platform() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if grep -qi microsoft /proc/version; then
            PLATFORM="WSL"
        else
            PLATFORM="Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macOS"
    else
        PLATFORM="Unknown"
    fi

    print_info "Detected platform: $PLATFORM"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies on Ubuntu/WSL
install_ubuntu_deps() {
    print_header "Installing System Dependencies (Ubuntu/WSL)"

    print_info "Updating package lists..."
    sudo apt-get update -qq

    print_info "Installing required packages..."
    sudo apt-get install -y \
        python3 \
        python3-pip \
        curl \
        build-essential \
        pkg-config \
        libssl-dev \
        git \
        jq \
        >/dev/null 2>&1

    print_success "System dependencies installed"
}

# Install system dependencies on macOS
install_macos_deps() {
    print_header "Installing System Dependencies (macOS)"

    # Check if Homebrew is installed
    if ! command_exists brew; then
        print_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        print_success "Homebrew already installed"
    fi

    print_info "Installing required packages..."
    brew install python3 curl jq pkg-config openssl git >/dev/null 2>&1

    print_success "System dependencies installed"
}

# Install Rust
install_rust() {
    print_header "Installing Rust"

    if command_exists cargo && command_exists rustc; then
        print_success "Rust already installed"
        rustc --version
        cargo --version
    else
        print_info "Installing Rust via rustup..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y >/dev/null 2>&1

        # Load cargo env
        source "$HOME/.cargo/env"

        # Add to shell profile
        if [[ -f "$HOME/.bashrc" ]]; then
            echo 'source "$HOME/.cargo/env"' >> "$HOME/.bashrc"
        fi
        if [[ -f "$HOME/.zshrc" ]]; then
            echo 'source "$HOME/.cargo/env"' >> "$HOME/.zshrc"
        fi

        print_success "Rust installed successfully"
        rustc --version
        cargo --version
    fi
}

# Install Node.js and npm
install_nodejs() {
    print_header "Installing Node.js and npm"

    if command_exists node && command_exists npm; then
        print_success "Node.js already installed"
        node --version
        npm --version
    else
        if [[ "$PLATFORM" == "WSL" ]] || [[ "$PLATFORM" == "Linux" ]]; then
            print_info "Installing Node.js via NodeSource..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - >/dev/null 2>&1
            sudo apt-get install -y nodejs >/dev/null 2>&1
        elif [[ "$PLATFORM" == "macOS" ]]; then
            print_info "Installing Node.js via Homebrew..."
            brew install node >/dev/null 2>&1
        fi

        print_success "Node.js installed successfully"
        node --version
        npm --version
    fi
}

# Install Python dependencies
install_python_deps() {
    print_header "Installing Python Dependencies"

    # Check if requirements.txt exists
    if [[ ! -f "requirements.txt" ]]; then
        print_warning "requirements.txt not found, skipping Python dependencies"
        return
    fi

    print_info "Upgrading pip..."
    pip3 install --upgrade pip >/dev/null 2>&1

    print_info "Installing Python packages from requirements.txt..."
    pip3 install -r requirements.txt >/dev/null 2>&1

    print_success "Python dependencies installed"
}

# Install Claude Flow MCP
install_claude_flow() {
    print_header "Installing Claude Flow MCP"

    if command_exists claude-flow; then
        print_success "Claude Flow already installed"
        npm list -g claude-flow 2>/dev/null || true
    else
        print_info "Installing Claude Flow globally..."

        # Setup npm global directory for non-root installs
        if [[ "$PLATFORM" == "WSL" ]] || [[ "$PLATFORM" == "Linux" ]]; then
            mkdir -p "$HOME/.npm-global"
            npm config set prefix "$HOME/.npm-global"

            # Add to PATH
            if [[ -f "$HOME/.bashrc" ]]; then
                echo 'export PATH=~/.npm-global/bin:$PATH' >> "$HOME/.bashrc"
            fi
            if [[ -f "$HOME/.zshrc" ]]; then
                echo 'export PATH=~/.npm-global/bin:$PATH' >> "$HOME/.zshrc"
            fi

            export PATH="$HOME/.npm-global/bin:$PATH"
        fi

        npm install -g claude-flow@alpha >/dev/null 2>&1

        print_success "Claude Flow installed successfully"
    fi
}

# Verify installations
verify_installations() {
    print_header "Verifying Installations"

    local all_good=true

    # System dependencies
    print_info "Checking system dependencies..."

    if command_exists python3; then
        print_success "python3: $(python3 --version 2>&1)"
    else
        print_error "python3 not found"
        all_good=false
    fi

    if command_exists pip3; then
        print_success "pip3: $(pip3 --version 2>&1 | head -n1)"
    else
        print_error "pip3 not found"
        all_good=false
    fi

    if command_exists cargo; then
        print_success "cargo: $(cargo --version 2>&1)"
    else
        print_error "cargo not found"
        all_good=false
    fi

    if command_exists rustc; then
        print_success "rustc: $(rustc --version 2>&1)"
    else
        print_error "rustc not found"
        all_good=false
    fi

    if command_exists curl; then
        print_success "curl: $(curl --version 2>&1 | head -n1)"
    else
        print_error "curl not found"
        all_good=false
    fi

    if command_exists jq; then
        print_success "jq: $(jq --version 2>&1)"
    else
        print_warning "jq not found (optional)"
    fi

    if command_exists git; then
        print_success "git: $(git --version 2>&1)"
    else
        print_error "git not found"
        all_good=false
    fi

    if command_exists node; then
        print_success "node: $(node --version 2>&1)"
    else
        print_warning "node not found (optional)"
    fi

    if command_exists npm; then
        print_success "npm: $(npm --version 2>&1)"
    else
        print_warning "npm not found (optional)"
    fi

    # Python packages
    print_info "\nChecking Python packages..."

    for pkg in numpy pandas ccxt python-dotenv; do
        if pip3 show "$pkg" >/dev/null 2>&1; then
            version=$(pip3 show "$pkg" 2>/dev/null | grep "Version:" | awk '{print $2}')
            print_success "$pkg: $version"
        else
            print_warning "$pkg not found"
        fi
    done

    # Rust project check
    if [[ -d "rust" ]]; then
        print_info "\nChecking Rust project..."
        cd rust
        if cargo check >/dev/null 2>&1; then
            print_success "Rust project compiles successfully"
        else
            print_warning "Rust project has compilation issues"
        fi
        cd ..
    fi

    if [[ "$all_good" == true ]]; then
        print_success "\nAll critical dependencies installed successfully!"
    else
        print_warning "\nSome dependencies are missing. Please review the errors above."
    fi
}

# Main installation flow
main() {
    print_header "Rust Algorithm Trading - Dependency Installer"

    # Detect platform
    detect_platform

    # Check if we should skip certain steps
    SKIP_SYSTEM=false
    SKIP_RUST=false
    SKIP_NODE=false
    SKIP_PYTHON=false
    SKIP_CLAUDE=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-system)
                SKIP_SYSTEM=true
                shift
                ;;
            --skip-rust)
                SKIP_RUST=true
                shift
                ;;
            --skip-node)
                SKIP_NODE=true
                shift
                ;;
            --skip-python)
                SKIP_PYTHON=true
                shift
                ;;
            --skip-claude)
                SKIP_CLAUDE=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-system    Skip system dependencies"
                echo "  --skip-rust      Skip Rust installation"
                echo "  --skip-node      Skip Node.js installation"
                echo "  --skip-python    Skip Python dependencies"
                echo "  --skip-claude    Skip Claude Flow installation"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Install system dependencies
    if [[ "$SKIP_SYSTEM" == false ]]; then
        if [[ "$PLATFORM" == "WSL" ]] || [[ "$PLATFORM" == "Linux" ]]; then
            install_ubuntu_deps
        elif [[ "$PLATFORM" == "macOS" ]]; then
            install_macos_deps
        else
            print_error "Unsupported platform: $PLATFORM"
            exit 1
        fi
    fi

    # Install Rust
    if [[ "$SKIP_RUST" == false ]]; then
        install_rust
    fi

    # Install Node.js
    if [[ "$SKIP_NODE" == false ]]; then
        install_nodejs
    fi

    # Install Python dependencies
    if [[ "$SKIP_PYTHON" == false ]]; then
        install_python_deps
    fi

    # Install Claude Flow
    if [[ "$SKIP_CLAUDE" == false ]]; then
        install_claude_flow
    fi

    # Verify installations
    verify_installations

    print_header "Installation Complete"
    print_info "Next steps:"
    echo "  1. Restart your terminal or run: source ~/.bashrc"
    echo "  2. Run ./scripts/check_dependencies.sh to verify"
    echo "  3. Configure your .env file"
    echo "  4. Run ./scripts/start_trading.sh to start the system"
}

# Run main function
main "$@"
