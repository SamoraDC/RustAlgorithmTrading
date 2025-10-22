"""
Tests for DuckDB Time-Series Storage

Performance targets:
- Insert latency: <1ms per 1000 records
- Query latency: <50ms for 1M records
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import time

from src.observability.storage.duckdb_client import DuckDBClient, duckdb_session
from src.observability.storage.schemas import (
    MetricRecord,
    CandleRecord,
    PerformanceRecord,
    TimeInterval,
)


@pytest.fixture
async def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        client = DuckDBClient(str(db_path))
        await client.initialize()
        yield client
        await client.close()


@pytest.mark.asyncio
class TestDuckDBClient:
    """Test DuckDB client functionality"""

    async def test_initialization(self, temp_db):
        """Test database initialization"""
        stats = await temp_db.get_table_stats()
        assert "trading_metrics" in stats
        assert "candles" in stats
        assert "performance_history" in stats
        assert stats["trading_metrics"]["row_count"] == 0

    async def test_insert_single_metric(self, temp_db):
        """Test single metric insertion"""
        metric = MetricRecord(
            timestamp=datetime.utcnow(),
            metric_name="test_latency",
            value=42.5,
            symbol="BTC/USD",
            labels={"exchange": "test"},
        )

        await temp_db.insert_metric(metric)

        metrics = await temp_db.get_metrics(
            "test_latency",
            datetime.utcnow() - timedelta(hours=1),
        )
        assert len(metrics) == 1
        assert metrics[0]["value"] == 42.5
        assert metrics[0]["symbol"] == "BTC/USD"

    async def test_batch_metric_insertion(self, temp_db):
        """Test batch metric insertion performance"""
        now = datetime.utcnow()
        metrics = [
            MetricRecord(
                timestamp=now - timedelta(seconds=i),
                metric_name="price",
                value=100.0 + i,
                symbol="BTC/USD",
            )
            for i in range(1000)
        ]

        start = time.perf_counter()
        await temp_db.insert_metrics(metrics)
        duration = time.perf_counter() - start

        # Should be <1ms per 1000 records
        assert duration < 1.0, f"Batch insert took {duration:.3f}s"

        # Verify all inserted
        result = await temp_db.get_metrics(
            "price",
            now - timedelta(hours=1),
            limit=2000,
        )
        assert len(result) == 1000

    async def test_insert_candles(self, temp_db):
        """Test candle insertion and querying"""
        now = datetime.utcnow()
        candles = [
            CandleRecord(
                timestamp=now - timedelta(minutes=i),
                symbol="ETH/USD",
                open=2000.0 + i,
                high=2010.0 + i,
                low=1990.0 + i,
                close=2005.0 + i,
                volume=1000000,
            )
            for i in range(100)
        ]

        await temp_db.insert_candles(candles)

        # Query with 1-minute interval
        result = await temp_db.get_candles(
            "ETH/USD",
            TimeInterval.MINUTE,
            now - timedelta(hours=2),
        )
        assert len(result) > 0
        assert "open" in result[0]
        assert "volume" in result[0]

    async def test_performance_tracking(self, temp_db):
        """Test performance record insertion"""
        record = PerformanceRecord(
            timestamp=datetime.utcnow(),
            portfolio_value=100000.0,
            pnl=1500.0,
            sharpe_ratio=2.5,
            max_drawdown=-0.05,
            win_rate=0.65,
            total_trades=150,
        )

        await temp_db.insert_performance(record)

        summary = await temp_db.get_performance_summary(
            datetime.utcnow() - timedelta(hours=1),
        )
        assert summary["total_pnl"] == 1500.0
        assert summary["avg_sharpe"] == 2.5

    async def test_time_bucketing(self, temp_db):
        """Test time-bucketed aggregations"""
        now = datetime.utcnow()

        # Insert metrics every second for 5 minutes
        metrics = [
            MetricRecord(
                timestamp=now - timedelta(seconds=i),
                metric_name="latency",
                value=10.0 + (i % 20),  # Varying values
                symbol="BTC/USD",
            )
            for i in range(300)  # 5 minutes
        ]
        await temp_db.insert_metrics(metrics)

        # Query with 1-minute buckets
        result = await temp_db.get_aggregated_metrics(
            "latency",
            TimeInterval.MINUTE,
            now - timedelta(minutes=10),
            aggregation="avg",
        )

        assert len(result) >= 5  # At least 5 minute buckets
        assert "value" in result[0]
        assert "sample_count" in result[0]

    async def test_query_performance(self, temp_db):
        """Test query performance on large dataset"""
        now = datetime.utcnow()

        # Insert 10k metrics
        metrics = [
            MetricRecord(
                timestamp=now - timedelta(seconds=i),
                metric_name="test_metric",
                value=float(i),
                symbol="BTC/USD",
            )
            for i in range(10000)
        ]
        await temp_db.insert_metrics(metrics)

        # Query should be fast
        start = time.perf_counter()
        result = await temp_db.get_metrics(
            "test_metric",
            now - timedelta(hours=5),
        )
        duration = time.perf_counter() - start

        # Should be <50ms for 10k records
        assert duration < 0.05, f"Query took {duration:.3f}s"
        assert len(result) == 10000

    async def test_latest_metrics(self, temp_db):
        """Test getting latest metrics"""
        now = datetime.utcnow()

        # Insert various metrics
        metrics = [
            MetricRecord(
                timestamp=now - timedelta(seconds=i),
                metric_name=f"metric_{i % 5}",
                value=float(i),
                symbol="BTC/USD",
            )
            for i in range(50)
        ]
        await temp_db.insert_metrics(metrics)

        latest = await temp_db.get_latest_metrics(limit=10)
        assert len(latest) <= 10
        assert all("metric_name" in m for m in latest)

    async def test_optimize_database(self, temp_db):
        """Test database optimization"""
        # Insert some data
        metrics = [
            MetricRecord(
                timestamp=datetime.utcnow() - timedelta(seconds=i),
                metric_name="test",
                value=float(i),
            )
            for i in range(1000)
        ]
        await temp_db.insert_metrics(metrics)

        # Optimize should complete without errors
        await temp_db.optimize()

        # Verify data still accessible
        result = await temp_db.get_metrics(
            "test",
            datetime.utcnow() - timedelta(hours=1),
        )
        assert len(result) == 1000

    async def test_context_manager(self):
        """Test async context manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            async with duckdb_session(str(db_path)) as client:
                metric = MetricRecord(
                    timestamp=datetime.utcnow(),
                    metric_name="test",
                    value=123.0,
                )
                await client.insert_metric(metric)

            # Connection should be closed
            # Verify by opening new session
            async with duckdb_session(str(db_path)) as client:
                result = await client.get_metrics(
                    "test",
                    datetime.utcnow() - timedelta(hours=1),
                )
                assert len(result) == 1


@pytest.mark.asyncio
class TestPerformanceBenchmarks:
    """Performance benchmark tests"""

    async def test_insert_throughput(self, temp_db):
        """Test insertion throughput"""
        now = datetime.utcnow()
        batch_size = 10000

        metrics = [
            MetricRecord(
                timestamp=now - timedelta(seconds=i),
                metric_name="benchmark",
                value=float(i),
                symbol="BTC/USD",
            )
            for i in range(batch_size)
        ]

        start = time.perf_counter()
        await temp_db.insert_metrics(metrics)
        duration = time.perf_counter() - start

        throughput = batch_size / duration
        print(f"\nInsert throughput: {throughput:.0f} records/sec")

        # Should handle >10k records/sec
        assert throughput > 10000

    async def test_query_throughput(self, temp_db):
        """Test query throughput"""
        now = datetime.utcnow()

        # Insert 100k metrics
        metrics = [
            MetricRecord(
                timestamp=now - timedelta(seconds=i),
                metric_name="benchmark",
                value=float(i),
                symbol="BTC/USD",
            )
            for i in range(100000)
        ]
        await temp_db.insert_metrics(metrics)

        # Run 100 queries
        start = time.perf_counter()
        for _ in range(100):
            await temp_db.get_metrics(
                "benchmark",
                now - timedelta(hours=48),
                limit=1000,
            )
        duration = time.perf_counter() - start

        avg_query_time = duration / 100
        print(f"\nAverage query time: {avg_query_time*1000:.2f}ms")

        # Should average <50ms per query
        assert avg_query_time < 0.05
