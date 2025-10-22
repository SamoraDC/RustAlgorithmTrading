//! Database schema definitions and migrations

use crate::error::{DatabaseError, Result};
use duckdb::Connection;

/// Database schema management
pub struct Schema;

impl Schema {
    /// Create all tables and indexes
    pub fn create_all(conn: &Connection) -> Result<()> {
        Self::create_metrics_table(conn)?;
        Self::create_candles_table(conn)?;
        Self::create_events_table(conn)?;
        Self::create_indexes(conn)?;
        Ok(())
    }

    /// Create trading_metrics table
    ///
    /// Stores time-series metrics for market data, strategy performance, execution, and system metrics.
    fn create_metrics_table(conn: &Connection) -> Result<()> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS trading_metrics (
                timestamp TIMESTAMP NOT NULL,
                metric_name VARCHAR NOT NULL,
                value DOUBLE NOT NULL,
                symbol VARCHAR,
                labels JSON,
                PRIMARY KEY (timestamp, metric_name, symbol)
            )",
        )?;

        tracing::debug!("Created trading_metrics table");
        Ok(())
    }

    /// Create trading_candles table
    ///
    /// Stores OHLCV candle data for various timeframes.
    fn create_candles_table(conn: &Connection) -> Result<()> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS trading_candles (
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                trade_count INTEGER,
                PRIMARY KEY (timestamp, symbol)
            )",
        )?;

        tracing::debug!("Created trading_candles table");
        Ok(())
    }

    /// Create system_events table
    ///
    /// Stores system events, alerts, and logs.
    fn create_events_table(conn: &Connection) -> Result<()> {
        conn.execute_batch(
            "CREATE SEQUENCE IF NOT EXISTS system_events_seq;
            CREATE TABLE IF NOT EXISTS system_events (
                id BIGINT PRIMARY KEY DEFAULT nextval('system_events_seq'),
                timestamp TIMESTAMP NOT NULL,
                event_type VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                message TEXT NOT NULL,
                details JSON
            )",
        )?;

        tracing::debug!("Created system_events table");
        Ok(())
    }

    /// Create indexes for performance optimization
    fn create_indexes(conn: &Connection) -> Result<()> {
        // Metrics indexes
        conn.execute_batch(
            "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON trading_metrics(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_metrics_name_symbol ON trading_metrics(metric_name, symbol);
            CREATE INDEX IF NOT EXISTS idx_metrics_symbol ON trading_metrics(symbol) WHERE symbol IS NOT NULL;",
        )?;

        // Candles indexes
        conn.execute_batch(
            "CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON trading_candles(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON trading_candles(symbol, timestamp DESC);",
        )?;

        // Events indexes
        conn.execute_batch(
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_events_severity ON system_events(severity);
            CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type);",
        )?;

        tracing::debug!("Created database indexes");
        Ok(())
    }

    /// Drop all tables (use with caution!)
    #[allow(dead_code)]
    pub fn drop_all(conn: &Connection) -> Result<()> {
        conn.execute_batch(
            "DROP TABLE IF EXISTS trading_metrics CASCADE;
            DROP TABLE IF EXISTS trading_candles CASCADE;
            DROP TABLE IF EXISTS system_events CASCADE;
            DROP SEQUENCE IF EXISTS system_events_seq CASCADE;",
        )?;

        tracing::warn!("Dropped all database tables");
        Ok(())
    }

    /// Verify schema integrity
    pub fn verify(conn: &Connection) -> Result<()> {
        // Check if all tables exist
        let tables = vec!["trading_metrics", "trading_candles", "system_events"];

        for table in tables {
            let mut stmt = conn.prepare(&format!(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{}'",
                table
            ))?;

            let count: i64 = stmt.query_row([], |row| row.get(0))?;

            if count == 0 {
                return Err(DatabaseError::schema(format!("Table {} not found", table)));
            }
        }

        tracing::debug!("Schema verification passed");
        Ok(())
    }

    /// Get schema version
    pub fn version() -> &'static str {
        "1.0.0"
    }

    /// Get schema description
    pub fn description() -> &'static str {
        "DuckDB schema for trading system observability and analytics"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use duckdb::Connection;

    #[test]
    fn test_create_all_tables() {
        let conn = Connection::open_in_memory().unwrap();
        assert!(Schema::create_all(&conn).is_ok());
    }

    #[test]
    fn test_schema_verification() {
        let conn = Connection::open_in_memory().unwrap();
        Schema::create_all(&conn).unwrap();
        assert!(Schema::verify(&conn).is_ok());
    }

    #[test]
    fn test_drop_and_recreate() {
        let conn = Connection::open_in_memory().unwrap();
        Schema::create_all(&conn).unwrap();
        Schema::drop_all(&conn).unwrap();
        Schema::create_all(&conn).unwrap();
        assert!(Schema::verify(&conn).is_ok());
    }

    #[test]
    fn test_schema_version() {
        assert_eq!(Schema::version(), "1.0.0");
    }
}
