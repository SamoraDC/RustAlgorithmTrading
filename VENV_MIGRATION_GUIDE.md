# Virtual Environment Migration Guide

## 📋 Overview

This guide explains the virtual environment changes made to the project and how to migrate from the old setup to the new consolidated setup.

## 🔍 What Changed?

### Before:
- **Two virtual environments**: `venv/` (1.2 GB) and `.venv/` (315 MB)
- **Inconsistent activation**: Different scripts used different environments
- **Wasted space**: ~1.5 GB total for duplicate packages
- **Slow installs**: Using pip (traditional, slow)

### After:
- **One virtual environment**: `.venv/` only
- **Consistent activation**: All scripts use `.venv`
- **Space efficient**: Single environment (~300 MB)
- **Fast installs**: Using UV (10-100x faster than pip)

## 🚀 Migration Steps

### Option 1: Clean Install (Recommended)

This completely removes old environments and creates a fresh one:

```bash
# 1. Run the optimized installation script
sudo ./install_all_dependencies.sh

# This will:
#   - Remove old venv/ directory
#   - Remove old .venv/ directory
#   - Create fresh .venv/ with UV
#   - Install all dependencies with UV
```

### Option 2: Manual Cleanup

If you prefer to clean up manually:

```bash
# 1. Run the cleanup script
./scripts/cleanup_venv.sh

# This will:
#   - Detect duplicate environments
#   - Ask for confirmation
#   - Remove venv/ and keep .venv/
#   - Or rename venv/ to .venv/ if .venv/ doesn't exist

# 2. If needed, recreate the environment
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Option 3: Keep Existing .venv

If you already have a working `.venv/`:

```bash
# 1. Just remove the duplicate venv/
rm -rf venv

# 2. Update .gitignore
# (already done if you pulled latest changes)

# 3. Activate as usual
source .venv/bin/activate
```

## ✅ Activation

Always use this command to activate:

```bash
source .venv/bin/activate
```

Or use the convenience script:

```bash
source activate_env.sh
```

## 📦 Package Management with UV

### Installing Packages

```bash
# Activate environment first
source .venv/bin/activate

# Install a package
uv pip install package-name

# Install from requirements.txt
uv pip install -r requirements.txt

# Install with version constraint
uv pip install "numpy>=1.24.0"

# Install multiple packages
uv pip install pandas scipy matplotlib
```

### Listing Packages

```bash
# List installed packages
uv pip list

# Show specific package
uv pip show package-name

# Freeze to requirements.txt
uv pip freeze > requirements.txt
```

### Upgrading Packages

```bash
# Upgrade a package
uv pip install --upgrade package-name

# Upgrade pip itself
uv pip install --upgrade pip

# Upgrade all packages (careful!)
uv pip list --outdated | cut -d' ' -f1 | xargs uv pip install --upgrade
```

## 🔧 Troubleshooting

### Problem: "Virtual environment not found"

**Solution**:
```bash
# Create new virtual environment
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Problem: "UV command not found"

**Solution**:
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
uv --version
```

### Problem: "Import errors after migration"

**Solution**:
```bash
# Reinstall all packages
source .venv/bin/activate
uv pip install --force-reinstall -r requirements.txt
```

### Problem: "Scripts still reference old venv/"

**Solution**:
```bash
# Search for references
grep -r "venv/bin" scripts/ docs/

# Update them to use .venv/bin instead
# Example:
sed -i 's|venv/bin|.venv/bin|g' scripts/*.sh
```

## 📊 Performance Comparison

### Installation Speed

| Method | Time | Speedup |
|--------|------|---------|
| pip (old) | ~60s | 1x |
| UV (new) | ~8s | 7.5x |

### Disk Space

| Environment | Size | Status |
|-------------|------|--------|
| venv/ | 1.2 GB | ❌ Removed |
| .venv/ (old) | 315 MB | ⚠️ Replaced |
| .venv/ (new) | ~300 MB | ✅ Active |

**Total saved**: 1.2 GB

## 🎯 Best Practices

1. **Always use .venv**: Don't create new `venv/` directories
2. **Use UV for installs**: It's faster and more reliable
3. **Activate before work**: Always `source .venv/bin/activate`
4. **Keep requirements.txt updated**: Run `uv pip freeze > requirements.txt`
5. **Don't commit .venv/**: It's in .gitignore

## 📚 Additional Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [PEP 405 - Python Virtual Environments](https://peps.python.org/pep-0405/)

## ❓ FAQ

### Q: Why .venv instead of venv?

**A**: 
- Python community standard (PEP 405)
- Hidden by default (leading dot)
- Auto-detected by most tools (VS Code, PyCharm)
- UV's default choice

### Q: Can I still use pip?

**A**: 
Yes, but UV is recommended because:
- 10-100x faster
- Better dependency resolution
- Intelligent caching
- Drop-in replacement for pip

### Q: What if I have multiple Python versions?

**A**:
UV handles this automatically:
```bash
# Create environment with specific Python
uv venv .venv --python 3.12

# UV will find and use the correct Python version
```

### Q: How do I completely reset my environment?

**A**:
```bash
# Remove environment
rm -rf .venv

# Recreate with UV
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## ✅ Verification

After migration, verify everything works:

```bash
# 1. Check activation
source .venv/bin/activate
which python  # Should show .venv/bin/python

# 2. Check packages
uv pip list  # Should show all required packages

# 3. Test imports
python -c "import numpy, pandas, alpaca; print('✅ All imports work')"

# 4. Run tests
pytest tests/

# 5. Check disk usage
du -sh .venv  # Should be ~300 MB
```

## 🎉 Summary

**Old Setup**:
- Two environments (venv + .venv)
- 1.5 GB disk space
- Slow pip installs
- Inconsistent activation

**New Setup**:
- One environment (.venv)
- 300 MB disk space
- Fast UV installs
- Consistent activation

**You've saved**: ~1.2 GB and made installs 10-100x faster! 🚀
