//! Common metrics infrastructure for observability
//!
//! Provides unified metrics collection across all services using Prometheus format.
//! Metrics are exposed via HTTP endpoints and can be scraped by Prometheus or
//! Python collectors.

use axum::{routing::get, Router};
use std::net::SocketAddr;
use tokio::task::JoinHandle;
use tracing::{error, info};

/// Metrics server configuration
pub struct MetricsConfig {
    pub port: u16,
    pub host: String,
}

impl MetricsConfig {
    /// Create default metrics config for market-data service
    pub fn market_data() -> Self {
        Self {
            port: 9091,
            host: "127.0.0.1".to_string(),
        }
    }

    /// Create default metrics config for execution-engine service
    pub fn execution_engine() -> Self {
        Self {
            port: 9092,
            host: "127.0.0.1".to_string(),
        }
    }

    /// Create default metrics config for risk-manager service
    pub fn risk_manager() -> Self {
        Self {
            port: 9093,
            host: "127.0.0.1".to_string(),
        }
    }
}

/// Start metrics HTTP server
///
/// Returns a join handle that can be awaited to keep server running
pub fn start_metrics_server(config: MetricsConfig) -> Result<JoinHandle<()>, anyhow::Error> {
    let addr: SocketAddr = format!("{}:{}", config.host, config.port)
        .parse()
        .map_err(|e| anyhow::anyhow!("Invalid metrics address: {}", e))?;

    info!("Starting metrics server on {}", addr);

    let app = Router::new().route("/metrics", get(metrics_handler));

    let handle = tokio::spawn(async move {
        match axum::serve(
            tokio::net::TcpListener::bind(&addr).await.unwrap_or_else(|e| {
                panic!("Failed to bind metrics server to {}: {}", addr, e)
            }),
            app,
        )
        .await
        {
            Ok(_) => info!("Metrics server stopped gracefully"),
            Err(e) => error!("Metrics server error: {}", e),
        }
    });

    info!("Metrics server started successfully on {}", addr);
    Ok(handle)
}

/// Metrics endpoint handler
async fn metrics_handler() -> String {
    // Use metrics crate's encode function if available
    // For now, return a simple Prometheus-formatted response
    let mut output = String::new();

    // Add standard process metrics
    output.push_str("# HELP process_start_time_seconds Start time of the process\n");
    output.push_str("# TYPE process_start_time_seconds gauge\n");
    output.push_str(&format!(
        "process_start_time_seconds {}\n",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0)
    ));

    output.push('\n');

    // The metrics crate will automatically append its metrics here
    // This is a placeholder - in production, use metrics-exporter-prometheus
    output.push_str("# Metrics exported via metrics crate\n");

    output
}

/// Market data specific metrics
pub mod market_data {
    use ::metrics::{counter, gauge, histogram};

    /// Record a tick received
    pub fn record_tick_received(symbol: &str) {
        counter!("market_data_ticks_received_total", "symbol" => symbol.to_string()).increment(1);
    }

    /// Record a tick processed
    pub fn record_tick_processed(symbol: &str, latency_ms: f64) {
        counter!("market_data_ticks_processed_total", "symbol" => symbol.to_string()).increment(1);
        histogram!("market_data_processing_latency_ms", "symbol" => symbol.to_string())
            .record(latency_ms);
    }

    /// Record orderbook update
    pub fn record_orderbook_update(symbol: &str, depth: usize) {
        counter!("market_data_orderbook_updates_total", "symbol" => symbol.to_string())
            .increment(1);
        gauge!("market_data_orderbook_depth", "symbol" => symbol.to_string()).set(depth as f64);
    }

    /// Record WebSocket reconnection
    pub fn record_websocket_reconnect(reason: &str) {
        counter!("market_data_websocket_reconnects_total", "reason" => reason.to_string())
            .increment(1);
    }

    /// Set WebSocket connection status
    pub fn set_websocket_status(connected: bool) {
        gauge!("market_data_websocket_connected").set(if connected { 1.0 } else { 0.0 });
    }

    /// Record message queue size
    pub fn record_queue_size(size: usize) {
        gauge!("market_data_message_queue_size").set(size as f64);
    }

    /// Record price update
    pub fn record_price_update(symbol: &str, price: f64, volume: f64) {
        gauge!("market_data_price", "symbol" => symbol.to_string()).set(price);
        counter!("market_data_volume_total", "symbol" => symbol.to_string()).increment(volume as u64);
    }
}

/// Execution engine specific metrics
pub mod execution {
    use ::metrics::{counter, gauge, histogram};

    /// Record order submitted
    pub fn record_order_submitted(symbol: &str, side: &str) {
        counter!(
            "execution_orders_submitted_total",
            "symbol" => symbol.to_string(),
            "side" => side.to_string()
        )
        .increment(1);
    }

    /// Record order filled
    pub fn record_order_filled(symbol: &str, side: &str, fill_price: f64, latency_ms: f64) {
        counter!(
            "execution_orders_filled_total",
            "symbol" => symbol.to_string(),
            "side" => side.to_string()
        )
        .increment(1);
        gauge!("execution_last_fill_price", "symbol" => symbol.to_string()).set(fill_price);
        histogram!("execution_fill_latency_ms", "symbol" => symbol.to_string()).record(latency_ms);
    }

    /// Record order rejected
    pub fn record_order_rejected(symbol: &str, reason: &str) {
        counter!(
            "execution_orders_rejected_total",
            "symbol" => symbol.to_string(),
            "reason" => reason.to_string()
        )
        .increment(1);
    }

    /// Record order cancelled
    pub fn record_order_cancelled(symbol: &str) {
        counter!("execution_orders_cancelled_total", "symbol" => symbol.to_string()).increment(1);
    }

    /// Record slippage
    pub fn record_slippage(symbol: &str, slippage_bps: f64) {
        histogram!("execution_slippage_bps", "symbol" => symbol.to_string()).record(slippage_bps);
    }

    /// Record API call
    pub fn record_api_call(endpoint: &str, status: u16, latency_ms: f64) {
        counter!(
            "execution_api_calls_total",
            "endpoint" => endpoint.to_string(),
            "status" => status.to_string()
        )
        .increment(1);
        histogram!("execution_api_latency_ms", "endpoint" => endpoint.to_string())
            .record(latency_ms);
    }

    /// Set rate limit remaining
    pub fn set_rate_limit_remaining(remaining: u32) {
        gauge!("execution_rate_limit_remaining").set(remaining as f64);
    }

    /// Record execution time
    pub fn record_execution_time(operation: &str, duration_ms: f64) {
        histogram!("execution_time_ms", "operation" => operation.to_string()).record(duration_ms);
    }
}

/// Risk manager specific metrics
pub mod risk {
    use ::metrics::{counter, gauge, histogram};

    /// Set position count
    pub fn set_position_count(count: usize) {
        gauge!("risk_position_count").set(count as f64);
    }

    /// Set position size for symbol
    pub fn set_position_size(symbol: &str, size: f64) {
        gauge!("risk_position_size", "symbol" => symbol.to_string()).set(size);
    }

    /// Set total exposure
    pub fn set_total_exposure(exposure: f64) {
        gauge!("risk_total_exposure").set(exposure);
    }

    /// Record limit breach
    pub fn record_limit_breach(limit_type: &str) {
        counter!("risk_limit_breaches_total", "limit_type" => limit_type.to_string()).increment(1);
    }

    /// Set unrealized P&L
    pub fn set_unrealized_pnl(symbol: &str, pnl: f64) {
        gauge!("risk_pnl_unrealized", "symbol" => symbol.to_string()).set(pnl);
    }

    /// Set realized P&L
    pub fn set_realized_pnl(pnl: f64) {
        gauge!("risk_pnl_realized").set(pnl);
    }

    /// Record stop-loss trigger
    pub fn record_stop_loss_trigger(symbol: &str, stop_type: &str) {
        counter!(
            "risk_stop_loss_triggers_total",
            "symbol" => symbol.to_string(),
            "type" => stop_type.to_string()
        )
        .increment(1);
    }

    /// Record circuit breaker trip
    pub fn record_circuit_breaker_trip(reason: &str) {
        counter!("risk_circuit_breaker_trips_total", "reason" => reason.to_string()).increment(1);
    }

    /// Set circuit breaker status
    pub fn set_circuit_breaker_status(tripped: bool) {
        gauge!("risk_circuit_breaker_status").set(if tripped { 1.0 } else { 0.0 });
    }

    /// Set max drawdown
    pub fn set_max_drawdown(drawdown: f64) {
        gauge!("risk_max_drawdown").set(drawdown);
    }

    /// Record position check
    pub fn record_position_check(symbol: &str, check_duration_ms: f64) {
        counter!("risk_position_checks_total", "symbol" => symbol.to_string()).increment(1);
        histogram!("risk_check_duration_ms", "symbol" => symbol.to_string())
            .record(check_duration_ms);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_config_creation() {
        let market_data = MetricsConfig::market_data();
        assert_eq!(market_data.port, 9091);

        let execution = MetricsConfig::execution_engine();
        assert_eq!(execution.port, 9092);

        let risk = MetricsConfig::risk_manager();
        assert_eq!(risk.port, 9093);
    }
}
