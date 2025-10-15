# Production Deployment Guide

This guide covers deploying the Rust Algorithm Trading System to production environments.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Docker Deployment](#docker-deployment)
3. [Systemd Services](#systemd-services)
4. [Cloud Deployment](#cloud-deployment)
5. [Monitoring](#monitoring)
6. [Security Best Practices](#security-best-practices)
7. [Disaster Recovery](#disaster-recovery)

## Deployment Options

### Option 1: Docker Containers (Recommended)

**Pros**:
- Isolated environments
- Easy scaling with Kubernetes/Docker Swarm
- Reproducible deployments
- Resource limits

**Cons**:
- Slight performance overhead (~5%)
- Additional complexity

### Option 2: Systemd Services

**Pros**:
- Native performance
- Simple deployment
- System integration

**Cons**:
- Manual dependency management
- Harder to scale

### Option 3: Cloud Managed Services

**Pros**:
- Managed infrastructure
- Auto-scaling
- High availability

**Cons**:
- Higher costs
- Vendor lock-in

## Docker Deployment

### Create Dockerfiles

#### Base Dockerfile (`rust/Dockerfile`)

```dockerfile
# Multi-stage build for smaller images
FROM rust:1.77-slim as builder

# Install dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy workspace files
COPY Cargo.toml Cargo.lock ./
COPY common ./common
COPY market-data ./market-data
COPY signal-bridge ./signal-bridge
COPY risk-manager ./risk-manager
COPY execution-engine ./execution-engine

# Build release binaries
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    libzmq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy binaries from builder
COPY --from=builder /app/target/release/market-data /usr/local/bin/
COPY --from=builder /app/target/release/signal-bridge /usr/local/bin/
COPY --from=builder /app/target/release/risk-manager /usr/local/bin/
COPY --from=builder /app/target/release/execution-engine /usr/local/bin/

# Create non-root user
RUN useradd -ms /bin/bash trading
USER trading

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD pgrep -x market-data || exit 1

# Default command
CMD ["market-data"]
```

#### Component-Specific Dockerfiles

Create individual Dockerfiles for each component:

```dockerfile
# rust/market-data/Dockerfile
FROM rust:1.77-slim as builder
# ... (same as above)
CMD ["market-data"]
EXPOSE 5555

# rust/signal-bridge/Dockerfile
FROM rust:1.77-slim as builder
# ... (same as above)
CMD ["signal-bridge"]
EXPOSE 5556

# rust/risk-manager/Dockerfile
FROM rust:1.77-slim as builder
# ... (same as above)
CMD ["risk-manager"]
EXPOSE 5557

# rust/execution-engine/Dockerfile
FROM rust:1.77-slim as builder
# ... (same as above)
CMD ["execution-engine"]
EXPOSE 5558
```

### Build Docker Images

```bash
cd rust

# Build all images
docker build -t trading/market-data:latest -f market-data/Dockerfile .
docker build -t trading/signal-bridge:latest -f signal-bridge/Dockerfile .
docker build -t trading/risk-manager:latest -f risk-manager/Dockerfile .
docker build -t trading/execution-engine:latest -f execution-engine/Dockerfile .

# Verify images
docker images | grep trading
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  market-data:
    image: trading/market-data:latest
    container_name: market-data
    restart: unless-stopped
    environment:
      - RUST_LOG=info
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
    ports:
      - "5555:5555"
      - "9090:9090"  # Prometheus metrics
    volumes:
      - ./config:/config:ro
      - ./logs:/logs
    networks:
      - trading-net
    healthcheck:
      test: ["CMD", "pgrep", "-x", "market-data"]
      interval: 30s
      timeout: 5s
      retries: 3

  signal-bridge:
    image: trading/signal-bridge:latest
    container_name: signal-bridge
    restart: unless-stopped
    environment:
      - RUST_LOG=info
    ports:
      - "5556:5556"
      - "9091:9090"
    volumes:
      - ./config:/config:ro
      - ./models:/models:ro
      - ./logs:/logs
    depends_on:
      - market-data
    networks:
      - trading-net

  risk-manager:
    image: trading/risk-manager:latest
    container_name: risk-manager
    restart: unless-stopped
    environment:
      - RUST_LOG=info
    ports:
      - "5557:5557"
      - "9092:9090"
    volumes:
      - ./config:/config:ro
      - ./logs:/logs
    depends_on:
      - market-data
      - signal-bridge
    networks:
      - trading-net

  execution-engine:
    image: trading/execution-engine:latest
    container_name: execution-engine
    restart: unless-stopped
    environment:
      - RUST_LOG=info
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
    ports:
      - "5558:5558"
      - "9093:9090"
    volumes:
      - ./config:/config:ro
      - ./logs:/logs
    depends_on:
      - risk-manager
    networks:
      - trading-net

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - trading-net

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-clock-panel
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning:ro
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - trading-net

networks:
  trading-net:
    driver: bridge

volumes:
  prometheus-data:
  grafana-data:
```

### Environment Variables

Create `.env` file (never commit this!):

```bash
# Alpaca API credentials
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# Logging
RUST_LOG=info

# Monitoring
PROMETHEUS_RETENTION=30d
```

### Start System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop system
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Systemd Services

### Create Service Files

Create `/etc/systemd/system/trading-market-data.service`:

```ini
[Unit]
Description=Trading System - Market Data Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory=/opt/trading
Environment="RUST_LOG=info"
Environment="ALPACA_API_KEY=your_key"
Environment="ALPACA_SECRET_KEY=your_secret"
ExecStart=/opt/trading/bin/market-data
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

Create similar files for other components:
- `trading-signal-bridge.service`
- `trading-risk-manager.service`
- `trading-execution-engine.service`

### Deploy Binaries

```bash
# Build release binaries
cd rust
cargo build --release

# Create deployment directory
sudo mkdir -p /opt/trading/bin
sudo mkdir -p /opt/trading/config
sudo mkdir -p /opt/trading/logs

# Copy binaries
sudo cp target/release/market-data /opt/trading/bin/
sudo cp target/release/signal-bridge /opt/trading/bin/
sudo cp target/release/risk-manager /opt/trading/bin/
sudo cp target/release/execution-engine /opt/trading/bin/

# Copy configuration
sudo cp config/system.json /opt/trading/config/

# Create user
sudo useradd -r -s /bin/false trading
sudo chown -R trading:trading /opt/trading
sudo chmod 700 /opt/trading/config
sudo chmod 600 /opt/trading/config/system.json
```

### Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable trading-market-data
sudo systemctl enable trading-signal-bridge
sudo systemctl enable trading-risk-manager
sudo systemctl enable trading-execution-engine

# Start services
sudo systemctl start trading-market-data
sudo systemctl start trading-signal-bridge
sudo systemctl start trading-risk-manager
sudo systemctl start trading-execution-engine

# Check status
sudo systemctl status trading-market-data
sudo journalctl -u trading-market-data -f
```

## Cloud Deployment

### AWS Deployment

#### EC2 Instance

1. **Launch EC2 Instance**:
   - Instance type: t3.medium (2 vCPU, 4 GB RAM) minimum
   - AMI: Ubuntu 22.04 LTS
   - Storage: 20 GB gp3
   - Security group: Allow ports 22 (SSH), 5555-5558 (ZMQ)

2. **Install Dependencies**:
```bash
ssh ubuntu@your-ec2-ip

sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
```

3. **Deploy with Docker Compose**:
```bash
git clone https://github.com/SamoraDC/RustAlgorithmTrading.git
cd RustAlgorithmTrading
docker-compose up -d
```

#### ECS (Elastic Container Service)

1. **Push Images to ECR**:
```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag and push images
docker tag trading/market-data:latest \
    123456789012.dkr.ecr.us-east-1.amazonaws.com/trading/market-data:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/trading/market-data:latest
```

2. **Create ECS Task Definition** (see AWS documentation)

3. **Create ECS Service** with Application Load Balancer

### Google Cloud Platform

#### Compute Engine

Similar to EC2 deployment above.

#### Cloud Run

1. **Build and push to GCR**:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/market-data
```

2. **Deploy to Cloud Run**:
```bash
gcloud run deploy market-data \
    --image gcr.io/PROJECT_ID/market-data \
    --platform managed \
    --region us-central1 \
    --memory 512Mi
```

## Monitoring

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
      - targets: ['signal-bridge:9090']

  - job_name: 'risk-manager'
    static_configs:
      - targets: ['risk-manager:9090']

  - job_name: 'execution-engine'
    static_configs:
      - targets: ['execution-engine:9090']
```

### Grafana Dashboard

Import pre-built dashboard (create `monitoring/grafana/dashboard.json`):

```json
{
  "dashboard": {
    "title": "Trading System Metrics",
    "panels": [
      {
        "title": "Message Processing Rate",
        "targets": [
          {
            "expr": "rate(messages_processed_total[5m])"
          }
        ]
      },
      {
        "title": "Order Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, order_latency_seconds_bucket)"
          }
        ]
      }
    ]
  }
}
```

Access Grafana at `http://localhost:3000` (admin/admin)

### Alerting

Create `monitoring/alerts.yml`:

```yaml
groups:
  - name: trading_alerts
    interval: 30s
    rules:
      - alert: HighMessageLatency
        expr: histogram_quantile(0.99, message_latency_seconds_bucket) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High message processing latency"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
```

## Security Best Practices

### 1. API Key Management

**Never hardcode API keys!**

Use environment variables or secret management:

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value \
    --secret-id trading/alpaca-api-key \
    --query SecretString --output text

# HashiCorp Vault
vault kv get -field=api_key secret/trading/alpaca
```

### 2. Network Security

- Use VPC/private networks
- Restrict ZMQ ports to internal network
- Enable TLS for ZMQ (TODO: implement)
- Use security groups/firewalls

### 3. Container Security

```dockerfile
# Use non-root user
USER trading

# Read-only root filesystem
# (requires writable volumes for /tmp, /logs)
```

### 4. Logging

- Never log API keys or secrets
- Sanitize sensitive data in logs
- Use structured logging with tracing

```rust
#[tracing::instrument(skip(api_key))]
async fn call_api(api_key: &str) {
    // api_key won't appear in logs
}
```

## Disaster Recovery

### Backup Strategy

1. **Configuration**: Store in Git (encrypted secrets)
2. **Code**: Git repository with tags for releases
3. **Position Data**: Periodic snapshots to S3/GCS (future)

### Recovery Procedures

#### Service Crash

```bash
# Docker
docker-compose restart market-data

# Systemd
sudo systemctl restart trading-market-data
```

#### Data Loss

```bash
# Restore from backup (future)
aws s3 cp s3://trading-backups/positions.db /opt/trading/data/
```

#### Full System Recovery

1. Provision new infrastructure
2. Deploy latest Docker images
3. Restore configuration and secrets
4. Verify connectivity to Alpaca API
5. Start services in order: market-data → signal-bridge → risk-manager → execution-engine

### Monitoring Checklist

- [ ] Prometheus scraping all components
- [ ] Grafana dashboards showing real-time metrics
- [ ] Alerts configured for critical failures
- [ ] Log aggregation (ELK/Splunk) (optional)
- [ ] Uptime monitoring (Pingdom/UptimeRobot)

---

**Last Updated**: 2024-10-14 | **Maintainer**: Davi Castro Samora
