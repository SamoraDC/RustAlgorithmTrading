#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"
RELEASE_DIR="$PROJECT_ROOT/target/release"

# Service startup order (dependencies first)
SERVICES=(
    "market_data_service:5555"
    "order_execution_service:5556"
    "risk_management_service:5557"
    "strategy_engine:5558"
    "api_gateway:8080"
)

# Create necessary directories
mkdir -p "$LOG_DIR" "$PID_DIR"

echo -e "${GREEN}Starting Rust Algorithm Trading System${NC}"
echo "========================================"

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file with required configuration"
    exit 1
fi

# Load environment variables
export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}Error: Port $port is already in use${NC}"
        return 1
    fi
    return 0
}

# Function to start a service
start_service() {
    local service_name=$1
    local port=$2
    local binary="$RELEASE_DIR/$service_name"
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$PID_DIR/${service_name}.pid"

    echo -n "Starting $service_name on port $port... "

    # Check if binary exists
    if [ ! -f "$binary" ]; then
        echo -e "${RED}FAILED${NC}"
        echo -e "${RED}Error: Binary not found at $binary${NC}"
        echo "Please run: cargo build --release"
        return 1
    fi

    # Check if port is available
    if ! check_port $port; then
        return 1
    fi

    # Start the service
    nohup "$binary" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"

    # Wait and verify the service started
    sleep 2
    if ps -p $pid > /dev/null; then
        echo -e "${GREEN}OK${NC} (PID: $pid)"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "Check logs at: $log_file"
        return 1
    fi
}

# Function to wait for service health
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=0

    echo -n "Waiting for $service_name to be healthy... "

    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}OK${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${YELLOW}TIMEOUT${NC}"
    echo "Service may still be starting. Check logs for details."
    return 1
}

# Main startup sequence
main() {
    local failed=0

    # Start services in order
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port <<< "$service_config"

        if ! start_service "$service" "$port"; then
            failed=1
            break
        fi

        # Wait for service to be healthy before starting next one
        wait_for_service "$service" "$port"
    done

    if [ $failed -eq 1 ]; then
        echo -e "${RED}Failed to start all services. Initiating shutdown...${NC}"
        bash "$PROJECT_ROOT/scripts/stop_trading_system.sh"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}All services started successfully!${NC}"
    echo ""
    echo "Service Status:"
    echo "---------------"
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port <<< "$service_config"
        pid_file="$PID_DIR/${service}.pid"
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null; then
                echo -e "$service: ${GREEN}Running${NC} (PID: $pid, Port: $port)"
            else
                echo -e "$service: ${RED}Stopped${NC}"
            fi
        fi
    done

    echo ""
    echo "Logs are available at: $LOG_DIR"
    echo "Run health check: ./scripts/health_check.sh"
    echo "Stop services: ./scripts/stop_trading_system.sh"
}

# Trap SIGINT and SIGTERM
trap 'echo -e "\n${YELLOW}Interrupted. Stopping services...${NC}"; bash "$PROJECT_ROOT/scripts/stop_trading_system.sh"; exit 130' INT TERM

main
