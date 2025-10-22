# Dependency Installation Guide

Quick-fix guide for installing all required dependencies on various platforms.

## 🚀 Quick Fix (Current Issue)

If you're seeing "jq: command not found" on WSL/Ubuntu:

```bash
# Install jq on WSL/Ubuntu
sudo apt-get update
sudo apt-get install -y jq

# Verify installation
jq --version
# Expected output: jq-1.6 or higher
```

## ⚡ One-Command Install (Ubuntu/WSL)

Install all required dependencies with a single command:

```bash
# Install all system dependencies
sudo apt-get update && sudo apt-get install -y \
  python3 python3-pip curl build-essential jq \
  pkg-config libssl-dev git

# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Install Python dependencies
pip3 install -r requirements.txt

# Verify all installations
./scripts/check_dependencies.sh
```

## 📋 Required Dependencies

### System Dependencies

| Dependency | Purpose | Min Version |
|------------|---------|-------------|
| **python3** | Core runtime | 3.8+ |
| **pip3** | Python package manager | 20.0+ |
| **cargo** | Rust build tool | 1.70+ |
| **rustc** | Rust compiler | 1.70+ |
| **curl** | HTTP client | 7.68+ |
| **build-essential** | Compilation tools | Latest |
| **pkg-config** | Package configuration | Latest |
| **libssl-dev** | SSL/TLS library | 1.1.1+ |
| **git** | Version control | 2.25+ |

### Optional Dependencies

| Dependency | Purpose | Min Version |
|------------|---------|-------------|
| **jq** | JSON parsing in scripts | 1.6+ |
| **docker** | Containerization | 20.10+ |
| **docker-compose** | Multi-container orchestration | 2.0+ |

### Python Packages

All Python dependencies are listed in `requirements.txt`:
- numpy
- pandas
- ccxt (cryptocurrency exchange library)
- python-dotenv
- fastapi (if using REST API)
- uvicorn (ASGI server)
- pytest (testing)
- pytest-asyncio (async testing)

### Rust Dependencies

Managed by Cargo in `rust/Cargo.toml`:
- tokio (async runtime)
- serde (serialization)
- reqwest (HTTP client)
- anyhow (error handling)
- And more...

## 🖥️ Platform-Specific Instructions

### Ubuntu/WSL (Recommended)

#### 1. Update Package Lists
```bash
sudo apt-get update
```

#### 2. Install System Dependencies
```bash
sudo apt-get install -y \
  python3 python3-pip \
  curl build-essential \
  pkg-config libssl-dev \
  git jq
```

#### 3. Install Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Verify installation
rustc --version
cargo --version
```

#### 4. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

#### 5. Install Node.js and npm (for Claude Flow)
```bash
# Install Node.js 18+ via NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

#### 6. Install Claude Flow MCP
```bash
npm install -g claude-flow@alpha
```

### macOS

#### 1. Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install System Dependencies
```bash
brew install python3 rust curl jq pkg-config openssl git
```

#### 3. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

#### 4. Install Node.js and npm
```bash
brew install node
```

#### 5. Install Claude Flow MCP
```bash
npm install -g claude-flow@alpha
```

### Windows (Native - Not WSL)

#### 1. Install Python
Download and install from [python.org](https://www.python.org/downloads/)

#### 2. Install Rust
Download and run rustup from [rustup.rs](https://rustup.rs/)

#### 3. Install Visual Studio Build Tools
Required for Rust compilation:
- Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/)
- Select "Desktop development with C++"

#### 4. Install jq (Optional)
Download from [stedolan.github.io/jq](https://stedolan.github.io/jq/download/)

#### 5. Install Node.js
Download from [nodejs.org](https://nodejs.org/)

#### 6. Install Python Dependencies
```cmd
pip install -r requirements.txt
```

#### 7. Install Claude Flow MCP
```cmd
npm install -g claude-flow@alpha
```

## ✅ Verification Commands

Run these commands to verify all dependencies are installed correctly:

### System Dependencies
```bash
# Python
python3 --version
pip3 --version

# Rust
rustc --version
cargo --version

# Other tools
curl --version
jq --version
git --version

# Node.js
node --version
npm --version
```

### Python Packages
```bash
pip3 list | grep -E "(numpy|pandas|ccxt|dotenv|fastapi|uvicorn|pytest)"
```

### Rust Dependencies
```bash
cd rust
cargo check
```

### Automated Verification
```bash
# Run the automated dependency checker
./scripts/check_dependencies.sh

# Expected output: All checks should pass with ✓
```

## 🔧 Troubleshooting

### Issue: "jq: command not found"

**Solution:**
```bash
sudo apt-get update
sudo apt-get install -y jq
```

### Issue: "cargo: command not found" after installing Rust

**Solution:**
```bash
# Reload shell environment
source "$HOME/.cargo/env"

# Add to .bashrc or .zshrc for persistence
echo 'source "$HOME/.cargo/env"' >> ~/.bashrc
```

### Issue: "pip3: command not found"

**Solution (Ubuntu/WSL):**
```bash
sudo apt-get update
sudo apt-get install -y python3-pip
```

**Solution (macOS):**
```bash
python3 -m ensurepip --upgrade
```

### Issue: Rust compilation fails with SSL errors

**Solution:**
```bash
# Install SSL development libraries
sudo apt-get install -y pkg-config libssl-dev
```

### Issue: Python package installation fails

**Solution:**
```bash
# Upgrade pip
pip3 install --upgrade pip

# Install packages with user flag
pip3 install --user -r requirements.txt
```

### Issue: "Permission denied" when running scripts

**Solution:**
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### Issue: npm install fails with permission errors

**Solution (Ubuntu/WSL):**
```bash
# Use npm's built-in solution
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Retry installation
npm install -g claude-flow@alpha
```

### Issue: Docker not found (optional dependency)

**Solution (Ubuntu/WSL):**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install -y docker-compose
```

## 🚀 Quick Start Script

Use the automated installation script:

```bash
# Make script executable
chmod +x scripts/install_dependencies.sh

# Run installation script
./scripts/install_dependencies.sh

# The script will:
# - Auto-detect your platform
# - Install all required dependencies
# - Verify installations
# - Print a summary report
```

## 📦 Minimal Installation (Core Only)

If you only need the core trading system without development tools:

```bash
# System dependencies
sudo apt-get update && sudo apt-get install -y \
  python3 python3-pip curl build-essential

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Python packages (core only)
pip3 install numpy pandas ccxt python-dotenv
```

## 🔄 Updating Dependencies

### Update System Packages
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### Update Rust
```bash
rustup update stable
```

### Update Python Packages
```bash
pip3 install --upgrade -r requirements.txt
```

### Update Node.js Packages
```bash
npm update -g
```

### Update Claude Flow
```bash
npm update -g claude-flow@alpha
```

## 📊 Dependency Check Summary

After installation, verify everything with:

```bash
./scripts/check_dependencies.sh
```

Expected output:
```
Checking system dependencies...
✓ python3 found: Python 3.10.12
✓ pip3 found: pip 22.0.2
✓ cargo found: cargo 1.75.0
✓ rustc found: rustc 1.75.0
✓ curl found: curl 7.81.0
✓ jq found: jq-1.6
✓ git found: git version 2.34.1

Checking Python packages...
✓ numpy found: 1.24.3
✓ pandas found: 2.0.3
✓ ccxt found: 4.1.0
✓ python-dotenv found: 1.0.0

Checking Rust dependencies...
✓ Rust project compiles successfully

All dependencies are installed correctly!
```

## 🆘 Getting Help

If you encounter issues not covered here:

1. Check the main [README.md](/README.md) for project-specific setup
2. Review error messages carefully
3. Check platform-specific documentation
4. Create an issue on GitHub with:
   - Your platform (OS, version)
   - Error message
   - Output of `./scripts/check_dependencies.sh`

## 📚 Additional Resources

- [Rust Installation Guide](https://www.rust-lang.org/tools/install)
- [Python Installation Guide](https://www.python.org/downloads/)
- [Node.js Installation Guide](https://nodejs.org/en/download/)
- [Claude Flow Documentation](https://github.com/ruvnet/claude-flow)
- [WSL Setup Guide](https://docs.microsoft.com/en-us/windows/wsl/install)
