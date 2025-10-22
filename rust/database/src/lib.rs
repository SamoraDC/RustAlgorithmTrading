//! DuckDB Database Layer for Trading System
//!
//! This module provides a high-performance, type-safe database layer using DuckDB
//! for time-series analytics and observability data storage.
//!
//! # Features
//!
//! - **Connection Pooling**: Efficient connection management with r2d2
//! - **Type-Safe Queries**: Compile-time query validation
//! - **Time-Series Optimized**: Columnar storage for fast aggregations
//! - **Migration Support**: Schema versioning and upgrades
//! - **Observability**: Metrics collection and performance tracking
//!
//! # Example
//!
//! ```no_run
//! use database::{DatabaseManager, MetricRecord};
//! use chrono::Utc;
//!
//! # async fn example() -> anyhow::Result<()> {
//! // Initialize database
//! let db = DatabaseManager::new("trading_metrics.duckdb").await?;
//! db.initialize().await?;
//!
//! // Insert metric
//! let metric = MetricRecord {
//!     timestamp: Utc::now(),
//!     metric_name: "order_latency_ms".to_string(),
//!     value: 42.5,
//!     symbol: Some("BTC/USD".to_string()),
//!     labels: None,
//! };
//! db.insert_metric(&metric).await?;
//!
//! // Query metrics
//! let metrics = db.get_metrics("order_latency_ms", None, None, 100).await?;
//! # Ok(())
//! # }
//! ```

pub mod connection;
pub mod error;
pub mod models;
pub mod query;
pub mod schema;

#[cfg(feature = "migration-tools")]
pub mod migrations;

// Re-exports for convenience
pub use connection::{ConnectionPool, DatabaseManager};
pub use error::{DatabaseError, Result};
pub use models::*;
pub use query::{QueryBuilder, TimeInterval};
pub use schema::Schema;

#[cfg(test)]
mod tests;
