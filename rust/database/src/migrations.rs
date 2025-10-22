//! Database migration tools for schema versioning and data migration

use crate::error::{DatabaseError, Result};
use crate::DatabaseManager;
use chrono::{DateTime, Utc};
use duckdb::Connection;
use std::path::Path;

/// Migration record
#[derive(Debug, Clone)]
pub struct Migration {
    /// Migration version (e.g., "001", "002")
    pub version: String,
    /// Migration name
    pub name: String,
    /// SQL to apply migration
    pub up_sql: String,
    /// SQL to rollback migration (optional)
    pub down_sql: Option<String>,
}

/// Migration manager
pub struct MigrationManager {
    db: DatabaseManager,
}

impl MigrationManager {
    /// Create a new migration manager
    pub fn new(db: DatabaseManager) -> Self {
        Self { db }
    }

    /// Initialize migration tracking table
    pub async fn init_migrations_table(&self) -> Result<()> {
        let conn = self.db.get_connection()?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                applied_at TIMESTAMP NOT NULL,
                checksum VARCHAR
            )",
        )?;

        tracing::info!("Migration tracking table initialized");
        Ok(())
    }

    /// Apply a migration
    pub async fn apply(&self, migration: &Migration) -> Result<()> {
        let conn = self.db.get_connection()?;

        // Check if already applied
        if self.is_applied(&migration.version).await? {
            tracing::info!("Migration {} already applied, skipping", migration.version);
            return Ok(());
        }

        tracing::info!("Applying migration {}: {}", migration.version, migration.name);

        // Apply migration in a transaction
        let tx = conn.transaction()?;
        tx.execute_batch(&migration.up_sql)?;

        // Record migration
        tx.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            duckdb::params![
                &migration.version,
                &migration.name,
                Utc::now().to_rfc3339()
            ],
        )?;

        tx.commit()?;

        tracing::info!("Migration {} applied successfully", migration.version);
        Ok(())
    }

    /// Rollback a migration
    pub async fn rollback(&self, migration: &Migration) -> Result<()> {
        let down_sql = migration
            .down_sql
            .as_ref()
            .ok_or_else(|| DatabaseError::migration("No rollback SQL provided"))?;

        let conn = self.db.get_connection()?;

        tracing::info!("Rolling back migration {}", migration.version);

        let tx = conn.transaction()?;
        tx.execute_batch(down_sql)?;

        // Remove migration record
        tx.execute(
            "DELETE FROM schema_migrations WHERE version = ?",
            duckdb::params![&migration.version],
        )?;

        tx.commit()?;

        tracing::info!("Migration {} rolled back successfully", migration.version);
        Ok(())
    }

    /// Check if a migration has been applied
    pub async fn is_applied(&self, version: &str) -> Result<bool> {
        let conn = self.db.get_connection()?;
        let mut stmt = conn.prepare("SELECT COUNT(*) FROM schema_migrations WHERE version = ?")?;

        let count: i64 = stmt.query_row(duckdb::params![version], |row| row.get(0))?;

        Ok(count > 0)
    }

    /// Get all applied migrations
    pub async fn get_applied_migrations(&self) -> Result<Vec<(String, String, DateTime<Utc>)>> {
        let conn = self.db.get_connection()?;
        let mut stmt = conn.prepare("SELECT version, name, applied_at FROM schema_migrations ORDER BY version")?;

        let rows = stmt.query_map([], |row| {
            let timestamp_str: String = row.get(2)?;
            let timestamp = timestamp_str
                .parse()
                .map_err(|e| duckdb::Error::InvalidParameterType(
                    2,
                    format!("Invalid timestamp format in migration record: {}", e)
                ))?;
            Ok((
                row.get(0)?,
                row.get(1)?,
                timestamp,
            ))
        })?;

        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(DatabaseError::from)
    }
}

/// TimescaleDB to DuckDB migration helper
pub struct TimescaleMigrator;

impl TimescaleMigrator {
    /// Migrate data from PostgreSQL/TimescaleDB export to DuckDB
    ///
    /// # Arguments
    ///
    /// * `csv_path` - Path to CSV export from PostgreSQL
    /// * `target_table` - Target DuckDB table name
    /// * `conn` - DuckDB connection
    pub fn migrate_from_csv<P: AsRef<Path>>(
        csv_path: P,
        target_table: &str,
        conn: &Connection,
    ) -> Result<usize> {
        let path_str = csv_path.as_ref().to_str().ok_or_else(|| {
            DatabaseError::migration("Invalid path encoding")
        })?;

        tracing::info!("Migrating data from {} to {}", path_str, target_table);

        // Use DuckDB's native CSV reader (very fast)
        let query = format!(
            "INSERT INTO {} SELECT * FROM read_csv_auto('{}')",
            target_table, path_str
        );

        conn.execute(&query, [])?;

        // Get count
        let count: usize = conn.query_row(
            &format!("SELECT COUNT(*) FROM {}", target_table),
            [],
            |row| row.get(0),
        )?;

        tracing::info!("Migrated {} records to {}", count, target_table);
        Ok(count)
    }

    /// Migrate from Parquet files (high performance)
    pub fn migrate_from_parquet<P: AsRef<Path>>(
        parquet_path: P,
        target_table: &str,
        conn: &Connection,
    ) -> Result<usize> {
        let path_str = parquet_path.as_ref().to_str().ok_or_else(|| {
            DatabaseError::migration("Invalid path encoding")
        })?;

        tracing::info!("Migrating data from {} to {}", path_str, target_table);

        let query = format!(
            "INSERT INTO {} SELECT * FROM read_parquet('{}')",
            target_table, path_str
        );

        conn.execute(&query, [])?;

        let count: usize = conn.query_row(
            &format!("SELECT COUNT(*) FROM {}", target_table),
            [],
            |row| row.get(0),
        )?;

        tracing::info!("Migrated {} records from Parquet", count);
        Ok(count)
    }
}

/// Built-in migrations
pub fn get_builtin_migrations() -> Vec<Migration> {
    vec![
        Migration {
            version: "001".to_string(),
            name: "Initial schema".to_string(),
            up_sql: r#"
                CREATE TABLE IF NOT EXISTS trading_metrics (
                    timestamp TIMESTAMP NOT NULL,
                    metric_name VARCHAR NOT NULL,
                    value DOUBLE NOT NULL,
                    symbol VARCHAR,
                    labels JSON,
                    PRIMARY KEY (timestamp, metric_name, symbol)
                );

                CREATE TABLE IF NOT EXISTS trading_candles (
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR NOT NULL,
                    open DOUBLE NOT NULL,
                    high DOUBLE NOT NULL,
                    low DOUBLE NOT NULL,
                    close DOUBLE NOT NULL,
                    volume BIGINT NOT NULL,
                    trade_count INTEGER,
                    PRIMARY KEY (timestamp, symbol)
                );

                CREATE SEQUENCE IF NOT EXISTS system_events_seq;
                CREATE TABLE IF NOT EXISTS system_events (
                    id BIGINT PRIMARY KEY DEFAULT nextval('system_events_seq'),
                    timestamp TIMESTAMP NOT NULL,
                    event_type VARCHAR NOT NULL,
                    severity VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    details JSON
                );
            "#.to_string(),
            down_sql: Some(r#"
                DROP TABLE IF EXISTS trading_metrics CASCADE;
                DROP TABLE IF EXISTS trading_candles CASCADE;
                DROP TABLE IF EXISTS system_events CASCADE;
                DROP SEQUENCE IF EXISTS system_events_seq CASCADE;
            "#.to_string()),
        },
        Migration {
            version: "002".to_string(),
            name: "Add performance indexes".to_string(),
            up_sql: r#"
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON trading_metrics(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_metrics_name_symbol ON trading_metrics(metric_name, symbol);
                CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON trading_candles(symbol, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp DESC);
            "#.to_string(),
            down_sql: Some(r#"
                DROP INDEX IF EXISTS idx_metrics_timestamp;
                DROP INDEX IF EXISTS idx_metrics_name_symbol;
                DROP INDEX IF EXISTS idx_candles_symbol_time;
                DROP INDEX IF EXISTS idx_events_timestamp;
            "#.to_string()),
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[tokio::test]
    async fn test_migration_workflow() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();

        let manager = MigrationManager::new(db);
        manager.init_migrations_table().await.unwrap();

        let migrations = get_builtin_migrations();
        for migration in &migrations {
            manager.apply(migration).await.unwrap();
            assert!(manager.is_applied(&migration.version).await.unwrap());
        }

        let applied = manager.get_applied_migrations().await.unwrap();
        assert_eq!(applied.len(), migrations.len());
    }

    #[tokio::test]
    async fn test_rollback() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();

        let manager = MigrationManager::new(db);
        manager.init_migrations_table().await.unwrap();

        let migration = &get_builtin_migrations()[0];
        manager.apply(migration).await.unwrap();
        assert!(manager.is_applied(&migration.version).await.unwrap());

        manager.rollback(migration).await.unwrap();
        assert!(!manager.is_applied(&migration.version).await.unwrap());
    }
}
