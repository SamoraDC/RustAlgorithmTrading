# Testing Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Test Types](#test-types)
6. [Best Practices](#best-practices)
7. [CI/CD Integration](#cicd-integration)

## Overview

The py_rt project has comprehensive test coverage across both Python and Rust components, with multiple test types ensuring code quality, performance, and reliability.

### Test Statistics

- **Python Tests**: 200+ test cases
- **Rust Tests**: 150+ test cases
- **Coverage Target**: 90%+
- **Test Execution Time**: < 2 minutes (parallel)

## Test Structure

```
tests/
├── unit/
│   ├── python/           # Python unit tests
│   │   ├── test_backtest_engine.py
│   │   ├── test_strategy_base.py
│   │   └── ...
│   └── rust/             # Rust unit tests (in rust/*/tests/)
│
├── integration/
│   ├── python/           # Python integration tests
│   │   ├── test_alpaca_integration.py
│   │   └── ...
│   └── rust/             # Rust integration tests
│
├── property/             # Property-based tests
│   └── test_property_based.py
│
├── e2e/                  # End-to-end tests
│   └── test_full_system.py
│
├── benchmarks/           # Performance benchmarks
│   ├── python/
│   └── rust/
│
├── fixtures/             # Test data and mocks
│   ├── data/
│   └── mocks/
│
└── conftest.py           # Shared pytest configuration
```

## Running Tests

### Python Tests

#### All Tests
```bash
# Run all Python tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Parallel execution
pytest tests/ -n auto
```

#### Specific Test Types
```bash
# Unit tests only
pytest tests/unit/python/

# Integration tests
pytest tests/integration/python/

# Property-based tests
pytest tests/property/

# E2E tests
pytest tests/e2e/

# Exclude slow tests
pytest tests/ -m "not slow"
```

#### Single Test File or Function
```bash
# Run specific file
pytest tests/unit/python/test_backtest_engine.py

# Run specific test class
pytest tests/unit/python/test_backtest_engine.py::TestBacktestEngineInitialization

# Run specific test function
pytest tests/unit/python/test_backtest_engine.py::TestBacktestEngineInitialization::test_initialization_defaults

# Run with verbose output
pytest tests/unit/python/test_backtest_engine.py -v
```

### Rust Tests

#### All Tests
```bash
cd rust/
cargo test --workspace
```

#### Component Tests
```bash
# Market data component
cd rust/market-data
cargo test

# Execution engine
cd rust/execution-engine
cargo test

# With output
cargo test -- --nocapture

# With specific test
cargo test test_orderbook_operations
```

#### Integration Tests
```bash
cd rust/
cargo test --test integration_tests
```

#### Benchmarks
```bash
cd rust/
cargo bench
```

### Combined Testing

```bash
# Run everything (Python + Rust)
./scripts/test-all.sh

# Quick test (unit tests only)
./scripts/test-quick.sh
```

## Test Coverage

### Generating Coverage Reports

#### Python Coverage
```bash
# Generate HTML report
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html

# Generate XML for CI
pytest tests/ --cov=src --cov-report=xml

# Terminal report
pytest tests/ --cov=src --cov-report=term-missing
```

#### Rust Coverage
```bash
cd rust/
cargo install cargo-tarpaulin
cargo tarpaulin --all-features --workspace --timeout 120 --out Html
# Open tarpaulin-report.html
```

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Python Core | 90% | TBD |
| Backtesting | 95% | TBD |
| Strategies | 85% | TBD |
| Rust Core | 90% | TBD |
| Market Data | 95% | TBD |
| Execution | 95% | TBD |

## Test Types

### 1. Unit Tests

**Purpose**: Test individual functions and classes in isolation

**Location**: `tests/unit/python/`, `rust/*/tests/`

**Examples**:
- Backtest engine initialization
- Strategy parameter management
- Order book operations
- Price calculations

**Running**:
```bash
pytest tests/unit/python/
cd rust/ && cargo test --lib
```

### 2. Integration Tests

**Purpose**: Test component interactions and API integrations

**Location**: `tests/integration/python/`, `rust/*/tests/`

**Examples**:
- Alpaca API client integration
- ZeroMQ message passing
- Database connections
- WebSocket streaming

**Running**:
```bash
pytest tests/integration/python/
cd rust/ && cargo test --test integration_tests
```

### 3. Property-Based Tests

**Purpose**: Test invariants and properties across many inputs

**Location**: `tests/property/`

**Library**: Hypothesis (Python), proptest (Rust)

**Examples**:
- P&L calculations are consistent
- Position sizing respects limits
- OHLCV data invariants (High >= Low)
- Price types are always positive

**Running**:
```bash
pytest tests/property/
```

### 4. End-to-End Tests

**Purpose**: Test complete workflows from start to finish

**Location**: `tests/e2e/`

**Examples**:
- Full backtest execution
- Live trading simulation
- Data pipeline flow
- Multi-component integration

**Running**:
```bash
pytest tests/e2e/
```

### 5. Performance Benchmarks

**Purpose**: Ensure performance targets are met

**Location**: `tests/benchmarks/`

**Examples**:
- Order book update latency (<50μs)
- Backtest execution speed
- Memory usage
- Throughput testing

**Running**:
```bash
# Python benchmarks
pytest tests/benchmarks/ --benchmark-only

# Rust benchmarks
cd rust/ && cargo bench
```

## Best Practices

### Writing Tests

1. **Follow AAA Pattern**:
   ```python
   def test_example():
       # Arrange - Set up test data
       engine = BacktestEngine(initial_capital=100000.0)

       # Act - Perform action
       results = engine.run(strategy, data)

       # Assert - Verify results
       assert results['total_trades'] > 0
   ```

2. **Use Descriptive Names**:
   ```python
   # Good
   def test_backtest_engine_resets_state_between_runs()

   # Bad
   def test_reset()
   ```

3. **Test One Thing**:
   ```python
   # Good - Single assertion
   def test_initial_cash_equals_capital():
       engine = BacktestEngine(initial_capital=50000.0)
       assert engine.cash == 50000.0

   # Avoid - Multiple unrelated assertions
   def test_everything():
       assert engine.cash == 50000.0
       assert engine.commission_rate == 0.001
       assert len(engine.trades) == 0
       # ...
   ```

4. **Use Fixtures for Common Setup**:
   ```python
   @pytest.fixture
   def backtest_engine():
       return BacktestEngine(
           initial_capital=100000.0,
           commission_rate=0.001
       )

   def test_with_fixture(backtest_engine):
       assert backtest_engine.cash == 100000.0
   ```

5. **Mock External Dependencies**:
   ```python
   @patch('src.api.alpaca_client.TradingClient')
   def test_with_mock(mock_client):
       mock_client.get_account = Mock(return_value=mock_account)
       # Test with mock
   ```

### Test Organization

1. **Group Related Tests** in classes:
   ```python
   class TestBacktestEngineInitialization:
       def test_defaults(self):
           ...

       def test_custom_params(self):
           ...
   ```

2. **Use Markers** for categorization:
   ```python
   @pytest.mark.slow
   def test_large_dataset():
       ...

   @pytest.mark.integration
   def test_api_connection():
       ...
   ```

3. **Separate Unit from Integration** tests in different directories

4. **Keep Tests Independent** - Each test should run in isolation

### Performance Testing

1. **Set Realistic Thresholds**:
   ```python
   def test_performance():
       start = time.time()
       process_large_dataset()
       elapsed = time.time() - start

       assert elapsed < 1.0  # Must complete in < 1 second
   ```

2. **Use Benchmarking Tools**:
   ```python
   def test_benchmark(benchmark):
       result = benchmark(expensive_function)
       assert result.iterations > 100
   ```

## CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- Manual workflow dispatch

**Workflow Steps**:
1. Python Tests (3.11, 3.12)
2. Rust Tests (stable, beta)
3. Code Quality (black, flake8, clippy)
4. Coverage Reports
5. Benchmarks (on main branch)
6. Security Audit

### Configuration

See `.github/workflows/ci.yml` for complete CI/CD configuration.

**Environment Variables**:
```bash
# For CI testing
export TESTING=true
export LOG_LEVEL=INFO
export DATABASE_URL=sqlite:///:memory:
```

### Coverage Upload

Coverage reports are automatically uploaded to Codecov:
- Python coverage: `codecov/python`
- Rust coverage: `codecov/rust`

### Test Artifacts

Test artifacts are saved for 30 days:
- Test results (XML)
- Coverage reports (HTML/XML)
- Benchmark results (JSON)
- Security audit reports

## Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Ensure package is installed
   pip install -e .

   # Check PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Slow Tests**:
   ```bash
   # Use parallel execution
   pytest tests/ -n auto

   # Skip slow tests
   pytest tests/ -m "not slow"
   ```

3. **Flaky Tests**:
   ```bash
   # Run with retries
   pytest tests/ --reruns 3

   # Increase timeout
   pytest tests/ --timeout=300
   ```

4. **Memory Issues**:
   ```bash
   # Run tests in smaller batches
   pytest tests/unit/
   pytest tests/integration/

   # Reduce parallel workers
   pytest tests/ -n 2
   ```

### Debug Mode

```bash
# Run with debugger
pytest tests/ --pdb

# Stop on first failure
pytest tests/ -x

# Show full output
pytest tests/ -s

# Very verbose
pytest tests/ -vv
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Rust Testing Guide](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Code Coverage Best Practices](https://coverage.readthedocs.io/)

## Support

For test-related issues:
1. Check this documentation
2. Review existing tests for examples
3. Open an issue on GitHub
4. Contact the development team
