# Monitoring and Observability

This directory contains configuration for monitoring the Rust Algorithm Trading System using Prometheus and Grafana.

## Overview

The monitoring stack provides:
- Real-time metrics collection (Prometheus)
- Visual dashboards (Grafana)
- Alerting for critical events
- Performance tracking
- Service health monitoring

## Components

### Prometheus
- **Port**: 9090
- **Purpose**: Metrics collection and storage
- **Retention**: 30 days
- **Scrape Interval**: 5-15 seconds

### Grafana
- **Port**: 3000
- **Purpose**: Metrics visualization
- **Default User**: admin
- **Password**: Set in `.env` file

## Quick Start

### Using Docker Compose

Monitoring services are included in the main docker-compose.yml:

```bash
# Start all services including monitoring
docker-compose -f docker/docker-compose.yml up -d

# Access Prometheus: http://localhost:9090
# Access Grafana: http://localhost:3000
```

### Standalone Prometheus

```bash
# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Copy configuration
cp /path/to/monitoring/prometheus.yml ./prometheus.yml

# Start Prometheus
./prometheus --config.file=prometheus.yml
```

## Configuration Files

### prometheus.yml
Main Prometheus configuration defining:
- Scrape targets (all microservices)
- Scrape intervals
- Alert rules
- External labels

### alerts.yml
Alert rules for:
- Service downtime
- High error rates
- Resource exhaustion (CPU, memory, disk)
- Trading-specific alerts (order failures, risk breaches)
- API performance degradation

### grafana-datasources.yml
Grafana data source configuration:
- Connects Grafana to Prometheus
- Sets default query timeout
- Configures time intervals

### grafana-dashboard.json
Pre-built dashboard with panels for:
- Service status overview
- Request rates and latency
- CPU and memory usage
- Trading metrics (orders, positions, risk)
- Error rates by service

## Metrics Exposed

### System Metrics

```promql
# Service uptime (1 = up, 0 = down)
up

# CPU usage per service
rate(process_cpu_seconds_total[5m])

# Memory usage per service (bytes)
process_resident_memory_bytes

# Request rate
rate(http_requests_total[5m])

# Request latency (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Trading Metrics

```promql
# Order execution rate
rate(orders_executed_total[5m])

# Order failure rate
rate(orders_failed_total[5m])

# Active positions
active_positions_total

# Risk exposure
current_risk_exposure

# Risk limit utilization (percentage)
risk_limit_utilization
```

### Error Metrics

```promql
# HTTP error rate (5xx errors)
rate(http_requests_total{status=~"5.."}[5m])

# Strategy execution errors
rate(strategy_execution_errors_total[5m])

# Market data staleness
time() - market_data_last_update_timestamp
```

## Alerting

### Alert Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| critical | System down or data loss risk | Immediate |
| warning | Performance degradation | Within 15 minutes |
| info | General notifications | Review daily |

### Configured Alerts

#### Service Availability
- **ServiceDown**: Service unreachable for >1 minute
- **MarketDataStale**: No updates for >60 seconds

#### Performance
- **HighAPILatency**: p95 latency >1 second
- **HighCPUUsage**: CPU >80% for 10 minutes
- **HighMemoryUsage**: Memory >800MB for 5 minutes

#### Trading
- **OrderExecutionFailureRate**: >0.1 failures/sec
- **RiskLimitBreach**: Any risk limit violation
- **StrategyExecutionErrors**: Any strategy errors

#### Resources
- **LowDiskSpace**: <10% free space

### Alert Destinations

Configure alert destinations in `prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - 'alertmanager:9093'
```

## Grafana Dashboards

### Trading System Overview

**Panels:**
1. Service Status (stat panel)
2. Total Request Rate (graph)
3. CPU Usage by Service (graph)
4. Memory Usage by Service (graph)
5. Request Latency p95 (graph)
6. Order Execution Rate (graph)
7. Active Positions (stat panel)
8. Risk Metrics (stat panel)
9. Error Rates (graph)

### Importing the Dashboard

1. Access Grafana at http://localhost:3000
2. Login with admin credentials
3. Navigate to Dashboards → Import
4. Upload `grafana-dashboard.json`
5. Select Prometheus data source
6. Click Import

### Creating Custom Dashboards

1. Go to Dashboards → New Dashboard
2. Add Panel
3. Select metric from Prometheus
4. Configure visualization
5. Save dashboard

**Example Query:**
```promql
# Request rate with 5-minute average
rate(http_requests_total{service="api_gateway"}[5m])
```

## Common Queries

### Service Health

```promql
# Check which services are up
up{job=~".*_service"}

# Services that were down in last hour
changes(up[1h]) > 0
```

### Performance Analysis

```promql
# Top 5 slowest endpoints
topk(5, histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])))

# Request success rate
sum(rate(http_requests_total{status=~"2.."}[5m])) /
sum(rate(http_requests_total[5m]))
```

### Resource Utilization

```promql
# Memory usage trend
avg_over_time(process_resident_memory_bytes[1h])

# CPU saturation
avg(rate(process_cpu_seconds_total[5m])) by (service)
```

### Trading Analytics

```promql
# Order success rate
sum(rate(orders_executed_total[5m])) /
(sum(rate(orders_executed_total[5m])) +
 sum(rate(orders_failed_total[5m])))

# Average position hold time
avg(position_duration_seconds)
```

## Troubleshooting

### Prometheus Not Scraping Targets

1. **Check Prometheus targets page**: http://localhost:9090/targets
2. **Verify service is exposing metrics**:
   ```bash
   curl http://localhost:5555/metrics
   ```
3. **Check network connectivity**:
   ```bash
   docker exec trading_prometheus wget -O- http://market_data_service:5555/metrics
   ```

### Missing Metrics in Grafana

1. **Test query in Prometheus**: http://localhost:9090/graph
2. **Check data source configuration** in Grafana
3. **Verify time range** matches data availability
4. **Check metric names** are correct

### High Cardinality Warnings

Reduce label combinations:
- Avoid user IDs in labels
- Use recording rules for complex queries
- Aggregate high-cardinality metrics

### Performance Issues

1. **Increase scrape interval** for less critical services
2. **Reduce retention period** if storage is limited
3. **Use recording rules** for expensive queries:
   ```yaml
   groups:
     - name: example
       interval: 30s
       rules:
         - record: job:request_rate:5m
           expr: rate(http_requests_total[5m])
   ```

## Recording Rules

Add to `prometheus.yml` for pre-computed metrics:

```yaml
rule_files:
  - 'recording_rules.yml'
```

**Example recording_rules.yml:**
```yaml
groups:
  - name: trading_aggregations
    interval: 30s
    rules:
      - record: service:request_rate:5m
        expr: sum(rate(http_requests_total[5m])) by (service)

      - record: service:error_rate:5m
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)

      - record: service:latency_p95:5m
        expr: histogram_quantile(0.95,
          sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le))
```

## Production Best Practices

### 1. High Availability

```yaml
# Configure Prometheus with remote storage
remote_write:
  - url: "https://your-remote-storage/api/v1/write"
    basic_auth:
      username: "user"
      password: "pass"
```

### 2. Security

- Enable HTTPS for Grafana
- Use authentication for Prometheus
- Restrict network access
- Encrypt data at rest

### 3. Retention Policy

```yaml
# Adjust retention based on needs
storage:
  tsdb:
    retention.time: 30d
    retention.size: 10GB
```

### 4. Backup

```bash
# Backup Prometheus data
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz /prometheus/data

# Backup Grafana dashboards
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/search?type=dash-db | \
  jq -r '.[] | .uid' | \
  xargs -I {} curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/dashboards/uid/{} > dashboards-backup.json
```

### 5. Alertmanager Integration

**alertmanager.yml:**
```yaml
route:
  receiver: 'team-email'
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@example.com'
        from: 'prometheus@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'password'
```

## Monitoring Checklist

- [ ] All services exposing metrics on `/metrics` endpoint
- [ ] Prometheus scraping all targets successfully
- [ ] Grafana connected to Prometheus
- [ ] Dashboards imported and displaying data
- [ ] Alerts configured and tested
- [ ] Alert destinations configured (email, Slack, PagerDuty)
- [ ] Resource limits set appropriately
- [ ] Retention policy configured
- [ ] Backup strategy in place
- [ ] Documentation updated

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Tutorials](https://grafana.com/tutorials/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alerting Best Practices](https://prometheus.io/docs/practices/alerting/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
