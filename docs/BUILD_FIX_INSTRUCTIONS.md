# Quick Fix: Rust Build Dependencies

## Problem
The Rust workspace build fails due to missing system dependencies required by OpenSSL.

## Solution Options

### Option 1: Install System Dependencies (RECOMMENDED)

**Most straightforward and commonly used approach:**

```bash
# Update package list
sudo apt-get update

# Install required packages
sudo apt-get install -y pkg-config libssl-dev

# Verify installation
pkg-config --modversion openssl

# Clean and rebuild
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust
cargo clean
cargo build --workspace

# Run tests
cargo test --workspace
```

**Expected Result:** Build completes in ~4-5 minutes with all 5 crates successfully compiled.

---

### Option 2: Use Vendored OpenSSL (No sudo required)

**Compiles OpenSSL from source during build:**

Edit `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust/execution-engine/Cargo.toml`:

```toml
[dependencies]
# Change this line:
reqwest = { version = "0.12", features = ["json"] }

# To this:
reqwest = { version = "0.12", features = ["json", "native-tls-vendored"] }
```

Then rebuild:
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust
cargo clean
cargo build --workspace
```

**Note:** First build will take longer (~10-15 minutes) as it compiles OpenSSL from source.

---

### Option 3: Use Rustls (Pure Rust TLS)

**Eliminates OpenSSL dependency entirely:**

Edit `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust/execution-engine/Cargo.toml`:

```toml
[dependencies]
# Change this line:
reqwest = { version = "0.12", features = ["json"] }

# To this:
reqwest = { version = "0.12", features = ["json", "rustls-tls"], default-features = false }
```

Then rebuild:
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust
cargo clean
cargo build --workspace
```

**Pros:** No system dependencies, pure Rust implementation
**Cons:** Different TLS backend (usually not an issue)

---

## Verification Steps

After applying any solution:

1. **Verify Build Success:**
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust
cargo build --workspace --release
```

2. **Run All Tests:**
```bash
cargo test --workspace
```

3. **Check Binary Output:**
```bash
ls -lh target/release/
# Should show: market-data, signal-bridge, risk-manager, execution-engine
```

4. **Test Individual Binaries:**
```bash
./target/release/market-data --help
./target/release/execution-engine --help
./target/release/risk-manager --help
./target/release/signal-bridge --help
```

---

## Quick Reference

| Method | Pros | Cons | Build Time |
|--------|------|------|------------|
| System Deps | Fast, standard approach | Requires sudo | ~4 min |
| Vendored | No sudo needed | Slower first build | ~15 min |
| Rustls | Pure Rust, no deps | Different TLS impl | ~5 min |

---

## Common Issues

### Issue: "pkg-config not found" after install
**Solution:** Restart terminal or run `hash -r`

### Issue: "cannot find -lssl"
**Solution:** Ensure libssl-dev is installed, not just libssl3

### Issue: Build still fails with vendored
**Solution:** May need build-essential: `sudo apt-get install build-essential`

---

## Full Build + Test Script

```bash
#!/bin/bash
set -e

echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y pkg-config libssl-dev build-essential

echo "Navigating to workspace..."
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust

echo "Cleaning previous builds..."
cargo clean

echo "Building workspace..."
time cargo build --workspace

echo "Running tests..."
cargo test --workspace

echo "Building release binaries..."
time cargo build --workspace --release

echo "Build complete! Binaries in target/release/"
ls -lh target/release/ | grep -E "market-data|signal-bridge|risk-manager|execution-engine"
```

Save as `build.sh` and run with `bash build.sh`

---

**Recommendation:** Use Option 1 (system dependencies) unless you have specific constraints preventing sudo access.
