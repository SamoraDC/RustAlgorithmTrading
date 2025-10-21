#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/pids"

# Service shutdown order (reverse of startup)
SERVICES=(
    "api_gateway"
    "strategy_engine"
    "risk_management_service"
    "order_execution_service"
    "market_data_service"
)

echo -e "${YELLOW}Stopping Rust Algorithm Trading System${NC}"
echo "========================================"

# Function to stop a service gracefully
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"

    if [ ! -f "$pid_file" ]; then
        echo -e "$service_name: ${YELLOW}No PID file found${NC}"
        return 0
    fi

    local pid=$(cat "$pid_file")

    # Check if process is running
    if ! ps -p $pid > /dev/null 2>&1; then
        echo -e "$service_name: ${YELLOW}Not running${NC}"
        rm -f "$pid_file"
        return 0
    fi

    echo -n "Stopping $service_name (PID: $pid)... "

    # Send SIGTERM for graceful shutdown
    kill -TERM $pid 2>/dev/null || true

    # Wait up to 30 seconds for graceful shutdown
    local timeout=30
    local count=0
    while ps -p $pid > /dev/null 2>&1 && [ $count -lt $timeout ]; do
        sleep 1
        count=$((count + 1))
    done

    # If still running, force kill
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "${YELLOW}Timeout. Force killing...${NC}"
        kill -KILL $pid 2>/dev/null || true
        sleep 1
    fi

    # Verify process is stopped
    if ! ps -p $pid > /dev/null 2>&1; then
        echo -e "${GREEN}Stopped${NC}"
        rm -f "$pid_file"
        return 0
    else
        echo -e "${RED}Failed to stop${NC}"
        return 1
    fi
}

# Function to cleanup all PIDs
cleanup_all() {
    echo ""
    echo "Cleaning up any remaining processes..."

    # Kill any processes matching our service names
    for service in "${SERVICES[@]}"; do
        pkill -f "$service" 2>/dev/null || true
    done

    # Remove all PID files
    rm -f "$PID_DIR"/*.pid

    echo -e "${GREEN}Cleanup complete${NC}"
}

# Main shutdown sequence
main() {
    local failed=0

    # Check if PID directory exists
    if [ ! -d "$PID_DIR" ]; then
        echo -e "${YELLOW}No services appear to be running${NC}"
        exit 0
    fi

    # Stop services in reverse order
    for service in "${SERVICES[@]}"; do
        if ! stop_service "$service"; then
            failed=1
        fi
        # Small delay between service shutdowns
        sleep 1
    done

    if [ $failed -eq 1 ]; then
        echo -e "${YELLOW}Some services failed to stop gracefully${NC}"
        read -p "Force cleanup? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cleanup_all
        fi
    else
        echo ""
        echo -e "${GREEN}All services stopped successfully${NC}"
    fi

    # Final verification
    echo ""
    echo "Remaining processes:"
    pgrep -f "market_data_service|order_execution_service|risk_management_service|strategy_engine|api_gateway" || echo "None"
}

# Option to force kill all
if [ "$1" = "--force" ]; then
    echo -e "${RED}Force stopping all services...${NC}"
    cleanup_all
    exit 0
fi

main
