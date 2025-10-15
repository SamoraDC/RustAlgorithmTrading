# ZeroMQ Messaging Protocol

This document describes the ZeroMQ (ZMQ) messaging protocol used for inter-component communication in the trading system.

## Table of Contents

1. [Overview](#overview)
2. [Message Format](#message-format)
3. [Topic Structure](#topic-structure)
4. [Message Types](#message-types)
5. [Communication Patterns](#communication-patterns)
6. [Implementation Guide](#implementation-guide)
7. [Best Practices](#best-practices)

## Overview

ZeroMQ provides low-latency, high-throughput messaging between system components using a publish-subscribe (PUB/SUB) pattern.

### Why ZeroMQ?

1. **Performance**: <10μs message latency, millions of messages/second
2. **Simplicity**: No message broker required (brokerless architecture)
3. **Reliability**: Automatic reconnection, buffering, and backpressure
4. **Flexibility**: Multiple transport protocols (TCP, IPC, inproc)
5. **Language Agnostic**: Bindings for Rust, Python, C++, Go, etc.

### Architecture

```
Component A (Publisher)          Component B (Subscriber)
        │                                 │
        │ ZMQ PUB Socket                  │ ZMQ SUB Socket
        │ tcp://*:5555                    │ tcp://localhost:5555
        │                                 │
        │─────── Message ────────────────▶│
        │   [Topic][Payload]              │
        │                                 │
        │                                 │ Filter by topic prefix
        │                                 ▼
        │                            Process message
```

## Message Format

All messages use the following wire format:

```
┌──────────────┬────────────────────────────────┐
│ Topic (str)  │ Payload (JSON)                 │
├──────────────┼────────────────────────────────┤
│ market.trade │ {"symbol":"AAPL","price":...}  │
└──────────────┴────────────────────────────────┘
```

### Wire Protocol

ZMQ uses multi-part messages:

```rust
// Part 1: Topic (UTF-8 string)
let topic = b"market.trade";

// Part 2: Payload (JSON-serialized)
let payload = serde_json::to_vec(&message)?;

// Send as multi-part message
socket.send_multipart([topic, &payload], 0)?;
```

### Message Envelope

Each message payload is wrapped in a common envelope:

```json
{
  "type": "OrderBookUpdate",
  "timestamp": "2024-10-14T20:30:00.123456Z",
  "sequence": 12345,
  "data": {
    // Type-specific data
  }
}
```

## Topic Structure

Topics follow a hierarchical naming convention:

```
<component>.<message_type>[.<symbol>]

Examples:
  market.trade.AAPL      - Trade update for AAPL
  market.quote.MSFT      - Quote update for MSFT
  market.bar.GOOGL       - Bar update for GOOGL
  signal.generated       - Trading signal
  risk.approved          - Risk-approved order
  risk.rejected          - Risk-rejected order
  order.submitted        - Order submitted to exchange
  order.filled           - Order fill update
  system.heartbeat       - Component health check
```

### Topic Filtering

Subscribers use prefix matching:

```rust
// Subscribe to all market data
socket.set_subscribe(b"market.")?;

// Subscribe to AAPL trades only
socket.set_subscribe(b"market.trade.AAPL")?;

// Subscribe to all signals
socket.set_subscribe(b"signal.")?;

// Subscribe to everything (use with caution!)
socket.set_subscribe(b"")?;
```

## Message Types

### 1. Market Data Messages

#### Trade Update

**Topic**: `market.trade.<symbol>`

**Payload**:
```json
{
  "type": "TradeUpdate",
  "data": {
    "symbol": "AAPL",
    "price": 150.25,
    "quantity": 100.0,
    "side": "Buy",
    "timestamp": "2024-10-14T20:30:00.123456Z",
    "trade_id": "12345"
  }
}
```

**Rust Type**:
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub symbol: Symbol,
    pub price: Price,
    pub quantity: Quantity,
    pub side: Side,
    pub timestamp: DateTime<Utc>,
    pub trade_id: String,
}
```

#### Order Book Update

**Topic**: `market.orderbook.<symbol>`

**Payload**:
```json
{
  "type": "OrderBookUpdate",
  "data": {
    "symbol": "AAPL",
    "bids": [
      {"price": 150.24, "quantity": 1000.0, "timestamp": "..."},
      {"price": 150.23, "quantity": 500.0, "timestamp": "..."}
    ],
    "asks": [
      {"price": 150.26, "quantity": 800.0, "timestamp": "..."},
      {"price": 150.27, "quantity": 1200.0, "timestamp": "..."}
    ],
    "timestamp": "2024-10-14T20:30:00.123456Z",
    "sequence": 12345
  }
}
```

#### Bar Update (OHLCV)

**Topic**: `market.bar.<symbol>`

**Payload**:
```json
{
  "type": "BarUpdate",
  "data": {
    "symbol": "AAPL",
    "open": 150.20,
    "high": 150.50,
    "low": 150.15,
    "close": 150.45,
    "volume": 10000.0,
    "timestamp": "2024-10-14T20:30:00Z"
  }
}
```

### 2. Signal Messages

#### Signal Generated

**Topic**: `signal.generated`

**Payload**:
```json
{
  "type": "SignalGenerated",
  "data": {
    "symbol": "AAPL",
    "action": "Buy",
    "confidence": 0.85,
    "features": [0.5, 0.3, 0.2],
    "timestamp": "2024-10-14T20:30:00.123456Z"
  }
}
```

**Rust Type**:
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signal {
    pub symbol: Symbol,
    pub action: SignalAction,  // Buy, Sell, Hold
    pub confidence: f64,       // 0.0 to 1.0
    pub features: Vec<f64>,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignalAction {
    Buy,
    Sell,
    Hold,
}
```

### 3. Risk Management Messages

#### Risk Check Request

**Topic**: `risk.check`

**Payload**:
```json
{
  "type": "RiskCheck",
  "data": {
    "order": {
      "order_id": "order-123",
      "symbol": "AAPL",
      "side": "Buy",
      "order_type": "Limit",
      "quantity": 100.0,
      "price": 150.00
    }
  }
}
```

#### Risk Check Result

**Topic**: `risk.approved` or `risk.rejected`

**Payload**:
```json
{
  "type": "RiskCheckResult",
  "data": {
    "approved": true,
    "reason": null
  }
}

// Or for rejection:
{
  "type": "RiskCheckResult",
  "data": {
    "approved": false,
    "reason": "Exceeds max position size limit"
  }
}
```

### 4. Execution Messages

#### Order Request

**Topic**: `order.request`

**Payload**:
```json
{
  "type": "OrderRequest",
  "data": {
    "order_id": "order-123",
    "client_order_id": "my-order-456",
    "symbol": "AAPL",
    "side": "Buy",
    "order_type": "Limit",
    "quantity": 100.0,
    "price": 150.00,
    "stop_price": null,
    "status": "Pending",
    "filled_quantity": 0.0,
    "average_price": null,
    "created_at": "2024-10-14T20:30:00Z",
    "updated_at": "2024-10-14T20:30:00Z"
  }
}
```

#### Order Response

**Topic**: `order.submitted`, `order.filled`, `order.rejected`

**Payload**:
```json
{
  "type": "OrderResponse",
  "data": {
    "order_id": "order-123",
    "client_order_id": "my-order-456",
    "success": true,
    "error": null
  }
}
```

### 5. Position Updates

**Topic**: `position.update`

**Payload**:
```json
{
  "type": "PositionUpdate",
  "data": {
    "symbol": "AAPL",
    "side": "Bid",
    "quantity": 100.0,
    "entry_price": 150.00,
    "current_price": 150.50,
    "unrealized_pnl": 50.0,
    "realized_pnl": 0.0,
    "opened_at": "2024-10-14T20:00:00Z",
    "updated_at": "2024-10-14T20:30:00Z"
  }
}
```

### 6. System Messages

#### Heartbeat

**Topic**: `system.heartbeat`

**Payload**:
```json
{
  "type": "Heartbeat",
  "data": {
    "component": "market-data",
    "timestamp": "2024-10-14T20:30:00Z"
  }
}
```

#### Shutdown

**Topic**: `system.shutdown`

**Payload**:
```json
{
  "type": "Shutdown"
}
```

## Communication Patterns

### Pattern 1: PUB/SUB (Primary)

Used for broadcasting data to multiple subscribers.

**Publisher**:
```rust
use zmq::{Context, Socket, PUB};

pub struct Publisher {
    socket: Socket,
}

impl Publisher {
    pub fn new(address: &str) -> Result<Self> {
        let context = Context::new();
        let socket = context.socket(PUB)?;
        socket.bind(address)?;

        // Allow time for subscribers to connect
        std::thread::sleep(std::time::Duration::from_millis(100));

        Ok(Self { socket })
    }

    pub fn publish<T: Serialize>(&self, topic: &str, message: &T) -> Result<()> {
        let payload = serde_json::to_vec(message)?;
        self.socket.send_multipart([topic.as_bytes(), &payload], 0)?;
        Ok(())
    }
}
```

**Subscriber**:
```rust
use zmq::{Context, Socket, SUB};

pub struct Subscriber {
    socket: Socket,
}

impl Subscriber {
    pub fn new(address: &str, topics: &[&str]) -> Result<Self> {
        let context = Context::new();
        let socket = context.socket(SUB)?;
        socket.connect(address)?;

        // Subscribe to topics
        for topic in topics {
            socket.set_subscribe(topic.as_bytes())?;
        }

        Ok(Self { socket })
    }

    pub async fn receive(&self) -> Result<(String, Message)> {
        let msg = self.socket.recv_multipart(0)?;

        let topic = String::from_utf8(msg[0].clone())?;
        let message: Message = serde_json::from_slice(&msg[1])?;

        Ok((topic, message))
    }
}
```

### Pattern 2: REQ/REP (Future)

Used for synchronous request-response communication (e.g., querying account balance).

**Server**:
```rust
let context = Context::new();
let socket = context.socket(REP)?;
socket.bind("tcp://*:5559")?;

loop {
    let request: Request = socket.recv_json()?;
    let response = handle_request(request).await?;
    socket.send(serde_json::to_vec(&response)?, 0)?;
}
```

**Client**:
```rust
let context = Context::new();
let socket = context.socket(REQ)?;
socket.connect("tcp://localhost:5559")?;

let request = Request::GetBalance;
socket.send(serde_json::to_vec(&request)?, 0)?;
let response: Response = socket.recv_json()?;
```

### Pattern 3: PUSH/PULL (Future)

Used for load balancing tasks across multiple workers.

## Implementation Guide

### Setting Up ZMQ in Rust

Add to `Cargo.toml`:
```toml
[dependencies]
zmq = "0.10"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

### Complete Publisher Example

```rust
use zmq::{Context, PUB};
use serde::{Serialize, Deserialize};
use common::{Message, Trade};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let context = Context::new();
    let socket = context.socket(PUB)?;
    socket.bind("tcp://*:5555")?;

    // Allow subscribers to connect
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    loop {
        // Generate trade update
        let trade = Trade {
            symbol: Symbol("AAPL".into()),
            price: Price(150.25),
            quantity: Quantity(100.0),
            side: Side::Bid,
            timestamp: Utc::now(),
            trade_id: uuid::Uuid::new_v4().to_string(),
        };

        // Publish message
        let topic = format!("market.trade.{}", trade.symbol);
        let message = Message::TradeUpdate(trade);
        let payload = serde_json::to_vec(&message)?;

        socket.send_multipart([topic.as_bytes(), &payload], 0)?;

        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
}
```

### Complete Subscriber Example

```rust
use zmq::{Context, SUB};
use common::Message;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let context = Context::new();
    let socket = context.socket(SUB)?;
    socket.connect("tcp://localhost:5555")?;

    // Subscribe to all market data
    socket.set_subscribe(b"market.")?;

    loop {
        // Receive message
        let msg = socket.recv_multipart(0)?;

        let topic = String::from_utf8(msg[0].clone())?;
        let message: Message = serde_json::from_slice(&msg[1])?;

        // Process message
        match message {
            Message::TradeUpdate(trade) => {
                println!("Trade: {} @ {}", trade.symbol, trade.price);
            }
            Message::OrderBookUpdate(orderbook) => {
                println!("Order Book: {}", orderbook.symbol);
            }
            _ => {}
        }
    }
}
```

## Best Practices

### 1. Use Typed Messages

Define all message types in a shared `common` crate:

```rust
// common/src/messaging.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum Message {
    TradeUpdate(Trade),
    OrderBookUpdate(OrderBook),
    BarUpdate(Bar),
    SignalGenerated(Signal),
    // ... other types
}
```

### 2. Handle Deserialization Errors

```rust
match serde_json::from_slice::<Message>(&msg[1]) {
    Ok(message) => process_message(message).await?,
    Err(e) => {
        tracing::error!(?e, "Failed to deserialize message");
        continue;
    }
}
```

### 3. Set High Water Marks

Prevent memory exhaustion during backpressure:

```rust
socket.set_sndhwm(10000)?;  // Max 10,000 messages in send buffer
socket.set_rcvhwm(10000)?;  // Max 10,000 messages in receive buffer
```

### 4. Use TCP_NODELAY

Disable Nagle's algorithm for lower latency:

```rust
socket.set_tcp_keepalive(1)?;
socket.set_tcp_keepalive_idle(60)?;
```

### 5. Implement Heartbeats

Send periodic heartbeats to detect component failures:

```rust
tokio::spawn(async move {
    let mut interval = tokio::time::interval(Duration::from_secs(30));
    loop {
        interval.tick().await;
        publisher.publish("system.heartbeat", &Heartbeat {
            component: "market-data".into(),
            timestamp: Utc::now(),
        })?;
    }
});
```

### 6. Log All Messages (Debug Mode)

```rust
#[cfg(debug_assertions)]
tracing::debug!(topic = %topic, ?message, "Published message");
```

### 7. Use Async I/O

ZMQ operations are blocking. Use Tokio's blocking thread pool:

```rust
tokio::task::spawn_blocking(move || {
    socket.recv_multipart(0)
}).await??;
```

Or use async-zmq wrapper:
```toml
[dependencies]
async-zmq = "0.4"
```

### 8. Monitor Message Rates

Track messages per second with Prometheus:

```rust
use metrics::counter;

counter!("messages_published_total", "topic" => topic.clone()).increment(1);
```

### 9. Handle Reconnection

ZMQ automatically reconnects, but log connection events:

```rust
socket.set_reconnect_ivl(1000)?;       // Reconnect after 1s
socket.set_reconnect_ivl_max(60000)?;  // Max 60s between attempts
```

### 10. Test with Mock Publishers

Use in-memory ZMQ for testing:

```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_subscriber() {
        let context = Context::new();
        let pub_socket = context.socket(PUB).unwrap();
        pub_socket.bind("inproc://test").unwrap();

        let sub_socket = context.socket(SUB).unwrap();
        sub_socket.connect("inproc://test").unwrap();
        sub_socket.set_subscribe(b"test.").unwrap();

        // Test message exchange
    }
}
```

## Performance Tuning

### Optimize Message Size

Minimize JSON payload size:

```rust
// Instead of full precision floats:
{"price": 150.25000000000000}

// Use fixed precision:
{"price": 150.25}
```

### Batch Messages

Send multiple messages in a single ZMQ frame (future optimization):

```rust
let messages = vec![msg1, msg2, msg3];
let payload = serde_json::to_vec(&messages)?;
socket.send_multipart([b"batch", &payload], 0)?;
```

### Use Binary Serialization

For maximum performance, consider MessagePack or Protocol Buffers instead of JSON:

```toml
[dependencies]
rmp-serde = "1.1"  # MessagePack
```

```rust
use rmp_serde::{encode, decode};

let payload = encode::to_vec(&message)?;
socket.send_multipart([topic.as_bytes(), &payload], 0)?;
```

## Debugging

### Monitor Messages

Use `zmq_proxy` to log all messages:

```bash
# Install zmq tools
sudo apt install libzmq3-dev

# Run proxy
zmq_proxy -f tcp://localhost:5555 -b tcp://*:5556
```

### Message Inspector Script

```python
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5555")
socket.setsockopt_string(zmq.SUBSCRIBE, "")

while True:
    topic, payload = socket.recv_multipart()
    message = json.loads(payload)
    print(f"{topic.decode()}: {message}")
```

## References

- [ZeroMQ Guide](https://zguide.zeromq.org/)
- [zmq Rust Crate](https://docs.rs/zmq/latest/zmq/)
- [Serde JSON](https://docs.serde.rs/serde_json/)

---

**Last Updated**: 2024-10-14 | **Protocol Version**: 1.0
