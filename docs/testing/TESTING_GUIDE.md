# Testing Guide - DuckDB Observability Stack

## Overview

This guide covers testing strategies for the DuckDB-based observability system, including unit tests, integration tests, performance benchmarks, and CI/CD integration.

## Test Architecture

```
tests/observability/
├── test_duckdb_client.py       # DuckDB client tests + benchmarks
├── test_sqlite_client.py       # SQLite client tests
├── test_integration.py         # FastAPI integration tests
├── test_api_endpoints.py       # API endpoint tests
├── test_websocket.py           # WebSocket streaming tests
├── test_collectors.py          # Metric collector tests
├── conftest.py                 # Pytest fixtures
└── benchmarks/
    ├── test_performance.py     # Performance benchmarks
    └── test_load.py            # Load testing
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/observability/ -v

# Run specific test file
pytest tests/observability/test_duckdb_client.py -v

# Run with coverage
pytest tests/observability/ --cov=src/observability --cov-report=html

# Run benchmarks only
pytest tests/observability/benchmarks/ -v -s

# Run in parallel (faster)
pytest tests/observability/ -n auto
```

### Test Categories

```bash
# Unit tests only
pytest tests/observability/ -m unit

# Integration tests only
pytest tests/observability/ -m integration

# Performance tests only
pytest tests/observability/ -m performance

# Skip slow tests
pytest tests/observability/ -m "not slow"
```

## Unit Tests

### DuckDB Client Tests

```python
# tests/observability/test_duckdb_client.py
import pytest
from datetime import datetime, timedelta
from src.observability.storage import DuckDBClient, MetricRecord

@pytest.mark.asyncio
async def test_insert_and_query_metrics(duckdb_client):
    """Test basic insert and query operations"""
    # Insert test metric
    metric = MetricRecord(
        timestamp=datetime.utcnow(),
        metric_name="test_metric",
        value=42.5,
        symbol="TEST"
    )
    await duckdb_client.insert_metric(metric)

    # Query back
    results = await duckdb_client.get_metrics(
        metric_name="test_metric",
        start_time=datetime.utcnow() - timedelta(hours=1)
    )

    assert len(results) == 1
    assert results[0]["value"] == 42.5
    assert results[0]["symbol"] == "TEST"

@pytest.mark.asyncio
async def test_batch_insert_performance(duckdb_client):
    """Test batch insert performance (<1ms per 1000 records)"""
    import time

    # Create 1000 metrics
    metrics = [
        MetricRecord(
            timestamp=datetime.utcnow(),
            metric_name="batch_test",
            value=float(i),
            symbol="BATCH"
        )
        for i in range(1000)
    ]

    # Measure insert time
    start = time.perf_counter()
    await duckdb_client.insert_metrics(metrics)
    elapsed = (time.perf_counter() - start) * 1000  # ms

    assert elapsed < 1.0, f"Batch insert took {elapsed}ms (target: <1ms)"

@pytest.mark.asyncio
async def test_time_bucketing(duckdb_client):
    """Test time-bucketed aggregations"""
    from src.observability.storage.schemas import TimeInterval

    # Insert metrics across time range
    base_time = datetime.utcnow()
    for i in range(100):
        await duckdb_client.insert_metric(
            MetricRecord(
                timestamp=base_time + timedelta(minutes=i),
                metric_name="time_test",
                value=float(i)
            )
        )

    # Query with 1-hour bucketing
    results = await duckdb_client.get_aggregated_metrics(
        metric_name="time_test",
        interval=TimeInterval.HOUR,
        start_time=base_time,
        aggregation="avg"
    )

    assert len(results) > 0
    assert "value" in results[0]
    assert "sample_count" in results[0]
```

### Pytest Fixtures

```python
# tests/observability/conftest.py
import pytest
import tempfile
from pathlib import Path
from src.observability.storage import DuckDBClient, SQLiteClient

@pytest.fixture
async def duckdb_client():
    """Provide isolated DuckDB client for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        client = DuckDBClient(str(db_path))
        await client.initialize()

        yield client

        await client.close()

@pytest.fixture
async def sqlite_client():
    """Provide isolated SQLite client for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        client = SQLiteClient(str(db_path))
        await client.initialize()

        yield client

        await client.close()

@pytest.fixture
def sample_metrics():
    """Generate sample metrics for testing"""
    from datetime import datetime
    from src.observability.storage.schemas import MetricRecord

    return [
        MetricRecord(
            timestamp=datetime.utcnow(),
            metric_name="test_metric",
            value=float(i),
            symbol=f"SYM{i % 10}"
        )
        for i in range(100)
    ]
```

## Integration Tests

### FastAPI Endpoint Tests

```python
# tests/observability/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from src.observability.api.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_current_metrics_endpoint():
    """Test current metrics endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/metrics/current")

    assert response.status_code == 200
    data = response.json()
    assert "market_data" in data
    assert "strategy" in data

@pytest.mark.asyncio
async def test_metrics_history_endpoint():
    """Test historical metrics endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/metrics/history?minutes=60")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### WebSocket Tests

```python
# tests/observability/test_websocket.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.observability.api.main import app

@pytest.mark.asyncio
async def test_websocket_streaming():
    """Test WebSocket metrics streaming"""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/metrics") as websocket:
            # Receive first message
            data = websocket.receive_json()

            assert "timestamp" in data
            assert "market_data" in data

            # Receive a few more messages
            for _ in range(5):
                data = websocket.receive_json()
                assert data is not None

@pytest.mark.asyncio
async def test_websocket_reconnection():
    """Test WebSocket automatic reconnection"""
    # Simulate connection drop and reconnect
    with TestClient(app) as client:
        # First connection
        with client.websocket_connect("/ws/metrics") as ws1:
            data1 = ws1.receive_json()
            assert data1 is not None

        # Reconnect (new connection)
        with client.websocket_connect("/ws/metrics") as ws2:
            data2 = ws2.receive_json()
            assert data2 is not None
```

## Performance Benchmarks

### Benchmark Suite

```python
# tests/observability/benchmarks/test_performance.py
import pytest
import time
import asyncio
from src.observability.storage import DuckDBClient, MetricRecord
from datetime import datetime, timedelta

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_insert_throughput(benchmark, duckdb_client):
    """Benchmark: Insert throughput (target: >1000 records/sec)"""
    metrics = [
        MetricRecord(
            timestamp=datetime.utcnow(),
            metric_name="benchmark",
            value=float(i)
        )
        for i in range(1000)
    ]

    async def insert_batch():
        await duckdb_client.insert_metrics(metrics)

    # Run benchmark
    result = benchmark(lambda: asyncio.run(insert_batch()))

    # Calculate throughput
    throughput = 1000 / result
    assert throughput > 1000, f"Throughput: {throughput:.0f} records/sec (target: >1000)"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_query_latency(benchmark, duckdb_client):
    """Benchmark: Query latency (target: <50ms for 1M records)"""
    # Insert 1M test records
    await _insert_million_records(duckdb_client)

    async def query():
        await duckdb_client.get_metrics(
            metric_name="benchmark",
            start_time=datetime.utcnow() - timedelta(hours=24),
            limit=10000
        )

    # Run benchmark
    result = benchmark(lambda: asyncio.run(query()))
    latency_ms = result * 1000

    assert latency_ms < 50, f"Query latency: {latency_ms:.1f}ms (target: <50ms)"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_aggregation_performance(benchmark, duckdb_client):
    """Benchmark: Time-bucketed aggregations"""
    from src.observability.storage.schemas import TimeInterval

    # Insert test data
    await _insert_million_records(duckdb_client)

    async def aggregate():
        await duckdb_client.get_aggregated_metrics(
            metric_name="benchmark",
            interval=TimeInterval.MINUTE,
            start_time=datetime.utcnow() - timedelta(days=1),
            aggregation="avg"
        )

    result = benchmark(lambda: asyncio.run(aggregate()))
    latency_ms = result * 1000

    assert latency_ms < 100, f"Aggregation latency: {latency_ms:.1f}ms (target: <100ms)"
```

### Load Testing

```python
# tests/observability/benchmarks/test_load.py
import pytest
import asyncio
from httpx import AsyncClient
from src.observability.api.main import app

@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Load test: 1000 concurrent API requests"""
    async def make_request(client):
        response = await client.get("/api/metrics/current")
        return response.status_code == 200

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1000 concurrent requests
        tasks = [make_request(client) for _ in range(1000)]
        results = await asyncio.gather(*tasks)

        success_rate = sum(results) / len(results)
        assert success_rate > 0.99, f"Success rate: {success_rate:.1%} (target: >99%)"

@pytest.mark.load
@pytest.mark.asyncio
async def test_websocket_concurrent_connections():
    """Load test: 100 concurrent WebSocket connections"""
    async def ws_client():
        with TestClient(app) as client:
            with client.websocket_connect("/ws/metrics") as ws:
                # Receive 10 messages
                for _ in range(10):
                    data = ws.receive_json()
                    assert data is not None
                return True

    tasks = [ws_client() for _ in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_rate = sum(1 for r in results if r is True) / len(results)
    assert success_rate > 0.95, f"Success rate: {success_rate:.1%} (target: >95%)"
```

## Test Coverage Analysis

```bash
# Generate coverage report
pytest tests/observability/ \
    --cov=src/observability \
    --cov-report=html \
    --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Coverage targets:
# - Overall: >90%
# - DuckDB client: >95%
# - API endpoints: >90%
# - Collectors: >85%
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-observability.yml
name: Test Observability Stack

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov pytest-benchmark

    - name: Run unit tests
      run: pytest tests/observability/ -v --cov=src/observability

    - name: Run benchmarks
      run: pytest tests/observability/benchmarks/ -v -s

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  performance:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Performance regression tests
      run: |
        pytest tests/observability/benchmarks/ \
          --benchmark-only \
          --benchmark-compare=main
```

## Property-Based Testing

```python
# tests/observability/test_properties.py
import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta
from src.observability.storage import MetricRecord

@given(
    metric_name=st.text(min_size=1, max_size=50),
    value=st.floats(allow_nan=False, allow_infinity=False),
    symbol=st.text(min_size=1, max_size=10)
)
@pytest.mark.asyncio
async def test_metric_roundtrip(metric_name, value, symbol, duckdb_client):
    """Property: Any metric can be inserted and queried back"""
    metric = MetricRecord(
        timestamp=datetime.utcnow(),
        metric_name=metric_name,
        value=value,
        symbol=symbol
    )

    await duckdb_client.insert_metric(metric)

    results = await duckdb_client.get_metrics(
        metric_name=metric_name,
        start_time=datetime.utcnow() - timedelta(hours=1)
    )

    assert len(results) > 0
    assert results[0]["metric_name"] == metric_name
```

## Troubleshooting Tests

### Common Issues

#### 1. Async Test Failures

```python
# Bad
def test_async_function():
    result = await some_async_function()  # SyntaxError

# Good
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()  # Works
```

#### 2. Database Lock Errors

```python
# Use isolated fixtures
@pytest.fixture
async def isolated_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = DuckDBClient(f"{tmpdir}/test.duckdb")
        await client.initialize()
        yield client
        await client.close()
```

#### 3. Slow Tests

```bash
# Run in parallel
pytest tests/observability/ -n auto

# Skip slow tests
pytest tests/observability/ -m "not slow"

# Profile tests
pytest tests/observability/ --durations=10
```

## Best Practices

### 1. Use Fixtures for Setup/Teardown

```python
@pytest.fixture
async def setup_test_data(duckdb_client):
    """Set up test data"""
    # Insert test data
    await duckdb_client.insert_metrics(test_metrics)

    yield duckdb_client

    # Cleanup (automatically handled by temp directory)
```

### 2. Test Edge Cases

```python
@pytest.mark.asyncio
async def test_empty_query(duckdb_client):
    """Test querying with no results"""
    results = await duckdb_client.get_metrics(
        metric_name="nonexistent",
        start_time=datetime.utcnow() - timedelta(hours=1)
    )
    assert results == []

@pytest.mark.asyncio
async def test_large_batch_insert(duckdb_client):
    """Test inserting 10,000 metrics"""
    metrics = [
        MetricRecord(
            timestamp=datetime.utcnow(),
            metric_name="large_test",
            value=float(i)
        )
        for i in range(10000)
    ]

    await duckdb_client.insert_metrics(metrics)

    count = await duckdb_client._execute_sync(
        lambda: duckdb_client._conn.execute(
            "SELECT COUNT(*) FROM trading_metrics WHERE metric_name = 'large_test'"
        ).fetchone()[0]
    )

    assert count == 10000
```

### 3. Benchmark Critical Paths

```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_critical_path_latency(benchmark):
    """Ensure critical path meets SLA"""
    # End-to-end latency test
    result = benchmark(lambda: asyncio.run(full_workflow()))

    assert result < 0.1, f"Critical path took {result*1000}ms (target: <100ms)"
```

## Summary

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints and WebSocket streaming
- **Performance Tests**: Benchmark insert/query latency and throughput
- **Load Tests**: Verify system handles concurrent load
- **CI/CD**: Automated testing on every commit

**Coverage Targets**: >90% overall, >95% for critical paths

**Performance Targets**:
- Insert: <1ms per 1000 records
- Query: <50ms for 1M records
- WebSocket: <10ms end-to-end latency

For detailed performance analysis, see `/docs/analysis/performance-analysis-report.md`.
