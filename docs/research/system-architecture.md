# System Architecture Design
## Rust Algorithmic Trading System

**Research Phase:** ✅ Complete
**Date:** 2025-10-14
**Status:** Ready for Implementation

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADING SYSTEM LAYERS                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: MARKET DATA INGESTION                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Alpaca WebSocket │  │ Polygon REST API │  │ Finnhub (Backup) │     │
│  │ - Real-time      │  │ - Historical     │  │ - Alternative    │     │
│  │ - Trades/Quotes  │  │ - EOD data       │  │ - Intl markets   │     │
│  │ - 200 req/min    │  │ - 5 req/min      │  │ - 60 req/min     │     │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘     │
│           │                     │                      │                │
│           └─────────────────────┼──────────────────────┘                │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: DATA NORMALIZATION & VALIDATION (Rust)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Normalization Engine (serde + custom parsers)                   │  │
│  │  - Parse JSON/Binary messages                                    │  │
│  │  - Validate data integrity                                       │  │
│  │  - Convert to unified data structures                            │  │
│  │  - Handle missing/malformed data                                 │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                                │                                         │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: CORE ENGINE (Tokio Async Runtime)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐ │
│  │ Market Data Store  │  │  Strategy Engine   │  │  Risk Manager    │ │
│  │ - In-memory cache  │  │  - Signal gen      │  │  - Position      │ │
│  │ - Order book       │  │  - Indicators      │  │  - Limits        │ │
│  │ - Historical bars  │  │  - Entry/exit      │  │  - Validation    │ │
│  └────────┬───────────┘  └────────┬───────────┘  └────────┬─────────┘ │
│           │                       │                        │            │
│           └───────────────────────┼────────────────────────┘            │
│                                   │                                     │
│  ┌────────────────────────────────┼──────────────────────────────────┐ │
│  │             Order Management System                                │ │
│  │  - Order creation, routing, execution                              │ │
│  │  - Position tracking and P&L calculation                           │ │
│  │  - Fill notifications and reconciliation                           │ │
│  └────────────────────────────────┬──────────────────────────────────┘ │
│                                    │                                    │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: EXECUTION & BROKER INTEGRATION                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Alpaca Trading API (Paper Trading → Live)                       │  │
│  │  - Market/Limit/Stop orders                                      │  │
│  │  - Position management                                            │  │
│  │  - Account information                                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

                                     ┃
                    ═════════════════╬═════════════════
                    OPTIONAL PYTHON LAYER (PyO3)
                    ═════════════════╬═════════════════
                                     ┃
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: STRATEGY DEVELOPMENT & ANALYSIS (Python)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐ │
│  │ Strategy Backtester│  │  Data Analysis     │  │  Visualization   │ │
│  │ - Vectorized       │  │  - NumPy/Pandas    │  │  - Matplotlib    │ │
│  │ - Historical data  │  │  - Statistics      │  │  - Plotly        │ │
│  │ - Performance      │  │  - ML features     │  │  - Reports       │ │
│  └────────────────────┘  └────────────────────┘  └──────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Market Data Ingestion

**Primary:** Alpaca WebSocket
- Real-time trades, quotes, bars
- Low-latency (<10ms target)
- Persistent connection with automatic reconnection
- Rate limit: 200 requests/min REST, 1 WebSocket connection

**Historical:** Polygon.io REST API
- Batch historical data retrieval
- 2 years of minute-level data (free tier)
- Cache locally for backtesting
- Rate limit: 5 requests/min

**Backup:** Finnhub
- Alternative data source
- International market coverage
- Prototyping and testing
- Rate limit: 60 requests/min

### 2. Data Normalization

**Technology:** serde + serde_json

```rust
#[derive(Debug, Serialize, Deserialize)]
pub struct Trade {
    pub symbol: String,
    pub price: f64,
    pub size: u32,
    pub timestamp: i64,
    pub exchange: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Bar {
    pub symbol: String,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: u64,
    pub timestamp: i64,
}
```

**Responsibilities:**
- Parse API-specific JSON formats
- Validate data integrity (price > 0, timestamp valid, etc.)
- Convert to unified internal structures
- Handle edge cases (missing fields, invalid data)

### 3. Core Engine Components

#### Market Data Store
```rust
pub struct MarketDataStore {
    trades: HashMap<String, VecDeque<Trade>>,
    quotes: HashMap<String, Quote>,
    bars: HashMap<String, Vec<Bar>>,
    order_book: HashMap<String, OrderBook>,
}
```

**Features:**
- In-memory cache for fast access
- Configurable retention policy (e.g., keep last 1000 trades)
- Thread-safe (Arc<RwLock<T>>)
- Efficient lookups

#### Strategy Engine
```rust
pub trait Strategy {
    fn on_trade(&mut self, trade: &Trade) -> Option<Signal>;
    fn on_bar(&mut self, bar: &Bar) -> Option<Signal>;
    fn on_quote(&mut self, quote: &Quote) -> Option<Signal>;
}

pub enum Signal {
    Buy { symbol: String, quantity: u32, limit_price: Option<f64> },
    Sell { symbol: String, quantity: u32, limit_price: Option<f64> },
    Hold,
}
```

**Features:**
- Pluggable strategy interface
- Multiple strategies running concurrently
- Signal aggregation and prioritization

#### Risk Manager
```rust
pub struct RiskManager {
    max_position_size: f64,
    max_portfolio_value: f64,
    daily_loss_limit: f64,
    position_limits: HashMap<String, f64>,
}

impl RiskManager {
    pub fn validate_order(&self, order: &Order, positions: &Positions) -> Result<(), RiskError>;
}
```

**Features:**
- Pre-trade risk checks
- Position size limits
- Portfolio value limits
- Daily loss limits
- Real-time position monitoring

#### Order Management System
```rust
pub struct OrderManager {
    pending_orders: HashMap<OrderId, Order>,
    filled_orders: Vec<Order>,
    positions: HashMap<String, Position>,
}

impl OrderManager {
    pub async fn submit_order(&mut self, order: Order) -> Result<OrderId, OrderError>;
    pub fn cancel_order(&mut self, order_id: OrderId) -> Result<(), OrderError>;
    pub fn get_positions(&self) -> &HashMap<String, Position>;
}
```

**Features:**
- Order lifecycle management (pending → filled → cancelled)
- Position tracking (entries, exits, P&L)
- Fill notifications and reconciliation
- Order status monitoring

### 4. Execution Layer

**Alpaca Trading API Integration:**
```rust
pub struct AlpacaClient {
    http_client: reqwest::Client,
    api_key: String,
    secret_key: String,
    base_url: String, // paper-api.alpaca.markets or api.alpaca.markets
}

impl AlpacaClient {
    pub async fn submit_order(&self, order: &Order) -> Result<OrderResponse, AlpacaError>;
    pub async fn get_positions(&self) -> Result<Vec<Position>, AlpacaError>;
    pub async fn get_account(&self) -> Result<Account, AlpacaError>;
    pub async fn cancel_order(&self, order_id: &str) -> Result<(), AlpacaError>;
}
```

### 5. Python Integration (Optional)

**PyO3 Bindings:**
```rust
#[pyclass]
pub struct TradingEngine {
    #[pyo3(get)]
    pub is_running: bool,
}

#[pymethods]
impl TradingEngine {
    #[new]
    fn new() -> Self {
        TradingEngine { is_running: false }
    }

    fn start(&mut self, symbols: Vec<String>) -> PyResult<()> {
        // Start Rust trading engine
        self.is_running = true;
        Ok(())
    }

    fn get_positions(&self) -> PyResult<Vec<(String, f64, f64)>> {
        // Return (symbol, quantity, avg_price)
        Ok(vec![])
    }
}
```

**Python Usage:**
```python
import trading_engine

# Create engine (Rust core)
engine = trading_engine.TradingEngine()

# Start trading
engine.start(["AAPL", "TSLA", "MSFT"])

# Get positions
positions = engine.get_positions()
for symbol, qty, price in positions:
    print(f"{symbol}: {qty} @ ${price}")
```

---

## Data Flow Diagram

```
┌─────────────┐
│ Alpaca WS   │ ────┐
└─────────────┘     │
                    │
┌─────────────┐     │    ┌──────────────────┐
│ Polygon API │ ────┼───▶│  Normalization   │
└─────────────┘     │    │     Engine       │
                    │    └────────┬─────────┘
┌─────────────┐     │             │
│ Finnhub API │ ────┘             │
└─────────────┘                   │
                                  ▼
                         ┌────────────────┐
                         │ Market Data    │
                         │     Store      │
                         └────────┬───────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
          ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
          │  Strategy   │ │  Indicator  │ │   Other     │
          │  Engine #1  │ │  Calculations│ │ Strategies  │
          └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                 │                │                │
                 └────────────────┼────────────────┘
                                  │ (Signals)
                                  ▼
                         ┌────────────────┐
                         │  Risk Manager  │
                         │  (Validation)  │
                         └────────┬───────┘
                                  │ (Approved Orders)
                                  ▼
                         ┌────────────────┐
                         │ Order Manager  │
                         └────────┬───────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │  Alpaca API    │
                         │  (Execution)   │
                         └────────────────┘
```

---

## Concurrency Model

### Tokio Task Structure

```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Shared state
    let market_data = Arc::new(RwLock::new(MarketDataStore::new()));
    let order_manager = Arc::new(RwLock::new(OrderManager::new()));

    // Task 1: WebSocket data ingestion
    let market_data_clone = market_data.clone();
    tokio::spawn(async move {
        let ws = AlpacaWebSocket::new(...);
        ws.connect(market_data_clone).await.unwrap();
    });

    // Task 2: Strategy execution
    let market_data_clone = market_data.clone();
    let order_manager_clone = order_manager.clone();
    tokio::spawn(async move {
        let strategy = MyStrategy::new();
        strategy.run(market_data_clone, order_manager_clone).await.unwrap();
    });

    // Task 3: Risk monitoring
    let order_manager_clone = order_manager.clone();
    tokio::spawn(async move {
        let risk_manager = RiskManager::new();
        risk_manager.monitor(order_manager_clone).await.unwrap();
    });

    // Task 4: Order execution
    let order_manager_clone = order_manager.clone();
    tokio::spawn(async move {
        let alpaca = AlpacaClient::new(...);
        alpaca.execute_orders(order_manager_clone).await.unwrap();
    });

    // Main loop: Health checks and coordination
    loop {
        tokio::time::sleep(Duration::from_secs(60)).await;
        // Check system health
    }
}
```

---

## Error Handling Strategy

### Error Types
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum TradingError {
    #[error("WebSocket connection failed: {0}")]
    WebSocketError(String),

    #[error("API rate limit exceeded")]
    RateLimitExceeded,

    #[error("Invalid market data: {0}")]
    InvalidData(String),

    #[error("Order rejected: {0}")]
    OrderRejected(String),

    #[error("Risk check failed: {0}")]
    RiskViolation(String),

    #[error("Network error: {0}")]
    NetworkError(#[from] reqwest::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
}
```

### Recovery Strategies
- **WebSocket disconnection:** Exponential backoff reconnection
- **Rate limit (429):** Exponential backoff retry
- **Invalid data:** Log and skip, continue processing
- **Order rejection:** Alert, log, continue
- **Risk violation:** Block order, alert, log

---

## Logging & Monitoring

### Structured Logging with Tracing
```rust
use tracing::{info, warn, error, debug, instrument};

#[instrument]
async fn process_trade(trade: &Trade) {
    debug!("Processing trade: {:?}", trade);

    if trade.price <= 0.0 {
        warn!("Invalid trade price: {}", trade.price);
        return;
    }

    info!(
        symbol = %trade.symbol,
        price = trade.price,
        size = trade.size,
        "Trade processed successfully"
    );
}
```

### Key Metrics to Track
- WebSocket latency (p50, p95, p99)
- Order execution time
- Market data processing rate (msgs/sec)
- Memory usage
- Open positions count
- Daily P&L
- API call counts (rate limit monitoring)

---

## Configuration Management

### Configuration File (TOML)
```toml
[api.alpaca]
api_key = "PKXXXXXXX"
secret_key = "xxxxxxxxxxxxx"
base_url = "https://paper-api.alpaca.markets"
websocket_url = "wss://stream.data.alpaca.markets/v2/iex"

[api.polygon]
api_key = "xxxxxxxxxxxxx"
base_url = "https://api.polygon.io"

[risk]
max_position_size = 10000.0
max_portfolio_value = 100000.0
daily_loss_limit = 5000.0

[strategy]
symbols = ["AAPL", "TSLA", "MSFT", "GOOGL"]
timeframe = "1Min"

[system]
log_level = "info"
market_data_retention = 1000  # Keep last 1000 trades per symbol
```

### Loading Configuration
```rust
use serde::Deserialize;
use config::Config;

#[derive(Debug, Deserialize)]
struct AppConfig {
    api: ApiConfig,
    risk: RiskConfig,
    strategy: StrategyConfig,
    system: SystemConfig,
}

fn load_config() -> Result<AppConfig, config::ConfigError> {
    let config = Config::builder()
        .add_source(config::File::with_name("config/default"))
        .add_source(config::Environment::with_prefix("TRADING"))
        .build()?;

    config.try_deserialize()
}
```

---

## Testing Strategy

### Unit Tests
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_risk_manager_validation() {
        let risk_manager = RiskManager::new(10000.0, 100000.0, 5000.0);
        let order = Order::new("AAPL", 100, 150.0);
        let positions = Positions::new();

        assert!(risk_manager.validate_order(&order, &positions).is_ok());
    }

    #[tokio::test]
    async fn test_order_submission() {
        let mut order_manager = OrderManager::new();
        let order = Order::new("AAPL", 100, 150.0);

        let order_id = order_manager.submit_order(order).await.unwrap();
        assert!(order_manager.pending_orders.contains_key(&order_id));
    }
}
```

### Integration Tests (with Mocks)
```rust
use mockito::{mock, server_url};

#[tokio::test]
async fn test_alpaca_integration() {
    let _m = mock("POST", "/v2/orders")
        .with_status(200)
        .with_body(r#"{"id":"order-123","status":"accepted"}"#)
        .create();

    let client = AlpacaClient::new_with_base_url(server_url());
    let order = Order::new("AAPL", 100, 150.0);

    let response = client.submit_order(&order).await.unwrap();
    assert_eq!(response.status, "accepted");
}
```

### Performance Benchmarks
```rust
#[bench]
fn bench_trade_processing(b: &mut Bencher) {
    let trade = Trade::new("AAPL", 150.0, 100);
    b.iter(|| {
        process_trade(&trade);
    });
}
```

---

## Deployment Architecture

### Development
```
┌─────────────────────┐
│  Local Machine      │
│  - Rust binary      │
│  - Paper trading    │
│  - Alpaca WS        │
│  - Logs to stdout   │
└─────────────────────┘
```

### Production
```
┌─────────────────────────────────────────────┐
│  Cloud VM (AWS EC2 / DigitalOcean)          │
│  ┌─────────────────────────────────────┐    │
│  │  Docker Container                   │    │
│  │  - Rust trading binary              │    │
│  │  - Config via env vars              │    │
│  │  - Logs to journald                 │    │
│  └─────────────────────────────────────┘    │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │  Monitoring                         │    │
│  │  - Prometheus metrics               │    │
│  │  - Grafana dashboards               │    │
│  │  - AlertManager                     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## Security Considerations

### API Key Management
- Store in environment variables (never in source code)
- Use `.env` file for local development (add to `.gitignore`)
- Use secrets management service in production (AWS Secrets Manager, etc.)

### Network Security
- Use TLS/SSL for all connections
- Validate SSL certificates
- Use VPN or private network in production

### Rate Limiting & Throttling
- Implement client-side rate limiting
- Use exponential backoff for retries
- Monitor API usage to avoid unexpected charges

### Error Handling
- Never expose sensitive information in logs
- Sanitize error messages before displaying
- Use structured logging with log levels

---

## Next Steps for Implementation

### Phase 1: Foundation (Week 1-2)
1. Set up Rust project with dependencies
2. Implement Alpaca WebSocket client
3. Implement data normalization layer
4. Create market data store
5. Add basic logging and error handling

### Phase 2: Order Management (Week 3-4)
1. Implement order manager
2. Integrate Alpaca Trading API
3. Add position tracking
4. Implement risk manager
5. Create order execution loop

### Phase 3: Strategy Engine (Week 5-6)
1. Design strategy interface
2. Implement example strategies (SMA crossover, etc.)
3. Add signal generation
4. Implement backtesting framework
5. Historical data retrieval (Polygon)

### Phase 4: Python Integration (Week 7-8)
1. Set up PyO3 bindings
2. Expose core functions to Python
3. Create Python examples
4. Add NumPy integration
5. Build documentation

### Phase 5: Production (Week 9-10)
1. Performance optimization
2. Comprehensive testing
3. Production deployment setup
4. Monitoring and alerting
5. Documentation and runbooks

---

**For implementation details, see:**
- [api-findings.md](./api-findings.md) - Complete API research
- [quick-reference.md](./quick-reference.md) - Quick lookup guide

---

**Status:** ✅ Architecture design complete, ready for ARCHITECT and CODER agents
