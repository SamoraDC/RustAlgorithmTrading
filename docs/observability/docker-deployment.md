# Docker Observability Deployment Guide

Complete guide for deploying the observability stack with Docker.

## 🎯 Overview

The Docker observability stack includes:
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Alertmanager** - Alert routing
- **FastAPI Observability Server** - Custom metrics API
- **Node Exporter** - System metrics (optional)
- **cAdvisor** - Container metrics (optional)

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 10GB disk space
- Linux/macOS/Windows with WSL2

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd docker
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Services

```bash
# Using Make (recommended)
make up

# Or using Docker Compose directly
docker-compose -f docker-compose.observability.yml up -d
```

### 3. Verify Services

```bash
# Check status
make status

# Check health
make health

# View logs
make logs
```

### 4. Access Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Observability API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Alertmanager**: http://localhost:9093

## 🔧 Configuration

### Environment Variables

Edit `docker/.env`:

```bash
# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure_password_here

# Observability API
WORKERS=2
ENABLE_CORS=true
API_PREFIX=/api/v1

# Prometheus
PROMETHEUS_RETENTION_TIME=30d

# Resource Limits
PROMETHEUS_MEM_LIMIT=512M
GRAFANA_MEM_LIMIT=512M
API_MEM_LIMIT=1G
```

### Prometheus Configuration

Create `docker/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/alerts.yml'

scrape_configs:
  # Trading system metrics
  - job_name: 'trading-system'
    static_configs:
      - targets: ['host.docker.internal:9091']
    scrape_interval: 5s

  # Observability API metrics
  - job_name: 'observability-api'
    static_configs:
      - targets: ['observability-api:8000']
    metrics_path: '/metrics'

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (system metrics)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # cAdvisor (container metrics)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

### Alert Rules

Create `docker/prometheus/alerts.yml`:

```yaml
groups:
  - name: trading_alerts
    interval: 30s
    rules:
      - alert: HighOrderLatency
        expr: trading_order_latency_seconds > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High order latency detected"
          description: "Order latency is {{ $value }}s"

      - alert: LowFillRate
        expr: trading_fill_rate < 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low fill rate detected"
          description: "Fill rate is {{ $value }}"

      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} has been down for 2 minutes"
```

### Alertmanager Configuration

Create `docker/alertmanager/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://observability-api:8000/api/v1/alerts'

  - name: 'critical'
    email_configs:
      - to: 'alerts@trading.com'
        from: 'alertmanager@trading.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@trading.com'
        auth_password: 'your-app-password'

  - name: 'warning'
    webhook_configs:
      - url: 'http://observability-api:8000/api/v1/alerts'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster']
```

### Grafana Provisioning

Create `docker/grafana/provisioning/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

Create `docker/grafana/provisioning/dashboards/dashboard.yml`:

```yaml
apiVersion: 1

providers:
  - name: 'Trading Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

## 🛠️ Make Commands

### Basic Commands

```bash
make help          # Show all commands
make build         # Build images
make up            # Start services
make down          # Stop services
make restart       # Restart services
make logs          # View all logs
make status        # Show service status
make health        # Check service health
```

### Development

```bash
make dev           # Start in dev mode with hot reload
make logs-api      # View API logs only
make exec-api      # Shell into API container
```

### Maintenance

```bash
make backup        # Backup all volumes
make restore       # Restore from backup
make clean         # Remove containers and volumes
make prune         # Clean up Docker system
make update        # Pull latest images
```

## 📊 Integration with Trading System

### Option 1: Docker Compose (Recommended)

Update `start_trading.sh`:

```bash
#!/bin/bash

# Start observability stack
cd docker
make up
cd ..

# Wait for services
sleep 10

# Start trading system
cargo run --release --bin trading_engine
```

### Option 2: Separate Start

```bash
# Terminal 1: Start observability
cd docker
make up

# Terminal 2: Start trading
cargo run --release --bin trading_engine
```

### Option 3: All-in-Docker

Add to `docker-compose.observability.yml`:

```yaml
services:
  trading-engine:
    build:
      context: ..
      dockerfile: Dockerfile
    volumes:
      - ../data:/app/data
      - ../.env:/app/.env
    environment:
      - RUST_LOG=info
    networks:
      - observability
    depends_on:
      - prometheus
```

## 🔍 Monitoring

### View Metrics in Prometheus

1. Navigate to http://localhost:9090
2. Query examples:
   - `trading_orders_total` - Total orders
   - `trading_order_latency_seconds` - Order latency
   - `rate(trading_orders_total[5m])` - Order rate

### Create Grafana Dashboard

1. Navigate to http://localhost:3000
2. Login (admin/admin)
3. Create new dashboard
4. Add panels with PromQL queries
5. Save dashboard

### View API Metrics

```bash
# Get current metrics
curl http://localhost:8000/api/v1/metrics

# Get trading statistics
curl http://localhost:8000/api/v1/stats

# Get system health
curl http://localhost:8000/health
```

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# Check logs
make logs

# Restart services
make restart
```

### Port Conflicts

Edit `docker-compose.observability.yml`:

```yaml
services:
  prometheus:
    ports:
      - "19090:9090"  # Use different port
```

### Prometheus Can't Scrape

On Linux, use `172.17.0.1` instead of `host.docker.internal`:

```yaml
scrape_configs:
  - job_name: 'trading-system'
    static_configs:
      - targets: ['172.17.0.1:9091']
```

### Out of Memory

Reduce resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 256M  # Reduce from 512M
```

### Permission Errors

```bash
# Fix volume permissions
sudo chown -R 1000:1000 ../data ../logs

# Or run as root (not recommended)
docker-compose run --user root observability-api bash
```

## 🔒 Security

### Production Hardening

1. **Change default passwords:**

```bash
# Generate secure password
openssl rand -base64 32

# Update .env
GRAFANA_ADMIN_PASSWORD=<generated-password>
SECRET_KEY=<generated-key>
```

2. **Enable authentication:**

```bash
API_KEY_ENABLED=true
API_KEY=$(openssl rand -hex 16)
```

3. **Restrict network access:**

```yaml
ports:
  - "127.0.0.1:9090:9090"  # Only localhost
```

4. **Use HTTPS:**

Deploy behind nginx/traefik with SSL:

```nginx
server {
    listen 443 ssl;
    server_name grafana.trading.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

## 📈 Performance Tuning

### For High-Load Systems

1. **Increase workers:**

```bash
WORKERS=4
```

2. **Optimize Prometheus storage:**

```yaml
command:
  - '--storage.tsdb.retention.time=15d'
  - '--storage.tsdb.min-block-duration=2h'
  - '--storage.tsdb.max-block-duration=24h'
```

3. **Add more resources:**

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

## 📦 Backup & Restore

### Automated Backup

```bash
# Backup all volumes
make backup

# Backups saved to ../backups/
ls -lh ../backups/
```

### Manual Backup

```bash
# Backup Prometheus data
docker run --rm \
  -v trading-observability_prometheus-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz -C /data .

# Backup Grafana data
docker run --rm \
  -v trading-observability_grafana-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/grafana-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
# Restore all volumes
make restore

# Or manual restore
docker run --rm \
  -v trading-observability_prometheus-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/prometheus-20250121.tar.gz -C /data
```

## 🚀 Scaling

### Horizontal Scaling

For distributed setup:

1. **Deploy Prometheus federation:**

```yaml
scrape_configs:
  - job_name: 'federate'
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="trading-system"}'
    static_configs:
      - targets:
        - 'prometheus-1:9090'
        - 'prometheus-2:9090'
```

2. **Use external storage:**

Deploy Thanos or Cortex for long-term storage.

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 Support

For issues or questions:
1. Check logs: `make logs`
2. Verify health: `make health`
3. Review configuration files
4. Check Docker resources: `docker system df`
