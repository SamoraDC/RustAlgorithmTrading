# Sample Data Fixtures

## Purpose

This document provides sample data fixtures for testing the algorithmic trading system. These fixtures represent realistic Alpaca IEX market data events and system states.

## 1. Market Data Fixtures

### 1.1 Trade Events

**Normal Trade - AAPL**
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

**Large Block Trade - SPY**
```json
{
  "T": "t",
  "S": "SPY",
  "i": 52983525029462,
  "x": "V",
  "p": 445.67,
  "s": 50000,
  "t": "2025-10-14T14:30:01.234567890Z",
  "c": ["@", "I", "B"],
  "z": "C"
}
```

**Odd Lot Trade - TSLA**
```json
{
  "T": "t",
  "S": "TSLA",
  "i": 52983525029463,
  "x": "V",
  "p": 242.18,
  "s": 7,
  "t": "2025-10-14T14:30:02.345678901Z",
  "c": ["@", "I", "O"],
  "z": "C"
}
```

### 1.2 Quote Events

**Normal Quote - AAPL**
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

**Wide Spread Quote - Low Liquidity**
```json
{
  "T": "q",
  "S": "GME",
  "bx": "V",
  "bp": 22.50,
  "bs": 100,
  "ax": "V",
  "ap": 22.75,
  "as": 100,
  "t": "2025-10-14T14:30:01.234567890Z",
  "c": ["R"],
  "z": "C"
}
```

**Tight Spread Quote - High Liquidity**
```json
{
  "T": "q",
  "S": "SPY",
  "bx": "V",
  "bp": 445.66,
  "bs": 10000,
  "ax": "V",
  "ap": 445.67,
  "as": 8000,
  "t": "2025-10-14T14:30:02.345678901Z",
  "c": ["R"],
  "z": "C"
}
```

### 1.3 Bar Events

**1-Minute Bar - AAPL**
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

**5-Minute Bar - SPY**
```json
{
  "T": "b",
  "S": "SPY",
  "o": 445.50,
  "h": 445.80,
  "l": 445.40,
  "c": 445.67,
  "v": 850000,
  "t": "2025-10-14T14:30:00Z",
  "n": 6420,
  "vw": 445.61
}
```

**Daily Bar - QQQ**
```json
{
  "T": "b",
  "S": "QQQ",
  "o": 385.20,
  "h": 387.50,
  "l": 384.80,
  "c": 386.45,
  "v": 45000000,
  "t": "2025-10-14T00:00:00Z",
  "n": 425000,
  "vw": 386.12
}
```

## 2. Order Book Fixtures

### 2.1 Normal Market Conditions

**AAPL Order Book**
```rust
OrderBook {
    symbol: "AAPL".to_string(),
    best_bid: Some(PriceLevel {
        price: 173.20,
        size: 500,
        exchange: *b"IEX\0",
        timestamp: 1728922200123456789,
    }),
    best_ask: Some(PriceLevel {
        price: 173.25,
        size: 300,
        exchange: *b"IEX\0",
        timestamp: 1728922200123456789,
    }),
    last_update: 1728922200123456789,
    sequence: 12345,
}
```

**SPY Order Book (High Liquidity)**
```rust
OrderBook {
    symbol: "SPY".to_string(),
    best_bid: Some(PriceLevel {
        price: 445.66,
        size: 10000,
        exchange: *b"IEX\0",
        timestamp: 1728922201234567890,
    }),
    best_ask: Some(PriceLevel {
        price: 445.67,
        size: 8000,
        exchange: *b"IEX\0",
        timestamp: 1728922201234567890,
    }),
    last_update: 1728922201234567890,
    sequence: 12346,
}
```

### 2.2 Stress Conditions

**Crossed Market (Invalid)**
```rust
// Should be rejected by validation
OrderBook {
    symbol: "TEST".to_string(),
    best_bid: Some(PriceLevel {
        price: 100.50,  // Bid > Ask (invalid!)
        size: 100,
        exchange: *b"IEX\0",
        timestamp: 1728922202345678901,
    }),
    best_ask: Some(PriceLevel {
        price: 100.25,
        size: 100,
        exchange: *b"IEX\0",
        timestamp: 1728922202345678901,
    }),
    last_update: 1728922202345678901,
    sequence: 12347,
}
```

**Wide Spread (Low Liquidity)**
```rust
OrderBook {
    symbol: "RARE".to_string(),
    best_bid: Some(PriceLevel {
        price: 10.00,
        size: 50,
        exchange: *b"IEX\0",
        timestamp: 1728922203456789012,
    }),
    best_ask: Some(PriceLevel {
        price: 10.50,  // 5% spread
        size: 50,
        exchange: *b"IEX\0",
        timestamp: 1728922203456789012,
    }),
    last_update: 1728922203456789012,
    sequence: 12348,
}
```

## 3. Position and Order Fixtures

### 3.1 Order States

**New Market Order**
```rust
Order {
    order_id: Uuid::parse_str("550e8400-e29b-41d4-a716-446655440000").unwrap(),
    symbol: "AAPL".to_string(),
    side: Side::Buy,
    order_type: OrderType::Market,
    quantity: 100,
    filled_quantity: 0,
    limit_price: None,
    stop_price: None,
    status: OrderStatus::New,
    created_at: Utc::now(),
    updated_at: Utc::now(),
    filled_avg_price: None,
}
```

**Partially Filled Limit Order**
```rust
Order {
    order_id: Uuid::parse_str("550e8400-e29b-41d4-a716-446655440001").unwrap(),
    symbol: "SPY".to_string(),
    side: Side::Sell,
    order_type: OrderType::Limit,
    quantity: 1000,
    filled_quantity: 650,
    limit_price: Some(445.75),
    stop_price: None,
    status: OrderStatus::PartiallyFilled,
    created_at: Utc::now() - Duration::seconds(30),
    updated_at: Utc::now(),
    filled_avg_price: Some(445.76),
}
```

**Filled Stop Loss Order**
```rust
Order {
    order_id: Uuid::parse_str("550e8400-e29b-41d4-a716-446655440002").unwrap(),
    symbol: "TSLA".to_string(),
    side: Side::Sell,
    order_type: OrderType::Stop,
    quantity: 50,
    filled_quantity: 50,
    limit_price: None,
    stop_price: Some(240.00),
    status: OrderStatus::Filled,
    created_at: Utc::now() - Duration::minutes(5),
    updated_at: Utc::now(),
    filled_avg_price: Some(239.85),
}
```

**Rejected Order**
```rust
Order {
    order_id: Uuid::parse_str("550e8400-e29b-41d4-a716-446655440003").unwrap(),
    symbol: "GME".to_string(),
    side: Side::Buy,
    order_type: OrderType::Market,
    quantity: 10000,  // Exceeds buying power
    filled_quantity: 0,
    limit_price: None,
    stop_price: None,
    status: OrderStatus::Rejected,
    created_at: Utc::now(),
    updated_at: Utc::now(),
    filled_avg_price: None,
}
```

### 3.2 Position States

**Long Position with Profit**
```rust
Position {
    symbol: "AAPL".to_string(),
    quantity: 500,
    avg_entry_price: 170.50,
    market_value: 86625.0,  // 500 * 173.25
    unrealized_pnl: 1375.0,  // (173.25 - 170.50) * 500
    realized_pnl: 0.0,
    last_update: Utc::now(),
}
```

**Short Position with Loss**
```rust
Position {
    symbol: "TSLA".to_string(),
    quantity: -100,
    avg_entry_price: 235.00,
    market_value: 24218.0,  // 100 * 242.18
    unrealized_pnl: -718.0,  // (235.00 - 242.18) * 100
    realized_pnl: 0.0,
    last_update: Utc::now(),
}
```

**Flat Position (Recently Closed)**
```rust
Position {
    symbol: "SPY".to_string(),
    quantity: 0,
    avg_entry_price: 444.50,
    market_value: 0.0,
    unrealized_pnl: 0.0,
    realized_pnl: 585.0,  // Closed at 445.67, bought at 444.50, 500 shares
    last_update: Utc::now(),
}
```

### 3.3 Portfolio States

**Active Portfolio**
```rust
Portfolio {
    cash: 50000.0,
    positions: {
        "AAPL": Position {
            symbol: "AAPL".to_string(),
            quantity: 500,
            avg_entry_price: 170.50,
            market_value: 86625.0,
            unrealized_pnl: 1375.0,
            realized_pnl: 0.0,
            last_update: Utc::now(),
        },
        "SPY": Position {
            symbol: "SPY".to_string(),
            quantity: 200,
            avg_entry_price: 440.00,
            market_value: 89134.0,
            unrealized_pnl: 1134.0,
            realized_pnl: 0.0,
            last_update: Utc::now(),
        },
    }.into_iter().collect(),
    pending_orders: vec![],
    total_equity: 227134.0,  // 50000 + 86625 + 89134 + 1375 + 1134
    total_pnl: 2509.0,
}
```

## 4. Time Series Fixtures

### 4.1 Historical Bars (Parquet)

**Sample Daily Bars - AAPL (Jan 2024)**
```
timestamp,symbol,open,high,low,close,volume,trade_count,vwap
2024-01-02T00:00:00Z,AAPL,185.64,186.95,184.90,185.64,82291644,780123,185.82
2024-01-03T00:00:00Z,AAPL,184.35,185.29,183.92,184.25,80738456,765234,184.51
2024-01-04T00:00:00Z,AAPL,182.15,184.26,180.93,181.91,98678432,892456,182.34
2024-01-05T00:00:00Z,AAPL,181.27,183.09,180.17,181.18,92456783,845678,181.52
```

**Sample Minute Bars - SPY (Intraday)**
```
timestamp,symbol,open,high,low,close,volume,trade_count,vwap
2025-10-14T14:30:00Z,SPY,445.50,445.60,445.45,445.55,125000,1250,445.52
2025-10-14T14:31:00Z,SPY,445.55,445.70,445.52,445.67,142000,1380,445.61
2025-10-14T14:32:00Z,SPY,445.67,445.75,445.60,445.72,135000,1320,445.68
2025-10-14T14:33:00Z,SPY,445.72,445.80,445.68,445.75,128000,1240,445.74
```

### 4.2 Tick Data (Trades)

**AAPL Trade Stream (5 seconds)**
```json
[
  {"T":"t","S":"AAPL","i":1,"x":"V","p":173.20,"s":100,"t":"2025-10-14T14:30:00.100Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":2,"x":"V","p":173.21,"s":50,"t":"2025-10-14T14:30:00.250Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":3,"x":"V","p":173.22,"s":200,"t":"2025-10-14T14:30:00.500Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":4,"x":"V","p":173.23,"s":75,"t":"2025-10-14T14:30:00.750Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":5,"x":"V","p":173.25,"s":150,"t":"2025-10-14T14:30:01.000Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":6,"x":"V","p":173.24,"s":100,"t":"2025-10-14T14:30:01.250Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":7,"x":"V","p":173.26,"s":300,"t":"2025-10-14T14:30:01.500Z","c":["@","I"],"z":"C"},
  {"T":"t","S":"AAPL","i":8,"x":"V","p":173.25,"s":50,"t":"2025-10-14T14:30:01.750Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":9,"x":"V","p":173.27,"s":125,"t":"2025-10-14T14:30:02.000Z","c":["@"],"z":"C"},
  {"T":"t","S":"AAPL","i":10,"x":"V","p":173.28,"s":200,"t":"2025-10-14T14:30:02.250Z","c":["@","I"],"z":"C"}
]
```

## 5. Test Scenarios

### 5.1 Normal Trading Day

**Sequence**: Market Open → Steady Trading → Market Close
- 5,000 trades per symbol
- Quote updates every 100ms
- 1-minute bars generated
- No gaps or anomalies

### 5.2 High Volatility Event

**Sequence**: Normal → News Event → Spike → Recovery
- 50,000 trades in 5 minutes
- Price moves 10% in 30 seconds
- Spread widens to 0.5%
- Order book imbalance >80%

### 5.3 Connection Loss Recovery

**Sequence**: Normal → Disconnect → Reconnect → Catch Up
- Gap in sequence numbers
- Missed 1000 messages
- Requires snapshot request
- Recovery in 2 seconds

### 5.4 End of Day Settlement

**Sequence**: Trading → Close → Position Settlement
- All orders canceled
- Positions marked to market
- Daily P&L calculated
- Portfolio state saved

## 6. Usage in Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_trade() {
        let json = r#"{
            "T": "t",
            "S": "AAPL",
            "i": 52983525029461,
            "x": "V",
            "p": 173.25,
            "s": 100,
            "t": "2025-10-14T14:30:00.123456789Z",
            "c": ["@", "I"],
            "z": "C"
        }"#;

        let trade: Trade = serde_json::from_str(json).unwrap();
        assert_eq!(trade.symbol, "AAPL");
        assert_eq!(trade.price, 173.25);
        assert_eq!(trade.size, 100);
        assert!(trade.validate().is_ok());
    }

    #[test]
    fn test_order_book_metrics() {
        let book = OrderBook {
            symbol: "AAPL".to_string(),
            best_bid: Some(PriceLevel {
                price: 173.20,
                size: 500,
                exchange: *b"IEX\0",
                timestamp: 1728922200123456789,
            }),
            best_ask: Some(PriceLevel {
                price: 173.25,
                size: 300,
                exchange: *b"IEX\0",
                timestamp: 1728922200123456789,
            }),
            last_update: 1728922200123456789,
            sequence: 12345,
        };

        assert_eq!(book.mid_price(), Some(173.225));
        assert!(book.spread_bps().unwrap() < 3.0);
        assert!(book.imbalance().abs() < 0.3);
    }

    #[test]
    fn test_position_pnl_calculation() {
        let mut position = Position {
            symbol: "AAPL".to_string(),
            quantity: 500,
            avg_entry_price: 170.50,
            market_value: 0.0,
            unrealized_pnl: 0.0,
            realized_pnl: 0.0,
            last_update: Utc::now(),
        };

        position.calculate_unrealized_pnl(173.25);
        assert_eq!(position.unrealized_pnl, 1375.0);
        assert_eq!(position.market_value, 86625.0);
    }
}
```

## 7. Fixture Files Location

```
tests/
  fixtures/
    market_data/
      trades_normal.json
      trades_stress.json
      quotes_normal.json
      quotes_wide_spread.json
      bars_daily.csv
      bars_minute.csv
    orders/
      orders_various_states.json
      fills_sequence.json
    positions/
      positions_mixed.json
      portfolio_snapshot.json
    scenarios/
      normal_trading_day.json
      high_volatility_event.json
      connection_recovery.json
```

## References

- Use `include_str!` macro to load fixtures in tests
- Generate additional fixtures with `proptest` for fuzzing
- Validate all fixtures against JSON schemas
