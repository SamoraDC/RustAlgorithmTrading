# 🚀 Quick Start Guide - Rust Algorithmic Trading System

## Problem: `./scripts/start_trading.sh` fails with dependency errors

### ✅ **SOLUTION (One-Time Setup)**

Run this **ONE COMMAND** to fix everything:

```bash
sudo ./install_all_dependencies.sh
```

This will:
1. ✅ Install system packages (jq, python3-venv, build tools)
2. ✅ Create Python virtual environment
3. ✅ Install all Python dependencies
4. ✅ Build Rust services
5. ✅ Validate installation

---

## 🎯 After Installation

### **Every time you open a new terminal:**

```bash
# Activate the virtual environment
source venv/bin/activate
```

### **Start the trading system:**

```bash
./scripts/start_trading.sh
```

---

## 📋 What Was Fixed

The Hive Mind identified and fixed **3 critical issues**:

### 1. **Dependency Check Script** ✅
- **Issue**: Optional dependency `jq` was causing hard failure
- **Fix**: Script now properly handles optional vs required dependencies
- **Impact**: Deployment proceeds with warnings instead of failures

### 2. **Python Virtual Environment** ✅
- **Issue**: Python 3.12+ requires venv for package installation
- **Fix**: Automated venv creation in `install_all_dependencies.sh`
- **Impact**: Clean, isolated Python environment

### 3. **Startup Script** ✅
- **Issue**: No comprehensive error handling or validation
- **Fix**: Enhanced with health checks, retries, graceful shutdown
- **Impact**: Robust production-ready startup sequence

---

## 🛠️ Alternative: Manual Installation

If you prefer to install step-by-step:

```bash
# 1. Install system packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3.12-venv \\
    build-essential pkg-config libssl-dev curl git jq

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Build Rust services
cd rust
cargo build --release
cd ..

# 5. Start trading system
./scripts/start_trading.sh
```

---

## 🚀 Ready to Trade!

You're now ready to start the algorithmic trading system:

```bash
source venv/bin/activate
./scripts/start_trading.sh
```

**Happy Trading! 📈**
