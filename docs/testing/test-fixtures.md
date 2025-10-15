# Test Fixtures Specification
## Rust Algorithmic Trading System

**Document Version:** 1.0
**Last Updated:** 2025-10-14

---

## Overview

This document specifies the test fixtures and mock data structures used throughout the testing suite. All fixtures are designed to be:

- **Realistic**: Based on actual market data patterns
- **Reproducible**: Deterministic generation using seeded RNGs
- **Comprehensive**: Cover common, edge, and error cases
- **Maintainable**: Centralized fixture management

---

## Directory Structure

```
tests/
  fixtures/
    market_data/
      snapshots/
        orderbook_AAPL_deep.json          # 1000 levels
        orderbook_AAPL_sparse.json        # 10 levels
        orderbook_AAPL_crossed.json       # Invalid (bid > ask)
      deltas/
        updates_AAPL_normal.json          # Standard update sequence
        updates_AAPL_gap.json             # Sequence gap scenario
        updates_AAPL_aggressive.json      # High-frequency updates
      ticks/
        ticks_SPY_1min.csv                # 1 minute of SPY ticks
        ticks_TSLA_volatile.csv           # High volatility period
        ticks_AAPL_open.csv               # Market open behavior
    orders/
      valid/
        market_orders.json
        limit_orders.json
        stop_orders.json
      invalid/
        negative_quantity.json
        invalid_price.json
        unknown_symbol.json
    fills/
      complete/
        market_fill_immediate.json
        limit_fill_partial_then_complete.json
      partial/
        partial_fill_queue.json
      rejected/
        rejected_insufficient_balance.json
        rejected_risk_limit.json
    positions/
      simple/
        long_position_single_fill.json
        short_position_single_fill.json
      complex/
        multiple_partial_fills.json
        averaged_position.json
    risk/
      scenarios/
        within_limits.json
        exceeding_position_limit.json
        exceeding_notional_limit.json
        circuit_breaker_triggered.json
```

---

## Market Data Fixtures

### 1. Order Book Snapshots

#### 1.1 Deep Order Book (AAPL)

**File:** `tests/fixtures/market_data/snapshots/orderbook_AAPL_deep.json`

```json
{
  "symbol": "AAPL",
  "timestamp": "2025-10-14T14:30:00.000Z",
  "lastUpdateId": 123456789,
  "bids": [
    [175.50, 100],
    [175.49, 250],
    [175.48, 500],
    ...
    [170.00, 10000]
  ],
  "asks": [
    [175.51, 150],
    [175.52, 300],
    [175.53, 450],
    ...
    [180.00, 15000]
  ]
}
```

**Properties:**
- 1000 price levels each side
- Spread: $0.01 (1 cent)
- Total bid volume: 1,500,000 shares
- Total ask volume: 1,600,000 shares
- Best bid: $175.50
- Best ask: $175.51

#### 1.2 Sparse Order Book (Low Liquidity)

**File:** `tests/fixtures/market_data/snapshots/orderbook_AAPL_sparse.json`

```json
{
  "symbol": "AAPL",
  "timestamp": "2025-10-14T20:00:00.000Z",
  "lastUpdateId": 123456790,
  "bids": [
    [175.40, 10],
    [175.30, 5],
    [175.00, 20],
    [174.50, 50],
    [174.00, 100]
  ],
  "asks": [
    [175.60, 15],
    [175.80, 8],
    [176.00, 25],
    [176.50, 60],
    [177.00, 120]
  ]
}
```

**Properties:**
- Only 5 price levels each side
- Wide spread: $0.20 (20 cents)
- Low liquidity: Total <500 shares
- Use case: Test behavior in illiquid markets

#### 1.3 Crossed Order Book (Invalid)

**File:** `tests/fixtures/market_data/snapshots/orderbook_AAPL_crossed.json`

```json
{
  "symbol": "AAPL",
  "timestamp": "2025-10-14T14:31:00.000Z",
  "lastUpdateId": 123456791,
  "bids": [
    [175.55, 100]
  ],
  "asks": [
    [175.50, 150]
  ]
}
```

**Properties:**
- Best bid ($175.55) > Best ask ($175.50) - INVALID
- Use case: Test error detection and handling

---

### 2. Order Book Delta Updates

#### 2.1 Normal Update Sequence

**File:** `tests/fixtures/market_data/deltas/updates_AAPL_normal.json`

```json
[
  {
    "symbol": "AAPL",
    "timestamp": "2025-10-14T14:30:01.000Z",
    "firstUpdateId": 123456790,
    "lastUpdateId": 123456790,
    "bids": [
      [175.50, 120]  // Quantity update
    ],
    "asks": []
  },
  {
    "symbol": "AAPL",
    "timestamp": "2025-10-14T14:30:01.100Z",
    "firstUpdateId": 123456791,
    "lastUpdateId": 123456791,
    "bids": [],
    "asks": [
      [175.51, 0]    // Remove price level
    ]
  },
  {
    "symbol": "AAPL",
    "timestamp": "2025-10-14T14:30:01.200Z",
    "firstUpdateId": 123456792,
    "lastUpdateId": 123456792,
    "bids": [
      [175.52, 500]  // New price level
    ],
    "asks": []
  }
]
```

**Properties:**
- Sequential update IDs (no gaps)
- Mix of updates, deletions, insertions
- 100ms intervals

#### 2.2 Sequence Gap Scenario

**File:** `tests/fixtures/market_data/deltas/updates_AAPL_gap.json`

```json
[
  {
    "firstUpdateId": 123456790,
    "lastUpdateId": 123456790,
    ...
  },
  {
    "firstUpdateId": 123456795,  // GAP: missing 791-794
    "lastUpdateId": 123456795,
    ...
  }
]
```

**Properties:**
- Gap in sequence numbers
- Use case: Test snapshot re-request logic

---

### 3. Tick Data

#### 3.1 Standard Tick Stream (SPY)

**File:** `tests/fixtures/market_data/ticks/ticks_SPY_1min.csv`

```csv
timestamp,symbol,price,size,side
2025-10-14T14:30:00.001Z,SPY,450.25,100,BUY
2025-10-14T14:30:00.015Z,SPY,450.26,50,BUY
2025-10-14T14:30:00.032Z,SPY,450.25,75,SELL
2025-10-14T14:30:00.048Z,SPY,450.24,200,SELL
...
2025-10-14T14:31:00.000Z,SPY,450.30,150,BUY
```

**Properties:**
- 1 minute of data (60,000ms)
- ~500 ticks (avg 120ms between ticks)
- Price range: $450.20 - $450.35
- Total volume: 50,000 shares
- Use case: Tick-to-bar aggregation tests

#### 3.2 High Volatility Period (TSLA)

**File:** `tests/fixtures/market_data/ticks/ticks_TSLA_volatile.csv`

```csv
timestamp,symbol,price,size,side
2025-10-14T14:30:00.001Z,TSLA,250.00,100,BUY
2025-10-14T14:30:00.050Z,TSLA,252.50,500,BUY
2025-10-14T14:30:00.100Z,TSLA,248.00,1000,SELL
2025-10-14T14:30:00.150Z,TSLA,255.00,750,BUY
...
```

**Properties:**
- Large price swings (+/- 5% in seconds)
- High frequency (20ms avg)
- Large size variation (100 - 2000 shares)
- Use case: Test volatility handling, circuit breakers

---

## Order Fixtures

### 4. Valid Orders

#### 4.1 Market Orders

**File:** `tests/fixtures/orders/valid/market_orders.json`

```json
[
  {
    "order_id": "TEST-MKT-001",
    "client_order_id": "CLIENT-001",
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 100,
    "timestamp": "2025-10-14T14:30:00.000Z"
  },
  {
    "order_id": "TEST-MKT-002",
    "client_order_id": "CLIENT-002",
    "symbol": "SPY",
    "side": "SELL",
    "order_type": "MARKET",
    "quantity": 50,
    "timestamp": "2025-10-14T14:31:00.000Z"
  }
]
```

#### 4.2 Limit Orders

**File:** `tests/fixtures/orders/valid/limit_orders.json`

```json
[
  {
    "order_id": "TEST-LMT-001",
    "client_order_id": "CLIENT-003",
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "quantity": 100,
    "price": 175.00,
    "time_in_force": "GTC",
    "timestamp": "2025-10-14T14:30:00.000Z"
  },
  {
    "order_id": "TEST-LMT-002",
    "client_order_id": "CLIENT-004",
    "symbol": "TSLA",
    "side": "SELL",
    "order_type": "LIMIT",
    "quantity": 200,
    "price": 252.50,
    "time_in_force": "IOC",
    "timestamp": "2025-10-14T14:32:00.000Z"
  }
]
```

#### 4.3 Stop-Loss Orders

**File:** `tests/fixtures/orders/valid/stop_orders.json`

```json
[
  {
    "order_id": "TEST-STOP-001",
    "client_order_id": "CLIENT-005",
    "symbol": "AAPL",
    "side": "SELL",
    "order_type": "STOP_LOSS",
    "quantity": 100,
    "stop_price": 170.00,
    "timestamp": "2025-10-14T14:30:00.000Z"
  },
  {
    "order_id": "TEST-STOP-002",
    "client_order_id": "CLIENT-006",
    "symbol": "SPY",
    "side": "SELL",
    "order_type": "STOP_LIMIT",
    "quantity": 50,
    "stop_price": 445.00,
    "limit_price": 444.00,
    "timestamp": "2025-10-14T14:35:00.000Z"
  }
]
```

---

### 5. Invalid Orders

#### 5.1 Negative Quantity

**File:** `tests/fixtures/orders/invalid/negative_quantity.json`

```json
{
  "order_id": "TEST-INVALID-001",
  "symbol": "AAPL",
  "side": "BUY",
  "order_type": "MARKET",
  "quantity": -100,
  "expected_error": "INVALID_QUANTITY"
}
```

#### 5.2 Invalid Price

**File:** `tests/fixtures/orders/invalid/invalid_price.json`

```json
{
  "order_id": "TEST-INVALID-002",
  "symbol": "AAPL",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": 100,
  "price": -175.00,
  "expected_error": "INVALID_PRICE"
}
```

---

## Fill Fixtures

### 6. Complete Fills

#### 6.1 Immediate Market Fill

**File:** `tests/fixtures/fills/complete/market_fill_immediate.json`

```json
{
  "fill_id": "FILL-001",
  "order_id": "TEST-MKT-001",
  "client_order_id": "CLIENT-001",
  "symbol": "AAPL",
  "side": "BUY",
  "quantity": 100,
  "filled_quantity": 100,
  "avg_fill_price": 175.51,
  "commission": 1.00,
  "fill_timestamp": "2025-10-14T14:30:00.050Z",
  "execution_details": [
    {
      "price": 175.51,
      "quantity": 100,
      "timestamp": "2025-10-14T14:30:00.050Z"
    }
  ]
}
```

#### 6.2 Limit Order Partial Then Complete Fill

**File:** `tests/fixtures/fills/complete/limit_fill_partial_then_complete.json`

```json
{
  "fill_id": "FILL-002",
  "order_id": "TEST-LMT-001",
  "client_order_id": "CLIENT-003",
  "symbol": "AAPL",
  "side": "BUY",
  "quantity": 100,
  "filled_quantity": 100,
  "avg_fill_price": 175.00,
  "commission": 1.00,
  "execution_details": [
    {
      "price": 175.00,
      "quantity": 30,
      "timestamp": "2025-10-14T14:30:05.000Z"
    },
    {
      "price": 175.00,
      "quantity": 70,
      "timestamp": "2025-10-14T14:30:15.000Z"
    }
  ]
}
```

---

### 7. Partial Fills

**File:** `tests/fixtures/fills/partial/partial_fill_queue.json`

```json
{
  "fill_id": "FILL-003",
  "order_id": "TEST-LMT-002",
  "client_order_id": "CLIENT-004",
  "symbol": "TSLA",
  "side": "SELL",
  "quantity": 200,
  "filled_quantity": 75,
  "remaining_quantity": 125,
  "avg_fill_price": 252.50,
  "commission": 0.38,
  "status": "PARTIALLY_FILLED",
  "execution_details": [
    {
      "price": 252.50,
      "quantity": 75,
      "timestamp": "2025-10-14T14:32:10.000Z"
    }
  ]
}
```

---

## Position Fixtures

### 8. Simple Positions

#### 8.1 Long Position Single Fill

**File:** `tests/fixtures/positions/simple/long_position_single_fill.json`

```json
{
  "position_id": "POS-001",
  "symbol": "AAPL",
  "side": "LONG",
  "quantity": 100,
  "avg_entry_price": 175.51,
  "current_price": 176.25,
  "unrealized_pnl": 74.00,
  "realized_pnl": 0.00,
  "commission_paid": 1.00,
  "open_timestamp": "2025-10-14T14:30:00.050Z"
}
```

---

### 9. Complex Positions

#### 9.1 Multiple Partial Fills (Averaging)

**File:** `tests/fixtures/positions/complex/multiple_partial_fills.json`

```json
{
  "position_id": "POS-002",
  "symbol": "SPY",
  "side": "LONG",
  "quantity": 150,
  "avg_entry_price": 450.33,
  "fill_history": [
    {"quantity": 50, "price": 450.25, "timestamp": "2025-10-14T14:30:00.000Z"},
    {"quantity": 75, "price": 450.35, "timestamp": "2025-10-14T14:31:00.000Z"},
    {"quantity": 25, "price": 450.40, "timestamp": "2025-10-14T14:32:00.000Z"}
  ],
  "current_price": 450.50,
  "unrealized_pnl": 25.50,
  "commission_paid": 1.50
}
```

**Calculation Verification:**
```
Avg entry = (50*450.25 + 75*450.35 + 25*450.40) / 150
          = (22512.50 + 33776.25 + 11260.00) / 150
          = 67548.75 / 150
          = 450.325 ≈ 450.33

Unrealized P&L = 150 * (450.50 - 450.33) = 150 * 0.17 = 25.50
```

---

## Risk Scenario Fixtures

### 10. Within Limits

**File:** `tests/fixtures/risk/scenarios/within_limits.json`

```json
{
  "scenario": "WITHIN_LIMITS",
  "current_state": {
    "open_positions": 5,
    "total_notional_exposure": 50000.00,
    "daily_pnl": 250.00
  },
  "risk_limits": {
    "max_open_positions": 10,
    "max_notional_exposure": 100000.00,
    "max_daily_loss": -5000.00
  },
  "proposed_order": {
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 100,
    "estimated_cost": 17550.00
  },
  "expected_result": "APPROVED"
}
```

### 11. Exceeding Limits

#### 11.1 Position Limit

**File:** `tests/fixtures/risk/scenarios/exceeding_position_limit.json`

```json
{
  "scenario": "EXCEEDING_POSITION_LIMIT",
  "current_state": {
    "symbol": "AAPL",
    "current_position": 900,
    "max_position_size": 1000
  },
  "proposed_order": {
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 200
  },
  "expected_result": "REJECTED",
  "expected_reason": "POSITION_LIMIT_EXCEEDED",
  "violation_details": {
    "current_position": 900,
    "order_quantity": 200,
    "resulting_position": 1100,
    "max_allowed": 1000
  }
}
```

---

## Fixture Loading Utilities

### Rust Helper Functions

```rust
// tests/common/fixtures.rs

use serde::de::DeserializeOwned;
use std::fs;
use std::path::Path;

pub fn load_fixture<T: DeserializeOwned>(relative_path: &str) -> T {
    let base = Path::new("tests/fixtures");
    let full_path = base.join(relative_path);
    let data = fs::read_to_string(full_path)
        .expect(&format!("Failed to read fixture: {}", relative_path));
    serde_json::from_str(&data)
        .expect(&format!("Failed to parse fixture: {}", relative_path))
}

// Example usage:
// let snapshot: OrderBookSnapshot = load_fixture("market_data/snapshots/orderbook_AAPL_deep.json");
```

---

## Fixture Maintenance

### Guidelines

1. **Version Control**: All fixtures committed to git
2. **Naming Convention**: `{type}_{symbol}_{scenario}.{ext}`
3. **Documentation**: Each fixture file includes header comment with description
4. **Validation**: CI validates fixture format on commit
5. **Size Limits**: Max 1MB per fixture file (use compression for large datasets)

### Update Process

```bash
# Validate fixtures
make validate-fixtures

# Regenerate synthetic fixtures
make generate-fixtures

# Update from live data (captured snapshots)
make capture-live-fixtures --symbol AAPL --duration 60s
```

---

## Appendix: Synthetic Data Generation

### Market Data Generator Parameters

```rust
pub struct MarketDataGeneratorConfig {
    pub symbol: String,
    pub initial_price: f64,
    pub volatility_annual: f64,        // e.g., 0.25 for 25% annual vol
    pub drift_annual: f64,             // e.g., 0.05 for 5% annual drift
    pub tick_frequency_ms: u64,        // avg milliseconds between ticks
    pub jump_probability: f64,         // probability of large jump
    pub jump_size_range: (f64, f64),   // jump size as fraction of price
    pub order_book_depth: usize,       // number of price levels
    pub spread_bps: f64,               // spread in basis points
}
```

---

**End of Test Fixtures Specification**
