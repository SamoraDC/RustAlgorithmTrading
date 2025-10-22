#!/bin/bash
# Staging Deployment Script
# One-command deployment of the complete staging environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
ENV_FILE="${DOCKER_DIR}/.env.staging"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Staging Environment Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/8] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
echo ""

# Check environment file
echo -e "${YELLOW}[2/8] Checking environment configuration...${NC}"

if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${RED}Error: Environment file not found: ${ENV_FILE}${NC}"
    echo -e "${YELLOW}Creating from .env.example...${NC}"

    if [ -f "${DOCKER_DIR}/.env.example" ]; then
        cp "${DOCKER_DIR}/.env.example" "${ENV_FILE}"
        echo -e "${YELLOW}⚠ Please edit ${ENV_FILE} with your credentials before deploying${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Check for placeholder values
if grep -q "CHANGE_ME" "${ENV_FILE}"; then
    echo -e "${YELLOW}⚠ Warning: Environment file contains placeholder values (CHANGE_ME)${NC}"
    echo -e "${YELLOW}  Please update the credentials in ${ENV_FILE}${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓ Environment configuration checked${NC}"
echo ""

# Stop any existing staging environment
echo -e "${YELLOW}[3/8] Stopping existing staging environment...${NC}"
cd "${DOCKER_DIR}"
docker-compose -f docker-compose.staging.yml --env-file .env.staging down -v 2>/dev/null || true
echo -e "${GREEN}✓ Existing environment stopped${NC}"
echo ""

# Build images
echo -e "${YELLOW}[4/8] Building Docker images...${NC}"
docker-compose -f docker-compose.staging.yml --env-file .env.staging build --no-cache
echo -e "${GREEN}✓ Images built successfully${NC}"
echo ""

# Create necessary directories
echo -e "${YELLOW}[5/8] Creating data directories...${NC}"
mkdir -p "${DOCKER_DIR}/load-test-results"
mkdir -p "${DOCKER_DIR}/redis-data"
mkdir -p "${DOCKER_DIR}/jaeger-data"
chmod -R 755 "${DOCKER_DIR}/load-test-results"
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Start services
echo -e "${YELLOW}[6/8] Starting staging services...${NC}"
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Wait for services to be healthy
echo -e "${YELLOW}[7/8] Waiting for services to be healthy...${NC}"

wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1

    echo -n "  Waiting for ${service}..."

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.staging.yml --env-file .env.staging ps | grep "${service}" | grep -q "healthy\|Up"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Error: ${service} failed to become healthy${NC}"
    return 1
}

# Wait for critical services
wait_for_service "postgres-staging" || exit 1
wait_for_service "redis-staging" || exit 1
wait_for_service "prometheus-staging" || exit 1
wait_for_service "grafana-staging" || exit 1
wait_for_service "jaeger-staging" || exit 1
wait_for_service "duckdb-staging" || exit 1
wait_for_service "trading-engine-staging" || exit 1

echo -e "${GREEN}✓ All services are healthy${NC}"
echo ""

# Run health checks
echo -e "${YELLOW}[8/8] Running health checks...${NC}"

check_endpoint() {
    local name=$1
    local url=$2

    echo -n "  Checking ${name}..."
    if curl -sf "${url}" > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        return 0
    else
        echo -e " ${RED}✗${NC}"
        return 1
    fi
}

check_endpoint "Trading Engine" "http://localhost:9001/health"
check_endpoint "DuckDB Storage" "http://localhost:8001/health"
check_endpoint "Prometheus" "http://localhost:9091/-/healthy"
check_endpoint "Grafana" "http://localhost:3001/api/health"
check_endpoint "Jaeger UI" "http://localhost:16687/"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Staging Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  Trading Engine:  http://localhost:9001"
echo -e "  DuckDB Storage:  http://localhost:8001"
echo -e "  Grafana:         http://localhost:3001"
echo -e "  Prometheus:      http://localhost:9091"
echo -e "  Jaeger UI:       http://localhost:16687"
echo -e "  PostgreSQL:      localhost:5433"
echo -e "  Redis:           localhost:6380"
echo ""
echo -e "${BLUE}Default Credentials:${NC}"
echo -e "  Grafana:         admin / staging_grafana_pass"
echo -e "  PostgreSQL:      trading_user / staging_password_change_me"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. View logs:         ${YELLOW}docker-compose -f docker/docker-compose.staging.yml logs -f${NC}"
echo -e "  2. Run load tests:    ${YELLOW}./scripts/run-load-tests.sh${NC}"
echo -e "  3. Verify deployment: ${YELLOW}./scripts/verify-staging.sh${NC}"
echo -e "  4. Stop services:     ${YELLOW}docker-compose -f docker/docker-compose.staging.yml down${NC}"
echo ""
