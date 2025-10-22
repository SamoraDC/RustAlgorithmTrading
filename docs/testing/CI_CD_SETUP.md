# CI/CD Test Automation Setup

## Overview

This document describes the continuous integration and deployment setup for automated testing of the Rust algorithmic trading system.

## GitHub Actions Workflows

### Main Test Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  CARGO_TERM_COLOR: always
  RUST_BACKTRACE: 1

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true
          components: rustfmt, clippy

      - name: Cache cargo registry
        uses: actions/cache@v3
        with:
          path: ~/.cargo/registry
          key: ${{ runner.os }}-cargo-registry-${{ hashFiles('**/Cargo.lock') }}

      - name: Cache cargo index
        uses: actions/cache@v3
        with:
          path: ~/.cargo/git
          key: ${{ runner.os }}-cargo-git-${{ hashFiles('**/Cargo.lock') }}

      - name: Cache cargo build
        uses: actions/cache@v3
        with:
          path: target
          key: ${{ runner.os }}-cargo-build-target-${{ hashFiles('**/Cargo.lock') }}

      - name: Run unit tests
        run: |
          cargo test --lib --workspace --verbose
          cargo test --test test_common_types --verbose
          cargo test --test test_common_health --verbose
          cargo test --test test_market_data_orderbook --verbose
          cargo test --test test_risk_limits --verbose
          cargo test --test test_execution_router --verbose

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true

      - name: Install Python dependencies
        run: |
          python3 -m pip install --upgrade pip
          pip3 install duckdb fastapi uvicorn

      - name: Setup test databases
        run: |
          mkdir -p data
          python3 -c "import duckdb; conn = duckdb.connect('data/metrics.duckdb'); conn.execute('CREATE TABLE IF NOT EXISTS market_data_metrics (timestamp TIMESTAMP, symbol VARCHAR, price DOUBLE, volume BIGINT, bid DOUBLE, ask DOUBLE, spread DOUBLE)'); conn.close()"

      - name: Run integration tests
        run: |
          cargo test --test integration --verbose
          cargo test --test websocket_integration --verbose
          cargo test --test concurrent_integration --verbose
          cargo test --test duckdb_storage_integration --verbose

  property-tests:
    name: Property-Based Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true

      - name: Run property-based tests
        run: cargo test --test test_order_invariants --verbose
        env:
          PROPTEST_CASES: 1000

  benchmarks:
    name: Performance Benchmarks
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true

      - name: Run benchmarks (validation only)
        run: cargo bench --no-run --workspace --verbose

  coverage:
    name: Code Coverage
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true

      - name: Install tarpaulin
        run: cargo install cargo-tarpaulin

      - name: Generate coverage
        run: |
          cargo tarpaulin --out Xml --workspace --timeout 300

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./cobertura.xml
          fail_ci_if_error: true

      - name: Upload coverage artifact
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: cobertura.xml

  lint:
    name: Linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true
          components: rustfmt, clippy

      - name: Check formatting
        run: cargo fmt --all -- --check

      - name: Run clippy
        run: cargo clippy --workspace --all-targets -- -D warnings

  security-audit:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install cargo-audit
        run: cargo install cargo-audit

      - name: Run security audit
        run: cargo audit

  test-summary:
    name: Test Summary
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, property-tests, coverage, lint]
    if: always()
    steps:
      - name: Summary
        run: |
          echo "## Test Results" >> $GITHUB_STEP_SUMMARY
          echo "✅ Unit Tests: ${{ needs.unit-tests.result }}" >> $GITHUB_STEP_SUMMARY
          echo "✅ Integration Tests: ${{ needs.integration-tests.result }}" >> $GITHUB_STEP_SUMMARY
          echo "✅ Property Tests: ${{ needs.property-tests.result }}" >> $GITHUB_STEP_SUMMARY
          echo "✅ Coverage: ${{ needs.coverage.result }}" >> $GITHUB_STEP_SUMMARY
          echo "✅ Linting: ${{ needs.lint.result }}" >> $GITHUB_STEP_SUMMARY
```

### Nightly Benchmark Workflow

Create `.github/workflows/nightly-benchmarks.yml`:

```yaml
name: Nightly Benchmarks

on:
  schedule:
    - cron: '0 2 * * *'  # Run at 2 AM UTC daily
  workflow_dispatch:  # Allow manual trigger

jobs:
  benchmarks:
    name: Run Full Benchmark Suite
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true

      - name: Run benchmarks
        run: cargo bench --workspace

      - name: Archive benchmark results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: target/criterion

      - name: Compare with baseline
        run: |
          if [ -f baseline.json ]; then
            cargo bench --bench critical_path_benchmarks -- --save-baseline current
            cargo bench --bench critical_path_benchmarks -- --baseline current --load-baseline baseline
          fi
```

## Local Pre-Commit Hooks

Install pre-commit hooks with:

```bash
# Create .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

echo "Running pre-commit checks..."

# Format check
echo "Checking code formatting..."
cargo fmt --all -- --check
if [ $? -ne 0 ]; then
    echo "❌ Code formatting issues found. Run 'cargo fmt' to fix."
    exit 1
fi

# Clippy
echo "Running clippy..."
cargo clippy --workspace --all-targets -- -D warnings
if [ $? -ne 0 ]; then
    echo "❌ Clippy warnings found."
    exit 1
fi

# Unit tests
echo "Running unit tests..."
cargo test --lib --workspace
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed."
    exit 1
fi

echo "✅ All pre-commit checks passed!"
exit 0
EOF

chmod +x .git/hooks/pre-commit
```

## Running Tests Locally

### Quick Test Suite (< 1 minute)
```bash
cargo test --lib --workspace
```

### Full Test Suite (2-5 minutes)
```bash
cargo test --workspace --verbose
```

### With Coverage
```bash
cargo tarpaulin --out Html --output-dir coverage --workspace
open coverage/index.html
```

### Continuous Testing (watch mode)
```bash
cargo install cargo-watch
cargo watch -x test
```

## Test Results Reporting

### JUnit XML Output
```bash
cargo install cargo2junit
cargo test -- -Z unstable-options --format json | cargo2junit > test-results.xml
```

### HTML Coverage Report
```bash
cargo tarpaulin --out Html --output-dir coverage
```

## Performance Tracking

### Benchmark Comparison
```bash
# Run baseline
cargo bench -- --save-baseline main

# After changes
cargo bench -- --baseline main
```

### Historical Performance
Store benchmark results in Git:

```bash
# .gitignore
!target/criterion/**/base/estimates.json
```

## Integration with IDEs

### VS Code
Add to `.vscode/settings.json`:
```json
{
  "rust-analyzer.checkOnSave.command": "clippy",
  "rust-analyzer.cargo.features": "all",
  "editor.formatOnSave": true
}
```

### IntelliJ IDEA
- Enable "Run tests automatically"
- Configure Rust plugin to use clippy

## Troubleshooting

### Tests Hanging
```bash
# Add timeout
cargo test -- --test-threads=1 --nocapture
```

### Flaky Tests
```bash
# Run multiple times
for i in {1..10}; do cargo test test_name || break; done
```

### Memory Issues
```bash
# Reduce parallel tests
cargo test -- --test-threads=2
```

## Test Environment Variables

Create `.env.test`:
```bash
RUST_LOG=debug
RUST_BACKTRACE=1
ALPACA_API_KEY=test_key
ALPACA_SECRET_KEY=test_secret
TEST_DATABASE_URL=:memory:
```

Load in tests:
```rust
#[cfg(test)]
use dotenv::dotenv;

#[test]
fn test_with_env() {
    dotenv().ok();
    // Test code
}
```

## Coverage Goals

| Metric | Goal | Current |
|--------|------|---------|
| Statement Coverage | >95% | TBD |
| Branch Coverage | >90% | TBD |
| Function Coverage | >95% | TBD |
| Line Coverage | >95% | TBD |

## Reporting Issues

When tests fail in CI:
1. Check GitHub Actions logs
2. Reproduce locally: `cargo test --test <test_name> -- --nocapture`
3. Add debug output if needed
4. File issue with:
   - Test name
   - Error message
   - Environment (OS, Rust version)
   - Steps to reproduce
