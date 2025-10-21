# Monitoring & Observability - Rust Algorithm Trading System

## Overview

This directory contains comprehensive monitoring and observability specifications for the py_rt (Python-Rust Trading System). The monitoring strategy focuses on ensuring system reliability, performance tracking, and rapid incident response for a high-frequency algorithmic trading platform.

## Documents

### 1. [Monitoring Specification](./monitoring-specification.md) ⭐
**Complete monitoring architecture and metrics catalog**

- **54 metrics definitions** across 5 categories:
  - Latency metrics (WebSocket, order submission, ML inference, risk checks)
  - Throughput metrics (messages/sec, orders/sec, signals/sec)
  - Error rate metrics (failures, rejections, disconnections)
  - Business metrics (P&L, positions, slippage, fill rates)
  - System resource metrics (CPU, memory, queue depth)

- **15 alert rules** with P0/P1/P2 prioritization
- **Service Level Objectives (SLOs)**:
  - 99.95% availability for critical services
  - p99 order latency < 100μs
  - p99 market data processing < 10μs

- **Dashboard layouts** for Grafana
- **Log aggregation strategy** (Elasticsearch/Kibana)
- **Operational runbooks** for incident response

### 2. [Implementation Guide](./implementation-guide.md) 🚀
**Step-by-step implementation instructions**

- **Phase 1**: Add core dependencies (15 minutes)
  - Prometheus crate integration
  - Metrics server setup
  - Common metrics module

- **Phase 2**: Instrument services (1 hour per service)
  - Market Data Service (port 9090)
  - Signal Bridge (port 9091)
  - Risk Manager (port 9092)
  - Execution Engine (port 9093)

- **Phase 3**: Verify metrics (10 minutes)
  - Test endpoints with curl
  - Validate metric formats

- **Phase 4**: Deploy monitoring stack (30 minutes)
  - Prometheus deployment
  - Grafana deployment
  - Data source configuration

- **Phase 5**: Configure alerts (20 minutes)
  - Alert rule definitions
  - Alertmanager setup
  - Notification channels

## Quick Start

### 1. Read the Specification
Start with [monitoring-specification.md](./monitoring-specification.md) to understand:
- What metrics we're tracking and why
- SLO targets and alert thresholds
- Architecture and design decisions

### 2. Follow the Implementation Guide
Use [implementation-guide.md](./implementation-guide.md) to:
- Add Prometheus metrics to services
- Deploy monitoring infrastructure
- Configure alerts and dashboards

### 3. Deploy with Docker Compose

```bash
cd monitoring
docker-compose up -d
```

This starts:
- Prometheus (http://localhost:9999)
- Grafana (http://localhost:3000, admin/admin)
- Alertmanager (http://localhost:9093)

### 4. Access Dashboards

**Prometheus UI**: http://localhost:9999
- Query metrics: `execution_engine_order_submission_latency_us`
- Check targets: Status > Targets

**Grafana**: http://localhost:3000
- Import dashboards from `grafana-dashboards/`
- View real-time trading metrics

## Key Metrics to Monitor

### Critical Path Latency
```promql
# Order submission (target: p99 < 100μs)
histogram_quantile(0.99, rate(execution_engine_order_submission_latency_us_bucket[5m]))

# Market data processing (target: p99 < 10μs)
histogram_quantile(0.99, rate(market_data_websocket_latency_us_bucket[5m]))

# Risk checks (target: p95 < 500μs)
histogram_quantile(0.95, rate(risk_manager_pretrade_check_latency_us_bucket[5m]))
```

### Business Metrics
```promql
# Current P&L
sum(trading_unrealized_pnl_usd)

# Order success rate
100 * (
  rate(execution_engine_orders_submitted_total{status="success"}[5m])
  /
  rate(execution_engine_orders_submitted_total[5m])
)

# Open positions
trading_open_positions_count
```

### Error Rates
```promql
# API failures
rate(execution_engine_api_failures_total[5m])

# Risk check failures
rate(risk_manager_risk_failures_total[5m])

# WebSocket disconnections
rate(market_data_websocket_connection_failures_total[5m])
```

## Alert Severity Levels

### P0 - Critical (Immediate Action)
- Circuit breaker triggered
- Max daily loss exceeded
- WebSocket disconnected
- Execution API down
- Memory leak detected

**Response Time**: Immediate (< 5 minutes)

### P1 - High Priority (Respond within 15 minutes)
- High order latency (p99 > 5ms)
- High slippage (p95 > 50 bps)
- ML inference failures
- Risk check failures
- Low fill rate
- API rate limit hit

**Response Time**: 15 minutes

### P2 - Medium Priority (Daily review)
- Elevated market data latency
- High CPU usage
- ZMQ queue backlog
- Retry escalation
- Low message throughput

**Response Time**: Same business day

## Service Ports

| Service | Metrics Port | Process Port | Health Check |
|---------|-------------|--------------|--------------|
| Market Data | 9090 | 5555 (ZMQ) | `curl localhost:9090/metrics` |
| Signal Bridge | 9091 | 5556 (ZMQ) | `curl localhost:9091/metrics` |
| Risk Manager | 9092 | 5557 (ZMQ) | `curl localhost:9092/metrics` |
| Execution Engine | 9093 | 5558 (ZMQ) | `curl localhost:9093/metrics` |

## Troubleshooting

### Metrics endpoint returns 404
Check that metrics server started before service initialization:
```rust
tokio::spawn(async {
    metrics::serve_metrics(9090).await;
});
tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
```

### Prometheus can't scrape targets
Verify services are running:
```bash
curl localhost:9090/metrics  # Market Data
curl localhost:9091/metrics  # Signal Bridge
curl localhost:9092/metrics  # Risk Manager
curl localhost:9093/metrics  # Execution Engine
```

### High memory usage
Review metric cardinality. Avoid high-cardinality labels:
```rust
// ❌ BAD - order_id creates millions of time series
METRIC.with_label_values(&[&order_id, "alpaca"]).observe(latency);

// ✅ GOOD - Low cardinality
METRIC.with_label_values(&["market", "alpaca"]).observe(latency);
```

## Implementation Status

✅ **Completed**:
- Monitoring specification document
- Implementation guide
- Prometheus configuration
- Alert rule definitions
- Service port allocation

❌ **TODO**:
- [ ] Add `prometheus` dependency to `common/Cargo.toml`
- [ ] Create `common/src/metrics.rs`
- [ ] Instrument all 4 services (market-data, signal-bridge, risk-manager, execution-engine)
- [ ] Deploy Prometheus
- [ ] Deploy Grafana
- [ ] Create Grafana dashboards
- [ ] Configure Alertmanager
- [ ] Set up log aggregation (Elasticsearch/Kibana)
- [ ] Add distributed tracing (OpenTelemetry/Jaeger)

## Next Steps

1. **Week 1**: Implement Phase 1-3 (core metrics in all services)
2. **Week 2**: Deploy monitoring stack and configure alerts
3. **Week 3**: Create Grafana dashboards
4. **Week 4**: Set up log aggregation
5. **Ongoing**: Add distributed tracing and advanced observability

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [Rust `tracing` Crate](https://docs.rs/tracing/)
- [OpenTelemetry Rust](https://github.com/open-telemetry/opentelemetry-rust)
- [Google SRE Book - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

## Support

For questions or issues with monitoring implementation:
- Review the [Implementation Guide](./implementation-guide.md)
- Check the [Troubleshooting](#troubleshooting) section
- Refer to the [Monitoring Specification](./monitoring-specification.md) for design details

---

**Version**: 1.0
**Last Updated**: 2025-10-21
**Maintained by**: Trading Platform Team
**Status**: Ready for Implementation
