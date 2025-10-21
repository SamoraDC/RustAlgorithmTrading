# Monitoring Implementation Quick-Start Guide

## Overview

This guide provides step-by-step instructions to implement the monitoring specification for the Rust Algorithm Trading System. Follow this guide to add Prometheus metrics, structured logging, and alerting to all microservices.

---

## Phase 1: Add Core Dependencies (15 minutes)

### Step 1.1: Update `rust/common/Cargo.toml`

Add monitoring dependencies to the common crate:

```toml
[dependencies]
# Existing dependencies...
serde.workspace = true
serde_json.workspace = true
chrono.workspace = true
anyhow.workspace = true
thiserror.workspace = true
indexmap.workspace = true

# NEW: Monitoring dependencies
prometheus = "0.13"
lazy_static = "1.4"
warp = "0.3"
tokio = { version = "1", features = ["full"] }
```

### Step 1.2: Create `rust/common/src/metrics.rs`

Create a new file with shared metrics definitions:

```rust
use lazy_static::lazy_static;
use prometheus::{
    register_histogram_vec, register_counter_vec, register_gauge_vec,
    HistogramVec, CounterVec, GaugeVec, Registry, Encoder, TextEncoder
};
use std::sync::Arc;

lazy_static! {
    pub static ref REGISTRY: Registry = Registry::new();

    // ===== LATENCY METRICS =====

    /// Market data WebSocket processing latency (microseconds)
    pub static ref MARKET_DATA_WEBSOCKET_LATENCY: HistogramVec = register_histogram_vec!(
        "market_data_websocket_latency_us",
        "WebSocket message processing latency in microseconds",
        &["exchange", "message_type", "symbol"],
        vec![1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 5000.0]
    ).unwrap();

    /// Order book update latency (microseconds)
    pub static ref MARKET_DATA_ORDERBOOK_LATENCY: HistogramVec = register_histogram_vec!(
        "market_data_orderbook_update_latency_us",
        "Order book update latency in microseconds",
        &["symbol", "update_type"],
        vec![1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0]
    ).unwrap();

    /// ML model inference latency (microseconds)
    pub static ref SIGNAL_INFERENCE_LATENCY: HistogramVec = register_histogram_vec!(
        "signal_bridge_inference_latency_us",
        "ML model inference latency in microseconds",
        &["model_name"],
        vec![10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 5000.0]
    ).unwrap();

    /// Risk check latency (microseconds)
    pub static ref RISK_CHECK_LATENCY: HistogramVec = register_histogram_vec!(
        "risk_manager_pretrade_check_latency_us",
        "Pre-trade risk check latency in microseconds",
        &["check_type"],
        vec![5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0]
    ).unwrap();

    /// Order submission latency (microseconds)
    pub static ref ORDER_SUBMISSION_LATENCY: HistogramVec = register_histogram_vec!(
        "execution_engine_order_submission_latency_us",
        "Order submission latency in microseconds",
        &["exchange", "order_type"],
        vec![25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
    ).unwrap();

    /// External API call latency (milliseconds)
    pub static ref API_CALL_LATENCY: HistogramVec = register_histogram_vec!(
        "execution_engine_api_call_latency_ms",
        "External API call latency in milliseconds",
        &["endpoint", "method", "status_code"],
        vec![10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0]
    ).unwrap();

    // ===== THROUGHPUT METRICS =====

    /// Messages processed counter
    pub static ref MESSAGES_PROCESSED: CounterVec = register_counter_vec!(
        "market_data_messages_processed_total",
        "Total messages processed",
        &["message_type", "symbol", "exchange"]
    ).unwrap();

    /// Signals generated counter
    pub static ref SIGNALS_GENERATED: CounterVec = register_counter_vec!(
        "signal_bridge_signals_generated_total",
        "Total signals generated",
        &["signal_type", "symbol", "confidence_bucket"]
    ).unwrap();

    /// Orders submitted counter
    pub static ref ORDERS_SUBMITTED: CounterVec = register_counter_vec!(
        "execution_engine_orders_submitted_total",
        "Total orders submitted",
        &["order_type", "status", "exchange"]
    ).unwrap();

    /// Risk checks counter
    pub static ref RISK_CHECKS_PERFORMED: CounterVec = register_counter_vec!(
        "risk_manager_checks_performed_total",
        "Total risk checks performed",
        &["check_type", "result"]
    ).unwrap();

    // ===== ERROR METRICS =====

    /// WebSocket connection failures
    pub static ref WEBSOCKET_FAILURES: CounterVec = register_counter_vec!(
        "market_data_websocket_connection_failures_total",
        "WebSocket connection failures",
        &["exchange", "error_type"]
    ).unwrap();

    /// Order rejections
    pub static ref ORDER_REJECTIONS: CounterVec = register_counter_vec!(
        "execution_engine_order_rejections_total",
        "Order rejections",
        &["rejection_reason", "symbol"]
    ).unwrap();

    /// Risk check failures
    pub static ref RISK_FAILURES: CounterVec = register_counter_vec!(
        "risk_manager_risk_failures_total",
        "Risk check failures",
        &["failure_type", "symbol"]
    ).unwrap();

    /// API failures
    pub static ref API_FAILURES: CounterVec = register_counter_vec!(
        "execution_engine_api_failures_total",
        "API call failures",
        &["endpoint", "status_code", "error_message"]
    ).unwrap();

    // ===== BUSINESS METRICS =====

    /// Position values (gauge)
    pub static ref POSITION_VALUE: GaugeVec = register_gauge_vec!(
        "trading_position_value_usd",
        "Current position value in USD",
        &["symbol", "side"]
    ).unwrap();

    /// Unrealized P&L (gauge)
    pub static ref UNREALIZED_PNL: GaugeVec = register_gauge_vec!(
        "trading_unrealized_pnl_usd",
        "Unrealized P&L in USD",
        &["symbol"]
    ).unwrap();

    /// Realized P&L (counter)
    pub static ref REALIZED_PNL: CounterVec = register_counter_vec!(
        "trading_realized_pnl_usd",
        "Realized P&L in USD",
        &["symbol", "trade_id", "strategy"]
    ).unwrap();

    /// Open positions count
    pub static ref OPEN_POSITIONS: GaugeVec = register_gauge_vec!(
        "trading_open_positions_count",
        "Number of open positions",
        &[]
    ).unwrap();

    /// Portfolio value
    pub static ref PORTFOLIO_VALUE: GaugeVec = register_gauge_vec!(
        "trading_portfolio_value_usd",
        "Total portfolio value in USD",
        &[]
    ).unwrap();

    // ===== SYSTEM METRICS =====

    /// CPU usage (gauge)
    pub static ref CPU_USAGE: GaugeVec = register_gauge_vec!(
        "system_cpu_usage_percent",
        "CPU usage percentage",
        &["service"]
    ).unwrap();

    /// Memory usage (gauge)
    pub static ref MEMORY_USAGE: GaugeVec = register_gauge_vec!(
        "system_memory_usage_mb",
        "Memory usage in MB",
        &["service"]
    ).unwrap();

    /// ZMQ queue depth (gauge)
    pub static ref ZMQ_QUEUE_DEPTH: GaugeVec = register_gauge_vec!(
        "system_zmq_queue_depth",
        "ZMQ queue depth",
        &["service", "queue"]
    ).unwrap();
}

/// Start Prometheus metrics HTTP server on specified port
pub async fn serve_metrics(port: u16) {
    use warp::Filter;

    let metrics_route = warp::path!("metrics").map(|| {
        let encoder = TextEncoder::new();
        let metric_families = REGISTRY.gather();
        let mut buffer = vec![];
        encoder.encode(&metric_families, &mut buffer).unwrap();
        warp::reply::with_header(
            String::from_utf8(buffer).unwrap(),
            "Content-Type",
            encoder.format_type(),
        )
    });

    tracing::info!(port = %port, "Starting Prometheus metrics server");
    warp::serve(metrics_route)
        .run(([0, 0, 0, 0], port))
        .await;
}
```

### Step 1.3: Update `rust/common/src/lib.rs`

Add the new metrics module:

```rust
pub mod config;
pub mod errors;
pub mod messaging;
pub mod types;
pub mod metrics;  // NEW
```

---

## Phase 2: Instrument Services (1 hour per service)

### Step 2.1: Market Data Service

Update `rust/market-data/src/main.rs`:

```rust
use market_data::MarketDataService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;
use common::metrics;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing with JSON format for structured logging
    tracing_subscriber::registry()
        .with(fmt::layer().json())  // JSON output for log aggregation
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Market Data Service starting...");

    // Start Prometheus metrics server on port 9090
    tokio::spawn(async {
        metrics::serve_metrics(9090).await;
    });

    // Load configuration
    let config = SystemConfig::from_file("config/system.json")?;

    // Initialize service
    let mut service = MarketDataService::new(config.market_data).await?;

    // Run service
    service.run().await?;

    Ok(())
}
```

Update WebSocket message processing in `rust/market-data/src/websocket.rs`:

```rust
use std::time::Instant;
use common::metrics::{MARKET_DATA_WEBSOCKET_LATENCY, MESSAGES_PROCESSED};

async fn process_message(&self, msg: Message) -> Result<()> {
    let start = Instant::now();

    // Parse message
    let message_type = self.parse_message_type(&msg)?;
    let symbol = self.extract_symbol(&msg)?;

    // Process based on type
    match message_type {
        MessageType::Trade => self.handle_trade(msg).await?,
        MessageType::Quote => self.handle_quote(msg).await?,
        MessageType::OrderBook => self.handle_orderbook(msg).await?,
    }

    // Record metrics
    let latency_us = start.elapsed().as_micros() as f64;
    MARKET_DATA_WEBSOCKET_LATENCY
        .with_label_values(&[&self.exchange, &message_type.to_string(), &symbol])
        .observe(latency_us);

    MESSAGES_PROCESSED
        .with_label_values(&[&message_type.to_string(), &symbol, &self.exchange])
        .inc();

    Ok(())
}
```

### Step 2.2: Execution Engine Service

Update `rust/execution-engine/src/main.rs`:

```rust
use execution_engine::ExecutionEngineService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;
use common::metrics;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(fmt::layer().json())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Execution Engine Service starting...");

    // Start Prometheus metrics server on port 9093
    tokio::spawn(async {
        metrics::serve_metrics(9093).await;
    });

    // Load configuration
    let config = SystemConfig::from_file("config/system.json")?;

    // Initialize service
    let service = ExecutionEngineService::new(config.execution).await?;

    tracing::info!("Execution Engine ready");

    service.run().await?;

    Ok(())
}
```

Update order submission in `rust/execution-engine/src/lib.rs`:

```rust
use std::time::Instant;
use common::metrics::{ORDER_SUBMISSION_LATENCY, ORDERS_SUBMITTED, ORDER_REJECTIONS};
use tracing::{info, error, instrument};

#[instrument(skip(self, order))]
pub async fn submit_order(&self, order: Order) -> Result<OrderResponse> {
    let start = Instant::now();

    info!(
        order_id = %order.order_id,
        symbol = %order.symbol,
        order_type = ?order.order_type,
        "Submitting order"
    );

    match self.exchange_api.submit_order(order.clone()).await {
        Ok(response) => {
            let latency_us = start.elapsed().as_micros() as f64;

            // Record latency
            ORDER_SUBMISSION_LATENCY
                .with_label_values(&["alpaca", &order.order_type.to_string()])
                .observe(latency_us);

            // Increment success counter
            ORDERS_SUBMITTED
                .with_label_values(&[
                    &order.order_type.to_string(),
                    "success",
                    "alpaca"
                ])
                .inc();

            info!(
                order_id = %response.order_id,
                latency_us = %latency_us,
                "Order submitted successfully"
            );

            Ok(response)
        }
        Err(e) => {
            // Increment failure counter
            ORDERS_SUBMITTED
                .with_label_values(&[
                    &order.order_type.to_string(),
                    "failure",
                    "alpaca"
                ])
                .inc();

            // Track rejection reason
            let rejection_reason = e.to_string();
            ORDER_REJECTIONS
                .with_label_values(&[&rejection_reason, &order.symbol.to_string()])
                .inc();

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

### Step 2.3: Risk Manager Service

Update `rust/risk-manager/src/main.rs`:

```rust
use risk_manager::RiskManagerService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;
use common::metrics;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::registry()
        .with(fmt::layer().json())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Risk Manager Service starting...");

    // Start Prometheus metrics server on port 9092
    tokio::spawn(async {
        metrics::serve_metrics(9092).await;
    });

    let config = SystemConfig::from_file("config/system.json")?;
    let service = RiskManagerService::new(config.risk).await?;

    service.run().await?;

    Ok(())
}
```

Update risk checks in `rust/risk-manager/src/lib.rs`:

```rust
use std::time::Instant;
use common::metrics::{RISK_CHECK_LATENCY, RISK_CHECKS_PERFORMED, RISK_FAILURES};
use tracing::{warn, debug, instrument};

#[instrument(skip(self, order))]
pub async fn check_pre_trade_risk(&self, order: &Order) -> Result<()> {
    let start = Instant::now();

    debug!(order_id = %order.order_id, "Performing pre-trade risk check");

    // Position limit check
    if let Err(e) = self.check_position_limit(order).await {
        RISK_FAILURES
            .with_label_values(&["position_limit_exceeded", &order.symbol.to_string()])
            .inc();
        RISK_CHECKS_PERFORMED
            .with_label_values(&["position_limit", "fail"])
            .inc();
        return Err(e);
    }

    // Exposure limit check
    if let Err(e) = self.check_exposure_limit(order).await {
        RISK_FAILURES
            .with_label_values(&["exposure_limit_exceeded", &order.symbol.to_string()])
            .inc();
        RISK_CHECKS_PERFORMED
            .with_label_values(&["exposure_limit", "fail"])
            .inc();
        return Err(e);
    }

    // Circuit breaker check
    if let Err(e) = self.check_circuit_breaker().await {
        RISK_FAILURES
            .with_label_values(&["circuit_breaker_triggered", ""])
            .inc();
        RISK_CHECKS_PERFORMED
            .with_label_values(&["circuit_breaker", "fail"])
            .inc();

        warn!("CRITICAL: Circuit breaker triggered!");

        return Err(e);
    }

    let latency_us = start.elapsed().as_micros() as f64;
    RISK_CHECK_LATENCY
        .with_label_values(&["all_checks"])
        .observe(latency_us);

    RISK_CHECKS_PERFORMED
        .with_label_values(&["all_checks", "pass"])
        .inc();

    debug!(latency_us = %latency_us, "Risk checks passed");

    Ok(())
}
```

### Step 2.4: Signal Bridge Service

Update `rust/signal-bridge/src/main.rs`:

```rust
use signal_bridge::SignalBridgeService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;
use common::metrics;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::registry()
        .with(fmt::layer().json())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Signal Bridge Service starting...");

    // Start Prometheus metrics server on port 9091
    tokio::spawn(async {
        metrics::serve_metrics(9091).await;
    });

    let config = SystemConfig::from_file("config/system.json")?;
    let service = SignalBridgeService::new(config.signal).await?;

    service.run().await?;

    Ok(())
}
```

---

## Phase 3: Verify Metrics (10 minutes)

### Step 3.1: Build and Run Services

```bash
cd rust
cargo build --release

# Terminal 1
cd market-data
cargo run --release

# Terminal 2
cd risk-manager
cargo run --release

# Terminal 3
cd execution-engine
cargo run --release

# Terminal 4
cd signal-bridge
cargo run --release
```

### Step 3.2: Check Metrics Endpoints

```bash
# Market Data metrics
curl http://localhost:9090/metrics | grep market_data

# Signal Bridge metrics
curl http://localhost:9091/metrics | grep signal_bridge

# Risk Manager metrics
curl http://localhost:9092/metrics | grep risk_manager

# Execution Engine metrics
curl http://localhost:9093/metrics | grep execution_engine
```

Expected output:
```
# HELP market_data_websocket_latency_us WebSocket message processing latency in microseconds
# TYPE market_data_websocket_latency_us histogram
market_data_websocket_latency_us_bucket{exchange="alpaca",message_type="trade",symbol="AAPL",le="1"} 0
market_data_websocket_latency_us_bucket{exchange="alpaca",message_type="trade",symbol="AAPL",le="5"} 12
market_data_websocket_latency_us_bucket{exchange="alpaca",message_type="trade",symbol="AAPL",le="10"} 45
...
```

---

## Phase 4: Deploy Monitoring Stack (30 minutes)

### Step 4.1: Deploy Prometheus

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

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

Run Prometheus:

```bash
docker run -d \
  --name prometheus \
  -p 9999:9090 \
  -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

Access Prometheus UI: http://localhost:9999

### Step 4.2: Deploy Grafana

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana
```

Access Grafana: http://localhost:3000 (admin/admin)

### Step 4.3: Add Prometheus Data Source in Grafana

1. Go to Configuration > Data Sources
2. Add Prometheus
3. URL: `http://host.docker.internal:9999`
4. Click "Save & Test"

### Step 4.4: Import Dashboard

1. Go to Dashboards > Import
2. Upload `docs/monitoring/grafana-dashboard.json` (create this from template)
3. Select Prometheus data source
4. Click Import

---

## Phase 5: Configure Alerts (20 minutes)

### Step 5.1: Create Alert Rules

Create `monitoring/alerts/trading_system.yml`:

```yaml
groups:
  - name: trading_critical
    interval: 10s
    rules:
      - alert: CircuitBreakerTriggered
        expr: risk_manager_risk_failures_total{failure_type="circuit_breaker_triggered"} > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "CRITICAL: Circuit breaker triggered"

      - alert: HighOrderLatency
        expr: histogram_quantile(0.99, rate(execution_engine_order_submission_latency_us_bucket[5m])) > 5000
        for: 5m
        labels:
          severity: high
        annotations:
          summary: "High order latency (p99 > 5ms)"
```

### Step 5.2: Update Prometheus Config

Add to `monitoring/prometheus.yml`:

```yaml
rule_files:
  - "/etc/prometheus/alerts/trading_system.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

---

## Testing Checklist

- [ ] All services start successfully
- [ ] Metrics endpoints respond on ports 9090-9093
- [ ] Prometheus scrapes all targets (check Status > Targets)
- [ ] Grafana displays metrics in dashboard
- [ ] Test alert triggers (manually trigger circuit breaker)
- [ ] Verify log output is JSON formatted
- [ ] Check latency metrics show realistic values (<100μs p99)
- [ ] Verify business metrics update (positions, P&L)

---

## Troubleshooting

### Issue: Metrics endpoint returns 404

**Solution**: Ensure metrics server is started before service:

```rust
// Start metrics server BEFORE service initialization
tokio::spawn(async {
    metrics::serve_metrics(9090).await;
});

// Give it time to bind
tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
```

### Issue: Prometheus can't scrape targets

**Solution**: Check firewall rules and Docker network:

```bash
# Test from Prometheus container
docker exec -it prometheus wget http://host.docker.internal:9090/metrics -O -
```

### Issue: High memory usage

**Solution**: Limit histogram buckets and metric cardinality. Avoid high-cardinality labels (e.g., don't use `order_id` as label).

---

## Next Steps

1. ✅ Complete Phase 1-3 (Core metrics)
2. Deploy monitoring stack (Phase 4)
3. Configure alerts (Phase 5)
4. Add distributed tracing (OpenTelemetry)
5. Set up log aggregation (Elasticsearch/Kibana)
6. Create runbooks for each alert
7. Schedule weekly SLO review meetings

---

**Document Version**: 1.0
**Last Updated**: 2025-10-21
**Author**: Analyst Agent (Hive Mind Swarm)
