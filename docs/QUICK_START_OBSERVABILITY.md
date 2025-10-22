# Quick Start: One-Command Trading with Observability

## TL;DR

```bash
# One command to start everything:
./scripts/start_trading.sh

# Opens browser automatically to http://localhost:8000
# Watch real-time metrics, trades, and system health
# Press Ctrl+C for graceful shutdown
```

## What You Get

```
✓ Real-time dashboard at http://localhost:8000
✓ API documentation at http://localhost:8000/docs
✓ WebSocket streaming at ws://localhost:8000/ws/metrics
✓ Automatic dependency checking
✓ Database initialization (DuckDB + SQLite)
✓ Complete trading pipeline (backtest → validate → trade)
✓ Graceful shutdown with state persistence
```

## Before First Run

### 1. Install Dependencies

```bash
# Python packages
pip3 install fastapi uvicorn websockets pydantic duckdb loguru psutil numpy pandas

# Or use the setup script
./scripts/setup_python_deps.sh
```

### 2. Create .env File

```bash
# Create .env in project root
cat > .env <<EOF
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_PAPER=true
EOF
```

### 3. Verify Dependencies

```bash
# Check if everything is ready
./scripts/check_dependencies.sh
```

## Usage Examples

### Standard Startup

```bash
# Start everything (recommended)
./scripts/start_trading.sh

# Output:
# ✓ All dependencies verified
# ✓ Observability stack is ready
# 📊 Dashboard: http://localhost:8000
# 📖 API Docs: http://localhost:8000/docs
# ✓ Starting trading system...
```

### Without Dashboard

```bash
# API only (faster startup, less resources)
./scripts/start_trading.sh --no-dashboard

# Still get:
# - FastAPI server
# - WebSocket streaming
# - Database persistence
# - Real-time metrics
```

### Without Observability

```bash
# Legacy mode (trading only)
./scripts/start_trading.sh --no-observability

# Just runs the trading system
```

### Standalone Observability

```bash
# Start observability without trading
./scripts/start_observability.sh

# Useful for:
# - Testing dashboard
# - Viewing historical data
# - API development
```

## What Happens During Startup

```
[0:00] 📋 Checking dependencies...
[0:02] ✓ Python 3.11.5 (>= 3.8 required)
[0:02] ✓ fastapi, uvicorn, duckdb installed
[0:02] ✓ Port 8000 available
[0:03] ✓ All dependencies verified

[0:03] 🚀 Starting observability stack...
[0:04] ✓ Created directories (logs/, data/, monitoring/)
[0:05] ✓ DuckDB database initialized
[0:05] ✓ SQLite database initialized
[0:07] ✓ FastAPI server started (PID: 12345)
[0:10] ✓ Observability stack is ready

[0:10] 📊 Dashboard: http://localhost:8000
[0:10] 📖 API Docs: http://localhost:8000/docs

[0:11] 🤖 Starting trading system...
[0:15] ✓ Rust services built
[0:16] ⚙️  Running backtest...
[0:45] ✓ Backtest PASSED (Sharpe: 1.45)
[0:45] ⚙️  Running simulation...
[1:15] ✓ Simulation PASSED (Risk acceptable)
[1:15] 🔄 Starting paper trading...

🎉 All systems operational!
```

## Monitoring Your System

### Real-Time Dashboard

Open http://localhost:8000 to see:

- **Market Data**: Live price feeds, spreads, volume
- **Strategy Metrics**: Signals, confidence, indicators
- **Execution Stats**: Order latency, fill rates, slippage
- **System Health**: CPU, memory, disk, network
- **Trade History**: P&L, win rate, active positions

### API Endpoints

```bash
# Current metrics snapshot
curl http://localhost:8000/api/metrics/current

# Last 60 minutes of data
curl http://localhost:8000/api/metrics/history?minutes=60

# Active trades
curl http://localhost:8000/api/trades/active

# System status
curl http://localhost:8000/api/system/status
```

### WebSocket Streaming

```javascript
// Connect to real-time stream
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onmessage = (event) => {
    const metrics = JSON.parse(event.data);
    console.log('Market data:', metrics.market_data);
    console.log('Strategy:', metrics.strategy);
    console.log('Execution:', metrics.execution);
    console.log('System:', metrics.system);
};

// Heartbeat
setInterval(() => ws.send('ping'), 30000);
```

## Graceful Shutdown

Press **Ctrl+C** to stop:

```
[15:30:45] 🛑 Shutting down all services...
[15:30:45] ⏹️  Stopping trading system...
[15:30:46] ✓ All positions closed
[15:30:46] ⏹️  Stopping observability stack...
[15:30:47] 💾 Saving final state to database...
[15:30:47] ✓ Final state saved to DuckDB
[15:30:47] ✓ Graceful shutdown complete
```

## Accessing Historical Data

```bash
# Query DuckDB
python3 <<EOF
import duckdb
conn = duckdb.connect('data/metrics.duckdb')

# Last 100 system metrics
result = conn.execute('''
    SELECT timestamp, cpu_percent, memory_percent
    FROM system_metrics
    ORDER BY timestamp DESC
    LIMIT 100
''')

for row in result.fetchall():
    print(row)

conn.close()
EOF
```

```bash
# Export to CSV
python3 <<EOF
import duckdb
conn = duckdb.connect('data/metrics.duckdb')

conn.execute('''
    COPY (
        SELECT * FROM execution_metrics
        WHERE timestamp >= current_timestamp - INTERVAL 24 HOUR
    ) TO 'data/execution_last_24h.csv' (HEADER, DELIMITER ',')
''')

print("Exported to data/execution_last_24h.csv")
conn.close()
EOF
```

## Common Issues

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Kill the process
lsof -ti :8000 | xargs kill -9

# Or let the dependency checker handle it
./scripts/check_dependencies.sh
```

### Missing Dependencies

```bash
# Run dependency checker
./scripts/check_dependencies.sh

# Install missing packages
pip3 install <missing_package>
```

### API Not Starting

```bash
# Check logs
tail -f logs/observability/api.log

# Verify FastAPI is installed
python3 -c "import fastapi; print(fastapi.__version__)"

# Test manually
python3 monitoring/run_api.py
```

### Database Errors

```bash
# Remove and reinitialize
rm data/metrics.duckdb data/events.db

# Restart observability
./scripts/start_observability.sh
```

## Directory Structure

After first run, you'll see:

```
RustAlgorithmTrading/
├── logs/
│   └── observability/
│       ├── api.log              # FastAPI logs
│       └── dashboard.log        # Dashboard logs
├── data/
│   ├── metrics.duckdb          # Time-series metrics
│   └── events.db               # Real-time events
├── monitoring/
│   ├── observability_api.pid   # API process ID
│   ├── dashboard.pid           # Dashboard process ID
│   └── run_api.py              # Generated launcher
```

## Performance Tips

### Reduce Resource Usage

```bash
# Skip dashboard (saves ~100MB RAM)
./scripts/start_trading.sh --no-dashboard

# Use API directly via curl/HTTP clients
curl http://localhost:8000/api/metrics/current
```

### Optimize Streaming

Edit `src/observability/api/main.py`:

```python
# Change streaming interval (default 100ms)
await asyncio.sleep(0.5)  # 2Hz instead of 10Hz
```

### Database Cleanup

```bash
# Archive old metrics
python3 <<EOF
import duckdb
conn = duckdb.connect('data/metrics.duckdb')

# Export old data
conn.execute('''
    COPY (
        SELECT * FROM system_metrics
        WHERE timestamp < current_timestamp - INTERVAL 7 DAY
    ) TO 'data/archive_system_metrics.csv'
''')

# Delete old data
conn.execute('''
    DELETE FROM system_metrics
    WHERE timestamp < current_timestamp - INTERVAL 7 DAY
''')

conn.close()
EOF
```

## Next Steps

1. **Explore the Dashboard**: http://localhost:8000
2. **Read API Docs**: http://localhost:8000/docs
3. **Customize Metrics**: Edit `src/observability/metrics/`
4. **Add Alerts**: Implement rules in API routes
5. **Deploy to Production**: See `/docs/OBSERVABILITY_INTEGRATION.md`

## Help

```bash
# View all available commands
./scripts/start_trading.sh --help

# Check system health
curl http://localhost:8000/health/ready

# View logs
tail -f logs/observability/api.log
tail -f logs/autonomous/autonomous.log
```

## Summary

```bash
# Start everything
./scripts/start_trading.sh

# Monitor at http://localhost:8000
# Press Ctrl+C to stop gracefully
# Check logs/ for details
# Query data/ for historical metrics
```

That's it! You now have a fully observable algorithmic trading system running with real-time monitoring, automated backtesting, and production-grade infrastructure.
