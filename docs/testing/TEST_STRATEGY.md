# Comprehensive Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for the Rust algorithmic trading system. The test suite ensures reliability, performance, and correctness across all components.

## Test Pyramid

```
              /\
             /E2E\          <- 5% (End-to-end scenarios)
            /------\
           /Integr.\        <- 15% (Component integration)
          /----------\
         / Property  \      <- 20% (Property-based tests)
        /--------------\
       /   Unit Tests  \    <- 60% (Fast, isolated)
      /------------------\
```

## Test Categories

### 1. Unit Tests (60% of test suite)

**Location**: `tests/unit/`

**Purpose**: Test individual components in isolation

**Files**:
- `test_common_types.rs` - Core domain types (Order, Position, Trade, etc.)
- `test_common_health.rs` - Health check system
- `test_market_data_orderbook.rs` - Order book management
- `test_risk_limits.rs` - Risk management limits
- `test_execution_router.rs` - Order routing and execution
- `test_security_fixes.rs` - Security vulnerability tests
- `test_router_security.rs` - Router-specific security tests

**Coverage Goals**:
- Statements: >95%
- Branches: >90%
- Functions: >95%
- Lines: >95%

**Key Test Patterns**:
```rust
#[test]
fn test_order_creation() {
    let order = Order {
        id: "test-1".to_string(),
        symbol: "AAPL".to_string(),
        side: OrderSide::Buy,
        order_type: OrderType::Limit,
        quantity: 100,
        price: Some(150.00),
        status: OrderStatus::Pending,
        timestamp: Utc::now(),
    };

    assert_eq!(order.quantity, 100);
    assert!(matches!(order.side, OrderSide::Buy));
}
```

### 2. Integration Tests (15% of test suite)

**Location**: `tests/integration/`

**Purpose**: Test component interactions and end-to-end workflows

**Files**:
- `test_end_to_end.rs` - Complete trading workflows
- `test_websocket.rs` - WebSocket connections and data feeds
- `test_concurrent.rs` - Concurrent operations and race conditions
- `test_duckdb_storage.rs` - Database integration with observability

**Test Scenarios**:
1. **Order Lifecycle**:
   - Create order → Submit → Fill → Record trade
   - Test all order types (Market, Limit, Stop, StopLimit)
   - Verify order state transitions

2. **Market Data Flow**:
   - WebSocket connection → Tick processing → Bar aggregation → Publishing
   - Handle reconnection and failover
   - Data integrity across pipeline

3. **Risk Management Integration**:
   - Order submission → Risk checks → Position update → P&L calculation
   - Circuit breaker activation
   - Stop-loss triggers

4. **Observability Storage**:
   - Metrics collection → DuckDB storage → Query and analysis
   - Real-time event streaming to SQLite
   - Performance monitoring

**Example**:
```rust
#[tokio::test]
async fn test_complete_order_workflow() {
    // Setup
    let market_data = MarketDataService::new(config).await?;
    let risk_manager = RiskManagerService::new(risk_config)?;
    let execution_engine = ExecutionEngineService::new(exec_config).await?;

    // Create order
    let order = OrderBuilder::new()
        .symbol("AAPL")
        .limit_order(150.00)
        .quantity(100)
        .build();

    // Risk check
    let approved = risk_manager.check_order(&order)?;
    assert!(approved);

    // Execute
    execution_engine.submit_order(order).await?;

    // Verify
    // ... assertions
}
```

### 3. Property-Based Tests (20% of test suite)

**Location**: `tests/property/`

**Purpose**: Verify invariants hold for all possible inputs using `proptest`

**Files**:
- `test_order_invariants.rs` - Order data model properties

**Properties Tested**:
1. **Order Quantity**: Always non-negative
2. **Price Positivity**: Prices always > 0
3. **Order Value**: price × quantity consistency
4. **Position P&L**: Calculation correctness
5. **Spread**: Ask ≥ Bid
6. **Serialization**: Roundtrip lossless
7. **Volume Overflow**: No arithmetic overflow

**Example**:
```rust
proptest! {
    #[test]
    fn test_order_quantity_always_non_negative(quantity in 0i32..1_000_000) {
        let order = Order {
            // ... fields
            quantity,
            // ... fields
        };

        prop_assert!(order.quantity >= 0);
    }

    #[test]
    fn test_position_pnl_consistency(
        quantity in 1i32..1000,
        avg_price in 50.0f64..500.0,
        current_price in 50.0f64..500.0
    ) {
        let expected_pnl = (current_price - avg_price) * quantity as f64;
        let position = Position { /* ... */ };

        let diff = (position.unrealized_pnl - expected_pnl).abs();
        prop_assert!(diff < 0.01); // Floating point tolerance
    }
}
```

### 4. Performance Benchmarks

**Location**: `tests/benchmarks/`

**Purpose**: Measure and track performance of critical paths using `criterion`

**Files**:
- `critical_path_benchmarks.rs` - Core operation benchmarks
- `orderbook_bench.rs` - Order book performance
- `performance_benchmarks.rs` - System-wide benchmarks

**Benchmarked Operations**:
1. **Order Creation**: < 100ns
2. **Order Serialization**: < 1μs
3. **Order Deserialization**: < 2μs
4. **OrderBook Update**: < 500ns per level
5. **Position P&L Calculation**: < 50ns
6. **Tick Processing**: 100k ticks/sec
7. **Bar Aggregation**: < 1μs per bar
8. **Spread Calculation**: < 10ns

**Example**:
```rust
fn benchmark_order_creation(c: &mut Criterion) {
    c.bench_function("order_creation", |b| {
        b.iter(|| {
            let order = Order { /* ... */ };
            black_box(order);
        });
    });
}

criterion_group!(benches, benchmark_order_creation);
criterion_main!(benches);
```

**Running Benchmarks**:
```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench -- order_creation

# Generate HTML report
cargo bench -- --save-baseline main
```

## Test Fixtures and Mocks

**Location**: `tests/fixtures/`

**Files**:
- `comprehensive_mocks.rs` - Builders and generators
- `mock_data.rs` - Sample data
- `mod.rs` - Fixture exports

**Builders**:
- `OrderBuilder` - Fluent order creation
- `PositionBuilder` - Position with calculated P&L
- `TradeBuilder` - Trade construction
- `RandomGenerator` - Random test data
- `HistoricalDataGenerator` - Time-series data
- `ScenarioGenerator` - Complete scenarios

**Usage**:
```rust
use tests::fixtures::comprehensive_mocks::*;

let order = OrderBuilder::new()
    .symbol("AAPL")
    .limit_order(150.00)
    .quantity(100)
    .status(OrderStatus::Filled)
    .build();

let position = PositionBuilder::new()
    .symbol("TSLA")
    .quantity(50)
    .with_profit(5.0) // 5% profit
    .build();

let ticks = HistoricalDataGenerator::generate_ticks("NVDA", 1000, 450.0);
let bars = HistoricalDataGenerator::generate_trend_bars("GOOG", 100, 2500.0, 0.5);
```

## Running Tests

### Run All Tests
```bash
cargo test --workspace
```

### Run Unit Tests Only
```bash
cargo test --lib --workspace
```

### Run Integration Tests
```bash
cargo test --test '*' --workspace
```

### Run Property-Based Tests
```bash
cargo test --test test_order_invariants
```

### Run Benchmarks
```bash
cargo bench --workspace
```

### Run with Coverage
```bash
# Install tarpaulin
cargo install cargo-tarpaulin

# Generate coverage report
cargo tarpaulin --out Html --output-dir coverage --workspace

# View report
open coverage/index.html
```

## Test Organization

```
tests/
├── unit/                       # Unit tests (fast, isolated)
│   ├── test_common_types.rs
│   ├── test_common_health.rs
│   ├── test_market_data_orderbook.rs
│   ├── test_risk_limits.rs
│   ├── test_execution_router.rs
│   ├── test_security_fixes.rs
│   └── test_router_security.rs
├── integration/                # Integration tests (slower)
│   ├── test_end_to_end.rs
│   ├── test_websocket.rs
│   ├── test_concurrent.rs
│   └── test_duckdb_storage.rs
├── property/                   # Property-based tests
│   └── test_order_invariants.rs
├── benchmarks/                 # Performance benchmarks
│   ├── critical_path_benchmarks.rs
│   ├── orderbook_bench.rs
│   └── performance_benchmarks.rs
├── fixtures/                   # Test utilities
│   ├── comprehensive_mocks.rs
│   ├── mock_data.rs
│   └── mod.rs
├── Cargo.toml                  # Test dependencies
└── lib.rs                      # Test exports
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          override: true

      - name: Run unit tests
        run: cargo test --lib --workspace

      - name: Run integration tests
        run: cargo test --test '*' --workspace

      - name: Run property tests
        run: cargo test --test test_order_invariants

      - name: Run benchmarks (validation only)
        run: cargo bench --no-run --workspace

      - name: Generate coverage
        run: |
          cargo install cargo-tarpaulin
          cargo tarpaulin --out Xml --workspace

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Data Management

### Environment Variables for Tests
```bash
# .env.test
ALPACA_API_KEY=test_key
ALPACA_SECRET_KEY=test_secret
RUST_LOG=debug
TEST_DATABASE_URL=sqlite::memory:
```

### Test Database Setup
```rust
#[tokio::test]
async fn setup_test_db() -> Result<()> {
    let conn = duckdb::connect(":memory:")?;

    conn.execute("CREATE TABLE market_data_metrics (...)")?;
    conn.execute("CREATE TABLE strategy_metrics (...)")?;
    // ... other tables

    Ok(())
}
```

## Best Practices

### 1. Test Independence
- Each test should be completely independent
- No shared mutable state between tests
- Use fixtures/builders for test data

### 2. Clear Test Names
```rust
// ✅ Good
#[test]
fn test_limit_order_requires_price() { }

// ❌ Bad
#[test]
fn test1() { }
```

### 3. Arrange-Act-Assert Pattern
```rust
#[test]
fn test_position_pnl_calculation() {
    // Arrange
    let position = PositionBuilder::new()
        .average_price(100.0)
        .current_price(110.0)
        .quantity(100)
        .build();

    // Act
    let pnl = position.unrealized_pnl;

    // Assert
    assert_eq!(pnl, 1000.0);
}
```

### 4. Test Edge Cases
- Zero values
- Negative values
- Maximum values (u64::MAX, etc.)
- Empty collections
- Null/None values
- Boundary conditions

### 5. Mock External Dependencies
```rust
#[cfg(test)]
use mockall::predicate::*;
use mockall::mock;

mock! {
    ExchangeClient {
        fn submit_order(&self, order: Order) -> Result<()>;
    }
}
```

## Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| common | >95% |
| market-data | >90% |
| execution-engine | >90% |
| risk-manager | >95% |
| signal-bridge | >85% |

## Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Order creation | <100ns | TBD |
| OrderBook update | <500ns | TBD |
| Risk check | <1μs | TBD |
| Order routing | <100μs | TBD |
| Bar aggregation | <1μs | TBD |

## Troubleshooting

### Tests Failing
```bash
# Run with verbose output
cargo test -- --nocapture

# Run specific test
cargo test test_order_creation -- --nocapture

# Show test stdout
cargo test -- --show-output
```

### Slow Tests
```bash
# Show test durations
cargo test -- --show-output --test-threads=1

# Run tests in parallel (default)
cargo test --workspace
```

### Coverage Issues
```bash
# Check which lines are not covered
cargo tarpaulin --out Html --output-dir coverage

# Exclude test files from coverage
cargo tarpaulin --ignore-tests
```

## Future Enhancements

1. **Mutation Testing**: Use `cargo-mutants` to verify test quality
2. **Fuzzing**: Add `cargo-fuzz` for security-critical code
3. **Stress Testing**: Long-running tests under load
4. **Chaos Engineering**: Random failure injection
5. **Contract Testing**: API contract verification
6. **Visual Regression**: For dashboard components

## References

- [Rust Testing Book](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Proptest Documentation](https://altsysrq.github.io/proptest-book/)
- [Criterion Documentation](https://bheisler.github.io/criterion.rs/book/)
- [Mockall Documentation](https://docs.rs/mockall/)
