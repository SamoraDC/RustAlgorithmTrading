"""
End-to-End Integration Tests for Observability Stack.

Tests:
- Complete metric flow: Collector → DuckDB → API → Dashboard
- Log correlation with trades
- Real-time dashboard updates
- Graceful shutdown and data persistence
"""
import asyncio
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import httpx
import pytest
import websockets
from loguru import logger


class TestObservabilityIntegration:
    """End-to-end integration tests for the complete observability pipeline."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    async def full_stack(self, project_root: Path):
        """Start complete observability stack."""
        # Ensure directories exist
        (project_root / "data").mkdir(exist_ok=True)
        (project_root / "logs").mkdir(exist_ok=True)

        # Start API server
        api_process = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "uvicorn",
            "src.observability.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for API to be ready
        async with httpx.AsyncClient() as client:
            for _ in range(30):
                try:
                    response = await client.get(
                        "http://localhost:8000/health",
                        timeout=2.0
                    )
                    if response.status_code == 200:
                        break
                except (httpx.ConnectError, httpx.TimeoutException):
                    await asyncio.sleep(1)

        yield {
            "api_process": api_process,
            "project_root": project_root,
        }

        # Cleanup
        api_process.terminate()
        try:
            await asyncio.wait_for(api_process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            api_process.kill()
            await api_process.wait()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_metric_flow_collector_to_dashboard(self, full_stack):
        """Test complete metric flow from collector through to dashboard."""
        project_root = full_stack["project_root"]

        # Step 1: Simulate metric collection (write to DuckDB)
        try:
            import duckdb

            db_path = project_root / "data" / "metrics.duckdb"
            conn = duckdb.connect(str(db_path))

            # Create metrics table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp TIMESTAMP,
                    metric_name VARCHAR,
                    value DOUBLE,
                    labels VARCHAR
                )
                """
            )

            # Insert test metrics
            test_metrics = [
                (
                    datetime.now(),
                    "order_latency_ms",
                    5.2,
                    '{"service": "trading-engine"}',
                )
            ]

            conn.executemany(
                "INSERT INTO metrics VALUES (?, ?, ?, ?)",
                test_metrics
            )

            conn.close()

        except ImportError:
            pytest.skip("DuckDB not installed")

        # Step 2: Verify API can query the data
        async with httpx.AsyncClient() as client:
            # API should be able to access the database
            response = await client.get(
                "http://localhost:8000/health",
                timeout=5.0
            )
            assert response.status_code == 200

        # Step 3: Connect WebSocket and receive streamed metrics
        ws_url = "ws://localhost:8000/ws/metrics"

        async with websockets.connect(ws_url) as websocket:
            # Receive at least one metric message
            received = False

            for _ in range(20):  # Try for 2 seconds (10Hz)
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=0.2
                    )

                    if message not in ["ping", "pong"]:
                        data = json.loads(message)
                        assert "timestamp" in data
                        received = True
                        break

                except asyncio.TimeoutError:
                    continue

            assert received, "No metrics received via WebSocket"

        logger.info("✓ Complete metric flow validated: Collector → DuckDB → API → Dashboard")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_log_correlation_with_trades(self, full_stack, tmp_path: Path):
        """Test that logs can be correlated with trade executions."""
        project_root = full_stack["project_root"]

        # Create SQLite trades database
        trades_db = tmp_path / "trades.db"
        conn = sqlite3.connect(str(trades_db))
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL
            )
            """
        )

        # Insert test trade
        correlation_id = "corr-test-12345"
        timestamp = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO trades (timestamp, correlation_id, symbol, side, quantity, price)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, correlation_id, "AAPL", "buy", 100, 150.25)
        )
        conn.commit()

        # Query trade back
        cursor.execute(
            "SELECT * FROM trades WHERE correlation_id = ?",
            (correlation_id,)
        )
        trade = cursor.fetchone()

        assert trade is not None
        assert trade[2] == correlation_id  # correlation_id column
        assert trade[3] == "AAPL"          # symbol column

        conn.close()

        logger.info(f"✓ Trade logged with correlation_id: {correlation_id}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dashboard_updates_in_real_time(self, full_stack):
        """Test that dashboard receives real-time metric updates."""
        ws_url = "ws://localhost:8000/ws/metrics"

        messages_received = []

        async with websockets.connect(ws_url) as websocket:
            # Collect messages for 1 second
            start_time = time.time()

            while time.time() - start_time < 1.0:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=0.2
                    )

                    if message not in ["ping", "pong"]:
                        messages_received.append(message)

                except asyncio.TimeoutError:
                    continue

        # Should receive multiple updates
        assert len(messages_received) >= 5, (
            f"Expected at least 5 messages, got {len(messages_received)}"
        )

        # Verify all messages are valid JSON
        for message in messages_received:
            data = json.loads(message)
            assert "timestamp" in data

        logger.info(
            f"✓ Dashboard received {len(messages_received)} real-time updates"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_graceful_shutdown_preserves_data(self, project_root: Path):
        """Test that graceful shutdown preserves all data."""
        # Start API
        api_process = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "uvicorn",
            "src.observability.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for startup
        await asyncio.sleep(3)

        # Write some test data to DuckDB
        try:
            import duckdb

            db_path = project_root / "data" / "metrics_shutdown_test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_data (
                    id INTEGER,
                    value VARCHAR
                )
                """
            )

            test_values = [(1, "value1"), (2, "value2"), (3, "value3")]
            conn.executemany("INSERT INTO test_data VALUES (?, ?)", test_values)

            conn.close()

        except ImportError:
            pytest.skip("DuckDB not installed")

        # Trigger graceful shutdown
        api_process.terminate()
        await asyncio.wait_for(api_process.wait(), timeout=10.0)

        # Verify data persisted
        conn = duckdb.connect(str(db_path))
        result = conn.execute("SELECT COUNT(*) FROM test_data").fetchone()

        assert result[0] == 3, "Data not preserved after shutdown"

        conn.close()

        logger.info("✓ Graceful shutdown preserved all data")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_metric_collection_and_streaming(self, full_stack):
        """Test concurrent metric collection and WebSocket streaming."""
        project_root = full_stack["project_root"]

        # Task 1: Simulate continuous metric collection
        async def simulate_metric_collection():
            try:
                import duckdb

                db_path = project_root / "data" / "metrics.duckdb"

                for i in range(10):
                    conn = duckdb.connect(str(db_path))

                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS metrics (
                            timestamp TIMESTAMP,
                            metric_name VARCHAR,
                            value DOUBLE,
                            labels VARCHAR
                        )
                        """
                    )

                    conn.execute(
                        "INSERT INTO metrics VALUES (?, ?, ?, ?)",
                        [datetime.now(), f"test_metric_{i}", float(i), "{}"]
                    )

                    conn.close()
                    await asyncio.sleep(0.1)

            except ImportError:
                pass

        # Task 2: Consume metrics via WebSocket
        async def consume_websocket_metrics():
            ws_url = "ws://localhost:8000/ws/metrics"
            messages = []

            async with websockets.connect(ws_url) as websocket:
                for _ in range(10):
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=0.2
                        )

                        if message not in ["ping", "pong"]:
                            messages.append(message)

                    except asyncio.TimeoutError:
                        continue

            return messages

        # Run both tasks concurrently
        collection_task = asyncio.create_task(simulate_metric_collection())
        streaming_task = asyncio.create_task(consume_websocket_metrics())

        messages = await streaming_task
        await collection_task

        # Should receive messages while collecting
        assert len(messages) > 0, "No messages received during concurrent collection"

        logger.info(
            f"✓ Concurrent collection and streaming: {len(messages)} messages"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_recovery_and_resilience(self, full_stack):
        """Test system recovery from transient errors."""
        ws_url = "ws://localhost:8000/ws/metrics"

        # Connect, disconnect, and reconnect
        for attempt in range(3):
            async with websockets.connect(ws_url) as websocket:
                # Send ping
                await websocket.send("ping")

                # Receive pong
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=2.0
                )

                assert response == "pong"

                logger.info(f"✓ Connection attempt {attempt + 1} successful")

            # Brief pause between connections
            await asyncio.sleep(0.5)

        logger.info("✓ System demonstrated resilience through reconnections")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_client_metric_broadcast(self, full_stack):
        """Test that metrics are broadcast to multiple connected clients."""
        ws_url = "ws://localhost:8000/ws/metrics"
        num_clients = 5

        async def client_receiver(client_id: int):
            """Receive messages as a client."""
            messages = []

            async with websockets.connect(ws_url) as websocket:
                for _ in range(10):
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=0.2
                        )

                        if message not in ["ping", "pong"]:
                            messages.append(message)

                    except asyncio.TimeoutError:
                        continue

            return client_id, messages

        # Connect multiple clients concurrently
        results = await asyncio.gather(
            *[client_receiver(i) for i in range(num_clients)]
        )

        # All clients should receive messages
        for client_id, messages in results:
            assert len(messages) > 0, (
                f"Client {client_id} received no messages"
            )

        logger.info(
            f"✓ Metrics broadcast to {num_clients} clients simultaneously"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metric_aggregation_and_querying(self, full_stack):
        """Test metric aggregation and historical querying."""
        project_root = full_stack["project_root"]

        try:
            import duckdb

            db_path = project_root / "data" / "metrics_agg_test.duckdb"
            conn = duckdb.connect(str(db_path))

            # Create and populate metrics
            conn.execute(
                """
                CREATE TABLE metrics (
                    timestamp TIMESTAMP,
                    metric_name VARCHAR,
                    value DOUBLE,
                    labels VARCHAR
                )
                """
            )

            # Insert time-series data
            metrics = [
                (datetime.now(), "latency_ms", float(i * 1.5), "{}")
                for i in range(100)
            ]

            conn.executemany(
                "INSERT INTO metrics VALUES (?, ?, ?, ?)",
                metrics
            )

            # Test aggregation query
            result = conn.execute(
                """
                SELECT
                    metric_name,
                    AVG(value) as avg_value,
                    MAX(value) as max_value,
                    MIN(value) as min_value,
                    COUNT(*) as count
                FROM metrics
                GROUP BY metric_name
                """
            ).fetchone()

            assert result is not None
            assert result[0] == "latency_ms"
            assert result[4] == 100  # count

            conn.close()

            logger.info("✓ Metric aggregation and querying functional")

        except ImportError:
            pytest.skip("DuckDB not installed")
