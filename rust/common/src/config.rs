use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::errors::{Result, TradingError};

/// Configuration for market data component
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketDataConfig {
    pub exchange: String,
    pub symbols: Vec<String>,
    pub websocket_url: String,
    pub reconnect_delay_ms: u64,
    pub zmq_publish_address: String,
}

impl MarketDataConfig {
    /// Validate market data configuration
    pub fn validate(&self) -> Result<()> {
        if self.symbols.is_empty() {
            return Err(TradingError::Configuration(
                "symbols list cannot be empty".to_string()
            ));
        }

        if !self.websocket_url.starts_with("ws://") && !self.websocket_url.starts_with("wss://") {
            return Err(TradingError::Configuration(
                format!("invalid websocket URL: {}", self.websocket_url)
            ));
        }

        if !self.zmq_publish_address.starts_with("tcp://") {
            return Err(TradingError::Configuration(
                format!("invalid ZMQ address: {}", self.zmq_publish_address)
            ));
        }

        if self.reconnect_delay_ms < 100 {
            return Err(TradingError::Configuration(
                "reconnect_delay_ms must be at least 100ms".to_string()
            ));
        }

        Ok(())
    }
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

impl RiskConfig {
    /// Validate risk configuration
    pub fn validate(&self) -> Result<()> {
        if self.max_position_size <= 0.0 {
            return Err(TradingError::Configuration(
                "max_position_size must be positive".to_string()
            ));
        }

        if self.max_notional_exposure <= 0.0 {
            return Err(TradingError::Configuration(
                "max_notional_exposure must be positive".to_string()
            ));
        }

        if self.max_open_positions == 0 {
            return Err(TradingError::Configuration(
                "max_open_positions must be at least 1".to_string()
            ));
        }

        if self.stop_loss_percent <= 0.0 || self.stop_loss_percent > 100.0 {
            return Err(TradingError::Configuration(
                "stop_loss_percent must be between 0 and 100".to_string()
            ));
        }

        if self.trailing_stop_percent <= 0.0 || self.trailing_stop_percent > 100.0 {
            return Err(TradingError::Configuration(
                "trailing_stop_percent must be between 0 and 100".to_string()
            ));
        }

        if self.max_loss_threshold <= 0.0 {
            return Err(TradingError::Configuration(
                "max_loss_threshold must be positive".to_string()
            ));
        }

        Ok(())
    }
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
    /// Maximum allowed slippage in basis points (default: 50.0 = 0.5%)
    #[serde(default = "default_max_slippage_bps")]
    pub max_slippage_bps: f64,
}

fn default_max_slippage_bps() -> f64 {
    50.0 // 50 basis points = 0.5%
}

impl ExecutionConfig {
    /// Validate execution configuration
    pub fn validate(&self) -> Result<()> {
        if !self.exchange_api_url.starts_with("http://") && !self.exchange_api_url.starts_with("https://") {
            return Err(TradingError::Configuration(
                format!("invalid API URL: {}", self.exchange_api_url)
            ));
        }

        if self.rate_limit_per_second == 0 {
            return Err(TradingError::Configuration(
                "rate_limit_per_second must be at least 1".to_string()
            ));
        }

        if self.retry_attempts == 0 {
            return Err(TradingError::Configuration(
                "retry_attempts must be at least 1".to_string()
            ));
        }

        if self.retry_delay_ms < 100 {
            return Err(TradingError::Configuration(
                "retry_delay_ms must be at least 100ms".to_string()
            ));
        }

        // Validate max_slippage_bps: must be finite, positive and <= 500 bps (5%)
        if !self.max_slippage_bps.is_finite() {
            return Err(TradingError::Configuration(
                "max_slippage_bps must be a finite number (not NaN or Infinity)".to_string()
            ));
        }

        if self.max_slippage_bps <= 0.0 {
            return Err(TradingError::Configuration(
                "max_slippage_bps must be positive".to_string()
            ));
        }

        if self.max_slippage_bps > 500.0 {
            return Err(TradingError::Configuration(
                format!(
                    "max_slippage_bps ({}) exceeds maximum allowed (500 bps = 5%)",
                    self.max_slippage_bps
                )
            ));
        }

        Ok(())
    }

    /// Load API credentials from environment variables
    pub fn load_credentials(&mut self) -> Result<()> {
        if self.api_key.is_none() {
            let key = std::env::var("ALPACA_API_KEY")
                .map_err(|_| TradingError::Configuration(
                    "ALPACA_API_KEY environment variable not set".to_string()
                ))?;

            // Validate API key is not empty
            if key.trim().is_empty() {
                return Err(TradingError::Configuration(
                    "ALPACA_API_KEY cannot be empty".to_string()
                ));
            }

            self.api_key = Some(key);
        }

        if self.api_secret.is_none() {
            let secret = std::env::var("ALPACA_SECRET_KEY")
                .map_err(|_| TradingError::Configuration(
                    "ALPACA_SECRET_KEY environment variable not set".to_string()
                ))?;

            // Validate API secret is not empty
            if secret.trim().is_empty() {
                return Err(TradingError::Configuration(
                    "ALPACA_SECRET_KEY cannot be empty".to_string()
                ));
            }

            self.api_secret = Some(secret);
        }

        Ok(())
    }

    /// Validate that API credentials are configured and not empty
    pub fn validate_credentials(&self) -> Result<()> {
        if !self.paper_trading {
            // In live trading mode, credentials are required
            let key = self.api_key.as_ref()
                .ok_or_else(|| TradingError::Configuration(
                    "API key not configured for live trading".to_string()
                ))?;

            if key.trim().is_empty() {
                return Err(TradingError::Configuration(
                    "API key cannot be empty".to_string()
                ));
            }

            let secret = self.api_secret.as_ref()
                .ok_or_else(|| TradingError::Configuration(
                    "API secret not configured for live trading".to_string()
                ))?;

            if secret.trim().is_empty() {
                return Err(TradingError::Configuration(
                    "API secret cannot be empty".to_string()
                ));
            }
        }

        Ok(())
    }

    /// Validate that the API URL uses HTTPS protocol
    pub fn validate_https(&self) -> Result<()> {
        if !self.paper_trading {
            // In live trading, enforce HTTPS
            if !self.exchange_api_url.starts_with("https://") {
                return Err(TradingError::Configuration(
                    format!(
                        "API URL must use HTTPS for live trading. Got: {}. \
                        This is required to protect API credentials from interception.",
                        self.exchange_api_url
                    )
                ));
            }
        }

        Ok(())
    }
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

impl SignalConfig {
    /// Validate signal configuration
    pub fn validate(&self) -> Result<()> {
        if self.features.is_empty() {
            return Err(TradingError::Configuration(
                "features list cannot be empty".to_string()
            ));
        }

        if !self.zmq_subscribe_address.starts_with("tcp://") {
            return Err(TradingError::Configuration(
                format!("invalid ZMQ subscribe address: {}", self.zmq_subscribe_address)
            ));
        }

        if !self.zmq_publish_address.starts_with("tcp://") {
            return Err(TradingError::Configuration(
                format!("invalid ZMQ publish address: {}", self.zmq_publish_address)
            ));
        }

        if self.update_interval_ms < 100 {
            return Err(TradingError::Configuration(
                "update_interval_ms must be at least 100ms".to_string()
            ));
        }

        Ok(())
    }
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
    /// Load configuration from file and validate all components
    pub fn from_file(path: &str) -> Result<Self> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| TradingError::Configuration(
                format!("failed to read config file {}: {}", path, e)
            ))?;

        let mut config: Self = serde_json::from_str(&content)
            .map_err(|e| TradingError::Configuration(
                format!("failed to parse config file {}: {}", path, e)
            ))?;

        // Validate all components
        config.market_data.validate()?;
        config.risk.validate()?;
        config.execution.validate()?;
        config.signal.validate()?;

        // Load API credentials from environment
        config.execution.load_credentials()?;

        Ok(config)
    }

    /// Save configuration to file
    pub fn to_file(&self, path: &str) -> Result<()> {
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| TradingError::Configuration(
                format!("failed to serialize config: {}", e)
            ))?;

        std::fs::write(path, content)
            .map_err(|e| TradingError::Configuration(
                format!("failed to write config file {}: {}", path, e)
            ))?;

        Ok(())
    }

    /// Get environment name from metadata
    pub fn environment(&self) -> String {
        self.metadata
            .get("environment")
            .cloned()
            .unwrap_or_else(|| "unknown".to_string())
    }

    /// Check if running in production mode
    pub fn is_production(&self) -> bool {
        self.environment() == "production"
    }

    /// Check if paper trading is enabled
    pub fn is_paper_trading(&self) -> bool {
        self.execution.paper_trading
    }
}
