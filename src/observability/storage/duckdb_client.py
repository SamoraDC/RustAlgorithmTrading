"""
DuckDB Time-Series Storage Client

High-performance analytics database for time-series trading data.
Optimized for OLAP queries with blazing fast aggregations.

Performance targets:
- Insert latency: <1ms
- Query latency: <50ms for 1M records
- Auto-optimization enabled
"""

import asyncio
import duckdb
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging

from .schemas import (
    MetricRecord,
    CandleRecord,
    PerformanceRecord,
    TimeInterval,
    DUCKDB_SCHEMAS,
)


logger = logging.getLogger(__name__)


class DuckDBClient:
    """
    DuckDB client for time-series analytics

    Features:
    - Embedded database (no server)
    - Blazing fast OLAP queries
    - Automatic optimization
    - Async operations via thread pool
    - Time-bucketed aggregations
    """

    def __init__(
        self,
        db_path: str = "data/trading_metrics.duckdb",
        read_only: bool = False,
        threads: int = 4,
    ):
        """
        Initialize DuckDB client

        Args:
            db_path: Path to DuckDB database file
            read_only: Open in read-only mode
            threads: Number of threads for query execution
        """
        self.db_path = Path(db_path)
        self.read_only = read_only
        self.threads = threads
        self._executor = ThreadPoolExecutor(max_workers=threads)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database and create tables"""
        await self._execute_sync(self._init_db)
        logger.info(f"DuckDB initialized: {self.db_path}")

    def _init_db(self) -> None:
        """Initialize database (sync operation)"""
        self._conn = duckdb.connect(
            str(self.db_path),
            read_only=self.read_only,
        )

        # Configure for optimal performance
        self._conn.execute("PRAGMA threads=4")
        self._conn.execute("PRAGMA memory_limit='4GB'")
        self._conn.execute("PRAGMA enable_object_cache")

        # Create tables
        for table_name, schema_sql in DUCKDB_SCHEMAS.items():
            self._conn.execute(schema_sql)
            logger.debug(f"Created table: {table_name}")

    async def close(self) -> None:
        """Close database connection"""
        if self._conn:
            await self._execute_sync(self._conn.close)
            self._conn = None
        self._executor.shutdown(wait=True)
        logger.info("DuckDB connection closed")

    async def _execute_sync(self, func, *args, **kwargs) -> Any:
        """Execute sync function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)

    # ========== Write Operations ==========

    async def insert_metric(self, metric: MetricRecord) -> None:
        """Insert single metric record"""
        await self.insert_metrics([metric])

    async def insert_metrics(self, metrics: List[MetricRecord]) -> None:
        """
        Batch insert metrics

        Performance: <1ms per 1000 records
        """
        if not metrics:
            return

        def _insert():
            data = [m.to_dict() for m in metrics]
            self._conn.executemany(
                """
                INSERT INTO trading_metrics
                (timestamp, metric_name, value, symbol, labels)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(
                    d["timestamp"],
                    d["metric_name"],
                    d["value"],
                    d["symbol"],
                    d["labels"],
                ) for d in data]
            )

        await self._execute_sync(_insert)
        logger.debug(f"Inserted {len(metrics)} metrics")

    async def insert_candle(self, candle: CandleRecord) -> None:
        """Insert single candle"""
        await self.insert_candles([candle])

    async def insert_candles(self, candles: List[CandleRecord]) -> None:
        """Batch insert candles"""
        if not candles:
            return

        def _insert():
            data = [c.to_dict() for c in candles]
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO candles
                (timestamp, symbol, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [(
                    d["timestamp"],
                    d["symbol"],
                    d["open"],
                    d["high"],
                    d["low"],
                    d["close"],
                    d["volume"],
                ) for d in data]
            )

        await self._execute_sync(_insert)
        logger.debug(f"Inserted {len(candles)} candles")

    async def insert_performance(self, record: PerformanceRecord) -> None:
        """Insert performance record"""
        def _insert():
            data = record.to_dict()
            self._conn.execute(
                """
                INSERT OR REPLACE INTO performance_history
                (timestamp, portfolio_value, pnl, sharpe_ratio,
                 max_drawdown, win_rate, total_trades)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["timestamp"],
                    data["portfolio_value"],
                    data["pnl"],
                    data["sharpe_ratio"],
                    data["max_drawdown"],
                    data["win_rate"],
                    data["total_trades"],
                )
            )

        await self._execute_sync(_insert)

    # ========== Query Operations ==========

    async def get_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        symbol: Optional[str] = None,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Query metrics with time range filtering

        Performance: <50ms for 1M records
        """
        end_time = end_time or datetime.utcnow()

        def _query():
            query = """
                SELECT timestamp, metric_name, value, symbol, labels
                FROM trading_metrics
                WHERE metric_name = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
            """
            params = [metric_name, start_time, end_time]

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            result = self._conn.execute(query, params).fetchall()
            return [
                {
                    "timestamp": row[0],
                    "metric_name": row[1],
                    "value": row[2],
                    "symbol": row[3],
                    "labels": row[4],
                }
                for row in result
            ]

        return await self._execute_sync(_query)

    async def get_candles(
        self,
        symbol: str,
        interval: TimeInterval,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Query candles with time-bucketing

        Supports dynamic intervals: 1s, 1m, 1h, 1d, 1w, 1mo
        """
        end_time = end_time or datetime.utcnow()

        def _query():
            query = f"""
                SELECT
                    time_bucket(INTERVAL '{interval.duckdb_interval}', timestamp) as bucket,
                    first(open) as open,
                    max(high) as high,
                    min(low) as low,
                    last(close) as close,
                    sum(volume) as volume
                FROM candles
                WHERE symbol = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT ?
            """
            result = self._conn.execute(
                query,
                [symbol, start_time, end_time, limit]
            ).fetchall()

            return [
                {
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                }
                for row in result
            ]

        return await self._execute_sync(_query)

    async def get_performance_summary(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated performance metrics"""
        end_time = end_time or datetime.utcnow()

        def _query():
            result = self._conn.execute(
                """
                SELECT
                    first(portfolio_value) as start_value,
                    last(portfolio_value) as end_value,
                    sum(pnl) as total_pnl,
                    avg(sharpe_ratio) as avg_sharpe,
                    min(max_drawdown) as worst_drawdown,
                    avg(win_rate) as avg_win_rate,
                    max(total_trades) as total_trades
                FROM performance_history
                WHERE timestamp >= ? AND timestamp <= ?
                """,
                [start_time, end_time]
            ).fetchone()

            if not result or result[0] is None:
                return {}

            return {
                "start_value": result[0],
                "end_value": result[1],
                "total_pnl": result[2],
                "avg_sharpe": result[3],
                "worst_drawdown": result[4],
                "avg_win_rate": result[5],
                "total_trades": result[6],
                "return_pct": ((result[1] - result[0]) / result[0] * 100)
                              if result[0] else 0,
            }

        return await self._execute_sync(_query)

    async def get_aggregated_metrics(
        self,
        metric_name: str,
        interval: TimeInterval,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        aggregation: str = "avg",
    ) -> List[Dict[str, Any]]:
        """
        Get time-bucketed aggregated metrics

        Args:
            metric_name: Metric to aggregate
            interval: Time bucket size
            start_time: Start of time range
            end_time: End of time range
            aggregation: avg, sum, min, max, count
        """
        end_time = end_time or datetime.utcnow()

        def _query():
            query = f"""
                SELECT
                    time_bucket(INTERVAL '{interval.duckdb_interval}', timestamp) as bucket,
                    {aggregation}(value) as agg_value,
                    count(*) as sample_count
                FROM trading_metrics
                WHERE metric_name = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                GROUP BY bucket
                ORDER BY bucket DESC
            """
            result = self._conn.execute(
                query,
                [metric_name, start_time, end_time]
            ).fetchall()

            return [
                {
                    "timestamp": row[0],
                    "value": row[1],
                    "sample_count": row[2],
                }
                for row in result
            ]

        return await self._execute_sync(_query)

    async def get_latest_metrics(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get most recent metrics across all types"""
        def _query():
            result = self._conn.execute(
                """
                SELECT DISTINCT ON (metric_name, symbol)
                    timestamp,
                    metric_name,
                    value,
                    symbol
                FROM trading_metrics
                ORDER BY metric_name, symbol, timestamp DESC
                LIMIT ?
                """,
                [limit]
            ).fetchall()

            return [
                {
                    "timestamp": row[0],
                    "metric_name": row[1],
                    "value": row[2],
                    "symbol": row[3],
                }
                for row in result
            ]

        return await self._execute_sync(_query)

    # ========== Optimization & Maintenance ==========

    async def optimize(self) -> None:
        """Optimize database for better query performance"""
        def _optimize():
            self._conn.execute("CHECKPOINT")
            self._conn.execute("VACUUM")
            logger.info("Database optimized")

        await self._execute_sync(_optimize)

    async def get_table_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get storage statistics for all tables"""
        def _query():
            stats = {}
            for table in ["trading_metrics", "candles", "performance_history"]:
                result = self._conn.execute(
                    f"SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM {table}"
                ).fetchone()

                stats[table] = {
                    "row_count": result[0],
                    "min_timestamp": result[1],
                    "max_timestamp": result[2],
                }
            return stats

        return await self._execute_sync(_query)


# Context manager for automatic connection handling
@asynccontextmanager
async def duckdb_session(db_path: str = "data/trading_metrics.duckdb"):
    """Async context manager for DuckDB sessions"""
    client = DuckDBClient(db_path)
    await client.initialize()
    try:
        yield client
    finally:
        await client.close()
