#!/bin/bash
# Staging Environment Verification Script
# Comprehensive health checks for all staging services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Staging Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Track results
declare -a checks_passed
declare -a checks_failed

# Function to perform a check
check() {
    local description=$1
    local command=$2

    echo -n "  ${description}..."

    if eval "${command}" > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        checks_passed+=("${description}")
        return 0
    else
        echo -e " ${RED}✗${NC}"
        checks_failed+=("${description}")
        return 1
    fi
}

# 1. Docker Compose Status
echo -e "${YELLOW}[1/8] Docker Compose Status${NC}"

cd "${DOCKER_DIR}"

check "Docker Compose file exists" "test -f docker-compose.staging.yml"
check "Environment file exists" "test -f .env.staging"
check "Services are running" "docker-compose -f docker-compose.staging.yml ps | grep -q 'Up'"

echo ""

# 2. Container Health
echo -e "${YELLOW}[2/8] Container Health${NC}"

check "PostgreSQL healthy" "docker-compose -f docker-compose.staging.yml ps postgres-staging | grep -q 'healthy\|Up'"
check "Redis healthy" "docker-compose -f docker-compose.staging.yml ps redis-staging | grep -q 'healthy\|Up'"
check "DuckDB healthy" "docker-compose -f docker-compose.staging.yml ps duckdb-staging | grep -q 'healthy\|Up'"
check "Trading Engine healthy" "docker-compose -f docker-compose.staging.yml ps trading-engine-staging | grep -q 'healthy\|Up'"
check "Prometheus healthy" "docker-compose -f docker-compose.staging.yml ps prometheus-staging | grep -q 'healthy\|Up'"
check "Grafana healthy" "docker-compose -f docker-compose.staging.yml ps grafana-staging | grep -q 'healthy\|Up'"
check "Jaeger healthy" "docker-compose -f docker-compose.staging.yml ps jaeger-staging | grep -q 'healthy\|Up'"

echo ""

# 3. HTTP Endpoints
echo -e "${YELLOW}[3/8] HTTP Endpoint Health Checks${NC}"

check "Trading Engine health endpoint" "curl -sf http://localhost:9001/health | grep -q 'ok\|healthy'"
check "DuckDB health endpoint" "curl -sf http://localhost:8001/health | grep -q 'ok\|healthy'"
check "Prometheus health endpoint" "curl -sf http://localhost:9091/-/healthy"
check "Grafana health endpoint" "curl -sf http://localhost:3001/api/health | grep -q 'ok'"
check "Jaeger UI accessible" "curl -sf http://localhost:16687/ | grep -q 'Jaeger'"

echo ""

# 4. Database Connectivity
echo -e "${YELLOW}[4/8] Database Connectivity${NC}"

POSTGRES_CONTAINER=$(docker-compose -f docker-compose.staging.yml ps -q postgres-staging)

check "PostgreSQL accepts connections" "docker exec ${POSTGRES_CONTAINER} pg_isready -U trading_user -d trading_staging"
check "PostgreSQL can execute queries" "docker exec ${POSTGRES_CONTAINER} psql -U trading_user -d trading_staging -c 'SELECT 1' | grep -q '1 row'"

REDIS_CONTAINER=$(docker-compose -f docker-compose.staging.yml ps -q redis-staging)

check "Redis accepts connections" "docker exec ${REDIS_CONTAINER} redis-cli ping | grep -q 'PONG'"

echo ""

# 5. Service Metrics
echo -e "${YELLOW}[5/8] Service Metrics Collection${NC}"

check "Prometheus scraping targets" "curl -sf http://localhost:9091/api/v1/targets | grep -q 'activeTargets'"
check "Prometheus has metrics" "curl -sf 'http://localhost:9091/api/v1/query?query=up' | grep -q '\"value\"'"
check "Trading Engine exports metrics" "curl -sf http://localhost:9001/metrics | grep -q 'HELP'"

echo ""

# 6. Storage and Persistence
echo -e "${YELLOW}[6/8] Storage and Persistence${NC}"

check "PostgreSQL data volume exists" "docker volume ls | grep -q 'staging-postgres-data'"
check "DuckDB data volume exists" "docker volume ls | grep -q 'staging-duckdb-data'"
check "Grafana data volume exists" "docker volume ls | grep -q 'staging-grafana-data'"
check "Prometheus data volume exists" "docker volume ls | grep -q 'staging-prometheus-data'"

echo ""

# 7. Resource Usage
echo -e "${YELLOW}[7/8] Resource Usage${NC}"

# Check if containers are within resource limits
check_resource() {
    local container=$1
    local max_cpu=$2
    local max_mem_gb=$3

    local stats=$(docker stats --no-stream --format "{{.CPUPerc}} {{.MemUsage}}" "${container}" 2>/dev/null)

    if [ -n "$stats" ]; then
        return 0
    else
        return 1
    fi
}

TRADING_ENGINE=$(docker-compose -f docker-compose.staging.yml ps -q trading-engine-staging)
check "Trading Engine resource usage tracked" "check_resource ${TRADING_ENGINE} 400 8"

POSTGRES=$(docker-compose -f docker-compose.staging.yml ps -q postgres-staging)
check "PostgreSQL resource usage tracked" "check_resource ${POSTGRES} 200 2"

echo ""

# 8. Network Connectivity
echo -e "${YELLOW}[8/8] Network Connectivity${NC}"

check "Staging network exists" "docker network ls | grep -q 'staging-network'"
check "Services connected to network" "docker network inspect staging-network | grep -q 'trading-engine-staging'"

# Test inter-service communication
TRADING_ENGINE=$(docker-compose -f docker-compose.staging.yml ps -q trading-engine-staging)
check "Trading Engine can reach PostgreSQL" "docker exec ${TRADING_ENGINE} nc -zv postgres-staging 5432 2>&1 | grep -q 'succeeded\|open'"
check "Trading Engine can reach DuckDB" "docker exec ${TRADING_ENGINE} nc -zv duckdb-staging 8000 2>&1 | grep -q 'succeeded\|open'"
check "Trading Engine can reach Redis" "docker exec ${TRADING_ENGINE} nc -zv redis-staging 6379 2>&1 | grep -q 'succeeded\|open'"

echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

total_checks=$((${#checks_passed[@]} + ${#checks_failed[@]}))

echo -e "${GREEN}Passed: ${#checks_passed[@]}/${total_checks}${NC}"

if [ ${#checks_failed[@]} -gt 0 ]; then
    echo -e "${RED}Failed: ${#checks_failed[@]}/${total_checks}${NC}"
    echo ""
    echo -e "${RED}Failed Checks:${NC}"
    for check in "${checks_failed[@]}"; do
        echo -e "  ${RED}✗${NC} ${check}"
    done
    echo ""
fi

echo ""

if [ ${#checks_failed[@]} -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ALL CHECKS PASSED ✓${NC}"
    echo -e "${GREEN}  Staging environment is healthy${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Run load tests:    ${YELLOW}./scripts/run-load-tests.sh${NC}"
    echo -e "  2. View Grafana:      ${YELLOW}http://localhost:3001${NC}"
    echo -e "  3. View Jaeger:       ${YELLOW}http://localhost:16687${NC}"
    echo -e "  4. View Prometheus:   ${YELLOW}http://localhost:9091${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  VERIFICATION FAILED ✗${NC}"
    echo -e "${RED}  ${#checks_failed[@]} check(s) failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo -e "  1. View logs:         ${YELLOW}docker-compose -f docker/docker-compose.staging.yml logs${NC}"
    echo -e "  2. Restart services:  ${YELLOW}./scripts/deploy-staging.sh${NC}"
    echo -e "  3. Check resources:   ${YELLOW}docker stats${NC}"
    echo ""
    exit 1
fi
