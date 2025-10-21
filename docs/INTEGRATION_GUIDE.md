# Python-Rust Integration Guide

## Quick Start

### 1. Build Rust Components

```bash
cd rust
cargo build --release --workspace
```

### 2. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install alpaca-py python-dotenv loguru pyzmq
```

### 3. Configure Credentials

Create `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/.env`:

```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### 4. Test Components

```bash
# Test Alpaca connection
python src/api/alpaca_paper_trading.py

# Test Rust bridge (requires Rust build)
python src/bridge/rust_bridge.py

# Test ZMQ bridge
python src/bridge/zmq_bridge.py
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Python ML Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Strategy   │  │  Backtesting │  │   Alpaca     │      │
│  │   Models     │  │   Engine     │  │   Client     │      │
│  └───────┬──────┘  └──────────────┘  └──────┬───────┘      │
│          │                                    │              │
│  ┌───────▼──────────────────────────────────▼──────┐       │
│  │           Bridge Layer (This Work)              │       │
│  │  ┌──────────────┐      ┌──────────────────┐    │       │
│  │  │ Rust Bridge  │      │   ZMQ Bridge     │    │       │
│  │  │   (PyO3)     │      │  (Publisher/Sub) │    │       │
│  │  └──────┬───────┘      └────────┬─────────┘    │       │
└───────────┼──────────────────────────┼──────────────────────┘
            │                          │
            │ Feature Computation      │ Signals/Data
            │ (direct calls)           │ (async messaging)
            │                          │
┌───────────▼──────────────────────────▼──────────────────────┐
│                     Rust Trading Engine                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Market Data  │  │ Signal       │  │ Execution    │      │
│  │ Service      │  │ Bridge       │  │ Engine       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────ZMQ─────┴──────────────────┘              │
│                                                               │
│  ┌──────────────┐                      ┌──────────────┐     │
│  │ Risk Manager │                      │ Health Check │     │
│  └──────────────┘                      │ Endpoints    │     │
│                                         └──────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Integration

### 1. Rust Feature Computer (PyO3)

**Purpose**: Direct Python-to-Rust calls for high-performance indicators

**Python Side**:
```python
from src.bridge import RustFeatureComputer, MarketBar

# Initialize computer
computer = RustFeatureComputer()

# Create market bar
bar = MarketBar(
    symbol="AAPL",
    open=150.0,
    high=152.5,
    low=149.5,
    close=151.0,
    volume=1_000_000.0,
    timestamp=1234567890
)

# Compute features (3-10x faster than pure Python)
features = computer.compute_streaming(bar)
# Returns: [close, rsi, macd_line, macd_signal, macd_hist, ema_fast, ema_slow, spread, sma, dist_from_sma, volume, range_pct]
```

**Rust Side** (`signal-bridge/src/bridge.rs`):
```rust
#[pyclass]
pub struct FeatureComputer {
    rsi: RSI,
    macd: MACD,
    // ... other indicators
}

#[pymethods]
impl FeatureComputer {
    pub fn compute_streaming(&mut self, bar: &Bar) -> PyResult<Vec<f64>> {
        // Fast Rust computation with SIMD
        // Returns directly to Python
    }
}
```

**Build Requirement**:
```bash
cd rust
cargo build --release --package signal-bridge
# The .so/.pyd file goes to target/release/
export PYTHONPATH=$PWD/target/release:$PYTHONPATH
```

---

### 2. ZeroMQ Message Bridge

**Purpose**: Async communication between Python and Rust services

#### Python Publisher → Rust Subscriber

**Python**: Send trading signals to Rust execution engine
```python
from src.bridge import ZMQPublisher, Signal

async with ZMQPublisher("tcp://127.0.0.1:5556") as pub:
    signal = Signal(
        symbol="AAPL",
        direction="long",
        strength=0.85,
        timestamp=int(time.time() * 1000),
        features=[1.0, 2.0, 3.0],
        metadata={"strategy": "ml-predictor"}
    )
    await pub.publish_signal(signal)
```

**Rust**: Receive signals
```rust
// In execution-engine
let context = zmq::Context::new();
let subscriber = context.socket(zmq::SUB)?;
subscriber.connect("tcp://127.0.0.1:5556")?;
subscriber.set_subscribe(b"signal")?;

loop {
    let msg = subscriber.recv_string(0)?.unwrap();
    let parts: Vec<&str> = msg.splitn(2, ' ').collect();
    let signal: Signal = serde_json::from_str(parts[1])?;

    // Process signal
    handle_signal(signal).await?;
}
```

#### Rust Publisher → Python Subscriber

**Rust**: Publish market data
```rust
// In market-data
let publisher = context.socket(zmq::PUB)?;
publisher.bind("tcp://127.0.0.1:5555")?;

let message = Message::BarUpdate(bar);
let json = serde_json::to_string(&message)?;
publisher.send(&format!("market {}", json), 0)?;
```

**Python**: Receive market data
```python
from src.bridge import ZMQSubscriber

async with ZMQSubscriber("tcp://127.0.0.1:5555") as sub:
    await sub.connect(["market", "signal"])

    async for topic, message in sub.receive():
        if message["type"] == "BarUpdate":
            # Process bar update
            process_bar(message)
        elif message["type"] == "TradeUpdate":
            # Process trade
            process_trade(message)
```

---

### 3. Alpaca Paper Trading Integration

**Purpose**: Safe paper trading with comprehensive portfolio management

**Basic Usage**:
```python
from src.api.alpaca_paper_trading import AlpacaPaperTrading, OrderType

# Initialize (forced paper trading for safety)
client = AlpacaPaperTrading()

# Get account and portfolio
account = client.get_account_info()
metrics = client.get_portfolio_metrics()

print(f"Cash: ${metrics.cash}")
print(f"P&L: ${metrics.total_pl} ({metrics.total_pl_pct}%)")
print(f"Positions: {metrics.positions_count}")

# Place order with validation
order = client.place_order(
    symbol="AAPL",
    qty=10,
    side="buy",
    order_type=OrderType.LIMIT,
    limit_price=150.0,
    time_in_force="gtc"
)

print(f"Order placed: {order['id']} - Status: {order['status']}")

# Get positions
positions = client.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.qty} @ ${pos.avg_entry_price}")
    print(f"  P&L: ${pos.unrealized_pl} ({pos.unrealized_pl_pct}%)")

# Get historical data
from datetime import datetime, timedelta
bars = client.get_historical_bars(
    symbol="AAPL",
    start=datetime.now() - timedelta(days=10),
    end=datetime.now()
)
```

**Advanced Features**:
```python
# Validate order without submitting
order = client.place_order(
    symbol="AAPL",
    qty=100,
    side="buy",
    order_type=OrderType.MARKET,
    validate_only=True  # Don't actually place order
)

# Get latest quote
quote = client.get_latest_quote("AAPL")
print(f"Bid: ${quote['bid_price']}, Ask: ${quote['ask_price']}")
print(f"Spread: ${quote['ask_price'] - quote['bid_price']}")

# Close position
client.close_position("AAPL")

# Close all positions and cancel all orders
client.close_all_positions()
```

---

### 4. Health Check Endpoints

**Purpose**: Kubernetes-ready health probes for all services

**Rust Implementation**:
```rust
use common::{HealthCheck, start_health_server};
use std::sync::Arc;
use tokio::sync::RwLock;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Create health tracker
    let health = Arc::new(RwLock::new(HealthCheck::healthy("market-data")));

    // Start health server on port 8080
    let health_clone = health.clone();
    tokio::spawn(async move {
        if let Err(e) = start_health_server(8080, health_clone).await {
            tracing::error!("Health server error: {}", e);
        }
    });

    // Update health status
    {
        let mut h = health.write().await;
        *h = h.clone()
            .with_metric("websocket_connected", "true")
            .with_metric("messages_processed", "1234");
    }

    // Main service logic...
    Ok(())
}
```

**Health Endpoints**:

`GET http://localhost:8080/health`
```json
{
  "status": "healthy",
  "component": "market-data",
  "message": "All systems operational",
  "metrics": {
    "websocket_connected": "true",
    "messages_processed": "1234",
    "uptime_seconds": "3600"
  },
  "timestamp": "2025-10-21T17:00:00Z"
}
```

`GET http://localhost:8080/ready`
```json
{
  "ready": true,
  "component": "market-data",
  "timestamp": "2025-10-21T17:00:00Z"
}
```

`GET http://localhost:8080/live`
```
200 OK
"alive"
```

---

## End-to-End Integration Example

### Complete Trading System Flow

```python
import asyncio
from src.bridge import RustFeatureComputer, ZMQPublisher, ZMQSubscriber, Signal, MarketBar
from src.api.alpaca_paper_trading import AlpacaPaperTrading, OrderType

async def trading_system():
    # 1. Initialize components
    feature_computer = RustFeatureComputer()
    alpaca = AlpacaPaperTrading()

    # 2. Setup ZMQ communication
    signal_publisher = ZMQPublisher("tcp://127.0.0.1:5556")
    market_subscriber = ZMQSubscriber("tcp://127.0.0.1:5555")

    await signal_publisher.connect()
    await market_subscriber.connect(["market"])

    # 3. Main trading loop
    async for topic, message in market_subscriber.receive():
        if message["type"] == "BarUpdate":
            # Convert to MarketBar
            bar = MarketBar(
                symbol=message["symbol"],
                open=message["open"],
                high=message["high"],
                low=message["low"],
                close=message["close"],
                volume=message["volume"],
                timestamp=message["timestamp"]
            )

            # 4. Compute features using Rust (fast!)
            features = feature_computer.compute_streaming(bar)

            # 5. Make trading decision (your ML model here)
            prediction = your_ml_model.predict(features)

            # 6. Generate signal if prediction is strong
            if abs(prediction) > 0.7:
                signal = Signal(
                    symbol=bar.symbol,
                    direction="long" if prediction > 0 else "short",
                    strength=abs(prediction),
                    timestamp=bar.timestamp,
                    features=features
                )

                # 7. Send signal to execution engine via ZMQ
                await signal_publisher.publish_signal(signal)

                # 8. Place order via Alpaca
                if prediction > 0:
                    order = alpaca.place_order(
                        symbol=bar.symbol,
                        qty=10,
                        side="buy",
                        order_type=OrderType.MARKET
                    )
                    print(f"Order placed: {order['id']}")

# Run trading system
if __name__ == "__main__":
    asyncio.run(trading_system())
```

---

## Troubleshooting

### PyO3 Import Error

**Error**: `ImportError: No module named 'signal_bridge'`

**Solution**:
```bash
cd rust
cargo build --release --package signal-bridge
export PYTHONPATH=$PWD/target/release:$PYTHONPATH
python -c "import signal_bridge; print('Success!')"
```

### ZMQ Connection Error

**Error**: `zmq.error.ZMQError: Address already in use`

**Solution**:
```bash
# Check what's using the port
lsof -i :5555
# Kill the process or use a different port
```

### Alpaca API Error

**Error**: `ValueError: Alpaca credentials not found`

**Solution**:
```bash
# Create .env file with credentials
cat > .env << EOF
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
EOF
```

### Health Check Not Responding

**Error**: Connection refused on health endpoint

**Solution**:
```bash
# Check if service is running
ps aux | grep market-data

# Check logs
tail -f logs/market-data.log

# Verify port not in use
netstat -tlnp | grep 8080
```

---

## Performance Tips

### 1. PyO3 Bridge
- Use batch processing for multiple bars
- Pre-allocate feature vectors
- Minimize Python-Rust boundary crossings

### 2. ZMQ Bridge
- Use topic filtering to reduce network traffic
- Batch messages when possible
- Set appropriate high water marks

### 3. Alpaca API
- Respect rate limits (200/min)
- Use WebSocket for real-time data
- Cache historical data locally

---

## Next Steps

1. **Run Integration Tests**: Test end-to-end flow
2. **Performance Tuning**: Profile and optimize hot paths
3. **Monitoring**: Add Grafana dashboards
4. **Scaling**: Deploy multiple strategy instances
5. **Production**: Move to staging environment

---

For detailed implementation information, see `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/CODER_IMPLEMENTATION_COMPLETE.md`
