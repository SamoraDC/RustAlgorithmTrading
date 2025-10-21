#!/bin/bash
# Optimized build script for Rust trading system
# Usage: ./scripts/build_optimized.sh [release|pgo]

set -euo pipefail

BUILD_TYPE=${1:-release}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT/rust"

echo "==================================================="
echo "Rust Trading System - Optimized Build"
echo "==================================================="
echo "Build type: $BUILD_TYPE"
echo "Working directory: $(pwd)"
echo ""

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    LINKER="lld"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    LINKER="ld64"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
    LINKER="lld-link"
else
    PLATFORM="unknown"
    LINKER="default"
fi

echo "Platform: $PLATFORM"
echo "Linker: $LINKER"
echo ""

# Set optimization flags
if [[ "$PLATFORM" == "linux" ]]; then
    export RUSTFLAGS="-C target-cpu=native -C link-arg=-fuse-ld=lld"
elif [[ "$PLATFORM" == "macos" ]]; then
    export RUSTFLAGS="-C target-cpu=native"
else
    export RUSTFLAGS="-C target-cpu=native"
fi

echo "RUSTFLAGS: $RUSTFLAGS"
echo ""

case "$BUILD_TYPE" in
    release)
        echo "==> Building optimized release binary..."
        cargo build --release
        echo ""
        echo "✓ Release build complete!"
        ;;

    pgo)
        echo "==> Profile-Guided Optimization Build"
        echo ""

        PGO_DATA_DIR="/tmp/rust-trading-pgo-data"
        mkdir -p "$PGO_DATA_DIR"

        echo "Step 1: Building instrumented binary..."
        RUSTFLAGS="$RUSTFLAGS -C profile-generate=$PGO_DATA_DIR" \
            cargo build --release
        echo "✓ Instrumented binary built"
        echo ""

        echo "Step 2: Running profiling workload..."
        echo "Starting market-data service for profiling..."

        # Run market-data with sample configuration
        timeout 60 ./target/release/market-data || true

        # Check if profile data was generated
        if [ ! -d "$PGO_DATA_DIR" ] || [ -z "$(ls -A $PGO_DATA_DIR)" ]; then
            echo "❌ Error: No profile data generated"
            echo "Please ensure the profiling workload ran successfully"
            exit 1
        fi

        echo "✓ Profile data collected"
        echo ""

        echo "Step 3: Merging profile data..."
        if command -v llvm-profdata &> /dev/null; then
            llvm-profdata merge -o "$PGO_DATA_DIR/merged.profdata" "$PGO_DATA_DIR"/*.profraw
            echo "✓ Profile data merged"
        else
            echo "❌ Error: llvm-profdata not found"
            echo "Install with: sudo apt-get install llvm (Linux) or brew install llvm (macOS)"
            exit 1
        fi
        echo ""

        echo "Step 4: Building optimized binary with PGO..."
        RUSTFLAGS="$RUSTFLAGS -C profile-use=$PGO_DATA_DIR/merged.profdata -C llvm-args=-pgo-warn-missing-function" \
            cargo build --release
        echo "✓ PGO-optimized binary built"
        echo ""

        # Cleanup
        echo "Cleaning up profile data..."
        rm -rf "$PGO_DATA_DIR"
        echo ""

        echo "✓ PGO build complete!"
        ;;

    bench)
        echo "==> Building and running benchmarks..."
        cargo bench
        echo ""
        echo "✓ Benchmarks complete!"
        ;;

    clean)
        echo "==> Cleaning build artifacts..."
        cargo clean
        echo "✓ Clean complete!"
        ;;

    *)
        echo "❌ Error: Unknown build type: $BUILD_TYPE"
        echo ""
        echo "Usage: $0 [release|pgo|bench|clean]"
        echo ""
        echo "Build types:"
        echo "  release - Standard optimized build"
        echo "  pgo     - Profile-guided optimization build"
        echo "  bench   - Build and run benchmarks"
        echo "  clean   - Clean build artifacts"
        exit 1
        ;;
esac

echo ""
echo "==================================================="
echo "Build Summary"
echo "==================================================="

# Show binary information
if [ -f "target/release/market-data" ]; then
    echo "Binary: target/release/market-data"
    ls -lh target/release/market-data | awk '{print "Size: " $5}'

    # Check for CPU-specific instructions (Linux only)
    if [[ "$PLATFORM" == "linux" ]] && command -v objdump &> /dev/null; then
        echo ""
        echo "CPU Instructions Used:"
        if objdump -d target/release/market-data | grep -q "avx2"; then
            echo "  ✓ AVX2 instructions detected"
        else
            echo "  ⚠ No AVX2 instructions found"
        fi
        if objdump -d target/release/market-data | grep -q "fma"; then
            echo "  ✓ FMA instructions detected"
        else
            echo "  ⚠ No FMA instructions found"
        fi
    fi
fi

echo ""
echo "==================================================="
echo "Next Steps"
echo "==================================================="
echo "1. Run benchmarks: cargo bench"
echo "2. Test binary: ./target/release/market-data --help"
echo "3. Profile: perf record -g ./target/release/market-data"
echo "4. Flamegraph: cargo flamegraph --release"
echo ""
