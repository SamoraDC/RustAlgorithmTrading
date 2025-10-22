# Staging Environment - Quick Start Guide

## Overview

This staging environment provides a complete, production-like deployment of the Rust Algorithm Trading system with comprehensive observability and load testing capabilities.

## Architecture

### Services Deployed

1. **Trading Engine** (Port 9001)
   - Rust-based algorithmic trading engine
   - 4 CPU cores, 8GB RAM
   - Health checks enabled
   - Prometheus metrics export

2. **PostgreSQL** (Port 5433)
   - Primary transactional database
   - 2 CPU cores, 2GB RAM
   - Performance-tuned configuration
   - 200 max connections

3. **DuckDB Storage** (Port 8001)
   - Analytical data storage service
   - 2 CPU cores, 4GB RAM
   - REST API for queries

4. **Redis** (Port 6380)
   - Caching and session management
   - 512MB memory limit
   - LRU eviction policy

5. **Prometheus** (Port 9091)
   - Metrics collection and alerting
   - 30-day retention
   - Comprehensive alert rules

6. **Grafana** (Port 3001)
   - Visualization and dashboards
   - Pre-configured datasources
   - Performance dashboard included

7. **Jaeger** (Port 16687)
   - Distributed tracing
   - Request flow visualization

8. **Load Tester**
   - Automated load testing suite
   - 4 comprehensive test scenarios

## Quick Start

### 1. Deploy Staging Environment

```bash
# One-command deployment
./scripts/deploy-staging.sh
```

This script will:
- ✓ Check prerequisites (Docker, Docker Compose)
- ✓ Validate environment configuration
- ✓ Build Docker images
- ✓ Start all services
- ✓ Wait for services to be healthy
- ✓ Run health checks

### 2. Verify Deployment

```bash
# Comprehensive verification
./scripts/verify-staging.sh
```

Verification includes:
- Container health status
- HTTP endpoint accessibility
- Database connectivity
- Metrics collection
- Resource usage
- Network connectivity

### 3. Run Load Tests

```bash
# Execute full load testing suite
./scripts/run-load-tests.sh
```

Load tests included:
- **Market Data Flood Test**: 1000 ticks/sec sustained
- **Order Stress Test**: 100 concurrent orders
- **Database Throughput Test**: 1000 writes/sec
- **WebSocket Concurrency Test**: 50 concurrent connections

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Trading Engine | http://localhost:9001 | N/A |
| DuckDB Storage | http://localhost:8001 | N/A |
| Grafana | http://localhost:3001 | admin / staging_grafana_pass |
| Prometheus | http://localhost:9091 | N/A |
| Jaeger UI | http://localhost:16687 | N/A |
| PostgreSQL | localhost:5433 | trading_user / staging_password_change_me |
| Redis | localhost:6380 | N/A |

## Configuration

### Environment Variables

All configuration is managed in `docker/.env.staging`:

```bash
# Database
STAGING_POSTGRES_DB=trading_staging
STAGING_POSTGRES_USER=trading_user
STAGING_POSTGRES_PASSWORD=staging_password_CHANGE_ME

# Trading Engine
STAGING_MAX_POSITION_SIZE=1000
STAGING_RISK_LIMIT_PERCENT=2.0

# Binance API (Use testnet credentials)
STAGING_BINANCE_API_KEY=your_testnet_api_key_here
STAGING_BINANCE_SECRET_KEY=your_testnet_secret_key_here

# Load Testing
LOAD_TEST_DURATION=300
LOAD_TEST_USERS=100
LOAD_TEST_TARGET_TPS=1000
```

**⚠️ Important**: Update credentials before deploying!

### Resource Limits

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| Trading Engine | 4.0 cores | 8GB |
| PostgreSQL | 2.0 cores | 2GB |
| DuckDB | 2.0 cores | 4GB |
| Prometheus | 1.0 core | 2GB |
| Grafana | 1.0 core | 1GB |
| Redis | 0.5 cores | 768MB |

## Load Testing Details

### 1. Market Data Flood Test

**Purpose**: Test system throughput under high-frequency market data

**Target Performance**:
- 1000 ticks/second sustained
- 99% success rate
- Median latency ≤ 100ms

**Duration**: 5 minutes (configurable)

**Test Execution**:
```bash
docker exec load-tester python /tests/market_data_flood_test.py
```

### 2. Order Stress Test

**Purpose**: Test order processing under concurrent load

**Target Performance**:
- 100 concurrent orders
- Mean latency ≤ 100ms
- P99 latency ≤ 500ms
- Success rate ≥ 95%

**Test Execution**:
```bash
docker exec load-tester python /tests/order_stress_test.py
```

### 3. Database Throughput Test

**Purpose**: Test database performance under write-heavy load

**Target Performance**:
- 1000 writes/second
- Write success rate ≥ 99%
- Write median latency ≤ 50ms
- Read median latency ≤ 100ms

**Test Execution**:
```bash
docker exec load-tester python /tests/database_throughput_test.py
```

### 4. WebSocket Concurrency Test

**Purpose**: Test WebSocket connection handling and streaming

**Target Performance**:
- 50 concurrent connections
- Connection success rate ≥ 95%
- Message median latency ≤ 100ms
- Stable connections ≥ 90% of target

**Test Execution**:
```bash
docker exec load-tester python /tests/websocket_concurrency_test.py
```

## Monitoring & Observability

### Grafana Dashboards

Access: http://localhost:3001

Pre-configured dashboards:
- **Staging Performance Dashboard**: Real-time metrics
  - Order throughput
  - P99 latency
  - Error rates
  - Database connections
  - CPU/Memory usage

### Prometheus Alerts

Access: http://localhost:9091/alerts

Alert rules configured:
- High order latency (>100ms)
- Critical latency (>500ms)
- High error rate (>1%)
- Database connection exhaustion
- Slow queries
- Service downtime

### Distributed Tracing

Access: http://localhost:16687

Features:
- Request flow visualization
- Performance bottleneck identification
- Service dependency mapping

## Common Operations

### View Logs

```bash
# All services
docker-compose -f docker/docker-compose.staging.yml logs -f

# Specific service
docker-compose -f docker/docker-compose.staging.yml logs -f trading-engine-staging

# Last 100 lines
docker-compose -f docker/docker-compose.staging.yml logs --tail=100
```

### Restart Services

```bash
# All services
docker-compose -f docker/docker-compose.staging.yml restart

# Specific service
docker-compose -f docker/docker-compose.staging.yml restart trading-engine-staging
```

### Scale Services

```bash
# Not directly supported in staging (use production for scaling)
# To increase resources, edit docker-compose.staging.yml
```

### Stop Environment

```bash
# Stop all services
docker-compose -f docker/docker-compose.staging.yml down

# Stop and remove volumes
docker-compose -f docker/docker-compose.staging.yml down -v
```

### Database Access

```bash
# PostgreSQL
docker-compose -f docker/docker-compose.staging.yml exec postgres-staging \
  psql -U trading_user -d trading_staging

# Redis
docker-compose -f docker/docker-compose.staging.yml exec redis-staging \
  redis-cli
```

## Troubleshooting

### Services Not Starting

1. Check Docker resources:
```bash
docker system df
docker system prune  # If needed
```

2. Check logs for errors:
```bash
docker-compose -f docker/docker-compose.staging.yml logs
```

3. Verify environment file:
```bash
cat docker/.env.staging
```

### Load Tests Failing

1. Verify staging environment is healthy:
```bash
./scripts/verify-staging.sh
```

2. Check service resources:
```bash
docker stats
```

3. Review load test results:
```bash
cat docker/load-test-results/summary.txt
```

### High Resource Usage

1. Check container stats:
```bash
docker stats
```

2. Reduce load test parameters in `.env.staging`:
```bash
LOAD_TEST_DURATION=60  # Reduce to 1 minute
LOAD_TEST_USERS=50     # Reduce concurrent users
```

### Database Connection Issues

1. Check PostgreSQL logs:
```bash
docker-compose -f docker/docker-compose.staging.yml logs postgres-staging
```

2. Verify connection limits:
```bash
docker-compose -f docker/docker-compose.staging.yml exec postgres-staging \
  psql -U trading_user -d trading_staging -c "SHOW max_connections;"
```

## Performance Tuning

### PostgreSQL

Edit `docker-compose.staging.yml`:

```yaml
command: >
  postgres
  -c max_connections=200          # Increase if needed
  -c shared_buffers=512MB         # Increase for more cache
  -c effective_cache_size=2GB     # Increase based on available RAM
```

### Trading Engine

Edit `docker/.env.staging`:

```bash
STAGING_RUST_LOG=info            # Change to debug for detailed logs
STAGING_MAX_POSITION_SIZE=1000   # Adjust risk limits
```

### Load Testing

Edit `docker/.env.staging`:

```bash
LOAD_TEST_DURATION=600           # Longer test duration
LOAD_TEST_USERS=200              # More concurrent users
LOAD_TEST_TARGET_TPS=2000        # Higher throughput target
```

## Security Best Practices

1. **Change Default Passwords**: Update all passwords in `.env.staging`

2. **Use Testnet API Keys**: Never use production API keys in staging

3. **Network Isolation**: Staging network is isolated from host

4. **Resource Limits**: All containers have CPU/memory limits

5. **No External Access**: Services only accessible via localhost

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Staging Tests

on:
  push:
    branches: [develop]

jobs:
  staging-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy Staging
        run: ./scripts/deploy-staging.sh

      - name: Verify Deployment
        run: ./scripts/verify-staging.sh

      - name: Run Load Tests
        run: ./scripts/run-load-tests.sh

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: docker/load-test-results/
```

## Next Steps

1. **Production Deployment**: Use staging configuration as template
2. **Custom Dashboards**: Create additional Grafana dashboards
3. **Alert Integration**: Connect Prometheus to Slack/PagerDuty
4. **Automated Testing**: Integrate load tests into CI/CD pipeline
5. **Performance Baselines**: Establish performance benchmarks

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Run verification: `./scripts/verify-staging.sh`
3. Review test results: `docker/load-test-results/`
4. Consult documentation: `docs/deployment/STAGING_DEPLOYMENT.md`

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
**Maintained By**: CI/CD Engineering Team
