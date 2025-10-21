# CI/CD and Deployment Infrastructure Guide

## Overview

This document provides a comprehensive guide to the CI/CD pipeline and deployment infrastructure for the Rust Algorithm Trading System.

## Table of Contents

1. [CI/CD Pipeline](#cicd-pipeline)
2. [Deployment Scripts](#deployment-scripts)
3. [Docker Deployment](#docker-deployment)
4. [Monitoring Setup](#monitoring-setup)
5. [Quick Start Guide](#quick-start-guide)
6. [Troubleshooting](#troubleshooting)

---

## CI/CD Pipeline

### GitHub Actions Workflow

**Location**: `.github/workflows/rust.yml`

The automated CI/CD pipeline runs on every push and pull request to main and develop branches.

### Pipeline Stages

#### 1. Code Quality Checks
- **Format checking** with rustfmt
- **Linting** with clippy (all warnings as errors)
- **Documentation** generation check

#### 2. Test Suite
- **Matrix testing** on stable and nightly Rust
- **Unit tests** for all workspace crates
- **Integration tests** for service interactions
- **Documentation tests** to validate examples
- **Parallel execution** across Rust versions

#### 3. Security Audit
- **Dependency scanning** with cargo-audit
- **Vulnerability detection** in dependencies
- **Outdated dependency warnings**

#### 4. Release Build (main branch only)
- **Optimized compilation** with LTO and bitcode
- **Binary stripping** for size reduction
- **Artifact upload** for release binaries
- **30-day retention** of build artifacts

#### 5. Docker Build (on push)
- **Multi-stage builds** for minimal image size
- **GitHub Container Registry** publishing
- **Build caching** for faster builds
- **Semantic versioning** tags

#### 6. Code Coverage
- **Coverage reporting** with tarpaulin
- **Codecov integration** for tracking
- **Visualization** of coverage trends

### Optimization Features

- **Cargo caching** for dependencies
- **Build artifact caching** for faster rebuilds
- **Parallel test execution**
- **Matrix builds** for multiple Rust versions

### Required Secrets

Configure in GitHub repository settings:

- `GITHUB_TOKEN` - Automatically provided
- `CODECOV_TOKEN` - Optional, for coverage reporting

---

## Deployment Scripts

### Location
`/scripts/` directory

All scripts are executable bash scripts with comprehensive error handling.

### 1. start_trading_system.sh

**Purpose**: Start all services in correct dependency order

**Features**:
- Environment validation (.env file check)
- Port availability verification
- Sequential service startup with health checks
- PID file management
- Comprehensive logging
- Graceful error handling with automatic cleanup

**Usage**:
```bash
./scripts/start_trading_system.sh
```

**Service Startup Order**:
1. Market Data Service (port 5555)
2. Order Execution Service (port 5556)
3. Risk Management Service (port 5557)
4. Strategy Engine (port 5558)
5. API Gateway (port 8080)

**Output Locations**:
- Logs: `logs/[service_name].log`
- PIDs: `pids/[service_name].pid`

### 2. stop_trading_system.sh

**Purpose**: Gracefully shutdown all services

**Features**:
- Reverse dependency order shutdown
- SIGTERM for graceful shutdown (30s timeout)
- SIGKILL fallback for hung processes
- PID file cleanup
- Force kill option

**Usage**:
```bash
# Graceful shutdown
./scripts/stop_trading_system.sh

# Force kill all
./scripts/stop_trading_system.sh --force
```

### 3. health_check.sh

**Purpose**: Monitor service health and performance

**Features**:
- Process status verification
- Port connectivity checks
- HTTP health endpoint validation
- Service uptime tracking
- Memory and CPU usage monitoring
- Recent error log scanning
- Color-coded status output
- Watch mode for continuous monitoring

**Usage**:
```bash
# Single check
./scripts/health_check.sh

# Continuous monitoring (5s refresh)
./scripts/health_check.sh --watch
```

**Health Check Metrics**:
- Process running status
- Port accessibility
- HTTP endpoint health (API Gateway)
- Uptime
- Memory usage (MB)
- CPU usage (%)
- Recent errors in logs

### Script Requirements

- Bash 4.0+
- System tools: `lsof`, `nc`, `curl`, `ps`
- Release binaries built: `cargo build --release`
- Configured `.env` file

---

## Docker Deployment

### Multi-Stage Docker Build

**Location**: `docker/Dockerfile`

**Build Stages**:
1. **Builder**: Rust compilation with optimizations
2. **Runtime Services**: One stage per microservice

**Optimizations**:
- LTO (Link-Time Optimization)
- Symbol stripping
- Bitcode embedding
- Dependency caching
- ~50MB final image size per service

### Docker Compose Orchestration

**Location**: `docker/docker-compose.yml`

**Services**:
- 5 trading microservices
- Prometheus (metrics)
- Grafana (visualization)

**Features**:
- Service dependency management
- Health checks for all services
- Resource limits (CPU, memory)
- Volume persistence
- Network isolation
- Auto-restart policies

### Quick Commands

```bash
# Build and start all services
docker-compose -f docker/docker-compose.yml up -d

# View service status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop all services
docker-compose -f docker/docker-compose.yml down

# Rebuild after code changes
docker-compose -f docker/docker-compose.yml up -d --build
```

### Service URLs

| Service | URL |
|---------|-----|
| API Gateway | http://localhost:8080 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

### Persistent Volumes

- `market_data_logs`, `market_data_cache`
- `order_execution_logs`, `order_execution_data`
- `risk_management_logs`, `risk_management_data`
- `strategy_engine_logs`, `strategy_engine_data`
- `api_gateway_logs`
- `prometheus_data`
- `grafana_data`

---

## Monitoring Setup

### Prometheus Configuration

**Location**: `monitoring/prometheus.yml`

**Scrape Targets**:
- All 5 microservices (5-15s intervals)
- Self-monitoring

**Retention**: 30 days

**Alert Rules**: `monitoring/alerts.yml`

### Alert Categories

1. **Service Availability**
   - ServiceDown (>1 minute)
   - MarketDataStale (>60 seconds)

2. **Performance**
   - HighAPILatency (p95 >1s)
   - HighCPUUsage (>80% for 10m)
   - HighMemoryUsage (>800MB for 5m)

3. **Trading**
   - OrderExecutionFailureRate (>0.1/sec)
   - RiskLimitBreach (any violation)
   - StrategyExecutionErrors

4. **Resources**
   - LowDiskSpace (<10% free)

### Grafana Dashboard

**Location**: `monitoring/grafana-dashboard.json`

**Panels**:
- Service status overview
- Request rates and latency
- CPU and memory usage
- Trading metrics (orders, positions, risk)
- Error rates by service

**Access**: http://localhost:3000
**Default Credentials**: admin / (set in .env)

### Key Metrics

```promql
# Service uptime
up

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Memory usage
process_resident_memory_bytes / 1024 / 1024

# Order execution rate
rate(orders_executed_total[5m])

# Risk exposure
current_risk_exposure
```

---

## Quick Start Guide

### 1. Prerequisites

```bash
# Install dependencies
sudo apt-get install -y libzmq3-dev pkg-config

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Docker
curl -fsSL https://get.docker.com | sh
```

### 2. Configuration

Create `.env` file in project root:

```bash
# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Risk Management
MAX_POSITION_SIZE=10000
MAX_DAILY_LOSS=1000

# Grafana
GRAFANA_PASSWORD=secure_password
```

### 3. Build

```bash
# Build release binaries
cargo build --release

# Or build Docker images
docker-compose -f docker/docker-compose.yml build
```

### 4. Deploy

**Option A: Native Deployment**

```bash
# Start services
./scripts/start_trading_system.sh

# Check health
./scripts/health_check.sh

# Monitor continuously
./scripts/health_check.sh --watch
```

**Option B: Docker Deployment**

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

### 5. Access Services

- **API Gateway**: http://localhost:8080
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

### 6. Stop Services

**Native**:
```bash
./scripts/stop_trading_system.sh
```

**Docker**:
```bash
docker-compose -f docker/docker-compose.yml down
```

---

## Troubleshooting

### Build Failures

**Issue**: Cargo build fails
```bash
# Check Rust installation
rustc --version

# Update Rust
rustup update

# Clean build
cargo clean && cargo build --release
```

**Issue**: Missing dependencies
```bash
# Install ZeroMQ
sudo apt-get install -y libzmq3-dev pkg-config
```

### Service Startup Issues

**Issue**: Port already in use
```bash
# Find process using port
lsof -i :5555

# Kill process
kill -9 <PID>
```

**Issue**: Service crashes immediately
```bash
# Check logs
cat logs/[service_name].log

# Check environment
cat .env
```

### Docker Issues

**Issue**: Container won't start
```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs service_name

# Inspect container
docker inspect trading_market_data
```

**Issue**: Network connectivity
```bash
# Test connectivity
docker exec trading_api_gateway nc -zv market_data_service 5555

# Inspect network
docker network inspect trading_trading_network
```

### Monitoring Issues

**Issue**: Prometheus not scraping
```bash
# Check targets
curl http://localhost:9090/targets

# Test metrics endpoint
curl http://localhost:5555/metrics
```

**Issue**: Grafana dashboard empty
1. Check Prometheus data source connection
2. Verify time range
3. Test query in Prometheus first

### CI/CD Issues

**Issue**: GitHub Actions failing
1. Check workflow logs
2. Verify secrets are set
3. Test locally with `act` tool

**Issue**: Docker build timeout
1. Enable BuildKit
2. Use build cache
3. Increase GitHub Actions timeout

---

## Performance Optimization

### Build Performance

1. **Use cargo cache**:
   ```yaml
   - uses: actions/cache@v4
     with:
       path: ~/.cargo
   ```

2. **Parallel builds**:
   ```bash
   cargo build -j 8 --release
   ```

3. **Incremental compilation**:
   ```toml
   [profile.dev]
   incremental = true
   ```

### Runtime Performance

1. **Tune resource limits** in docker-compose.yml
2. **Adjust ZeroMQ settings** for throughput
3. **Enable CPU affinity** for critical services
4. **Use tmpfs** for temporary data

### Monitoring Performance

1. **Reduce scrape frequency** for less critical metrics
2. **Use recording rules** for expensive queries
3. **Implement data retention policies**
4. **Archive old metrics** to cold storage

---

## Security Best Practices

### Secrets Management

1. **Never commit** `.env` files
2. **Use GitHub Secrets** for CI/CD
3. **Rotate API keys** regularly
4. **Encrypt sensitive data** at rest

### Docker Security

1. **Scan images**:
   ```bash
   docker scan trading/market_data:latest
   ```

2. **Use read-only filesystems**:
   ```yaml
   read_only: true
   ```

3. **Drop capabilities**:
   ```yaml
   cap_drop:
     - ALL
   ```

4. **Run as non-root user**

### Network Security

1. **Use internal networks** for service communication
2. **Expose only necessary ports**
3. **Implement rate limiting**
4. **Enable HTTPS** for external endpoints

---

## Maintenance

### Regular Tasks

**Daily**:
- Review monitoring alerts
- Check service health
- Verify backup completion

**Weekly**:
- Review error logs
- Update dependencies
- Test disaster recovery

**Monthly**:
- Security audit
- Performance review
- Capacity planning

### Backup Strategy

**Automated Backups**:
```bash
# Prometheus data
docker run --rm -v trading_prometheus_data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data

# Grafana dashboards
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/search?type=dash-db > dashboards.json
```

### Update Procedure

1. **Test in development** environment
2. **Review release notes**
3. **Backup current state**
4. **Deploy with canary release**
5. **Monitor metrics closely**
6. **Rollback if issues detected**

---

## Additional Resources

### Documentation
- [Rust Documentation](https://doc.rust-lang.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

### Tools
- [GitHub Actions](https://github.com/features/actions)
- [cargo-audit](https://github.com/rustsec/rustsec)
- [tarpaulin](https://github.com/xd009642/tarpaulin)

### Support
- **Issues**: Check service logs in `logs/` directory
- **Docker**: Review docker-compose logs
- **CI/CD**: Check GitHub Actions workflow runs
- **Monitoring**: Review Grafana dashboards

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-21 | Initial CI/CD infrastructure setup |

---

**Author**: CI/CD Engineer Agent (Hive Mind Swarm)
**Last Updated**: 2025-10-21
**Status**: Production Ready
