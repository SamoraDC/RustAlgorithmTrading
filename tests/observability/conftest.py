"""
Pytest configuration and shared fixtures for observability tests.
"""
import asyncio
import json
import logging
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import websockets
from fastapi.testclient import TestClient


# ============================================================================
# FIXTURES: Test Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Create temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture
def temp_metrics_dir(tmp_path: Path) -> Path:
    """Create temporary directory for metrics files."""
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return metrics_dir


@pytest.fixture
def log_config(temp_log_dir: Path) -> Dict[str, Any]:
    """Generate test logging configuration."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
            }
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(temp_log_dir / "test.log"),
                "formatter": "json",
            }
        },
        "root": {"level": "INFO", "handlers": ["file"]},
    }


# ============================================================================
# FIXTURES: Mock Services
# ============================================================================

@pytest.fixture
def mock_websocket_server():
    """Mock WebSocket server for testing."""

    class MockWebSocketServer:
        def __init__(self):
            self.clients: List[Any] = []
            self.messages: List[Dict] = []
            self.is_running = False

        async def handler(self, websocket, path):
            """Handle WebSocket connections."""
            self.clients.append(websocket)
            try:
                async for message in websocket:
                    data = json.loads(message)
                    self.messages.append(data)
                    # Echo back confirmation
                    await websocket.send(json.dumps({"status": "received", "data": data}))
            finally:
                self.clients.remove(websocket)

        async def start(self, host="localhost", port=8765):
            """Start WebSocket server."""
            self.server = await websockets.serve(self.handler, host, port)
            self.is_running = True

        async def stop(self):
            """Stop WebSocket server."""
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            self.is_running = False

        async def broadcast(self, message: Dict):
            """Broadcast message to all clients."""
            msg_json = json.dumps(message)
            for client in self.clients:
                await client.send(msg_json)

    return MockWebSocketServer()


@pytest.fixture
def mock_logger():
    """Mock structured logger for testing."""
    logger = MagicMock(spec=logging.Logger)
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector for testing."""

    class MockMetricsCollector:
        def __init__(self):
            self.metrics: Dict[str, List[float]] = {}
            self.labels: Dict[str, Dict[str, str]] = {}

        def record(self, metric_name: str, value: float, labels: Dict[str, str] = None):
            """Record a metric value."""
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            self.metrics[metric_name].append(value)

            if labels:
                if metric_name not in self.labels:
                    self.labels[metric_name] = {}
                self.labels[metric_name].update(labels)

        def get_metric(self, metric_name: str) -> List[float]:
            """Get all recorded values for a metric."""
            return self.metrics.get(metric_name, [])

        def get_latest(self, metric_name: str) -> float:
            """Get the latest value for a metric."""
            values = self.get_metric(metric_name)
            return values[-1] if values else 0.0

        def clear(self):
            """Clear all metrics."""
            self.metrics.clear()
            self.labels.clear()

    return MockMetricsCollector()


# ============================================================================
# FIXTURES: Sample Data
# ============================================================================

@pytest.fixture
def sample_log_entries() -> List[Dict[str, Any]]:
    """Generate sample log entries for testing."""
    base_time = datetime.now()
    return [
        {
            "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
            "level": level,
            "message": f"Test log message {i}",
            "correlation_id": f"corr-{i // 10}",
            "service": "trading-engine",
            "component": "order-executor",
            "metadata": {"order_id": f"ORD-{i}", "symbol": "AAPL"},
        }
        for i, level in enumerate(
            ["INFO", "DEBUG", "WARNING", "ERROR", "INFO"] * 20
        )
    ]


@pytest.fixture
def sample_metrics_data() -> List[Dict[str, Any]]:
    """Generate sample metrics data for testing."""
    base_time = datetime.now()
    return [
        {
            "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
            "metric_name": metric,
            "value": value,
            "labels": {"service": "trading-engine", "environment": "test"},
        }
        for i, (metric, value) in enumerate([
            ("order_latency_ms", 5.2),
            ("order_latency_ms", 4.8),
            ("order_latency_ms", 6.1),
            ("orders_executed_total", 1),
            ("orders_executed_total", 1),
            ("market_data_updates_total", 10),
            ("market_data_updates_total", 12),
            ("websocket_connections_active", 5),
            ("websocket_connections_active", 6),
            ("memory_usage_bytes", 104857600),
        ])
    ]


@pytest.fixture
def sample_trade_execution() -> Dict[str, Any]:
    """Generate sample trade execution event."""
    return {
        "event_type": "trade_executed",
        "timestamp": datetime.now().isoformat(),
        "correlation_id": "corr-12345",
        "order_id": "ORD-67890",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "price": 150.25,
        "execution_time_ms": 4.5,
        "exchange": "NASDAQ",
        "strategy": "momentum",
    }


@pytest.fixture
def sample_websocket_message() -> Dict[str, Any]:
    """Generate sample WebSocket message."""
    return {
        "type": "metric_update",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "metric_name": "order_latency_p99",
            "value": 8.2,
            "labels": {"service": "order-router", "priority": "high"},
        },
    }


# ============================================================================
# FIXTURES: Performance Testing
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""

    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            """Start timing."""
            self.start_time = time.perf_counter()

        def stop(self):
            """Stop timing and return elapsed time in seconds."""
            self.end_time = time.perf_counter()
            return self.elapsed

        @property
        def elapsed(self) -> float:
            """Get elapsed time in seconds."""
            if self.start_time is None:
                return 0.0
            end = self.end_time if self.end_time else time.perf_counter()
            return end - self.start_time

        @property
        def elapsed_ms(self) -> float:
            """Get elapsed time in milliseconds."""
            return self.elapsed * 1000

    return PerformanceTimer()


@pytest.fixture
def memory_profiler():
    """Memory profiler fixture for testing."""
    import tracemalloc

    class MemoryProfiler:
        def __init__(self):
            self.snapshot_before = None
            self.snapshot_after = None

        def start(self):
            """Start memory profiling."""
            tracemalloc.start()
            self.snapshot_before = tracemalloc.take_snapshot()

        def stop(self):
            """Stop memory profiling and return memory delta in bytes."""
            self.snapshot_after = tracemalloc.take_snapshot()
            tracemalloc.stop()
            return self.memory_delta

        @property
        def memory_delta(self) -> int:
            """Get memory delta in bytes."""
            if not self.snapshot_before or not self.snapshot_after:
                return 0

            stats = self.snapshot_after.compare_to(self.snapshot_before, 'lineno')
            total = sum(stat.size_diff for stat in stats)
            return total

        @property
        def memory_delta_mb(self) -> float:
            """Get memory delta in megabytes."""
            return self.memory_delta / (1024 * 1024)

    return MemoryProfiler()


# ============================================================================
# FIXTURES: Correlation Testing
# ============================================================================

@pytest.fixture
def correlation_context():
    """Correlation context for distributed tracing."""

    class CorrelationContext:
        def __init__(self):
            self.correlation_id = None
            self.trace_id = None
            self.span_id = None

        def new_correlation(self) -> str:
            """Generate new correlation ID."""
            import uuid
            self.correlation_id = f"corr-{uuid.uuid4().hex[:12]}"
            self.trace_id = f"trace-{uuid.uuid4().hex}"
            self.span_id = f"span-{uuid.uuid4().hex[:8]}"
            return self.correlation_id

        def to_dict(self) -> Dict[str, str]:
            """Convert to dictionary for headers."""
            return {
                "X-Correlation-ID": self.correlation_id or "",
                "X-Trace-ID": self.trace_id or "",
                "X-Span-ID": self.span_id or "",
            }

    return CorrelationContext()


# ============================================================================
# MARKERS AND CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers for observability tests."""
    config.addinivalue_line(
        "markers", "logging: Tests for logging infrastructure"
    )
    config.addinivalue_line(
        "markers", "metrics: Tests for metrics collection"
    )
    config.addinivalue_line(
        "markers", "websocket: Tests for WebSocket functionality"
    )
    config.addinivalue_line(
        "markers", "api: Tests for backend API"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for observability"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "correlation: Tests for correlation ID propagation"
    )


# ============================================================================
# CLEANUP HOOKS
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_logs(temp_log_dir: Path):
    """Auto-cleanup log files after each test."""
    yield
    # Cleanup happens automatically with tmp_path
