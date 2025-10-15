# Rust API Reference

Complete API reference for all Rust crates in the py_rt trading system.

## Overview

The Rust layer provides high-performance components for:
- Real-time market data processing
- Order execution and routing
- Risk management and position tracking
- ZeroMQ messaging infrastructure

## Crate Structure

```
rust/
├── common/              # Shared types and utilities
│   ├── types.rs        # Domain types (Order, Trade, Bar)
│   ├── messaging.rs    # ZMQ message definitions
│   ├── errors.rs       # Error types
│   └── config.rs       # Configuration
├── market-data/        # Market data service
│   ├── websocket.rs    # WebSocket client
│   ├── orderbook.rs    # Order book management
│   ├── aggregation.rs  # Bar aggregation
│   └── publisher.rs    # ZMQ publisher
├── signal-bridge/      # Python ML integration
│   ├── lib.rs          # PyO3 bindings
│   ├── bridge.rs       # Rust-Python bridge
│   └── indicators.rs   # Technical indicators
├── risk-manager/       # Risk management
│   ├── limits.rs       # Risk limit checks
│   ├── pnl.rs          # P&L tracking
│   └── stops.rs        # Stop loss/take profit
└── execution-engine/   # Order execution
    ├── router.rs       # Order routing
    ├── retry.rs        # Retry logic
    └── slippage.rs     # Slippage protection
```

## Quick Links

### Core Crates
- [common](common/index.md) - Shared types and utilities
- [market-data](market-data/index.md) - Market data service
- [signal-bridge](signal-bridge/index.md) - Python integration
- [risk-manager](risk-manager/index.md) - Risk management
- [execution-engine](execution-engine/index.md) - Order execution

### Modules
- [Types](common/types.md) - Domain type definitions
- [Messaging](common/messaging.md) - ZMQ message protocol
- [Errors](common/errors.md) - Error handling
- [Config](common/config.md) - Configuration management

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
common = { path = "../common" }
tokio = { version = "1.40", features = ["full"] }
zmq = "0.10"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

## Basic Usage

### Market Data Service

```rust
use market_data::{WebSocketClient, OrderBook, Publisher};
use common::types::{Bar, Trade};
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create WebSocket client
    let ws_client = WebSocketClient::new(
        "YOUR_API_KEY".to_string(),
        "YOUR_SECRET_KEY".to_string(),
        vec!["AAPL".to_string(), "MSFT".to_string()],
    )?;

    // Create order book manager
    let mut order_books = OrderBook::new();

    // Create ZMQ publisher
    let publisher = Publisher::new("tcp://*:5555")?;

    // Create channel for WebSocket messages
    let (tx, mut rx) = mpsc::unbounded_channel();

    // Spawn WebSocket client
    tokio::spawn(async move {
        ws_client.connect(tx).await
    });

    // Process messages
    while let Some(msg) = rx.recv().await {
        match msg {
            Message::Trade(trade) => {
                // Update order book
                order_books.update(&trade);

                // Publish to subscribers
                publisher.publish_trade(&trade).await?;
            }
            Message::Quote(quote) => {
                // Handle quote update
                publisher.publish_quote(&quote).await?;
            }
            _ => {}
        }
    }

    Ok(())
}
```

### Risk Manager

```rust
use risk_manager::{RiskManager, RiskLimits, Position};
use common::types::Order;

// Initialize risk manager
let limits = RiskLimits {
    max_position_size: 10000.0,
    max_order_size: 1000.0,
    max_daily_loss: 5000.0,
    position_limit_pct: 0.1,
};

let mut risk_manager = RiskManager::new(limits);

// Check order against risk limits
let order = Order {
    symbol: "AAPL".to_string(),
    side: Side::Buy,
    quantity: 100,
    order_type: OrderType::Limit,
    limit_price: Some(150.0),
};

match risk_manager.check_order(&order).await {
    Ok(_) => {
        println!("Order approved");
        // Send to execution engine
    }
    Err(e) => {
        println!("Order rejected: {}", e);
    }
}
```

### Execution Engine

```rust
use execution_engine::{ExecutionEngine, OrderRouter};
use common::types::{Order, OrderResponse};

// Initialize execution engine
let engine = ExecutionEngine::new(
    "YOUR_API_KEY".to_string(),
    "YOUR_SECRET_KEY".to_string(),
    "https://paper-api.alpaca.markets".to_string(),
)?;

// Execute order with retry logic
let order = Order {
    symbol: "AAPL".to_string(),
    side: Side::Buy,
    quantity: 100,
    order_type: OrderType::Market,
    limit_price: None,
};

let response = engine.execute_order(order).await?;
match response.status {
    OrderStatus::Filled => {
        println!("Order filled at {}", response.filled_price);
    }
    OrderStatus::PartiallyFilled => {
        println!("Order partially filled: {}/{}",
                 response.filled_qty, order.quantity);
    }
    OrderStatus::Rejected => {
        println!("Order rejected: {}", response.reject_reason);
    }
    _ => {}
}
```

## Core Types

### Order

```rust
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub symbol: String,
    pub side: Side,
    pub quantity: u32,
    pub order_type: OrderType,
    pub limit_price: Option<f64>,
    pub stop_price: Option<f64>,
    pub time_in_force: TimeInForce,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Side {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TimeInForce {
    Day,
    GTC,  // Good 'til canceled
    IOC,  // Immediate or cancel
    FOK,  // Fill or kill
}
```

### Trade

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub symbol: String,
    pub price: f64,
    pub size: u32,
    pub timestamp: i64,  // Unix timestamp in microseconds
    pub exchange: String,
    pub conditions: Vec<String>,
}
```

### Bar (OHLCV)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bar {
    pub symbol: String,
    pub timestamp: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: u64,
    pub vwap: Option<f64>,
}
```

### Position

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub quantity: i64,  // Positive = long, negative = short
    pub avg_price: f64,
    pub market_value: f64,
    pub unrealized_pnl: f64,
    pub realized_pnl: f64,
}
```

## ZMQ Messaging

### Publisher

```rust
use zmq::{Context, Socket, PUB};
use serde_json;

pub struct Publisher {
    socket: Socket,
}

impl Publisher {
    pub fn new(address: &str) -> Result<Self, zmq::Error> {
        let context = Context::new();
        let socket = context.socket(PUB)?;
        socket.bind(address)?;
        Ok(Publisher { socket })
    }

    pub async fn publish<T: Serialize>(&self,
                                       topic: &str,
                                       message: &T) -> Result<(), Error> {
        let data = serde_json::to_vec(message)?;
        self.socket.send_multipart([topic.as_bytes(), &data], 0)?;
        Ok(())
    }
}
```

### Subscriber

```rust
use zmq::{Context, Socket, SUB};

pub struct Subscriber {
    socket: Socket,
}

impl Subscriber {
    pub fn new(address: &str, topics: &[&str]) -> Result<Self, zmq::Error> {
        let context = Context::new();
        let socket = context.socket(SUB)?;
        socket.connect(address)?;

        for topic in topics {
            socket.set_subscribe(topic.as_bytes())?;
        }

        Ok(Subscriber { socket })
    }

    pub async fn recv<T: DeserializeOwned>(&mut self) -> Result<(String, T), Error> {
        let msg = self.socket.recv_multipart(0)?;
        let topic = String::from_utf8(msg[0].clone())?;
        let data: T = serde_json::from_slice(&msg[1])?;
        Ok((topic, data))
    }
}
```

## Error Handling

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum Error {
    #[error("WebSocket error: {0}")]
    WebSocket(#[from] tungstenite::Error),

    #[error("ZMQ error: {0}")]
    Zmq(#[from] zmq::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Risk limit exceeded: {0}")]
    RiskLimit(String),

    #[error("Order rejected: {0}")]
    OrderRejected(String),

    #[error("API error: {0}")]
    Api(String),
}

pub type Result<T> = std::result::Result<T, Error>;
```

## Configuration

```rust
use serde::{Deserialize, Serialize};
use std::fs;

#[derive(Debug, Deserialize, Serialize)]
pub struct Config {
    pub market_data: MarketDataConfig,
    pub risk_manager: RiskManagerConfig,
    pub execution_engine: ExecutionEngineConfig,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct MarketDataConfig {
    pub alpaca_api_key: String,
    pub alpaca_secret_key: String,
    pub zmq_pub_address: String,
    pub symbols: Vec<String>,
    pub reconnect_delay_secs: u64,
}

impl Config {
    pub fn from_file(path: &str) -> Result<Self, Error> {
        let contents = fs::read_to_string(path)?;
        let config: Config = serde_json::from_str(&contents)?;
        Ok(config)
    }
}
```

## Async Runtime

All components use Tokio for async operations:

```rust
use tokio::runtime::Runtime;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create Tokio runtime
    let rt = Runtime::new()?;

    // Run async code
    rt.block_on(async {
        run_market_data_service().await
    })?;

    Ok(())
}
```

## Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tokio::test;

    #[test]
    async fn test_order_execution() {
        let engine = ExecutionEngine::new_test();
        let order = Order {
            symbol: "AAPL".to_string(),
            side: Side::Buy,
            quantity: 100,
            order_type: OrderType::Market,
            limit_price: None,
        };

        let response = engine.execute_order(order).await.unwrap();
        assert_eq!(response.status, OrderStatus::Filled);
    }
}
```

## Performance Benchmarks

```bash
# Run benchmarks
cargo bench

# Benchmark specific component
cargo bench --package market-data
```

Example benchmark results:
```
test orderbook_update    ... bench:      1,234 ns/iter (+/- 89)
test zmq_publish         ... bench:      8,456 ns/iter (+/- 321)
test risk_check          ... bench:        567 ns/iter (+/- 43)
```

## Documentation Generation

Generate Rust documentation:

```bash
# Generate docs
cargo doc --no-deps --open

# Generate with private items
cargo doc --no-deps --document-private-items --open
```

## Next Steps

- [Python API Reference](../python/index.md)
- [REST API](../rest/index.md)
- [ZMQ Protocol](../zmq/index.md)
- [Developer Guide](../../developer/contributing.md)

---

**Last Updated**: 2025-10-14
