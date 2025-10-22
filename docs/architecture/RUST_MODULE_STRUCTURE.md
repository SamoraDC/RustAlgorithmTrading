# Rust Module Structure for DuckDB Database Layer

**Date**: October 21, 2025
**Author**: Hive Mind Architecture Agent
**Purpose**: Define complete Rust module organization for DuckDB integration

---

## 1. Directory Structure

```
rust/
├── Cargo.toml                          # Workspace configuration
├── database/                           # NEW: DuckDB database crate
│   ├── Cargo.toml
│   ├── README.md
│   ├── src/
│   │   ├── lib.rs                      # Public API exports
│   │   ├── config.rs                   # Configuration management
│   │   ├── error.rs                    # Error types and handling
│   │   ├── connection/                 # Connection management
│   │   │   ├── mod.rs
│   │   │   ├── pool.rs                 # Connection pooling
│   │   │   ├── reader.rs               # Read connection wrapper
│   │   │   └── writer.rs               # Write connection wrapper
│   │   ├── models/                     # Domain models
│   │   │   ├── mod.rs
│   │   │   ├── order.rs
│   │   │   ├── trade.rs
│   │   │   ├── position.rs
│   │   │   ├── market_data.rs
│   │   │   └── portfolio.rs
│   │   ├── repositories/               # Data access layer
│   │   │   ├── mod.rs
│   │   │   ├── traits.rs               # Repository traits
│   │   │   ├── order_repository.rs
│   │   │   ├── trade_repository.rs
│   │   │   ├── position_repository.rs
│   │   │   ├── market_data_repository.rs
│   │   │   └── metrics_repository.rs
│   │   ├── query/                      # Query building
│   │   │   ├── mod.rs
│   │   │   ├── builder.rs              # SQL query builder
│   │   │   ├── filter.rs               # Query filters
│   │   │   └── pagination.rs           # Pagination helpers
│   │   ├── migrations/                 # Schema migrations
│   │   │   ├── mod.rs
│   │   │   ├── runner.rs               # Migration runner
│   │   │   ├── v001_initial_schema.rs
│   │   │   ├── v002_add_metrics.rs
│   │   │   └── v003_add_indexes.rs
│   │   ├── observability/              # Metrics and tracing
│   │   │   ├── mod.rs
│   │   │   ├── metrics.rs              # Prometheus metrics
│   │   │   ├── tracing.rs              # Distributed tracing
│   │   │   └── slow_query_log.rs       # Slow query detection
│   │   ├── partitioning/               # Partition management
│   │   │   ├── mod.rs
│   │   │   ├── lifecycle.rs            # Partition lifecycle
│   │   │   └── export.rs               # Parquet export
│   │   ├── backup/                     # Backup and recovery
│   │   │   ├── mod.rs
│   │   │   ├── backup.rs
│   │   │   └── restore.rs
│   │   └── testing/                    # Test utilities
│   │       ├── mod.rs
│   │       ├── fixtures.rs             # Test data fixtures
│   │       └── mocks.rs                # Mock implementations
│   ├── tests/
│   │   ├── integration_tests.rs        # Integration tests
│   │   ├── connection_pool_tests.rs
│   │   ├── repository_tests.rs
│   │   └── migration_tests.rs
│   ├── benches/
│   │   ├── query_benchmarks.rs         # Query performance
│   │   ├── insert_benchmarks.rs        # Write performance
│   │   └── concurrent_benchmarks.rs    # Concurrency tests
│   └── examples/
│       ├── basic_usage.rs
│       ├── transaction_example.rs
│       └── batch_insert_example.rs
├── market-data/                        # Existing crate
│   └── Cargo.toml
├── signal-bridge/                      # Existing crate
│   └── Cargo.toml
├── risk-manager/                       # Existing crate
│   └── Cargo.toml
├── execution-engine/                   # Existing crate
│   └── Cargo.toml
└── common/                             # Existing shared crate
    ├── Cargo.toml
    └── src/
        ├── lib.rs
        └── types.rs                    # Shared types across all crates
```

---

## 2. lib.rs - Public API

```rust
// rust/database/src/lib.rs

//! DuckDB database layer for trading system
//!
//! This crate provides high-performance database access to market data,
//! orders, trades, and positions using DuckDB.
//!
//! # Features
//! - Connection pooling (50+ concurrent readers)
//! - Repository pattern for data access
//! - Automatic partitioning and retention
//! - Observability (metrics, tracing)
//! - Migration management
//!
//! # Example
//! ```no_run
//! use database::{DatabaseConfig, DuckDBConnectionPool, repositories::OrderRepository};
//!
//! #[tokio::main]
//! async fn main() -> Result<()> {
//!     let config = DatabaseConfig::default();
//!     let pool = DuckDBConnectionPool::new(config).await?;
//!     let order_repo = OrderRepository::new(pool.clone());
//!
//!     let orders = order_repo.find_by_symbol("AAPL", 100).await?;
//!     println!("Found {} orders", orders.len());
//!     Ok(())
//! }
//! ```

// Re-export main types
pub use config::{DatabaseConfig, PoolConfig, PerformanceConfig};
pub use error::{DatabaseError, Result};
pub use connection::pool::DuckDBConnectionPool;

// Re-export models
pub use models::{Order, Trade, Position, MarketTick, OHLCVBar, PortfolioSnapshot};

// Re-export repositories
pub use repositories::{
    OrderRepository,
    TradeRepository,
    PositionRepository,
    MarketDataRepository,
    MetricsRepository,
};

// Module declarations
pub mod config;
pub mod error;
pub mod connection;
pub mod models;
pub mod repositories;
pub mod query;
pub mod migrations;
pub mod observability;
pub mod partitioning;
pub mod backup;

#[cfg(test)]
pub mod testing;
```

---

## 3. Core Modules

### 3.1 config.rs

```rust
// rust/database/src/config.rs

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use anyhow::Result;

/// Main database configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    /// Path to DuckDB database file
    pub database_path: PathBuf,

    /// Connection pool configuration
    pub pool: PoolConfig,

    /// Performance tuning
    pub performance: PerformanceConfig,

    /// Observability settings
    pub observability: ObservabilityConfig,

    /// Data retention policies
    pub retention: RetentionConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoolConfig {
    /// Maximum number of read connections
    #[serde(default = "default_max_readers")]
    pub max_readers: usize,

    /// Connection timeout in milliseconds
    #[serde(default = "default_connection_timeout")]
    pub connection_timeout_ms: u64,

    /// Query timeout in milliseconds
    #[serde(default = "default_query_timeout")]
    pub query_timeout_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    /// Memory limit in megabytes
    #[serde(default = "default_memory_limit")]
    pub memory_limit_mb: usize,

    /// Number of threads for query execution
    #[serde(default = "default_num_threads")]
    pub num_threads: usize,

    /// Temporary directory for spilling
    pub temp_directory: PathBuf,

    /// Enable query profiling
    #[serde(default)]
    pub enable_profiling: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObservabilityConfig {
    /// Enable Prometheus metrics
    #[serde(default = "default_true")]
    pub enable_metrics: bool,

    /// Enable distributed tracing
    #[serde(default = "default_true")]
    pub enable_tracing: bool,

    /// Slow query threshold in milliseconds
    #[serde(default = "default_slow_query_threshold")]
    pub slow_query_threshold_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionConfig {
    /// Days to keep in hot tier (in-memory/fast)
    #[serde(default = "default_hot_days")]
    pub hot_data_days: u32,

    /// Days to keep in warm tier (on-disk)
    #[serde(default = "default_warm_days")]
    pub warm_data_days: u32,

    /// Days to keep in cold tier (Parquet archives)
    #[serde(default = "default_cold_days")]
    pub cold_data_days: u32,
}

// Default value functions
fn default_max_readers() -> usize { 50 }
fn default_connection_timeout() -> u64 { 5000 }
fn default_query_timeout() -> u64 { 30000 }
fn default_memory_limit() -> usize { 8192 }
fn default_num_threads() -> usize { 4 }
fn default_true() -> bool { true }
fn default_slow_query_threshold() -> u64 { 1000 }
fn default_hot_days() -> u32 { 7 }
fn default_warm_days() -> u32 { 90 }
fn default_cold_days() -> u32 { 365 }

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            database_path: PathBuf::from("/data/trading.duckdb"),
            pool: PoolConfig::default(),
            performance: PerformanceConfig::default(),
            observability: ObservabilityConfig::default(),
            retention: RetentionConfig::default(),
        }
    }
}

impl DatabaseConfig {
    /// Load configuration from TOML file
    pub fn from_file(path: &str) -> Result<Self> {
        let contents = std::fs::read_to_string(path)?;
        let config = toml::from_str(&contents)?;
        Ok(config)
    }

    /// Load configuration from environment variables
    pub fn from_env() -> Self {
        let mut config = Self::default();

        if let Ok(path) = std::env::var("DATABASE_PATH") {
            config.database_path = PathBuf::from(path);
        }

        if let Ok(mem) = std::env::var("DATABASE_MEMORY_LIMIT_MB") {
            config.performance.memory_limit_mb = mem.parse().unwrap_or(8192);
        }

        config
    }
}
```

### 3.2 error.rs

```rust
// rust/database/src/error.rs

use thiserror::Error;

pub type Result<T> = std::result::Result<T, DatabaseError>;

#[derive(Error, Debug)]
pub enum DatabaseError {
    #[error("Connection timeout after {timeout_ms}ms")]
    ConnectionTimeout { timeout_ms: u64 },

    #[error("Query timeout: {query}")]
    QueryTimeout { query: String },

    #[error("Write conflict: {message}")]
    WriteConflict { message: String },

    #[error("Disk full: {path}")]
    DiskFull { path: String },

    #[error("Migration failed: {version} - {message}")]
    MigrationFailed { version: String, message: String },

    #[error("Partition not found: {partition_id}")]
    PartitionNotFound { partition_id: String },

    #[error("Validation error: {0}")]
    ValidationError(String),

    #[error("Not found: {entity_type} with id {id}")]
    NotFound { entity_type: String, id: String },

    #[error("DuckDB error: {0}")]
    DuckDB(#[from] duckdb::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Configuration error: {0}")]
    Config(#[from] toml::de::Error),
}

impl DatabaseError {
    /// Check if error is transient and can be retried
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            DatabaseError::ConnectionTimeout { .. } |
            DatabaseError::WriteConflict { .. }
        )
    }

    /// Get HTTP status code for API errors
    pub fn status_code(&self) -> u16 {
        match self {
            DatabaseError::NotFound { .. } => 404,
            DatabaseError::ValidationError(_) => 400,
            DatabaseError::ConnectionTimeout { .. } => 503,
            _ => 500,
        }
    }
}
```

### 3.3 connection/pool.rs

```rust
// rust/database/src/connection/pool.rs

use crate::{DatabaseConfig, DatabaseError, Result};
use duckdb::{Connection, AccessMode};
use tokio::sync::{RwLock, Semaphore};
use std::sync::Arc;
use tracing::{info, warn, instrument};

/// DuckDB connection pool with single-writer, multiple-reader pattern
pub struct DuckDBConnectionPool {
    writer: Arc<RwLock<Connection>>,
    readers: Vec<Arc<Connection>>,
    reader_semaphore: Arc<Semaphore>,
    config: DatabaseConfig,
}

impl DuckDBConnectionPool {
    /// Create new connection pool
    #[instrument(skip(config))]
    pub async fn new(config: DatabaseConfig) -> Result<Arc<Self>> {
        info!(
            "Initializing DuckDB connection pool at {:?}",
            config.database_path
        );

        // Create writer connection
        let writer = Connection::open(&config.database_path)?;
        configure_connection(&writer, &config)?;

        // Create reader connections
        let mut readers = Vec::with_capacity(config.pool.max_readers);
        for i in 0..config.pool.max_readers {
            let reader = Connection::open_with_flags(
                &config.database_path,
                AccessMode::ReadOnly
            )?;
            configure_connection(&reader, &config)?;
            readers.push(Arc::new(reader));

            if i % 10 == 0 {
                info!("Created {}/{} read connections", i + 1, config.pool.max_readers);
            }
        }

        info!("Connection pool initialized successfully");

        Ok(Arc::new(Self {
            writer: Arc::new(RwLock::new(writer)),
            readers,
            reader_semaphore: Arc::new(Semaphore::new(config.pool.max_readers)),
            config,
        }))
    }

    /// Get writer connection (exclusive lock)
    #[instrument(skip(self))]
    pub async fn get_writer(&self) -> WriteConnection {
        let conn = self.writer.write().await;
        WriteConnection { conn }
    }

    /// Get reader connection (shared)
    #[instrument(skip(self))]
    pub async fn get_reader(&self) -> Result<ReadConnection> {
        let permit = self.reader_semaphore.acquire().await
            .map_err(|_| DatabaseError::ConnectionTimeout {
                timeout_ms: self.config.pool.connection_timeout_ms
            })?;

        // Load balance across readers
        let reader_idx = rand::random::<usize>() % self.readers.len();
        let conn = self.readers[reader_idx].clone();

        Ok(ReadConnection {
            conn,
            _permit: permit,
        })
    }

    /// Get pool statistics
    pub fn stats(&self) -> PoolStats {
        PoolStats {
            total_readers: self.readers.len(),
            available_readers: self.reader_semaphore.available_permits(),
            writer_locked: self.writer.try_write().is_err(),
        }
    }
}

/// Configure DuckDB connection with performance settings
fn configure_connection(conn: &Connection, config: &DatabaseConfig) -> Result<()> {
    conn.execute_batch(&format!(
        "PRAGMA threads={};
         PRAGMA memory_limit='{}MB';
         PRAGMA temp_directory='{}';",
        config.performance.num_threads,
        config.performance.memory_limit_mb,
        config.performance.temp_directory.display()
    ))?;
    Ok(())
}

#[derive(Debug)]
pub struct PoolStats {
    pub total_readers: usize,
    pub available_readers: usize,
    pub writer_locked: bool,
}
```

---

## 4. Repository Pattern

### 4.1 repositories/traits.rs

```rust
// rust/database/src/repositories/traits.rs

use crate::Result;
use async_trait::async_trait;

/// Generic repository trait for CRUD operations
#[async_trait]
pub trait Repository<T, ID> {
    async fn create(&self, entity: &T) -> Result<T>;
    async fn find_by_id(&self, id: ID) -> Result<Option<T>>;
    async fn update(&self, entity: &T) -> Result<T>;
    async fn delete(&self, id: ID) -> Result<()>;
    async fn find_all(&self, filter: &QueryFilter) -> Result<Vec<T>>;
}

#[derive(Debug, Clone, Default)]
pub struct QueryFilter {
    pub limit: Option<usize>,
    pub offset: Option<usize>,
    pub order_by: Option<String>,
    pub filters: Vec<(String, FilterValue)>,
}

#[derive(Debug, Clone)]
pub enum FilterValue {
    String(String),
    Int(i64),
    Float(f64),
    Bool(bool),
}
```

### 4.2 repositories/order_repository.rs

```rust
// rust/database/src/repositories/order_repository.rs

use crate::{
    connection::DuckDBConnectionPool,
    models::Order,
    Result,
    DatabaseError,
};
use std::sync::Arc;
use duckdb::params;
use uuid::Uuid;
use tracing::instrument;

pub struct OrderRepository {
    pool: Arc<DuckDBConnectionPool>,
}

impl OrderRepository {
    pub fn new(pool: Arc<DuckDBConnectionPool>) -> Self {
        Self { pool }
    }

    #[instrument(skip(self, order))]
    pub async fn create_order(&self, order: &Order) -> Result<Order> {
        let writer = self.pool.get_writer().await;

        writer.conn.execute(
            "INSERT INTO orders (
                order_id, client_order_id, exchange, symbol, side,
                order_type, quantity, price, status, correlation_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params![
                order.order_id,
                order.client_order_id,
                order.exchange,
                order.symbol,
                order.side,
                order.order_type,
                order.quantity,
                order.price,
                order.status,
                order.correlation_id,
                order.created_at,
            ]
        )?;

        Ok(order.clone())
    }

    #[instrument(skip(self))]
    pub async fn find_by_id(&self, order_id: Uuid) -> Result<Option<Order>> {
        let reader = self.pool.get_reader().await?;

        let mut stmt = reader.conn.prepare(
            "SELECT * FROM orders WHERE order_id = ?"
        )?;

        let order = stmt.query_row(params![order_id], |row| {
            Ok(Order {
                order_id: row.get("order_id")?,
                client_order_id: row.get("client_order_id")?,
                exchange: row.get("exchange")?,
                symbol: row.get("symbol")?,
                side: row.get("side")?,
                order_type: row.get("order_type")?,
                quantity: row.get("quantity")?,
                price: row.get("price")?,
                status: row.get("status")?,
                correlation_id: row.get("correlation_id")?,
                created_at: row.get("created_at")?,
            })
        }).optional()?;

        Ok(order)
    }

    #[instrument(skip(self))]
    pub async fn find_by_symbol(
        &self,
        symbol: &str,
        limit: usize
    ) -> Result<Vec<Order>> {
        let reader = self.pool.get_reader().await?;

        let mut stmt = reader.conn.prepare(
            "SELECT * FROM orders
             WHERE symbol = ?
             ORDER BY created_at DESC
             LIMIT ?"
        )?;

        let orders: Vec<Order> = stmt.query_map(params![symbol, limit], |row| {
            Ok(Order {
                order_id: row.get("order_id")?,
                client_order_id: row.get("client_order_id")?,
                exchange: row.get("exchange")?,
                symbol: row.get("symbol")?,
                side: row.get("side")?,
                order_type: row.get("order_type")?,
                quantity: row.get("quantity")?,
                price: row.get("price")?,
                status: row.get("status")?,
                correlation_id: row.get("correlation_id")?,
                created_at: row.get("created_at")?,
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;

        Ok(orders)
    }

    #[instrument(skip(self))]
    pub async fn update_status(
        &self,
        order_id: Uuid,
        new_status: &str
    ) -> Result<()> {
        let writer = self.pool.get_writer().await;

        let rows = writer.conn.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP
             WHERE order_id = ?",
            params![new_status, order_id]
        )?;

        if rows == 0 {
            return Err(DatabaseError::NotFound {
                entity_type: "Order".to_string(),
                id: order_id.to_string(),
            });
        }

        Ok(())
    }
}
```

---

## 5. Migration System

### 5.1 migrations/runner.rs

```rust
// rust/database/src/migrations/runner.rs

use crate::{DuckDBConnectionPool, Result, DatabaseError};
use std::sync::Arc;
use tracing::{info, warn};

pub struct MigrationRunner {
    pool: Arc<DuckDBConnectionPool>,
    migrations: Vec<Box<dyn Migration>>,
}

#[async_trait]
pub trait Migration: Send + Sync {
    fn version(&self) -> &str;
    fn description(&self) -> &str;
    async fn up(&self, conn: &Connection) -> Result<()>;
    async fn down(&self, conn: &Connection) -> Result<()>;
}

impl MigrationRunner {
    pub fn new(pool: Arc<DuckDBConnectionPool>) -> Self {
        Self {
            pool,
            migrations: vec![
                Box::new(V001InitialSchema),
                Box::new(V002AddMetrics),
                Box::new(V003AddIndexes),
            ],
        }
    }

    pub async fn run_all(&self) -> Result<()> {
        info!("Running database migrations...");

        let writer = self.pool.get_writer().await;

        // Create migrations table
        writer.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )",
            []
        )?;

        for migration in &self.migrations {
            let version = migration.version();

            // Check if already applied
            let applied: Option<String> = writer.conn.query_row(
                "SELECT version FROM schema_migrations WHERE version = ?",
                params![version],
                |row| row.get(0)
            ).optional()?;

            if applied.is_some() {
                info!("Migration {} already applied, skipping", version);
                continue;
            }

            info!("Applying migration {}: {}", version, migration.description());

            match migration.up(&writer.conn).await {
                Ok(_) => {
                    writer.conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (?)",
                        params![version]
                    )?;
                    info!("Migration {} completed successfully", version);
                }
                Err(e) => {
                    return Err(DatabaseError::MigrationFailed {
                        version: version.to_string(),
                        message: e.to_string(),
                    });
                }
            }
        }

        info!("All migrations completed");
        Ok(())
    }
}
```

---

## 6. Testing Module

### 6.1 testing/fixtures.rs

```rust
// rust/database/src/testing/fixtures.rs

use crate::models::*;
use uuid::Uuid;
use chrono::Utc;
use rust_decimal::Decimal;

pub fn create_test_order(symbol: &str) -> Order {
    Order {
        order_id: Uuid::new_v4(),
        client_order_id: format!("test-{}", Uuid::new_v4()),
        exchange: "alpaca".to_string(),
        symbol: symbol.to_string(),
        side: "buy".to_string(),
        order_type: "limit".to_string(),
        quantity: Decimal::from(100),
        price: Some(Decimal::from(150)),
        status: "pending".to_string(),
        correlation_id: Uuid::new_v4(),
        created_at: Utc::now(),
    }
}

pub fn create_test_pool() -> Arc<DuckDBConnectionPool> {
    let config = DatabaseConfig {
        database_path: PathBuf::from(":memory:"),
        ..Default::default()
    };

    let pool = DuckDBConnectionPool::new(config)
        .await
        .expect("Failed to create test pool");

    // Run migrations
    let runner = MigrationRunner::new(pool.clone());
    runner.run_all().await.expect("Failed to run migrations");

    pool
}
```

---

## Summary

This module structure provides:

1. **Clear Separation of Concerns**: Each module has a specific responsibility
2. **Testability**: Mock implementations and fixtures for testing
3. **Observability**: Built-in metrics and tracing
4. **Extensibility**: Easy to add new repositories and models
5. **Type Safety**: Strong typing throughout with Rust's type system

**Integration with Existing Crates**:
- `market-data`: Uses `MarketDataRepository`
- `execution-engine`: Uses `OrderRepository` and `TradeRepository`
- `risk-manager`: Uses `PositionRepository` and `PortfolioRepository`
- `common`: Shared types and utilities

**Created by**: Hive Mind Architecture Agent
**Ready for**: Coder Agent implementation
