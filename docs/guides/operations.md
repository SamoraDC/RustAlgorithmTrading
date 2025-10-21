# Operations Guide

Day-to-day operational procedures for the py_rt algorithmic trading system.

## Table of Contents

- [Service Management](#service-management)
- [Health Monitoring](#health-monitoring)
- [Log Analysis](#log-analysis)
- [Metrics and Dashboards](#metrics-and-dashboards)
- [Backup and Recovery](#backup-and-recovery)
- [Common Operational Tasks](#common-operational-tasks)
- [Emergency Procedures](#emergency-procedures)

## Service Management

### Starting Services

#### Native Deployment (systemd)

```bash
# Start individual services
sudo systemctl start trading-market-data
sudo systemctl start trading-risk-manager
sudo systemctl start trading-execution-engine
sudo systemctl start trading-signal-bridge

# Start all services with automated script
cd /opt/RustAlgorithmTrading
./scripts/start_trading_system.sh

# Enable auto-start on boot
sudo systemctl enable trading-market-data
sudo systemctl enable trading-risk-manager
sudo systemctl enable trading-execution-engine
sudo systemctl enable trading-signal-bridge
```

#### Docker Deployment

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Start specific service
docker-compose -f docker/docker-compose.yml up -d market_data_service

# View startup logs
docker-compose -f docker/docker-compose.yml logs -f
```

### Stopping Services

#### Graceful Shutdown

**Native Deployment**:
```bash
# Stop services in reverse order (opposite of startup)
sudo systemctl stop trading-signal-bridge
sleep 2
sudo systemctl stop trading-execution-engine
sleep 2
sudo systemctl stop trading-risk-manager
sleep 2
sudo systemctl stop trading-market-data

# Or use automated script
./scripts/stop_trading_system.sh
```

**Docker Deployment**:
```bash
# Graceful shutdown (sends SIGTERM)
docker-compose -f docker/docker-compose.yml down

# Force stop (sends SIGKILL after timeout)
docker-compose -f docker/docker-compose.yml down --timeout 30
```

#### Emergency Shutdown

For immediate system halt (use only in emergencies):

```bash
# Native deployment
./scripts/emergency_stop.sh

# Docker deployment
docker-compose -f docker/docker-compose.yml kill
```

### Restarting Services

#### Individual Service Restart

**Native Deployment**:
```bash
# Restart specific service
sudo systemctl restart trading-market-data

# Reload configuration without restart
sudo systemctl reload trading-market-data
```

**Docker Deployment**:
```bash
# Restart specific service
docker-compose -f docker/docker-compose.yml restart market_data_service

# Restart with rebuild
docker-compose -f docker/docker-compose.yml up -d --build market_data_service
```

#### Full System Restart

```bash
# Native deployment
./scripts/restart_trading_system.sh

# Docker deployment
docker-compose -f docker/docker-compose.yml restart
```

### Service Status

#### Check Running Status

**Native Deployment**:
```bash
# Check all trading services
sudo systemctl status trading-*

# Check specific service
sudo systemctl status trading-market-data

# Check if process is running
ps aux | grep market-data
```

**Docker Deployment**:
```bash
# Check all containers
docker-compose -f docker/docker-compose.yml ps

# Check specific container
docker inspect trading_market_data

# Check container health
docker ps --filter "name=trading_" --format "table {{.Names}}\t{{.Status}}"
```

## Health Monitoring

### Automated Health Checks

#### System Health Script

Run the automated health check:

```bash
# Comprehensive health check
./scripts/health_check.sh

# Output example:
# ✓ Market Data Service: HEALTHY (uptime: 2d 4h)
# ✓ Risk Manager: HEALTHY (uptime: 2d 4h)
# ✓ Execution Engine: HEALTHY (uptime: 2d 4h)
# ✓ Signal Bridge: HEALTHY (uptime: 2d 4h)
# ✓ ZeroMQ Connections: 4/4 active
# ✓ Prometheus Metrics: 1234 data points
# ⚠ Warning: High memory usage on execution-engine (78%)
```

#### Service-Specific Health Checks

**Market Data Service**:
```bash
# Check WebSocket connection
curl -s http://localhost:9090/metrics | grep market_data_websocket_connected
# Should return: market_data_websocket_connected 1

# Check message rate
curl -s http://localhost:9090/metrics | grep market_data_messages_received_total
```

**Risk Manager**:
```bash
# Check risk calculation status
curl -s http://localhost:9090/metrics | grep risk_checks_performed_total

# Check circuit breaker status
curl -s http://localhost:9090/metrics | grep risk_circuit_breaker_active
# Should return: risk_circuit_breaker_active 0
```

**Execution Engine**:
```bash
# Check order submission rate
curl -s http://localhost:9090/metrics | grep execution_orders_submitted_total

# Check fill rate
curl -s http://localhost:9090/metrics | grep execution_orders_filled_total
```

### Real-time Monitoring

#### Watch Service Metrics

```bash
# Monitor all metrics in real-time
watch -n 5 'curl -s http://localhost:9090/metrics | grep -E "(trading_|market_|risk_|execution_)"'

# Monitor specific metric
watch -n 1 'curl -s http://localhost:9090/metrics | grep market_data_latency_seconds'
```

#### ZeroMQ Connection Monitor

```bash
# Monitor ZeroMQ message flow
python scripts/monitor_zmq.py --port 5555 --interval 1

# Output:
# Market Data: 127 msgs/sec, avg latency: 0.45ms
# Signals: 45 msgs/sec, avg latency: 1.2ms
# Risk Checks: 45 msgs/sec, avg latency: 0.8ms
# Executions: 12 msgs/sec, avg latency: 2.1ms
```

## Log Analysis

### Log Locations

**Native Deployment**:
- Market Data: `/opt/RustAlgorithmTrading/logs/market_data.log`
- Risk Manager: `/opt/RustAlgorithmTrading/logs/risk_manager.log`
- Execution Engine: `/opt/RustAlgorithmTrading/logs/execution_engine.log`
- Signal Bridge: `/opt/RustAlgorithmTrading/logs/signal_bridge.log`
- System Logs: `/var/log/syslog` (via journalctl)

**Docker Deployment**:
- Container logs: `docker logs <container_name>`
- Persistent logs: Mounted volumes in `/var/lib/docker/volumes/`

### Viewing Logs

#### Real-time Log Streaming

**Native Deployment**:
```bash
# View systemd logs
sudo journalctl -u trading-market-data -f

# View file logs
tail -f /opt/RustAlgorithmTrading/logs/market_data.log

# View all trading logs combined
tail -f /opt/RustAlgorithmTrading/logs/*.log
```

**Docker Deployment**:
```bash
# Follow logs for all services
docker-compose -f docker/docker-compose.yml logs -f

# Follow specific service
docker-compose -f docker/docker-compose.yml logs -f market_data_service

# Follow with timestamps
docker-compose -f docker/docker-compose.yml logs -f --timestamps
```

#### Historical Log Analysis

```bash
# View logs from last hour
sudo journalctl -u trading-market-data --since "1 hour ago"

# View logs from specific time range
sudo journalctl -u trading-market-data --since "2025-10-21 09:00" --until "2025-10-21 17:00"

# Search for errors
sudo journalctl -u trading-* --priority=err --since today

# Export logs to file
sudo journalctl -u trading-market-data --since "1 day ago" > market_data_last_24h.log
```

#### Log Filtering and Searching

```bash
# Search for specific errors
grep -i "error\|panic\|fatal" /opt/RustAlgorithmTrading/logs/market_data.log

# Find WebSocket connection issues
grep "websocket.*disconnect\|websocket.*error" /opt/RustAlgorithmTrading/logs/market_data.log

# Find order execution failures
grep "order.*failed\|order.*rejected" /opt/RustAlgorithmTrading/logs/execution_engine.log

# Find risk violations
grep "risk.*violation\|circuit.*breaker" /opt/RustAlgorithmTrading/logs/risk_manager.log

# Count errors by type
grep -o "Error: [^:]*" /opt/RustAlgorithmTrading/logs/*.log | sort | uniq -c | sort -rn
```

### Log Rotation

Logs are automatically rotated via logrotate:

```bash
# Check logrotate configuration
cat /etc/logrotate.d/trading-system

# Manually trigger rotation
sudo logrotate -f /etc/logrotate.d/trading-system

# View rotated logs
ls -lh /opt/RustAlgorithmTrading/logs/market_data.log*
```

## Metrics and Dashboards

### Prometheus Metrics

Access Prometheus at: http://localhost:9090

#### Key Metrics to Monitor

**System Performance**:
```promql
# Message processing rate
rate(trading_messages_processed_total[5m])

# Processing latency (p99)
histogram_quantile(0.99, trading_processing_latency_seconds_bucket)

# Memory usage
process_resident_memory_bytes

# CPU usage
rate(process_cpu_seconds_total[5m])
```

**Trading Operations**:
```promql
# Order submission rate
rate(execution_orders_submitted_total[5m])

# Order fill rate
rate(execution_orders_filled_total[5m]) / rate(execution_orders_submitted_total[5m])

# Current open positions
trading_open_positions

# Total P&L
trading_realized_pnl_total + trading_unrealized_pnl
```

**Risk Metrics**:
```promql
# Risk check failures
rate(risk_checks_failed_total[5m])

# Position utilization
trading_position_size / risk_max_position_size

# Circuit breaker activations
increase(risk_circuit_breaker_activations_total[1d])
```

### Grafana Dashboards

Access Grafana at: http://localhost:3000 (default credentials: admin/admin)

#### Pre-configured Dashboards

1. **Trading System Overview**
   - System health status
   - Service uptime
   - Message throughput
   - Error rates
   - Resource utilization

2. **Market Data Performance**
   - WebSocket connection status
   - Message latency distribution
   - Quote/trade message rates
   - Data feed lag

3. **Order Execution Metrics**
   - Order submission rate
   - Fill rate and slippage
   - Execution latency
   - Order book depth

4. **Risk Management Dashboard**
   - Current positions and exposure
   - P&L (realized and unrealized)
   - Risk limit utilization
   - Circuit breaker status
   - VaR and drawdown metrics

5. **System Resources**
   - CPU usage per service
   - Memory usage and GC activity
   - Network I/O
   - Disk I/O

#### Creating Custom Dashboards

```bash
# Import dashboard from JSON
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana-dashboards/custom-dashboard.json

# Export existing dashboard
curl http://localhost:3000/api/dashboards/uid/trading-overview > backup-dashboard.json
```

### Alerting

#### Configure Alert Rules

Edit `monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: trading_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(trading_errors_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      # Circuit breaker triggered
      - alert: CircuitBreakerActive
        expr: risk_circuit_breaker_active == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Trading circuit breaker activated"
          description: "System has halted trading due to risk limits"

      # WebSocket disconnected
      - alert: MarketDataDisconnected
        expr: market_data_websocket_connected == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Market data feed disconnected"
```

#### Alert Notification Channels

Configure notification endpoints in `monitoring/grafana/provisioning/notifiers/`:

```yaml
# Slack notifications
notifiers:
  - name: slack-alerts
    type: slack
    uid: slack-trading
    settings:
      url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
      recipient: '#trading-alerts'

# Email notifications
  - name: email-alerts
    type: email
    uid: email-trading
    settings:
      addresses: alerts@example.com
```

## Backup and Recovery

### Data Backup

#### Automated Backup Script

```bash
# Run daily backup
./scripts/backup_system.sh

# Backup locations
ls -lh /opt/RustAlgorithmTrading/backups/
# - configs/      (configuration files)
# - logs/         (compressed log archives)
# - data/         (position state, P&L data)
# - models/       (ML models)
```

#### Manual Backup

```bash
# Backup configuration files
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Backup trading data
tar -czf data-backup-$(date +%Y%m%d).tar.gz data/

# Copy to remote storage
scp *-backup-*.tar.gz backup-server:/backups/trading/
```

### State Recovery

#### Restore from Backup

```bash
# Stop trading system
./scripts/stop_trading_system.sh

# Restore configuration
tar -xzf config-backup-20251021.tar.gz

# Restore data
tar -xzf data-backup-20251021.tar.gz

# Verify configuration
./scripts/verify_config.sh

# Restart system
./scripts/start_trading_system.sh
```

#### Position Reconciliation

After downtime, reconcile positions with exchange:

```bash
# Run position reconciliation script
python scripts/reconcile_positions.py

# Output:
# Reconciling positions with Alpaca...
# Local positions: 5
# Exchange positions: 5
# Discrepancies: 0
# Status: OK
```

## Common Operational Tasks

### Update Trading Symbols

```bash
# Edit configuration
nano config/system.json

# Update symbols list
"symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

# Restart market data service
sudo systemctl restart trading-market-data

# Verify new symbols
curl -s http://localhost:9090/metrics | grep market_data_symbols
```

### Adjust Risk Limits

```bash
# Edit risk limits
nano config/risk_limits.toml

# Update limits (example: reduce max position size)
max_shares = 500
max_notional_per_position = 5000.0

# Restart risk manager
sudo systemctl restart trading-risk-manager

# Verify new limits
curl -s http://localhost:9090/metrics | grep risk_max_position_size
```

### Deploy New ML Model

```bash
# Copy new model to models directory
cp ~/new_model.onnx /opt/RustAlgorithmTrading/models/trading_model_v2.onnx

# Update configuration
nano config/system.json
# Change: "model_path": "models/trading_model_v2.onnx"

# Restart signal bridge
sudo systemctl restart trading-signal-bridge

# Verify model loaded
sudo journalctl -u trading-signal-bridge -n 50 | grep "Model loaded"
```

### Manual Trade Execution

```bash
# Use CLI tool for manual trades
python scripts/manual_trade.py \
  --symbol AAPL \
  --action buy \
  --quantity 10 \
  --order-type market

# Check order status
python scripts/check_order.py --order-id abc123
```

### Clear Market Data Cache

```bash
# Stop market data service
sudo systemctl stop trading-market-data

# Clear cache
rm -rf /opt/RustAlgorithmTrading/cache/market_data/*

# Restart service
sudo systemctl start trading-market-data
```

## Emergency Procedures

### Emergency Stop (Kill Switch)

Immediately halt all trading activity:

```bash
# Execute emergency stop
./scripts/emergency_stop.sh

# This will:
# 1. Activate circuit breaker
# 2. Cancel all open orders
# 3. Stop all services
# 4. Send alert notifications
```

### Circuit Breaker Manual Activation

```bash
# Activate circuit breaker via API
curl -X POST http://localhost:8080/api/v1/circuit-breaker/activate

# Deactivate after issue resolved
curl -X POST http://localhost:8080/api/v1/circuit-breaker/deactivate
```

### Liquidate All Positions

In case of emergency, close all positions:

```bash
# Run liquidation script
python scripts/liquidate_positions.py --confirm

# This will:
# 1. Retrieve all open positions
# 2. Submit market orders to close
# 3. Wait for fills
# 4. Report final P&L
```

### Restore from Critical Failure

```bash
# 1. Stop all services
./scripts/stop_trading_system.sh

# 2. Check for data corruption
./scripts/verify_data_integrity.sh

# 3. Restore from last known good backup
./scripts/restore_from_backup.sh --date 2025-10-21 --time 14:00

# 4. Reconcile with exchange
python scripts/reconcile_positions.py

# 5. Restart system in safe mode (no auto-trading)
./scripts/start_trading_system.sh --safe-mode

# 6. Verify system health
./scripts/health_check.sh

# 7. Resume normal operation
curl -X POST http://localhost:8080/api/v1/trading/enable
```

### Incident Response Checklist

When issues occur:

- [ ] Activate circuit breaker to halt trading
- [ ] Document the incident (time, symptoms, metrics)
- [ ] Capture logs and metrics snapshot
- [ ] Assess position and P&L impact
- [ ] Determine root cause
- [ ] Apply fix or workaround
- [ ] Test in safe mode
- [ ] Resume trading with monitoring
- [ ] Conduct post-mortem analysis
- [ ] Update runbooks and documentation

## Routine Maintenance Schedule

### Daily Tasks

- [ ] Review overnight logs for errors
- [ ] Check system health metrics
- [ ] Verify position reconciliation
- [ ] Review P&L and risk metrics
- [ ] Monitor circuit breaker activations

### Weekly Tasks

- [ ] Analyze performance trends
- [ ] Review and optimize trading strategies
- [ ] Update ML models if needed
- [ ] Check backup integrity
- [ ] Review alert thresholds

### Monthly Tasks

- [ ] Comprehensive system audit
- [ ] Security updates and patches
- [ ] Disk space cleanup
- [ ] Review and update documentation
- [ ] Performance tuning and optimization

## Reference Commands

### Quick Reference Table

| Task | Command |
|------|---------|
| Start all services | `./scripts/start_trading_system.sh` |
| Stop all services | `./scripts/stop_trading_system.sh` |
| Check health | `./scripts/health_check.sh` |
| View live logs | `tail -f logs/*.log` |
| Check metrics | `curl localhost:9090/metrics` |
| Emergency stop | `./scripts/emergency_stop.sh` |
| Backup data | `./scripts/backup_system.sh` |
| Reconcile positions | `python scripts/reconcile_positions.py` |

## Support

For operational issues:
- Runbooks: `/opt/RustAlgorithmTrading/docs/runbooks/`
- GitHub Issues: https://github.com/SamoraDC/RustAlgorithmTrading/issues
- On-call: Check PagerDuty escalation policy

## Related Documentation

- [Deployment Guide](deployment.md) - Initial system deployment
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [Monitoring Guide](monitoring.md) - Detailed monitoring configuration
- [Security Guide](security.md) - Security best practices
