"""
FastAPI Integration Helpers

Provides easy integration between FastAPI endpoints and storage clients.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import HTTPException
import logging

from .duckdb_client import DuckDBClient
from .sqlite_client import SQLiteClient
from .schemas import MetricRecord, CandleRecord, PerformanceRecord, TimeInterval


logger = logging.getLogger(__name__)


class StorageManager:
    """
    Unified storage manager for FastAPI applications

    Manages both DuckDB (analytics) and SQLite (operational) connections.
    Thread-safe and optimized for concurrent requests.
    """

    def __init__(
        self,
        duckdb_path: str = "data/trading_metrics.duckdb",
        sqlite_path: str = "data/trading_operational.db",
    ):
        """
        Initialize storage manager

        Args:
            duckdb_path: Path to DuckDB database
            sqlite_path: Path to SQLite database
        """
        self.duckdb_path = duckdb_path
        self.sqlite_path = sqlite_path
        self._duckdb: Optional[DuckDBClient] = None
        self._sqlite: Optional[SQLiteClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize both database connections"""
        if self._initialized:
            return

        self._duckdb = DuckDBClient(self.duckdb_path)
        await self._duckdb.initialize()

        self._sqlite = SQLiteClient(self.sqlite_path)
        await self._sqlite.initialize()

        self._initialized = True
        logger.info("Storage manager initialized")

    async def close(self) -> None:
        """Close all database connections"""
        if self._duckdb:
            await self._duckdb.close()
        if self._sqlite:
            await self._sqlite.close()
        self._initialized = False
        logger.info("Storage manager closed")

    @property
    def duckdb(self) -> DuckDBClient:
        """Get DuckDB client"""
        if not self._initialized or not self._duckdb:
            raise RuntimeError("StorageManager not initialized")
        return self._duckdb

    @property
    def sqlite(self) -> SQLiteClient:
        """Get SQLite client"""
        if not self._initialized or not self._sqlite:
            raise RuntimeError("StorageManager not initialized")
        return self._sqlite

    # ========== Convenience Methods for FastAPI ==========

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        symbol: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single metric (convenience method)"""
        metric = MetricRecord(
            timestamp=datetime.utcnow(),
            metric_name=metric_name,
            value=value,
            symbol=symbol,
            labels=labels,
        )
        await self.duckdb.insert_metric(metric)

    async def get_recent_metrics(
        self,
        metric_name: str,
        minutes: int = 60,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent metrics (last N minutes)"""
        try:
            return await self.duckdb.get_metrics(
                metric_name=metric_name,
                start_time=datetime.utcnow() - timedelta(minutes=minutes),
                symbol=symbol,
            )
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_market_data(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get market candles for a symbol"""
        try:
            # Parse interval
            interval_map = {
                "1s": TimeInterval.SECOND,
                "1m": TimeInterval.MINUTE,
                "1h": TimeInterval.HOUR,
                "1d": TimeInterval.DAY,
            }
            time_interval = interval_map.get(interval, TimeInterval.MINUTE)

            return await self.duckdb.get_candles(
                symbol=symbol,
                interval=time_interval,
                start_time=datetime.utcnow() - timedelta(days=7),
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def log_trade_execution(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log a trade execution"""
        try:
            return await self.sqlite.log_trade(
                timestamp=datetime.utcnow(),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_id=order_id,
                status="executed",
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_trading_summary(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Get trading summary for last N hours"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)

            # Get trade stats from SQLite
            trade_stats = await self.sqlite.get_trade_stats(start_time)

            # Get performance metrics from DuckDB
            performance = await self.duckdb.get_performance_summary(start_time)

            return {
                "period": f"last_{hours}h",
                "trades": trade_stats,
                "performance": performance,
            }
        except Exception as e:
            logger.error(f"Failed to get trading summary: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            # Get database stats
            duckdb_stats = await self.duckdb.get_table_stats()
            sqlite_size = await self.sqlite.get_db_size()

            # Get recent events
            events = await self.sqlite.get_event_counts(
                start_time=datetime.utcnow() - timedelta(hours=1)
            )

            return {
                "status": "healthy",
                "databases": {
                    "duckdb": duckdb_stats,
                    "sqlite": {
                        "size_bytes": sqlite_size,
                        "size_mb": sqlite_size / (1024 * 1024),
                    },
                },
                "recent_events": events,
            }
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get global storage manager instance"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


# FastAPI lifespan context manager
@asynccontextmanager
async def storage_lifespan(app):
    """
    FastAPI lifespan context manager

    Usage:
        from fastapi import FastAPI
        from src.observability.storage.integration import storage_lifespan

        app = FastAPI(lifespan=storage_lifespan)
    """
    storage = get_storage_manager()
    await storage.initialize()
    logger.info("Storage initialized for FastAPI app")

    yield {"storage": storage}

    await storage.close()
    logger.info("Storage closed for FastAPI app")


# Dependency injection for FastAPI routes
async def get_storage() -> StorageManager:
    """
    FastAPI dependency for storage access

    Usage:
        from fastapi import Depends
        from src.observability.storage.integration import get_storage

        @app.get("/metrics")
        async def get_metrics(storage: StorageManager = Depends(get_storage)):
            return await storage.get_recent_metrics("price")
    """
    storage = get_storage_manager()
    if not storage._initialized:
        await storage.initialize()
    return storage
