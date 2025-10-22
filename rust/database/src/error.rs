//! Error types for database operations

use thiserror::Error;

/// Database operation result type
pub type Result<T> = std::result::Result<T, DatabaseError>;

/// Database errors
#[derive(Error, Debug)]
pub enum DatabaseError {
    /// DuckDB connection error
    #[error("DuckDB connection error: {0}")]
    Connection(#[from] duckdb::Error),

    /// Pool error
    #[error("Connection pool error: {0}")]
    Pool(#[from] r2d2::Error),

    /// Serialization error
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    /// Query error
    #[error("Query error: {0}")]
    Query(String),

    /// Schema error
    #[error("Schema error: {0}")]
    Schema(String),

    /// Migration error
    #[error("Migration error: {0}")]
    Migration(String),

    /// Invalid parameter
    #[error("Invalid parameter: {0}")]
    InvalidParameter(String),

    /// Not found
    #[error("Record not found: {0}")]
    NotFound(String),

    /// IO error
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// Generic error
    #[error("Database error: {0}")]
    Other(String),
}

impl DatabaseError {
    /// Create a query error
    pub fn query<S: Into<String>>(msg: S) -> Self {
        Self::Query(msg.into())
    }

    /// Create a schema error
    pub fn schema<S: Into<String>>(msg: S) -> Self {
        Self::Schema(msg.into())
    }

    /// Create a migration error
    pub fn migration<S: Into<String>>(msg: S) -> Self {
        Self::Migration(msg.into())
    }

    /// Create an invalid parameter error
    pub fn invalid_param<S: Into<String>>(msg: S) -> Self {
        Self::InvalidParameter(msg.into())
    }

    /// Create a not found error
    pub fn not_found<S: Into<String>>(msg: S) -> Self {
        Self::NotFound(msg.into())
    }
}

// Note: No need for From<DatabaseError> for anyhow::Error
// anyhow already provides a blanket implementation for all error types
// that implement std::error::Error, which DatabaseError does via #[derive(Error)]
