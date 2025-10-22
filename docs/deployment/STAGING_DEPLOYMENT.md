# Staging Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-21
**Environment:** Staging

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Steps](#deployment-steps)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedure](#rollback-procedure)

---

## Prerequisites

### System Requirements

```bash
# Operating System
Ubuntu 22.04 LTS or later
macOS 12+ (for development)
Windows 11 + WSL2 (for development)

# Software Dependencies
- Docker 24.0+
- Docker Compose 2.20+
- Git 2.40+
- Python 3.8+
- Rust 1.70+
- Node.js 18+ (for dashboard)
- PostgreSQL 15+ or DuckDB 1.1+ (for production metrics)
```

### Access Requirements

```bash
# Required credentials
✓ Alpaca API key (paper trading account)
✓ Alpaca secret key
✓ SSH access to staging server
✓ Docker Hub or container registry access
✓ GitHub repository access

# Required ports (must be open on staging server)
✓ 8000 (Observability API)
✓ 3000 (Dashboard)
✓ 5001 (Market Data Service)
✓ 5002 (Execution Engine)
✓ 5003 (Risk Manager)
```

---

## Environment Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/SamoraDC/RustAlgorithmTrading.git
cd RustAlgorithmTrading

# Checkout staging branch
git checkout staging

# Or use specific release tag
git checkout v0.2.0
```

### 2. Create Environment File

```bash
# Create .env file for staging
cat > .env <<EOF
# === Alpaca API Configuration ===
ALPACA_API_KEY=your_staging_api_key_here
ALPACA_SECRET_KEY=your_staging_secret_key_here
ALPACA_PAPER=true
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# === System Configuration ===
ENVIRONMENT=staging
LOG_LEVEL=info
ENABLE_OBSERVABILITY=true
ENABLE_DASHBOARD=true

# === Database Configuration ===
DATABASE_TYPE=duckdb
DATABASE_PATH=./data/metrics.duckdb
SQLITE_PATH=./data/events.db

# === Risk Management ===
MAX_DAILY_LOSS=5000.0
MAX_POSITION_SIZE=10000.0
CIRCUIT_BREAKER_ENABLED=true

# === Monitoring ===
METRICS_ENABLED=true
METRICS_PORT=8000
DASHBOARD_PORT=3000

# === Service Ports ===
MARKET_DATA_PORT=5001
EXECUTION_PORT=5002
RISK_MANAGER_PORT=5003
EOF
```

### 3. Configure System Settings

```bash
# Copy staging configuration
cp config/system.staging.json config/system.json

# Verify configuration
cat config/system.json | jq .
```

**Example `config/system.staging.json`:**

```json
{
  "environment": "staging",
  "services": {
    "market_data": {
      "enabled": true,
      "port": 5001,
      "websocket_url": "wss://paper-api.alpaca.markets/stream",
      "reconnect_attempts": 5,
      "reconnect_delay_ms": 2000
    },
    "execution_engine": {
      "enabled": true,
      "port": 5002,
      "mode": "paper",
      "dry_run": false
    },
    "risk_manager": {
      "enabled": true,
      "port": 5003,
      "strict_mode": true,
      "config_file": "config/risk_limits.toml"
    }
  },
  "observability": {
    "enabled": true,
    "api_port": 8000,
    "dashboard_port": 3000,
    "metrics_interval_ms": 100,
    "database": {
      "duckdb_path": "./data/metrics.duckdb",
      "sqlite_path": "./data/events.db"
    }
  },
  "logging": {
    "level": "info",
    "format": "json",
    "outputs": ["stdout", "file"],
    "file_path": "./logs/trading.log",
    "max_size_mb": 100,
    "max_backups": 10
  }
}
```

---

## Deployment Steps

### Option 1: Docker Deployment (Recommended)

#### Step 1: Build Images

```bash
# Build all services
docker-compose -f docker/docker-compose.yml build

# Or build specific services
docker-compose -f docker/docker-compose.yml build market-data
docker-compose -f docker/docker-compose.yml build execution-engine
```

#### Step 2: Start Services

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

**Docker Compose File:** `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  market-data:
    build:
      context: ..
      dockerfile: docker/Dockerfile.market-data
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - RUST_LOG=info
    ports:
      - "5001:5001"
    volumes:
      - ../logs:/app/logs
      - ../data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  execution-engine:
    build:
      context: ..
      dockerfile: docker/Dockerfile.execution-engine
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - RUST_LOG=info
    ports:
      - "5002:5002"
    volumes:
      - ../logs:/app/logs
      - ../data:/app/data
    restart: unless-stopped
    depends_on:
      - market-data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  risk-manager:
    build:
      context: ..
      dockerfile: docker/Dockerfile.risk-manager
    environment:
      - RUST_LOG=info
    ports:
      - "5003:5003"
    volumes:
      - ../logs:/app/logs
      - ../data:/app/data
      - ../config:/app/config:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  observability-api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.observability
    environment:
      - PYTHONUNBUFFERED=1
    ports:
      - "8000:8000"
    volumes:
      - ../logs:/app/logs
      - ../data:/app/data
      - ../src/observability:/app/src/observability
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  dashboard:
    build:
      context: ../src/observability/dashboard
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - observability-api
    restart: unless-stopped
```

### Option 2: Manual Deployment

#### Step 1: Build Rust Services

```bash
# Build all Rust services in release mode
cd rust
cargo build --release --workspace

# Verify binaries
ls -lh target/release/market-data
ls -lh target/release/execution-engine
ls -lh target/release/risk-manager
```

#### Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import fastapi, uvicorn, duckdb; print('OK')"
```

#### Step 3: Start Services

```bash
# Start services using the main script
./scripts/start_trading.sh

# Or start services individually
./rust/target/release/market-data &
./rust/target/release/execution-engine &
./rust/target/release/risk-manager &
./scripts/start_observability.sh &
```

---

## Configuration

### Risk Limits (Staging)

**File:** `config/risk_limits.toml`

```toml
[position_limits]
max_shares = 500  # Reduced for staging
max_notional_per_position = 5000.0
max_total_exposure = 20000.0
max_open_positions = 3

[loss_limits]
max_loss_per_trade = 250.0
max_daily_loss = 2000.0  # Tighter limit for staging
max_weekly_loss = 5000.0
max_monthly_loss = 15000.0

[stop_loss]
default_stop_loss_percent = 3.0  # Tighter stop for staging
enable_trailing_stop = true
trailing_stop_percent = 2.0

[circuit_breaker]
enabled = true
daily_loss_threshold = 2000.0
max_consecutive_losses = 3  # More sensitive in staging
cooldown_minutes = 30
auto_resume = false  # Require manual resume
```

### Logging Configuration

```bash
# Create log directories
mkdir -p logs/{observability,trades,metrics,system}

# Set log rotation
cat > /etc/logrotate.d/trading-system <<EOF
/path/to/RustAlgorithmTrading/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload trading-system
    endscript
}
EOF
```

---

## Verification

### 1. Health Checks

```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health

# Check observability readiness
curl http://localhost:8000/health/ready | jq .

# Expected output:
{
  "ready": true,
  "collectors": {
    "market_data": true,
    "strategy": true,
    "execution": true,
    "system": true
  }
}
```

### 2. Verify Database Connections

```bash
# Check DuckDB
python3 <<EOF
import duckdb
conn = duckdb.connect('data/metrics.duckdb')
result = conn.execute('SELECT COUNT(*) FROM system_metrics').fetchone()
print(f"System metrics records: {result[0]}")
conn.close()
EOF

# Check SQLite
sqlite3 data/events.db "SELECT COUNT(*) FROM trade_events;"
```

### 3. Test Market Data Feed

```bash
# Subscribe to market data
wscat -c ws://localhost:5001/stream

# Should see market data messages:
{"type":"tick","symbol":"AAPL","price":150.00,"timestamp":"..."}
```

### 4. Test Order Placement (Paper Trading)

```bash
# Submit test order
curl -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "buy",
    "type": "limit",
    "quantity": 1,
    "price": 150.00
  }'

# Verify order in dashboard
open http://localhost:3000
```

### 5. Verify Observability Stack

```bash
# Check API documentation
open http://localhost:8000/docs

# Check dashboard
open http://localhost:3000

# Test WebSocket streaming
wscat -c ws://localhost:8000/ws/metrics

# Send ping
> ping

# Should receive pong and metrics stream
```

---

## Monitoring

### Key Metrics to Monitor

```bash
# 1. Service Health
watch -n 5 'curl -s http://localhost:8000/api/system/status | jq .'

# 2. Trading Performance
curl http://localhost:8000/api/trades/pnl?period=today | jq .

# 3. Risk Metrics
curl http://localhost:8000/api/risk/exposure | jq .

# 4. Circuit Breaker Status
curl http://localhost:8000/api/system/circuit-breaker/status | jq .

# 5. Database Metrics
curl http://localhost:8000/api/metrics/system | jq .
```

### Set Up Alerts

**Alert Configuration:** `config/alerts.staging.yaml`

```yaml
alerts:
  - name: "Service Down"
    condition: "service.status != 'healthy'"
    severity: "critical"
    channels: ["email", "slack"]

  - name: "Daily Loss Warning"
    condition: "daily_pnl < -1500"
    severity: "warning"
    channels: ["email"]

  - name: "Circuit Breaker Activated"
    condition: "circuit_breaker.active == true"
    severity: "critical"
    channels: ["email", "slack", "sms"]

  - name: "High Error Rate"
    condition: "error_rate > 5%"
    severity: "warning"
    channels: ["slack"]

notification_channels:
  email:
    to: ["team@example.com"]
    from: "alerts@trading-system.com"

  slack:
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    channel: "#staging-alerts"

  sms:
    provider: "twilio"
    to: ["+1234567890"]
```

---

## Troubleshooting

### Services Won't Start

**Problem:** Services fail to start

**Diagnosis:**
```bash
# Check logs
tail -f logs/observability/api.log
tail -f logs/system/*.log

# Check ports
lsof -i :8000
lsof -i :5001-5003

# Check dependencies
./scripts/check_dependencies.sh
```

**Solutions:**
```bash
# Kill conflicting processes
lsof -ti :8000 | xargs kill -9

# Restart services
docker-compose -f docker/docker-compose.yml restart

# Or manual restart
./scripts/stop_trading_system.sh
./scripts/start_trading.sh
```

### Database Connection Errors

**Problem:** Cannot connect to DuckDB or SQLite

**Diagnosis:**
```bash
# Check database files
ls -lh data/*.db data/*.duckdb

# Check file permissions
ls -la data/

# Check disk space
df -h
```

**Solutions:**
```bash
# Reinitialize databases
rm data/metrics.duckdb data/events.db
./scripts/start_observability.sh

# Fix permissions
chmod 664 data/*.db data/*.duckdb
chown $USER:$USER data/*.db data/*.duckdb
```

### High Memory Usage

**Problem:** System consuming too much memory

**Diagnosis:**
```bash
# Check memory usage
free -h
docker stats

# Check per-process memory
ps aux --sort=-%mem | head -20
```

**Solutions:**
```bash
# Reduce database cache
# Edit config/system.json
"database": {
  "cache_size_mb": 256  # Reduce from default
}

# Reduce metrics retention
python3 <<EOF
import duckdb
conn = duckdb.connect('data/metrics.duckdb')
conn.execute("DELETE FROM system_metrics WHERE timestamp < current_timestamp - INTERVAL 7 DAY")
conn.close()
EOF

# Restart services with lower memory limits
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d --scale worker=1
```

### WebSocket Disconnections

**Problem:** WebSocket connections dropping frequently

**Diagnosis:**
```bash
# Check network stability
ping -c 100 paper-api.alpaca.markets

# Check connection logs
grep -i "websocket" logs/observability/api.log

# Check firewall rules
sudo iptables -L -n
```

**Solutions:**
```bash
# Increase reconnection attempts
# Edit config/system.json
"market_data": {
  "reconnect_attempts": 10,
  "reconnect_delay_ms": 5000
}

# Enable keep-alive
# Edit src/observability/api/main.py
websocket.send_str("ping")  # Every 30 seconds

# Restart services
docker-compose -f docker/docker-compose.yml restart market-data
```

---

## Rollback Procedure

### Quick Rollback

```bash
# 1. Stop current deployment
docker-compose -f docker/docker-compose.yml down

# 2. Checkout previous version
git checkout v0.1.0  # or previous stable tag

# 3. Restore previous configuration
cp config/system.staging.backup.json config/system.json

# 4. Restart services
docker-compose -f docker/docker-compose.yml up -d

# 5. Verify rollback
curl http://localhost:8000/health
```

### Database Rollback

```bash
# 1. Stop services
./scripts/stop_trading_system.sh

# 2. Restore database backup
cp backups/metrics.duckdb.backup data/metrics.duckdb
cp backups/events.db.backup data/events.db

# 3. Verify backup integrity
python3 <<EOF
import duckdb
conn = duckdb.connect('data/metrics.duckdb')
result = conn.execute('SELECT COUNT(*) FROM system_metrics')
print(f"Records restored: {result.fetchone()[0]}")
conn.close()
EOF

# 4. Restart services
./scripts/start_trading.sh
```

### Complete Rollback with Data Preservation

```bash
# 1. Export current data
python3 scripts/export_metrics.py --output=rollback_backup_$(date +%Y%m%d).csv

# 2. Stop all services
docker-compose -f docker/docker-compose.yml down -v

# 3. Checkout previous version
git fetch --tags
git checkout v0.1.0

# 4. Rebuild containers
docker-compose -f docker/docker-compose.yml build

# 5. Import preserved data
python3 scripts/import_metrics.py --input=rollback_backup_*.csv

# 6. Start services
docker-compose -f docker/docker-compose.yml up -d

# 7. Verify system
./scripts/production_validation.sh
```

---

## Best Practices

### Pre-Deployment Checklist

```bash
✓ Run all tests: cargo test --workspace --release
✓ Run integration tests: pytest tests/e2e/
✓ Verify configurations: ./scripts/validate_config.sh
✓ Check disk space: df -h (need 10GB+ free)
✓ Backup databases: ./scripts/backup_databases.sh
✓ Tag release: git tag -a v0.2.0 -m "Release 0.2.0"
✓ Update changelog: vim docs/CHANGELOG_CRITICAL_FIXES.md
✓ Notify team: Send deployment notification
```

### Post-Deployment Checklist

```bash
✓ Verify all health checks pass
✓ Check dashboard for anomalies
✓ Monitor logs for errors (first 15 minutes)
✓ Verify market data streaming
✓ Test order placement (1 test order)
✓ Check database writes
✓ Verify circuit breaker works
✓ Monitor system metrics (CPU, memory, disk)
✓ Document any issues
✓ Create post-deployment backup
```

---

## Additional Resources

- [Quick Start Guide](/docs/QUICK_START_OBSERVABILITY.md)
- [Observability Integration](/docs/OBSERVABILITY_INTEGRATION.md)
- [Risk Management Guide](/docs/guides/RISK_MANAGEMENT_GUIDE.md)
- [Error Handling Patterns](/docs/guides/ERROR_HANDLING_PATTERNS.md)
- [Testing Guide](/docs/testing/TESTING_GUIDE.md)

---

## Support

For deployment issues:
- Check logs: `./logs/`
- Run diagnostics: `./scripts/health_check.sh`
- Review documentation: `/docs/`
- Contact: team@example.com
