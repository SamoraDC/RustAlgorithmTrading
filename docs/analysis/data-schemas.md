# Data Schemas Analysis

## Executive Summary

This document defines the data schemas for the Rust algorithmic trading system, based on Alpaca Markets IEX real-time data feed. The schemas are designed for zero-copy deserialization, efficient memory layout, and sub-millisecond processing latency.

## 1. Alpaca IEX Data Feed Structure

### 1.1 WebSocket Endpoints

**Market Data Stream (IEX)**
- URL: `wss://stream.data.alpaca.markets/v2/iex`
- Authentication: API Key + Secret
- Latency: ~30-50ms typical

**Paper Trading Updates**
- URL: `wss://paper-api.alpaca.markets/stream`
- Purpose: Order fills, position updates, account status

### 1.2 Message Types

#### Trade Message
```json
{
  "T": "t",
  "S": "AAPL",
  "i": 52983525029461,
  "x": "V",
  "p": 173.25,
  "s": 100,
  "t": "2025-10-14T14:30:00.123456789Z",
  "c": ["@", "I"],
  "z": "C"
}
```

**Fields:**
- `T`: Message type ("t" = trade)
- `S`: Symbol ticker
- `i`: Trade ID (unique)
- `x`: Exchange code ("V" = IEX)
- `p`: Price (float64)
- `s`: Size (shares)
- `t`: Timestamp (RFC3339 with nanoseconds)
- `c`: Trade conditions (array)
- `z`: Tape ("A", "B", "C")

#### Quote Message (Top-of-Book)
```json
{
  "T": "q",
  "S": "AAPL",
  "bx": "V",
  "bp": 173.20,
  "bs": 500,
  "ax": "V",
  "ap": 173.25,
  "as": 300,
  "t": "2025-10-14T14:30:00.123456789Z",
  "c": ["R"],
  "z": "C"
}
```

**Fields:**
- `T`: Message type ("q" = quote)
- `S`: Symbol ticker
- `bx`: Bid exchange
- `bp`: Bid price
- `bs`: Bid size
- `ax`: Ask exchange
- `ap`: Ask price
- `as`: Ask size
- `t`: Timestamp
- `c`: Quote conditions
- `z`: Tape

#### Bar Message (OHLCV)
```json
{
  "T": "b",
  "S": "AAPL",
  "o": 173.10,
  "h": 173.50,
  "l": 173.00,
  "c": 173.25,
  "v": 125000,
  "t": "2025-10-14T14:30:00Z",
  "n": 1250,
  "vw": 173.23
}
```

**Fields:**
- `T`: Message type ("b" = bar)
- `S`: Symbol ticker
- `o`: Open price
- `h`: High price
- `l`: Low price
- `c`: Close price
- `v`: Volume
- `t`: Bar timestamp
- `n`: Number of trades
- `vw`: VWAP

## 2. Rust Data Schema Definitions

### 2.1 Core Market Data Types

```rust
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

/// Market data event types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "T")]
pub enum MarketDataEvent {
    #[serde(rename = "t")]
    Trade(Trade),
    #[serde(rename = "q")]
    Quote(Quote),
    #[serde(rename = "b")]
    Bar(Bar),
}

/// Individual trade execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    /// Symbol ticker
    #[serde(rename = "S")]
    pub symbol: String,

    /// Trade ID
    #[serde(rename = "i")]
    pub trade_id: u64,

    /// Exchange code
    #[serde(rename = "x")]
    pub exchange: String,

    /// Price in USD
    #[serde(rename = "p")]
    pub price: f64,

    /// Size in shares
    #[serde(rename = "s")]
    pub size: u32,

    /// Timestamp with nanosecond precision
    #[serde(rename = "t")]
    pub timestamp: DateTime<Utc>,

    /// Trade conditions
    #[serde(rename = "c")]
    pub conditions: Vec<String>,

    /// Tape (A, B, C)
    #[serde(rename = "z")]
    pub tape: String,
}

/// Top-of-book quote (bid/ask)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Quote {
    /// Symbol ticker
    #[serde(rename = "S")]
    pub symbol: String,

    /// Bid exchange
    #[serde(rename = "bx")]
    pub bid_exchange: String,

    /// Bid price
    #[serde(rename = "bp")]
    pub bid_price: f64,

    /// Bid size
    #[serde(rename = "bs")]
    pub bid_size: u32,

    /// Ask exchange
    #[serde(rename = "ax")]
    pub ask_exchange: String,

    /// Ask price
    #[serde(rename = "ap")]
    pub ask_price: f64,

    /// Ask size
    #[serde(rename = "as")]
    pub ask_size: u32,

    /// Timestamp
    #[serde(rename = "t")]
    pub timestamp: DateTime<Utc>,

    /// Quote conditions
    #[serde(rename = "c")]
    pub conditions: Vec<String>,

    /// Tape
    #[serde(rename = "z")]
    pub tape: String,
}

/// Aggregated OHLCV bar
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bar {
    /// Symbol ticker
    #[serde(rename = "S")]
    pub symbol: String,

    /// Open price
    #[serde(rename = "o")]
    pub open: f64,

    /// High price
    #[serde(rename = "h")]
    pub high: f64,

    /// Low price
    #[serde(rename = "l")]
    pub low: f64,

    /// Close price
    #[serde(rename = "c")]
    pub close: f64,

    /// Volume
    #[serde(rename = "v")]
    pub volume: u64,

    /// Bar timestamp
    #[serde(rename = "t")]
    pub timestamp: DateTime<Utc>,

    /// Number of trades
    #[serde(rename = "n")]
    pub trade_count: u32,

    /// Volume-weighted average price
    #[serde(rename = "vw")]
    pub vwap: f64,
}
```

### 2.2 Order Book Schema

```rust
use std::collections::BTreeMap;

/// Price level in order book
#[derive(Debug, Clone, Copy)]
pub struct PriceLevel {
    pub price: f64,
    pub size: u32,
    pub exchange: [u8; 4], // Fixed-size for efficiency
    pub timestamp: i64,     // Unix nanos
}

/// Order book (top-of-book from IEX quotes)
#[derive(Debug, Clone)]
pub struct OrderBook {
    pub symbol: String,

    /// Best bid (highest buy price)
    pub best_bid: Option<PriceLevel>,

    /// Best ask (lowest sell price)
    pub best_ask: Option<PriceLevel>,

    /// Last update timestamp
    pub last_update: i64,

    /// Update sequence number
    pub sequence: u64,
}

impl OrderBook {
    /// Calculate mid price
    pub fn mid_price(&self) -> Option<f64> {
        match (self.best_bid, self.best_ask) {
            (Some(bid), Some(ask)) => Some((bid.price + ask.price) / 2.0),
            _ => None,
        }
    }

    /// Calculate spread in basis points
    pub fn spread_bps(&self) -> Option<f64> {
        match (self.best_bid, self.best_ask) {
            (Some(bid), Some(ask)) => {
                Some((ask.price - bid.price) / bid.price * 10000.0)
            }
            _ => None,
        }
    }

    /// Calculate order book imbalance (-1 to 1)
    pub fn imbalance(&self) -> f64 {
        match (self.best_bid, self.best_ask) {
            (Some(bid), Some(ask)) => {
                let bid_notional = bid.price * bid.size as f64;
                let ask_notional = ask.price * ask.size as f64;
                (bid_notional - ask_notional) / (bid_notional + ask_notional)
            }
            _ => 0.0,
        }
    }
}
```

### 2.3 Position and Order State

```rust
use uuid::Uuid;

/// Order side
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Side {
    Buy,
    Sell,
}

/// Order type
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
}

/// Order status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    New,
    PartiallyFilled,
    Filled,
    Canceled,
    Rejected,
    PendingNew,
    PendingCancel,
}

/// Order state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub order_id: Uuid,
    pub symbol: String,
    pub side: Side,
    pub order_type: OrderType,
    pub quantity: u32,
    pub filled_quantity: u32,
    pub limit_price: Option<f64>,
    pub stop_price: Option<f64>,
    pub status: OrderStatus,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub filled_avg_price: Option<f64>,
}

impl Order {
    /// Remaining quantity to fill
    pub fn remaining_quantity(&self) -> u32 {
        self.quantity.saturating_sub(self.filled_quantity)
    }

    /// Check if order is terminal state
    pub fn is_terminal(&self) -> bool {
        matches!(
            self.status,
            OrderStatus::Filled | OrderStatus::Canceled | OrderStatus::Rejected
        )
    }
}

/// Position state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub quantity: i32, // Positive = long, negative = short
    pub avg_entry_price: f64,
    pub market_value: f64,
    pub unrealized_pnl: f64,
    pub realized_pnl: f64,
    pub last_update: DateTime<Utc>,
}

impl Position {
    /// Update position with new fill
    pub fn apply_fill(&mut self, side: Side, quantity: u32, price: f64) {
        let qty = quantity as i32;
        let signed_qty = match side {
            Side::Buy => qty,
            Side::Sell => -qty,
        };

        // Calculate realized P&L if closing/reducing position
        if (self.quantity > 0 && signed_qty < 0) || (self.quantity < 0 && signed_qty > 0) {
            let close_qty = signed_qty.abs().min(self.quantity.abs());
            self.realized_pnl += (price - self.avg_entry_price) * close_qty as f64
                * if self.quantity > 0 { 1.0 } else { -1.0 };
        }

        // Update position
        let old_qty = self.quantity;
        self.quantity += signed_qty;

        // Recalculate average entry price if increasing position
        if (old_qty >= 0 && signed_qty > 0) || (old_qty <= 0 && signed_qty < 0) {
            let old_notional = old_qty.abs() as f64 * self.avg_entry_price;
            let new_notional = qty as f64 * price;
            self.avg_entry_price = (old_notional + new_notional) / self.quantity.abs() as f64;
        }
    }

    /// Calculate unrealized P&L at current market price
    pub fn calculate_unrealized_pnl(&mut self, current_price: f64) {
        self.unrealized_pnl = (current_price - self.avg_entry_price) * self.quantity as f64;
        self.market_value = current_price * self.quantity.abs() as f64;
    }
}

/// Portfolio state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portfolio {
    pub cash: f64,
    pub positions: BTreeMap<String, Position>,
    pub pending_orders: Vec<Order>,
    pub total_equity: f64,
    pub total_pnl: f64,
}

impl Portfolio {
    /// Calculate total equity (cash + positions)
    pub fn calculate_equity(&mut self) {
        let positions_value: f64 = self.positions.values()
            .map(|p| p.market_value)
            .sum();
        self.total_equity = self.cash + positions_value;

        let total_unrealized: f64 = self.positions.values()
            .map(|p| p.unrealized_pnl)
            .sum();
        let total_realized: f64 = self.positions.values()
            .map(|p| p.realized_pnl)
            .sum();
        self.total_pnl = total_realized + total_unrealized;
    }
}
```

## 3. Storage Strategy

### 3.1 Hot Path (In-Memory)

**Lock-Free Structures**
- Use `crossbeam::queue::ArrayQueue` for event queues
- Use `dashmap::DashMap` for concurrent symbol lookups
- Use `parking_lot::RwLock` for order book (read-heavy)

**Memory Layout**
```rust
/// Cache-aligned market data cache
#[repr(align(64))] // CPU cache line
pub struct MarketDataCache {
    pub order_books: DashMap<String, OrderBook>,
    pub last_trades: DashMap<String, Trade>,
    pub last_quotes: DashMap<String, Quote>,
}
```

### 3.2 Cold Path (Persistent Storage)

**Parquet Schema for Historical Bars**
```
message Bar {
  required int64 timestamp;
  required binary symbol (STRING);
  required double open;
  required double high;
  required double low;
  required double close;
  required int64 volume;
  optional int32 trade_count;
  optional double vwap;
}
```

**Parquet Schema for Trades**
```
message Trade {
  required int64 timestamp;
  required binary symbol (STRING);
  required int64 trade_id;
  required double price;
  required int32 size;
  required binary exchange (STRING);
  repeated binary conditions (STRING);
}
```

**File Organization**
```
data/
  historical/
    bars/
      daily/
        AAPL/
          2024/
            AAPL_2024-01.parquet
            AAPL_2024-02.parquet
      minute/
        AAPL/
          2024-01/
            AAPL_2024-01-01.parquet
    trades/
      AAPL/
        2024-01/
          AAPL_2024-01-01.parquet
```

### 3.3 Message Queue Format

**ZeroMQ PUB/SUB Messages**
```rust
/// Wire format for IPC
#[derive(Serialize, Deserialize)]
pub struct MarketDataMessage {
    pub topic: String,      // Symbol ticker
    pub sequence: u64,      // Monotonic sequence
    pub timestamp: i64,     // Unix nanos
    pub payload: MarketDataEvent,
}
```

## 4. Performance Considerations

### 4.1 Serialization Strategy

- **Hot Path**: Zero-copy with `bincode` or `rkyv`
- **Cold Path**: Parquet with Snappy compression
- **Network**: JSON (Alpaca native) with `simd-json`

### 4.2 Memory Efficiency

**Size Estimates (per symbol)**
- OrderBook: 128 bytes
- Trade: 96 bytes
- Quote: 112 bytes
- Bar: 88 bytes

**Buffer Sizing**
- 10,000 trades/second → 960 KB/s/symbol
- Ring buffer: 60s window = ~60 MB/symbol

### 4.3 Latency Targets

- WebSocket decode: <50 μs
- Order book update: <10 μs
- Event dispatch: <5 μs
- Total hot path: <100 μs

## 5. Data Quality and Validation

### 5.1 Sanity Checks

```rust
impl Trade {
    /// Validate trade data
    pub fn validate(&self) -> Result<(), String> {
        if self.price <= 0.0 {
            return Err("Invalid price".to_string());
        }
        if self.size == 0 {
            return Err("Invalid size".to_string());
        }
        if self.timestamp > Utc::now() {
            return Err("Future timestamp".to_string());
        }
        Ok(())
    }
}

impl Quote {
    /// Validate quote data
    pub fn validate(&self) -> Result<(), String> {
        if self.bid_price <= 0.0 || self.ask_price <= 0.0 {
            return Err("Invalid prices".to_string());
        }
        if self.bid_price >= self.ask_price {
            return Err("Crossed market".to_string());
        }
        if self.bid_size == 0 || self.ask_size == 0 {
            return Err("Invalid sizes".to_string());
        }
        Ok(())
    }
}
```

### 5.2 Gap Detection

```rust
/// Detect sequence gaps in market data
pub struct SequenceTracker {
    symbol: String,
    last_sequence: u64,
    gap_count: u64,
}

impl SequenceTracker {
    pub fn check(&mut self, sequence: u64) -> Option<u64> {
        if sequence != self.last_sequence + 1 {
            let gap = sequence - self.last_sequence - 1;
            self.gap_count += gap;
            self.last_sequence = sequence;
            Some(gap)
        } else {
            self.last_sequence = sequence;
            None
        }
    }
}
```

## 6. Schema Evolution Strategy

### 6.1 Versioning

```rust
#[derive(Serialize, Deserialize)]
pub struct VersionedEvent {
    pub version: u32,
    pub event: MarketDataEvent,
}
```

### 6.2 Backward Compatibility

- Use `#[serde(default)]` for new fields
- Use `Option<T>` for optional fields
- Document breaking changes clearly
- Maintain parsers for legacy versions

## Next Steps

1. Implement parsers with `serde_json` and `simd-json`
2. Create unit tests with sample fixtures
3. Benchmark serialization/deserialization performance
4. Implement Parquet writers with `parquet` crate
5. Design metrics collection schema (separate doc)

## References

- Alpaca Market Data API: https://alpaca.markets/docs/api-references/market-data-api/
- IEX Cloud Reference: https://iexcloud.io/docs/
- Apache Parquet Format: https://parquet.apache.org/docs/
