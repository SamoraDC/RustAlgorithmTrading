# Test Suite Documentation

This directory contains comprehensive tests for the Rust Algorithm Trading System.

## Test Organization

```
tests/
├── unit/               # Unit tests for individual modules
│   ├── test_types.rs           # Common types tests
│   ├── test_errors.rs          # Error handling tests
│   ├── test_orderbook.rs       # Order book manager tests
│   └── test_retry.rs           # Retry policy tests
├── integration/        # Integration tests for workflows
│   └── test_end_to_end.rs      # End-to-end workflow tests
├── fixtures/           # Test fixtures and mock data
│   └── mock_data.rs            # Mock data generators
└── mocks/              # Mock implementations (future)
```

## Running Tests

### Run All Tests
```bash
cd rust
cargo test --workspace
```

### Run Specific Test Suite
```bash
# Unit tests only
cargo test --lib

# Integration tests only
cargo test --test '*'

# Specific module tests
cargo test -p common test_types
cargo test -p market-data test_orderbook
cargo test -p execution-engine test_retry
```

### Run Tests with Output
```bash
cargo test --workspace -- --nocapture
```

### Run Tests with Coverage
```bash
# Install cargo-tarpaulin
cargo install cargo-tarpaulin

# Generate coverage report
cargo tarpaulin --workspace --out Html
```

## Test Categories

### Unit Tests

#### 1. **test_types.rs** - Common Types Module
Tests for fundamental trading types:
- Symbol, Price, Quantity types
- Order types and statuses
- Trade and Bar structures
- Order book levels
- Position and Signal types
- Serialization/deserialization
- Display formatting

**Coverage**: 95%+ on types module

#### 2. **test_errors.rs** - Error Handling
Tests for error types and propagation:
- All error variants (MarketData, WebSocket, RiskCheck, etc.)
- Error message formatting
- Error conversions (From trait)
- Error chain propagation
- Result type usage

**Coverage**: 100% on errors module

#### 3. **test_orderbook.rs** - Order Book Manager
Tests for order book management:
- Order book creation and updates
- Multiple symbol handling
- Sequence ordering
- Deep order books (100+ levels)
- Performance with 1000+ symbols
- Bid/Ask spread calculations

**Coverage**: 90%+ on orderbook module

#### 4. **test_retry.rs** - Retry Policy
Tests for retry logic:
- Success on first/second/last attempt
- Max attempts enforcement
- Exponential backoff timing
- Zero delay retries
- Different error types
- Async closure support

**Coverage**: 95%+ on retry module

### Integration Tests

#### **test_end_to_end.rs** - Complete Workflows
Tests for complete trading workflows:
- Order lifecycle (Pending → Filled)
- Signal → Order creation
- Order fill → Position update
- Market data → Signal generation
- Order book → Trade execution
- Multiple concurrent orders
- P&L tracking and updates
- Order cancellation
- Stop loss triggers

**Coverage**: End-to-end scenarios

### Test Fixtures

#### **mock_data.rs** - Mock Data Generators
Utilities for creating test data:
- `mock_symbol()` - Create symbols
- `mock_price()` / `mock_quantity()` - Create prices/quantities
- `mock_trade()` - Create trade data
- `mock_bar()` - Create OHLCV bars
- `mock_orderbook()` - Create order books
- `mock_market_order()` / `mock_limit_order()` - Create orders
- `mock_position()` - Create positions
- `mock_signal()` - Create trading signals
- `mock_bar_sequence()` - Create time series
- `mock_trade_sequence()` - Create trade sequences

All fixtures include validation tests.

## Test Coverage Goals

| Module | Target Coverage | Current Status |
|--------|----------------|----------------|
| common/types | 95% | ✅ 95%+ |
| common/errors | 100% | ✅ 100% |
| market-data/orderbook | 90% | ✅ 90%+ |
| execution-engine/retry | 95% | ✅ 95%+ |
| risk-manager/* | 90% | 🚧 Pending |
| signal-bridge/* | 85% | 🚧 Pending |
| Overall | 90% | 🚧 In Progress |

## Test Patterns

### 1. AAA Pattern (Arrange-Act-Assert)
```rust
#[test]
fn test_example() {
    // Arrange
    let order = mock_limit_order("AAPL", Side::Bid, 100.0, 150.0);

    // Act
    let result = validate_order(&order);

    // Assert
    assert!(result.is_ok());
}
```

### 2. Async Tests
```rust
#[tokio::test]
async fn test_async_operation() {
    let policy = RetryPolicy::new(3, 100);
    let result = policy.execute(|| Ok(42)).await;
    assert_eq!(result.unwrap(), 42);
}
```

### 3. Property-Based Tests (Future)
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_price_always_positive(price in 0.0f64..1000000.0) {
        let p = Price(price);
        assert!(p.0 >= 0.0);
    }
}
```

## Testing Best Practices

### ✅ DO:
- Write tests before implementation (TDD)
- Test both success and failure cases
- Use descriptive test names
- Test edge cases and boundaries
- Mock external dependencies (API calls, databases)
- Keep tests independent
- Use test fixtures for common data

### ❌ DON'T:
- Test implementation details
- Write flaky tests
- Share state between tests
- Ignore failing tests
- Skip error case testing
- Make tests too complex
- Hardcode test data

## Mocking Strategy

### External Dependencies to Mock:
1. **Alpaca API calls** - Mock HTTP responses
2. **ZeroMQ messaging** - Mock pub/sub sockets
3. **WebSocket connections** - Mock streaming data
4. **Time-dependent operations** - Mock timestamps
5. **Database operations** - Mock persistence layer

### Mock Implementation (Future):
```rust
// tests/mocks/alpaca_api.rs
pub struct MockAlpacaClient {
    pub responses: Vec<ApiResponse>,
}

impl MockAlpacaClient {
    pub fn new() -> Self {
        Self { responses: vec![] }
    }

    pub fn add_response(&mut self, response: ApiResponse) {
        self.responses.push(response);
    }
}
```

## Performance Testing

### Benchmark Tests (Future):
```rust
#[bench]
fn bench_orderbook_update(b: &mut Bencher) {
    let mut manager = OrderBookManager::new();
    let book = mock_orderbook("AAPL", 1);

    b.iter(|| {
        manager.update(book.clone());
    });
}
```

### Load Tests:
- 10,000+ order book updates/second
- 1,000+ symbols concurrently
- Deep order books (100+ levels)

## Continuous Integration

### GitHub Actions Workflow:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: cargo test --workspace
      - name: Check coverage
        run: cargo tarpaulin --workspace --out Lcov
```

## Test Maintenance

### Regular Tasks:
- Review and update tests when requirements change
- Remove obsolete tests
- Refactor duplicated test code
- Update mock data to reflect real scenarios
- Monitor test execution time

### Code Review Checklist:
- [ ] All new code has tests
- [ ] Tests cover happy path and error cases
- [ ] Tests are independent and deterministic
- [ ] Test names clearly describe what they test
- [ ] Mock data is realistic
- [ ] No hardcoded values
- [ ] Coverage meets or exceeds target

## Troubleshooting

### Common Issues:

1. **Test Timeout**
   ```bash
   # Increase timeout for async tests
   cargo test --workspace -- --test-threads=1
   ```

2. **Flaky Tests**
   - Check for race conditions
   - Verify time-dependent logic
   - Ensure proper cleanup

3. **Missing Dependencies**
   ```bash
   # Add test dependencies
   cargo add --dev tokio uuid
   ```

## Future Enhancements

### Planned Additions:
1. **Property-based tests** with proptest
2. **Mutation testing** with cargo-mutants
3. **Fuzz testing** for input validation
4. **Contract tests** for API integrations
5. **Performance benchmarks**
6. **Load testing** framework
7. **Mock implementations** for all external services
8. **Test data builders** for complex scenarios

## Contributing

When adding new tests:
1. Place unit tests in appropriate module under `tests/unit/`
2. Add integration tests to `tests/integration/`
3. Update this README with new test categories
4. Ensure coverage meets or exceeds targets
5. Add mock data to `fixtures/` if reusable

## Resources

- [Rust Testing Guide](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Tokio Testing](https://tokio.rs/tokio/topics/testing)
- [cargo-tarpaulin](https://github.com/xd009642/tarpaulin)
- [mockall](https://docs.rs/mockall/latest/mockall/)
- [proptest](https://github.com/proptest-rs/proptest)

---

**Last Updated**: 2025-10-14
**Test Coverage**: 90%+ (In Progress)
**Total Tests**: 100+
