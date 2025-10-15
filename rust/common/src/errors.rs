use thiserror::Error;

pub type Result<T> = std::result::Result<T, TradingError>;

#[derive(Error, Debug)]
pub enum TradingError {
    #[error("Market data error: {0}")]
    MarketData(String),

    #[error("WebSocket error: {0}")]
    WebSocket(String),

    #[error("Order validation error: {0}")]
    OrderValidation(String),

    #[error("Risk check failed: {0}")]
    RiskCheck(String),

    #[error("Execution error: {0}")]
    Execution(String),

    #[error("Messaging error: {0}")]
    Messaging(String),

    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Unknown error: {0}")]
    Unknown(String),
}
