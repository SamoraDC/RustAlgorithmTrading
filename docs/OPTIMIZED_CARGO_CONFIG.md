# Optimized Cargo Configuration

## Recommended Cargo.toml Updates

### 1. Workspace Cargo.toml

Replace the `[profile.release]` section in `/rust/Cargo.toml`:

```toml
[profile.release]
# Maximum optimization level
opt-level = 3

# Thin LTO for faster compilation, or "fat" for maximum optimization
# Use "fat" for production builds, "thin" for development
lto = "thin"  # Change to "fat" for production

# Single codegen unit for best optimization (slower compile, faster runtime)
codegen-units = 1

# Strip symbols to reduce binary size
strip = true

# Abort on panic (removes unwinding overhead, ~10% perf gain)
panic = "abort"

# Disable overflow checks in release (trading correctness for speed)
# Only enable if you're confident in your arithmetic
overflow-checks = false

# Disable debug assertions in release
debug-assertions = false

# Incremental compilation (disable for release builds)
incremental = false
```

### 2. Build Configuration (.cargo/config.toml)

Create `/rust/.cargo/config.toml`:

```toml
[build]
# Use lld linker for faster linking
rustflags = [
    "-C", "link-arg=-fuse-ld=lld",
    "-C", "target-cpu=native",           # Use CPU-specific optimizations
    "-C", "target-feature=+avx2,+fma",   # Enable AVX2 and FMA instructions
]

[target.x86_64-unknown-linux-gnu]
rustflags = [
    "-C", "link-arg=-fuse-ld=lld",
    "-C", "target-cpu=native",
    "-C", "target-feature=+avx2,+fma",
]

[target.x86_64-pc-windows-msvc]
rustflags = [
    "-C", "target-cpu=native",
    "-C", "target-feature=+avx2,+fma",
]

[profile.release]
# Additional release profile settings
lto = "fat"
codegen-units = 1
```

### 3. Performance-Critical Dependencies

Add these to `/rust/Cargo.toml` workspace dependencies:

```toml
[workspace.dependencies]
# Existing dependencies...

# Zero-copy JSON with SIMD
simd-json = "0.13"

# Fast binary serialization (5-10x faster than JSON)
bincode = "1.3"
rmp-serde = "1.1"

# Lock-free data structures
crossbeam-channel = "0.5"
crossbeam-skiplist = "0.1"
crossbeam-queue = "0.3"

# Faster locks
parking_lot = "0.12"

# High-resolution latency histograms
hdrhistogram = "7.5"

# CPU affinity for thread pinning
core_affinity = "0.8"

# Stack-allocated vectors
smallvec = { version = "1.11", features = ["union", "const_generics"] }

# Faster hashing (2-3x faster than SipHash)
ahash = "0.8"

# Better allocator
tikv-jemallocator = "0.5"
# Alternative: mimalloc = "0.1"

# Memory profiling
dhat = "0.3"

# SIMD operations
wide = "0.7"
```

### 4. Per-Crate Optimizations

#### market-data/Cargo.toml
```toml
[dependencies]
common = { path = "../common" }

# Performance-critical
simd-json.workspace = true
crossbeam-channel.workspace = true
parking_lot.workspace = true
ahash.workspace = true

# Existing dependencies...
tokio.workspace = true
# ... rest
```

#### common/Cargo.toml
```toml
[dependencies]
# Replace JSON with binary serialization
bincode.workspace = true
rmp-serde.workspace = true
smallvec.workspace = true

# Keep serde but optimize
serde = { workspace = true, features = ["derive", "rc"] }

# ... rest
```

#### execution-engine/Cargo.toml
```toml
[dependencies]
common = { path = "../common" }

# Connection pooling
reqwest = { version = "0.12", features = ["json", "stream"] }

# Rate limiting
governor.workspace = true
parking_lot.workspace = true

# ... rest
```

### 5. Benchmark Configuration

Add to `/rust/Cargo.toml`:

```toml
[profile.bench]
inherits = "release"
debug = true  # Keep debug symbols for flamegraphs
```

### 6. Development Profile (Fast Compile)

```toml
[profile.dev]
opt-level = 1          # Some optimization for faster dev builds
debug = true
incremental = true
```

### 7. Custom Allocator

In each binary crate's `main.rs`:

```rust
// Option 1: jemalloc (better for multi-threaded)
use tikv_jemallocator::Jemalloc;

#[global_allocator]
static GLOBAL: Jemalloc = Jemalloc;

// Option 2: mimalloc (better for single-threaded)
// use mimalloc::MiMalloc;
//
// #[global_allocator]
// static GLOBAL: MiMalloc = MiMalloc;
```

---

## Build Commands

### Standard Release Build
```bash
cd rust
cargo build --release
```

### Maximum Performance Build
```bash
cd rust
RUSTFLAGS="-C target-cpu=native -C link-arg=-fuse-ld=lld" \
cargo build --release
```

### Profile-Guided Optimization (PGO)

#### Step 1: Build instrumented binary
```bash
RUSTFLAGS="-C profile-generate=/tmp/pgo-data" \
cargo build --release --package market-data
```

#### Step 2: Run representative workload
```bash
# Run with typical data to collect profile
./target/release/market-data --config config/market-data.toml &
sleep 300  # Run for 5 minutes
pkill market-data
```

#### Step 3: Merge profile data
```bash
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/*.profraw
```

#### Step 4: Build with PGO
```bash
RUSTFLAGS="-C profile-use=/tmp/pgo-data/merged.profdata -C llvm-args=-pgo-warn-missing-function" \
cargo build --release --package market-data
```

### Benchmark Build
```bash
cargo bench --no-run
cargo bench
```

### Flamegraph Profiling
```bash
# Install flamegraph
cargo install flamegraph

# Profile a benchmark
cargo flamegraph --bench orderbook_bench
```

---

## Platform-Specific Optimizations

### Linux
```bash
# Use mold linker (faster than lld)
sudo apt install mold
RUSTFLAGS="-C link-arg=-fuse-ld=mold" cargo build --release

# Enable huge pages for better TLB performance
echo 'vm.nr_hugepages=1024' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Windows
```powershell
# Ensure MSVC toolchain is installed
rustup default stable-x86_64-pc-windows-msvc

# Build with native CPU features
$env:RUSTFLAGS="-C target-cpu=native"
cargo build --release
```

### macOS
```bash
# Use system allocator (often faster on macOS)
# Don't use jemalloc/mimalloc on macOS
cargo build --release
```

---

## Verification

After applying optimizations, verify performance:

```bash
# Run benchmarks
cargo bench

# Check binary size
ls -lh target/release/market-data

# Verify CPU instructions used
objdump -d target/release/market-data | grep -i avx

# Profile with perf (Linux)
perf record -g ./target/release/market-data
perf report

# Memory profiling
valgrind --tool=massif ./target/release/market-data
```

---

## Expected Improvements

| Optimization | Compile Time | Binary Size | Runtime Performance |
|--------------|--------------|-------------|---------------------|
| opt-level = 3 | +50% | +10% | +30% |
| LTO = thin | +100% | -5% | +15% |
| LTO = fat | +300% | -10% | +25% |
| codegen-units = 1 | +50% | +5% | +10% |
| panic = "abort" | -5% | -8% | +8% |
| target-cpu=native | 0% | 0% | +15-25% |
| PGO | +200% | 0% | +10-15% |
| jemalloc | 0% | +2% | +5-15% |
| **Total** | **+400%** | **-8%** | **+100-200%** |

---

## Notes

1. **Compile Time**: Production builds will be 4-5x slower. Use `opt-level=1` for dev builds.

2. **Portability**: `target-cpu=native` creates CPU-specific binaries. For distribution:
   ```bash
   # Build generic x86_64 binary
   RUSTFLAGS="-C target-cpu=x86-64-v3" cargo build --release
   ```

3. **Debugging**: If optimized builds cause issues:
   ```toml
   [profile.release-debug]
   inherits = "release"
   debug = true
   strip = false
   ```

4. **CI/CD**: Use separate profiles for different environments:
   - Development: `opt-level = 1`, `lto = false`
   - Staging: `opt-level = 3`, `lto = "thin"`
   - Production: `opt-level = 3`, `lto = "fat"`, PGO

5. **Memory Safety**: `overflow-checks = false` can hide bugs. Only disable after thorough testing.

---

## Recommended Build Script

Create `/rust/scripts/build_optimized.sh`:

```bash
#!/bin/bash
set -euo pipefail

BUILD_TYPE=${1:-release}
USE_PGO=${2:-false}

echo "Building with: BUILD_TYPE=$BUILD_TYPE, USE_PGO=$USE_PGO"

# Set optimization flags
export RUSTFLAGS="-C target-cpu=native -C link-arg=-fuse-ld=lld"

if [ "$USE_PGO" = "true" ]; then
    echo "==> Step 1: Building instrumented binary..."
    RUSTFLAGS="$RUSTFLAGS -C profile-generate=/tmp/pgo-data" \
        cargo build --release

    echo "==> Step 2: Running profiling workload..."
    # Run your typical workload here
    timeout 300 ./target/release/market-data || true

    echo "==> Step 3: Merging profile data..."
    llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/*.profraw

    echo "==> Step 4: Building optimized binary with PGO..."
    RUSTFLAGS="$RUSTFLAGS -C profile-use=/tmp/pgo-data/merged.profdata" \
        cargo build --release

    echo "==> PGO build complete!"
else
    echo "==> Building release binary..."
    cargo build --release
    echo "==> Release build complete!"
fi

echo ""
echo "Binary location: target/release/"
ls -lh target/release/market-data
```

Usage:
```bash
# Standard optimized build
./scripts/build_optimized.sh release

# Build with PGO
./scripts/build_optimized.sh release true
```
