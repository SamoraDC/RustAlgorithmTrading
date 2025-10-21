# Docker Deployment Guide

This directory contains Docker configuration for containerized deployment of the Rust Algorithm Trading System.

## Overview

The system uses multi-stage Docker builds for optimal image size and includes:
- 5 microservices (Market Data, Order Execution, Risk Management, Strategy Engine, API Gateway)
- Prometheus for metrics collection
- Grafana for visualization
- Service orchestration via Docker Compose
- Health checks and auto-restart policies

## Quick Start

### Prerequisites
- Docker 24.0+ installed
- Docker Compose V2 installed
- `.env` file configured in project root
- At least 4GB RAM available

### Build and Start All Services

```bash
# From project root
docker-compose -f docker/docker-compose.yml up -d
```

### Check Service Status

```bash
docker-compose -f docker/docker-compose.yml ps
```

### View Logs

```bash
# All services
docker-compose -f docker/docker-compose.yml logs -f

# Specific service
docker-compose -f docker/docker-compose.yml logs -f market_data_service
```

### Stop All Services

```bash
docker-compose -f docker/docker-compose.yml down
```

## Service Architecture

### Microservices

| Service | Port | Description |
|---------|------|-------------|
| market_data_service | 5555 | Market data ingestion and distribution |
| order_execution_service | 5556 | Order placement and execution |
| risk_management_service | 5557 | Risk monitoring and limits |
| strategy_engine | 5558 | Trading strategy execution |
| api_gateway | 8080 | REST API and WebSocket interface |

### Monitoring

| Service | Port | Description |
|---------|------|-------------|
| prometheus | 9090 | Metrics collection and storage |
| grafana | 3000 | Metrics visualization dashboards |

## Service Dependencies

The system enforces startup order through Docker Compose dependencies:

```
market_data_service (base)
    ↓
order_execution_service
    ↓
risk_management_service
    ↓
strategy_engine
    ↓
api_gateway
```

## Docker Images

### Multi-Stage Build Process

1. **Builder Stage**: Compiles Rust code with optimizations
   - LTO (Link-Time Optimization)
   - Symbol stripping
   - Bitcode embedding

2. **Runtime Stage**: Minimal Debian image with only runtime dependencies
   - ~50MB per service image
   - Only includes necessary libraries (libssl, libzmq)

### Build Individual Images

```bash
# Build specific service
docker build -f docker/Dockerfile --target market_data_service -t trading/market_data:latest .

# Build all services
docker-compose -f docker/docker-compose.yml build
```

### Image Size Optimization

The multi-stage build reduces image size by:
- Separating build and runtime environments
- Stripping debug symbols from binaries
- Using slim Debian base images
- Only copying necessary artifacts

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Risk Management
MAX_POSITION_SIZE=10000
MAX_DAILY_LOSS=1000

# Grafana
GRAFANA_PASSWORD=secure_admin_password
```

### Service Configuration

Each service reads environment variables from:
1. `.env` file (via docker-compose)
2. Environment variables in `docker-compose.yml`
3. Default values in service code

### Port Mapping

Modify port mappings in `docker-compose.yml`:

```yaml
services:
  market_data_service:
    ports:
      - "5555:5555"  # Change to "15555:5555" for custom external port
```

## Health Checks

All services include health checks:

```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "5555"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 30s
```

### Check Health Status

```bash
docker-compose -f docker/docker-compose.yml ps
```

Healthy services show: `Up (healthy)`

## Resource Limits

Services have CPU and memory limits configured:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### Adjust Resource Limits

Edit `docker-compose.yml` to modify limits based on your hardware.

## Networking

Services communicate via Docker bridge network:
- Network: `trading_network`
- Subnet: `172.25.0.0/16`
- Internal DNS resolution enabled

### Service Communication

Services use container names as hostnames:
```
tcp://market_data_service:5555
tcp://order_execution_service:5556
```

## Persistent Data

Volumes are created for data persistence:

```yaml
volumes:
  market_data_logs:       # Market data logs
  order_execution_data:   # Order history
  prometheus_data:        # Metrics data
  grafana_data:          # Dashboard configurations
```

### Backup Volumes

```bash
# Backup Prometheus data
docker run --rm -v trading_prometheus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup.tar.gz /data

# Restore Prometheus data
docker run --rm -v trading_prometheus_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/prometheus-backup.tar.gz -C /
```

## Monitoring and Observability

### Prometheus

Access Prometheus at: http://localhost:9090

**Useful Queries:**
```promql
# Service uptime
up

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Memory usage
process_resident_memory_bytes / 1024 / 1024
```

### Grafana

Access Grafana at: http://localhost:3000

**Default Credentials:**
- Username: `admin`
- Password: Set in `.env` as `GRAFANA_PASSWORD`

**Pre-configured Dashboards:**
- Trading System Overview
- Service Performance
- Error Rates
- Resource Usage

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs service_name

# Check health
docker inspect trading_market_data --format='{{.State.Health.Status}}'
```

### Network Issues

```bash
# Inspect network
docker network inspect trading_trading_network

# Test connectivity between services
docker exec trading_api_gateway nc -zv market_data_service 5555
```

### Resource Issues

```bash
# Check resource usage
docker stats

# View resource limits
docker-compose -f docker/docker-compose.yml config
```

### Rebuild After Code Changes

```bash
# Rebuild and restart services
docker-compose -f docker/docker-compose.yml up -d --build

# Force rebuild without cache
docker-compose -f docker/docker-compose.yml build --no-cache
```

## Production Deployment

### Security Best Practices

1. **Use secrets management**:
   ```bash
   echo "your_api_key" | docker secret create binance_api_key -
   ```

2. **Enable Docker Content Trust**:
   ```bash
   export DOCKER_CONTENT_TRUST=1
   ```

3. **Scan images for vulnerabilities**:
   ```bash
   docker scan trading/market_data:latest
   ```

4. **Use read-only root filesystem**:
   ```yaml
   security_opt:
     - no-new-privileges:true
   read_only: true
   ```

### High Availability

For production HA deployment:
1. Use Docker Swarm or Kubernetes
2. Implement service replication
3. Configure load balancing
4. Set up health check monitoring
5. Implement automatic failover

### Logging

Configure centralized logging:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

Or use external logging driver (syslog, fluentd, etc.)

## CI/CD Integration

The GitHub Actions workflow automatically:
1. Builds Docker images on push to main
2. Pushes to GitHub Container Registry
3. Tags with branch and SHA
4. Caches layers for faster builds

### Pull Images from GHCR

```bash
docker pull ghcr.io/your-username/trading-system:main
```

## Performance Tuning

### Optimize Build Time

1. **Use BuildKit**:
   ```bash
   DOCKER_BUILDKIT=1 docker-compose build
   ```

2. **Layer caching**:
   - Copy dependency files first
   - Build dependencies separately
   - Copy source code last

3. **Parallel builds**:
   ```bash
   docker-compose build --parallel
   ```

### Runtime Optimization

1. **Adjust ZeroMQ settings** in service code
2. **Tune resource limits** based on load
3. **Enable connection pooling** where applicable
4. **Use tmpfs for temporary data**:
   ```yaml
   tmpfs:
     - /tmp
   ```

## Maintenance

### Update Images

```bash
# Pull latest base images
docker-compose -f docker/docker-compose.yml pull

# Rebuild with latest dependencies
docker-compose -f docker/docker-compose.yml up -d --build
```

### Clean Up

```bash
# Remove stopped containers
docker-compose -f docker/docker-compose.yml down

# Remove volumes (WARNING: deletes data)
docker-compose -f docker/docker-compose.yml down -v

# Clean up unused images
docker image prune -a
```

## Support

For issues related to:
- Docker configuration: Check this README
- Service errors: Check service logs
- Build failures: Review CI/CD workflow logs
- Performance issues: Review Grafana dashboards

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
