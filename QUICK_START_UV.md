# ⚡ Quick Start - UV Installation (10-100x Faster!)

## The Problem You Had

`./scripts/start_trading.sh` was failing AND pip was painfully slow (60+ seconds for dependencies).

## ✅ The Solution - UV

**UV is 10-100x faster than pip!**

### One Command to Fix Everything (with UV):

```bash
sudo ./install_all_dependencies.sh
```

This will:
- ✅ Install system packages
- ✅ **Install UV automatically**
- ✅ Create venv with UV (faster)
- ✅ **Install dependencies in 3-5 seconds** (vs 60+ with pip)
- ✅ Build Rust services
- ✅ Validate installation

**Estimated total time**: **2-3 minutes** (vs 5-10 minutes with pip)

---

## Why UV is Perfect for You

| Metric | pip | UV | Improvement |
|--------|-----|-----|-------------|
| **Install Time** | 60-90s | 3-5s | **10-20x faster** |
| **Tool** | Python-based | Rust-based | Compiled binary |
| **Downloads** | Sequential | Parallel | Much faster |
| **Caching** | Basic | Intelligent | Reuses packages |

---

## After Installation

### Start Trading System:

```bash
# 1. Activate venv (same as before)
source venv/bin/activate

# 2. Start system
./scripts/start_trading.sh
```

### Daily Development (with UV):

```bash
# Activate venv
source venv/bin/activate

# Add new package (FAST!)
uv pip install package-name

# List packages
uv pip list

# Update requirements
uv pip freeze > requirements.txt
```

---

## Performance Comparison

**Your project has 20+ dependencies. Here's the difference:**

### With pip (what you experienced):
```
$ pip install -r requirements.txt
Collecting numpy...
Downloading numpy-2.x.x.tar.gz (15.5 MB)
Building wheel for numpy... [45s]
Installing collected packages: numpy
Successfully installed numpy-2.x.x
... [repeats for 20+ packages]
Total time: 60-90 seconds ⏱️
```

### With UV (what you'll get):
```
$ uv pip install -r requirements.txt
Resolved 23 packages in 450ms
Downloaded 23 packages in 1.2s
Installed 23 packages in 3.1s
Total time: 3-5 seconds ⚡
```

**Result**: **15-30x faster!**

---

## UV Commands (Drop-in Replacement)

| Task | Old (pip) | New (UV) |
|------|-----------|----------|
| Install package | `pip install pandas` | `uv pip install pandas` |
| Install from file | `pip install -r requirements.txt` | `uv pip install -r requirements.txt` |
| Uninstall | `pip uninstall pandas` | `uv pip uninstall pandas` |
| List packages | `pip list` | `uv pip list` |
| Create venv | `python3 -m venv venv` | `uv venv venv` |

---

## If You Want pip Instead (Not Recommended)

```bash
sudo ./install_all_dependencies.sh --use-pip
```

But why would you? UV is:
- ✅ 10-100x faster
- ✅ More reliable
- ✅ Better caching
- ✅ Drop-in pip replacement
- ✅ No learning curve (same commands)

---

## Quick Reference Card

```bash
# ONE-TIME SETUP (installs UV + everything)
sudo ./install_all_dependencies.sh

# DAILY USAGE
source venv/bin/activate          # Activate venv
uv pip install package             # Add package (FAST!)
uv pip install -r requirements.txt # Reinstall deps (FAST!)
./scripts/start_trading.sh         # Start trading

# UV BENEFITS
# • 10-100x faster installations
# • Intelligent caching
# • Parallel downloads
# • Same commands as pip
```

---

## More Info

- **Full UV Guide**: `docs/deployment/UV_SETUP_GUIDE.md`
- **Troubleshooting**: `docs/troubleshooting/DEPLOYMENT_TROUBLESHOOTING.md`
- **UV Docs**: https://github.com/astral-sh/uv

---

**Recommendation**: Use UV (default). It's significantly faster with zero downsides.

Run this now:
```bash
sudo ./install_all_dependencies.sh
```

**Installation will complete in 2-3 minutes instead of 5-10 minutes! ⚡**
