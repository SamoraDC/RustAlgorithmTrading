# Observability Backend API Documentation

## Overview

The Observability Backend provides a production-ready FastAPI application with WebSocket streaming for real-time monitoring of the algorithmic trading system.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
├─────────────────────────────────────────────────────────┤
│  REST API Endpoints          WebSocket Streaming        │
│  ├─ GET /api/metrics        ws://localhost:8000/ws      │
│  ├─ GET /api/trades         - Real-time updates         │
│  ├─ GET /api/system         - 10Hz streaming            │
│  └─ GET /health             - < 50ms latency            │
├─────────────────────────────────────────────────────────┤
│              Metric Collectors                           │
│  ├─ MarketDataCollector    (prices, volumes)           │
│  ├─ StrategyCollector      (P&L, positions)            │
│  ├─ ExecutionCollector     (orders, fills)             │
│  └─ SystemCollector        (CPU, memory, health)       │
├─────────────────────────────────────────────────────────┤
│           WebSocket Manager                              │
│  ├─ Connection Pool (100+ concurrent clients)          │
│  ├─ Broadcast Queue (backpressure handling)            │
│  ├─ Heartbeat/Ping-Pong                                │
│  └─ Rate Limiting                                       │
└─────────────────────────────────────────────────────────┘
```

## Features

### Real-Time Streaming
- **WebSocket endpoint** at `/ws/metrics`
- **10Hz update rate** (100ms intervals)
- **< 50ms latency** guarantee
- **100+ concurrent connections** supported
- **Automatic reconnection** handling
- **Heartbeat/ping-pong** for connection health

### REST API Endpoints

#### Metrics API
- `GET /api/metrics/current` - Current metrics snapshot
- `POST /api/metrics/history` - Historical metrics query
- `GET /api/metrics/symbols` - List tracked symbols
- `GET /api/metrics/summary` - High-level summary

#### Trades API
- `GET /api/trades` - Trade history with filters
- `GET /api/trades/{trade_id}` - Specific trade details
- `GET /api/trades/stats/summary` - Trade statistics
- `GET /api/trades/execution/quality` - Execution quality metrics

#### System API
- `GET /api/system/health` - System health status
- `GET /api/system/performance` - Performance metrics
- `GET /api/system/components` - Component status
- `GET /api/system/logs/recent` - Recent log entries
- `POST /api/system/alerts/acknowledge/{alert_id}` - Acknowledge alert
- `GET /api/system/stats` - System statistics

#### Health Checks
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (all services ready?)
- `GET /health/live` - Liveness check (service alive?)

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or with uv (faster)
uv pip install -r requirements.txt
```

### Starting the Server

```bash
# Basic start
python scripts/start_observability_api.py

# With auto-reload (development)
python scripts/start_observability_api.py --reload

# Custom port
python scripts/start_observability_api.py --port 8080

# Multiple workers (production)
python scripts/start_observability_api.py --workers 4
```

### Using uvicorn directly

```bash
# Development
uvicorn src.observability.api.main:app --reload --port 8000

# Production
uvicorn src.observability.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Usage Examples

### REST API

#### Get Current Metrics
```bash
curl http://localhost:8000/api/metrics/current
```

Response:
```json
{
  "timestamp": "2025-10-21T22:00:00Z",
  "market_data": {
    "AAPL": {
      "last_price": 150.25,
      "bid": 150.24,
      "ask": 150.26,
      "volume": 1250000,
      "trades": 5420
    }
  },
  "strategy": {
    "total_pnl": 1250.50,
    "daily_pnl": 125.75,
    "open_positions": 3
  },
  "execution": {
    "fill_rate": 0.95,
    "avg_latency_ms": 45.3
  },
  "system": {
    "cpu_percent": 35.2,
    "memory_percent": 62.1,
    "health": "healthy"
  }
}
```

#### Query Trade History
```bash
curl -X GET "http://localhost:8000/api/trades?symbol=AAPL&limit=10"
```

#### Get System Health
```bash
curl http://localhost:8000/api/system/health
```

### WebSocket Streaming

#### JavaScript Client
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onopen = () => {
    console.log('Connected to metrics stream');

    // Send heartbeat
    setInterval(() => {
        ws.send('ping');
    }, 15000);
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'connected') {
        console.log('Connected:', data);
    } else if (data.type === 'metrics_update') {
        console.log('Metrics:', data);
        // Update your dashboard UI
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected from metrics stream');
    // Implement reconnection logic
};
```

#### Python Client
```python
import asyncio
import websockets
import json

async def stream_metrics():
    uri = "ws://localhost:8000/ws/metrics"

    async with websockets.connect(uri) as websocket:
        print("Connected to metrics stream")

        # Start heartbeat task
        async def heartbeat():
            while True:
                await asyncio.sleep(15)
                await websocket.send("ping")

        heartbeat_task = asyncio.create_task(heartbeat())

        try:
            async for message in websocket:
                if message == "pong":
                    continue

                data = json.loads(message)
                print(f"Received: {data['timestamp']}")

                # Process metrics
                if 'market_data' in data:
                    print(f"Market data: {data['market_data']}")
        finally:
            heartbeat_task.cancel()

# Run
asyncio.run(stream_metrics())
```

## Performance Characteristics

### Latency Targets
- **WebSocket latency**: < 50ms (p99)
- **REST API response**: < 100ms (p95)
- **Metric collection**: 10Hz (100ms intervals)
- **Broadcast fanout**: < 10ms for 100 clients

### Scalability
- **Concurrent WebSocket connections**: 100+
- **HTTP requests per second**: 1000+
- **Metric updates per second**: 10 per client
- **Memory usage**: < 200MB per worker

### Resource Usage (Typical)
- **CPU**: 20-40% (1 worker)
- **Memory**: 150-200MB
- **Network**: ~10KB/s per WebSocket connection

## Configuration

### Environment Variables
```bash
# API Configuration
export API_HOST="0.0.0.0"
export API_PORT=8000
export API_WORKERS=4

# CORS Configuration
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173"

# WebSocket Configuration
export WS_MAX_CONNECTIONS=100
export WS_HEARTBEAT_INTERVAL=15
export WS_MESSAGE_QUEUE_SIZE=1000

# Collector Configuration
export METRIC_COLLECTION_INTERVAL=0.1  # 10Hz

# Logging
export LOG_LEVEL="INFO"
```

## Integration Points

### Market Data Feed
```python
from observability.metrics import MarketDataCollector

collector = MarketDataCollector()
await collector.start()

# Add symbols to track
await collector.add_symbol("AAPL")
await collector.add_symbol("MSFT")
```

### Strategy Engine
```python
from observability.metrics import StrategyCollector

collector = StrategyCollector()
await collector.start()

# Metrics are automatically collected
# from strategy engine via pub-sub
```

### Execution Engine
```python
from observability.metrics import ExecutionCollector

collector = ExecutionCollector()
await collector.start()

# Tracks orders and fills automatically
```

## Monitoring the API

### Prometheus Metrics
The API exposes Prometheus-compatible metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `websocket_connections_active` - Active WebSocket connections
- `websocket_messages_sent_total` - Total messages broadcasted
- `collector_metrics_collected_total` - Metrics collected per collector

### Health Monitoring
```bash
# Continuous health check
watch -n 5 curl -s http://localhost:8000/health/ready | jq
```

## Development

### Project Structure
```
src/observability/
├── api/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application
│   ├── websocket_manager.py     # WebSocket connection manager
│   └── routes/
│       ├── metrics.py           # Metrics endpoints
│       ├── trades.py            # Trade endpoints
│       └── system.py            # System endpoints
├── metrics/
│   ├── __init__.py
│   ├── collectors.py            # Base collector interface
│   ├── market_data_collector.py
│   ├── strategy_collector.py
│   ├── execution_collector.py
│   └── system_collector.py
└── models/
    ├── __init__.py
    ├── schemas.py               # Pydantic request/response models
    ├── metrics_models.py        # Internal metric structures
    └── events_models.py         # Event types for streaming
```

### Running Tests
```bash
# Run all tests
pytest tests/observability/

# Run with coverage
pytest --cov=src/observability tests/observability/

# Test WebSocket endpoint
pytest tests/observability/test_websocket.py -v
```

### Adding New Collectors

1. **Inherit from BaseCollector**:
```python
from observability.metrics.collectors import BaseCollector

class CustomCollector(BaseCollector):
    def __init__(self):
        super().__init__("custom")

    async def _start_impl(self):
        # Start collection
        pass

    async def _stop_impl(self):
        # Stop collection
        pass

    async def get_current_metrics(self) -> dict:
        # Return current metrics
        return {}
```

2. **Register in main.py**:
```python
self.collectors["custom"] = CustomCollector()
```

## Troubleshooting

### WebSocket Connection Fails
- Check CORS configuration
- Verify firewall rules
- Check server logs for errors

### High Latency
- Increase worker count
- Check network bandwidth
- Monitor system resources
- Reduce update frequency if needed

### Memory Growth
- Check for connection leaks
- Verify proper cleanup on disconnect
- Monitor recent_trades buffer size
- Adjust queue sizes if needed

## Production Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/

EXPOSE 8000

CMD ["python", "scripts/start_observability_api.py", "--workers", "4"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  observability-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_WORKERS=4
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Nginx Reverse Proxy
```nginx
upstream observability_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name observability.example.com;

    location / {
        proxy_pass http://observability_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://observability_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

## Support

For issues or questions:
- Check the [API documentation](http://localhost:8000/docs)
- Review logs in `.logs/observability/`
- Contact the development team

## License

Internal use only - Trading System Team
