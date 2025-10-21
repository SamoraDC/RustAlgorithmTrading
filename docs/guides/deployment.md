# Production Deployment Guide

This guide covers deploying the py_rt algorithmic trading system to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Configuration](#configuration)
- [Deployment Methods](#deployment-methods)
- [Service Startup Sequence](#service-startup-sequence)
- [Verification](#verification)
- [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements

**Minimum Hardware**:
- CPU: 4 cores (8 cores recommended)
- RAM: 8GB (16GB recommended)
- Disk: 50GB SSD (NVMe recommended for low latency)
- Network: Low latency connection (<10ms to exchange)

**Operating System**:
- Ubuntu 22.04 LTS or later (recommended)
- Debian 11+ or RHEL 8+
- Docker Engine 24.0+ (for containerized deployment)

### Software Dependencies

#### Rust Environment

```bash
# Install Rust via rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Verify installation (requires 1.70+)
rustc --version
cargo --version

# Install required system libraries
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev libzmq3-dev
```

#### Python Environment

```bash
# Install Python 3.11+ (if not available)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Install uv package manager (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Alternative: use pip
python3.11 -m pip install --upgrade pip
```

#### ZeroMQ

ZeroMQ is required for inter-process communication between services.

```bash
# Install ZeroMQ library
sudo apt-get install -y libzmq3-dev

# Verify installation
pkg-config --modversion libzmq
```

## Environment Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/SamoraDC/RustAlgorithmTrading.git
cd RustAlgorithmTrading

# Checkout production branch or tag
git checkout v1.0.0  # or main for latest
```

### 2. API Keys and Credentials

Create `.env` file in the project root:

```bash
# Alpaca Markets API Credentials
APCA_API_KEY_ID=your_alpaca_api_key
APCA_API_SECRET_KEY=your_alpaca_secret_key
APCA_API_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
# APCA_API_BASE_URL=https://api.alpaca.markets       # Live trading

# Alpaca Data API
APCA_DATA_BASE_URL=https://data.alpaca.markets

# ZeroMQ Configuration
ZMQ_MARKET_DATA_ADDR=tcp://127.0.0.1:5555
ZMQ_SIGNAL_ADDR=tcp://127.0.0.1:5556
ZMQ_RISK_ADDR=tcp://127.0.0.1:5557
ZMQ_EXECUTION_ADDR=tcp://127.0.0.1:5558

# Logging Configuration
RUST_LOG=info
RUST_BACKTRACE=1

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PASSWORD=secure_password_here
```

**IMPORTANT**: Never commit `.env` file to version control. Add it to `.gitignore`.

### 3. Python Environment Setup

```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
uv pip install -e ".[dev]"

# Verify installation
python -c "import pandas, numpy, torch; print('Python environment ready')"
```

### 4. Rust Build

```bash
cd rust

# Build all services in release mode
cargo build --release --workspace

# Run tests to verify
cargo test --workspace --release

# Build artifacts will be in target/release/
ls -lh target/release/
```

## Configuration

### System Configuration

Copy and customize the production configuration template:

```bash
# Copy production template
cp config/system.production.json config/system.json

# Edit with your settings
nano config/system.json
```

**config/system.json** structure:

```json
{
  "market_data": {
    "exchange": "alpaca",
    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    "websocket_url": "wss://stream.data.alpaca.markets/v2/iex",
    "reconnect_delay_ms": 5000,
    "zmq_publish_address": "tcp://127.0.0.1:5555"
  },
  "risk": {
    "max_position_size": 1000.0,
    "max_notional_exposure": 50000.0,
    "max_open_positions": 5,
    "stop_loss_percent": 2.0,
    "trailing_stop_percent": 1.5,
    "enable_circuit_breaker": true,
    "max_loss_threshold": 5000.0
  },
  "execution": {
    "exchange_api_url": "https://paper-api.alpaca.markets/v2",
    "api_key": null,
    "api_secret": null,
    "rate_limit_per_second": 200,
    "retry_attempts": 3,
    "retry_delay_ms": 1000,
    "paper_trading": true
  },
  "signal": {
    "model_path": "models/trading_model.pkl",
    "features": [
      "rsi", "macd", "bollinger_bands",
      "moving_average_20", "moving_average_50",
      "volume_ratio", "price_momentum"
    ],
    "update_interval_ms": 1000,
    "zmq_subscribe_address": "tcp://127.0.0.1:5555",
    "zmq_publish_address": "tcp://127.0.0.1:5556"
  },
  "metadata": {
    "environment": "production",
    "version": "1.0.0"
  }
}
```

### Risk Limits Configuration

The `config/risk_limits.toml` file contains comprehensive risk management parameters. Review and adjust for your risk tolerance:

**Key Parameters to Configure**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_shares` | 1000 | Maximum shares per position |
| `max_notional_per_position` | $10,000 | Maximum position value |
| `max_total_exposure` | $50,000 | Maximum total portfolio exposure |
| `max_daily_loss` | $5,000 | Daily loss circuit breaker threshold |
| `max_slippage_percent` | 0.5% | Maximum acceptable slippage |

See `config/risk_limits.toml` for full configuration options.

## Deployment Methods

### Method 1: Native Deployment (Recommended for Low Latency)

Deploy services directly on the host OS for minimal latency.

#### 1. Create System Service Files

Create systemd service files for each Rust component:

**`/etc/systemd/system/trading-market-data.service`**:

```ini
[Unit]
Description=Trading System - Market Data Service
After=network.target
Requires=network.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory=/opt/RustAlgorithmTrading
EnvironmentFile=/opt/RustAlgorithmTrading/.env
ExecStart=/opt/RustAlgorithmTrading/rust/target/release/market-data
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading-market-data

# Resource limits
LimitNOFILE=65535
LimitNPROC=4096

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/RustAlgorithmTrading/logs /opt/RustAlgorithmTrading/data

[Install]
WantedBy=multi-user.target
```

Create similar service files for other components:
- `trading-risk-manager.service`
- `trading-execution-engine.service`
- `trading-signal-bridge.service`

#### 2. Install and Enable Services

```bash
# Copy service files
sudo cp scripts/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable trading-market-data
sudo systemctl enable trading-risk-manager
sudo systemctl enable trading-execution-engine
sudo systemctl enable trading-signal-bridge

# Start services (see startup sequence below)
sudo systemctl start trading-market-data
sleep 5
sudo systemctl start trading-risk-manager
sleep 2
sudo systemctl start trading-execution-engine
sleep 2
sudo systemctl start trading-signal-bridge
```

#### 3. Verify Services

```bash
# Check status
sudo systemctl status trading-market-data
sudo systemctl status trading-risk-manager
sudo systemctl status trading-execution-engine
sudo systemctl status trading-signal-bridge

# View logs
sudo journalctl -u trading-market-data -f
```

### Method 2: Docker Deployment

Use Docker for isolated, reproducible deployments.

#### 1. Build Docker Images

```bash
# Build all service images
docker-compose -f docker/docker-compose.yml build

# Verify images
docker images | grep trading
```

#### 2. Deploy with Docker Compose

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Check service health
docker-compose -f docker/docker-compose.yml ps
```

#### 3. Docker Service Management

```bash
# Stop all services
docker-compose -f docker/docker-compose.yml down

# Restart specific service
docker-compose -f docker/docker-compose.yml restart market_data_service

# View service logs
docker-compose -f docker/docker-compose.yml logs -f market_data_service

# Execute command in container
docker-compose -f docker/docker-compose.yml exec market_data_service /bin/bash
```

### Method 3: Kubernetes Deployment (Enterprise)

For large-scale, distributed deployments.

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/

# Check deployment status
kubectl get pods -n trading-system
kubectl get services -n trading-system
```

See `docs/guides/kubernetes-deployment.md` for detailed K8s setup.

## Service Startup Sequence

Services must be started in the correct order due to ZeroMQ dependencies.

### Startup Order

```
1. Market Data Service (provides data stream)
   ↓ (wait 5-10 seconds for WebSocket connection)
2. Risk Manager (subscribes to market data)
   ↓ (wait 2-3 seconds)
3. Execution Engine (connects to risk manager)
   ↓ (wait 2-3 seconds)
4. Signal Bridge (connects to all services)
```

### Manual Startup (Native)

```bash
# 1. Start market data service
cd /opt/RustAlgorithmTrading/rust/market-data
RUST_LOG=info cargo run --release &
MARKET_PID=$!
echo "Market Data PID: $MARKET_PID"
sleep 10  # Wait for WebSocket connection

# 2. Start risk manager
cd /opt/RustAlgorithmTrading/rust/risk-manager
RUST_LOG=info cargo run --release &
RISK_PID=$!
echo "Risk Manager PID: $RISK_PID"
sleep 3

# 3. Start execution engine
cd /opt/RustAlgorithmTrading/rust/execution-engine
RUST_LOG=info cargo run --release &
EXEC_PID=$!
echo "Execution Engine PID: $EXEC_PID"
sleep 3

# 4. Start signal bridge
cd /opt/RustAlgorithmTrading/rust/signal-bridge
RUST_LOG=info cargo run --release &
SIGNAL_PID=$!
echo "Signal Bridge PID: $SIGNAL_PID"

# Save PIDs for later management
echo "$MARKET_PID $RISK_PID $EXEC_PID $SIGNAL_PID" > /tmp/trading_pids.txt
```

### Automated Startup Script

Use the provided startup script:

```bash
# Make executable
chmod +x scripts/start_trading_system.sh

# Start all services
./scripts/start_trading_system.sh

# Monitor startup
tail -f logs/trading_system.log
```

### Docker Startup

Docker Compose handles startup order automatically via `depends_on` and health checks:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

## Verification

### Health Checks

#### 1. Check Process Status

**Native Deployment**:
```bash
# Check systemd services
sudo systemctl status trading-market-data
sudo systemctl status trading-risk-manager
sudo systemctl status trading-execution-engine
sudo systemctl status trading-signal-bridge

# Check process existence
ps aux | grep -E '(market-data|risk-manager|execution-engine|signal-bridge)'
```

**Docker Deployment**:
```bash
# Check container health
docker-compose -f docker/docker-compose.yml ps

# Should show all services as "healthy"
```

#### 2. Check ZeroMQ Connections

```bash
# Install zmq_monitor tool
pip install pyzmq

# Monitor ZeroMQ traffic
python scripts/monitor_zmq.py tcp://localhost:5555  # Market data
python scripts/monitor_zmq.py tcp://localhost:5556  # Signals
python scripts/monitor_zmq.py tcp://localhost:5557  # Risk
python scripts/monitor_zmq.py tcp://localhost:5558  # Execution
```

#### 3. Check Logs

**Native Deployment**:
```bash
# View systemd logs
sudo journalctl -u trading-market-data -n 100
sudo journalctl -u trading-risk-manager -n 100

# View file logs
tail -f logs/market_data.log
tail -f logs/risk_manager.log
tail -f logs/execution_engine.log
```

**Docker Deployment**:
```bash
# View container logs
docker-compose -f docker/docker-compose.yml logs -f market_data_service
docker-compose -f docker/docker-compose.yml logs -f risk_management_service
```

#### 4. Verify Metrics Endpoint

```bash
# Check Prometheus metrics
curl http://localhost:9090/metrics | grep trading_

# Expected metrics:
# - trading_messages_processed_total
# - trading_orders_executed_total
# - trading_risk_checks_total
# - trading_latency_seconds
```

#### 5. End-to-End Test

Run the integration test suite:

```bash
# Native deployment
cd tests
cargo test --test integration --release

# Docker deployment
docker-compose -f docker/docker-compose.yml exec strategy_engine \
  cargo test --test integration --release
```

### Monitoring Dashboard

Access Grafana dashboard for real-time monitoring:

```bash
# Open browser
xdg-open http://localhost:3000

# Default credentials
Username: admin
Password: (value from GRAFANA_PASSWORD in .env)
```

Pre-configured dashboards:
- **Trading System Overview**: Overall system health
- **Market Data Performance**: WebSocket latency, message rates
- **Order Execution Metrics**: Fill rates, slippage, latency
- **Risk Management**: Position limits, P&L, circuit breaker status

## Security Considerations

### API Key Protection

```bash
# Set restrictive permissions on .env file
chmod 600 .env

# Use secrets management in production
# Example with HashiCorp Vault:
vault kv put secret/trading/alpaca \
  api_key=$APCA_API_KEY_ID \
  api_secret=$APCA_API_SECRET_KEY
```

### Network Security

```bash
# Firewall rules (allow only necessary ports)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 3000/tcp    # Grafana (restrict to VPN)
sudo ufw allow 9090/tcp    # Prometheus (restrict to VPN)
sudo ufw enable

# ZeroMQ ports should NOT be exposed externally
# Use localhost binding: tcp://127.0.0.1:5555
```

### User Permissions

```bash
# Create dedicated trading user
sudo useradd -r -s /bin/bash -d /opt/RustAlgorithmTrading trading

# Set ownership
sudo chown -R trading:trading /opt/RustAlgorithmTrading

# Restrict file permissions
chmod 750 /opt/RustAlgorithmTrading
chmod 600 /opt/RustAlgorithmTrading/.env
chmod 640 /opt/RustAlgorithmTrading/config/*.json
```

### SSL/TLS Configuration

Enable TLS for WebSocket connections to exchanges:

```json
{
  "market_data": {
    "websocket_url": "wss://stream.data.alpaca.markets/v2/iex",
    "tls_verify": true,
    "tls_cert_path": "/etc/ssl/certs/alpaca.pem"
  }
}
```

### Audit Logging

Enable comprehensive audit logging:

```bash
# Set RUST_LOG for detailed logs
export RUST_LOG=info,market_data=debug,execution_engine=debug

# Configure log rotation
sudo apt-get install logrotate

# Create /etc/logrotate.d/trading-system
cat > /etc/logrotate.d/trading-system <<EOF
/opt/RustAlgorithmTrading/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 trading trading
}
EOF
```

## Production Checklist

Before going live, verify:

- [ ] API keys are valid and have correct permissions
- [ ] Paper trading is enabled (`paper_trading: true` in config)
- [ ] Risk limits are properly configured
- [ ] All services start in correct order
- [ ] ZeroMQ connections are established
- [ ] Metrics are being collected (Prometheus)
- [ ] Dashboards are accessible (Grafana)
- [ ] Logs are being written and rotated
- [ ] Backup procedures are in place
- [ ] Alerting is configured (email/SMS/webhook)
- [ ] Emergency stop procedures documented
- [ ] Circuit breaker tested

## Troubleshooting Quick Reference

| Issue | Check | Solution |
|-------|-------|----------|
| Service won't start | Logs: `journalctl -u trading-*` | Check dependencies, ports, config |
| No market data | WebSocket connection | Verify API keys, network connectivity |
| Orders not executing | Risk manager status | Check risk limits, circuit breaker |
| High latency | Prometheus metrics | Check CPU, network, ZeroMQ queues |
| Memory leak | `ps aux` memory usage | Restart service, check for message buildup |

See [docs/guides/troubleshooting.md](troubleshooting.md) for detailed troubleshooting procedures.

## Next Steps

- [Operations Guide](operations.md) - Day-to-day operational procedures
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [Monitoring Guide](monitoring.md) - Metrics and alerting configuration
- [Backup and Recovery](backup-recovery.md) - Disaster recovery procedures

## Support

For deployment issues:
- GitHub Issues: https://github.com/SamoraDC/RustAlgorithmTrading/issues
- Documentation: https://github.com/SamoraDC/RustAlgorithmTrading/docs
- Email: davi.samora@example.com
