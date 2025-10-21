# Production Deployment Guide
## Rust Algorithmic Trading System

**Version**: 1.0.0
**Last Updated**: October 21, 2025
**System Status**: Production Ready (92% completion)
**Target Environment**: Linux (Ubuntu 20.04+ / RHEL 8+), Docker, Kubernetes

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Methods](#deployment-methods)
4. [Configuration Management](#configuration-management)
5. [Security Hardening](#security-hardening)
6. [Database Setup](#database-setup)
7. [Monitoring & Observability](#monitoring--observability)
8. [Verification & Testing](#verification--testing)
9. [Rollback Procedures](#rollback-procedures)

---

## 1. Prerequisites

### System Requirements

#### Hardware Requirements
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB+ SSD (NVMe recommended for low latency)
- **Network**: Low-latency connection (<5ms to exchange)

#### Software Requirements
```bash
# Operating System
Ubuntu 20.04 LTS or newer
RHEL 8+ or CentOS Stream

# Runtime Dependencies
Rust 1.70+
Python 3.9+
Docker 24.0+
Docker Compose 2.20+
Kubernetes 1.28+ (for K8s deployment)
PostgreSQL 15+ (for persistence)

# System Libraries
pkg-config
libssl-dev (OpenSSL 1.1.1+)
build-essential
```

### Network Requirements
- **Outbound HTTPS** to Alpaca API (`api.alpaca.markets:443`)
- **Outbound WSS** to Alpaca WebSocket (`stream.data.alpaca.markets:443`)
- **Internal TCP** ports for ZeroMQ (5555-5558)
- **Monitoring** ports (Prometheus: 9090, Grafana: 3000)

---

## 2. Environment Setup

### 2.1 Install System Dependencies

#### Ubuntu/Debian
```bash
# Update package list
sudo apt-get update

# Install build dependencies
sudo apt-get install -y \
    pkg-config \
    libssl-dev \
    build-essential \
    curl \
    git

# Install Rust (if not present)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
rustc --version  # Verify installation
```

#### RHEL/CentOS
```bash
# Install build dependencies
sudo dnf install -y \
    pkgconfig \
    openssl-devel \
    gcc \
    gcc-c++ \
    make \
    curl \
    git

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 2.2 Environment Variables

Create a production `.env` file:

```bash
# /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/.env.production

# === ALPACA API CREDENTIALS ===
ALPACA_API_KEY=your_api_key_here
ALPACA_API_SECRET=your_api_secret_here
ALPACA_API_URL=https://api.alpaca.markets  # Live trading
# ALPACA_API_URL=https://paper-api.alpaca.markets  # Paper trading

# === TRADING ENVIRONMENT ===
TRADING_MODE=production  # CRITICAL: Set to 'production' for live trading
PAPER_TRADING=false      # CRITICAL: Set to false for live trading

# === DATABASE CONFIGURATION ===
DATABASE_URL=postgresql://trading_user:secure_password@localhost:5432/trading_db
DB_POOL_SIZE=20
DB_TIMEOUT_SECONDS=30

# === LOGGING & MONITORING ===
RUST_LOG=info,market_data=debug,execution_engine=debug
LOG_LEVEL=info
METRICS_PORT=9100

# === RISK MANAGEMENT ===
MAX_POSITION_SIZE=10000
MAX_DAILY_LOSS=5000
MAX_OPEN_POSITIONS=5
CIRCUIT_BREAKER_ENABLED=true

# === NETWORK CONFIGURATION ===
ZMQ_MARKET_DATA_PORT=5555
ZMQ_SIGNAL_PORT=5556
API_GATEWAY_PORT=8080

# === SECURITY ===
ENABLE_TLS=true
TLS_MIN_VERSION=1.2
ENABLE_ZMQ_ENCRYPTION=true  # Recommended for production
```

**SECURITY WARNING**: Never commit `.env.production` to version control!

```bash
# Secure the environment file
chmod 600 .env.production
chown trading_user:trading_group .env.production
```

---

## 3. Deployment Methods

### Method 1: Native Deployment (Recommended for Production)

**Advantages**: Lowest latency (<50μs), full control, optimal performance
**Best For**: Production trading with strict latency requirements

#### Step 1: Build Optimized Binaries

```bash
# Navigate to Rust workspace
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/rust

# Build with maximum optimizations
RUSTFLAGS="-C target-cpu=native -C link-arg=-fuse-ld=lld" \
  cargo build --release --workspace

# Verify binaries
ls -lh target/release/{market-data,execution-engine,risk-manager,signal-bridge}
```

#### Step 2: Install as systemd Services

Create systemd service files:

**Market Data Service** (`/etc/systemd/system/trading-market-data.service`):
```ini
[Unit]
Description=Trading System - Market Data Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=trading_user
Group=trading_group
WorkingDirectory=/opt/trading-system
EnvironmentFile=/opt/trading-system/.env.production
ExecStart=/opt/trading-system/bin/market-data
Restart=on-failure
RestartSec=10s
LimitNOFILE=65536

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/trading-system/logs

[Install]
WantedBy=multi-user.target
```

Repeat for other services: `trading-execution-engine.service`, `trading-risk-manager.service`, `trading-signal-bridge.service`

#### Step 3: Deploy and Start Services

```bash
# Copy binaries to deployment directory
sudo mkdir -p /opt/trading-system/{bin,logs,config}
sudo cp target/release/{market-data,execution-engine,risk-manager,signal-bridge} /opt/trading-system/bin/
sudo cp config/* /opt/trading-system/config/
sudo cp .env.production /opt/trading-system/.env.production

# Set ownership
sudo useradd -r -s /bin/false trading_user
sudo chown -R trading_user:trading_group /opt/trading-system
sudo chmod 600 /opt/trading-system/.env.production

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable trading-market-data trading-execution-engine trading-risk-manager trading-signal-bridge
sudo systemctl start trading-market-data
sleep 5  # Wait for market data to initialize
sudo systemctl start trading-execution-engine trading-risk-manager trading-signal-bridge

# Verify services
sudo systemctl status trading-*
```

#### Step 4: Validate Deployment

```bash
# Use the health check script
./scripts/health_check.sh --production

# Check logs
sudo journalctl -u trading-market-data -f
```

---

### Method 2: Docker Deployment

**Advantages**: Isolated environment, easy rollback, consistent across environments
**Best For**: Staging, UAT, development environments

#### Step 1: Build Docker Images

```bash
# Build all services
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading
docker compose -f docker/docker-compose.yml build

# Tag for production
docker tag trading_market_data:latest trading_market_data:v1.0.0
docker tag trading_order_execution:latest trading_order_execution:v1.0.0
docker tag trading_risk_management:latest trading_risk_management:v1.0.0
```

#### Step 2: Configure Production Compose File

Create `docker/docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  market_data_service:
    image: trading_market_data:v1.0.0
    container_name: trading_market_data
    env_file:
      - ../.env.production
    environment:
      - RUST_LOG=info
    ports:
      - "5555:5555"
    networks:
      - trading_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "5555"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    volumes:
      - market_data_logs:/app/logs:rw
      - /etc/localtime:/etc/localtime:ro
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '1.0'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  # ... (repeat for other services)

networks:
  trading_network:
    driver: bridge

volumes:
  market_data_logs:
    driver: local
```

#### Step 3: Deploy with Docker Compose

```bash
# Start all services
docker compose -f docker/docker-compose.production.yml up -d

# Monitor startup
docker compose -f docker/docker-compose.production.yml logs -f

# Verify health
docker compose -f docker/docker-compose.production.yml ps
```

---

### Method 3: Kubernetes Deployment

**Advantages**: High availability, auto-scaling, enterprise-grade orchestration
**Best For**: Large-scale deployments, multi-region setups

#### Step 1: Create Kubernetes Manifests

**Namespace** (`k8s/namespace.yaml`):
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: trading-system
  labels:
    name: trading-system
    environment: production
```

**ConfigMap** (`k8s/configmap.yaml`):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-config
  namespace: trading-system
data:
  system.production.json: |
    {
      "market_data": {
        "exchange": "alpaca",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        "websocket_url": "wss://stream.data.alpaca.markets/v2/iex",
        "reconnect_delay_ms": 5000,
        "zmq_publish_address": "tcp://0.0.0.0:5555"
      },
      "risk": {
        "max_position_size": 10000.0,
        "max_notional_exposure": 50000.0,
        "max_open_positions": 5,
        "max_loss_threshold": 5000.0,
        "enable_circuit_breaker": true
      },
      "execution": {
        "exchange_api_url": "https://api.alpaca.markets/v2",
        "rate_limit_per_second": 200,
        "retry_attempts": 3,
        "paper_trading": false
      }
    }
```

**Secret** (`k8s/secret.yaml`):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: trading-secrets
  namespace: trading-system
type: Opaque
stringData:
  ALPACA_API_KEY: "your_api_key_here"
  ALPACA_API_SECRET: "your_api_secret_here"
  DATABASE_URL: "postgresql://user:pass@postgres:5432/trading_db"
```

**Deployment - Market Data** (`k8s/market-data-deployment.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: market-data
  namespace: trading-system
  labels:
    app: market-data
    component: data-ingestion
spec:
  replicas: 2
  selector:
    matchLabels:
      app: market-data
  template:
    metadata:
      labels:
        app: market-data
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: market-data
              topologyKey: kubernetes.io/hostname
      containers:
      - name: market-data
        image: trading_market_data:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 5555
          name: zmq-pub
          protocol: TCP
        env:
        - name: RUST_LOG
          value: "info"
        - name: ALPACA_API_KEY
          valueFrom:
            secretKeyRef:
              name: trading-secrets
              key: ALPACA_API_KEY
        - name: ALPACA_API_SECRET
          valueFrom:
            secretKeyRef:
              name: trading-secrets
              key: ALPACA_API_SECRET
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "1Gi"
        livenessProbe:
          tcpSocket:
            port: 5555
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          tcpSocket:
            port: 5555
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
      volumes:
      - name: config
        configMap:
          name: trading-config
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: market-data
  namespace: trading-system
spec:
  selector:
    app: market-data
  ports:
  - port: 5555
    targetPort: 5555
    protocol: TCP
    name: zmq-pub
  type: ClusterIP
```

#### Step 2: Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy secrets (use sealed-secrets in production!)
kubectl apply -f k8s/secret.yaml

# Deploy config
kubectl apply -f k8s/configmap.yaml

# Deploy services
kubectl apply -f k8s/market-data-deployment.yaml
kubectl apply -f k8s/execution-engine-deployment.yaml
kubectl apply -f k8s/risk-manager-deployment.yaml

# Verify deployment
kubectl get pods -n trading-system
kubectl logs -n trading-system -l app=market-data -f
```

#### Step 3: Configure Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: market-data-hpa
  namespace: trading-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: market-data
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 4. Configuration Management

### 4.1 Environment-Specific Configurations

The system supports three environments: `development`, `staging`, `production`

**Configuration Files**:
- `config/system.json` - Development
- `config/system.staging.json` - Staging
- `config/system.production.json` - Production
- `config/risk_limits.toml` - Risk parameters

### 4.2 Configuration Validation

Before deployment, validate all configuration files:

```bash
./scripts/validate_config.sh --env production

# Expected output:
# ✓ system.production.json is valid
# ✓ risk_limits.toml is valid
# ✓ Environment variables are set
# ✓ API credentials are configured
# ✓ All services reachable
```

### 4.3 Runtime Configuration Updates

**For Native Deployment**:
```bash
# Update configuration
sudo nano /opt/trading-system/config/system.production.json

# Restart affected service
sudo systemctl restart trading-execution-engine
```

**For Docker Deployment**:
```bash
# Update config file
nano config/system.production.json

# Recreate container
docker compose -f docker/docker-compose.production.yml up -d --force-recreate execution_engine_service
```

**For Kubernetes**:
```bash
# Update ConfigMap
kubectl edit configmap trading-config -n trading-system

# Trigger rolling restart
kubectl rollout restart deployment/execution-engine -n trading-system
```

---

## 5. Security Hardening

### 5.1 TLS/SSL Configuration

**Enforce HTTPS for all API calls** (already implemented in code):

```rust
// In router.rs - HTTPS is enforced
let http_client = Client::builder()
    .timeout(std::time::Duration::from_secs(10))
    .min_tls_version(reqwest::tls::Version::TLS_1_2)
    .https_only(true)  // Production mode
    .build()
```

### 5.2 ZeroMQ Encryption

**CRITICAL**: Enable CurveZMQ encryption for inter-service communication:

```bash
# Generate key pairs
zmq_curve_keygen /opt/trading-system/keys/market-data

# Update environment with keys
echo "ZMQ_SERVER_PUBLIC_KEY=$(cat /opt/trading-system/keys/market-data.pub)" >> .env.production
echo "ZMQ_SERVER_SECRET_KEY=$(cat /opt/trading-system/keys/market-data.key)" >> .env.production
```

### 5.3 Secrets Management

**Production Best Practices**:

1. **Use a Secret Manager**: AWS Secrets Manager, HashiCorp Vault, or Kubernetes Secrets
2. **Rotate Credentials Regularly**: Every 90 days minimum
3. **Audit Access**: Log all secret retrievals
4. **Principle of Least Privilege**: Only grant necessary permissions

**Example with AWS Secrets Manager**:
```bash
# Store Alpaca credentials
aws secretsmanager create-secret \
    --name trading-system/alpaca/api-key \
    --secret-string "your_api_key"

# Retrieve in deployment script
export ALPACA_API_KEY=$(aws secretsmanager get-secret-value \
    --secret-id trading-system/alpaca/api-key \
    --query SecretString --output text)
```

### 5.4 Firewall Rules

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.0.0.0/24 to any port 5555 proto tcp comment "ZMQ Market Data"
sudo ufw allow from 10.0.0.0/24 to any port 5556 proto tcp comment "ZMQ Signals"
sudo ufw allow from 10.0.0.0/24 to any port 9100 proto tcp comment "Metrics"
sudo ufw enable
```

---

## 6. Database Setup

### 6.1 PostgreSQL Installation

```bash
# Install PostgreSQL 15
sudo apt-get install -y postgresql-15 postgresql-client-15

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 6.2 Create Trading Database

```sql
-- Connect as postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE trading_db;
CREATE USER trading_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;

-- Connect to trading database
\c trading_db

-- Create schema (from docs/architecture/database-persistence.md)
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    current_price DECIMAL(18, 8) NOT NULL,
    unrealized_pnl DECIMAL(18, 8) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short')),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, side)
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type VARCHAR(20) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),
    status VARCHAR(20) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    filled_quantity DECIMAL(18, 8) DEFAULT 0,
    filled_avg_price DECIMAL(18, 8)
);

CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL REFERENCES orders(order_id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    commission DECIMAL(18, 8) DEFAULT 0,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE daily_pnl (
    id SERIAL PRIMARY KEY,
    trading_date DATE NOT NULL UNIQUE,
    realized_pnl DECIMAL(18, 8) NOT NULL DEFAULT 0,
    unrealized_pnl DECIMAL(18, 8) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(18, 8) NOT NULL DEFAULT 0,
    trade_count INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_submitted_at ON orders(submitted_at);
CREATE INDEX idx_trades_order_id ON trades(order_id);
CREATE INDEX idx_trades_executed_at ON trades(executed_at);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_risk_events_occurred_at ON risk_events(occurred_at);

-- Enable row-level security (optional)
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
```

### 6.3 Configure Backups

```bash
# Create backup script
sudo nano /opt/trading-system/scripts/backup_db.sh
```

```bash
#!/bin/bash
# Database backup script

BACKUP_DIR="/opt/trading-system/backups/db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/trading_db_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -U trading_user -h localhost trading_db | gzip > $BACKUP_FILE

# Retain only last 30 days of backups
find $BACKUP_DIR -name "trading_db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

```bash
# Make executable
sudo chmod +x /opt/trading-system/scripts/backup_db.sh

# Add to crontab (backup every 6 hours)
sudo crontab -e
0 */6 * * * /opt/trading-system/scripts/backup_db.sh
```

---

## 7. Monitoring & Observability

### 7.1 Deploy Monitoring Stack

```bash
# Start Prometheus and Grafana
cd monitoring
docker compose up -d

# Access Grafana
# URL: http://localhost:3000
# Default: admin / admin
```

### 7.2 Configure Alerting

Edit `monitoring/alertmanager.yml`:

```yaml
route:
  receiver: 'trading-alerts'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
- name: 'trading-alerts'
  email_configs:
  - to: 'ops-team@company.com'
    from: 'trading-system@company.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'alerts@company.com'
    auth_password: 'app_password'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#trading-alerts'
    title: 'Trading System Alert'
```

### 7.3 Key Metrics to Monitor

See `docs/monitoring/monitoring-specification.md` for complete list:

- **Latency**: p50, p95, p99 order execution time
- **Throughput**: Orders per second
- **Error Rate**: Failed orders / Total orders
- **P&L**: Real-time profit/loss tracking
- **Circuit Breaker**: Status and trip events
- **WebSocket**: Connection status, message latency

---

## 8. Verification & Testing

### 8.1 Pre-Production Checklist

```bash
# Run comprehensive health check
./scripts/health_check.sh --production --verbose

# Verify all services are running
systemctl status trading-*
# OR
docker compose ps
# OR
kubectl get pods -n trading-system

# Test API connectivity
curl -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"

# Verify database connection
psql -U trading_user -d trading_db -c "SELECT NOW();"

# Check logs for errors
sudo journalctl -u trading-market-data --since "1 hour ago" | grep -i error
```

### 8.2 Paper Trading Validation

**CRITICAL**: Run in paper trading mode for minimum 1 week before going live!

```bash
# Set paper trading mode
export PAPER_TRADING=true
export ALPACA_API_URL=https://paper-api.alpaca.markets

# Restart services
sudo systemctl restart trading-*

# Monitor for issues
tail -f /opt/trading-system/logs/*.log
```

### 8.3 Load Testing

```bash
# Run load tests
cd tests
cargo test --release -- --ignored

# Run benchmarks
cargo bench

# Expected results:
# - Order book updates: <10μs
# - Risk checks: <5μs
# - End-to-end latency: <100μs (target)
```

---

## 9. Rollback Procedures

### 9.1 Native Deployment Rollback

```bash
# Stop current version
sudo systemctl stop trading-*

# Restore previous binaries
sudo cp /opt/trading-system/backups/v0.9.0/* /opt/trading-system/bin/

# Restore previous config
sudo cp /opt/trading-system/backups/config-v0.9.0/* /opt/trading-system/config/

# Restart services
sudo systemctl start trading-*

# Verify
./scripts/health_check.sh
```

### 9.2 Docker Rollback

```bash
# Stop current containers
docker compose -f docker/docker-compose.production.yml down

# Restore previous version
docker compose -f docker/docker-compose.production.yml pull
docker tag trading_market_data:v0.9.0 trading_market_data:latest

# Start previous version
docker compose -f docker/docker-compose.production.yml up -d
```

### 9.3 Kubernetes Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/market-data -n trading-system

# Verify rollback
kubectl rollout status deployment/market-data -n trading-system

# Check specific revision
kubectl rollout history deployment/market-data -n trading-system
kubectl rollout undo deployment/market-data --to-revision=2 -n trading-system
```

---

## Deployment Troubleshooting

### Service Won't Start

**Symptom**: Service fails to start with error
**Solution**:
```bash
# Check logs
sudo journalctl -u trading-market-data -n 100

# Verify configuration
./scripts/validate_config.sh

# Check file permissions
ls -la /opt/trading-system/

# Verify dependencies
ldd /opt/trading-system/bin/market-data
```

### API Connection Failures

**Symptom**: Cannot connect to Alpaca API
**Solution**:
```bash
# Test API connectivity
curl -v https://api.alpaca.markets/v2/account

# Check firewall
sudo ufw status

# Verify credentials
echo $ALPACA_API_KEY  # Should be set
```

### High Latency

**Symptom**: Order execution >100μs
**Solution**:
- Check network latency to exchange
- Review `docs/PERFORMANCE_ANALYSIS.md` for optimization
- Apply Phase 1 optimizations
- Consider moving to cloud region closer to exchange

---

## Emergency Stop Procedure

**CRITICAL**: Use when immediate trading halt is required

```bash
# Method 1: Stop all services
sudo systemctl stop trading-*

# Method 2: Trigger circuit breaker via API
curl -X POST http://localhost:8080/api/v1/circuit-breaker/trip

# Method 3: Emergency shutdown script
./scripts/emergency_stop.sh

# Verify all trading stopped
./scripts/health_check.sh
```

---

## Post-Deployment Checklist

- [ ] All services running and healthy
- [ ] Database schema created and backed up
- [ ] Monitoring dashboards accessible
- [ ] Alerts configured and tested
- [ ] API connectivity verified
- [ ] Paper trading validated (1+ week)
- [ ] Emergency stop procedure tested
- [ ] Rollback procedure documented
- [ ] Team trained on operations
- [ ] 24/7 on-call rotation established

---

## Support & Escalation

**On-Call Rotation**: Ensure 24/7 coverage during trading hours

**Escalation Path**:
1. **L1 Support**: Check health endpoints, review dashboards
2. **L2 Support**: Analyze logs, restart services if needed
3. **L3 Support**: Code-level debugging, emergency patches

**Contact Information**:
- **Primary On-Call**: [Phone/Slack]
- **Secondary On-Call**: [Phone/Slack]
- **Engineering Lead**: [Email/Phone]

---

## Additional Resources

- [Operations Runbook](../operations/OPERATIONS_RUNBOOK.md)
- [Troubleshooting Guide](../guides/troubleshooting.md)
- [Architecture Documentation](../architecture/SYSTEM_ARCHITECTURE.md)
- [Performance Tuning Guide](../PERFORMANCE_ANALYSIS.md)
- [Security Audit Report](../SECURITY_AUDIT_REPORT.md)

---

**Document Version**: 1.0.0
**Last Updated**: October 21, 2025
**Maintained By**: Documentation Specialist Agent
**Status**: Production Ready
