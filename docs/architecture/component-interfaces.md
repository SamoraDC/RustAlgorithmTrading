# Component Interfaces & Trait Boundaries
## Rust Algorithmic Trading System

**Document Version:** 1.0
**Created:** 2025-10-14
**Author:** System Architect Agent (Hive Mind Swarm)

---

## Table of Contents

1. [Interface Design Principles](#1-interface-design-principles)
2. [Market Data Feed Interfaces](#2-market-data-feed-interfaces)
3. [Signal Generation Interfaces](#3-signal-generation-interfaces)
4. [Risk Management Interfaces](#4-risk-management-interfaces)
5. [Execution Engine Interfaces](#5-execution-engine-interfaces)
6. [Cross-Cutting Interfaces](#6-cross-cutting-interfaces)

---

## 1. Interface Design Principles

### 1.1 Design Goals

| Principle | Implementation |
|-----------|----------------|
| **Testability** | All interfaces have mock implementations |
| **Composability** | Traits can be combined via trait objects |
| **Type Safety** | Use newtype pattern for domain types |
| **Error Handling** | Explicit Result types, no panics |
| **Async-First** | All I/O operations are async |
| **Zero-Cost Abstractions** | Traits compile to static dispatch where possible |

### 1.2 Common Patterns

#### Newtype Pattern for Type Safety

```rust
/// Prevents mixing up different ID types at compile time
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct OrderId(Uuid);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct SymbolId(u32);

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Symbol(String);

impl Symbol {
    pub fn new(s: impl Into<String>) -> Self {
        Symbol(s.into().to_uppercase())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}
```

#### Builder Pattern for Complex Configurations

```rust
#[derive(Debug, Clone)]
pub struct MarketDataConfig {
    pub websocket_url: String,
    pub symbols: Vec<Symbol>,
    pub reconnect_delay: Duration,
    pub max_reconnect_attempts: u32,
}

impl MarketDataConfig {
    pub fn builder() -> MarketDataConfigBuilder {
        MarketDataConfigBuilder::default()
    }
}

#[derive(Default)]
pub struct MarketDataConfigBuilder {
    websocket_url: Option<String>,
    symbols: Vec<Symbol>,
    reconnect_delay: Option<Duration>,
    max_reconnect_attempts: Option<u32>,
}

impl MarketDataConfigBuilder {
    pub fn websocket_url(mut self, url: impl Into<String>) -> Self {
        self.websocket_url = Some(url.into());
        self
    }

    pub fn add_symbol(mut self, symbol: Symbol) -> Self {
        self.symbols.push(symbol);
        self
    }

    pub fn reconnect_delay(mut self, delay: Duration) -> Self {
        self.reconnect_delay = Some(delay);
        self
    }

    pub fn build(self) -> Result<MarketDataConfig, ConfigError> {
        Ok(MarketDataConfig {
            websocket_url: self.websocket_url.ok_or(ConfigError::MissingField("websocket_url"))?,
            symbols: if self.symbols.is_empty() {
                return Err(ConfigError::EmptySymbols);
            } else {
                self.symbols
            },
            reconnect_delay: self.reconnect_delay.unwrap_or(Duration::from_secs(1)),
            max_reconnect_attempts: self.max_reconnect_attempts.unwrap_or(5),
        })
    }
}
```

---

## 2. Market Data Feed Interfaces

### 2.1 Core Market Data Trait

```rust
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use rust_decimal::Decimal;

/// Abstraction over live/replay market data sources
#[async_trait]
pub trait MarketDataFeed: Send + Sync {
    /// Connect to data source
    async fn connect(&mut self) -> Result<(), MarketDataError>;

    /// Subscribe to symbols
    async fn subscribe(&mut self, symbols: Vec<Symbol>) -> Result<(), MarketDataError>;

    /// Unsubscribe from symbols
    async fn unsubscribe(&mut self, symbols: Vec<Symbol>) -> Result<(), MarketDataError>;

    /// Get next market data event (blocking)
    async fn next_event(&mut self) -> Result<MarketDataEvent, MarketDataError>;

    /// Get current connection status
    fn status(&self) -> FeedStatus;

    /// Gracefully disconnect
    async fn disconnect(&mut self) -> Result<(), MarketDataError>;
}

/// Market data event types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum MarketDataEvent {
    Trade(Trade),
    Quote(Quote),
    Bar(Bar),
    OrderBookSnapshot(OrderBookSnapshot),
    OrderBookDelta(OrderBookDelta),
    Status(StatusUpdate),
}

/// Individual trade
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub symbol: Symbol,
    pub trade_id: u64,
    pub price: Decimal,
    pub size: u32,
    pub exchange: Exchange,
    pub timestamp: DateTime<Utc>,
    pub conditions: Vec<TradeCondition>,
}

/// Top-of-book quote
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Quote {
    pub symbol: Symbol,
    pub bid_price: Decimal,
    pub bid_size: u32,
    pub bid_exchange: Exchange,
    pub ask_price: Decimal,
    pub ask_size: u32,
    pub ask_exchange: Exchange,
    pub timestamp: DateTime<Utc>,
    pub conditions: Vec<QuoteCondition>,
}

/// OHLCV bar
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bar {
    pub symbol: Symbol,
    pub open: Decimal,
    pub high: Decimal,
    pub low: Decimal,
    pub close: Decimal,
    pub volume: u64,
    pub timestamp: DateTime<Utc>,
    pub trade_count: u32,
    pub vwap: Decimal,
}

/// Order book snapshot (full depth)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderBookSnapshot {
    pub symbol: Symbol,
    pub bids: Vec<PriceLevel>,
    pub asks: Vec<PriceLevel>,
    pub timestamp: DateTime<Utc>,
    pub sequence: u64,
}

/// Order book delta (incremental update)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderBookDelta {
    pub symbol: Symbol,
    pub bids: Vec<PriceLevelDelta>,
    pub asks: Vec<PriceLevelDelta>,
    pub timestamp: DateTime<Utc>,
    pub sequence: u64,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct PriceLevel {
    pub price: Decimal,
    pub size: u32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct PriceLevelDelta {
    pub price: Decimal,
    pub size: u32,          // 0 = remove level
    pub operation: DeltaOp, // Add, Update, Delete
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeltaOp {
    Add,
    Update,
    Delete,
}

/// Feed connection status
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FeedStatus {
    Disconnected,
    Connecting,
    Connected,
    Subscribing,
    Subscribed,
    Error,
}

/// Exchange identifier
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Exchange {
    IEX,
    NASDAQ,
    NYSE,
    ARCA,
    BATS,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeCondition(pub String);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteCondition(pub String);

/// Status update events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StatusUpdate {
    Connected,
    Disconnected { reason: String },
    Subscribed { symbols: Vec<Symbol> },
    Unsubscribed { symbols: Vec<Symbol> },
    Error { message: String },
}
```

### 2.2 Order Book Interface

```rust
/// Order book management trait
pub trait OrderBookManager: Send + Sync {
    /// Initialize order book from snapshot
    fn initialize(&mut self, snapshot: OrderBookSnapshot) -> Result<(), OrderBookError>;

    /// Apply incremental delta update
    fn apply_delta(&mut self, delta: OrderBookDelta) -> Result<(), OrderBookError>;

    /// Get best bid/ask
    fn top_of_book(&self) -> Option<(PriceLevel, PriceLevel)>;

    /// Get mid price
    fn mid_price(&self) -> Option<Decimal>;

    /// Get spread in basis points
    fn spread_bps(&self) -> Option<Decimal>;

    /// Get order book depth (total volume at N levels)
    fn depth(&self, num_levels: usize) -> (Decimal, Decimal); // (bid_volume, ask_volume)

    /// Get order book imbalance (-1 to 1)
    fn imbalance(&self) -> Decimal;

    /// Check if order book is valid (bid < ask, sorted)
    fn validate(&self) -> Result<(), OrderBookError>;

    /// Get current sequence number
    fn sequence(&self) -> u64;
}

#[derive(Error, Debug)]
pub enum OrderBookError {
    #[error("Sequence gap detected: expected {expected}, got {actual}")]
    SequenceGap { expected: u64, actual: u64 },

    #[error("Invalid order book: {0}")]
    Invalid(String),

    #[error("Crossed market: bid {bid} >= ask {ask}")]
    CrossedMarket { bid: Decimal, ask: Decimal },
}
```

### 2.3 Market Data Store Interface

```rust
/// Thread-safe market data cache
pub trait MarketDataStore: Send + Sync {
    /// Update order book
    fn update_order_book(&self, symbol: &Symbol, update: OrderBookDelta) -> Result<(), OrderBookError>;

    /// Get current order book
    fn get_order_book(&self, symbol: &Symbol) -> Option<Arc<OrderBook>>;

    /// Add trade to history
    fn add_trade(&self, trade: Trade);

    /// Get last N trades
    fn get_recent_trades(&self, symbol: &Symbol, count: usize) -> Vec<Trade>;

    /// Update latest quote
    fn update_quote(&self, quote: Quote);

    /// Get latest quote
    fn get_latest_quote(&self, symbol: &Symbol) -> Option<Quote>;

    /// Add bar to time series
    fn add_bar(&self, bar: Bar);

    /// Get last N bars
    fn get_bars(&self, symbol: &Symbol, timeframe: Timeframe, count: usize) -> Vec<Bar>;

    /// Get last price (from most recent trade or quote mid)
    fn get_last_price(&self, symbol: &Symbol) -> Option<Decimal>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Timeframe {
    Tick,
    Second1,
    Second5,
    Minute1,
    Minute5,
    Minute15,
    Hour1,
    Day1,
}
```

---

## 3. Signal Generation Interfaces

### 3.1 Strategy Trait

```rust
/// Trading strategy interface
#[async_trait]
pub trait Strategy: Send + Sync {
    /// Process new market data event
    async fn on_event(&mut self, event: &MarketDataEvent) -> Result<Vec<Signal>, StrategyError>;

    /// Get strategy metadata
    fn metadata(&self) -> StrategyMetadata;

    /// Get current strategy state
    fn state(&self) -> StrategyState;

    /// Reset strategy state
    fn reset(&mut self);
}

/// Strategy metadata
#[derive(Debug, Clone)]
pub struct StrategyMetadata {
    pub name: String,
    pub version: String,
    pub description: String,
    pub symbols: Vec<Symbol>,
    pub timeframe: Timeframe,
}

/// Strategy execution state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StrategyState {
    Initializing,
    Running,
    Paused,
    Stopped,
    Error,
}

/// Trading signal (unvalidated)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signal {
    pub symbol: Symbol,
    pub side: Side,
    pub quantity: u32,
    pub order_type: OrderType,
    pub limit_price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub time_in_force: TimeInForce,
    pub timestamp: DateTime<Utc>,
    pub confidence: f64,  // 0.0 to 1.0
    pub metadata: SignalMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalMetadata {
    pub strategy_name: String,
    pub strategy_version: String,
    pub reason: String,  // Human-readable explanation
    pub features: HashMap<String, f64>,  // Feature values used
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Side {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TimeInForce {
    Day,
    GTC,  // Good-till-canceled
    IOC,  // Immediate-or-cancel
    FOK,  // Fill-or-kill
}

#[derive(Error, Debug)]
pub enum StrategyError {
    #[error("Insufficient data for strategy")]
    InsufficientData,

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    #[error("Calculation error: {0}")]
    CalculationError(String),
}
```

### 3.2 Feature Calculator Interface

```rust
/// Technical indicator calculator
pub trait FeatureCalculator: Send + Sync {
    /// Calculate features from bar history
    fn calculate(&self, bars: &[Bar]) -> Result<FeatureVector, FeatureError>;

    /// Get feature names (for ML model compatibility)
    fn feature_names(&self) -> Vec<String>;

    /// Get minimum required bars
    fn min_bars_required(&self) -> usize;
}

/// Feature vector for ML models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureVector {
    pub timestamp: DateTime<Utc>,
    pub features: HashMap<String, f64>,
}

impl FeatureVector {
    /// Convert to array for ONNX/PyTorch inference
    pub fn to_array(&self, feature_names: &[String]) -> Vec<f64> {
        feature_names.iter()
            .map(|name| self.features.get(name).copied().unwrap_or(0.0))
            .collect()
    }
}

#[derive(Error, Debug)]
pub enum FeatureError {
    #[error("Insufficient bars: required {required}, got {actual}")]
    InsufficientBars { required: usize, actual: usize },

    #[error("Missing feature: {0}")]
    MissingFeature(String),

    #[error("Calculation error: {0}")]
    CalculationError(String),
}
```

---

## 4. Risk Management Interfaces

### 4.1 Risk Manager Trait

```rust
/// Risk management interface
#[async_trait]
pub trait RiskManager: Send + Sync {
    /// Validate signal against risk limits
    async fn validate_signal(&self, signal: Signal) -> Result<ApprovedSignal, RejectedSignal>;

    /// Update position state (from fills)
    async fn update_position(&self, fill: Fill) -> Result<(), RiskError>;

    /// Get current positions
    async fn get_positions(&self) -> HashMap<Symbol, Position>;

    /// Get current portfolio state
    async fn get_portfolio_state(&self) -> PortfolioState;

    /// Check circuit breaker status
    async fn circuit_breaker_status(&self) -> CircuitBreakerStatus;

    /// Manually trip circuit breaker (emergency)
    async fn trip_circuit_breaker(&self, reason: String) -> Result<(), RiskError>;

    /// Reset circuit breaker (after recovery)
    async fn reset_circuit_breaker(&self) -> Result<(), RiskError>;
}

/// Approved signal (passed risk checks)
#[derive(Debug, Clone)]
pub struct ApprovedSignal {
    pub signal: Signal,
    pub approval_timestamp: DateTime<Utc>,
    pub checks_passed: Vec<RiskCheck>,
}

/// Rejected signal (failed risk checks)
#[derive(Debug, Clone)]
pub struct RejectedSignal {
    pub signal: Signal,
    pub rejection_timestamp: DateTime<Utc>,
    pub reason: RejectionReason,
    pub failed_check: RiskCheck,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RiskCheck {
    PositionLimit,
    NotionalExposure,
    ConcentrationLimit,
    DailyLossLimit,
    CircuitBreaker,
    OrderCountLimit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RejectionReason {
    PositionLimitExceeded { current: i64, max: i64 },
    NotionalLimitExceeded { current: Decimal, max: Decimal },
    ConcentrationLimitExceeded { pct: Decimal, max: Decimal },
    DailyLossLimitExceeded { current: Decimal, max: Decimal },
    CircuitBreakerOpen { reason: String },
    OrderCountLimitExceeded { current: usize, max: usize },
    InvalidOrder { reason: String },
}

/// Position state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: Symbol,
    pub quantity: i64,  // Positive = long, negative = short
    pub avg_entry_price: Decimal,
    pub market_value: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub last_update: DateTime<Utc>,
}

/// Portfolio-level state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioState {
    pub cash: Decimal,
    pub total_equity: Decimal,
    pub total_pnl: Decimal,
    pub daily_pnl: Decimal,
    pub open_positions: usize,
    pub pending_orders: usize,
    pub buying_power: Decimal,
}

/// Circuit breaker status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CircuitBreakerStatus {
    pub state: CircuitState,
    pub trip_count: u32,
    pub last_trip_time: Option<DateTime<Utc>>,
    pub last_trip_reason: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CircuitState {
    Closed,   // Normal operation
    Open,     // Halted, no new orders
    HalfOpen, // Testing recovery
}

#[derive(Error, Debug)]
pub enum RiskError {
    #[error("Risk check failed: {0:?}")]
    CheckFailed(RejectionReason),

    #[error("Position not found: {0}")]
    PositionNotFound(Symbol),

    #[error("Circuit breaker is open")]
    CircuitBreakerOpen,
}
```

### 4.2 Position Tracker Interface

```rust
/// Position tracking and P&L calculation
pub trait PositionTracker: Send + Sync {
    /// Apply fill to update position
    fn apply_fill(&mut self, fill: &Fill, current_price: Decimal) -> Result<(), PositionError>;

    /// Get position for symbol
    fn get_position(&self, symbol: &Symbol) -> Option<&Position>;

    /// Get all positions
    fn get_all_positions(&self) -> Vec<&Position>;

    /// Mark all positions to market
    fn mark_to_market(&mut self, prices: &HashMap<Symbol, Decimal>);

    /// Calculate total portfolio P&L
    fn total_pnl(&self) -> Decimal;

    /// Calculate total equity
    fn total_equity(&self, cash: Decimal) -> Decimal;
}

/// Fill notification from exchange
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fill {
    pub order_id: OrderId,
    pub symbol: Symbol,
    pub side: Side,
    pub quantity: u32,
    pub price: Decimal,
    pub commission: Decimal,
    pub timestamp: DateTime<Utc>,
}

#[derive(Error, Debug)]
pub enum PositionError {
    #[error("Invalid fill: {0}")]
    InvalidFill(String),

    #[error("Position calculation error: {0}")]
    CalculationError(String),
}
```

---

## 5. Execution Engine Interfaces

### 5.1 Order Router Trait

```rust
/// Order routing to exchange
#[async_trait]
pub trait OrderRouter: Send + Sync {
    /// Submit order to exchange
    async fn submit_order(&self, order: Order) -> Result<OrderAck, ExecutionError>;

    /// Cancel pending order
    async fn cancel_order(&self, order_id: OrderId) -> Result<(), ExecutionError>;

    /// Get order status
    async fn get_order_status(&self, order_id: OrderId) -> Result<OrderStatus, ExecutionError>;

    /// Get all open orders
    async fn get_open_orders(&self) -> Result<Vec<Order>, ExecutionError>;

    /// Get account information
    async fn get_account(&self) -> Result<Account, ExecutionError>;
}

/// Order structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub order_id: OrderId,
    pub client_order_id: Uuid,  // For idempotency
    pub symbol: Symbol,
    pub side: Side,
    pub order_type: OrderType,
    pub quantity: u32,
    pub filled_quantity: u32,
    pub limit_price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub time_in_force: TimeInForce,
    pub status: OrderStatus,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub filled_avg_price: Option<Decimal>,
    pub commission: Option<Decimal>,
}

/// Order acknowledgment from exchange
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderAck {
    pub order_id: OrderId,
    pub client_order_id: Uuid,
    pub status: OrderStatus,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    PendingNew,
    New,
    PartiallyFilled,
    Filled,
    PendingCancel,
    Canceled,
    Rejected,
}

/// Account information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Account {
    pub account_id: String,
    pub cash: Decimal,
    pub buying_power: Decimal,
    pub portfolio_value: Decimal,
    pub equity: Decimal,
    pub initial_margin: Decimal,
    pub maintenance_margin: Decimal,
}

#[derive(Error, Debug)]
pub enum ExecutionError {
    #[error("Order rejected: {0}")]
    OrderRejected(String),

    #[error("Rate limited")]
    RateLimited,

    #[error("Network timeout")]
    Timeout,

    #[error("Invalid order: {0}")]
    InvalidOrder(String),

    #[error("Max retries exceeded")]
    MaxRetriesExceeded,

    #[error("HTTP error: {0}")]
    HttpError(String),
}
```

### 5.2 Order Manager Interface

```rust
/// Order lifecycle management
#[async_trait]
pub trait OrderManager: Send + Sync {
    /// Submit new order
    async fn submit(&mut self, order: Order) -> Result<OrderAck, ExecutionError>;

    /// Cancel order
    async fn cancel(&mut self, order_id: OrderId) -> Result<(), ExecutionError>;

    /// Update order status (from exchange notifications)
    async fn update_status(&mut self, order_id: OrderId, status: OrderStatus) -> Result<(), OrderError>;

    /// Process fill notification
    async fn process_fill(&mut self, fill: Fill) -> Result<(), OrderError>;

    /// Get pending orders
    fn get_pending_orders(&self) -> Vec<&Order>;

    /// Get filled orders
    fn get_filled_orders(&self) -> Vec<&Order>;

    /// Reconcile state with exchange (sync)
    async fn reconcile(&mut self) -> Result<Vec<Divergence>, OrderError>;
}

/// State divergence detected during reconciliation
#[derive(Debug, Clone)]
pub enum Divergence {
    UnknownOrder(Order),  // Order on exchange, not locally
    StatusMismatch {
        order_id: OrderId,
        local_status: OrderStatus,
        remote_status: OrderStatus,
    },
    QuantityMismatch {
        order_id: OrderId,
        local_filled: u32,
        remote_filled: u32,
    },
}

#[derive(Error, Debug)]
pub enum OrderError {
    #[error("Order not found: {0:?}")]
    NotFound(OrderId),

    #[error("Invalid state transition: {from:?} -> {to:?}")]
    InvalidTransition { from: OrderStatus, to: OrderStatus },

    #[error("Divergence detected: {0:?}")]
    Divergence(Divergence),
}
```

### 5.3 Rate Limiter Interface

```rust
/// Rate limiting for API calls
#[async_trait]
pub trait RateLimiter: Send + Sync {
    /// Acquire permission to make request (may block)
    async fn acquire(&self) -> Result<(), RateLimitError>;

    /// Try to acquire without blocking
    fn try_acquire(&self) -> Result<(), RateLimitError>;

    /// Get available capacity
    fn available(&self) -> u32;

    /// Get rate limit configuration
    fn config(&self) -> RateLimitConfig;
}

#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    pub requests_per_second: u32,
    pub burst_size: u32,
}

#[derive(Error, Debug)]
pub enum RateLimitError {
    #[error("Rate limit exceeded")]
    Exceeded,

    #[error("Failed to acquire token")]
    AcquireFailed,
}
```

---

## 6. Cross-Cutting Interfaces

### 6.1 Configuration Interface

```rust
/// Configuration management
pub trait ConfigProvider: Send + Sync {
    /// Load configuration from file
    fn load(&self, path: &Path) -> Result<Config, ConfigError>;

    /// Reload configuration (hot reload)
    fn reload(&mut self) -> Result<(), ConfigError>;

    /// Get configuration value by key
    fn get<T: DeserializeOwned>(&self, key: &str) -> Result<T, ConfigError>;

    /// Validate configuration
    fn validate(&self) -> Result<(), ConfigError>;
}

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Missing required field: {0}")]
    MissingField(&'static str),

    #[error("Invalid value for {field}: {reason}")]
    InvalidValue { field: String, reason: String },

    #[error("File not found: {0}")]
    FileNotFound(PathBuf),

    #[error("Parse error: {0}")]
    ParseError(String),
}
```

### 6.2 Metrics Interface

```rust
use prometheus::{Counter, Gauge, Histogram};

/// Metrics collection
pub trait MetricsCollector: Send + Sync {
    /// Record counter increment
    fn increment_counter(&self, name: &str, labels: &[(&str, &str)]);

    /// Set gauge value
    fn set_gauge(&self, name: &str, value: f64, labels: &[(&str, &str)]);

    /// Record histogram observation
    fn observe_histogram(&self, name: &str, value: f64, labels: &[(&str, &str)]);

    /// Get Prometheus registry (for scraping)
    fn registry(&self) -> &prometheus::Registry;
}

/// Standard metrics
pub struct SystemMetrics {
    pub market_data_latency: Histogram,
    pub order_book_updates: Counter,
    pub signals_generated: Counter,
    pub orders_submitted: Counter,
    pub orders_filled: Counter,
    pub orders_rejected: Counter,
    pub risk_rejections: Counter,
    pub circuit_breaker_trips: Counter,
    pub position_count: Gauge,
    pub total_pnl: Gauge,
    pub daily_pnl: Gauge,
}
```

### 6.3 Logging Interface

```rust
use tracing::{Level, Span};

/// Structured logging
pub trait Logger: Send + Sync {
    /// Log with level and structured fields
    fn log(&self, level: Level, message: &str, fields: &[(&str, &dyn std::fmt::Display)]);

    /// Create new span for distributed tracing
    fn span(&self, name: &str, fields: &[(&str, &dyn std::fmt::Display)]) -> Span;
}
```

---

## 7. Mock Implementations

### 7.1 Mock Market Data Feed

```rust
pub struct MockMarketDataFeed {
    events: VecDeque<MarketDataEvent>,
    status: FeedStatus,
}

impl MockMarketDataFeed {
    pub fn new(events: Vec<MarketDataEvent>) -> Self {
        Self {
            events: events.into(),
            status: FeedStatus::Disconnected,
        }
    }

    pub fn add_event(&mut self, event: MarketDataEvent) {
        self.events.push_back(event);
    }
}

#[async_trait]
impl MarketDataFeed for MockMarketDataFeed {
    async fn connect(&mut self) -> Result<(), MarketDataError> {
        self.status = FeedStatus::Connected;
        Ok(())
    }

    async fn subscribe(&mut self, _symbols: Vec<Symbol>) -> Result<(), MarketDataError> {
        self.status = FeedStatus::Subscribed;
        Ok(())
    }

    async fn unsubscribe(&mut self, _symbols: Vec<Symbol>) -> Result<(), MarketDataError> {
        Ok(())
    }

    async fn next_event(&mut self) -> Result<MarketDataEvent, MarketDataError> {
        self.events.pop_front()
            .ok_or(MarketDataError::Disconnected)
    }

    fn status(&self) -> FeedStatus {
        self.status
    }

    async fn disconnect(&mut self) -> Result<(), MarketDataError> {
        self.status = FeedStatus::Disconnected;
        Ok(())
    }
}
```

### 7.2 Mock Risk Manager

```rust
pub struct MockRiskManager {
    always_approve: bool,
    rejection_reason: Option<RejectionReason>,
}

impl MockRiskManager {
    pub fn always_approve() -> Self {
        Self {
            always_approve: true,
            rejection_reason: None,
        }
    }

    pub fn always_reject(reason: RejectionReason) -> Self {
        Self {
            always_approve: false,
            rejection_reason: Some(reason),
        }
    }
}

#[async_trait]
impl RiskManager for MockRiskManager {
    async fn validate_signal(&self, signal: Signal) -> Result<ApprovedSignal, RejectedSignal> {
        if self.always_approve {
            Ok(ApprovedSignal {
                signal,
                approval_timestamp: Utc::now(),
                checks_passed: vec![],
            })
        } else {
            Err(RejectedSignal {
                signal,
                rejection_timestamp: Utc::now(),
                reason: self.rejection_reason.clone().unwrap(),
                failed_check: RiskCheck::PositionLimit,
            })
        }
    }

    // ... other methods with default implementations
}
```

---

## 8. Testing Contracts

### 8.1 Contract Testing Pattern

```rust
/// Test that implementation satisfies trait contract
pub mod contract_tests {
    use super::*;

    /// Contract test for MarketDataFeed
    pub async fn test_market_data_feed_contract<T: MarketDataFeed>(mut feed: T) {
        // Contract: connect() should succeed
        assert!(feed.connect().await.is_ok());
        assert_eq!(feed.status(), FeedStatus::Connected);

        // Contract: subscribe() should succeed for valid symbols
        let symbols = vec![Symbol::new("AAPL")];
        assert!(feed.subscribe(symbols).await.is_ok());

        // Contract: next_event() should return data after subscribe
        let event = feed.next_event().await.unwrap();
        match event {
            MarketDataEvent::Trade(_) | MarketDataEvent::Quote(_) | MarketDataEvent::Bar(_) => {
                // Valid event types
            }
            _ => panic!("Unexpected event type"),
        }

        // Contract: disconnect() should succeed
        assert!(feed.disconnect().await.is_ok());
        assert_eq!(feed.status(), FeedStatus::Disconnected);
    }

    #[tokio::test]
    async fn test_mock_feed_satisfies_contract() {
        let events = vec![
            MarketDataEvent::Trade(Trade { /* ... */ }),
        ];
        let feed = MockMarketDataFeed::new(events);
        test_market_data_feed_contract(feed).await;
    }
}
```

---

**Document Status:** ✅ Complete
**Next Steps:** Implement interfaces and create comprehensive unit tests

**Coordination Hooks:**
```bash
npx claude-flow@alpha hooks post-edit --file "docs/architecture/component-interfaces.md" --memory-key "swarm/architect/component-interfaces"
```
