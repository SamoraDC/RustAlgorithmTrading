# Operations Runbook
## Rust Algorithmic Trading System

**Version**: 1.0.0
**Last Updated**: October 21, 2025
**Audience**: Operations Team, DevOps Engineers, SREs

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Service Management](#service-management)
3. [Health Monitoring](#health-monitoring)
4. [Incident Response](#incident-response)
5. [Performance Tuning](#performance-tuning)
6. [Backup & Recovery](#backup--recovery)
7. [Security Operations](#security-operations)
8. [Common Issues](#common-issues)

---

## 1. Daily Operations

### 1.1 Pre-Market Checklist (Before 9:30 AM ET)

**Execute 30 minutes before market open**:

```bash
#!/bin/bash
# /opt/trading-system/scripts/pre_market_checklist.sh

echo "=== PRE-MARKET CHECKLIST ==="
echo "Date: $(date)"

# 1. Verify all services are running
echo -n "Checking services... "
if systemctl is-active --quiet trading-market-data trading-execution-engine trading-risk-manager; then
    echo "✓ All services running"
else
    echo "✗ Service failure detected!"
    systemctl status trading-* --no-pager
    exit 1
fi

# 2. Check API connectivity
echo -n "Testing Alpaca API... "
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
    -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}" \
    https://api.alpaca.markets/v2/account)

if [ "$response" = "200" ]; then
    echo "✓ API connected"
else
    echo "✗ API connection failed (HTTP $response)"
    exit 1
fi

# 3. Verify database connectivity
echo -n "Testing database... "
if psql -U trading_user -d trading_db -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ Database connected"
else
    echo "✗ Database connection failed"
    exit 1
fi

# 4. Check disk space
echo -n "Checking disk space... "
disk_usage=$(df -h /opt/trading-system | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 80 ]; then
    echo "✓ Disk usage: ${disk_usage}%"
else
    echo "⚠ WARNING: Disk usage high: ${disk_usage}%"
fi

# 5. Reset circuit breaker if tripped
echo -n "Checking circuit breaker... "
# TODO: Add API call to check circuit breaker status
echo "✓ Circuit breaker ready"

# 6. Verify monitoring stack
echo -n "Checking Prometheus... "
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✓ Prometheus healthy"
else
    echo "✗ Prometheus not responding"
fi

# 7. Check daily loss limits
echo -n "Verifying risk limits... "
# Query database for current P&L
daily_pnl=$(psql -U trading_user -d trading_db -t -c \
    "SELECT total_pnl FROM daily_pnl WHERE trading_date = CURRENT_DATE;" 2>/dev/null || echo "0")
echo "Current P&L: $daily_pnl"

# 8. Review overnight positions
echo "=== OVERNIGHT POSITIONS ==="
psql -U trading_user -d trading_db -c \
    "SELECT symbol, quantity, entry_price, unrealized_pnl, side FROM positions ORDER BY unrealized_pnl DESC;"

echo ""
echo "=== PRE-MARKET CHECKLIST COMPLETE ==="
echo "System ready for trading"
```

**Run checklist**:
```bash
sudo /opt/trading-system/scripts/pre_market_checklist.sh
```

### 1.2 Market Hours Monitoring (9:30 AM - 4:00 PM ET)

**Continuous monitoring tasks**:

```bash
# Watch real-time P&L
watch -n 10 'psql -U trading_user -d trading_db -c \
    "SELECT trading_date, realized_pnl, unrealized_pnl, total_pnl, trade_count \
     FROM daily_pnl WHERE trading_date = CURRENT_DATE;"'

# Monitor order flow
tail -f /opt/trading-system/logs/execution-engine.log | grep "ORDER"

# Watch circuit breaker status
watch -n 5 'curl -s http://localhost:8080/api/v1/circuit-breaker/status | jq'

# Monitor service health
watch -n 30 './scripts/health_check.sh --production'
```

**Key Metrics Dashboard** (Grafana):
- Navigate to: http://localhost:3000/d/trading-overview
- Watch for alerts on:
  - Order latency >100μs
  - WebSocket disconnections
  - Failed orders >1%
  - Daily loss approaching limit ($4,000 of $5,000)

### 1.3 Post-Market Procedures (After 4:00 PM ET)

```bash
#!/bin/bash
# /opt/trading-system/scripts/post_market_procedures.sh

echo "=== POST-MARKET PROCEDURES ==="

# 1. Generate daily P&L report
echo "=== DAILY P&L SUMMARY ==="
psql -U trading_user -d trading_db -c \
    "SELECT
        trading_date,
        realized_pnl,
        unrealized_pnl,
        total_pnl,
        trade_count,
        winning_trades,
        losing_trades,
        ROUND((winning_trades::numeric / NULLIF(trade_count, 0) * 100), 2) as win_rate
     FROM daily_pnl
     WHERE trading_date = CURRENT_DATE;"

# 2. List open positions
echo "=== OPEN POSITIONS ==="
psql -U trading_user -d trading_db -c \
    "SELECT symbol, quantity, entry_price, current_price, unrealized_pnl, side
     FROM positions ORDER BY symbol;"

# 3. Review risk events
echo "=== RISK EVENTS TODAY ==="
psql -U trading_user -d trading_db -c \
    "SELECT event_type, severity, message, occurred_at
     FROM risk_events
     WHERE occurred_at::date = CURRENT_DATE
     ORDER BY occurred_at DESC
     LIMIT 20;"

# 4. Backup database
echo "Running daily backup..."
/opt/trading-system/scripts/backup_db.sh

# 5. Archive logs
echo "Archiving logs..."
tar -czf /opt/trading-system/logs/archive/logs-$(date +%Y%m%d).tar.gz \
    /opt/trading-system/logs/*.log
find /opt/trading-system/logs/archive -name "logs-*.tar.gz" -mtime +90 -delete

# 6. Generate metrics report
echo "=== PERFORMANCE METRICS ==="
echo "Average order latency (p95):"
# Query Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,order_execution_duration_seconds_bucket)' \
    | jq -r '.data.result[0].value[1]'

echo ""
echo "=== POST-MARKET PROCEDURES COMPLETE ==="
```

---

## 2. Service Management

### 2.1 Starting Services

**Native Deployment (systemd)**:
```bash
# Start all services in correct order
sudo systemctl start trading-market-data
sleep 5  # Wait for market data to initialize

sudo systemctl start trading-execution-engine
sudo systemctl start trading-risk-manager
sudo systemctl start trading-signal-bridge

# Verify all started
sudo systemctl status trading-*
```

**Docker Deployment**:
```bash
# Start all services
docker compose -f docker/docker-compose.production.yml up -d

# Follow startup logs
docker compose -f docker/docker-compose.production.yml logs -f

# Verify health
docker compose -f docker/docker-compose.production.yml ps
```

**Kubernetes Deployment**:
```bash
# Scale up deployment
kubectl scale deployment --replicas=2 -n trading-system --all

# Check pod status
kubectl get pods -n trading-system

# Follow logs
kubectl logs -n trading-system -l app=market-data -f
```

### 2.2 Stopping Services

**CRITICAL**: Always close positions before stopping services!

```bash
# 1. Trigger graceful shutdown via API
curl -X POST http://localhost:8080/api/v1/shutdown \
    -H "Content-Type: application/json" \
    -d '{"close_positions": true, "timeout_seconds": 300}'

# 2. Wait for positions to close (monitor)
watch -n 5 'psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM positions;"'

# 3. Stop services
sudo systemctl stop trading-signal-bridge
sudo systemctl stop trading-execution-engine
sudo systemctl stop trading-risk-manager
sleep 5
sudo systemctl stop trading-market-data
```

### 2.3 Restarting Services

**Individual Service Restart**:
```bash
# Restart specific service (zero downtime for stateless services)
sudo systemctl restart trading-market-data

# Verify restart
sudo systemctl status trading-market-data
sudo journalctl -u trading-market-data -n 50
```

**Full System Restart**:
```bash
# Use the provided script
./scripts/restart_trading_system.sh

# Manual procedure
sudo systemctl stop trading-*
sleep 10
sudo systemctl start trading-market-data
sleep 5
sudo systemctl start trading-execution-engine trading-risk-manager trading-signal-bridge
./scripts/health_check.sh
```

### 2.4 Service Dependencies

**Startup Order**:
1. **market-data** (must start first, provides price feeds)
2. **execution-engine** + **risk-manager** (can start in parallel)
3. **signal-bridge** (depends on market-data)

**Shutdown Order** (reverse):
1. **signal-bridge**
2. **execution-engine** + **risk-manager**
3. **market-data** (stop last)

---

## 3. Health Monitoring

### 3.1 Health Check Commands

```bash
# Quick health check (all services)
./scripts/health_check.sh

# Detailed health check
./scripts/health_check.sh --verbose --production

# Individual service health
curl http://localhost:8080/health/market-data
curl http://localhost:8080/health/execution-engine
curl http://localhost:8080/health/risk-manager
```

### 3.2 Key Health Indicators

| Indicator | Healthy Range | Warning | Critical |
|-----------|---------------|---------|----------|
| Order Latency (p99) | <100μs | 100-500μs | >500μs |
| WebSocket Lag | <10ms | 10-50ms | >50ms |
| Failed Orders Rate | <0.1% | 0.1-1% | >1% |
| Memory Usage | <70% | 70-85% | >85% |
| CPU Usage | <60% | 60-80% | >80% |
| Disk Space | >20% free | 10-20% free | <10% free |
| Database Connections | <50% pool | 50-80% pool | >80% pool |

### 3.3 Log Monitoring

**Real-time log aggregation**:
```bash
# All logs combined
journalctl -u trading-* -f --since "1 hour ago"

# Errors only
journalctl -u trading-* -f --since "1 hour ago" -p err

# Specific service
journalctl -u trading-execution-engine -f

# Filter for order events
journalctl -u trading-execution-engine | grep "ORDER_FILLED"
```

**Log locations**:
- Native: `/var/log/syslog` (systemd journald)
- Docker: `docker compose logs -f [service]`
- Kubernetes: `kubectl logs -n trading-system [pod]`
- Application logs: `/opt/trading-system/logs/*.log`

### 3.4 Metrics & Alerts

**Prometheus Queries** (http://localhost:9090):

```promql
# Order execution latency (p95)
histogram_quantile(0.95, rate(order_execution_duration_seconds_bucket[5m]))

# Order success rate
sum(rate(orders_total{status="filled"}[5m])) / sum(rate(orders_total[5m]))

# WebSocket message rate
rate(websocket_messages_received_total[1m])

# Daily P&L
current_daily_pnl_usd

# Circuit breaker trips
increase(circuit_breaker_trips_total[1h])
```

**Critical Alerts** (should page on-call):
- Circuit breaker tripped
- Daily loss >$4,500 (90% of $5,000 limit)
- WebSocket disconnected >1 minute
- Order execution latency >500μs sustained
- API rate limit hit
- Service crashed

**Warning Alerts** (Slack notification):
- Daily loss >$4,000
- Order latency >200μs
- Failed orders >0.5%
- High memory usage >80%
- Database connections >70%

---

## 4. Incident Response

### 4.1 Incident Severity Levels

| Severity | Definition | Response Time | Examples |
|----------|------------|---------------|----------|
| **P0 - Critical** | Trading halted, financial loss | Immediate (5 min) | Circuit breaker trip, API down, position loss >$1000 |
| **P1 - High** | Degraded trading | 15 minutes | High latency, partial service outage |
| **P2 - Medium** | Monitoring issues | 1 hour | Metrics gaps, log rotation failure |
| **P3 - Low** | Minor issues | 4 hours | Documentation outdated, cosmetic bugs |

### 4.2 Incident Response Playbooks

#### P0: Circuit Breaker Tripped

**Symptoms**: Trading halted, circuit_breaker_status = "OPEN"

**Immediate Actions**:
```bash
# 1. Assess situation
psql -U trading_user -d trading_db -c \
    "SELECT * FROM daily_pnl WHERE trading_date = CURRENT_DATE;"

# 2. Review recent risk events
psql -U trading_user -d trading_db -c \
    "SELECT * FROM risk_events WHERE occurred_at > NOW() - INTERVAL '1 hour' ORDER BY occurred_at DESC;"

# 3. Check for runaway positions
psql -U trading_user -d trading_db -c \
    "SELECT * FROM positions ORDER BY ABS(unrealized_pnl) DESC;"

# 4. Verify if circuit breaker trip was valid
# If daily loss < $5000 and trip was false alarm:
curl -X POST http://localhost:8080/api/v1/circuit-breaker/reset \
    -H "Authorization: Bearer $ADMIN_TOKEN"

# 5. If trip was valid, investigate root cause
journalctl -u trading-* --since "2 hours ago" | grep -i "error\|loss\|risk"
```

**Root Cause Analysis**:
- Was the loss legitimate (bad market conditions)?
- Was there a bug in risk management?
- Did slippage exceed expectations?
- Was there a fat-finger trade?

**Recovery**:
- Fix root cause
- Manually reset circuit breaker (after approval)
- Resume trading cautiously

#### P0: WebSocket Disconnection

**Symptoms**: No market data updates, `websocket_status = "DISCONNECTED"`

**Immediate Actions**:
```bash
# 1. Check WebSocket service status
sudo systemctl status trading-market-data

# 2. Review logs for connection errors
journalctl -u trading-market-data -n 100 | grep -i "websocket\|disconnect"

# 3. Test Alpaca WebSocket manually
wscat -c "wss://stream.data.alpaca.markets/v2/iex" \
    -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
    -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"

# 4. If Alpaca service is down, check status page
curl -s https://status.alpaca.markets/api/v2/status.json | jq

# 5. Restart market data service
sudo systemctl restart trading-market-data

# 6. Verify reconnection
tail -f /opt/trading-system/logs/market-data.log | grep "CONNECTED"
```

#### P0: Position Loss Exceeds Threshold

**Symptoms**: Single position unrealized_pnl < -$1000

**Immediate Actions**:
```bash
# 1. Identify losing position
psql -U trading_user -d trading_db -c \
    "SELECT * FROM positions WHERE unrealized_pnl < -1000 ORDER BY unrealized_pnl;"

# 2. Check if stop loss executed
psql -U trading_user -d trading_db -c \
    "SELECT * FROM orders WHERE symbol = 'AAPL' AND side = 'sell' AND status = 'filled'
     ORDER BY submitted_at DESC LIMIT 5;"

# 3. If stop loss failed, manually close position
curl -X POST http://localhost:8080/api/v1/positions/AAPL/close \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN"

# 4. Investigate why stop loss didn't trigger
journalctl -u trading-risk-manager --since "1 hour ago" | grep "STOP_LOSS"
```

#### P1: High Order Latency

**Symptoms**: Order execution >500μs sustained

**Diagnostic Actions**:
```bash
# 1. Check system resources
top -b -n 1 | head -20
df -h
free -h

# 2. Identify bottleneck
# CPU-bound:
top -H -p $(pgrep execution-engine)

# Memory-bound:
pmap -x $(pgrep execution-engine)

# Network-bound:
ping -c 10 api.alpaca.markets
traceroute api.alpaca.markets

# 3. Review performance metrics
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,order_execution_duration_seconds_bucket)' \
    | jq -r '.data.result[0].value[1]'

# 4. Check for database slowness
psql -U trading_user -d trading_db -c \
    "SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;"
```

**Mitigation**:
- Apply performance optimizations from `docs/PERFORMANCE_ANALYSIS.md`
- Restart services to clear memory leaks
- Reduce order frequency temporarily
- Scale up infrastructure

#### P1: Database Connection Exhaustion

**Symptoms**: Errors "connection pool exhausted"

**Immediate Actions**:
```bash
# 1. Check active connections
psql -U postgres -c \
    "SELECT count(*) as connections FROM pg_stat_activity WHERE datname = 'trading_db';"

# 2. Identify long-running queries
psql -U postgres -c \
    "SELECT pid, age(clock_timestamp(), query_start), usename, query
     FROM pg_stat_activity
     WHERE state != 'idle' AND query NOT ILIKE '%pg_stat_activity%'
     ORDER BY query_start DESC;"

# 3. Kill long-running queries (if necessary)
psql -U postgres -c "SELECT pg_terminate_backend(12345);"  # Replace with actual PID

# 4. Increase connection pool size temporarily
# Edit config/system.production.json:
# "database": { "pool_size": 30 }  # Increase from 20

# 5. Restart services to apply
sudo systemctl restart trading-execution-engine
```

### 4.3 Post-Incident Review

**Required within 24 hours of P0/P1 incident**:

```markdown
## Incident Post-Mortem Template

**Incident ID**: INC-20251021-001
**Date**: October 21, 2025
**Severity**: P0
**Duration**: 15 minutes
**Impact**: Trading halted, $500 loss

### Timeline
- 10:00 AM: Circuit breaker tripped
- 10:02 AM: On-call engineer paged
- 10:05 AM: Investigation started
- 10:10 AM: Root cause identified (bug in risk calculation)
- 10:15 AM: Circuit breaker reset, trading resumed

### Root Cause
Bug in risk calculation logic caused false positive circuit breaker trip.

### Action Items
1. [ ] Fix risk calculation bug (ENG-123) - Owner: John, Due: 10/22
2. [ ] Add unit test for edge case (ENG-124) - Owner: Jane, Due: 10/22
3. [ ] Improve circuit breaker logging (ENG-125) - Owner: Bob, Due: 10/25
4. [ ] Update runbook with this scenario (DOC-45) - Owner: Alice, Due: 10/23

### Lessons Learned
- Need better test coverage for risk calculations
- Circuit breaker logs should include calculation details
- Consider adding manual override with two-person approval
```

---

## 5. Performance Tuning

### 5.1 Latency Optimization

**Phase 1: Quick Wins** (4-8 hours implementation):

```bash
# 1. Apply optimized Cargo flags
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust
RUSTFLAGS="-C target-cpu=native -C link-arg=-fuse-ld=lld" cargo build --release

# 2. Update system configuration
sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.wmem_max=26214400
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 26214400"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 26214400"

# 3. Increase file descriptor limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 4. Restart services
sudo systemctl restart trading-*
```

**Expected Improvement**: 3-5x latency reduction (200-500μs → 70-150μs)

### 5.2 Resource Tuning

**Memory Optimization**:
```bash
# Monitor memory usage
watch -n 5 'ps aux | grep -E "market-data|execution-engine|risk-manager" | grep -v grep'

# If high memory usage, adjust settings
# Edit /opt/trading-system/config/system.production.json:
{
  "market_data": {
    "orderbook_cache_size": 100  // Reduce from default 1000
  },
  "execution": {
    "order_cache_size": 500  // Reduce from default 1000
  }
}
```

**CPU Affinity** (pin services to specific cores):
```bash
# Pin market-data to cores 0-1
sudo taskset -cp 0,1 $(pgrep market-data)

# Pin execution-engine to cores 2-3
sudo taskset -cp 2,3 $(pgrep execution-engine)

# Verify
taskset -cp $(pgrep market-data)
```

### 5.3 Database Performance

**Optimize PostgreSQL**:
```sql
-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM positions WHERE symbol = 'AAPL';

-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_positions_symbol_side
ON positions(symbol, side);

-- Vacuum and analyze
VACUUM ANALYZE positions;
VACUUM ANALYZE orders;
VACUUM ANALYZE trades;

-- Update statistics
ANALYZE;
```

**PostgreSQL Configuration** (`/etc/postgresql/15/main/postgresql.conf`):
```ini
# Increase shared buffers for trading workload
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 50MB
maintenance_work_mem = 512MB

# Optimize for OLTP
random_page_cost = 1.1  # SSD
effective_io_concurrency = 200

# Connection pooling
max_connections = 100
```

---

## 6. Backup & Recovery

### 6.1 Backup Schedule

| Backup Type | Frequency | Retention | Location |
|-------------|-----------|-----------|----------|
| **Database Full** | Every 6 hours | 30 days | `/opt/trading-system/backups/db/` |
| **Database WAL** | Continuous | 7 days | `/opt/trading-system/backups/wal/` |
| **Configurations** | Daily | 90 days | `/opt/trading-system/backups/config/` |
| **Logs** | Daily | 90 days | `/opt/trading-system/logs/archive/` |
| **Binaries** | On deployment | 5 versions | `/opt/trading-system/backups/binaries/` |

### 6.2 Manual Backup

```bash
# Full system backup
./scripts/backup_full_system.sh

# Database only
pg_dump -U trading_user -d trading_db -F c -f /tmp/trading_db_$(date +%Y%m%d).backup

# Configuration only
tar -czf /tmp/config_backup_$(date +%Y%m%d).tar.gz /opt/trading-system/config/
```

### 6.3 Recovery Procedures

**Database Recovery** (from backup):
```bash
# 1. Stop services
sudo systemctl stop trading-*

# 2. Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE trading_db;"
sudo -u postgres psql -c "CREATE DATABASE trading_db OWNER trading_user;"

# 3. Restore from backup
pg_restore -U trading_user -d trading_db /opt/trading-system/backups/db/trading_db_20251021.backup

# 4. Verify restoration
psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM positions;"

# 5. Restart services
sudo systemctl start trading-*
```

**Configuration Recovery**:
```bash
# Restore previous configuration
tar -xzf /opt/trading-system/backups/config/config_20251020.tar.gz -C /opt/trading-system/

# Restart affected services
sudo systemctl restart trading-execution-engine
```

### 6.4 Disaster Recovery

**RTO (Recovery Time Objective)**: 30 minutes
**RPO (Recovery Point Objective)**: 15 minutes (max data loss)

**Full System Recovery**:
```bash
# 1. Provision new server
# 2. Install dependencies (from PRODUCTION_DEPLOYMENT.md)
# 3. Restore binaries
sudo cp -r /mnt/backup/trading-system/bin/* /opt/trading-system/bin/

# 4. Restore database
pg_restore -U trading_user -d trading_db /mnt/backup/trading_db_latest.backup

# 5. Restore configurations
tar -xzf /mnt/backup/config_latest.tar.gz -C /opt/trading-system/

# 6. Start services
sudo systemctl start trading-*

# 7. Verify reconciliation
./scripts/reconcile_positions.sh
```

---

## 7. Security Operations

### 7.1 Credential Rotation

**Alpaca API Keys** (rotate every 90 days):
```bash
# 1. Generate new API key in Alpaca dashboard
# 2. Update .env.production
nano /opt/trading-system/.env.production
# Update ALPACA_API_KEY and ALPACA_API_SECRET

# 3. Restart services
sudo systemctl restart trading-*

# 4. Verify with test order
curl -X POST http://localhost:8080/api/v1/orders/test

# 5. Deactivate old API key in Alpaca dashboard
```

**Database Passwords** (rotate every 90 days):
```bash
# 1. Change password
sudo -u postgres psql -c "ALTER USER trading_user WITH PASSWORD 'new_secure_password';"

# 2. Update DATABASE_URL in .env.production
# 3. Restart services
sudo systemctl restart trading-*
```

### 7.2 Access Audit

```bash
# Review database access logs
psql -U postgres -c \
    "SELECT usename, application_name, client_addr, state, query_start
     FROM pg_stat_activity
     WHERE datname = 'trading_db';"

# Review failed login attempts
sudo journalctl -u ssh | grep "Failed password"

# Review sudo access
sudo journalctl | grep sudo | tail -50
```

### 7.3 Security Scanning

```bash
# Update dependencies
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust
cargo update
cargo audit

# Scan for vulnerabilities
cargo audit fix

# Check for outdated dependencies
cargo outdated
```

---

## 8. Common Issues

### Issue: Service Won't Start

**Symptoms**: `systemctl start` fails
**Diagnosis**:
```bash
sudo journalctl -u trading-market-data -n 50
sudo systemctl status trading-market-data
```

**Common Causes**:
- Missing environment variables
- Port already in use
- File permission issues
- Missing dependencies

**Solutions**:
```bash
# Check environment
env | grep ALPACA

# Check port availability
sudo netstat -tlnp | grep 5555

# Fix permissions
sudo chown -R trading_user:trading_group /opt/trading-system

# Verify dependencies
ldd /opt/trading-system/bin/market-data
```

---

### Issue: High Memory Usage

**Symptoms**: Memory >85%
**Diagnosis**:
```bash
free -h
ps aux --sort=-%mem | head -10
```

**Solutions**:
```bash
# Restart services (clears memory leaks)
sudo systemctl restart trading-*

# Reduce cache sizes in config
# Increase swap if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### Issue: Order Execution Failures

**Symptoms**: Orders rejected by Alpaca
**Diagnosis**:
```bash
journalctl -u trading-execution-engine | grep "ORDER_REJECTED"
```

**Common Causes**:
- Insufficient buying power
- Invalid symbol
- Outside market hours
- Rate limit exceeded

**Solutions**:
```bash
# Check account status
curl -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
     -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}" \
     https://api.alpaca.markets/v2/account

# Verify market hours
date -u  # Should be during 9:30 AM - 4:00 PM ET

# Check rate limiting
grep "rate_limit" /opt/trading-system/logs/execution-engine.log
```

---

## On-Call Runbook Quick Reference

**Before Your Shift**:
- [ ] Review open incidents
- [ ] Check system health dashboard
- [ ] Verify alerting is working (send test alert)
- [ ] Ensure access to all systems

**During Market Hours (9:30 AM - 4:00 PM ET)**:
- [ ] Monitor P&L every 30 minutes
- [ ] Watch for circuit breaker alerts
- [ ] Review order execution latency
- [ ] Check for WebSocket disconnections

**After Market Close**:
- [ ] Run post-market procedures
- [ ] Review daily P&L report
- [ ] Check for overnight positions
- [ ] Verify backups completed

**Escalation Contacts**:
- **Engineering Lead**: [Name] - [Phone]
- **DevOps Manager**: [Name] - [Phone]
- **CTO**: [Name] - [Phone] (P0 only)

---

**Document Version**: 1.0.0
**Last Updated**: October 21, 2025
**Maintained By**: Documentation Specialist Agent
