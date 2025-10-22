//! Data models for database records

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Metric record for time-series data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricRecord {
    /// Timestamp of the metric
    pub timestamp: DateTime<Utc>,
    /// Name of the metric (e.g., "order_latency_ms", "price")
    pub metric_name: String,
    /// Numeric value
    pub value: f64,
    /// Optional symbol (e.g., "BTC/USD")
    pub symbol: Option<String>,
    /// Optional labels for filtering (JSON)
    pub labels: Option<HashMap<String, String>>,
}

/// Candle/OHLCV record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandleRecord {
    /// Timestamp (start of candle)
    pub timestamp: DateTime<Utc>,
    /// Trading symbol
    pub symbol: String,
    /// Open price
    pub open: f64,
    /// High price
    pub high: f64,
    /// Low price
    pub low: f64,
    /// Close price
    pub close: f64,
    /// Volume
    pub volume: i64,
    /// Number of trades (optional)
    pub trade_count: Option<i32>,
}

/// Trade execution record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeRecord {
    /// Unique trade ID
    pub trade_id: String,
    /// Associated order ID
    pub order_id: String,
    /// Trading symbol
    pub symbol: String,
    /// Side (buy/sell)
    pub side: String,
    /// Quantity
    pub quantity: f64,
    /// Execution price
    pub price: f64,
    /// Execution timestamp
    pub timestamp: DateTime<Utc>,
    /// Commission/fees
    pub commission: f64,
    /// Trade value (quantity * price)
    pub trade_value: f64,
    /// Liquidity (maker/taker)
    pub liquidity: Option<String>,
}

/// System event record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemEvent {
    /// Event ID (auto-generated)
    pub id: Option<i64>,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event type (e.g., "order", "system", "error")
    pub event_type: String,
    /// Severity (info, warning, error, critical)
    pub severity: String,
    /// Event message
    pub message: String,
    /// Additional details (JSON)
    pub details: Option<serde_json::Value>,
}

/// Performance summary statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceSummary {
    /// Start value
    pub start_value: f64,
    /// End value
    pub end_value: f64,
    /// Total P&L
    pub total_pnl: f64,
    /// Return percentage
    pub return_pct: f64,
    /// Average Sharpe ratio (if available)
    pub avg_sharpe: Option<f64>,
    /// Worst drawdown
    pub worst_drawdown: Option<f64>,
    /// Number of trades
    pub trade_count: i64,
    /// Win rate percentage
    pub win_rate: Option<f64>,
}

/// Table statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableStats {
    /// Table name
    pub table_name: String,
    /// Row count
    pub row_count: i64,
    /// Minimum timestamp
    pub min_timestamp: Option<DateTime<Utc>>,
    /// Maximum timestamp
    pub max_timestamp: Option<DateTime<Utc>>,
    /// Size in bytes
    pub size_bytes: Option<i64>,
}

/// Aggregated metric result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedMetric {
    /// Time bucket
    pub time_bucket: DateTime<Utc>,
    /// Metric name
    pub metric_name: String,
    /// Symbol (if applicable)
    pub symbol: Option<String>,
    /// Aggregated value
    pub value: f64,
    /// Number of data points in bucket
    pub count: i64,
}

impl MetricRecord {
    /// Create a new metric record with current timestamp
    pub fn new(metric_name: impl Into<String>, value: f64) -> Self {
        Self {
            timestamp: Utc::now(),
            metric_name: metric_name.into(),
            value,
            symbol: None,
            labels: None,
        }
    }

    /// Set symbol
    pub fn with_symbol(mut self, symbol: impl Into<String>) -> Self {
        self.symbol = Some(symbol.into());
        self
    }

    /// Set labels
    pub fn with_labels(mut self, labels: HashMap<String, String>) -> Self {
        self.labels = Some(labels);
        self
    }

    /// Add a single label
    pub fn add_label(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        let labels = self.labels.get_or_insert_with(HashMap::new);
        labels.insert(key.into(), value.into());
        self
    }
}

impl CandleRecord {
    /// Create a new candle record
    pub fn new(
        timestamp: DateTime<Utc>,
        symbol: impl Into<String>,
        open: f64,
        high: f64,
        low: f64,
        close: f64,
        volume: i64,
    ) -> Self {
        Self {
            timestamp,
            symbol: symbol.into(),
            open,
            high,
            low,
            close,
            volume,
            trade_count: None,
        }
    }

    /// Set trade count
    pub fn with_trade_count(mut self, count: i32) -> Self {
        self.trade_count = Some(count);
        self
    }
}

impl SystemEvent {
    /// Create a new system event
    pub fn new(
        event_type: impl Into<String>,
        severity: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            id: None,
            timestamp: Utc::now(),
            event_type: event_type.into(),
            severity: severity.into(),
            message: message.into(),
            details: None,
        }
    }

    /// Set details
    pub fn with_details(mut self, details: serde_json::Value) -> Self {
        self.details = Some(details);
        self
    }

    /// Create an info event
    pub fn info(message: impl Into<String>) -> Self {
        Self::new("system", "info", message)
    }

    /// Create a warning event
    pub fn warning(message: impl Into<String>) -> Self {
        Self::new("system", "warning", message)
    }

    /// Create an error event
    pub fn error(message: impl Into<String>) -> Self {
        Self::new("system", "error", message)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metric_record_builder() {
        let metric = MetricRecord::new("test_metric", 42.5)
            .with_symbol("BTC/USD")
            .add_label("exchange", "alpaca");

        assert_eq!(metric.metric_name, "test_metric");
        assert_eq!(metric.value, 42.5);
        assert_eq!(metric.symbol, Some("BTC/USD".to_string()));
        assert!(metric.labels.is_some());
        assert_eq!(
            metric.labels.unwrap().get("exchange"),
            Some(&"alpaca".to_string())
        );
    }

    #[test]
    fn test_system_event_helpers() {
        let event = SystemEvent::info("Test message");
        assert_eq!(event.severity, "info");
        assert_eq!(event.message, "Test message");

        let event = SystemEvent::error("Error message");
        assert_eq!(event.severity, "error");
    }
}
