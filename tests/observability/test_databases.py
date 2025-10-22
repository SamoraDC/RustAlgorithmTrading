"""
Database Performance and Persistence Tests.

Tests:
- DuckDB write performance (>1000 inserts/sec)
- DuckDB query performance (<50ms)
- SQLite trade recording
- Data persistence after restart
"""
import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import pytest
from loguru import logger


class TestDatabasePerformance:
    """Test database performance benchmarks."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def duckdb_path(self, project_root: Path, tmp_path: Path) -> Path:
        """Create temporary DuckDB database."""
        db_path = tmp_path / "test_metrics.duckdb"
        return db_path

    @pytest.fixture
    def sqlite_path(self, project_root: Path, tmp_path: Path) -> Path:
        """Create temporary SQLite database."""
        db_path = tmp_path / "test_trades.db"
        return db_path

    @pytest.mark.performance
    def test_duckdb_write_performance_exceeds_1000_per_sec(
        self, duckdb_path: Path
    ):
        """Test DuckDB can handle >1000 inserts/second."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("DuckDB not installed")

        conn = duckdb.connect(str(duckdb_path))

        # Create test table
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

        # Generate test data
        num_records = 10000
        test_data = [
            (
                datetime.now() + timedelta(seconds=i),
                f"metric_{i % 10}",
                float(i),
                f'{{"service": "test", "id": {i}}}',
            )
            for i in range(num_records)
        ]

        # Benchmark batch insert
        start_time = time.perf_counter()

        conn.executemany(
            "INSERT INTO metrics VALUES (?, ?, ?, ?)",
            test_data
        )

        elapsed = time.perf_counter() - start_time
        inserts_per_sec = num_records / elapsed

        logger.info(
            f"DuckDB: {num_records} inserts in {elapsed:.3f}s "
            f"({inserts_per_sec:.0f} inserts/sec)"
        )

        assert inserts_per_sec > 1000, (
            f"Insert rate {inserts_per_sec:.0f}/s is below 1000/s target"
        )

        # Verify data
        result = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()
        assert result[0] == num_records

        conn.close()

    @pytest.mark.performance
    def test_duckdb_query_performance_under_50ms(self, duckdb_path: Path):
        """Test DuckDB queries complete in <50ms."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("DuckDB not installed")

        conn = duckdb.connect(str(duckdb_path))

        # Create and populate test table
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

        # Insert test data
        test_data = [
            (
                datetime.now() + timedelta(seconds=i),
                f"metric_{i % 10}",
                float(i),
                f'{{"service": "test"}}',
            )
            for i in range(100000)
        ]

        conn.executemany("INSERT INTO metrics VALUES (?, ?, ?, ?)", test_data)

        # Create index for faster queries
        conn.execute("CREATE INDEX idx_timestamp ON metrics(timestamp)")
        conn.execute("CREATE INDEX idx_metric_name ON metrics(metric_name)")

        # Test various query patterns
        queries = [
            "SELECT COUNT(*) FROM metrics",
            "SELECT metric_name, AVG(value) FROM metrics GROUP BY metric_name",
            "SELECT * FROM metrics WHERE metric_name = 'metric_5' LIMIT 100",
            """
            SELECT metric_name, AVG(value) as avg_value
            FROM metrics
            WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL 1 HOUR
            GROUP BY metric_name
            """,
        ]

        for query in queries:
            start_time = time.perf_counter()
            result = conn.execute(query).fetchall()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(f"Query took {elapsed_ms:.2f}ms: {query[:50]}...")

            assert elapsed_ms < 50, (
                f"Query took {elapsed_ms:.2f}ms (>50ms): {query[:50]}"
            )
            assert len(result) > 0

        conn.close()

    @pytest.mark.performance
    def test_sqlite_trade_recording(self, sqlite_path: Path):
        """Test SQLite trade recording with realistic trade volume."""
        conn = sqlite3.connect(str(sqlite_path))
        cursor = conn.cursor()

        # Create trades table
        cursor.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                execution_time_ms REAL,
                strategy TEXT
            )
            """
        )
        conn.commit()

        # Generate realistic trade data
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        sides = ["buy", "sell"]
        strategies = ["momentum", "mean_reversion", "arbitrage"]

        trades = [
            (
                (datetime.now() + timedelta(minutes=i)).isoformat(),
                symbols[i % len(symbols)],
                sides[i % len(sides)],
                float((i % 10 + 1) * 10),  # quantity
                150.0 + (i % 100) * 0.5,   # price
                3.5 + (i % 5) * 0.2,       # execution_time_ms
                strategies[i % len(strategies)],
            )
            for i in range(1000)
        ]

        # Benchmark insert
        start_time = time.perf_counter()

        cursor.executemany(
            """
            INSERT INTO trades
            (timestamp, symbol, side, quantity, price, execution_time_ms, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            trades,
        )
        conn.commit()

        elapsed = time.perf_counter() - start_time
        logger.info(f"Inserted 1000 trades in {elapsed:.3f}s")

        # Verify trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]
        assert count == 1000

        # Test queries
        cursor.execute("SELECT * FROM trades WHERE symbol = 'AAPL'")
        aapl_trades = cursor.fetchall()
        assert len(aapl_trades) > 0

        cursor.execute("SELECT SUM(quantity) FROM trades WHERE side = 'buy'")
        buy_volume = cursor.fetchone()[0]
        assert buy_volume > 0

        conn.close()

    @pytest.mark.integration
    def test_duckdb_data_persistence(self, duckdb_path: Path):
        """Test that DuckDB data persists after connection close."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("DuckDB not installed")

        # First connection: create and populate
        conn1 = duckdb.connect(str(duckdb_path))
        conn1.execute(
            """
            CREATE TABLE persistent_data (
                id INTEGER,
                value VARCHAR
            )
            """
        )
        conn1.execute("INSERT INTO persistent_data VALUES (1, 'test_value')")
        conn1.close()

        # Second connection: verify data exists
        conn2 = duckdb.connect(str(duckdb_path))
        result = conn2.execute(
            "SELECT * FROM persistent_data WHERE id = 1"
        ).fetchone()

        assert result is not None
        assert result[0] == 1
        assert result[1] == "test_value"

        conn2.close()

    @pytest.mark.integration
    def test_sqlite_data_persistence(self, sqlite_path: Path):
        """Test that SQLite data persists after connection close."""
        # First connection: create and populate
        conn1 = sqlite3.connect(str(sqlite_path))
        cursor1 = conn1.cursor()

        cursor1.execute(
            """
            CREATE TABLE persistent_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT
            )
            """
        )
        cursor1.execute("INSERT INTO persistent_trades VALUES (1, 'AAPL')")
        conn1.commit()
        conn1.close()

        # Second connection: verify data exists
        conn2 = sqlite3.connect(str(sqlite_path))
        cursor2 = conn2.cursor()

        cursor2.execute("SELECT * FROM persistent_trades WHERE id = 1")
        result = cursor2.fetchone()

        assert result is not None
        assert result[0] == 1
        assert result[1] == "AAPL"

        conn2.close()

    @pytest.mark.performance
    def test_concurrent_database_access(self, duckdb_path: Path):
        """Test concurrent read/write operations."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("DuckDB not installed")

        # Setup database
        conn = duckdb.connect(str(duckdb_path))
        conn.execute(
            """
            CREATE TABLE concurrent_test (
                id INTEGER,
                thread_id INTEGER,
                value DOUBLE
            )
            """
        )
        conn.close()

        # Concurrent writes (DuckDB handles file locking)
        def write_worker(thread_id: int, num_writes: int):
            conn = duckdb.connect(str(duckdb_path))
            for i in range(num_writes):
                conn.execute(
                    "INSERT INTO concurrent_test VALUES (?, ?, ?)",
                    [i, thread_id, float(i * thread_id)]
                )
            conn.close()

        import threading

        threads = []
        num_threads = 5
        writes_per_thread = 100

        start_time = time.perf_counter()

        for i in range(num_threads):
            t = threading.Thread(target=write_worker, args=(i, writes_per_thread))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.perf_counter() - start_time
        total_writes = num_threads * writes_per_thread

        logger.info(
            f"Concurrent writes: {total_writes} records in {elapsed:.3f}s"
        )

        # Verify all writes succeeded
        conn = duckdb.connect(str(duckdb_path))
        result = conn.execute("SELECT COUNT(*) FROM concurrent_test").fetchone()
        assert result[0] == total_writes

        conn.close()

    @pytest.mark.performance
    def test_bulk_data_aggregation(self, duckdb_path: Path):
        """Test aggregation queries on large datasets."""
        try:
            import duckdb
        except ImportError:
            pytest.skip("DuckDB not installed")

        conn = duckdb.connect(str(duckdb_path))

        # Create large dataset
        conn.execute(
            """
            CREATE TABLE large_metrics AS
            SELECT
                CURRENT_TIMESTAMP + INTERVAL (i) SECOND as timestamp,
                'metric_' || (i % 100)::VARCHAR as metric_name,
                random() * 100 as value
            FROM range(1000000) t(i)
            """
        )

        # Complex aggregation query
        start_time = time.perf_counter()

        result = conn.execute(
            """
            SELECT
                metric_name,
                COUNT(*) as count,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                STDDEV(value) as stddev_value
            FROM large_metrics
            GROUP BY metric_name
            ORDER BY avg_value DESC
            LIMIT 10
            """
        ).fetchall()

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Aggregation on 1M rows took {elapsed_ms:.2f}ms"
        )

        assert elapsed_ms < 500, f"Aggregation took {elapsed_ms:.2f}ms (>500ms)"
        assert len(result) == 10

        conn.close()
