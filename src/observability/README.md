# Observability API - Quick Start

Production-ready FastAPI backend with DuckDB for real-time trading metrics.

## Quick Start

### Development Mode (Auto-reload)
```bash
# Linux/Mac
./scripts/start_observability.sh --dev

# Windows
scripts\start_observability.bat --dev
```

### Production Mode
```bash
# Linux/Mac
./scripts/start_observability.sh --workers 4

# Windows
scripts\start_observability.bat --workers 4
```

### Direct Python Execution
```bash
# Development
python src/observability/server.py --dev

# Production
python src/observability/server.py --workers 4
```

## Access Points

- **API Docs**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws/metrics
- **Health Check**: http://localhost:8000/health

## Key Endpoints

### REST API
- `GET /api/metrics/current` - Current metrics snapshot
- `POST /api/metrics/history` - Historical data query
- `GET /api/metrics/summary` - Aggregated statistics
- `GET /api/trades` - Trade history
- `GET /api/system/health` - System health

### WebSocket
- `/ws/metrics` - Real-time streaming at 10Hz

## Features

- Real-time metrics streaming (10Hz, < 50ms latency)
- DuckDB embedded database (no separate server)
- Thread-safe connection pooling
- Batch write optimization
- Time-series aggregation queries
- Automatic data persistence
- Production-ready ASGI server

## Documentation

Full documentation: [docs/OBSERVABILITY_DUCKDB.md](../../docs/OBSERVABILITY_DUCKDB.md)

## Requirements

- Python 3.8+
- FastAPI
- DuckDB
- Uvicorn
- psutil

Install: `pip install -r requirements.txt`
