# Database Module API Documentation

## Overview

The database module provides high-performance time-series storage and operational data management using DuckDB and SQLite.

## Architecture

```
src/observability/storage/
├── __init__.py              # Public API exports
├── schemas.py               # Data models & SQL schemas
├── duckdb_client.py         # DuckDB time-series client
├── sqlite_client.py         # SQLite operational client
└── integration.py           # FastAPI integration
```

## DuckDB Client

### Class: `DuckDBClient`

High-performance analytics database for time-series trading data.

#### Initialization

```python
from src.observability.storage import DuckDBClient

client = DuckDBClient(
    db_path="data/trading_metrics.duckdb",  # Database file path
    read_only=False,                         # Read-only mode
    threads=4                                # Query threads
)

# Initialize database and create tables
await client.initialize()
```

#### Write Operations

##### `insert_metric(metric: MetricRecord) -> None`

Insert single metric record.

```python
from src.observability.storage.schemas import MetricRecord
from datetime import datetime

metric = MetricRecord(
    timestamp=datetime.utcnow(),
    metric_name="order_latency_ms",
    value=42.5,
    symbol="AAPL",
    labels={"exchange": "alpaca"}
)

await client.insert_metric(metric)
```

##### `insert_metrics(metrics: List[MetricRecord]) -> None`

Batch insert metrics (recommended for performance).

**Performance**: <1ms per 1000 records

```python
metrics = [
    MetricRecord(
        timestamp=datetime.utcnow(),
        metric_name="price",
        value=150.0 + i,
        symbol="AAPL"
    )
    for i in range(1000)
]

await client.insert_metrics(metrics)
```

##### `insert_candle(candle: CandleRecord) -> None`

Insert OHLCV candle data.

```python
from src.observability.storage.schemas import CandleRecord

candle = CandleRecord(
    timestamp=datetime.utcnow(),
    symbol="BTC/USD",
    open=50000.0,
    high=51000.0,
    low=49500.0,
    close=50500.0,
    volume=1000000
)

await client.insert_candle(candle)
```

##### `insert_candles(candles: List[CandleRecord]) -> None`

Batch insert candles.

```python
candles = [...]  # List of CandleRecord
await client.insert_candles(candles)
```

##### `insert_performance(record: PerformanceRecord) -> None`

Insert portfolio performance snapshot.

```python
from src.observability.storage.schemas import PerformanceRecord

perf = PerformanceRecord(
    timestamp=datetime.utcnow(),
    portfolio_value=105000.0,
    pnl=5000.0,
    sharpe_ratio=2.5,
    max_drawdown=-0.05,
    win_rate=0.65,
    total_trades=150
)

await client.insert_performance(perf)
```

#### Query Operations

##### `get_metrics(metric_name: str, start_time: datetime, end_time: Optional[datetime] = None, symbol: Optional[str] = None, limit: int = 10000) -> List[Dict[str, Any]]`

Query metrics with time range filtering.

**Performance**: <50ms for 1M records

```python
from datetime import datetime, timedelta

# Get last hour of latency metrics
metrics = await client.get_metrics(
    metric_name="order_latency_ms",
    start_time=datetime.utcnow() - timedelta(hours=1),
    symbol="AAPL",
    limit=1000
)

# Returns:
# [
#     {
#         "timestamp": datetime(...),
#         "metric_name": "order_latency_ms",
#         "value": 42.5,
#         "symbol": "AAPL",
#         "labels": {"exchange": "alpaca"}
#     },
#     ...
# ]
```

##### `get_candles(symbol: str, interval: TimeInterval, start_time: datetime, end_time: Optional[datetime] = None, limit: int = 1000) -> List[Dict[str, Any]]`

Query candles with time-bucketing.

```python
from src.observability.storage.schemas import TimeInterval

# Get 1-minute candles
candles = await client.get_candles(
    symbol="BTC/USD",
    interval=TimeInterval.MINUTE,
    start_time=datetime.utcnow() - timedelta(hours=24),
    limit=1440  # 24 hours * 60 minutes
)

# Returns:
# [
#     {
#         "timestamp": datetime(...),
#         "open": 50000.0,
#         "high": 51000.0,
#         "low": 49500.0,
#         "close": 50500.0,
#         "volume": 1000000
#     },
#     ...
# ]
```

##### `get_aggregated_metrics(metric_name: str, interval: TimeInterval, start_time: datetime, end_time: Optional[datetime] = None, aggregation: str = "avg") -> List[Dict[str, Any]]`

Get time-bucketed aggregated metrics.

**Aggregations**: avg, sum, min, max, count

```python
# Get hourly average latency
aggregated = await client.get_aggregated_metrics(
    metric_name="order_latency_ms",
    interval=TimeInterval.HOUR,
    start_time=datetime.utcnow() - timedelta(days=7),
    aggregation="avg"
)

# Returns:
# [
#     {
#         "timestamp": datetime(...),
#         "value": 45.2,        # avg(latency)
#         "sample_count": 3600  # samples in hour
#     },
#     ...
# ]
```

##### `get_performance_summary(start_time: datetime, end_time: Optional[datetime] = None) -> Dict[str, Any]`

Get aggregated performance metrics.

```python
summary = await client.get_performance_summary(
    start_time=datetime.utcnow() - timedelta(days=30)
)

# Returns:
# {
#     "start_value": 100000.0,
#     "end_value": 105000.0,
#     "total_pnl": 5000.0,
#     "return_pct": 5.0,
#     "avg_sharpe": 2.5,
#     "worst_drawdown": -0.05,
#     "avg_win_rate": 0.65,
#     "total_trades": 150
# }
```

##### `get_latest_metrics(limit: int = 100) -> List[Dict[str, Any]]`

Get most recent metrics across all types.

```python
latest = await client.get_latest_metrics(limit=50)

# Returns latest value for each metric/symbol pair
```

#### Maintenance Operations

##### `optimize() -> None`

Optimize database for better query performance.

```python
# Run periodically (e.g., daily)
await client.optimize()  # VACUUM + CHECKPOINT
```

##### `get_table_stats() -> Dict[str, Dict[str, Any]]`

Get storage statistics for all tables.

```python
stats = await client.get_table_stats()

# Returns:
# {
#     "trading_metrics": {
#         "row_count": 1000000,
#         "min_timestamp": datetime(...),
#         "max_timestamp": datetime(...)
#     },
#     "candles": {...},
#     "performance_history": {...}
# }
```

##### `close() -> None`

Close database connection.

```python
await client.close()
```

### Context Manager

```python
from src.observability.storage import duckdb_session

# Automatic connection management
async with duckdb_session("data/metrics.duckdb") as client:
    await client.insert_metric(...)
    metrics = await client.get_metrics(...)
# Connection automatically closed
```

## SQLite Client

### Class: `SQLiteClient`

Operational database for transactional data (trade logs, system events).

#### Initialization

```python
from src.observability.storage import SQLiteClient

client = SQLiteClient("data/trading_operational.db")
await client.initialize()
```

#### Write Operations

##### `log_trade(timestamp: datetime, symbol: str, side: str, quantity: float, price: float, order_id: Optional[str] = None, status: str = "executed", metadata: Optional[Dict] = None) -> int`

Log trade execution.

```python
trade_id = await client.log_trade(
    timestamp=datetime.utcnow(),
    symbol="AAPL",
    side="buy",
    quantity=100.0,
    price=150.0,
    order_id="alpaca-123",
    status="executed",
    metadata={"strategy": "momentum"}
)
```

##### `log_event(event_type: str, severity: str, message: str, details: Optional[Dict] = None) -> int`

Log system event.

```python
event_id = await client.log_event(
    event_type="order",
    severity="error",
    message="Order failed: insufficient funds",
    details={"order_id": "123", "symbol": "AAPL"}
)
```

#### Query Operations

##### `get_trades(start_time: datetime, end_time: Optional[datetime] = None, symbol: Optional[str] = None, limit: int = 1000) -> List[Dict]`

Query trade history.

```python
trades = await client.get_trades(
    start_time=datetime.utcnow() - timedelta(days=7),
    symbol="AAPL",
    limit=100
)
```

##### `get_events(start_time: datetime, end_time: Optional[datetime] = None, event_type: Optional[str] = None, severity: Optional[str] = None, limit: int = 1000) -> List[Dict]`

Query system events.

```python
events = await client.get_events(
    start_time=datetime.utcnow() - timedelta(hours=1),
    severity="error"
)
```

## Data Models

### `MetricRecord`

Trading metric record.

```python
@dataclass
class MetricRecord:
    timestamp: datetime          # Metric timestamp
    metric_name: str            # Metric identifier
    value: float                # Numeric value
    symbol: Optional[str]       # Trading symbol (optional)
    labels: Optional[Dict]      # Additional labels (optional)

    def to_dict(self) -> Dict[str, Any]
```

### `CandleRecord`

OHLCV candle record.

```python
@dataclass
class CandleRecord:
    timestamp: datetime  # Candle timestamp
    symbol: str         # Trading symbol
    open: float         # Opening price
    high: float         # High price
    low: float          # Low price
    close: float        # Closing price
    volume: int         # Trading volume

    def to_dict(self) -> Dict[str, Any]
```

### `PerformanceRecord`

Portfolio performance record.

```python
@dataclass
class PerformanceRecord:
    timestamp: datetime              # Snapshot timestamp
    portfolio_value: float           # Total portfolio value
    pnl: float                       # Profit & Loss
    sharpe_ratio: Optional[float]    # Sharpe ratio
    max_drawdown: Optional[float]    # Maximum drawdown
    win_rate: Optional[float]        # Win rate (0-1)
    total_trades: Optional[int]      # Total trades executed

    def to_dict(self) -> Dict[str, Any]
```

### `TimeInterval`

Time interval enum for aggregations.

```python
class TimeInterval(str, Enum):
    SECOND = "1s"   # 1-second buckets
    MINUTE = "1m"   # 1-minute buckets
    HOUR = "1h"     # 1-hour buckets
    DAY = "1d"      # 1-day buckets
    WEEK = "1w"     # 1-week buckets
    MONTH = "1mo"   # 1-month buckets

    @property
    def seconds(self) -> int
        """Get interval in seconds"""

    @property
    def duckdb_interval(self) -> str
        """Get DuckDB interval expression"""
```

## FastAPI Integration

### Dependency Injection

```python
from fastapi import FastAPI, Depends
from src.observability.storage.integration import (
    storage_lifespan,
    get_storage,
    StorageManager
)

# Initialize app with storage
app = FastAPI(lifespan=storage_lifespan)

@app.get("/api/metrics/{metric_name}")
async def get_metrics(
    metric_name: str,
    storage: StorageManager = Depends(get_storage)
):
    """Get metrics using dependency injection"""
    metrics = await storage.get_recent_metrics(metric_name, minutes=60)
    return {"metrics": metrics}
```

### StorageManager

Unified interface for DuckDB and SQLite.

```python
class StorageManager:
    duckdb: DuckDBClient    # Time-series analytics
    sqlite: SQLiteClient    # Operational data

    async def get_recent_metrics(
        self,
        metric_name: str,
        minutes: int = 60
    ) -> List[Dict]

    async def get_recent_trades(
        self,
        minutes: int = 60
    ) -> List[Dict]

    async def get_system_status(self) -> Dict
```

## Error Handling

### Common Exceptions

```python
try:
    await client.insert_metric(metric)
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Database operation failed")
```

### Connection Management

```python
# Always close connections
try:
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()
    # ... operations ...
finally:
    await client.close()

# Or use context manager (recommended)
async with duckdb_session() as client:
    # ... operations ...
    pass  # Automatically closed
```

## Performance Best Practices

### 1. Batch Operations

```python
# Good: Batch insert (10-100x faster)
await client.insert_metrics(batch)

# Bad: Individual inserts
for metric in batch:
    await client.insert_metric(metric)
```

### 2. Use Time Filters

```python
# Good: Time range filter
await client.get_metrics(
    "price",
    start_time=datetime.now() - timedelta(hours=1)
)

# Bad: No filter (full table scan)
await client.get_metrics("price")
```

### 3. Limit Result Sets

```python
# Good: Limit results
await client.get_metrics("price", start_time=..., limit=1000)

# Bad: Unlimited results (potential OOM)
await client.get_metrics("price", start_time=..., limit=999999)
```

### 4. Use Aggregations

```python
# Good: Server-side aggregation
await client.get_aggregated_metrics(
    "latency",
    interval=TimeInterval.MINUTE,
    aggregation="avg"
)

# Bad: Client-side aggregation
raw = await client.get_metrics("latency")
avg = sum(m["value"] for m in raw) / len(raw)
```

## Examples

### Complete Usage Example

```python
from datetime import datetime, timedelta
from src.observability.storage import (
    DuckDBClient,
    MetricRecord,
    CandleRecord,
    TimeInterval
)

async def trading_analytics():
    # Initialize client
    async with duckdb_session("data/metrics.duckdb") as client:
        # Record metrics
        await client.insert_metrics([
            MetricRecord(
                timestamp=datetime.utcnow(),
                metric_name="price",
                value=150.0,
                symbol="AAPL"
            ),
            MetricRecord(
                timestamp=datetime.utcnow(),
                metric_name="volume",
                value=1000000,
                symbol="AAPL"
            )
        ])

        # Query recent prices
        prices = await client.get_metrics(
            metric_name="price",
            start_time=datetime.utcnow() - timedelta(hours=1),
            symbol="AAPL"
        )

        # Get hourly aggregates
        hourly_avg = await client.get_aggregated_metrics(
            metric_name="price",
            interval=TimeInterval.HOUR,
            start_time=datetime.utcnow() - timedelta(days=7),
            aggregation="avg"
        )

        # Get performance summary
        performance = await client.get_performance_summary(
            start_time=datetime.utcnow() - timedelta(days=30)
        )

        return {
            "latest_prices": prices,
            "hourly_average": hourly_avg,
            "performance": performance
        }
```

## References

- **DuckDB Documentation**: https://duckdb.org/docs/
- **Storage Guide**: /docs/STORAGE_GUIDE.md
- **Migration Guide**: /docs/migration/DUCKDB_MIGRATION.md
- **Observability Guide**: /docs/observability/DUCKDB_OBSERVABILITY.md
