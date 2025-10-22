"""
Tests for SQLite Operational Storage
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from src.observability.storage.sqlite_client import SQLiteClient, sqlite_session


@pytest.fixture
async def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        client = SQLiteClient(str(db_path))
        await client.initialize()
        yield client
        await client.close()


@pytest.mark.asyncio
class TestSQLiteClient:
    """Test SQLite client functionality"""

    async def test_initialization(self, temp_db):
        """Test database initialization"""
        # Should not raise errors
        assert temp_db._conn is not None

    async def test_log_trade(self, temp_db):
        """Test trade logging"""
        trade_id = await temp_db.log_trade(
            timestamp=datetime.utcnow(),
            symbol="BTC/USD",
            side="buy",
            quantity=0.5,
            price=50000.0,
            order_id="test-order-123",
            status="executed",
            metadata={"strategy": "momentum"},
        )

        assert trade_id > 0

        # Query trade
        trades = await temp_db.get_trades(
            start_time=datetime.utcnow() - timedelta(hours=1),
        )
        assert len(trades) == 1
        assert trades[0]["symbol"] == "BTC/USD"
        assert trades[0]["quantity"] == 0.5
        assert trades[0]["metadata"]["strategy"] == "momentum"

    async def test_trade_stats(self, temp_db):
        """Test trade statistics"""
        now = datetime.utcnow()

        # Log multiple trades
        for i in range(10):
            await temp_db.log_trade(
                timestamp=now - timedelta(minutes=i),
                symbol="ETH/USD",
                side="buy" if i % 2 == 0 else "sell",
                quantity=1.0,
                price=3000.0,
                status="executed",
            )

        stats = await temp_db.get_trade_stats(
            start_time=now - timedelta(hours=1),
        )

        assert stats["total_trades"] == 10
        assert stats["buy_count"] == 5
        assert stats["sell_count"] == 5

    async def test_log_event(self, temp_db):
        """Test event logging"""
        event_id = await temp_db.log_event(
            event_type="order",
            severity="info",
            message="Order placed successfully",
            details={"order_id": "123", "symbol": "BTC/USD"},
        )

        assert event_id > 0

        # Query events
        events = await temp_db.get_events(
            start_time=datetime.utcnow() - timedelta(hours=1),
        )
        assert len(events) == 1
        assert events[0]["event_type"] == "order"
        assert events[0]["severity"] == "info"

    async def test_event_filtering(self, temp_db):
        """Test event filtering by type and severity"""
        now = datetime.utcnow()

        # Log various events
        await temp_db.log_event("order", "info", "Order placed", timestamp=now)
        await temp_db.log_event("order", "error", "Order failed", timestamp=now)
        await temp_db.log_event("system", "warning", "High latency", timestamp=now)

        # Filter by type
        order_events = await temp_db.get_events(
            start_time=now - timedelta(hours=1),
            event_type="order",
        )
        assert len(order_events) == 2

        # Filter by severity
        error_events = await temp_db.get_events(
            start_time=now - timedelta(hours=1),
            severity="error",
        )
        assert len(error_events) == 1
        assert error_events[0]["message"] == "Order failed"

    async def test_event_counts(self, temp_db):
        """Test event count aggregation"""
        now = datetime.utcnow()

        # Log multiple events
        for _ in range(5):
            await temp_db.log_event("order", "info", "Test", timestamp=now)
        for _ in range(3):
            await temp_db.log_event("order", "error", "Test", timestamp=now)
        for _ in range(2):
            await temp_db.log_event("system", "warning", "Test", timestamp=now)

        counts = await temp_db.get_event_counts(
            start_time=now - timedelta(hours=1),
        )

        assert counts["order"]["info"] == 5
        assert counts["order"]["error"] == 3
        assert counts["system"]["warning"] == 2

    async def test_context_manager(self):
        """Test async context manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            async with sqlite_session(str(db_path)) as client:
                trade_id = await client.log_trade(
                    timestamp=datetime.utcnow(),
                    symbol="BTC/USD",
                    side="buy",
                    quantity=1.0,
                    price=50000.0,
                )
                assert trade_id > 0

            # Verify data persisted
            async with sqlite_session(str(db_path)) as client:
                trades = await client.get_trades(
                    start_time=datetime.utcnow() - timedelta(hours=1),
                )
                assert len(trades) == 1

    async def test_database_size(self, temp_db):
        """Test database size tracking"""
        # Initial size
        size_before = await temp_db.get_db_size()

        # Insert data
        for i in range(100):
            await temp_db.log_trade(
                timestamp=datetime.utcnow(),
                symbol="BTC/USD",
                side="buy",
                quantity=1.0,
                price=50000.0,
            )

        # Size should increase
        size_after = await temp_db.get_db_size()
        assert size_after > size_before
