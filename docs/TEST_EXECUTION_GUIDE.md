# Test Execution Guide

## Quick Test Execution

### Run All Tests
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust

# Run workspace tests
cargo test --workspace

# Run with output
cargo test --workspace -- --nocapture --test-threads=1
```

### Run Specific Test Files

#### Unit Tests
```bash
# Risk manager tests (42 tests)
cargo test --package risk-manager --lib

# Market data tests (25 tests)
cargo test --package market-data --lib

# Execution engine tests (15 tests)
cargo test --package execution-engine --lib

# Common types and errors (75 tests)
cargo test --package common --lib
```

#### Integration Tests
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/tests

# End-to-end workflows (10 tests)
cargo test --test integration

# WebSocket integration (40 tests)
cargo test --test websocket_integration

# Concurrent operations (30 tests)
cargo test --test concurrent_integration
```

### Run Benchmarks
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/tests

# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench --bench orderbook_bench
```

## Test Count Summary

### By File
- **test_types.rs**: 60 tests
- **test_errors.rs**: 15 tests
- **test_orderbook.rs**: 25 tests
- **test_retry.rs**: 15 tests
- **test_risk_manager.rs**: 42 tests ⭐ NEW
- **test_slippage.rs**: 20 tests ⭐ NEW
- **test_end_to_end.rs**: 10 tests
- **test_websocket.rs**: 40 tests ⭐ NEW
- **test_concurrent.rs**: 30 tests ⭐ NEW
- **Total**: 257+ tests

### By Category
- **Unit Tests**: 177 tests
- **Integration Tests**: 80 tests
- **Benchmarks**: 8 benchmarks
- **Total**: 257+ tests + 8 benchmarks

## Coverage Generation

### Install Coverage Tools
```bash
# Install tarpaulin
cargo install cargo-tarpaulin

# Or use llvm-cov
rustup component add llvm-tools-preview
cargo install cargo-llvm-cov
```

### Generate Coverage Report
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust

# Using tarpaulin (HTML report)
cargo tarpaulin --workspace --out Html --output-dir ../target/coverage

# Using llvm-cov
cargo llvm-cov --workspace --html

# View report
# Open target/coverage/index.html in browser
```

### Coverage Targets
- **Overall**: 85%+
- **Risk Manager**: 90%+
- **Order Book**: 90%+
- **Retry Logic**: 95%+
- **Types/Errors**: 95%+

## Debugging Test Failures

### Run with Verbose Output
```bash
# Show println! output
cargo test -- --nocapture

# Show test names
cargo test -- --test-threads=1 --nocapture

# Run specific test
cargo test test_risk_manager -- --exact --nocapture
```

### Common Issues

#### Compilation Timeouts
The first compilation may take 2-3 minutes due to dependencies.
```bash
# Build first, then test
cargo build --workspace
cargo test --workspace --no-fail-fast
```

#### Test Dependencies
Ensure all workspace members are built:
```bash
cd rust
cargo build --workspace --all-targets
```

## Test Files Location

```
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/
├── rust/
│   ├── common/tests/             # Common library tests
│   ├── market-data/tests/        # Market data component tests
│   ├── execution-engine/tests/   # Execution component tests
│   └── risk-manager/tests/       # Risk manager component tests
└── tests/                        # Comprehensive test suite
    ├── unit/                     # 177 unit tests
    ├── integration/              # 80 integration tests
    ├── benchmarks/               # 8 benchmarks
    └── fixtures/                 # Test utilities
```

## Performance Targets

All tests should complete within:
- **Unit tests**: <5 seconds total
- **Integration tests**: <10 seconds total
- **Full suite**: <30 seconds total

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
      - name: Run tests
        run: |
          cd rust
          cargo test --workspace
      - name: Generate coverage
        run: |
          cargo install cargo-tarpaulin
          cargo tarpaulin --workspace --out Xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Next Steps

1. **First Run**: Execute `cargo test --workspace` to verify all tests pass
2. **Coverage**: Generate coverage report to identify gaps
3. **Benchmarks**: Run benchmarks to establish baseline performance
4. **CI Integration**: Set up automated testing in CI/CD pipeline

## Support

If tests fail or you encounter issues:
1. Check compilation errors first
2. Review test output with `--nocapture`
3. Run specific failing tests in isolation
4. Check dependencies are up to date: `cargo update`

---

**Total Tests**: 257+ tests
**Test Files**: 12
**Benchmarks**: 8
**Estimated Runtime**: <30 seconds
**Coverage Target**: 85%+
