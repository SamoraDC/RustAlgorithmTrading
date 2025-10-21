# Deployment Scripts

This directory contains scripts for managing the Rust Algorithm Trading System.

## Scripts Overview

### start_trading_system.sh
Starts all trading system services in the correct dependency order.

**Usage:**
```bash
./scripts/start_trading_system.sh
```

**Features:**
- Validates environment configuration (.env file)
- Checks port availability before starting services
- Starts services in dependency order
- Waits for each service to be healthy before starting the next
- Creates PID files for process management
- Comprehensive logging

**Service Startup Order:**
1. Market Data Service (port 5555)
2. Order Execution Service (port 5556)
3. Risk Management Service (port 5557)
4. Strategy Engine (port 5558)
5. API Gateway (port 8080)

### stop_trading_system.sh
Gracefully stops all running services.

**Usage:**
```bash
./scripts/stop_trading_system.sh        # Graceful shutdown
./scripts/stop_trading_system.sh --force # Force kill all processes
```

**Features:**
- Stops services in reverse dependency order
- Sends SIGTERM for graceful shutdown
- Waits up to 30 seconds per service
- Force kills if graceful shutdown fails
- Cleans up PID files
- Option to force kill all processes

### health_check.sh
Monitors the health and status of all services.

**Usage:**
```bash
./scripts/health_check.sh          # Single check
./scripts/health_check.sh --watch  # Continuous monitoring (refreshes every 5s)
```

**Features:**
- Process status verification
- Port connectivity checks
- HTTP health endpoint validation (for API Gateway)
- Service uptime reporting
- Memory and CPU usage monitoring
- Recent error detection in logs
- Color-coded status output
- Watch mode for continuous monitoring

## Prerequisites

All scripts require:
- Bash shell
- Release binaries built (`cargo build --release`)
- `.env` file with required configuration
- Required system tools: `lsof`, `nc` (netcat), `curl`, `ps`

## Installation

Make scripts executable:
```bash
chmod +x scripts/*.sh
```

## Directory Structure

The scripts will create and use these directories:
- `logs/` - Service log files
- `pids/` - Process ID files for service management

## Environment Variables

Create a `.env` file in the project root with:
```bash
# Binance API credentials
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Risk management settings
MAX_POSITION_SIZE=10000
MAX_DAILY_LOSS=1000

# Service ports (optional, defaults shown)
MARKET_DATA_PORT=5555
ORDER_EXECUTION_PORT=5556
RISK_MANAGEMENT_PORT=5557
STRATEGY_ENGINE_PORT=5558
API_GATEWAY_PORT=8080
```

## Troubleshooting

### Services won't start
- Check that binaries are built: `cargo build --release`
- Verify .env file exists and is properly formatted
- Check that ports are not already in use
- Review logs in `logs/` directory

### Services crash after startup
- Check service logs in `logs/` directory
- Verify all environment variables are set
- Ensure dependencies are running (check with `health_check.sh`)

### Port already in use
```bash
# Find process using port
lsof -i :5555

# Kill process
kill -9 <PID>
```

### Force cleanup
If services are stuck:
```bash
./scripts/stop_trading_system.sh --force
```

## Production Deployment

For production deployment, consider:
1. Using systemd service files instead of these scripts
2. Setting up log rotation
3. Configuring automatic restart on failure
4. Using Docker Compose for containerized deployment
5. Setting up monitoring and alerting

## See Also

- [Docker Deployment](../docker/README.md)
- [CI/CD Pipeline](../.github/workflows/README.md)
- [Monitoring Setup](../monitoring/README.md)
