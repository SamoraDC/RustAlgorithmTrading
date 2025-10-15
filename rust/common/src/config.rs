use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Configuration for market data component
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketDataConfig {
    pub exchange: String,
    pub symbols: Vec<String>,
    pub websocket_url: String,
    pub reconnect_delay_ms: u64,
    pub zmq_publish_address: String,
}

/// Configuration for risk management
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskConfig {
    pub max_position_size: f64,
    pub max_notional_exposure: f64,
    pub max_open_positions: usize,
    pub stop_loss_percent: f64,
    pub trailing_stop_percent: f64,
    pub enable_circuit_breaker: bool,
    pub max_loss_threshold: f64,
}

/// Configuration for execution engine
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionConfig {
    pub exchange_api_url: String,
    pub api_key: Option<String>,
    pub api_secret: Option<String>,
    pub rate_limit_per_second: u32,
    pub retry_attempts: u32,
    pub retry_delay_ms: u64,
    pub paper_trading: bool,
}

/// Configuration for signal bridge
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalConfig {
    pub model_path: String,
    pub features: Vec<String>,
    pub update_interval_ms: u64,
    pub zmq_subscribe_address: String,
    pub zmq_publish_address: String,
}

/// Top-level system configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemConfig {
    pub market_data: MarketDataConfig,
    pub risk: RiskConfig,
    pub execution: ExecutionConfig,
    pub signal: SignalConfig,
    pub metadata: HashMap<String, String>,
}

impl SystemConfig {
    pub fn from_file(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let config = serde_json::from_str(&content)?;
        Ok(config)
    }

    pub fn to_file(&self, path: &str) -> anyhow::Result<()> {
        let content = serde_json::to_string_pretty(self)?;
        std::fs::write(path, content)?;
        Ok(())
    }
}
