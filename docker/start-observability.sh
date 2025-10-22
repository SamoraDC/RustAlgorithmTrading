#!/bin/bash
# Start Observability Stack - Production Ready Launcher
# Usage: ./start-observability.sh [mode]
#   mode: docker (default) | native | dev

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODE="${1:-docker}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_success() { echo -e "${GREEN}✓${NC} $1"; }
echo_error() { echo -e "${RED}✗${NC} $1"; }
echo_info() { echo -e "${YELLOW}ℹ${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."

    if [ "$MODE" = "docker" ] || [ "$MODE" = "dev" ]; then
        if ! command -v docker &> /dev/null; then
            echo_error "Docker not found. Please install Docker."
            exit 1
        fi

        if ! command -v docker-compose &> /dev/null; then
            echo_error "Docker Compose not found. Please install Docker Compose."
            exit 1
        fi

        if ! docker info &> /dev/null; then
            echo_error "Docker daemon not running. Please start Docker."
            exit 1
        fi

        echo_success "Docker and Docker Compose found"
    fi

    if [ "$MODE" = "native" ]; then
        if ! command -v python3 &> /dev/null; then
            echo_error "Python 3 not found. Please install Python 3.11+."
            exit 1
        fi
        echo_success "Python found"
    fi
}

# Setup environment
setup_environment() {
    echo_info "Setting up environment..."

    # Copy .env if not exists
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            echo_success "Created .env from .env.example"
            echo_info "Please edit docker/.env with your configuration"
        else
            echo_error ".env.example not found!"
            exit 1
        fi
    else
        echo_success ".env file exists"
    fi

    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs" "$PROJECT_ROOT/backups"
    echo_success "Created data directories"
}

# Start Docker mode
start_docker() {
    echo_info "Starting observability stack in Docker mode..."

    cd "$SCRIPT_DIR"

    # Check if services already running
    if docker-compose -f docker-compose.observability.yml ps | grep -q "Up"; then
        echo_info "Services already running. Restarting..."
        docker-compose -f docker-compose.observability.yml restart
    else
        docker-compose -f docker-compose.observability.yml up -d
    fi

    echo_success "Services started!"
    echo ""
    echo "Access points:"
    echo "  Prometheus:  http://localhost:9090"
    echo "  Grafana:     http://localhost:3000 (admin/admin)"
    echo "  API:         http://localhost:8000"
    echo "  Docs:        http://localhost:8000/docs"
    echo "  Alerts:      http://localhost:9093"
    echo ""
    echo "View logs: cd docker && make logs"
    echo "Check health: cd docker && make health"
}

# Start development mode
start_dev() {
    echo_info "Starting observability stack in development mode..."

    cd "$SCRIPT_DIR"
    docker-compose -f docker-compose.observability.yml -f docker-compose.dev.yml up --build
}

# Start native mode (without Docker)
start_native() {
    echo_info "Starting observability stack in native mode..."

    # Install Python dependencies
    if [ ! -d "$PROJECT_ROOT/src/observability/venv" ]; then
        echo_info "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/src/observability/venv"
    fi

    source "$PROJECT_ROOT/src/observability/venv/bin/activate"

    echo_info "Installing dependencies..."
    pip install -r "$PROJECT_ROOT/src/observability/requirements.txt"

    # Export environment variables
    export DUCKDB_PATH="$PROJECT_ROOT/data/metrics.duckdb"
    export SQLITE_PATH="$PROJECT_ROOT/data/trading.db"
    export LOG_PATH="$PROJECT_ROOT/logs"
    export PROMETHEUS_URL="http://localhost:9090"
    export GRAFANA_URL="http://localhost:3000"

    echo_info "Starting FastAPI server..."
    cd "$PROJECT_ROOT/src/observability"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

# Health check
health_check() {
    echo_info "Waiting for services to be healthy..."
    sleep 10

    PROMETHEUS_HEALTH=$(curl -s http://localhost:9090/-/healthy || echo "FAIL")
    GRAFANA_HEALTH=$(curl -s http://localhost:3000/api/health || echo "FAIL")
    API_HEALTH=$(curl -s http://localhost:8000/health || echo "FAIL")

    echo ""
    echo "Health Status:"
    if [[ "$PROMETHEUS_HEALTH" == *"Prometheus"* ]]; then
        echo_success "Prometheus: HEALTHY"
    else
        echo_error "Prometheus: UNHEALTHY"
    fi

    if [[ "$GRAFANA_HEALTH" == *"ok"* ]]; then
        echo_success "Grafana: HEALTHY"
    else
        echo_error "Grafana: UNHEALTHY"
    fi

    if [[ "$API_HEALTH" == *"status"* ]]; then
        echo_success "Observability API: HEALTHY"
    else
        echo_error "Observability API: UNHEALTHY"
    fi
}

# Main
main() {
    echo "=========================================="
    echo "  Observability Stack Launcher"
    echo "  Mode: $MODE"
    echo "=========================================="
    echo ""

    check_prerequisites
    setup_environment

    case "$MODE" in
        docker)
            start_docker
            if [ "$2" != "--no-health-check" ]; then
                health_check
            fi
            ;;
        dev)
            start_dev
            ;;
        native)
            start_native
            ;;
        *)
            echo_error "Unknown mode: $MODE"
            echo "Usage: $0 [docker|native|dev]"
            exit 1
            ;;
    esac
}

main "$@"
