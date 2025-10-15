# Rust Algorithmic Trading System

Production-ready algorithmic trading system built with Rust, featuring WebSocket market data feeds, ML-powered signal generation, risk management, and smart order execution.

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Market Data    │─────▶│  Signal Bridge   │─────▶│  Risk Manager   │
│  (WebSocket)    │      │  (Rust + Python) │      │  (Position Mgmt)│
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                                             │
                                                             ▼
┌─────────────────┐                              ┌─────────────────┐
│     Common      │◀────────────────────────────▶│   Execution     │
│  (Shared Types) │                              │    Engine       │
└─────────────────┘                              └─────────────────┘
```

## Workspace Structure

This is a Cargo workspace containing 5 crates:

### 1. `common` - Shared Types and Utilities
Core domain types used across all components:
- Trading types: Symbol, Price, Quantity, Order, Position, Trade, Bar
- Messaging protocol: ZMQ message types for inter-component communication
- Error handling: Unified TradingError type
- Configuration: System-wide config structures

### 2. `market-data` - Market Data Feed
Real-time market data processing:
- **WebSocket Client**: Connects to exchange WebSocket feeds (Binance, Coinbase, etc.)
- **Order Book Manager**: Reconstructs and maintains order book state with BTreeMap
- **Bar Aggregator**: Tick-to-bar aggregation for OHLCV candles
- **ZMQ Publisher**: Broadcasts market data to other components

**Key Dependencies:**
- `tokio-tungstenite` - WebSocket connections
- `zmq` - Inter-process messaging
- `metrics` - Performance tracking
- `tracing` - Structured logging

### 3. `signal-bridge` - Signal Generation (Rust + Python Bridge)
Bridges Python ML models with Rust feature engineering:
- **Feature Engine**: High-performance feature computation in Rust
- **Technical Indicators**: RSI, MACD, Bollinger Bands, ATR implementations
- **PyO3 Bindings**: Python can call Rust functions for feature computation
- **Signal Integration**: Subscribes to market data, generates trading signals

**Key Dependencies:**
- `pyo3` - Python bindings for seamless Rust ↔ Python integration
- `ta` - Technical analysis indicators library
- `ndarray` - Numerical computing

### 4. `risk-manager` - Risk Management
Multi-layered risk controls:
- **Limit Checker**: Position size limits, notional exposure caps
- **P&L Tracker**: Real-time profit/loss tracking with FIFO/LIFO/weighted average
- **Stop Manager**: Static and trailing stop-loss triggers
- **Circuit Breaker**: Automatic trading pause on anomalies

**Key Features:**
- Pre-trade risk checks
- Real-time position monitoring
- Configurable risk parameters
- Defensive programming for tail risks

### 5. `execution-engine` - Order Execution
Smart order routing and execution:
- **Order Router**: Routes orders to exchanges with retry logic
- **Retry Policy**: Exponential backoff for failed orders
- **Slippage Estimator**: Estimates market impact before execution
- **Rate Limiting**: Respects exchange API rate limits

**Key Dependencies:**
- `reqwest` - HTTP client for exchange APIs
- `governor` - Rate limiting

## Key Dependencies Summary

| Dependency | Version | Purpose |
|------------|---------|---------|
| `tokio` | 1.38 | Async runtime for all I/O operations |
| `tokio-tungstenite` | 0.23 | WebSocket client implementation |
| `serde` | 1.0 | Serialization/deserialization |
| `zmq` | 0.10 | Inter-process messaging (PUB/SUB, REQ/REP) |
| `pyo3` | 0.21 | Python bindings for ML integration |
| `metrics` | 0.23 | Performance metrics collection |
| `tracing` | 0.1 | Structured logging with spans |
| `chrono` | 0.4 | High-precision timestamps |
| `anyhow` / `thiserror` | 1.0 | Error handling |

## Building the System

### Prerequisites
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install ZeroMQ (Linux)
sudo apt-get install libzmq3-dev

# Install ZeroMQ (macOS)
brew install zeromq
```

### Build All Crates
```bash
cd rust
cargo build --workspace --release
```

### Build Individual Crates
```bash
cargo build -p market-data --release
cargo build -p signal-bridge --release
cargo build -p risk-manager --release
cargo build -p execution-engine --release
```

### Run Tests
```bash
cargo test --workspace
```

### Check Code
```bash
# Format
cargo fmt --all

# Lint
cargo clippy --workspace --all-targets --all-features

# Type check
cargo check --workspace
```

## Configuration

All components load configuration from `config/system.json`:

```json
{
  "market_data": {
    "exchange": "binance",
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "websocket_url": "wss://stream.binance.com:9443/ws",
    "reconnect_delay_ms": 5000,
    "zmq_publish_address": "tcp://127.0.0.1:5555"
  },
  "risk": {
    "max_position_size": 10.0,
    "max_notional_exposure": 100000.0,
    "max_open_positions": 5,
    "stop_loss_percent": 2.0,
    "trailing_stop_percent": 1.5,
    "enable_circuit_breaker": true,
    "max_loss_threshold": 5000.0
  },
  "execution": {
    "exchange_api_url": "https://api.binance.com",
    "rate_limit_per_second": 10,
    "retry_attempts": 3,
    "retry_delay_ms": 1000,
    "paper_trading": true
  },
  "signal": {
    "model_path": "models/ml_model.pkl",
    "features": ["rsi", "macd", "bb", "volume"],
    "update_interval_ms": 1000,
    "zmq_subscribe_address": "tcp://127.0.0.1:5555",
    "zmq_publish_address": "tcp://127.0.0.1:5556"
  }
}
```

## Running the System

Each component runs as a separate process, communicating via ZMQ:

```bash
# Terminal 1: Market Data Feed
RUST_LOG=info ./target/release/market-data

# Terminal 2: Signal Bridge
RUST_LOG=info ./target/release/signal-bridge

# Terminal 3: Risk Manager
RUST_LOG=info ./target/release/risk-manager

# Terminal 4: Execution Engine
RUST_LOG=info ./target/release/execution-engine
```

## Python Integration (Signal Bridge)

The signal-bridge crate compiles to both a library and a Python module:

```python
# Import Rust-compiled feature computation
from signal_bridge import FeatureComputer

# Create feature computer instance
computer = FeatureComputer()

# Compute features (calls Rust under the hood)
features = computer.compute(price_data)

# Use with your ML model
prediction = ml_model.predict([features])
```

Build the Python module:
```bash
cd signal-bridge
pip install maturin
maturin develop --release
```

## Inter-Component Communication

Components communicate via ZMQ PUB/SUB pattern:

1. **Market Data** publishes to `tcp://127.0.0.1:5555`:
   - Order book updates
   - Trade updates
   - Bar updates

2. **Signal Bridge** subscribes to market data, publishes signals to `tcp://127.0.0.1:5556`

3. **Risk Manager** subscribes to signals and orders, enforces risk rules

4. **Execution Engine** subscribes to approved orders, executes on exchange

## Monitoring and Observability

### Metrics
All components export Prometheus metrics:
- Latency distributions (order processing, WebSocket roundtrip)
- Counters (orders sent, fills received)
- Gauges (current positions, unrealized P&L)

### Logging
Structured logging with `tracing`:
```bash
# Set log level
export RUST_LOG=info,market_data=debug,execution_engine=trace

# Run with detailed logs
RUST_LOG=debug ./target/release/market-data
```

### Log Format
```
2025-10-14T20:15:32.123Z INFO [market_data] WebSocket connected to wss://stream.binance.com
2025-10-14T20:15:32.456Z DEBUG [market_data::orderbook] Order book updated: BTCUSDT bid=42150.5 ask=42151.0
2025-10-14T20:15:33.789Z INFO [signal_bridge] Signal generated: BUY BTCUSDT confidence=0.87
```

## Development Roadmap

### Phase 1: Foundation ✅ (Current)
- [x] Workspace structure
- [x] Common types and messaging
- [x] Module skeletons with proper structure

### Phase 2: Market Data (Next)
- [ ] WebSocket connection implementation
- [ ] Order book reconstruction with sequence numbers
- [ ] Tick-to-bar aggregation
- [ ] ZMQ publisher implementation
- [ ] Binance integration
- [ ] Unit tests

### Phase 3: Signal Generation
- [ ] Technical indicator implementations
- [ ] Feature engineering
- [ ] PyO3 bindings finalization
- [ ] Python ML model integration
- [ ] Backtesting framework

### Phase 4: Risk & Execution
- [ ] Position tracking
- [ ] Risk limit enforcement
- [ ] Stop-loss triggers
- [ ] Order routing
- [ ] Slippage estimation
- [ ] Integration tests

### Phase 5: Production
- [ ] Docker containers
- [ ] Grafana dashboards
- [ ] Alert system
- [ ] Paper trading validation
- [ ] Performance optimization

## Performance Targets

- **Market Data Latency**: < 1ms order book update processing
- **Signal Generation**: < 10ms feature computation
- **Risk Checks**: < 100μs per order
- **Order Submission**: < 50ms end-to-end

## Design Principles

1. **Low Latency**: Memory-efficient data structures, cache-friendly layouts
2. **Reliability**: Defensive programming, comprehensive error handling
3. **Observability**: Structured logging, metrics everywhere
4. **Modularity**: Clear separation of concerns, testable components
5. **Safety**: Rust's type system prevents common bugs

## License

MIT License - See LICENSE file

## Contributing

This is a portfolio project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

**Built with ❤️ using Rust for production-ready algorithmic trading**
