# Staging Environment - Quick Reference Card

## One-Line Commands

```bash
# Deploy staging environment
./scripts/deploy-staging.sh

# Verify all services are healthy
./scripts/verify-staging.sh

# Run complete load testing suite
./scripts/run-load-tests.sh

# View all logs
docker-compose -f docker/docker-compose.staging.yml logs -f

# Stop staging environment
docker-compose -f docker/docker-compose.staging.yml down
```

## Service URLs

| Service | URL | Login |
|---------|-----|-------|
| Trading Engine | http://localhost:9001 | - |
| DuckDB Storage | http://localhost:8001 | - |
| Grafana | http://localhost:3001 | admin / staging_grafana_pass |
| Prometheus | http://localhost:9091 | - |
| Jaeger | http://localhost:16687 | - |

## Database Connections

```bash
# PostgreSQL (port 5433)
psql -h localhost -p 5433 -U trading_user -d trading_staging

# Redis (port 6380)
redis-cli -p 6380
```

## Load Test Individual Execution

```bash
LOAD_TESTER=$(docker-compose -f docker/docker-compose.staging.yml ps -q load-tester)

# Market Data Flood (1000 ticks/sec)
docker exec $LOAD_TESTER python /tests/market_data_flood_test.py

# Order Stress (100 concurrent orders)
docker exec $LOAD_TESTER python /tests/order_stress_test.py

# Database Throughput (1000 writes/sec)
docker exec $LOAD_TESTER python /tests/database_throughput_test.py

# WebSocket Concurrency (50 connections)
docker exec $LOAD_TESTER python /tests/websocket_concurrency_test.py
```

## Common Troubleshooting

```bash
# Check service status
docker-compose -f docker/docker-compose.staging.yml ps

# Check specific service logs
docker-compose -f docker/docker-compose.staging.yml logs trading-engine-staging

# Check resource usage
docker stats

# Restart specific service
docker-compose -f docker/docker-compose.staging.yml restart trading-engine-staging

# View load test results
cat docker/load-test-results/summary.txt
ls -lh docker/load-test-results/*.json
```

## Environment Variables Location

```bash
# Edit staging configuration
vim docker/.env.staging

# Required changes before first deploy:
# - STAGING_BINANCE_API_KEY
# - STAGING_BINANCE_SECRET_KEY
# - STAGING_POSTGRES_PASSWORD
# - STAGING_GRAFANA_PASSWORD
```

## Performance Targets

- **Order Throughput**: 1000 tps
- **Order Latency (P99)**: ≤ 100ms
- **Database Writes**: 1000 wps
- **WebSocket Connections**: 50 concurrent
- **Success Rate**: ≥ 99%

## Resource Requirements

- **Minimum**: 8 CPU cores, 16GB RAM
- **Recommended**: 12+ CPU cores, 24GB RAM
- **Disk Space**: 50GB+ for logs and data

## File Locations

```
docker/
├── docker-compose.staging.yml    # Main configuration
├── .env.staging                  # Environment variables
└── README.staging.md             # Full documentation

scripts/
├── deploy-staging.sh             # Deployment
├── run-load-tests.sh             # Testing
├── verify-staging.sh             # Verification
└── load_testing/*.py             # Individual tests

docs/deployment/
└── STAGING_SETUP_COMPLETE.md     # Completion report
```

## Health Check Endpoints

```bash
curl http://localhost:9001/health    # Trading Engine
curl http://localhost:8001/health    # DuckDB
curl http://localhost:9091/-/healthy # Prometheus
curl http://localhost:3001/api/health # Grafana
```

## CI/CD Integration

```yaml
# .github/workflows/staging-tests.yml
- run: ./scripts/deploy-staging.sh
- run: ./scripts/verify-staging.sh
- run: ./scripts/run-load-tests.sh
```

---

**For detailed documentation, see**: `docker/README.staging.md`
**For completion report, see**: `docs/deployment/STAGING_SETUP_COMPLETE.md`
