# Observability Stack Integration Guide

## Overview

The observability stack is now fully integrated into the trading system startup process. With a single command, you can launch:

- **FastAPI Observability API** (port 8000)
- **React Real-Time Dashboard** (port 3000, optional)
- **DuckDB & SQLite Databases** (automatic initialization)
- **Complete Trading System** (backtesting → validation → paper trading)
- **Automatic Browser Launch** (to dashboard)

## Quick Start

### One-Command Startup

```bash
# Start everything with observability
./scripts/start_trading.sh

# Start without dashboard
./scripts/start_trading.sh --no-dashboard

# Start without observability (legacy mode)
./scripts/start_trading.sh --no-observability
```

### What Happens on Startup

```
1. ✓ Dependency verification (Python packages, Node.js, ports)
2. ✓ Directory creation (logs/, data/, monitoring/)
3. ✓ Database initialization (DuckDB metrics.duckdb, SQLite events.db)
4. ✓ FastAPI server starts (http://localhost:8000)
5. ✓ React dashboard starts (http://localhost:3000, if enabled)
6. ✓ Browser auto-opens to dashboard
7. ✓ Trading system launches (backtest → validate → trade)
8. ✓ Real-time metrics stream at 10Hz
```

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Trading System Process                     │
│  (Rust microservices + Python backtesting/trading)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Metrics & Events
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Observability API                       │
│                  (port 8000)                                 │
├─────────────────────────────────────────────────────────────┤
│  • REST Endpoints (/api/metrics, /api/trades, /api/system)  │
│  • WebSocket Stream (ws://localhost:8000/ws/metrics)        │
│  • Health Checks (/health, /health/ready, /health/live)     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ WebSocket (10Hz)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              React Dashboard (port 3000)                     │
│  • Real-time charts (TradingView, Chart.js)                 │
│  • Live metrics display                                      │
│  • Trade history & P&L                                       │
│  • System health monitoring                                  │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ Persistence
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     Databases                                │
├─────────────────────────────────────────────────────────────┤
│  • DuckDB (data/metrics.duckdb)                             │
│    - Market data, strategy metrics, execution, system       │
│  • SQLite (data/events.db)                                  │
│    - Real-time events, alerts                               │
└─────────────────────────────────────────────────────────────┘
```

## Scripts

### Main Scripts

#### `/scripts/start_trading.sh`
Master script that orchestrates everything.

**Options:**
- `--no-observability`: Skip observability stack (legacy mode)
- `--no-dashboard`: Start API only, no React dashboard

**Features:**
- Dependency verification
- Observability startup
- Trading system launch
- Graceful shutdown (Ctrl+C)
- State persistence on exit

#### `/scripts/check_dependencies.sh`
Comprehensive dependency checker.

**Checks:**
- System commands (python3, pip3, cargo, curl, node, npm)
- Python version (>= 3.8)
- Python packages (fastapi, uvicorn, duckdb, etc.)
- Directory structure
- Configuration files (.env, system.json)
- Port availability (8000, 3000, 5001-5003)
- Database files

**Usage:**
```bash
./scripts/check_dependencies.sh
```

#### `/scripts/start_observability.sh`
Standalone observability stack launcher.

**Options:**
- `--no-dashboard`: API only mode

**Features:**
- Directory setup
- Database initialization
- FastAPI server startup
- Optional dashboard startup
- Auto-browser launch
- Health monitoring loop

**Usage:**
```bash
# Start observability standalone
./scripts/start_observability.sh

# API only
./scripts/start_observability.sh --no-dashboard
```

## Startup Sequence

### Detailed Flow

```bash
#!/bin/bash
# This is what happens inside start_trading.sh

# 1. Pre-flight checks
./scripts/check_dependencies.sh || exit 1

# 2. Observability startup (background)
./scripts/start_observability.sh &
OBSERVABILITY_PID=$!

# 3. Wait for API ready
while ! curl -s http://localhost:8000/health; do
    sleep 1
done

# 4. Launch trading system
./scripts/autonomous_trading_system.sh --mode=full &
TRADING_PID=$!

# 5. Wait for completion
wait $TRADING_PID

# 6. Graceful shutdown
kill -TERM $OBSERVABILITY_PID
```

## Graceful Shutdown

### Shutdown Handlers

When you press **Ctrl+C**, the system performs graceful shutdown:

```bash
1. Signal caught (SIGINT/SIGTERM)
2. Trading system stops (close positions)
3. Observability API stops (flush metrics)
4. Dashboard stops
5. Final state saved to DuckDB
6. PID files cleaned up
7. Exit
```

### Implementation

```bash
cleanup() {
    log_info "Shutting down all services..."

    # Stop trading
    kill -TERM $TRADING_PID
    wait $TRADING_PID

    # Stop observability
    kill -TERM $OBSERVABILITY_PID
    wait $OBSERVABILITY_PID

    # Save state to DuckDB
    python3 <<'PYTHON'
import duckdb
conn = duckdb.connect('data/metrics.duckdb')
conn.execute("INSERT INTO system_metrics ...")
conn.close()
PYTHON

    log_success "Graceful shutdown complete"
}

trap cleanup EXIT INT TERM
```

## API Endpoints

### Base URL: `http://localhost:8000`

#### Health Endpoints

```bash
GET /health
# Basic health check
Response: {"status": "healthy", "service": "observability-api"}

GET /health/ready
# Readiness check (are collectors ready?)
Response: {
    "ready": true,
    "collectors": {
        "market_data": true,
        "strategy": true,
        "execution": true,
        "system": true
    }
}

GET /health/live
# Liveness check (is service alive?)
Response: {
    "alive": true,
    "websocket_connections": 2,
    "uptime_seconds": 3600.5
}
```

#### Metrics Endpoints

```bash
GET /api/metrics/current
# Get current metrics snapshot

GET /api/metrics/history?minutes=60
# Get historical metrics (last N minutes)

GET /api/metrics/market-data?symbol=AAPL
# Market data metrics for symbol

GET /api/metrics/strategy?name=momentum
# Strategy performance metrics

GET /api/metrics/execution?minutes=30
# Execution metrics (latency, fill rates)

GET /api/metrics/system
# System health metrics (CPU, memory, disk)
```

#### Trade Endpoints

```bash
GET /api/trades/active
# Get active trades

GET /api/trades/history?limit=100
# Get trade history

GET /api/trades/{trade_id}
# Get specific trade details

GET /api/trades/pnl?period=today
# Get P&L summary
```

#### System Endpoints

```bash
GET /api/system/status
# Overall system status

GET /api/system/performance
# Performance statistics

GET /api/system/alerts
# Active alerts and warnings
```

#### WebSocket Endpoint

```bash
WS ws://localhost:8000/ws/metrics
# Real-time metric streaming at 10Hz

# Message format:
{
    "timestamp": 1697654321.123,
    "market_data": { ... },
    "strategy": { ... },
    "execution": { ... },
    "system": { ... }
}

# Client sends:
"ping" -> server responds "pong"
"subscribe:market_data" -> selective subscription
```

## Databases

### DuckDB: `data/metrics.duckdb`

**Tables:**

```sql
-- Market data metrics
CREATE TABLE market_data_metrics (
    timestamp TIMESTAMP,
    symbol VARCHAR,
    price DOUBLE,
    volume BIGINT,
    bid DOUBLE,
    ask DOUBLE,
    spread DOUBLE,
    PRIMARY KEY (timestamp, symbol)
);

-- Strategy metrics
CREATE TABLE strategy_metrics (
    timestamp TIMESTAMP,
    strategy_name VARCHAR,
    signal VARCHAR,
    confidence DOUBLE,
    indicators JSON,
    PRIMARY KEY (timestamp, strategy_name)
);

-- Execution metrics
CREATE TABLE execution_metrics (
    timestamp TIMESTAMP,
    order_id VARCHAR,
    symbol VARCHAR,
    side VARCHAR,
    quantity INTEGER,
    price DOUBLE,
    status VARCHAR,
    latency_ms DOUBLE,
    PRIMARY KEY (timestamp, order_id)
);

-- System metrics
CREATE TABLE system_metrics (
    timestamp TIMESTAMP,
    cpu_percent DOUBLE,
    memory_percent DOUBLE,
    disk_usage_percent DOUBLE,
    network_sent_mb DOUBLE,
    network_recv_mb DOUBLE,
    active_threads INTEGER,
    PRIMARY KEY (timestamp)
);
```

**Querying:**

```bash
# Interactive query
python3 -c "
import duckdb
conn = duckdb.connect('data/metrics.duckdb')
result = conn.execute('SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT 10')
print(result.fetchall())
conn.close()
"
```

### SQLite: `data/events.db`

**Tables:**

```sql
-- Trade events
CREATE TABLE trade_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    event_type TEXT,
    symbol TEXT,
    data TEXT  -- JSON
);

-- Alert events
CREATE TABLE alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    severity TEXT,
    message TEXT,
    metadata TEXT  -- JSON
);
```

## Directory Structure

```
RustAlgorithmTrading/
├── logs/
│   ├── observability/
│   │   ├── api.log              # FastAPI logs
│   │   ├── dashboard.log        # React dev server logs
│   │   └── dashboard_install.log
│   ├── trades/                  # Trade-specific logs
│   ├── metrics/                 # Metric logs
│   └── system/                  # System logs
├── data/
│   ├── metrics.duckdb          # Time-series metrics
│   ├── events.db               # Real-time events
│   ├── backtest_results/       # Backtest outputs
│   ├── simulation_results/     # Simulation outputs
│   └── live_trading/           # Live trading data
├── monitoring/
│   ├── observability_api.pid   # API process ID
│   ├── dashboard.pid           # Dashboard process ID
│   └── run_api.py              # Generated API launcher
├── scripts/
│   ├── start_trading.sh        # Master startup script
│   ├── start_observability.sh  # Observability launcher
│   ├── check_dependencies.sh   # Dependency checker
│   └── autonomous_trading_system.sh  # Trading system
└── src/
    └── observability/
        ├── api/                # FastAPI application
        ├── dashboard/          # React dashboard
        ├── metrics/            # Metric collectors
        ├── logging/            # Structured logging
        └── models/             # Data models
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill process
lsof -ti :8000 | xargs kill -9

# Check dependencies script handles this automatically
./scripts/check_dependencies.sh
```

### Database Connection Errors

```bash
# Check if databases exist
ls -la data/*.db data/*.duckdb

# Reinitialize databases
rm data/metrics.duckdb data/events.db
./scripts/start_observability.sh
```

### API Not Starting

```bash
# Check logs
tail -f logs/observability/api.log

# Verify Python packages
pip3 list | grep -E "(fastapi|uvicorn|duckdb)"

# Run dependency check
./scripts/check_dependencies.sh
```

### Dashboard Not Starting

```bash
# Check Node.js/npm
node --version
npm --version

# Install dependencies
cd src/observability/dashboard
npm install

# Check logs
tail -f logs/observability/dashboard.log

# Start without dashboard
./scripts/start_trading.sh --no-dashboard
```

### WebSocket Connection Fails

```bash
# Test WebSocket endpoint
wscat -c ws://localhost:8000/ws/metrics

# Check CORS settings in main.py
# Should allow localhost:3000 and localhost:5173

# Verify API is running
curl http://localhost:8000/health
```

## Advanced Usage

### Running Components Separately

```bash
# 1. Only observability (no trading)
./scripts/start_observability.sh

# 2. Only trading (no observability)
./scripts/start_trading.sh --no-observability

# 3. Only API (no dashboard)
./scripts/start_observability.sh --no-dashboard
```

### Custom API Port

Edit `/scripts/start_observability.sh`:

```python
# In run_api.py generation
uvicorn.run(
    app,
    host="0.0.0.0",
    port=9000,  # Changed from 8000
    ...
)
```

### Custom Dashboard Port

Edit `src/observability/dashboard/vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    port: 4000,  // Changed from 3000
  }
})
```

### Production Deployment

```bash
# 1. Build optimized Rust services
cd rust
cargo build --release --workspace

# 2. Build dashboard for production
cd src/observability/dashboard
npm run build

# 3. Serve dashboard with API
# Edit start_observability.sh to serve static files
```

## Performance

### Metrics

- **API Latency**: < 10ms (REST), < 50ms (WebSocket)
- **Streaming Rate**: 10Hz (100ms intervals)
- **Database Write**: Batched every 1 second
- **Memory Usage**: ~200MB (API + collectors)
- **CPU Usage**: < 5% idle, < 15% during trading

### Optimization Tips

1. **Reduce WebSocket Frequency**: Change `await asyncio.sleep(0.1)` in `main.py`
2. **Limit Database History**: Implement data retention policies
3. **Disable Dashboard**: Use `--no-dashboard` for production
4. **Use Production Mode**: Set `reload=False` in Uvicorn config

## Dependencies

### Required Python Packages

```bash
pip3 install fastapi uvicorn websockets pydantic duckdb loguru psutil numpy pandas
```

### Optional Dependencies

```bash
# For dashboard
npm install  # in src/observability/dashboard

# For faster package management
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## FAQ

**Q: Can I skip observability?**
A: Yes, use `./scripts/start_trading.sh --no-observability`

**Q: How do I view real-time metrics?**
A: Open http://localhost:8000 in your browser (auto-opens)

**Q: Where are metrics stored?**
A: DuckDB at `data/metrics.duckdb` and SQLite at `data/events.db`

**Q: How do I export metrics?**
A: Use DuckDB export: `COPY (SELECT * FROM ...) TO 'output.csv' (HEADER, DELIMITER ',')`

**Q: Can I use a different database?**
A: Yes, modify collectors to use PostgreSQL, TimescaleDB, etc.

**Q: How do I secure the API?**
A: Add authentication middleware in `main.py` (JWT, API keys, etc.)

**Q: Can I run this on a remote server?**
A: Yes, change `host="0.0.0.0"` and configure firewall for ports 8000, 3000

## Next Steps

1. **Customize Dashboard**: Edit React components in `src/observability/dashboard/src/`
2. **Add Custom Metrics**: Extend collectors in `src/observability/metrics/`
3. **Setup Alerts**: Implement alerting rules in API routes
4. **Add Authentication**: Secure API with JWT or OAuth2
5. **Deploy to Production**: Setup reverse proxy (Nginx), HTTPS, monitoring

## Support

For issues or questions:
- Check logs in `logs/observability/`
- Run dependency checker: `./scripts/check_dependencies.sh`
- Review API docs: http://localhost:8000/docs
- Consult main README: `/docs/README.md`
