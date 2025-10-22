# ⚡ UV Setup Guide - Ultra-Fast Python Package Management

## Why UV?

**UV is 10-100x faster than pip** with these benefits:

- 🚀 **10-100x faster** package installation
- 📦 **Intelligent caching** - reuses downloaded packages
- ⚡ **Parallel downloads** - installs multiple packages simultaneously
- 🔄 **Drop-in replacement** - works with requirements.txt
- 🎯 **Rust-based** - compiled binary, not Python script

## Installation Performance Comparison

| Tool | Time to Install | Speed |
|------|----------------|-------|
| **pip** | 45-90 seconds | Baseline (1x) |
| **UV** | 2-5 seconds | **10-100x faster** |

For this project's requirements.txt (20+ packages), UV typically completes in **under 5 seconds** vs pip's **60+ seconds**.

---

## Quick Start with UV

### 1. Install Dependencies (Automatic UV Installation)

```bash
sudo ./install_all_dependencies.sh
```

This automatically:
- ✅ Installs UV
- ✅ Creates venv with UV
- ✅ Installs all packages with UV

### 2. Manual UV Installation (if needed)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.bashrc for persistence)
export PATH="$HOME/.cargo/bin:$PATH"

# Verify installation
uv --version
```

### 3. Using UV (Drop-in pip replacement)

```bash
# Create virtual environment
uv venv venv
source venv/bin/activate

# Install from requirements.txt (FAST!)
uv pip install -r requirements.txt

# Install single package
uv pip install numpy

# Install with version
uv pip install pandas==2.0.0

# Upgrade package
uv pip install --upgrade fastapi

# List installed packages
uv pip list

# Uninstall package
uv pip uninstall ccxt
```

---

## Using UV in This Project

### Daily Workflow

```bash
# 1. Activate virtual environment (same as before)
source venv/bin/activate

# 2. Install new package (use UV instead of pip)
uv pip install new-package

# 3. Update requirements.txt
uv pip freeze > requirements.txt

# 4. Install from requirements.txt
uv pip install -r requirements.txt
```

### Adding New Dependencies

```bash
# Traditional way (SLOW)
pip install requests

# UV way (FAST!)
uv pip install requests

# Update requirements.txt
uv pip freeze > requirements.txt
```

---

## UV vs Pip Command Mapping

| pip command | uv equivalent |
|-------------|---------------|
| `pip install package` | `uv pip install package` |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` |
| `pip uninstall package` | `uv pip uninstall package` |
| `pip list` | `uv pip list` |
| `pip freeze` | `uv pip freeze` |
| `pip show package` | `uv pip show package` |
| `python -m venv venv` | `uv venv venv` |

---

## Force Using Pip (if needed)

If you prefer pip for some reason:

```bash
# Install with pip instead
sudo ./install_all_dependencies.sh --use-pip
```

Or manually:
```bash
pip install -r requirements.txt
```

---

## Troubleshooting

### UV command not found after installation

```bash
# Add UV to PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Make permanent (add to ~/.bashrc)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### UV installation failed

```bash
# Fallback to pip
sudo ./install_all_dependencies.sh --use-pip
```

### Check UV cache location

```bash
# UV cache is at ~/.cache/uv
du -sh ~/.cache/uv  # Check cache size
```

### Clear UV cache (if needed)

```bash
# Clear cache to free disk space
rm -rf ~/.cache/uv
```

---

## Advanced UV Features

### Install from GitHub

```bash
uv pip install git+https://github.com/user/repo.git
```

### Install with extras

```bash
uv pip install fastapi[all]
```

### Install from local directory

```bash
uv pip install -e ./my-package
```

### Sync dependencies (install exact versions)

```bash
uv pip sync requirements.txt
```

---

## Performance Tips

1. **Use UV for all installations** - Significantly faster
2. **Keep UV cache** - Speeds up reinstallations
3. **Use requirements.txt** - UV can parallelize installations
4. **Update UV regularly** - `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## UV Configuration

UV respects standard Python/pip configurations:

- `requirements.txt` - Package list
- `setup.py` / `pyproject.toml` - Project metadata
- `.env` files - Environment variables
- `pip.conf` - pip configuration (UV compatible)

---

## Why UV is Perfect for Trading Systems

1. **Fast Deployment** - Critical for time-sensitive trading systems
2. **Reliable** - Rust-based, fewer errors than pip
3. **Efficient** - Lower resource usage during installation
4. **Compatible** - Works with existing pip workflows

---

## Migration from Pip to UV

Already using pip? Switch to UV:

```bash
# 1. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create new venv with UV
uv venv venv
source venv/bin/activate

# 3. Install existing requirements
uv pip install -r requirements.txt

# Done! Same packages, 10-100x faster
```

---

## Quick Reference Card

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv
uv venv venv && source venv/bin/activate

# Install dependencies (FAST!)
uv pip install -r requirements.txt

# Add new package
uv pip install package-name

# Update requirements
uv pip freeze > requirements.txt

# Start trading system
./scripts/start_trading.sh
```

---

## Support

- **UV Documentation**: https://github.com/astral-sh/uv
- **Issues**: https://github.com/astral-sh/uv/issues
- **This Project**: See `docs/troubleshooting/DEPLOYMENT_TROUBLESHOOTING.md`

---

**Recommendation**: Use UV for all Python package management in this project for **significantly faster** development and deployment cycles.
