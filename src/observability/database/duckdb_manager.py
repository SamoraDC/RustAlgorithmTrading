"""
DuckDB database manager for time-series metrics storage.

Provides high-performance, embedded analytics database with:
- Columnar storage for fast aggregations
- SQL interface compatible with PostgreSQL
- ACID transactions
- Fast batch inserts
- Time-series optimized queries
"""
import asyncio
import duckdb
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from contextlib import contextmanager
import threading


class DuckDBManager:
    """
    Thread-safe DuckDB connection manager for metrics storage.

    Features:
    - Connection pooling per thread
    - Automatic table creation
    - Batch write optimization
    - Time-series aggregation helpers
    """

    def __init__(self, db_path: str = "data/observability.duckdb"):
        """
        Initialize DuckDB manager.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self._connections: Dict[int, duckdb.DuckDBPyConnection] = {}
        self._lock = threading.Lock()

        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create initial connection and schema
        self._init_database()

        logger.info(f"DuckDB manager initialized: {db_path}")

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create connection for current thread."""
        thread_id = threading.get_ident()

        if thread_id not in self._connections:
            with self._lock:
                if thread_id not in self._connections:
                    self._connections[thread_id] = duckdb.connect(self.db_path)
                    logger.debug(f"Created DuckDB connection for thread {thread_id}")

        return self._connections[thread_id]

    @contextmanager
    def get_connection(self):
        """Context manager for getting thread-safe connection."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            logger.error(f"DuckDB error: {e}")
            raise

    def _init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            # Market data metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR NOT NULL,
                    last_price DOUBLE,
                    bid DOUBLE,
                    ask DOUBLE,
                    volume BIGINT,
                    trades INTEGER,
                    spread_bps DOUBLE,
                    PRIMARY KEY (timestamp, symbol)
                )
            """)

            # Create index for time-based queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_timestamp
                ON market_data(timestamp DESC)
            """)

            # Strategy metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_metrics (
                    timestamp TIMESTAMP NOT NULL,
                    strategy_name VARCHAR NOT NULL,
                    pnl DOUBLE,
                    daily_pnl DOUBLE,
                    positions INTEGER,
                    signals INTEGER,
                    win_rate DOUBLE,
                    PRIMARY KEY (timestamp, strategy_name)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_strategy_timestamp
                ON strategy_metrics(timestamp DESC)
            """)

            # Execution metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_metrics (
                    timestamp TIMESTAMP NOT NULL,
                    orders_submitted INTEGER,
                    orders_filled INTEGER,
                    orders_cancelled INTEGER,
                    orders_rejected INTEGER,
                    fill_rate DOUBLE,
                    avg_latency_ms DOUBLE,
                    avg_slippage_bps DOUBLE,
                    PRIMARY KEY (timestamp)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_timestamp
                ON execution_metrics(timestamp DESC)
            """)

            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    timestamp TIMESTAMP NOT NULL,
                    cpu_percent DOUBLE,
                    memory_percent DOUBLE,
                    disk_usage_percent DOUBLE,
                    uptime_seconds DOUBLE,
                    health_status VARCHAR,
                    active_alerts INTEGER,
                    PRIMARY KEY (timestamp)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_timestamp
                ON system_metrics(timestamp DESC)
            """)

            # Trades table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR NOT NULL,
                    side VARCHAR NOT NULL,
                    quantity DOUBLE NOT NULL,
                    price DOUBLE NOT NULL,
                    latency_ms DOUBLE,
                    slippage_bps DOUBLE,
                    strategy VARCHAR
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_timestamp
                ON trades(timestamp DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol
                ON trades(symbol)
            """)

            logger.info("DuckDB schema initialized")

    async def insert_market_data(self, data: List[Dict[str, Any]]):
        """
        Insert market data metrics in batch.

        Args:
            data: List of market data records
        """
        if not data:
            return

        try:
            with self.get_connection() as conn:
                # Prepare batch insert
                values = [
                    (
                        record.get("timestamp", datetime.utcnow()),
                        record["symbol"],
                        record.get("last_price"),
                        record.get("bid"),
                        record.get("ask"),
                        record.get("volume", 0),
                        record.get("trades", 0),
                        record.get("spread_bps", 0.0)
                    )
                    for record in data
                ]

                conn.executemany("""
                    INSERT OR REPLACE INTO market_data
                    (timestamp, symbol, last_price, bid, ask, volume, trades, spread_bps)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, values)

                logger.debug(f"Inserted {len(data)} market data records")
        except Exception as e:
            logger.error(f"Error inserting market data: {e}")
            raise

    async def insert_strategy_metrics(self, data: List[Dict[str, Any]]):
        """Insert strategy metrics in batch."""
        if not data:
            return

        try:
            with self.get_connection() as conn:
                values = [
                    (
                        record.get("timestamp", datetime.utcnow()),
                        record["strategy_name"],
                        record.get("pnl", 0.0),
                        record.get("daily_pnl", 0.0),
                        record.get("positions", 0),
                        record.get("signals", 0),
                        record.get("win_rate", 0.0)
                    )
                    for record in data
                ]

                conn.executemany("""
                    INSERT OR REPLACE INTO strategy_metrics
                    (timestamp, strategy_name, pnl, daily_pnl, positions, signals, win_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, values)

                logger.debug(f"Inserted {len(data)} strategy metrics records")
        except Exception as e:
            logger.error(f"Error inserting strategy metrics: {e}")
            raise

    async def insert_execution_metrics(self, data: Dict[str, Any]):
        """Insert execution metrics."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO execution_metrics
                    (timestamp, orders_submitted, orders_filled, orders_cancelled,
                     orders_rejected, fill_rate, avg_latency_ms, avg_slippage_bps)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get("timestamp", datetime.utcnow()),
                    data.get("orders_submitted", 0),
                    data.get("orders_filled", 0),
                    data.get("orders_cancelled", 0),
                    data.get("orders_rejected", 0),
                    data.get("fill_rate", 0.0),
                    data.get("avg_latency_ms", 0.0),
                    data.get("avg_slippage_bps", 0.0)
                ))

                logger.debug("Inserted execution metrics")
        except Exception as e:
            logger.error(f"Error inserting execution metrics: {e}")
            raise

    async def insert_system_metrics(self, data: Dict[str, Any]):
        """Insert system metrics."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_metrics
                    (timestamp, cpu_percent, memory_percent, disk_usage_percent,
                     uptime_seconds, health_status, active_alerts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get("timestamp", datetime.utcnow()),
                    data.get("cpu_percent", 0.0),
                    data.get("memory_percent", 0.0),
                    data.get("disk_usage_percent", 0.0),
                    data.get("uptime_seconds", 0.0),
                    data.get("health_status", "unknown"),
                    data.get("active_alerts", 0)
                ))

                logger.debug("Inserted system metrics")
        except Exception as e:
            logger.error(f"Error inserting system metrics: {e}")
            raise

    async def insert_trade(self, trade: Dict[str, Any]):
        """Insert a single trade record."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trades
                    (trade_id, timestamp, symbol, side, quantity, price,
                     latency_ms, slippage_bps, strategy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade["trade_id"],
                    trade.get("timestamp", datetime.utcnow()),
                    trade["symbol"],
                    trade["side"],
                    trade["quantity"],
                    trade["price"],
                    trade.get("latency_ms"),
                    trade.get("slippage_bps"),
                    trade.get("strategy")
                ))

                logger.debug(f"Inserted trade: {trade['trade_id']}")
        except Exception as e:
            logger.error(f"Error inserting trade: {e}")
            raise

    async def query_market_data(
        self,
        start_time: datetime,
        end_time: datetime,
        symbol: Optional[str] = None,
        interval: str = "1m"
    ) -> List[Dict[str, Any]]:
        """
        Query market data with time-based aggregation.

        Args:
            start_time: Query start time
            end_time: Query end time
            symbol: Optional symbol filter
            interval: Aggregation interval (1m, 5m, 15m, 1h, 1d)

        Returns:
            List of aggregated market data records
        """
        interval_map = {
            "1m": "1 minute",
            "5m": "5 minutes",
            "15m": "15 minutes",
            "1h": "1 hour",
            "1d": "1 day"
        }

        time_bucket = interval_map.get(interval, "1 minute")

        symbol_filter = f"AND symbol = '{symbol}'" if symbol else ""

        query = f"""
            SELECT
                time_bucket(INTERVAL '{time_bucket}', timestamp) as bucket,
                symbol,
                AVG(last_price) as avg_price,
                MAX(last_price) as high,
                MIN(last_price) as low,
                SUM(volume) as total_volume,
                SUM(trades) as total_trades,
                AVG(spread_bps) as avg_spread
            FROM market_data
            WHERE timestamp >= ? AND timestamp <= ?
            {symbol_filter}
            GROUP BY bucket, symbol
            ORDER BY bucket DESC
        """

        try:
            with self.get_connection() as conn:
                result = conn.execute(query, (start_time, end_time)).fetchall()

                return [
                    {
                        "timestamp": row[0],
                        "symbol": row[1],
                        "avg_price": row[2],
                        "high": row[3],
                        "low": row[4],
                        "total_volume": row[5],
                        "total_trades": row[6],
                        "avg_spread": row[7]
                    }
                    for row in result
                ]
        except Exception as e:
            logger.error(f"Error querying market data: {e}")
            return []

    async def query_strategy_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        strategy_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query strategy metrics."""
        strategy_filter = f"AND strategy_name = '{strategy_name}'" if strategy_name else ""

        query = f"""
            SELECT
                timestamp,
                strategy_name,
                pnl,
                daily_pnl,
                positions,
                signals,
                win_rate
            FROM strategy_metrics
            WHERE timestamp >= ? AND timestamp <= ?
            {strategy_filter}
            ORDER BY timestamp DESC
        """

        try:
            with self.get_connection() as conn:
                result = conn.execute(query, (start_time, end_time)).fetchall()

                return [
                    {
                        "timestamp": row[0],
                        "strategy_name": row[1],
                        "pnl": row[2],
                        "daily_pnl": row[3],
                        "positions": row[4],
                        "signals": row[5],
                        "win_rate": row[6]
                    }
                    for row in result
                ]
        except Exception as e:
            logger.error(f"Error querying strategy metrics: {e}")
            return []

    async def close(self):
        """Close all database connections."""
        with self._lock:
            for thread_id, conn in self._connections.items():
                try:
                    conn.close()
                    logger.debug(f"Closed DuckDB connection for thread {thread_id}")
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

            self._connections.clear()

        logger.info("DuckDB manager closed")


# Global database instance
_db_instance: Optional[DuckDBManager] = None


def get_db() -> DuckDBManager:
    """Get global DuckDB instance."""
    global _db_instance

    if _db_instance is None:
        _db_instance = DuckDBManager()

    return _db_instance
