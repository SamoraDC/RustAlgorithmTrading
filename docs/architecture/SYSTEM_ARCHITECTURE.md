# System Architecture Documentation
## Rust Algorithmic Trading System

**Version**: 1.0.0
**Last Updated**: October 21, 2025
**Architecture Pattern**: Microservices with Event-Driven Communication

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Component Specifications](#component-specifications)
4. [Data Flow](#data-flow)
5. [Integration Points](#integration-points)
6. [Failure Scenarios](#failure-scenarios)
7. [Scalability & Performance](#scalability--performance)

---

## 1. System Overview

### 1.1 High-Level Architecture

The system follows a **Python-Rust hybrid microservices architecture** with clear separation of concerns:

- **Rust Services**: Low-latency components (market data, execution, risk management)
- **Python Services**: ML/AI components (signal generation, strategy)
- **Inter-Service Communication**: ZeroMQ pub/sub pattern
- **State Management**: PostgreSQL for persistence, in-memory caches for hot paths
- **Monitoring**: Prometheus + Grafana stack

### 1.2 Design Principles

1. **Low Latency**: Target <100μs end-to-end latency for order execution
2. **High Availability**: 99.95% uptime during market hours
3. **Fault Tolerance**: Graceful degradation, circuit breakers, retry logic
4. **Observability**: Comprehensive metrics, logging, tracing
5. **Security**: TLS encryption, credential management, audit trails

### 1.3 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Services** | Rust 1.70+, Python 3.9+ | Core trading logic |
| **Messaging** | ZeroMQ 0.10 | Inter-service communication |
| **Database** | PostgreSQL 15 | State persistence |
| **Caching** | In-memory (Rust HashMap) | Hot path optimization |
| **Monitoring** | Prometheus, Grafana | Metrics & visualization |
| **Containerization** | Docker 24.0+ | Deployment |
| **Orchestration** | Kubernetes 1.28+ (optional) | Scaling & HA |
| **CI/CD** | GitHub Actions | Automation |

---

## 2. Architecture Diagrams

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SYSTEMS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐           ┌──────────────────┐                        │
│  │  Alpaca Markets │           │  PostgreSQL 15   │                        │
│  │  REST API       │           │  Database        │                        │
│  │  (HTTPS)        │           │  (Port 5432)     │                        │
│  └────────┬────────┘           └────────┬─────────┘                        │
│           │                              │                                  │
│  ┌────────▼────────┐                    │                                  │
│  │  Alpaca Markets │                    │                                  │
│  │  WebSocket      │                    │                                  │
│  │  (WSS)          │                    │                                  │
│  └────────┬────────┘                    │                                  │
└───────────┼─────────────────────────────┼──────────────────────────────────┘
            │                              │
┌───────────▼──────────────────────────────▼──────────────────────────────────┐
│                          TRADING SYSTEM SERVICES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    MARKET DATA SERVICE (Rust)                      │     │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │     │
│  │  │  WebSocket   │───▶│  Order Book  │───▶│  ZMQ Pub     │        │     │
│  │  │  Client      │    │  Manager     │    │  (Port 5555) │        │     │
│  │  └──────────────┘    └──────────────┘    └──────────────┘        │     │
│  │         │                                         │                │     │
│  │         │                                         ▼                │     │
│  │         │             ┌──────────────────────────────┐            │     │
│  │         └────────────▶│  Market Data Cache           │            │     │
│  │                       │  (In-Memory HashMap)         │            │     │
│  │                       └──────────────────────────────┘            │     │
│  └──────────────────────────────────┬───────────────────────────────┘     │
│                                      │ ZMQ Publish                          │
│                                      │                                      │
│  ┌───────────────────────────────────┼──────────────────────────────────┐  │
│  │           SIGNAL BRIDGE (Python)  │                                  │  │
│  │  ┌──────────────┐    ┌────────────▼──────┐    ┌──────────────┐    │  │
│  │  │  ZMQ Sub     │───▶│  Feature Engine   │───▶│  ML Model    │    │  │
│  │  │  (5555)      │    │  (RSI, MACD, etc.)│    │  Inference   │    │  │
│  │  └──────────────┘    └───────────────────┘    └──────┬───────┘    │  │
│  │                                                        │             │  │
│  │                                                        ▼             │  │
│  │                       ┌───────────────────────────────────┐         │  │
│  │                       │  Trading Signal Generator         │         │  │
│  │                       │  (Buy/Sell/Hold Decisions)        │         │  │
│  │                       └──────────┬────────────────────────┘         │  │
│  │                                  │                                   │  │
│  │  ┌──────────────┐                │                                   │  │
│  │  │  ZMQ Pub     │◀───────────────┘                                   │  │
│  │  │  (Port 5556) │                                                     │  │
│  │  └──────┬───────┘                                                     │  │
│  └─────────┼────────────────────────────────────────────────────────────┘  │
│            │ ZMQ Publish                                                   │
│            │                                                                │
│  ┌─────────▼─────────────────────────────────────────────────────────┐    │
│  │                  RISK MANAGER SERVICE (Rust)                       │    │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │    │
│  │  │  ZMQ Sub     │───▶│  Risk Checks │───▶│  Circuit     │        │    │
│  │  │  (5556)      │    │  Engine      │    │  Breaker     │        │    │
│  │  └──────────────┘    └──────┬───────┘    └──────────────┘        │    │
│  │                              │                                     │    │
│  │                              ▼                                     │    │
│  │                       ┌─────────────┐                              │    │
│  │                       │  Position   │                              │    │
│  │                       │  Tracker    │                              │    │
│  │                       └─────────────┘                              │    │
│  └────────────────────────────┬────────────────────────────────────┘     │
│                                │ Approved Signals                          │
│                                │                                           │
│  ┌─────────────────────────────▼─────────────────────────────────────┐    │
│  │                EXECUTION ENGINE SERVICE (Rust)                     │    │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │    │
│  │  │  Order       │───▶│  Order       │───▶│  Alpaca API  │        │    │
│  │  │  Router      │    │  Manager     │    │  Client      │        │    │
│  │  └──────────────┘    └──────────────┘    └──────┬───────┘        │    │
│  │         │                                        │                 │    │
│  │         │                                        ▼                 │    │
│  │         │             ┌────────────────────────────────┐           │    │
│  │         └────────────▶│  Rate Limiter (200 req/min)   │           │    │
│  │                       └────────────────────────────────┘           │    │
│  │                                                                     │    │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │    │
│  │  │  Retry Logic │    │  Order Cache │    │  Fill Tracker│        │    │
│  │  └──────────────┘    └──────────────┘    └──────────────┘        │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE & MONITORING                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    PostgreSQL Database                              │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │     │
│  │  │  Positions   │  │  Orders      │  │  Trades      │             │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │     │
│  │  ┌──────────────┐  ┌──────────────┐                               │     │
│  │  │  Daily P&L   │  │  Risk Events │                               │     │
│  │  └──────────────┘  └──────────────┘                               │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    Monitoring Stack                                 │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │     │
│  │  │  Prometheus  │  │  Grafana     │  │  Alertmanager│             │     │
│  │  │  (Port 9090) │  │  (Port 3000) │  │  (Port 9093) │             │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Diagram

```
1. Market Data Ingestion
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │   Alpaca    │  WSS    │   Market    │   ZMQ   │   Signal    │
   │  WebSocket  │────────▶│    Data     │ Pub/Sub │   Bridge    │
   └─────────────┘         │   Service   │────────▶│  (Python)   │
                           └─────────────┘         └─────────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │  Order Book │
                           │   Cache     │
                           └─────────────┘

2. Signal Generation
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │   Market    │  ZMQ    │   Feature   │  ML     │   Trading   │
   │    Data     │────────▶│   Engine    │ Model   │   Signal    │
   └─────────────┘         │  (RSI, etc.)│────────▶│ Generator   │
                           └─────────────┘         └─────────────┘
                                                           │
                                                           ▼
                                                    ┌─────────────┐
                                                    │  Buy/Sell   │
                                                    │  Decision   │
                                                    └─────────────┘

3. Risk Management
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │   Trading   │  ZMQ    │    Risk     │  Pass/  │  Execution  │
   │   Signal    │────────▶│   Manager   │  Reject │   Engine    │
   └─────────────┘         └─────────────┘────────▶└─────────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │  Circuit    │
                           │  Breaker    │
                           └─────────────┘

4. Order Execution
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │  Approved   │  HTTP   │   Alpaca    │  Fill   │   Order     │
   │   Signal    │────────▶│  REST API   │ Event   │   Tracker   │
   └─────────────┘         └─────────────┘────────▶└─────────────┘
                                                           │
                                                           ▼
                                                    ┌─────────────┐
                                                    │  Database   │
                                                    │  Persist    │
                                                    └─────────────┘
```

---

## 3. Component Specifications

### 3.1 Market Data Service

**Language**: Rust
**Responsibilities**:
- Maintain WebSocket connection to Alpaca
- Parse and validate incoming market data
- Update order book in real-time
- Publish market data to downstream consumers

**Key Modules**:
- `websocket.rs`: WebSocket client with auto-reconnection
- `orderbook.rs`: Fast order book implementation (BTreeMap-based)
- `main.rs`: Service orchestration

**Performance**:
- WebSocket message processing: <10μs (target)
- Order book update: <10μs
- ZMQ publish latency: <5μs

**State**:
- In-memory order books for subscribed symbols
- Connection state (connected/disconnected)
- Message sequence numbers

**Dependencies**:
- `tokio-tungstenite`: WebSocket client
- `serde_json`: JSON parsing
- `zmq`: Message publishing

### 3.2 Signal Bridge (Python)

**Language**: Python 3.9+
**Responsibilities**:
- Consume market data from ZMQ
- Calculate technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Run ML model inference
- Generate trading signals (buy/sell/hold)

**Key Modules**:
- `feature_engine.py`: Technical indicator calculations
- `model_inference.py`: ML model loading and prediction
- `signal_generator.py`: Trading logic

**Performance**:
- Feature calculation: <100ms
- Model inference: <50ms
- End-to-end signal generation: <200ms

**State**:
- Feature history buffers (rolling windows)
- Loaded ML model
- Signal history

**Dependencies**:
- `pandas`: Data manipulation
- `ta-lib`: Technical indicators
- `scikit-learn` / `tensorflow`: ML models
- `pyzmq`: ZMQ communication

### 3.3 Risk Manager Service

**Language**: Rust
**Responsibilities**:
- Validate signals against risk limits
- Track positions and P&L
- Enforce circuit breaker logic
- Monitor daily loss limits

**Key Modules**:
- `limits.rs`: Risk limit checker
- `circuit_breaker.rs`: Trading halt logic
- `position_tracker.rs`: Position management

**Performance**:
- Risk check: <5μs (target)
- Position update: <10μs

**State**:
- Open positions (symbol → Position)
- Daily P&L
- Circuit breaker status
- Risk event log

**Risk Limits** (configured in `config/risk_limits.toml`):
- Max position size: $10,000 per symbol
- Max total exposure: $50,000
- Max open positions: 5
- Daily loss limit: $5,000
- Circuit breaker cooldown: 60 minutes

### 3.4 Execution Engine Service

**Language**: Rust
**Responsibilities**:
- Route approved signals to Alpaca
- Manage order lifecycle
- Handle retries and error recovery
- Track order fills

**Key Modules**:
- `router.rs`: Order submission to Alpaca
- `retry.rs`: Exponential backoff retry logic
- `main.rs`: Service orchestration

**Performance**:
- Order submission: <100μs (target, excluding network)
- Rate limiting: 200 requests/minute

**State**:
- In-flight orders (order_id → Order)
- Rate limiter state
- Retry queue

**API Integration**:
- Alpaca REST API v2
- HTTPS with TLS 1.2+
- Header-based authentication

---

## 4. Data Flow

### 4.1 End-to-End Order Flow

**Typical Latency Budget**:

| Step | Component | Latency | Cumulative |
|------|-----------|---------|------------|
| 1 | Alpaca WebSocket → Market Data | 10μs | 10μs |
| 2 | Market Data → Signal Bridge (ZMQ) | 5μs | 15μs |
| 3 | Signal Bridge Processing | 200ms | 200.015ms |
| 4 | Signal Bridge → Risk Manager (ZMQ) | 5μs | 200.020ms |
| 5 | Risk Manager Checks | 5μs | 200.025ms |
| 6 | Risk Manager → Execution Engine | 5μs | 200.030ms |
| 7 | Execution Engine → Alpaca API | 50ms | 250.030ms |

**Total**: ~250ms (includes network latency to Alpaca)

**Optimization Goal**: Reduce steps 1-6 to <100μs total

### 4.2 Message Flow Patterns

**Pub/Sub Pattern** (ZeroMQ):
```rust
// Publisher (Market Data)
let socket = zmq::Context::new().socket(zmq::PUB)?;
socket.bind("tcp://127.0.0.1:5555")?;
socket.send(message_bytes, 0)?;

// Subscriber (Signal Bridge)
socket = zmq.Context().socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:5555")
socket.subscribe(b"")  # Subscribe to all messages
message = socket.recv()
```

**Benefits**:
- Decoupled services
- Multiple consumers supported
- Fire-and-forget (low latency)

**Drawbacks**:
- No delivery guarantee
- No backpressure
- Message loss on slow consumer

**Mitigation**:
- High water mark (HWM) configuration
- Message buffering
- Monitoring for message lag

---

## 5. Integration Points

### 5.1 External Systems

**Alpaca Markets API**:
- **REST API**: Order management, account queries
- **WebSocket**: Real-time market data
- **Authentication**: Header-based (APCA-API-KEY-ID, APCA-API-SECRET-KEY)
- **TLS**: Required (TLS 1.2+)
- **Rate Limits**: 200 requests/minute

**PostgreSQL Database**:
- **Connection**: TCP 5432
- **Authentication**: Username/password
- **SSL**: Recommended for production
- **Connection Pooling**: 20 connections

### 5.2 Internal Communication

**ZeroMQ Topology**:
```
Market Data (PUB:5555)
    ├──▶ Signal Bridge (SUB)
    └──▶ Risk Manager (SUB)

Signal Bridge (PUB:5556)
    └──▶ Risk Manager (SUB)

Risk Manager
    └──▶ Execution Engine (internal)
```

**Port Allocation**:
- 5555: Market data publishing
- 5556: Trading signals publishing
- 5432: PostgreSQL
- 9090: Prometheus
- 3000: Grafana
- 8080: API Gateway (optional)

### 5.3 Data Persistence

**Database Schema** (summary):
```sql
-- Position tracking
positions (id, symbol, quantity, entry_price, current_price, unrealized_pnl, side, opened_at, updated_at)

-- Order history
orders (id, order_id, symbol, side, order_type, quantity, price, status, submitted_at, filled_at)

-- Trade executions
trades (id, trade_id, order_id, symbol, side, quantity, price, commission, executed_at)

-- Risk events
risk_events (id, event_type, severity, message, metadata, occurred_at)

-- Daily P&L
daily_pnl (id, trading_date, realized_pnl, unrealized_pnl, total_pnl, trade_count, winning_trades, losing_trades)
```

**Persistence Strategy**:
- **Write-through**: Update database on every position change
- **Async writes**: Non-blocking database operations
- **Caching**: In-memory cache for hot reads
- **Retention**: 10 years (partitioned by month)

---

## 6. Failure Scenarios

### 6.1 WebSocket Disconnection

**Scenario**: Alpaca WebSocket connection lost

**Impact**: No market data updates

**Detection**:
- WebSocket ping/pong timeout
- No messages received for >30 seconds
- Prometheus alert: `alpaca_websocket_connected == 0`

**Automatic Recovery**:
1. Log disconnection event
2. Wait 5 seconds (configurable)
3. Attempt reconnection
4. Re-authenticate
5. Re-subscribe to symbols
6. Resume normal operation

**Manual Intervention**:
- If reconnection fails >5 times: Page on-call
- Check Alpaca status page
- Verify network connectivity
- Restart market data service

### 6.2 Circuit Breaker Trip

**Scenario**: Daily loss exceeds $5,000 threshold

**Impact**: All trading halted

**Detection**:
- Risk manager monitors daily P&L
- Prometheus alert: `circuit_breaker_status == "OPEN"`

**Automatic Behavior**:
1. Reject all new signals
2. Log circuit breaker event to database
3. Send critical alert to on-call
4. Wait for manual reset (or cooldown period)

**Manual Recovery**:
1. Review risk events: `SELECT * FROM risk_events WHERE occurred_at > NOW() - INTERVAL '1 hour'`
2. Analyze positions: `SELECT * FROM positions ORDER BY unrealized_pnl`
3. Determine root cause (bug vs. market conditions)
4. If safe, reset circuit breaker via API
5. Resume trading with reduced position sizes

### 6.3 Database Connection Failure

**Scenario**: PostgreSQL becomes unavailable

**Impact**: Cannot persist new positions/orders

**Detection**:
- Database connection pool exhausted
- SQL query timeout errors
- Prometheus alert: `postgresql_up == 0`

**Automatic Recovery**:
1. Retry connection with exponential backoff
2. Queue writes in memory (bounded buffer)
3. Continue trading with in-memory state (degraded mode)
4. Persist buffered writes on reconnection

**Manual Intervention**:
- Restart PostgreSQL
- Check database logs
- Verify disk space
- Restore from backup if corrupted

### 6.4 Order Submission Failure

**Scenario**: Alpaca API returns HTTP 500

**Impact**: Order not executed

**Detection**:
- HTTP response status != 200
- Prometheus counter: `alpaca_api_errors_total`

**Automatic Recovery**:
1. Log error with full context
2. Retry with exponential backoff (3 attempts)
3. If all retries fail, alert on-call
4. Continue processing other signals

**Fallback**:
- Circuit breaker may trip if too many failures
- Manual order submission via Alpaca dashboard

---

## 7. Scalability & Performance

### 7.1 Horizontal Scaling

**Stateless Services** (can scale horizontally):
- Signal Bridge (Python)
  - Multiple instances for different symbol groups
  - Load balance via ZMQ
  - No shared state

**Stateful Services** (vertical scaling only):
- Market Data Service
  - Single instance per data feed
  - Vertical scaling (more CPU/memory)

- Risk Manager
  - Single instance (global state)
  - Vertical scaling

- Execution Engine
  - Single instance (order sequencing)
  - Vertical scaling

### 7.2 Performance Optimization

**Phase 1 Optimizations** (see `docs/PERFORMANCE_ANALYSIS.md`):
- Replace order book BinaryHeap with BTreeMap
- Switch ZMQ serialization from JSON to Bincode
- Apply CPU-specific compilation flags
- Implement object pooling for allocations

**Expected Gains**:
- Order book updates: 10-50μs → 2-5μs (5-10x faster)
- ZMQ serialization: 20-100μs → 5-15μs (4-6x faster)
- Overall: 235-670μs → 70-150μs (3-5x faster)

### 7.3 Capacity Planning

**Current Capacity**:
- Symbols tracked: 5 (configurable to 1000)
- Orders per second: 3-5
- WebSocket messages/sec: ~100
- Database writes/sec: ~10

**Scaling Limits**:
- Alpaca rate limit: 200 requests/minute
- PostgreSQL: ~10,000 writes/sec (with tuning)
- ZMQ throughput: >1M messages/sec
- Network bandwidth: Not a bottleneck

**Bottleneck**: Alpaca API rate limits

---

## System Architecture Diagrams (ASCII)

### Component Interaction Sequence

```
User          Market Data     Signal Bridge    Risk Manager    Execution      Alpaca API
  │                │                │                │             │              │
  │                │                │                │             │              │
  ├─Start System──▶│                │                │             │              │
  │                ├─Connect WSS───────────────────────────────────────────────▶ │
  │                │◀────Auth OK────────────────────────────────────────────────┤
  │                │                │                │             │              │
  │                │◀─Market Data───────────────────────────────────────────────┤
  │                ├─Update Book───▶│                │             │              │
  │                ├─Publish (ZMQ)─▶│                │             │              │
  │                │                ├─Calculate RSI─▶│             │              │
  │                │                ├─ML Inference──▶│             │              │
  │                │                ├─Generate Signal─────────────▶│              │
  │                │                │                ├─Risk Check─▶│              │
  │                │                │                ├─PASS────────▶│             │
  │                │                │                │             ├─Submit Order─▶│
  │                │                │                │             │◀──Ack─────────┤
  │                │                │                │             ├─Track Fill───▶│
  │                │                │                │             │◀──Fill Event──┤
  │                │                │                │             ├─Update Pos───▶│
  │                │                │                │             ├─Persist DB───▶│
  │◀───Order Fill Notification──────────────────────────────────────┘             │
```

---

## Additional Resources

- **Performance Analysis**: `docs/PERFORMANCE_ANALYSIS.md`
- **Database Schema**: `docs/architecture/database-persistence.md`
- **Security Audit**: `docs/SECURITY_AUDIT_REPORT.md`
- **Deployment Guide**: `docs/deployment/PRODUCTION_DEPLOYMENT.md`
- **Operations Runbook**: `docs/operations/OPERATIONS_RUNBOOK.md`

---

**Document Version**: 1.0.0
**Last Updated**: October 21, 2025
**Maintained By**: Documentation Specialist Agent
