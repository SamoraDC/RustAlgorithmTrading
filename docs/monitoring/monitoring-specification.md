# Monitoring Specification for Rust Algorithm Trading System

## Executive Summary

This document defines a comprehensive monitoring and observability strategy for the py_rt (Python-Rust Trading System). The monitoring architecture focuses on four key pillars: **Latency**, **Throughput**, **Reliability**, and **Business Metrics**. All components expose Prometheus metrics, use structured logging via `tracing`, and integrate with industry-standard observability stacks.

**Target SLOs**:
- Order execution latency: p99 < 100μs
- Market data processing: p99 < 10μs
- System availability: 99.95%
- Error rate: < 0.1%

---

## 1. Metrics Architecture

### 1.1 Metrics Exposition Framework

All Rust microservices expose Prometheus metrics on port `9090` via HTTP endpoint `/metrics`:

```rust
// Example metrics server setup (common pattern)
use prometheus::{Registry, Encoder, TextEncoder};
use warp::Filter;

async fn metrics_server(registry: Registry) {
    let metrics_route = warp::path!("metrics")
        .map(move || {
            let encoder = TextEncoder::new();
            let metric_families = registry.gather();
            let mut buffer = vec![];
            encoder.encode(&metric_families, &mut buffer).unwrap();
            String::from_utf8(buffer).unwrap()
        });

    warp::serve(metrics_route).run(([0, 0, 0, 0], 9090)).await;
}
```

### 1.2 Service-Specific Metrics Ports

| Service | Metrics Port | Process Port | Description |
|---------|-------------|--------------|-------------|
| Market Data | 9090 | 5555 (ZMQ) | Market data WebSocket processing |
| Signal Bridge | 9091 | 5556 (ZMQ) | ML inference and signal generation |
| Risk Manager | 9092 | 5557 (ZMQ) | Risk checks and position tracking |
| Execution Engine | 9093 | 5558 (ZMQ) | Order routing and execution |

---

## 2. Key Performance Indicators (KPIs)

### 2.1 Latency Metrics

#### Market Data Service
```prometheus
# WebSocket message processing latency (microseconds)
market_data_websocket_latency_us{exchange="alpaca", message_type="trade|quote|orderbook"}
  Type: Histogram
  Buckets: [1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000]
  Labels: exchange, message_type, symbol
  Alert: p99 > 100μs for 5 minutes

# Order book update latency
market_data_orderbook_update_latency_us{symbol="AAPL"}
  Type: Histogram
  Buckets: [1, 2, 5, 10, 25, 50, 100]
  Labels: symbol, update_type="snapshot|delta"
  Alert: p99 > 10μs

# ZMQ publish latency
market_data_zmq_publish_latency_us{topic="trades|quotes|orderbook"}
  Type: Histogram
  Buckets: [10, 25, 50, 100, 250, 500, 1000]
  Labels: topic
  Alert: p95 > 500μs
```

#### Signal Bridge Service
```prometheus
# ML model inference latency
signal_bridge_inference_latency_us{model_name="strategy_v1"}
  Type: Histogram
  Buckets: [10, 25, 50, 100, 250, 500, 1000, 5000]
  Labels: model_name, input_features_count
  Alert: p99 > 1000μs (1ms)

# Feature computation latency
signal_bridge_feature_computation_us{feature_set="technical_indicators"}
  Type: Histogram
  Buckets: [5, 10, 25, 50, 100, 250]
  Labels: feature_set
  Alert: p95 > 250μs

# End-to-end signal generation latency
signal_bridge_signal_generation_latency_us{symbol="AAPL"}
  Type: Histogram
  Buckets: [50, 100, 250, 500, 1000, 2500, 5000]
  Labels: symbol, signal_type="buy|sell|hold"
  Alert: p99 > 5000μs (5ms)
```

#### Risk Manager Service
```prometheus
# Pre-trade risk check latency
risk_manager_pretrade_check_latency_us{check_type="position_limit|exposure_limit|circuit_breaker"}
  Type: Histogram
  Buckets: [5, 10, 25, 50, 100, 250, 500]
  Labels: check_type
  Alert: p99 > 500μs

# Position update latency
risk_manager_position_update_latency_us{symbol="AAPL"}
  Type: Histogram
  Buckets: [10, 25, 50, 100, 250]
  Labels: symbol
  Alert: p95 > 250μs

# P&L calculation latency
risk_manager_pnl_calculation_latency_us{calculation_type="unrealized|realized"}
  Type: Histogram
  Buckets: [10, 25, 50, 100, 250, 500]
  Labels: calculation_type
  Alert: p95 > 500μs
```

#### Execution Engine Service
```prometheus
# Order submission latency (from signal to API call)
execution_engine_order_submission_latency_us{exchange="alpaca"}
  Type: Histogram
  Buckets: [25, 50, 100, 250, 500, 1000, 2500, 5000]
  Labels: exchange, order_type="market|limit"
  Alert: p99 > 1000μs (1ms)

# Order routing decision latency
execution_engine_routing_latency_us{routing_strategy="smart|aggressive"}
  Type: Histogram
  Buckets: [5, 10, 25, 50, 100]
  Labels: routing_strategy
  Alert: p95 > 100μs

# API call latency (external Alpaca API)
execution_engine_api_call_latency_ms{endpoint="/v2/orders", method="POST"}
  Type: Histogram
  Buckets: [10, 25, 50, 100, 250, 500, 1000, 2500]
  Labels: endpoint, method, status_code
  Alert: p95 > 500ms

# Retry delay (exponential backoff tracking)
execution_engine_retry_delay_ms{retry_attempt="1|2|3"}
  Type: Histogram
  Buckets: [100, 250, 500, 1000, 2500, 5000]
  Labels: retry_attempt
  Alert: retry_attempt=3 count > 10/min
```

### 2.2 Throughput Metrics

```prometheus
# Messages processed per second
market_data_messages_processed_total{message_type="trade|quote|orderbook"}
  Type: Counter
  Labels: message_type, symbol, exchange
  Alert: rate < 100/s for active symbols

# Signals generated per second
signal_bridge_signals_generated_total{signal_type="buy|sell|hold"}
  Type: Counter
  Labels: signal_type, symbol, confidence_bucket="low|medium|high"

# Orders submitted per second
execution_engine_orders_submitted_total{order_type="market|limit", status="success|failure"}
  Type: Counter
  Labels: order_type, status, exchange
  Alert: success_rate < 95%

# Risk checks performed per second
risk_manager_checks_performed_total{check_type="position_limit|exposure|circuit_breaker", result="pass|fail"}
  Type: Counter
  Labels: check_type, result
  Alert: fail_rate > 10%

# ZMQ messages published
zmq_messages_published_total{service="market_data|signal_bridge|risk_manager", topic="trades|orders|signals"}
  Type: Counter
  Labels: service, topic
```

### 2.3 Error Rate Metrics

```prometheus
# WebSocket connection failures
market_data_websocket_connection_failures_total{exchange="alpaca", error_type="timeout|auth|network"}
  Type: Counter
  Labels: exchange, error_type
  Alert: rate > 5/min

# Order rejections
execution_engine_order_rejections_total{rejection_reason="insufficient_funds|risk_limit|invalid_params"}
  Type: Counter
  Labels: rejection_reason, symbol
  Alert: rate > 10/min

# Risk check failures
risk_manager_risk_failures_total{failure_type="position_limit_exceeded|circuit_breaker_triggered"}
  Type: Counter
  Labels: failure_type, symbol
  Alert: circuit_breaker_triggered count > 1

# API call failures
execution_engine_api_failures_total{endpoint="/v2/orders", status_code="400|401|429|500|503"}
  Type: Counter
  Labels: endpoint, status_code, error_message
  Alert: rate > 10/min OR status_code=429 (rate limit)

# ML inference errors
signal_bridge_inference_errors_total{error_type="model_load_failure|input_shape_mismatch|runtime_error"}
  Type: Counter
  Labels: error_type, model_name
  Alert: any error > 0
```

### 2.4 Business Metrics

```prometheus
# Current position values (gauge, updated in real-time)
trading_position_value_usd{symbol="AAPL", side="long|short"}
  Type: Gauge
  Labels: symbol, side
  Alert: abs(value) > max_position_size

# Realized P&L (cumulative counter)
trading_realized_pnl_usd{symbol="AAPL", trade_id="12345"}
  Type: Counter
  Labels: symbol, trade_id, strategy="momentum|mean_reversion"

# Unrealized P&L (current gauge)
trading_unrealized_pnl_usd{symbol="AAPL"}
  Type: Gauge
  Labels: symbol
  Alert: unrealized_pnl < -max_daily_loss

# Total portfolio value
trading_portfolio_value_usd
  Type: Gauge
  Alert: portfolio_value < initial_capital * 0.95 (5% drawdown)

# Open positions count
trading_open_positions_count
  Type: Gauge
  Alert: count > max_open_positions

# Daily trading volume
trading_daily_volume_usd{symbol="AAPL"}
  Type: Counter
  Labels: symbol
  Reset: Daily at midnight UTC

# Slippage tracking
trading_slippage_bps{symbol="AAPL", order_type="market|limit"}
  Type: Histogram
  Buckets: [0, 1, 5, 10, 25, 50, 100, 250]
  Labels: symbol, order_type
  Alert: p95 > 50 bps (0.5%)

# Order fill rate
trading_order_fill_rate{symbol="AAPL", order_type="market|limit"}
  Type: Gauge
  Labels: symbol, order_type
  Alert: fill_rate < 90% for market orders
```

### 2.5 System Resource Metrics

```prometheus
# CPU usage per service
system_cpu_usage_percent{service="market_data|signal_bridge|risk_manager|execution_engine"}
  Type: Gauge
  Labels: service
  Alert: usage > 80%

# Memory usage
system_memory_usage_mb{service="market_data|signal_bridge|risk_manager|execution_engine"}
  Type: Gauge
  Labels: service
  Alert: usage > 500 MB per service

# Connection pool size
system_connection_pool_size{service="execution_engine", pool_type="http|zmq"}
  Type: Gauge
  Labels: service, pool_type

# ZMQ queue depth (message backlog)
system_zmq_queue_depth{service="market_data", queue="outbound"}
  Type: Gauge
  Labels: service, queue
  Alert: depth > 10000 messages

# Tokio runtime metrics
system_tokio_workers_active{service="market_data"}
  Type: Gauge
  Labels: service
```

---

## 3. Logging Strategy

### 3.1 Structured Logging with `tracing`

All services use the `tracing` crate for structured, leveled logging:

```rust
use tracing::{info, warn, error, debug, trace, instrument};

#[instrument(skip(order))]
async fn submit_order(order: Order) -> Result<OrderResponse> {
    debug!(order_id = %order.order_id, symbol = %order.symbol, "Submitting order");

    match exchange_api.submit(order).await {
        Ok(response) => {
            info!(
                order_id = %response.order_id,
                filled_qty = response.filled_quantity,
                avg_price = response.average_price,
                "Order successfully submitted"
            );
            Ok(response)
        }
        Err(e) => {
            error!(
                order_id = %order.order_id,
                error = %e,
                "Order submission failed"
            );
            Err(e)
        }
    }
}
```

### 3.2 Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| ERROR | System failures, API errors, critical issues | "Failed to connect to WebSocket", "Risk limit breached" |
| WARN | Degraded performance, recoverable errors | "Retry attempt 2/3", "High latency detected (>500μs)" |
| INFO | Important state changes, business events | "Order filled", "Position opened", "Service started" |
| DEBUG | Detailed operational info for troubleshooting | "Received market data message", "Risk check passed" |
| TRACE | Very verbose, low-level debugging | "ZMQ message payload: {...}" |

### 3.3 Log Aggregation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Rust Services (tracing → JSON output to stdout)           │
│  ├─ market-data (tracing_subscriber::fmt::json())          │
│  ├─ signal-bridge                                           │
│  ├─ risk-manager                                            │
│  └─ execution-engine                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Filebeat / Fluent Bit │  (log shipper)
         │  - Tail stdout/stderr  │
         │  - Parse JSON          │
         │  - Add metadata        │
         └───────────┬────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Elasticsearch │  (centralized log storage)
              │  - Index logs │
              │  - 30-day retention
              └──────┬───────┘
                     │
                     ▼
                ┌─────────┐
                │ Kibana  │  (log visualization & search)
                └─────────┘
```

### 3.4 Log Format (JSON)

```json
{
  "timestamp": "2025-10-21T15:06:30.123456Z",
  "level": "INFO",
  "target": "execution_engine::router",
  "fields": {
    "message": "Order successfully submitted",
    "order_id": "a1b2c3d4",
    "symbol": "AAPL",
    "filled_qty": 100.0,
    "avg_price": 175.23,
    "latency_us": 342
  },
  "span": {
    "name": "submit_order",
    "order_id": "a1b2c3d4"
  }
}
```

### 3.5 Critical Log Queries

**High-priority alerts (query in Kibana/Elasticsearch)**:

```lucene
# All errors in last 5 minutes
level:ERROR AND timestamp:[now-5m TO now]

# Order rejections
fields.message:"Order rejection" OR fields.rejection_reason:*

# Circuit breaker triggers
target:risk_manager AND fields.message:"Circuit breaker triggered"

# API rate limits
fields.status_code:429 OR fields.error_message:*"rate limit"*

# High latency (>1ms for critical path)
fields.latency_us:>1000 AND target:(execution_engine OR risk_manager)

# WebSocket disconnections
target:market_data AND (level:ERROR OR level:WARN) AND fields.message:*"disconnect"*
```

---

## 4. Alert Definitions

### 4.1 Critical Alerts (P0 - Immediate Action Required)

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| **Circuit Breaker Triggered** | `risk_manager_risk_failures_total{failure_type="circuit_breaker_triggered"}` | count > 0 | STOP ALL TRADING, page on-call engineer |
| **Max Daily Loss Exceeded** | `trading_unrealized_pnl_usd < -max_daily_loss` | -$5000 (configurable) | HALT trading, close positions |
| **WebSocket Disconnect** | `market_data_websocket_connection_failures_total` | rate > 3/min | RESTART service, check network |
| **Execution API Down** | `execution_engine_api_failures_total{status_code="5xx"}` | rate > 10/min | PAUSE order submission, use backup venue |
| **Memory Leak** | `system_memory_usage_mb` | > 1 GB per service | RESTART affected service |

### 4.2 High-Priority Alerts (P1 - Respond within 15 minutes)

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| **High Order Latency** | `execution_engine_order_submission_latency_us` p99 | > 5ms | Investigate network/API, check CPU |
| **High Slippage** | `trading_slippage_bps` p95 | > 50 bps | Review execution strategy, check liquidity |
| **ML Inference Errors** | `signal_bridge_inference_errors_total` | any error > 0 | Validate model file, check ONNX runtime |
| **Risk Check Failures** | `risk_manager_risk_failures_total{failure_type="position_limit_exceeded"}` | rate > 10/min | Review position limits, check calculations |
| **Low Fill Rate** | `trading_order_fill_rate` | < 90% for market orders | Check exchange status, review order params |

### 4.3 Medium-Priority Alerts (P2 - Review daily)

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| **Elevated Market Data Latency** | `market_data_websocket_latency_us` p95 | > 500μs | Check WebSocket performance, optimize parser |
| **High CPU Usage** | `system_cpu_usage_percent` | > 80% sustained | Optimize hot paths, consider scaling |
| **ZMQ Queue Backlog** | `system_zmq_queue_depth` | > 5000 messages | Increase consumer rate, optimize pipeline |
| **Retry Escalation** | `execution_engine_retry_delay_ms{retry_attempt="3"}` | count > 10/min | Investigate root cause of failures |

### 4.4 Alerting Configuration (Prometheus Alertmanager)

```yaml
# /etc/prometheus/alerts/trading_system.yml
groups:
  - name: trading_critical
    interval: 10s
    rules:
      - alert: CircuitBreakerTriggered
        expr: risk_manager_risk_failures_total{failure_type="circuit_breaker_triggered"} > 0
        for: 0s
        labels:
          severity: critical
          team: trading
        annotations:
          summary: "CRITICAL: Circuit breaker triggered - all trading halted"
          description: "Risk Manager has triggered circuit breaker. Immediate action required."

      - alert: MaxDailyLossExceeded
        expr: trading_unrealized_pnl_usd < -5000
        for: 1m
        labels:
          severity: critical
          team: trading
        annotations:
          summary: "CRITICAL: Max daily loss exceeded ($5000)"
          description: "Unrealized P&L: {{ $value }} USD. Halt trading immediately."

      - alert: WebSocketDisconnected
        expr: rate(market_data_websocket_connection_failures_total[5m]) > 0.6
        for: 2m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Market data WebSocket disconnecting frequently"
          description: "{{ $value }} disconnections/sec. Trading may be impaired."

  - name: trading_high_priority
    interval: 30s
    rules:
      - alert: HighOrderLatency
        expr: histogram_quantile(0.99, rate(execution_engine_order_submission_latency_us_bucket[5m])) > 5000
        for: 5m
        labels:
          severity: high
          team: trading
        annotations:
          summary: "High order submission latency (p99 > 5ms)"
          description: "p99 latency: {{ $value }}μs. Investigate execution pipeline."

      - alert: HighSlippage
        expr: histogram_quantile(0.95, rate(trading_slippage_bps_bucket[15m])) > 50
        for: 10m
        labels:
          severity: high
          team: trading
        annotations:
          summary: "High slippage detected (p95 > 50 bps)"
          description: "p95 slippage: {{ $value }} bps. Review execution strategy."

      - alert: MLInferenceFailure
        expr: increase(signal_bridge_inference_errors_total[5m]) > 0
        for: 1m
        labels:
          severity: high
          team: ml
        annotations:
          summary: "ML inference errors detected"
          description: "Error count: {{ $value }}. Validate model and runtime."
```

---

## 5. Dashboard Requirements

### 5.1 Grafana Dashboard Layout

**Dashboard 1: Real-Time Trading Operations** (refresh: 5s)

```
┌────────────────────────────────────────────────────────────┐
│  REAL-TIME TRADING DASHBOARD                               │
├────────────────────────────────────────────────────────────┤
│  Row 1: KEY METRICS (single stat panels)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Open P&L │ │ Realized │ │  Open    │ │ Order    │      │
│  │  $1,234  │ │ P&L      │ │ Positions│ │ Fill Rate│      │
│  │   ▲ 2.3% │ │  $5,678  │ │    12    │ │  98.7%   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├────────────────────────────────────────────────────────────┤
│  Row 2: LATENCY DISTRIBUTION (heatmap)                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Order Submission Latency (p50/p95/p99)             │    │
│  │ [Heatmap: 5min intervals, μs buckets]              │    │
│  └────────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────────┤
│  Row 3: THROUGHPUT (time series graphs)                    │
│  ┌─────────────────────┐ ┌──────────────────────┐         │
│  │ Orders/sec          │ │ Signals/sec          │         │
│  │ [Time series graph] │ │ [Time series graph]  │         │
│  └─────────────────────┘ └──────────────────────┘         │
├────────────────────────────────────────────────────────────┤
│  Row 4: ERROR TRACKING (time series + table)               │
│  ┌─────────────────────┐ ┌──────────────────────┐         │
│  │ Error Rate          │ │ Recent Errors        │         │
│  │ [Stacked area chart]│ │ [Table: last 10]     │         │
│  └─────────────────────┘ └──────────────────────┘         │
└────────────────────────────────────────────────────────────┘
```

**Dashboard 2: System Health & Performance** (refresh: 30s)

```
┌────────────────────────────────────────────────────────────┐
│  SYSTEM HEALTH DASHBOARD                                   │
├────────────────────────────────────────────────────────────┤
│  Row 1: SERVICE STATUS (status panels)                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐  │
│  │ Market    │ │ Signal    │ │ Risk      │ │Execution │  │
│  │ Data      │ │ Bridge    │ │ Manager   │ │ Engine   │  │
│  │   ✓ OK    │ │   ✓ OK    │ │   ✓ OK    │ │  ✓ OK    │  │
│  └───────────┘ └───────────┘ └───────────┘ └──────────┘  │
├────────────────────────────────────────────────────────────┤
│  Row 2: RESOURCE UTILIZATION (gauges + time series)       │
│  ┌─────────────────────┐ ┌──────────────────────┐         │
│  │ CPU Usage (%)       │ │ Memory Usage (MB)    │         │
│  │ [Multi-gauge panel] │ │ [Stacked area chart] │         │
│  └─────────────────────┘ └──────────────────────┘         │
├────────────────────────────────────────────────────────────┤
│  Row 3: NETWORK & MESSAGING (time series)                 │
│  ┌─────────────────────┐ ┌──────────────────────┐         │
│  │ ZMQ Queue Depth     │ │ WebSocket Status     │         │
│  │ [Line graph]        │ │ [Connection status]  │         │
│  └─────────────────────┘ └──────────────────────┘         │
└────────────────────────────────────────────────────────────┘
```

### 5.2 Example Grafana Queries

**Query 1: Order Submission Latency (p50/p95/p99)**
```promql
# p50
histogram_quantile(0.50, rate(execution_engine_order_submission_latency_us_bucket[5m]))

# p95
histogram_quantile(0.95, rate(execution_engine_order_submission_latency_us_bucket[5m]))

# p99
histogram_quantile(0.99, rate(execution_engine_order_submission_latency_us_bucket[5m]))
```

**Query 2: Order Success Rate**
```promql
# Success rate (%)
100 * (
  rate(execution_engine_orders_submitted_total{status="success"}[5m])
  /
  rate(execution_engine_orders_submitted_total[5m])
)
```

**Query 3: Current Portfolio Value**
```promql
# Total portfolio value (sum across all positions)
sum(trading_position_value_usd)
```

**Query 4: Error Rate by Service**
```promql
# Errors per second by service
sum(rate(execution_engine_api_failures_total[5m])) by (service)
```

**Query 5: ZMQ Queue Backlog**
```promql
# Queue depth by service and queue
system_zmq_queue_depth{service=~"market_data|signal_bridge"}
```

---

## 6. Service Level Objectives (SLOs)

### 6.1 Availability SLOs

| Service | Target Availability | Max Downtime/Month | Max Downtime/Year |
|---------|---------------------|---------------------|-------------------|
| Market Data | 99.95% | 21.6 minutes | 4.38 hours |
| Execution Engine | 99.95% | 21.6 minutes | 4.38 hours |
| Risk Manager | 99.99% | 4.3 minutes | 52.6 minutes |
| Signal Bridge | 99.9% | 43.2 minutes | 8.76 hours |

### 6.2 Performance SLOs

| Metric | Target | Measurement Window | Enforcement |
|--------|--------|-------------------|-------------|
| Order Execution Latency (p99) | < 100μs | 5 minutes | Alert if exceeded for 5+ minutes |
| Market Data Processing (p99) | < 10μs | 5 minutes | Alert if exceeded for 5+ minutes |
| ML Inference (p99) | < 1ms | 5 minutes | Alert if exceeded for 10+ minutes |
| Risk Check (p95) | < 500μs | 5 minutes | Alert if exceeded for 5+ minutes |
| Order Success Rate | > 99% | 15 minutes | Alert if < 95% |

### 6.3 Reliability SLOs

| Metric | Target | Enforcement |
|--------|--------|-------------|
| Error Rate (all services) | < 0.1% | Alert if > 1% for 5+ minutes |
| WebSocket Connection Uptime | > 99.9% | Alert on 3+ disconnects/5min |
| Order Fill Rate (Market Orders) | > 99% | Alert if < 95% |
| Circuit Breaker False Positives | 0 per day | Manual review if triggered |

---

## 7. Monitoring Gaps & Recommendations

### 7.1 Current Implementation Status

✅ **Implemented**:
- `tracing` crate integration in all services
- Basic structured logging to stdout
- Manual metrics (no Prometheus yet)

❌ **Missing**:
- Prometheus metrics exposition
- Metrics server on port 9090
- Histogram/counter/gauge definitions
- Grafana dashboards
- Alertmanager integration
- Log aggregation (Elasticsearch/Kibana)

### 7.2 Recommended Instrumentation Improvements

#### Add to `common/Cargo.toml`:
```toml
[dependencies]
prometheus = "0.13"
lazy_static = "1.4"
```

#### Create `common/src/metrics.rs`:
```rust
use lazy_static::lazy_static;
use prometheus::{
    register_histogram_vec, register_counter_vec, register_gauge_vec,
    HistogramVec, CounterVec, GaugeVec, Registry
};

lazy_static! {
    pub static ref REGISTRY: Registry = Registry::new();

    // Latency metrics
    pub static ref ORDER_SUBMISSION_LATENCY: HistogramVec = register_histogram_vec!(
        "execution_engine_order_submission_latency_us",
        "Order submission latency in microseconds",
        &["exchange", "order_type"],
        vec![25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
    ).unwrap();

    // Throughput metrics
    pub static ref ORDERS_SUBMITTED: CounterVec = register_counter_vec!(
        "execution_engine_orders_submitted_total",
        "Total orders submitted",
        &["order_type", "status", "exchange"]
    ).unwrap();

    // Business metrics
    pub static ref POSITION_VALUE: GaugeVec = register_gauge_vec!(
        "trading_position_value_usd",
        "Current position value in USD",
        &["symbol", "side"]
    ).unwrap();
}
```

#### Update service main.rs:
```rust
// Start metrics server
tokio::spawn(async {
    serve_metrics(9090).await;
});

// Use metrics in code
use common::metrics::ORDER_SUBMISSION_LATENCY;

let start = Instant::now();
let result = submit_order(order).await;
ORDER_SUBMISSION_LATENCY
    .with_label_values(&["alpaca", "market"])
    .observe(start.elapsed().as_micros() as f64);
```

### 7.3 Tracing Enhancements

Add distributed tracing with `tracing-opentelemetry`:

```toml
[dependencies]
tracing-opentelemetry = "0.21"
opentelemetry = { version = "0.21", features = ["trace"] }
opentelemetry-jaeger = "0.20"
```

```rust
// Initialize OpenTelemetry/Jaeger for distributed tracing
use opentelemetry::global;
use tracing_subscriber::layer::SubscriberExt;

let tracer = opentelemetry_jaeger::new_agent_pipeline()
    .with_service_name("execution-engine")
    .install_simple()
    .unwrap();

let telemetry = tracing_opentelemetry::layer().with_tracer(tracer);

tracing_subscriber::registry()
    .with(telemetry)
    .with(EnvFilter::from_default_env())
    .init();
```

---

## 8. Implementation Roadmap

### Phase 1: Core Metrics (Week 1)
1. Add `prometheus` dependency to all services
2. Create `common/src/metrics.rs` with core metric definitions
3. Instrument critical paths:
   - Order submission latency
   - Market data processing latency
   - Risk check latency
4. Add metrics HTTP server on port 9090 to each service
5. Test metrics endpoint: `curl localhost:9090/metrics`

### Phase 2: Alerting (Week 2)
1. Deploy Prometheus server
2. Configure scrape targets for all services
3. Create alerting rules (`trading_system.yml`)
4. Deploy Alertmanager
5. Configure notification channels (PagerDuty, Slack)
6. Test critical alerts (circuit breaker, max loss)

### Phase 3: Dashboards (Week 3)
1. Deploy Grafana
2. Create "Real-Time Trading Operations" dashboard
3. Create "System Health & Performance" dashboard
4. Add custom panels for business metrics (P&L, positions)
5. Configure auto-refresh and alerting in Grafana

### Phase 4: Log Aggregation (Week 4)
1. Deploy Elasticsearch cluster (3 nodes)
2. Install Filebeat on all service hosts
3. Configure JSON log parsing
4. Create Kibana dashboards for log search
5. Set up log retention policy (30 days)

### Phase 5: Advanced Observability (Ongoing)
1. Add distributed tracing with OpenTelemetry/Jaeger
2. Implement anomaly detection (ML-based alerts)
3. Create SLO dashboards
4. Add capacity planning metrics
5. Integrate with incident management (PagerDuty)

---

## 9. Operational Runbooks

### 9.1 Circuit Breaker Triggered

**Alert**: `risk_manager_risk_failures_total{failure_type="circuit_breaker_triggered"} > 0`

**Response**:
1. **IMMEDIATE**: Stop all trading activity (kill execution-engine process)
2. **Investigate**: Check `trading_unrealized_pnl_usd` - did we hit max daily loss?
3. **Review logs**:
   ```bash
   grep "Circuit breaker" logs/risk-manager.log | tail -20
   ```
4. **Analyze positions**: Check Grafana "Current Positions" panel
5. **Decision**:
   - If legitimate trigger: Close positions manually, reset for next day
   - If false positive: Investigate risk calculation bug, fix, redeploy
6. **Document**: Record incident in incident log with root cause

### 9.2 High Order Latency

**Alert**: `execution_engine_order_submission_latency_us p99 > 5ms`

**Response**:
1. Check CPU usage: `system_cpu_usage_percent{service="execution_engine"}`
2. Check Alpaca API status: `execution_engine_api_call_latency_ms`
3. Check network latency: `ping api.alpaca.markets`
4. Review ZMQ queue depth: `system_zmq_queue_depth`
5. If CPU > 80%: Investigate hot paths with `perf` profiler
6. If API slow: Check Alpaca status page, consider backup venue
7. If ZMQ backlog: Increase consumer threads or optimize pipeline

### 9.3 WebSocket Disconnection

**Alert**: `market_data_websocket_connection_failures_total rate > 3/min`

**Response**:
1. Check WebSocket connection status in logs
2. Verify network connectivity: `ping stream.data.alpaca.markets`
3. Check Alpaca API status page
4. Review authentication logs (API key validity)
5. If persistent: Restart market-data service with exponential backoff
6. If Alpaca-side issue: Switch to backup data provider (if available)
7. Monitor order submission - may need to pause trading if data quality degrades

---

## 10. Appendix

### 10.1 Prometheus Configuration Example

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - "/etc/prometheus/alerts/trading_system.yml"

scrape_configs:
  - job_name: 'market-data'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          service: 'market-data'

  - job_name: 'signal-bridge'
    static_configs:
      - targets: ['localhost:9091']
        labels:
          service: 'signal-bridge'

  - job_name: 'risk-manager'
    static_configs:
      - targets: ['localhost:9092']
        labels:
          service: 'risk-manager'

  - job_name: 'execution-engine'
    static_configs:
      - targets: ['localhost:9093']
        labels:
          service: 'execution-engine'
```

### 10.2 References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [tracing crate documentation](https://docs.rs/tracing/)
- [OpenTelemetry Rust](https://github.com/open-telemetry/opentelemetry-rust)
- [SLO Calculation Guide](https://sre.google/workbook/slo-document/)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-21
**Author**: Analyst Agent (Hive Mind Swarm)
**Status**: Final Specification
