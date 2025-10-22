"""
SQLite Operational Data Client

Lightweight database for operational data and metadata (OLTP).
Used for trade logs, system events, and transactional data.
"""

import asyncio
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging

from .schemas import SQLITE_SCHEMAS


logger = logging.getLogger(__name__)


class SQLiteClient:
    """
    SQLite client for operational data

    Features:
    - Async operations with aiosqlite
    - ACID transactions
    - Optimized for OLTP workloads
    - JSON metadata support
    """

    def __init__(
        self,
        db_path: str = "data/trading_operational.db",
        timeout: float = 5.0,
    ):
        """
        Initialize SQLite client

        Args:
            db_path: Path to SQLite database file
            timeout: Connection timeout in seconds
        """
        self.db_path = Path(db_path)
        self.timeout = timeout
        self._conn: Optional[aiosqlite.Connection] = None

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database and create tables"""
        self._conn = await aiosqlite.connect(
            str(self.db_path),
            timeout=self.timeout,
        )

        # Enable WAL mode for better concurrency
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

        # Create tables
        for table_name, schema_sql in SQLITE_SCHEMAS.items():
            await self._conn.executescript(schema_sql)
            logger.debug(f"Created table: {table_name}")

        await self._conn.commit()
        logger.info(f"SQLite initialized: {self.db_path}")

    async def close(self) -> None:
        """Close database connection"""
        if self._conn:
            await self._conn.close()
            self._conn = None
        logger.info("SQLite connection closed")

    # ========== Trade Log Operations ==========

    async def log_trade(
        self,
        timestamp: datetime,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: Optional[str] = None,
        status: str = "executed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Log a trade execution

        Returns:
            Trade log ID
        """
        cursor = await self._conn.execute(
            """
            INSERT INTO trade_log
            (timestamp, symbol, side, quantity, price, order_id, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                symbol,
                side,
                quantity,
                price,
                order_id,
                status,
                json.dumps(metadata) if metadata else None,
            )
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def get_trades(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        symbol: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query trade log with filters"""
        end_time = end_time or datetime.utcnow()

        query = """
            SELECT id, timestamp, symbol, side, quantity, price,
                   order_id, status, metadata
            FROM trade_log
            WHERE timestamp >= ? AND timestamp <= ?
        """
        params = [start_time, end_time]

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "symbol": row[2],
                "side": row[3],
                "quantity": row[4],
                "price": row[5],
                "order_id": row[6],
                "status": row[7],
                "metadata": json.loads(row[8]) if row[8] else None,
            }
            for row in rows
        ]

    async def get_trade_stats(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated trade statistics"""
        end_time = end_time or datetime.utcnow()

        cursor = await self._conn.execute(
            """
            SELECT
                COUNT(*) as total_trades,
                COUNT(DISTINCT symbol) as symbols_traded,
                SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sell_count,
                SUM(quantity * price) as total_volume
            FROM trade_log
            WHERE timestamp >= ? AND timestamp <= ?
              AND status = 'executed'
            """,
            [start_time, end_time]
        )
        row = await cursor.fetchone()

        return {
            "total_trades": row[0] or 0,
            "symbols_traded": row[1] or 0,
            "buy_count": row[2] or 0,
            "sell_count": row[3] or 0,
            "total_volume": row[4] or 0.0,
        }

    # ========== System Events Operations ==========

    async def log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> int:
        """
        Log a system event

        Args:
            event_type: Event category (e.g., 'order', 'error', 'system')
            severity: Event severity (info, warning, error, critical)
            message: Human-readable message
            details: Additional event details
            timestamp: Event timestamp (defaults to now)

        Returns:
            Event log ID
        """
        timestamp = timestamp or datetime.utcnow()

        cursor = await self._conn.execute(
            """
            INSERT INTO system_events
            (timestamp, event_type, severity, message, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                event_type,
                severity,
                message,
                json.dumps(details) if details else None,
            )
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def get_events(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query system events with filters"""
        end_time = end_time or datetime.utcnow()

        query = """
            SELECT id, timestamp, event_type, severity, message, details
            FROM system_events
            WHERE timestamp >= ? AND timestamp <= ?
        """
        params = [start_time, end_time]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "severity": row[3],
                "message": row[4],
                "details": json.loads(row[5]) if row[5] else None,
            }
            for row in rows
        ]

    async def get_event_counts(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, int]]:
        """Get event counts by type and severity"""
        end_time = end_time or datetime.utcnow()

        cursor = await self._conn.execute(
            """
            SELECT event_type, severity, COUNT(*) as count
            FROM system_events
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY event_type, severity
            """,
            [start_time, end_time]
        )
        rows = await cursor.fetchall()

        counts = {}
        for row in rows:
            event_type = row[0]
            if event_type not in counts:
                counts[event_type] = {}
            counts[event_type][row[1]] = row[2]

        return counts

    # ========== Maintenance Operations ==========

    async def vacuum(self) -> None:
        """Optimize database and reclaim space"""
        await self._conn.execute("VACUUM")
        logger.info("Database vacuumed")

    async def get_db_size(self) -> int:
        """Get database file size in bytes"""
        return self.db_path.stat().st_size if self.db_path.exists() else 0


# Context manager for automatic connection handling
@asynccontextmanager
async def sqlite_session(db_path: str = "data/trading_operational.db"):
    """Async context manager for SQLite sessions"""
    client = SQLiteClient(db_path)
    await client.initialize()
    try:
        yield client
    finally:
        await client.close()
