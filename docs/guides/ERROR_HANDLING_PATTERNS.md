# Error Handling Patterns & Best Practices

**Version:** 1.0.0
**Last Updated:** 2025-10-21

---

## Table of Contents

1. [Overview](#overview)
2. [Error Type Hierarchy](#error-type-hierarchy)
3. [Common Patterns](#common-patterns)
4. [Database Error Handling](#database-error-handling)
5. [Network Error Handling](#network-error-handling)
6. [Recovery Strategies](#recovery-strategies)
7. [Logging Best Practices](#logging-best-practices)
8. [Testing Error Paths](#testing-error-paths)

---

## Overview

The trading system uses a comprehensive error handling strategy built on Rust's `Result<T, E>` type, `anyhow` for error propagation, and `thiserror` for custom error types.

### Error Handling Philosophy

1. **Fail Fast:** Detect errors early, fail loudly
2. **Contextualize:** Add context at each layer
3. **Recover Gracefully:** Attempt recovery where safe
4. **Log Everything:** Record all errors for debugging
5. **Never Panic:** Use `Result` instead of unwrap/expect

---

## Error Type Hierarchy

### Common Module Errors

**File:** `rust/common/src/error.rs`

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum TradingError {
    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Connection error: {0}")]
    Connection(String),

    #[error("Network error: {0}")]
    Network(String),

    #[error("Database error: {0}")]
    Database(String),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Risk limit exceeded: {0}")]
    RiskLimit(String),

    #[error("Order error: {0}")]
    Order(String),

    #[error("Position error: {0}")]
    Position(String),

    #[error("Market data error: {0}")]
    MarketData(String),

    #[error("Execution error: {0}")]
    Execution(String),

    #[error("Timeout: {0}")]
    Timeout(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

// Convenience type alias
pub type Result<T> = std::result::Result<T, TradingError>;
```

### Database Module Errors

**File:** `rust/database/src/error.rs`

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum DatabaseError {
    #[error("Connection error: {0}")]
    Connection(String),

    #[error("Pool error: {0}")]
    Pool(String),

    #[error("Query error: {0}")]
    Query(String),

    #[error("Schema error: {0}")]
    Schema(String),

    #[error("Migration error: {0}")]
    Migration(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("DuckDB error: {0}")]
    DuckDb(#[from] duckdb::Error),

    #[error("Pool error: {0}")]
    R2d2(#[from] r2d2::Error),
}

// Conversion to anyhow::Error
impl From<DatabaseError> for anyhow::Error {
    fn from(err: DatabaseError) -> Self {
        anyhow::anyhow!(err)
    }
}

pub type Result<T> = std::result::Result<T, DatabaseError>;
```

---

## Common Patterns

### Pattern 1: Error Propagation with Context

**Use `context()` from `anyhow` to add information:**

```rust
use anyhow::{Context, Result};

fn process_order(order_id: &str) -> Result<Order> {
    let order = fetch_order(order_id)
        .context(format!("Failed to fetch order {}", order_id))?;

    validate_order(&order)
        .context("Order validation failed")?;

    submit_order(&order)
        .context(format!("Failed to submit order {}", order_id))?;

    Ok(order)
}

// Error output will show:
// Error: Failed to submit order abc123
// Caused by:
//     Network error: Connection timeout
```

### Pattern 2: Custom Error with Conversion

**Define conversions for seamless error propagation:**

```rust
impl From<std::io::Error> for TradingError {
    fn from(err: std::io::Error) -> Self {
        TradingError::Internal(format!("IO error: {}", err))
    }
}

impl From<serde_json::Error> for TradingError {
    fn from(err: serde_json::Error) -> Self {
        TradingError::Serialization(format!("JSON error: {}", err))
    }
}

// Now you can use ? operator seamlessly
fn read_config(path: &str) -> Result<Config, TradingError> {
    let contents = std::fs::read_to_string(path)?; // io::Error -> TradingError
    let config: Config = serde_json::from_str(&contents)?; // serde_json::Error -> TradingError
    Ok(config)
}
```

### Pattern 3: Error Recovery

**Attempt recovery before propagating error:**

```rust
fn connect_with_retry(url: &str, max_retries: u32) -> Result<Connection> {
    let mut attempts = 0;

    loop {
        match connect(url) {
            Ok(conn) => {
                info!("Connected successfully on attempt {}", attempts + 1);
                return Ok(conn);
            }
            Err(e) if attempts < max_retries => {
                warn!("Connection attempt {} failed: {}", attempts + 1, e);
                attempts += 1;
                std::thread::sleep(Duration::from_secs(2u64.pow(attempts)));
            }
            Err(e) => {
                error!("All connection attempts failed");
                return Err(TradingError::Connection(
                    format!("Failed after {} attempts: {}", max_retries, e)
                ));
            }
        }
    }
}
```

### Pattern 4: Validate Early, Fail Fast

**Check preconditions before expensive operations:**

```rust
fn submit_order(order: &Order) -> Result<()> {
    // Validate inputs first
    if order.quantity.0 <= 0.0 {
        return Err(TradingError::Validation(
            "Order quantity must be positive".to_string()
        ));
    }

    if order.price.0 <= 0.0 {
        return Err(TradingError::Validation(
            "Order price must be positive".to_string()
        ));
    }

    if order.symbol.0.is_empty() {
        return Err(TradingError::Validation(
            "Order symbol cannot be empty".to_string()
        ));
    }

    // Now perform expensive operation
    execute_order(order)?;

    Ok(())
}
```

### Pattern 5: Error Logging with Context

**Log errors at appropriate levels:**

```rust
use tracing::{error, warn, info, debug};

fn process_tick(tick: &Tick) -> Result<()> {
    debug!("Processing tick: {:?}", tick);

    match update_orderbook(tick) {
        Ok(_) => {
            debug!("OrderBook updated successfully");
        }
        Err(e) => {
            // Warning level - non-critical error
            warn!("Failed to update orderbook: {}", e);
            // Continue processing despite error
        }
    }

    match publish_tick(tick) {
        Ok(_) => {
            debug!("Tick published successfully");
            Ok(())
        }
        Err(e) => {
            // Error level - critical failure
            error!("Failed to publish tick: {}", e);
            Err(TradingError::MarketData(format!("Publish failed: {}", e)))
        }
    }
}
```

---

## Database Error Handling

### Connection Pool Errors

```rust
use database::{DatabaseManager, DatabaseError};

async fn get_metrics() -> Result<Vec<MetricRecord>, DatabaseError> {
    let db = DatabaseManager::new("metrics.duckdb").await?;

    // Handle connection acquisition failure
    match db.get_metrics("latency", None, None, 100).await {
        Ok(metrics) => Ok(metrics),
        Err(DatabaseError::Pool(e)) => {
            error!("Connection pool exhausted: {}", e);
            // Wait and retry once
            tokio::time::sleep(Duration::from_millis(500)).await;
            db.get_metrics("latency", None, None, 100).await
        }
        Err(e) => Err(e),
    }
}
```

### Query Errors

```rust
async fn insert_batch_safe(
    db: &DatabaseManager,
    metrics: &[MetricRecord],
) -> Result<usize, DatabaseError> {
    match db.insert_metrics(metrics).await {
        Ok(count) => {
            info!("Inserted {} metrics successfully", count);
            Ok(count)
        }
        Err(DatabaseError::Query(e)) if e.contains("UNIQUE constraint") => {
            warn!("Duplicate metrics detected, filtering...");
            // Filter out duplicates and retry
            let unique_metrics = deduplicate_metrics(metrics);
            db.insert_metrics(&unique_metrics).await
        }
        Err(DatabaseError::Serialization(e)) => {
            error!("Serialization error: {}", e);
            // Try inserting one at a time to isolate bad record
            insert_one_by_one(db, metrics).await
        }
        Err(e) => {
            error!("Unrecoverable database error: {}", e);
            Err(e)
        }
    }
}

async fn insert_one_by_one(
    db: &DatabaseManager,
    metrics: &[MetricRecord],
) -> Result<usize, DatabaseError> {
    let mut success_count = 0;

    for metric in metrics {
        match db.insert_metric(metric).await {
            Ok(_) => success_count += 1,
            Err(e) => {
                error!("Failed to insert metric {:?}: {}", metric, e);
                // Continue with next metric
            }
        }
    }

    Ok(success_count)
}
```

### Schema Migration Errors

```rust
use database::migrations::MigrationManager;

async fn run_migrations(db: &DatabaseManager) -> Result<(), DatabaseError> {
    let manager = MigrationManager::new(db);

    // Initialize migration tracking table
    if let Err(e) = manager.init_migrations_table().await {
        error!("Failed to initialize migrations table: {}", e);
        return Err(DatabaseError::Migration(
            "Cannot proceed without migration tracking".to_string()
        ));
    }

    // Get migrations
    let migrations = manager.get_builtin_migrations();

    // Apply each migration with rollback on failure
    for migration in migrations {
        match manager.apply(&migration).await {
            Ok(_) => {
                info!("Applied migration: {}", migration.version);
            }
            Err(e) => {
                error!("Migration {} failed: {}", migration.version, e);

                // Attempt rollback
                if let Err(rollback_err) = manager.rollback(&migration).await {
                    error!("Rollback also failed: {}", rollback_err);
                    return Err(DatabaseError::Migration(
                        format!("Migration failed and rollback failed: {} -> {}", e, rollback_err)
                    ));
                }

                warn!("Migration rolled back successfully");
                return Err(DatabaseError::Migration(
                    format!("Migration {} failed but was rolled back: {}", migration.version, e)
                ));
            }
        }
    }

    info!("All migrations applied successfully");
    Ok(())
}
```

---

## Network Error Handling

### WebSocket Reconnection

```rust
use tokio_tungstenite::{connect_async, tungstenite::Error as WsError};

async fn maintain_websocket_connection(url: &str) -> Result<()> {
    let mut reconnect_attempts = 0;
    const MAX_RECONNECT_ATTEMPTS: u32 = 5;

    loop {
        match connect_async(url).await {
            Ok((ws_stream, _)) => {
                info!("WebSocket connected");
                reconnect_attempts = 0; // Reset on success

                // Handle connection
                if let Err(e) = handle_websocket(ws_stream).await {
                    warn!("WebSocket handler error: {}", e);
                    // Will reconnect after loop iteration
                }
            }
            Err(WsError::Http(response)) if response.status().is_server_error() => {
                error!("Server error: {}", response.status());
                reconnect_attempts += 1;

                if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS {
                    return Err(TradingError::Connection(
                        "Max reconnection attempts reached".to_string()
                    ));
                }

                // Exponential backoff
                let delay = Duration::from_secs(2u64.pow(reconnect_attempts));
                warn!("Retrying in {:?}...", delay);
                tokio::time::sleep(delay).await;
            }
            Err(e) => {
                error!("WebSocket connection error: {}", e);
                return Err(TradingError::Network(format!("Connection failed: {}", e)));
            }
        }
    }
}
```

### HTTP Request with Timeout

```rust
use reqwest::{Client, StatusCode};
use tokio::time::timeout;

async fn fetch_with_timeout(url: &str) -> Result<String, TradingError> {
    let client = Client::new();

    // Set request timeout
    let request = client
        .get(url)
        .timeout(Duration::from_secs(10))
        .send();

    // Wrap in tokio timeout for additional safety
    match timeout(Duration::from_secs(15), request).await {
        Ok(Ok(response)) => {
            match response.status() {
                StatusCode::OK => {
                    let body = response.text().await
                        .map_err(|e| TradingError::Network(format!("Body read error: {}", e)))?;
                    Ok(body)
                }
                StatusCode::TOO_MANY_REQUESTS => {
                    warn!("Rate limited, backing off...");
                    tokio::time::sleep(Duration::from_secs(60)).await;
                    fetch_with_timeout(url).await // Retry
                }
                status => {
                    Err(TradingError::Network(format!("HTTP {}", status)))
                }
            }
        }
        Ok(Err(e)) => {
            Err(TradingError::Network(format!("Request error: {}", e)))
        }
        Err(_) => {
            Err(TradingError::Timeout("Request timeout exceeded".to_string()))
        }
    }
}
```

---

## Recovery Strategies

### Circuit Breaker Pattern

```rust
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;

struct CircuitBreaker {
    state: Arc<AtomicBool>, // true = open (failing), false = closed (working)
    failure_count: Arc<AtomicU32>,
    threshold: u32,
    reset_timeout: Duration,
    last_failure: Arc<tokio::sync::Mutex<Option<Instant>>>,
}

impl CircuitBreaker {
    fn new(threshold: u32, reset_timeout: Duration) -> Self {
        Self {
            state: Arc::new(AtomicBool::new(false)),
            failure_count: Arc::new(AtomicU32::new(0)),
            threshold,
            reset_timeout,
            last_failure: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }

    async fn call<F, T>(&self, f: F) -> Result<T, TradingError>
    where
        F: FnOnce() -> Result<T, TradingError>,
    {
        // Check if circuit is open
        if self.state.load(Ordering::Acquire) {
            let last_failure = self.last_failure.lock().await;

            if let Some(time) = *last_failure {
                if time.elapsed() < self.reset_timeout {
                    return Err(TradingError::Internal(
                        "Circuit breaker open".to_string()
                    ));
                }
            }

            // Timeout elapsed, try half-open state
            drop(last_failure);
            self.state.store(false, Ordering::Release);
            self.failure_count.store(0, Ordering::Release);
        }

        // Execute function
        match f() {
            Ok(result) => {
                // Success - reset failure count
                self.failure_count.store(0, Ordering::Release);
                Ok(result)
            }
            Err(e) => {
                // Failure - increment count
                let failures = self.failure_count.fetch_add(1, Ordering::AcqRel) + 1;

                if failures >= self.threshold {
                    // Open circuit
                    self.state.store(true, Ordering::Release);
                    *self.last_failure.lock().await = Some(Instant::now());
                    error!("Circuit breaker opened after {} failures", failures);
                }

                Err(e)
            }
        }
    }
}

// Usage
async fn fetch_data_with_circuit_breaker() -> Result<Data> {
    static CIRCUIT_BREAKER: Lazy<CircuitBreaker> = Lazy::new(|| {
        CircuitBreaker::new(5, Duration::from_secs(60))
    });

    CIRCUIT_BREAKER.call(|| {
        fetch_data_from_api()
    }).await
}
```

### Graceful Degradation

```rust
async fn get_market_data(symbol: &str) -> Result<MarketData> {
    // Try primary source
    match fetch_from_primary(symbol).await {
        Ok(data) => {
            info!("Got data from primary source");
            return Ok(data);
        }
        Err(e) => {
            warn!("Primary source failed: {}, trying backup...", e);
        }
    }

    // Try backup source
    match fetch_from_backup(symbol).await {
        Ok(data) => {
            warn!("Using backup data source");
            return Ok(data);
        }
        Err(e) => {
            error!("Backup source also failed: {}", e);
        }
    }

    // Use cached data if available
    if let Some(cached) = get_cached_data(symbol).await {
        warn!("Using cached data (may be stale)");
        return Ok(cached);
    }

    // All options exhausted
    Err(TradingError::MarketData(
        format!("All data sources failed for {}", symbol)
    ))
}
```

---

## Logging Best Practices

### Structured Logging with Tracing

```rust
use tracing::{info, warn, error, instrument};

#[instrument(skip(db), fields(symbol = %order.symbol))]
async fn process_order(db: &DatabaseManager, order: &Order) -> Result<()> {
    info!(
        order_id = %order.id,
        quantity = %order.quantity.0,
        price = %order.price.0,
        "Processing order"
    );

    match validate_order(order) {
        Ok(_) => info!("Order validation passed"),
        Err(e) => {
            error!(
                error = %e,
                order_id = %order.id,
                "Order validation failed"
            );
            return Err(e);
        }
    }

    submit_order(order).await?;

    info!(order_id = %order.id, "Order processed successfully");
    Ok(())
}
```

### Error Context in Logs

```rust
use anyhow::Context;

async fn load_config(path: &str) -> Result<Config> {
    let contents = tokio::fs::read_to_string(path)
        .await
        .context(format!("Failed to read config file: {}", path))?;

    let config: Config = serde_json::from_str(&contents)
        .context("Failed to parse config JSON")?;

    info!(path = %path, "Config loaded successfully");

    Ok(config)
}

// Error output:
// ERROR Failed to parse config JSON
// Caused by:
//     missing field `api_key` at line 10 column 1
```

---

## Testing Error Paths

### Unit Tests for Errors

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_invalid_order_quantity() {
        let order = Order {
            quantity: Quantity(-10.0), // Invalid
            ..Default::default()
        };

        let result = validate_order(&order);
        assert!(result.is_err());

        match result.unwrap_err() {
            TradingError::Validation(msg) => {
                assert!(msg.contains("positive"));
            }
            _ => panic!("Expected validation error"),
        }
    }

    #[tokio::test]
    async fn test_connection_retry_exhaustion() {
        let url = "http://invalid-url:9999";
        let result = connect_with_retry(url, 3).await;

        assert!(result.is_err());

        match result.unwrap_err() {
            TradingError::Connection(msg) => {
                assert!(msg.contains("Failed after 3 attempts"));
            }
            _ => panic!("Expected connection error"),
        }
    }

    #[tokio::test]
    async fn test_database_duplicate_handling() {
        let db = DatabaseManager::new(":memory:").await.unwrap();
        db.initialize().await.unwrap();

        let metric = MetricRecord::new("test", 1.0);

        // First insert succeeds
        assert!(db.insert_metric(&metric).await.is_ok());

        // Duplicate insert should be handled gracefully
        let result = insert_batch_safe(&db, &[metric.clone()]).await;
        assert!(result.is_ok());
    }
}
```

---

## Summary Checklist

### Error Handling Best Practices

✅ **Use `Result<T, E>` everywhere** - Never use unwrap/expect in production code
✅ **Add context** - Use `.context()` to add meaningful error messages
✅ **Log appropriately** - Error/warn/info based on severity
✅ **Recover when safe** - Retry transient failures
✅ **Fail fast** - Validate early, propagate errors immediately
✅ **Test error paths** - Write tests for error conditions
✅ **Document errors** - Explain possible errors in function docs
✅ **Use custom error types** - Define domain-specific errors with `thiserror`
✅ **Never panic** - Handle all error cases gracefully
✅ **Propagate with ?** - Use the `?` operator for clean error propagation

For more information, see:
- `rust/common/src/error.rs` - Common error types
- `rust/database/src/error.rs` - Database error types
- `docs/API_DOCUMENTATION.md` - API error responses
- `docs/testing/TEST_STRATEGY.md` - Error testing strategy
