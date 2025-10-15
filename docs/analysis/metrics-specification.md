# Metrics and Observability Specification

## Executive Summary

This document defines the metrics, monitoring, and observability strategy for the Rust algorithmic trading system. The goal is to provide comprehensive insight into system performance, trading quality, and operational health with minimal latency overhead.

## 1. Metrics Architecture

### 1.1 Metric Categories

1. **Latency Metrics**: End-to-end timing measurements
2. **Throughput Metrics**: Message and order processing rates
3. **Market Data Metrics**: Order book and data quality
4. **Trading Metrics**: Order execution and fill quality
5. **Risk Metrics**: Position limits and exposure
6. **P&L Metrics**: Realized and unrealized profit/loss
7. **System Metrics**: Resource utilization and health

### 1.2 Collection Strategy

**Hot Path (In-Process)**
- Use `metrics` crate with lock-free counters
- Sub-microsecond overhead per metric
- Thread-local aggregation
- Export via Prometheus exporter

**Cold Path (External)**
- Structured logs with `tracing` crate
- Asynchronous batch writes
- JSON or structured format
- Send to log aggregator

## 2. Latency Metrics

### 2.1 Critical Path Latencies

**Market Data Processing**
```rust
/// Latency from WebSocket receive to event dispatch
metrics::histogram!("market_data.websocket_to_dispatch_us")
    .record(elapsed_micros);

/// Order book update latency
metrics::histogram!("market_data.order_book_update_us")
    .record(elapsed_micros);

/// Quote parsing and validation
metrics::histogram!("market_data.quote_parse_us")
    .record(elapsed_micros);

/// Trade parsing and validation
metrics::histogram!("market_data.trade_parse_us")
    .record(elapsed_micros);
```

**Signal Generation**
```rust
/// Feature calculation latency
metrics::histogram!("signal.feature_calculation_us")
    .record(elapsed_micros);

/// Model inference latency
metrics::histogram!("signal.model_inference_us")
    .record(elapsed_micros);

/// Signal generation end-to-end
metrics::histogram!("signal.generation_us")
    .record(elapsed_micros);
```

**Order Execution**
```rust
/// Signal to order submission
metrics::histogram!("execution.signal_to_order_us")
    .record(elapsed_micros);

/// Order validation and risk check
metrics::histogram!("execution.risk_check_us")
    .record(elapsed_micros);

/// Order to exchange (network)
metrics::histogram!("execution.order_to_exchange_ms")
    .record(elapsed_millis);

/// Fill acknowledgment latency
metrics::histogram!("execution.fill_ack_ms")
    .record(elapsed_millis);
```

**End-to-End Latency**
```rust
/// Market data event to order sent
metrics::histogram!("system.market_to_order_us")
    .record(elapsed_micros);

/// Full trading loop (event → signal → order → fill)
metrics::histogram!("system.full_trading_loop_ms")
    .record(elapsed_millis);
```

### 2.2 Percentile Tracking

Track P50, P95, P99, P999 for all latency metrics:
```rust
// Automatically calculated by Prometheus/Grafana
// Example query: histogram_quantile(0.99, market_data_websocket_to_dispatch_us)
```

**Target Latencies**
- WebSocket to dispatch: <50μs (P99)
- Order book update: <10μs (P99)
- Signal generation: <100μs (P99)
- Risk check: <20μs (P99)
- End-to-end (hot path): <200μs (P99)

## 3. Throughput Metrics

### 3.1 Message Rates

**Market Data**
```rust
/// Trades received per second
metrics::counter!("market_data.trades_received")
    .increment(1);

/// Quotes received per second
metrics::counter!("market_data.quotes_received")
    .increment(1);

/// Bars generated per second
metrics::counter!("market_data.bars_generated")
    .increment(1);

/// Messages dropped (overflow)
metrics::counter!("market_data.messages_dropped")
    .increment(1);
```

**Order Flow**
```rust
/// Orders submitted
metrics::counter!("execution.orders_submitted")
    .increment(1);

/// Orders filled
metrics::counter!("execution.orders_filled")
    .increment(1);

/// Orders rejected
metrics::counter!("execution.orders_rejected")
    .increment(1);

/// Orders canceled
metrics::counter!("execution.orders_canceled")
    .increment(1);
```

**System Throughput**
```rust
/// Events processed per second (total)
metrics::counter!("system.events_processed")
    .increment(1);

/// Signals generated per second
metrics::counter!("system.signals_generated")
    .increment(1);
```

### 3.2 Rate Limits

Track proximity to rate limits:
```rust
/// Alpaca API calls remaining (daily)
metrics::gauge!("api.alpaca_calls_remaining")
    .set(remaining_calls as f64);

/// Order rate (orders per minute)
metrics::gauge!("execution.order_rate_per_minute")
    .set(rate);
```

## 4. Market Data Quality Metrics

### 4.1 Data Integrity

**Sequence Tracking**
```rust
/// Sequence gaps detected
metrics::counter!("market_data.sequence_gaps")
    .increment(gap_size);

/// Messages out of order
metrics::counter!("market_data.out_of_order")
    .increment(1);

/// Invalid messages (failed validation)
metrics::counter!("market_data.invalid_messages")
    .increment(1);
```

**Staleness**
```rust
/// Age of last market data update (ms)
metrics::gauge!("market_data.last_update_age_ms")
    .set(age_millis as f64);

/// Symbols with stale data (>5s)
metrics::gauge!("market_data.stale_symbols")
    .set(stale_count as f64);
```

### 4.2 Order Book Metrics

**Spread Metrics**
```rust
/// Bid-ask spread in basis points
metrics::histogram!("order_book.spread_bps", "symbol" => symbol)
    .record(spread_bps);

/// Order book imbalance (-1 to 1)
metrics::gauge!("order_book.imbalance", "symbol" => symbol)
    .set(imbalance);

/// Mid price
metrics::gauge!("order_book.mid_price", "symbol" => symbol)
    .set(mid_price);
```

**Liquidity**
```rust
/// Top-of-book liquidity (notional)
metrics::gauge!("order_book.tob_liquidity_usd", "symbol" => symbol)
    .set(liquidity);

/// Crosses detected (invalid market)
metrics::counter!("order_book.crosses_detected", "symbol" => symbol)
    .increment(1);
```

## 5. Trading Performance Metrics

### 5.1 Execution Quality

**Fill Metrics**
```rust
/// Fill rate (filled / submitted)
metrics::gauge!("execution.fill_rate")
    .set(fill_rate);

/// Average fill time (ms)
metrics::histogram!("execution.fill_time_ms")
    .record(fill_time_ms);

/// Partial fill count
metrics::counter!("execution.partial_fills")
    .increment(1);
```

**Slippage**
```rust
/// Price slippage (actual - expected) in bps
metrics::histogram!("execution.slippage_bps", "symbol" => symbol)
    .record(slippage_bps);

/// Negative slippage (price improvement)
metrics::counter!("execution.price_improvements")
    .increment(1);
```

**Rejection Analysis**
```rust
/// Rejections by reason
metrics::counter!("execution.rejections", "reason" => reason)
    .increment(1);
// Reasons: insufficient_funds, invalid_quantity, market_closed, etc.
```

### 5.2 Trading Activity

**Order Types**
```rust
/// Orders by type (market, limit, stop)
metrics::counter!("execution.orders_by_type", "type" => order_type)
    .increment(1);

/// Orders by side (buy, sell)
metrics::counter!("execution.orders_by_side", "side" => side)
    .increment(1);
```

**Volume**
```rust
/// Total volume traded (USD)
metrics::counter!("execution.volume_traded_usd")
    .increment(notional_value);

/// Shares traded
metrics::counter!("execution.shares_traded", "symbol" => symbol)
    .increment(shares);
```

## 6. Risk Metrics

### 6.1 Position Limits

**Exposure**
```rust
/// Current position size (signed)
metrics::gauge!("risk.position_size", "symbol" => symbol)
    .set(position_quantity as f64);

/// Position notional value (USD)
metrics::gauge!("risk.position_value_usd", "symbol" => symbol)
    .set(position_value);

/// Total portfolio exposure (long + short)
metrics::gauge!("risk.total_exposure_usd")
    .set(total_exposure);
```

**Limit Violations**
```rust
/// Position limit breaches
metrics::counter!("risk.position_limit_breached", "symbol" => symbol)
    .increment(1);

/// Orders rejected by risk checks
metrics::counter!("risk.orders_rejected")
    .increment(1);
```

### 6.2 Drawdown Tracking

**Drawdown Metrics**
```rust
/// Current drawdown from peak (%)
metrics::gauge!("risk.current_drawdown_pct")
    .set(drawdown_pct);

/// Maximum drawdown today (%)
metrics::gauge!("risk.max_drawdown_today_pct")
    .set(max_dd_pct);

/// Days since new equity high
metrics::gauge!("risk.days_since_high")
    .set(days as f64);
```

## 7. P&L Metrics

### 7.1 Real-Time P&L

**Unrealized P&L**
```rust
/// Unrealized P&L by symbol
metrics::gauge!("pnl.unrealized", "symbol" => symbol)
    .set(unrealized_pnl);

/// Total unrealized P&L
metrics::gauge!("pnl.total_unrealized")
    .set(total_unrealized);
```

**Realized P&L**
```rust
/// Realized P&L by symbol
metrics::gauge!("pnl.realized", "symbol" => symbol)
    .set(realized_pnl);

/// Total realized P&L today
metrics::gauge!("pnl.total_realized_today")
    .set(realized_today);

/// Total P&L (realized + unrealized)
metrics::gauge!("pnl.total")
    .set(total_pnl);
```

### 7.2 Performance Ratios

**Sharpe Ratio**
```rust
/// Rolling Sharpe ratio (daily returns, 30-day window)
metrics::gauge!("performance.sharpe_ratio_30d")
    .set(sharpe_ratio);

/// Annualized return (%)
metrics::gauge!("performance.annual_return_pct")
    .set(annual_return_pct);
```

**Win Rate**
```rust
/// Winning trades / total trades (%)
metrics::gauge!("performance.win_rate_pct")
    .set(win_rate_pct);

/// Average win / average loss ratio
metrics::gauge!("performance.win_loss_ratio")
    .set(win_loss_ratio);
```

## 8. System Health Metrics

### 8.1 Resource Utilization

**CPU**
```rust
/// CPU usage per component (%)
metrics::gauge!("system.cpu_usage_pct", "component" => component)
    .set(cpu_pct);

/// Thread count
metrics::gauge!("system.thread_count")
    .set(thread_count as f64);
```

**Memory**
```rust
/// Heap memory used (MB)
metrics::gauge!("system.memory_heap_mb")
    .set(heap_mb);

/// RSS memory (MB)
metrics::gauge!("system.memory_rss_mb")
    .set(rss_mb);

/// Allocations per second
metrics::counter!("system.allocations")
    .increment(1);
```

**Network**
```rust
/// WebSocket connection status (0 = down, 1 = up)
metrics::gauge!("system.websocket_connected")
    .set(if connected { 1.0 } else { 0.0 });

/// Network bytes received
metrics::counter!("system.network_bytes_rx")
    .increment(bytes_received);

/// Network bytes sent
metrics::counter!("system.network_bytes_tx")
    .increment(bytes_sent);
```

### 8.2 Error Rates

**Error Tracking**
```rust
/// Errors by type and component
metrics::counter!("system.errors", "component" => component, "type" => error_type)
    .increment(1);

/// Warnings logged
metrics::counter!("system.warnings", "component" => component)
    .increment(1);
```

**Recovery Events**
```rust
/// WebSocket reconnections
metrics::counter!("system.websocket_reconnects")
    .increment(1);

/// API retry count
metrics::counter!("system.api_retries", "endpoint" => endpoint)
    .increment(1);
```

## 9. Implementation Guide

### 9.1 Rust Metrics Collection

```rust
use metrics::{counter, gauge, histogram};
use std::time::Instant;

/// Instrument a function with latency tracking
pub fn instrument_latency<F, R>(metric_name: &'static str, f: F) -> R
where
    F: FnOnce() -> R,
{
    let start = Instant::now();
    let result = f();
    let elapsed = start.elapsed().as_micros() as f64;
    histogram!(metric_name).record(elapsed);
    result
}

/// Example usage
fn process_trade(trade: &Trade) {
    instrument_latency("market_data.trade_parse_us", || {
        // Parse and validate trade
        trade.validate().unwrap();
    });

    counter!("market_data.trades_received").increment(1);
}
```

### 9.2 Prometheus Exporter

```rust
use metrics_exporter_prometheus::PrometheusBuilder;
use std::net::SocketAddr;

/// Initialize Prometheus exporter
pub fn init_metrics() -> Result<(), Box<dyn std::error::Error>> {
    let addr: SocketAddr = "0.0.0.0:9090".parse()?;

    PrometheusBuilder::new()
        .with_http_listener(addr)
        .idle_timeout(
            metrics_util::MetricKindMask::ALL,
            Some(std::time::Duration::from_secs(600))
        )
        .install()?;

    tracing::info!("Prometheus metrics server listening on {}", addr);
    Ok(())
}
```

### 9.3 Structured Logging

```rust
use tracing::{info, warn, error, instrument};

#[instrument(skip(order))]
pub fn submit_order(order: &Order) -> Result<(), OrderError> {
    info!(
        order_id = %order.order_id,
        symbol = %order.symbol,
        side = ?order.side,
        quantity = order.quantity,
        "Submitting order"
    );

    match execute_order(order) {
        Ok(fill) => {
            info!(
                order_id = %order.order_id,
                fill_price = fill.price,
                fill_quantity = fill.quantity,
                "Order filled"
            );
            Ok(())
        }
        Err(e) => {
            error!(
                order_id = %order.order_id,
                error = %e,
                "Order rejected"
            );
            Err(e)
        }
    }
}
```

## 10. Grafana Dashboard Design

### 10.1 Dashboard Panels

**Panel 1: System Overview**
- Total events/sec (counter rate)
- End-to-end latency P99 (histogram quantile)
- WebSocket connection status (gauge)
- Error rate (counter rate)

**Panel 2: Market Data Quality**
- Messages received by type (stacked area)
- Sequence gaps over time (counter rate)
- Data staleness by symbol (heatmap)

**Panel 3: Trading Performance**
- Orders by status (pie chart)
- Fill rate % (gauge)
- Slippage distribution (histogram)
- Volume traded (bar chart)

**Panel 4: P&L and Risk**
- Real-time P&L (line chart)
- Position sizes by symbol (bar chart)
- Current drawdown (gauge)
- Sharpe ratio (line chart)

**Panel 5: Latency Breakdown**
- Latency waterfall (stacked bar)
- P50/P95/P99 percentiles (multi-line)
- Component-wise latency (table)

### 10.2 Example Prometheus Queries

**Average latency over 5m**
```promql
rate(market_data_websocket_to_dispatch_us_sum[5m]) /
rate(market_data_websocket_to_dispatch_us_count[5m])
```

**P99 latency**
```promql
histogram_quantile(0.99,
  rate(market_data_websocket_to_dispatch_us_bucket[5m]))
```

**Order fill rate**
```promql
rate(execution_orders_filled[5m]) /
rate(execution_orders_submitted[5m])
```

**Total P&L**
```promql
pnl_total_unrealized + pnl_total_realized_today
```

## 11. Alerting Rules

### 11.1 Critical Alerts

**System Health**
```yaml
- alert: WebSocketDisconnected
  expr: system_websocket_connected == 0
  for: 30s
  labels:
    severity: critical
  annotations:
    summary: "Market data feed disconnected"
```

**Data Quality**
```yaml
- alert: HighSequenceGaps
  expr: rate(market_data_sequence_gaps[1m]) > 10
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High rate of sequence gaps in market data"
```

**Latency**
```yaml
- alert: HighLatency
  expr: histogram_quantile(0.99, rate(system_market_to_order_us_bucket[5m])) > 500
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P99 latency above 500μs"
```

**Risk**
```yaml
- alert: DrawdownExceeded
  expr: risk_current_drawdown_pct > 10
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Drawdown exceeded 10%"
```

### 11.2 Warning Alerts

**Performance Degradation**
```yaml
- alert: FillRateLow
  expr: rate(execution_orders_filled[5m]) / rate(execution_orders_submitted[5m]) < 0.8
  for: 10m
  labels:
    severity: warning
```

**Resource Utilization**
```yaml
- alert: HighMemoryUsage
  expr: system_memory_rss_mb > 1000
  for: 5m
  labels:
    severity: warning
```

## 12. Performance Impact

### 12.1 Overhead Analysis

**Metrics Collection Overhead**
- Counter increment: ~5-10ns
- Gauge set: ~5-10ns
- Histogram record: ~50-100ns
- Total overhead: <0.1% for typical workload

**Log Overhead**
- Structured log write: ~1-5μs (async)
- Negligible on hot path due to batching

### 12.2 Best Practices

1. **Use thread-local aggregation** for high-frequency metrics
2. **Batch histogram updates** when possible
3. **Limit cardinality** of label values (<100 unique values)
4. **Sample high-frequency events** if needed (e.g., 1% sampling)
5. **Use async logging** to avoid blocking hot path

## Summary

This metrics specification provides comprehensive observability across all system components while maintaining sub-microsecond overhead on critical paths. The combination of real-time metrics, structured logging, and Grafana dashboards enables rapid debugging and performance optimization.

## Next Steps

1. Implement metrics collection in each component
2. Set up Prometheus server and exporters
3. Create Grafana dashboards
4. Define alert thresholds based on backtests
5. Implement automated performance regression tests
