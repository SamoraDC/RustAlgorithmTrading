//! Database connection management with pooling

use crate::error::{DatabaseError, Result};
use crate::models::*;
use crate::query::{QueryBuilder, TimeInterval};
use crate::schema::Schema;

use chrono::{DateTime, Utc};
use duckdb::{Config, Connection};
use r2d2::{Pool, PooledConnection};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

/// Type alias for connection pool
pub type ConnectionPool = Pool<ConnectionManager>;

/// Connection manager for r2d2 pooling
pub struct ConnectionManager {
    path: PathBuf,
}

impl ConnectionManager {
    /// Create a new connection manager
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
        }
    }
}

impl r2d2::ManageConnection for ConnectionManager {
    type Connection = Connection;
    type Error = duckdb::Error;

    fn connect(&self) -> std::result::Result<Self::Connection, Self::Error> {
        let config = Config::default()
            .access_mode(duckdb::AccessMode::ReadWrite)?
            .enable_object_cache(true)?;

        Connection::open_with_flags(&self.path, config)
    }

    fn is_valid(&self, conn: &mut Self::Connection) -> std::result::Result<(), Self::Error> {
        conn.execute_batch("SELECT 1")?;
        Ok(())
    }

    fn has_broken(&self, _conn: &mut Self::Connection) -> bool {
        false
    }
}

/// High-level database manager with connection pooling
pub struct DatabaseManager {
    pool: Arc<ConnectionPool>,
    path: PathBuf,
}

impl DatabaseManager {
    /// Create a new database manager
    ///
    /// # Example
    ///
    /// ```no_run
    /// use database::DatabaseManager;
    ///
    /// # async fn example() -> anyhow::Result<()> {
    /// let db = DatabaseManager::new("metrics.duckdb").await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn new<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        let manager = ConnectionManager::new(&path);

        let pool = Pool::builder()
            .max_size(10) // Maximum 10 connections
            .min_idle(Some(2)) // Keep at least 2 idle connections
            .build(manager)?;

        Ok(Self {
            pool: Arc::new(pool),
            path,
        })
    }

    /// Initialize database schema
    ///
    /// This creates all necessary tables and indexes if they don't exist.
    pub async fn initialize(&self) -> Result<()> {
        let start = Instant::now();
        tracing::info!("Initializing database schema...");

        let conn = self.get_connection()?;
        Schema::create_all(&conn)?;

        let elapsed = start.elapsed();
        tracing::info!("Database initialized in {:?}", elapsed);
        metrics::counter!("database_initialized_total").increment(1);

        Ok(())
    }

    /// Get a pooled connection
    pub fn get_connection(&self) -> Result<PooledConnection<ConnectionManager>> {
        self.pool.get().map_err(DatabaseError::from)
    }

    /// Insert a single metric
    ///
    /// # Example
    ///
    /// ```no_run
    /// use database::{DatabaseManager, MetricRecord};
    /// use chrono::Utc;
    ///
    /// # async fn example(db: &DatabaseManager) -> anyhow::Result<()> {
    /// let metric = MetricRecord {
    ///     timestamp: Utc::now(),
    ///     metric_name: "price".to_string(),
    ///     value: 50000.0,
    ///     symbol: Some("BTC/USD".to_string()),
    ///     labels: None,
    /// };
    /// db.insert_metric(&metric).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn insert_metric(&self, metric: &MetricRecord) -> Result<()> {
        let conn = self.get_connection()?;
        let labels_json = metric
            .labels
            .as_ref()
            .map(|l| serde_json::to_string(l))
            .transpose()?;

        conn.execute(
            "INSERT INTO trading_metrics (timestamp, metric_name, value, symbol, labels) VALUES (?, ?, ?, ?, ?)",
            duckdb::params![
                metric.timestamp.to_rfc3339(),
                &metric.metric_name,
                metric.value,
                &metric.symbol,
                labels_json
            ],
        )?;

        metrics::counter!("database_metrics_inserted_total").increment(1);
        Ok(())
    }

    /// Insert multiple metrics in a batch (high performance)
    ///
    /// # Example
    ///
    /// ```no_run
    /// use database::{DatabaseManager, MetricRecord};
    /// use chrono::Utc;
    ///
    /// # async fn example(db: &DatabaseManager) -> anyhow::Result<()> {
    /// let metrics: Vec<MetricRecord> = (0..1000)
    ///     .map(|i| MetricRecord::new("price", 50000.0 + i as f64))
    ///     .collect();
    /// db.insert_metrics(&metrics).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn insert_metrics(&self, metrics: &[MetricRecord]) -> Result<()> {
        if metrics.is_empty() {
            return Ok(());
        }

        let start = Instant::now();
        let mut conn = self.get_connection()?;

        // Use a transaction for better performance
        let tx = conn.transaction()?;

        for metric in metrics {
            let labels_json = metric
                .labels
                .as_ref()
                .map(|l| serde_json::to_string(l))
                .transpose()?;

            tx.execute(
                "INSERT INTO trading_metrics (timestamp, metric_name, value, symbol, labels) VALUES (?, ?, ?, ?, ?)",
                duckdb::params![
                    metric.timestamp.to_rfc3339(),
                    &metric.metric_name,
                    metric.value,
                    &metric.symbol,
                    labels_json
                ],
            )?;
        }

        tx.commit()?;

        let elapsed = start.elapsed();
        metrics::counter!("database_metrics_inserted_total").increment(metrics.len() as u64);
        metrics::histogram!("database_batch_insert_duration_ms").record(elapsed.as_millis() as f64);

        tracing::debug!("Inserted {} metrics in {:?}", metrics.len(), elapsed);
        Ok(())
    }

    /// Get metrics with filtering
    ///
    /// # Arguments
    ///
    /// * `metric_name` - Name of the metric to retrieve
    /// * `symbol` - Optional symbol filter
    /// * `start_time` - Optional start time filter
    /// * `limit` - Maximum number of records to return
    pub async fn get_metrics(
        &self,
        metric_name: &str,
        symbol: Option<&str>,
        start_time: Option<DateTime<Utc>>,
        limit: i64,
    ) -> Result<Vec<MetricRecord>> {
        let conn = self.get_connection()?;
        let query = QueryBuilder::new()
            .select_metrics(metric_name, symbol, start_time, limit);

        let mut stmt = conn.prepare(&query)?;
        let rows = stmt.query_map([], |row| {
            let timestamp_str: String = row.get(0)?;
            let timestamp = timestamp_str
                .parse()
                .map_err(|e| duckdb::Error::FromSqlConversionFailure(
                    0,
                    duckdb::types::Type::Text,
                    Box::new(std::io::Error::new(std::io::ErrorKind::InvalidData, format!("Invalid timestamp format: {}", e)))
                ))?;

            Ok(MetricRecord {
                timestamp,
                metric_name: row.get(1)?,
                value: row.get(2)?,
                symbol: row.get(3)?,
                labels: row
                    .get::<_, Option<String>>(4)?
                    .and_then(|s| serde_json::from_str(&s).ok()),
            })
        })?;

        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(DatabaseError::from)
    }

    /// Insert a candle record
    pub async fn insert_candle(&self, candle: &CandleRecord) -> Result<()> {
        let conn = self.get_connection()?;

        conn.execute(
            "INSERT INTO trading_candles (timestamp, symbol, open, high, low, close, volume, trade_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            duckdb::params![
                candle.timestamp.to_rfc3339(),
                &candle.symbol,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
                candle.trade_count
            ],
        )?;

        metrics::counter!("database_candles_inserted_total").increment(1);
        Ok(())
    }

    /// Get candles with filtering
    pub async fn get_candles(
        &self,
        symbol: &str,
        interval: TimeInterval,
        start_time: Option<DateTime<Utc>>,
        limit: i64,
    ) -> Result<Vec<CandleRecord>> {
        let conn = self.get_connection()?;
        let query = QueryBuilder::new().select_candles(symbol, interval, start_time, limit);

        let mut stmt = conn.prepare(&query)?;
        let rows = stmt.query_map([], |row| {
            let timestamp_str: String = row.get(0)?;
            let timestamp = timestamp_str
                .parse()
                .map_err(|e| duckdb::Error::FromSqlConversionFailure(
                    0,
                    duckdb::types::Type::Text,
                    Box::new(std::io::Error::new(std::io::ErrorKind::InvalidData, format!("Invalid timestamp format in candle: {}", e)))
                ))?;

            Ok(CandleRecord {
                timestamp,
                symbol: row.get(1)?,
                open: row.get(2)?,
                high: row.get(3)?,
                low: row.get(4)?,
                close: row.get(5)?,
                volume: row.get(6)?,
                trade_count: row.get(7)?,
            })
        })?;

        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(DatabaseError::from)
    }

    /// Get aggregated metrics
    pub async fn get_aggregated_metrics(
        &self,
        metric_name: &str,
        interval: TimeInterval,
        start_time: Option<DateTime<Utc>>,
        aggregation: &str,
    ) -> Result<Vec<AggregatedMetric>> {
        let conn = self.get_connection()?;
        let query = QueryBuilder::new().aggregate_metrics(metric_name, interval, start_time, aggregation);

        let mut stmt = conn.prepare(&query)?;
        let rows = stmt.query_map([], |row| {
            let time_bucket_str: String = row.get(0)?;
            let time_bucket = time_bucket_str
                .parse()
                .map_err(|e| duckdb::Error::FromSqlConversionFailure(
                    0,
                    duckdb::types::Type::Text,
                    Box::new(std::io::Error::new(std::io::ErrorKind::InvalidData, format!("Invalid time_bucket format in aggregated metric: {}", e)))
                ))?;

            Ok(AggregatedMetric {
                time_bucket,
                metric_name: row.get(1)?,
                symbol: row.get(2)?,
                value: row.get(3)?,
                count: row.get(4)?,
            })
        })?;

        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(DatabaseError::from)
    }

    /// Log a system event
    pub async fn log_event(&self, event: &SystemEvent) -> Result<()> {
        let conn = self.get_connection()?;
        let details_json = event
            .details
            .as_ref()
            .map(|d| serde_json::to_string(d))
            .transpose()?;

        conn.execute(
            "INSERT INTO system_events (timestamp, event_type, severity, message, details) VALUES (?, ?, ?, ?, ?)",
            duckdb::params![
                event.timestamp.to_rfc3339(),
                &event.event_type,
                &event.severity,
                &event.message,
                details_json
            ],
        )?;

        metrics::counter!("database_events_logged_total").increment(1);
        Ok(())
    }

    /// Get database statistics
    pub async fn get_table_stats(&self) -> Result<Vec<TableStats>> {
        let conn = self.get_connection()?;
        let query = QueryBuilder::new().table_statistics();

        let mut stmt = conn.prepare(&query)?;
        let rows = stmt.query_map([], |row| {
            Ok(TableStats {
                table_name: row.get(0)?,
                row_count: row.get(1)?,
                min_timestamp: row.get::<_, Option<String>>(2)?.and_then(|s| s.parse().ok()),
                max_timestamp: row.get::<_, Option<String>>(3)?.and_then(|s| s.parse().ok()),
                size_bytes: row.get(4)?,
            })
        })?;

        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(DatabaseError::from)
    }

    /// Optimize database (run VACUUM and CHECKPOINT)
    pub async fn optimize(&self) -> Result<()> {
        let start = Instant::now();
        tracing::info!("Optimizing database...");

        let conn = self.get_connection()?;
        conn.execute_batch("VACUUM; CHECKPOINT;")?;

        let elapsed = start.elapsed();
        tracing::info!("Database optimized in {:?}", elapsed);
        metrics::counter!("database_optimizations_total").increment(1);

        Ok(())
    }

    /// Get database file path
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Get connection pool statistics
    pub fn pool_stats(&self) -> r2d2::State {
        self.pool.state()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[tokio::test]
    async fn test_database_initialization() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        assert!(db.initialize().await.is_ok());
    }

    #[tokio::test]
    async fn test_metric_insertion() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        let metric = MetricRecord::new("test_metric", 42.5);
        assert!(db.insert_metric(&metric).await.is_ok());
    }

    #[tokio::test]
    async fn test_batch_insertion() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        let metrics: Vec<MetricRecord> = (0..100)
            .map(|i| MetricRecord::new("test", i as f64))
            .collect();

        assert!(db.insert_metrics(&metrics).await.is_ok());

        let retrieved = db.get_metrics("test", None, None, 1000).await.unwrap();
        assert_eq!(retrieved.len(), 100);
    }
}
