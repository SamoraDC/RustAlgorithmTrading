# Deployment Guide

Complete guide for deploying the py_rt trading system to production.

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [System Requirements](#system-requirements)
3. [Production Configuration](#production-configuration)
4. [Systemd Services](#systemd-services)
5. [Docker Deployment](#docker-deployment)
6. [Monitoring Setup](#monitoring-setup)
7. [Security Hardening](#security-hardening)
8. [Backup and Recovery](#backup-and-recovery)

## Deployment Overview

The py_rt system consists of four independent services that can be deployed separately or together.

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Production Server                     │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Market Data  │  │Signal Bridge │  │Risk Manager  │  │
│  │   Service    │  │   Service    │  │   Service    │  │
│  │   :5555      │  │   :5556      │  │   :5557      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│          │                 │                 │          │
│          └─────────────────┴─────────────────┘          │
│                           │                             │
│                  ┌────────▼─────────┐                   │
│                  │   Execution      │                   │
│                  │    Engine        │                   │
│                  │    :5558         │                   │
│                  └──────────────────┘                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Prometheus   │  │   Grafana    │  │     Logs     │  │
│  │   :9090      │  │    :3000     │  │  /var/log    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## System Requirements

### Hardware Requirements

**Minimum**:
- CPU: 4 cores (Intel i5 or equivalent)
- RAM: 8 GB
- Storage: 50 GB SSD
- Network: 10 Mbps stable connection

**Recommended**:
- CPU: 8+ cores (Intel i7/Ryzen 7 or better)
- RAM: 16 GB
- Storage: 100 GB NVMe SSD
- Network: 100 Mbps with low latency

### Software Requirements

```bash
# Operating System
Ubuntu 22.04 LTS (recommended) or
Debian 11+ or
RHEL 8+

# Runtime
Rust 1.70+
Python 3.11+
uv package manager

# Dependencies
libzmq3-dev
build-essential
pkg-config
libssl-dev
```

### Network Requirements

- Stable internet connection
- Low latency to Alpaca Markets (<50ms recommended)
- Open outbound connections to:
  - `api.alpaca.markets` (HTTPS)
  - `data.alpaca.markets` (WebSocket)

## Production Configuration

### Environment Variables

Create `/etc/py_rt/.env`:

```bash
# Alpaca API (PRODUCTION)
ALPACA_API_KEY=your_live_api_key
ALPACA_SECRET_KEY=your_live_secret_key
ALPACA_BASE_URL=https://api.alpaca.markets
ALPACA_DATA_URL=https://data.alpaca.markets

# System
RUST_LOG=info
LOG_LEVEL=INFO
RUST_BACKTRACE=1

# Paths
DATA_DIR=/var/lib/py_rt
LOG_DIR=/var/log/py_rt
CONFIG_DIR=/etc/py_rt

# Security
ENABLE_TLS=true
TLS_CERT_PATH=/etc/py_rt/certs/cert.pem
TLS_KEY_PATH=/etc/py_rt/certs/key.pem
```

### System Configuration

Create `/etc/py_rt/system.json`:

```json
{
  "market_data": {
    "alpaca_api_key": "${ALPACA_API_KEY}",
    "alpaca_secret_key": "${ALPACA_SECRET_KEY}",
    "zmq_pub_address": "tcp://127.0.0.1:5555",
    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    "reconnect_delay_secs": 5,
    "heartbeat_interval_secs": 30,
    "max_reconnect_attempts": 10
  },
  "signal_bridge": {
    "zmq_sub_address": "tcp://127.0.0.1:5555",
    "zmq_pub_address": "tcp://127.0.0.1:5556",
    "python_module": "src.strategies.ml.models",
    "model_path": "/var/lib/py_rt/models",
    "update_interval_secs": 60
  },
  "risk_manager": {
    "zmq_sub_address": "tcp://127.0.0.1:5555,tcp://127.0.0.1:5556",
    "zmq_pub_address": "tcp://127.0.0.1:5557",
    "max_position_size": 50000.0,
    "max_order_size": 5000.0,
    "max_daily_loss": 10000.0,
    "position_limit_pct": 0.05,
    "enable_circuit_breaker": true,
    "circuit_breaker_threshold": 0.03,
    "persistence_enabled": true,
    "db_path": "/var/lib/py_rt/positions.db"
  },
  "execution_engine": {
    "alpaca_api_key": "${ALPACA_API_KEY}",
    "alpaca_secret_key": "${ALPACA_SECRET_KEY}",
    "zmq_sub_address": "tcp://127.0.0.1:5557",
    "zmq_pub_address": "tcp://127.0.0.1:5558",
    "max_retries": 3,
    "max_slippage_bps": 50,
    "rate_limit_per_minute": 200,
    "enable_dry_run": false
  },
  "monitoring": {
    "prometheus_enabled": true,
    "prometheus_port": 9090,
    "metrics_interval_secs": 10
  },
  "logging": {
    "level": "info",
    "format": "json",
    "output": "file",
    "log_dir": "/var/log/py_rt",
    "max_size_mb": 100,
    "max_backups": 10
  }
}
```

## Systemd Services

### Market Data Service

Create `/etc/systemd/system/py_rt-market-data.service`:

```ini
[Unit]
Description=py_rt Market Data Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=py_rt
Group=py_rt
WorkingDirectory=/opt/py_rt
EnvironmentFile=/etc/py_rt/.env
ExecStart=/opt/py_rt/rust/target/release/market-data
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=py_rt-market-data

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/py_rt /var/log/py_rt

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### Signal Bridge Service

Create `/etc/systemd/system/py_rt-signal-bridge.service`:

```ini
[Unit]
Description=py_rt Signal Bridge Service
After=network.target py_rt-market-data.service
Requires=py_rt-market-data.service

[Service]
Type=simple
User=py_rt
Group=py_rt
WorkingDirectory=/opt/py_rt
EnvironmentFile=/etc/py_rt/.env
ExecStart=/opt/py_rt/rust/target/release/signal-bridge
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=py_rt-signal-bridge

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/py_rt /var/log/py_rt

[Install]
WantedBy=multi-user.target
```

### Risk Manager Service

Create `/etc/systemd/system/py_rt-risk-manager.service`:

```ini
[Unit]
Description=py_rt Risk Manager Service
After=network.target py_rt-signal-bridge.service
Requires=py_rt-signal-bridge.service

[Service]
Type=simple
User=py_rt
Group=py_rt
WorkingDirectory=/opt/py_rt
EnvironmentFile=/etc/py_rt/.env
ExecStart=/opt/py_rt/rust/target/release/risk-manager
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=py_rt-risk-manager

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/py_rt /var/log/py_rt

[Install]
WantedBy=multi-user.target
```

### Execution Engine Service

Create `/etc/systemd/system/py_rt-execution-engine.service`:

```ini
[Unit]
Description=py_rt Execution Engine Service
After=network.target py_rt-risk-manager.service
Requires=py_rt-risk-manager.service

[Service]
Type=simple
User=py_rt
Group=py_rt
WorkingDirectory=/opt/py_rt
EnvironmentFile=/etc/py_rt/.env
ExecStart=/opt/py_rt/rust/target/release/execution-engine
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=py_rt-execution-engine

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/py_rt /var/log/py_rt

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable py_rt-market-data
sudo systemctl enable py_rt-signal-bridge
sudo systemctl enable py_rt-risk-manager
sudo systemctl enable py_rt-execution-engine

# Start services
sudo systemctl start py_rt-market-data
sudo systemctl start py_rt-signal-bridge
sudo systemctl start py_rt-risk-manager
sudo systemctl start py_rt-execution-engine

# Check status
sudo systemctl status py_rt-*
```

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
# Build stage
FROM rust:1.75-slim as builder

WORKDIR /build

# Install dependencies
RUN apt-get update && apt-get install -y \
    libzmq3-dev \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy workspace
COPY rust/ .

# Build release binaries
RUN cargo build --release --workspace

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libzmq5 \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -u 1000 -s /bin/bash py_rt

# Copy binaries
COPY --from=builder /build/target/release/market-data /usr/local/bin/
COPY --from=builder /build/target/release/signal-bridge /usr/local/bin/
COPY --from=builder /build/target/release/risk-manager /usr/local/bin/
COPY --from=builder /build/target/release/execution-engine /usr/local/bin/

# Create directories
RUN mkdir -p /var/lib/py_rt /var/log/py_rt && \
    chown -R py_rt:py_rt /var/lib/py_rt /var/log/py_rt

USER py_rt
WORKDIR /home/py_rt

EXPOSE 5555 5556 5557 5558 9090

CMD ["market-data"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  market-data:
    build: .
    container_name: py_rt-market-data
    command: market-data
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - RUST_LOG=info
    volumes:
      - ./config:/etc/py_rt:ro
      - market-data-logs:/var/log/py_rt
    ports:
      - "5555:5555"
      - "9090:9090"
    restart: unless-stopped
    networks:
      - py_rt-network

  signal-bridge:
    build: .
    container_name: py_rt-signal-bridge
    command: signal-bridge
    environment:
      - RUST_LOG=info
    volumes:
      - ./config:/etc/py_rt:ro
      - signal-bridge-logs:/var/log/py_rt
      - models:/var/lib/py_rt/models
    ports:
      - "5556:5556"
    depends_on:
      - market-data
    restart: unless-stopped
    networks:
      - py_rt-network

  risk-manager:
    build: .
    container_name: py_rt-risk-manager
    command: risk-manager
    environment:
      - RUST_LOG=info
    volumes:
      - ./config:/etc/py_rt:ro
      - risk-manager-logs:/var/log/py_rt
      - positions-db:/var/lib/py_rt
    ports:
      - "5557:5557"
    depends_on:
      - signal-bridge
    restart: unless-stopped
    networks:
      - py_rt-network

  execution-engine:
    build: .
    container_name: py_rt-execution-engine
    command: execution-engine
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - RUST_LOG=info
    volumes:
      - ./config:/etc/py_rt:ro
      - execution-engine-logs:/var/log/py_rt
    ports:
      - "5558:5558"
    depends_on:
      - risk-manager
    restart: unless-stopped
    networks:
      - py_rt-network

  prometheus:
    image: prom/prometheus:latest
    container_name: py_rt-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9091:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped
    networks:
      - py_rt-network

  grafana:
    image: grafana/grafana:latest
    container_name: py_rt-grafana
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - py_rt-network

volumes:
  market-data-logs:
  signal-bridge-logs:
  risk-manager-logs:
  execution-engine-logs:
  positions-db:
  models:
  prometheus-data:
  grafana-data:

networks:
  py_rt-network:
    driver: bridge
```

### Deploy with Docker

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Monitoring Setup

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'market-data'
    static_configs:
      - targets: ['market-data:9090']

  - job_name: 'signal-bridge'
    static_configs:
      - targets: ['signal-bridge:9091']

  - job_name: 'risk-manager'
    static_configs:
      - targets: ['risk-manager:9092']

  - job_name: 'execution-engine'
    static_configs:
      - targets: ['execution-engine:9093']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'
```

### Grafana Dashboards

See `monitoring/grafana/dashboards/` for pre-built dashboards.

## Security Hardening

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 3000/tcp  # Grafana
sudo ufw enable
```

### TLS Configuration

Generate certificates:

```bash
# Create CA
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 365 -key ca.key -out ca.crt

# Create server certificate
openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt
```

### Secrets Management

```bash
# Use environment variables (not in code)
export ALPACA_API_KEY=...
export ALPACA_SECRET_KEY=...

# Or use secrets manager
aws secretsmanager get-secret-value --secret-id py_rt/alpaca
```

## Backup and Recovery

### Backup Script

Create `/opt/py_rt/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backup/py_rt"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup positions database
cp /var/lib/py_rt/positions.db "$BACKUP_DIR/$DATE/"

# Backup configuration
cp -r /etc/py_rt "$BACKUP_DIR/$DATE/"

# Backup logs (compressed)
tar -czf "$BACKUP_DIR/$DATE/logs.tar.gz" /var/log/py_rt

# Delete old backups (keep last 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR/$DATE"
```

### Cron Job

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/py_rt/backup.sh >> /var/log/py_rt/backup.log 2>&1
```

## Next Steps

- [Monitoring Guide](../guides/monitoring.md) - Set up dashboards
- [Troubleshooting](troubleshooting.md) - Common issues
- [Performance Tuning](performance.md) - Optimization guide

---

**Last Updated**: 2025-10-14
