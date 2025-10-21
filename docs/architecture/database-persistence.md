# Database Persistence Layer Architecture

## Table of Contents
1. [Overview](#overview)
2. [Database Schema Design](#database-schema-design)
3. [Integration Architecture](#integration-architecture)
4. [Failure Recovery](#failure-recovery)
5. [Performance Optimization](#performance-optimization)
6. [Migration Plan](#migration-plan)
7. [Operational Procedures](#operational-procedures)

---

## Overview

### Purpose
Design a robust, high-performance PostgreSQL persistence layer for the algorithmic trading system to ensure data durability, auditability, and recovery capabilities.

### Key Design Principles
- **Durability**: All critical trading state persisted with ACID guarantees
- **Performance**: Sub-10ms write latency for critical operations
- **Auditability**: Complete audit trail for regulatory compliance
- **Recoverability**: System can reconstruct state from database after crashes
- **Scalability**: Support for growing trade volume and historical data

### Technology Stack
- **Database**: PostgreSQL 15+ (ACID compliance, JSON support, partitioning)
- **Connection Pool**: deadpool-postgres (async connection pooling)
- **ORM/Query Builder**: tokio-postgres (low-level async driver)
- **Migration Tool**: refinery or sqlx migrations
- **Backup**: pg_dump + WAL archiving

---

## Database Schema Design

### 1. Positions Table

Tracks current portfolio positions with real-time updates.

```sql
CREATE TABLE positions (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    average_price DECIMAL(20, 8) NOT NULL,
    market_value DECIMAL(20, 2) NOT NULL,
    unrealized_pnl DECIMAL(20, 2) NOT NULL,
    cost_basis DECIMAL(20, 2) NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT positions_symbol_unique UNIQUE (symbol),
    CONSTRAINT positions_quantity_valid CHECK (quantity != 0)
);

-- Indexes
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_last_updated ON positions(last_updated DESC);

-- Comments
COMMENT ON TABLE positions IS 'Current portfolio positions with real-time market values';
COMMENT ON COLUMN positions.quantity IS 'Positive for long positions, negative for short positions';
COMMENT ON COLUMN positions.unrealized_pnl IS 'Current P&L based on market price';
```

### 2. Orders Table

Complete order lifecycle tracking from submission to fill/cancel.

```sql
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    client_order_id VARCHAR(50) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    time_in_force VARCHAR(10) NOT NULL DEFAULT 'day',
    limit_price DECIMAL(20, 8),
    stop_price DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL,
    filled_quantity DECIMAL(20, 8) NOT NULL DEFAULT 0,
    filled_avg_price DECIMAL(20, 8),
    submitted_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    error_message TEXT,

    -- Foreign key to positions
    position_symbol VARCHAR(20) REFERENCES positions(symbol),

    -- Constraints
    CONSTRAINT orders_side_valid CHECK (side IN ('buy', 'sell')),
    CONSTRAINT orders_type_valid CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    CONSTRAINT orders_status_valid CHECK (status IN ('pending', 'submitted', 'partial_fill', 'filled', 'cancelled', 'rejected', 'expired')),
    CONSTRAINT orders_quantity_positive CHECK (quantity > 0),
    CONSTRAINT orders_filled_quantity_valid CHECK (filled_quantity >= 0 AND filled_quantity <= quantity)
);

-- Indexes
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_submitted_at ON orders(submitted_at DESC);
CREATE INDEX idx_orders_symbol_status ON orders(symbol, status);

-- Partial index for active orders (hot path)
CREATE INDEX idx_orders_active ON orders(symbol, status)
    WHERE status IN ('pending', 'submitted', 'partial_fill');

-- Comments
COMMENT ON TABLE orders IS 'Complete order lifecycle tracking for all trading activity';
COMMENT ON COLUMN orders.client_order_id IS 'Internal order ID for deduplication';
```

### 3. Trades Table

Individual trade execution records (partitioned by date).

```sql
CREATE TABLE trades (
    trade_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL REFERENCES orders(order_id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    commission DECIMAL(20, 8) NOT NULL DEFAULT 0,
    trade_value DECIMAL(20, 2) NOT NULL,
    liquidity VARCHAR(10),

    -- Constraints
    CONSTRAINT trades_side_valid CHECK (side IN ('buy', 'sell')),
    CONSTRAINT trades_quantity_positive CHECK (quantity > 0),
    CONSTRAINT trades_price_positive CHECK (price > 0)
) PARTITION BY RANGE (timestamp);

-- Create partitions for current and next quarter
CREATE TABLE trades_2025_q1 PARTITION OF trades
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE trades_2025_q2 PARTITION OF trades
    FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE trades_2025_q3 PARTITION OF trades
    FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE trades_2025_q4 PARTITION OF trades
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

-- Indexes (created on parent table, inherited by partitions)
CREATE INDEX idx_trades_order_id ON trades(order_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_timestamp ON trades(timestamp DESC);

-- Comments
COMMENT ON TABLE trades IS 'Individual trade executions, partitioned by quarter for performance';
COMMENT ON COLUMN trades.liquidity IS 'maker or taker';
```

### 4. Audit Log Table

Complete audit trail for compliance and debugging (partitioned by month).

```sql
CREATE TABLE audit_log (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    component VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB NOT NULL,
    user_id VARCHAR(50),
    session_id VARCHAR(50),
    severity VARCHAR(20) NOT NULL DEFAULT 'info',

    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create partitions for current and next 3 months
CREATE TABLE audit_log_2025_10 PARTITION OF audit_log
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE audit_log_2025_11 PARTITION OF audit_log
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE audit_log_2025_12 PARTITION OF audit_log
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Indexes
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_component ON audit_log(component);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_severity ON audit_log(severity) WHERE severity IN ('error', 'warning');

-- GIN index for JSONB queries
CREATE INDEX idx_audit_log_details ON audit_log USING GIN(details);

-- Comments
COMMENT ON TABLE audit_log IS 'Complete audit trail for regulatory compliance, partitioned by month';
COMMENT ON COLUMN audit_log.details IS 'JSONB field for flexible event data storage';
```

### 5. Risk Snapshots Table

Periodic risk metrics for analysis and alerts.

```sql
CREATE TABLE risk_snapshots (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    portfolio_value DECIMAL(20, 2) NOT NULL,
    cash_balance DECIMAL(20, 2) NOT NULL,
    total_exposure DECIMAL(20, 2) NOT NULL,
    var_95 DECIMAL(20, 2),
    var_99 DECIMAL(20, 2),
    max_drawdown DECIMAL(10, 4),
    position_count INTEGER NOT NULL,
    largest_position_pct DECIMAL(10, 4),
    sector_concentration JSONB,
    metrics JSONB,

    -- Constraints
    CONSTRAINT risk_snapshots_timestamp_unique UNIQUE (timestamp)
);

-- Indexes
CREATE INDEX idx_risk_snapshots_timestamp ON risk_snapshots(timestamp DESC);

-- Partial index for recent snapshots (hot queries)
CREATE INDEX idx_risk_snapshots_recent ON risk_snapshots(timestamp DESC)
    WHERE timestamp > NOW() - INTERVAL '30 days';

-- Comments
COMMENT ON TABLE risk_snapshots IS 'Periodic risk metrics snapshots (every 5 minutes during trading)';
COMMENT ON COLUMN risk_snapshots.sector_concentration IS 'JSONB mapping of sector -> exposure percentage';
```

### 6. Market Data Cache Table (Optional)

Cache for frequently accessed market data to reduce API calls.

```sql
CREATE TABLE market_data_cache (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    bid DECIMAL(20, 8),
    ask DECIMAL(20, 8),
    volume BIGINT,

    PRIMARY KEY (symbol, timestamp)
);

-- Indexes
CREATE INDEX idx_market_data_symbol_timestamp ON market_data_cache(symbol, timestamp DESC);

-- Partial index for recent data (keep last 24 hours)
CREATE INDEX idx_market_data_recent ON market_data_cache(timestamp DESC)
    WHERE timestamp > NOW() - INTERVAL '24 hours';

-- Comments
COMMENT ON TABLE market_data_cache IS 'Recent market data cache to reduce API calls';
```

### 7. System State Table

Persistent system configuration and state.

```sql
CREATE TABLE system_state (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT
);

-- Common state keys
INSERT INTO system_state (key, value, description) VALUES
    ('trading_enabled', 'true', 'Master trading switch'),
    ('risk_limits', '{"max_position_size": 10000, "max_daily_loss": 5000}', 'Risk limit configuration'),
    ('last_reconciliation', 'null', 'Last position reconciliation timestamp');

-- Comments
COMMENT ON TABLE system_state IS 'Persistent system configuration and operational state';
```

---

## Integration Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Trading Application                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Strategy   │  │     Risk     │  │   Execution  │          │
│  │   Engine     │  │   Manager    │  │   Engine     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│                   ┌────────▼────────┐                            │
│                   │  Persistence    │                            │
│                   │  Coordinator    │                            │
│                   └────────┬────────┘                            │
│                            │                                      │
│         ┌──────────────────┼──────────────────┐                 │
│         │                  │                  │                  │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐         │
│  │   Position   │  │    Order     │  │     Risk     │         │
│  │    Cache     │  │    Cache     │  │    Cache     │         │
│  │  (Write-Thru)│  │              │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                 │
│                            │                                      │
│                   ┌────────▼────────┐                            │
│                   │  DB Connection  │                            │
│                   │      Pool       │                            │
│                   │ (deadpool-pg)   │                            │
│                   └────────┬────────┘                            │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │   Primary DB    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │  Read Replica   │
                    │  (Analytics)    │
                    └─────────────────┘
```

### Component Design

#### 1. Persistence Coordinator

**Responsibility**: Central coordinator for all database operations.

**Key Features**:
- Connection pool management
- Transaction coordination
- Write batching for performance
- Retry logic with exponential backoff
- Circuit breaker for database failures

**Interface**:
```rust
pub struct PersistenceCoordinator {
    pool: Pool<PostgresConnectionManager<NoTls>>,
    position_cache: Arc<RwLock<HashMap<String, Position>>>,
    metrics: Arc<PersistenceMetrics>,
}

impl PersistenceCoordinator {
    // Position operations
    async fn save_position(&self, position: &Position) -> Result<()>;
    async fn get_position(&self, symbol: &str) -> Result<Option<Position>>;
    async fn list_positions(&self) -> Result<Vec<Position>>;

    // Order operations
    async fn save_order(&self, order: &Order) -> Result<()>;
    async fn update_order_status(&self, order_id: &str, status: OrderStatus) -> Result<()>;

    // Trade operations
    async fn save_trade(&self, trade: &Trade) -> Result<()>;
    async fn get_trades_for_order(&self, order_id: &str) -> Result<Vec<Trade>>;

    // Audit operations
    async fn log_audit(&self, component: &str, action: &str, details: serde_json::Value) -> Result<()>;

    // Risk snapshots
    async fn save_risk_snapshot(&self, snapshot: &RiskSnapshot) -> Result<()>;

    // System state
    async fn get_system_state(&self, key: &str) -> Result<Option<serde_json::Value>>;
    async fn set_system_state(&self, key: &str, value: serde_json::Value) -> Result<()>;
}
```

#### 2. Write-Through Position Cache

**Strategy**: Cache positions in memory with synchronous writes to database.

**Rationale**:
- Positions are read frequently (every order decision)
- Positions change infrequently (only on fills)
- Strong consistency required (can't have stale positions)

**Implementation**:
```rust
pub struct PositionCache {
    cache: Arc<RwLock<HashMap<String, Position>>>,
    db: Arc<PersistenceCoordinator>,
}

impl PositionCache {
    pub async fn update_position(&self, position: Position) -> Result<()> {
        // Write-through: update DB first
        self.db.save_position(&position).await?;

        // Then update cache
        let mut cache = self.cache.write().await;
        cache.insert(position.symbol.clone(), position);

        Ok(())
    }

    pub async fn get_position(&self, symbol: &str) -> Result<Option<Position>> {
        // Read from cache
        let cache = self.cache.read().await;
        Ok(cache.get(symbol).cloned())
    }
}
```

#### 3. Periodic Snapshot Manager

**Purpose**: Create regular snapshots of risk metrics.

**Implementation**:
```rust
pub struct SnapshotManager {
    coordinator: Arc<PersistenceCoordinator>,
    risk_manager: Arc<RiskManager>,
    interval: Duration,
}

impl SnapshotManager {
    pub async fn run(&self) {
        let mut interval = tokio::time::interval(self.interval);

        loop {
            interval.tick().await;

            if let Err(e) = self.create_snapshot().await {
                error!("Failed to create risk snapshot: {}", e);
            }
        }
    }

    async fn create_snapshot(&self) -> Result<()> {
        let metrics = self.risk_manager.get_current_metrics().await?;
        let snapshot = RiskSnapshot {
            timestamp: Utc::now(),
            portfolio_value: metrics.portfolio_value,
            var_95: metrics.var_95,
            max_drawdown: metrics.max_drawdown,
            position_count: metrics.position_count,
            // ... other fields
        };

        self.coordinator.save_risk_snapshot(&snapshot).await?;
        Ok(())
    }
}
```

#### 4. Audit Logger

**Purpose**: Async, non-blocking audit logging.

**Implementation**:
```rust
pub struct AuditLogger {
    tx: mpsc::UnboundedSender<AuditEvent>,
}

impl AuditLogger {
    pub fn new(coordinator: Arc<PersistenceCoordinator>) -> Self {
        let (tx, mut rx) = mpsc::unbounded_channel();

        // Background task to process audit events
        tokio::spawn(async move {
            while let Some(event) = rx.recv().await {
                if let Err(e) = coordinator.log_audit(
                    &event.component,
                    &event.action,
                    event.details
                ).await {
                    error!("Failed to log audit event: {}", e);
                }
            }
        });

        Self { tx }
    }

    pub fn log(&self, component: &str, action: &str, details: serde_json::Value) {
        let event = AuditEvent {
            component: component.to_string(),
            action: action.to_string(),
            details,
        };

        // Fire and forget
        let _ = self.tx.send(event);
    }
}
```

### Connection Pool Configuration

**Configuration**:
```rust
use deadpool_postgres::{Config, Pool, Runtime};

pub fn create_pool() -> Result<Pool> {
    let mut cfg = Config::new();
    cfg.host = Some("localhost".to_string());
    cfg.port = Some(5432);
    cfg.dbname = Some("trading_system".to_string());
    cfg.user = Some("trading_user".to_string());
    cfg.password = Some(std::env::var("DB_PASSWORD")?);

    // Pool sizing
    cfg.pool = Some(deadpool_postgres::PoolConfig {
        max_size: 20,           // Max connections
        timeouts: Timeouts {
            wait: Some(Duration::from_secs(5)),
            create: Some(Duration::from_secs(10)),
            recycle: Some(Duration::from_secs(5)),
        },
    });

    cfg.create_pool(Some(Runtime::Tokio1), NoTls)
}
```

**Pool Sizing Rationale**:
- **Max 20 connections**: Balance between throughput and resource usage
- **Wait timeout 5s**: Fail fast if pool exhausted
- **Create timeout 10s**: Allow time for network issues
- **Recycle timeout 5s**: Check connection health regularly

### Transaction Isolation Levels

**Strategy by Operation Type**:

| Operation | Isolation Level | Rationale |
|-----------|----------------|-----------|
| Position Updates | SERIALIZABLE | Prevent race conditions on position calculations |
| Order Submissions | READ COMMITTED | Balance consistency and performance |
| Trade Recording | READ COMMITTED | No concurrent modification risk |
| Audit Logging | READ UNCOMMITTED | Performance, no consistency requirement |
| Risk Snapshots | REPEATABLE READ | Consistent view of portfolio state |

**Implementation Example**:
```rust
async fn update_position_with_transaction(&self, symbol: &str, delta: Decimal) -> Result<()> {
    let mut client = self.pool.get().await?;
    let transaction = client.transaction().await?;

    // Set isolation level
    transaction.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", &[]).await?;

    // Read current position
    let row = transaction.query_one(
        "SELECT quantity, average_price FROM positions WHERE symbol = $1 FOR UPDATE",
        &[&symbol]
    ).await?;

    let current_qty: Decimal = row.get(0);
    let avg_price: Decimal = row.get(1);

    // Calculate new values
    let new_qty = current_qty + delta;

    // Update position
    transaction.execute(
        "UPDATE positions SET quantity = $1, last_updated = NOW() WHERE symbol = $2",
        &[&new_qty, &symbol]
    ).await?;

    transaction.commit().await?;
    Ok(())
}
```

---

## Failure Recovery

### 1. Position Reconciliation on Startup

**Purpose**: Ensure database state matches broker state after crashes.

**Process**:
```
┌─────────────────────────────────────────────────────────────┐
│                   Startup Reconciliation                     │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │  Load DB Positions    │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │ Fetch Broker Positions│
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │   Compare Positions   │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
        ┌───────┤  Any Discrepancies?   ├────────┐
        │       └───────────────────────┘        │
        │ Yes                               No   │
        │                                        │
┌───────▼───────┐                     ┌──────────▼─────────┐
│  Log WARNING  │                     │  Reconciliation    │
│  Alert Admin  │                     │    Complete        │
└───────┬───────┘                     └────────────────────┘
        │
┌───────▼───────┐
│ Use Broker as │
│ Source of     │
│ Truth         │
└───────┬───────┘
        │
┌───────▼───────┐
│  Update DB    │
│  Positions    │
└───────────────┘
```

**Implementation**:
```rust
pub async fn reconcile_positions(&self) -> Result<()> {
    // 1. Load positions from database
    let db_positions = self.coordinator.list_positions().await?;

    // 2. Fetch current positions from broker
    let broker_positions = self.broker.get_positions().await?;

    // 3. Compare
    let mut discrepancies = Vec::new();

    for broker_pos in &broker_positions {
        let db_pos = db_positions.iter().find(|p| p.symbol == broker_pos.symbol);

        match db_pos {
            Some(db_pos) if db_pos.quantity != broker_pos.quantity => {
                discrepancies.push(format!(
                    "Symbol {}: DB quantity {} != Broker quantity {}",
                    broker_pos.symbol, db_pos.quantity, broker_pos.quantity
                ));
            }
            None if broker_pos.quantity != Decimal::ZERO => {
                discrepancies.push(format!(
                    "Symbol {}: Not in DB but broker has quantity {}",
                    broker_pos.symbol, broker_pos.quantity
                ));
            }
            _ => {}
        }
    }

    // 4. Handle discrepancies
    if !discrepancies.is_empty() {
        error!("Position reconciliation discrepancies found:");
        for discrepancy in &discrepancies {
            error!("  {}", discrepancy);
        }

        // 5. Use broker as source of truth
        for broker_pos in broker_positions {
            self.coordinator.save_position(&broker_pos).await?;
        }

        // 6. Alert admin
        self.alert_manager.send_alert(
            AlertSeverity::High,
            "Position Reconciliation",
            &format!("Found {} discrepancies, updated from broker", discrepancies.len())
        ).await?;
    }

    Ok(())
}
```

### 2. Order State Recovery

**Problem**: Orders may be in intermediate states after crashes.

**Solution**: State machine recovery on startup.

```rust
pub async fn recover_orders(&self) -> Result<()> {
    // Find orders in intermediate states
    let pending_orders = self.coordinator.get_orders_by_status(&[
        OrderStatus::Pending,
        OrderStatus::Submitted,
        OrderStatus::PartialFill,
    ]).await?;

    for order in pending_orders {
        // Check actual status from broker
        match self.broker.get_order_status(&order.order_id).await {
            Ok(broker_status) => {
                // Update to actual status
                if broker_status != order.status {
                    self.coordinator.update_order_status(&order.order_id, broker_status).await?;
                }
            }
            Err(e) => {
                // Order doesn't exist at broker - mark as error
                error!("Order {} not found at broker: {}", order.order_id, e);
                self.coordinator.update_order_status(&order.order_id, OrderStatus::Rejected).await?;
            }
        }
    }

    Ok(())
}
```

### 3. Rollback Strategies

**Strategy by Operation Type**:

| Operation | Rollback Strategy | Implementation |
|-----------|------------------|----------------|
| Position Update | Database transaction rollback | Wrap in transaction with SERIALIZABLE isolation |
| Order Submission | Compensating transaction | Cancel order at broker, mark as cancelled in DB |
| Trade Recording | Idempotent writes | Use trade_id as primary key, ignore duplicates |
| Risk Snapshot | No rollback needed | Append-only, no updates |

**Example: Order Submission Rollback**:
```rust
pub async fn submit_order_with_rollback(&self, order: Order) -> Result<Order> {
    // 1. Save order in DB as "pending"
    self.coordinator.save_order(&order).await?;

    // 2. Submit to broker
    match self.broker.submit_order(&order).await {
        Ok(broker_order_id) => {
            // Success - update order status
            self.coordinator.update_order(
                &order.order_id,
                OrderStatus::Submitted,
                Some(broker_order_id)
            ).await?;
            Ok(order)
        }
        Err(e) => {
            // Failure - mark as rejected
            self.coordinator.update_order_status(
                &order.order_id,
                OrderStatus::Rejected
            ).await?;

            self.coordinator.log_audit(
                "execution_engine",
                "order_rejected",
                json!({
                    "order_id": order.order_id,
                    "error": e.to_string()
                })
            ).await?;

            Err(e)
        }
    }
}
```

### 4. Database Connection Failure Handling

**Circuit Breaker Pattern**:
```rust
pub struct DatabaseCircuitBreaker {
    state: Arc<RwLock<CircuitState>>,
    failure_threshold: u32,
    timeout: Duration,
}

enum CircuitState {
    Closed { failure_count: u32 },
    Open { opened_at: Instant },
    HalfOpen,
}

impl DatabaseCircuitBreaker {
    pub async fn execute<F, T>(&self, operation: F) -> Result<T>
    where
        F: Future<Output = Result<T>>,
    {
        match *self.state.read().await {
            CircuitState::Open { opened_at } => {
                if opened_at.elapsed() > self.timeout {
                    // Try transitioning to half-open
                    *self.state.write().await = CircuitState::HalfOpen;
                } else {
                    return Err(Error::CircuitOpen);
                }
            }
            _ => {}
        }

        match operation.await {
            Ok(result) => {
                // Success - reset circuit
                *self.state.write().await = CircuitState::Closed { failure_count: 0 };
                Ok(result)
            }
            Err(e) => {
                // Failure - increment counter
                let mut state = self.state.write().await;
                match *state {
                    CircuitState::Closed { failure_count } => {
                        let new_count = failure_count + 1;
                        if new_count >= self.failure_threshold {
                            *state = CircuitState::Open { opened_at: Instant::now() };
                        } else {
                            *state = CircuitState::Closed { failure_count: new_count };
                        }
                    }
                    CircuitState::HalfOpen => {
                        *state = CircuitState::Open { opened_at: Instant::now() };
                    }
                    _ => {}
                }
                Err(e)
            }
        }
    }
}
```

### 5. Backup and Recovery Procedures

**Backup Strategy**:
- **Full backup**: Daily at 2 AM EST (off-market hours)
- **Incremental backup**: Every 6 hours
- **WAL archiving**: Continuous for point-in-time recovery
- **Retention**: 30 days full, 90 days WAL archives

**Backup Script** (to be run via cron):
```bash
#!/bin/bash
# /opt/trading/scripts/backup-db.sh

set -e

BACKUP_DIR="/opt/trading/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="trading_system"

# Full backup
pg_dump -Fc -Z9 $DB_NAME > "$BACKUP_DIR/full_${TIMESTAMP}.dump"

# Upload to S3 (or other cloud storage)
aws s3 cp "$BACKUP_DIR/full_${TIMESTAMP}.dump" \
    "s3://trading-system-backups/postgres/full_${TIMESTAMP}.dump"

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "full_*.dump" -mtime +30 -delete

echo "Backup completed: full_${TIMESTAMP}.dump"
```

**Recovery Procedure**:
```bash
# 1. Stop trading application
systemctl stop trading-system

# 2. Drop and recreate database
dropdb trading_system
createdb trading_system

# 3. Restore from backup
pg_restore -d trading_system /path/to/backup.dump

# 4. Verify data integrity
psql trading_system -c "SELECT COUNT(*) FROM positions;"
psql trading_system -c "SELECT COUNT(*) FROM orders;"

# 5. Run reconciliation
./trading-system --reconcile-only

# 6. Restart application
systemctl start trading-system
```

---

## Performance Optimization

### 1. Index Strategy

**Primary Indexes** (already defined in schema):
- Unique indexes on primary keys
- Indexes on foreign keys
- Indexes on frequently filtered columns (symbol, status, timestamp)

**Composite Indexes** (for common query patterns):
```sql
-- Order queries by symbol and status
CREATE INDEX idx_orders_symbol_status_timestamp ON orders(symbol, status, submitted_at DESC);

-- Trade queries by symbol and date
CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp DESC);

-- Recent audit log queries
CREATE INDEX idx_audit_recent_component ON audit_log(component, timestamp DESC)
    WHERE timestamp > NOW() - INTERVAL '7 days';
```

**Index Monitoring**:
```sql
-- Query to find unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexrelname NOT LIKE 'pg_toast%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Query to find missing indexes
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / seq_scan AS avg_seq_tup_read
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;
```

### 2. Partitioning Strategy

**Tables to Partition**:

| Table | Partition Key | Strategy | Retention |
|-------|--------------|----------|-----------|
| trades | timestamp | Range (quarterly) | 7 years |
| audit_log | timestamp | Range (monthly) | 2 years |
| market_data_cache | timestamp | Range (daily) | 30 days |

**Automated Partition Management**:
```sql
-- Function to create new partition
CREATE OR REPLACE FUNCTION create_partition_if_not_exists(
    table_name TEXT,
    partition_start DATE,
    partition_end DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
BEGIN
    partition_name := table_name || '_' || TO_CHAR(partition_start, 'YYYY_Q"q"');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            table_name,
            partition_start,
            partition_end
        );

        RAISE NOTICE 'Created partition: %', partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Scheduled job to create partitions (run weekly)
DO $$
DECLARE
    current_quarter DATE;
    next_quarter DATE;
BEGIN
    current_quarter := DATE_TRUNC('quarter', CURRENT_DATE);
    next_quarter := current_quarter + INTERVAL '3 months';

    -- Create partition for next quarter
    PERFORM create_partition_if_not_exists('trades', next_quarter, next_quarter + INTERVAL '3 months');
END $$;
```

**Partition Pruning Verification**:
```sql
-- Verify partition pruning is working
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM trades
WHERE timestamp >= '2025-10-01' AND timestamp < '2025-11-01'
    AND symbol = 'AAPL';

-- Should show only relevant partition scanned
```

### 3. Bulk Insert Optimization

**Problem**: Individual inserts are slow for high-frequency trades.

**Solution**: Batch inserts using COPY or multi-value INSERT.

```rust
pub async fn bulk_insert_trades(&self, trades: &[Trade]) -> Result<()> {
    if trades.is_empty() {
        return Ok(());
    }

    let client = self.pool.get().await?;

    // Use COPY for maximum performance
    let stmt = "COPY trades (trade_id, order_id, symbol, side, quantity, price, timestamp, commission, trade_value) FROM STDIN WITH (FORMAT csv)";

    let mut writer = client.copy_in(stmt).await?;

    for trade in trades {
        let row = format!(
            "{},{},{},{},{},{},{},{},{}\n",
            trade.trade_id,
            trade.order_id,
            trade.symbol,
            trade.side,
            trade.quantity,
            trade.price,
            trade.timestamp.to_rfc3339(),
            trade.commission,
            trade.trade_value
        );
        writer.write_all(row.as_bytes()).await?;
    }

    writer.finish().await?;
    Ok(())
}
```

**Performance Comparison**:
- Individual INSERTs: ~100 trades/sec
- Multi-value INSERT: ~500 trades/sec
- COPY command: ~5,000 trades/sec

### 4. Read Replica for Analytics

**Architecture**:
```
┌─────────────┐
│   Primary   │ ◄────── Writes (Trading App)
│   Database  │
└──────┬──────┘
       │
       │ Streaming Replication
       │
┌──────▼──────┐
│    Read     │ ◄────── Reads (Analytics, Reports)
│   Replica   │
└─────────────┘
```

**Configuration** (postgresql.conf on primary):
```ini
# Enable WAL archiving for replication
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
hot_standby = on
```

**Replica Setup**:
```bash
# On replica server
pg_basebackup -h primary-host -D /var/lib/postgresql/data -U replication -P -v -X stream

# Create recovery.conf
cat > /var/lib/postgresql/data/recovery.conf <<EOF
standby_mode = 'on'
primary_conninfo = 'host=primary-host port=5432 user=replication password=xxxx'
trigger_file = '/tmp/postgresql.trigger'
EOF
```

**Application Routing**:
```rust
pub struct DatabaseRouter {
    primary_pool: Pool,
    replica_pool: Pool,
}

impl DatabaseRouter {
    pub async fn execute_read<F, T>(&self, query: F) -> Result<T>
    where
        F: FnOnce(&Client) -> Future<Output = Result<T>>,
    {
        // Route reads to replica
        let client = self.replica_pool.get().await?;
        query(&client).await
    }

    pub async fn execute_write<F, T>(&self, query: F) -> Result<T>
    where
        F: FnOnce(&Client) -> Future<Output = Result<T>>,
    {
        // Route writes to primary
        let client = self.primary_pool.get().await?;
        query(&client).await
    }
}
```

### 5. Query Optimization

**Slow Query Monitoring**:
```sql
-- Enable slow query logging (postgresql.conf)
log_min_duration_statement = 1000  -- Log queries taking > 1 second

-- Create extension for query analysis
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

**Common Query Optimizations**:

1. **Position Lookup** (hot path):
```sql
-- Before (table scan)
SELECT * FROM positions WHERE symbol = 'AAPL';

-- After (index scan)
-- Already optimized with index on symbol

-- Add covering index for common queries
CREATE INDEX idx_positions_symbol_cover ON positions(symbol)
    INCLUDE (quantity, average_price, market_value, unrealized_pnl);
```

2. **Recent Orders Query**:
```sql
-- Before (slow)
SELECT * FROM orders
WHERE symbol = 'AAPL' AND status IN ('submitted', 'partial_fill')
ORDER BY submitted_at DESC;

-- After (fast with partial index)
-- Uses idx_orders_active partial index
```

3. **Trade History Query**:
```sql
-- Before (scans all partitions)
SELECT * FROM trades WHERE symbol = 'AAPL';

-- After (partition pruning)
SELECT * FROM trades
WHERE symbol = 'AAPL'
    AND timestamp >= '2025-10-01'
    AND timestamp < '2025-11-01';
```

### 6. Connection Pooling Best Practices

**Pool Configuration by Component**:

| Component | Pool Size | Rationale |
|-----------|-----------|-----------|
| Execution Engine | 5 | Low concurrency, high priority |
| Risk Manager | 3 | Periodic queries, medium priority |
| Market Data | 2 | Low frequency writes |
| Audit Logger | 2 | Background task, low priority |
| Analytics | 10 | High concurrency reads on replica |

**Total**: 22 connections (within typical PostgreSQL limit of 100)

### 7. Database Tuning Parameters

**Recommended postgresql.conf settings**:
```ini
# Memory
shared_buffers = 4GB                    # 25% of system RAM
effective_cache_size = 12GB             # 75% of system RAM
maintenance_work_mem = 1GB
work_mem = 64MB                         # For sorting/hashing

# Checkpoints
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
max_wal_size = 4GB
min_wal_size = 1GB

# Query Planning
random_page_cost = 1.1                  # For SSDs
effective_io_concurrency = 200          # For SSDs
default_statistics_target = 100

# Logging
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_duration = on
log_lock_waits = on

# Replication
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
hot_standby = on
```

---

## Migration Plan

### Phase 1: Schema Deployment (Week 1)

**Objectives**:
- Deploy database schema to staging
- Validate schema with test data
- Performance benchmark empty tables

**Tasks**:
1. Create database and user
2. Run DDL scripts
3. Create partitions for next 2 quarters
4. Load test data (1M trades, 10K orders)
5. Run performance tests
6. Document baseline metrics

**Success Criteria**:
- All tables created successfully
- Indexes operational
- Insert performance > 1000 trades/sec
- Query performance < 100ms for common queries

### Phase 2: Dual-Write Implementation (Week 2-3)

**Objectives**:
- Modify application to write to both memory and database
- Validate data consistency
- Monitor performance impact

**Architecture**:
```
┌──────────────┐
│  Application │
└──────┬───────┘
       │
       ├────────────┐
       │            │
       ▼            ▼
┌──────────┐  ┌──────────┐
│  Memory  │  │ Database │
│  Store   │  │ (Async)  │
└──────────┘  └──────────┘
```

**Implementation Steps**:
1. Add persistence coordinator to application
2. Modify position updates to write-through cache
3. Add async order/trade persistence
4. Deploy to staging
5. Run integration tests
6. Monitor for 3 days

**Rollback Plan**: Disable database writes via feature flag

### Phase 3: Read Migration (Week 4)

**Objectives**:
- Migrate reads from memory to database cache
- Validate read performance
- Test failure scenarios

**Implementation Steps**:
1. Implement position cache with DB backing
2. Modify startup to load positions from DB
3. Add reconciliation logic
4. Deploy to staging
5. Test crash recovery
6. Monitor for 3 days

**Rollback Plan**: Revert to memory-only reads via feature flag

### Phase 4: Production Deployment (Week 5)

**Objectives**:
- Deploy to production during market close
- Validate system behavior
- Monitor for issues

**Deployment Checklist**:
```
□ Create production database
□ Run DDL scripts
□ Create initial partitions
□ Configure connection pool
□ Enable database writes
□ Deploy application
□ Run reconciliation
□ Monitor for 1 hour
□ Validate first trade
□ Monitor for full trading day
□ Post-deployment review
```

**Rollback Plan**:
- Revert application to previous version
- Disable database feature flag
- Continue trading with memory-only state

### Phase 5: Optimization (Week 6-8)

**Objectives**:
- Optimize query performance
- Add read replica
- Implement automated backups
- Fine-tune connection pool

**Tasks**:
1. Analyze slow query log
2. Add missing indexes
3. Set up streaming replication
4. Configure backup schedule
5. Implement partition maintenance
6. Load testing with production data

### Migration Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database connection failures | Trading halted | Circuit breaker + memory fallback |
| Write performance degradation | Order delays | Connection pooling + bulk inserts |
| Reconciliation discrepancies | Position errors | Broker as source of truth + alerts |
| Partition maintenance missed | Query performance | Automated partition creation script |
| Backup storage exhaustion | Recovery impossible | Automated cleanup + monitoring |

---

## Operational Procedures

### Daily Operations

**Pre-Market (8:00 AM EST)**:
1. Verify database connectivity
2. Check disk space (> 20% free)
3. Review overnight backup status
4. Check replication lag (< 1 second)
5. Validate connection pool health

**During Market Hours (9:30 AM - 4:00 PM EST)**:
1. Monitor query performance dashboard
2. Watch for slow queries (> 1 second)
3. Monitor connection pool utilization
4. Track write latency metrics
5. Alert on database errors

**Post-Market (4:30 PM EST)**:
1. Run daily reconciliation
2. Generate risk snapshot report
3. Archive old audit logs
4. Review system health metrics
5. Plan any maintenance

### Weekly Operations

**Sunday 2:00 AM EST** (market closed):
1. Run VACUUM ANALYZE on all tables
2. Rebuild fragmented indexes
3. Create new partitions for upcoming period
4. Review slow query log
5. Update table statistics
6. Test backup restoration (monthly)

### Monitoring and Alerts

**Critical Alerts** (PagerDuty):
- Database connection failures
- Write latency > 100ms
- Replication lag > 10 seconds
- Disk space < 10%
- Backup failures

**Warning Alerts** (Email):
- Connection pool > 80% utilized
- Query execution time > 1 second
- Reconciliation discrepancies
- Disk space < 20%
- Replication lag > 5 seconds

**Metrics Dashboard** (Grafana):
```
┌─────────────────────────────────────────────────────────────┐
│                    Database Metrics                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐│
│ │ Query Latency   │ │ Connection Pool │ │  Write Rate     ││
│ │   P50: 5ms      │ │  10/20 active   │ │  150 writes/sec ││
│ │   P95: 15ms     │ │  50% utilized   │ │  avg: 10KB/write││
│ │   P99: 50ms     │ └─────────────────┘ └─────────────────┘│
│ └─────────────────┘                                          │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐│
│ │ Replication Lag │ │  Disk Usage     │ │  Table Sizes    ││
│ │   0.5 seconds   │ │  500GB / 1TB    │ │  trades: 200GB  ││
│ │   [HEALTHY]     │ │  50% utilized   │ │  orders: 5GB    ││
│ └─────────────────┘ └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Disaster Recovery

**Recovery Time Objective (RTO)**: 30 minutes
**Recovery Point Objective (RPO)**: 15 minutes (via WAL archiving)

**Disaster Scenarios**:

1. **Primary Database Failure**:
   - Promote read replica to primary (5 minutes)
   - Reconfigure application connection strings (5 minutes)
   - Run reconciliation (10 minutes)
   - Resume trading

2. **Complete Data Center Failure**:
   - Restore from S3 backup to new instance (15 minutes)
   - Apply WAL archives for point-in-time recovery (10 minutes)
   - Run reconciliation (10 minutes)
   - Resume trading

3. **Data Corruption**:
   - Identify last good backup (5 minutes)
   - Restore to point before corruption (15 minutes)
   - Replay orders from audit log (10 minutes)
   - Reconcile with broker (10 minutes)

### Capacity Planning

**Current Estimates** (based on typical trading volume):
- Orders: ~1,000/day = 250K/year = 2.5M in 10 years
- Trades: ~500/day = 125K/year = 1.25M in 10 years
- Audit logs: ~50K/day = 12.5M/year = 125M in 10 years

**Storage Projection**:
```
Year 1:  50 GB
Year 2:  120 GB
Year 3:  200 GB
Year 5:  400 GB
Year 10: 1 TB
```

**Scaling Triggers**:
- Database size > 750 GB → Add disk space
- Write rate > 5,000/sec → Optimize batch inserts
- Connection pool > 90% → Increase pool size
- Replication lag > 30 sec → Upgrade replica hardware

---

## Appendix

### A. Connection String Format

```
postgresql://username:password@host:port/database?options

Examples:
- Development: postgresql://trading_user:password@localhost:5432/trading_system
- Production:  postgresql://trading_user:password@db.example.com:5432/trading_system?sslmode=require
- Replica:     postgresql://trading_user:password@db-replica.example.com:5432/trading_system?sslmode=require
```

### B. Useful SQL Queries

**Table Sizes**:
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Index Usage**:
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

**Active Connections**:
```sql
SELECT
    datname,
    usename,
    application_name,
    client_addr,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'trading_system';
```

### C. Rust Dependencies

Add to `Cargo.toml`:
```toml
[dependencies]
tokio-postgres = "0.7"
deadpool-postgres = "0.11"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
chrono = { version = "0.4", features = ["serde"] }
rust_decimal = "1.32"
anyhow = "1.0"
```

### D. Environment Variables

Required for database connection:
```bash
DATABASE_URL=postgresql://trading_user:password@localhost:5432/trading_system
DATABASE_POOL_SIZE=20
DATABASE_TIMEOUT_SECONDS=5
DATABASE_SSL_MODE=require  # For production
```

### E. Schema Version Control

Use migration tool (e.g., refinery or sqlx-cli):
```bash
# Create migration
sqlx migrate add create_positions_table

# Run migrations
sqlx migrate run

# Revert last migration
sqlx migrate revert
```

---

## Summary

This architecture provides:

✅ **Durability**: All critical state persisted with ACID guarantees
✅ **Performance**: Write-through caching + connection pooling for sub-10ms latency
✅ **Scalability**: Partitioning + read replicas for growth
✅ **Recoverability**: Position reconciliation + broker as source of truth
✅ **Auditability**: Complete audit trail with JSONB flexibility
✅ **Operational Excellence**: Automated backups, monitoring, disaster recovery

**Next Steps**:
1. Review and approve architecture
2. Set up staging database
3. Begin Phase 1 implementation (schema deployment)
4. Develop persistence coordinator
5. Integration testing

---

**Document Version**: 1.0
**Last Updated**: 2025-10-21
**Author**: System Architecture Team
**Status**: Ready for Review
