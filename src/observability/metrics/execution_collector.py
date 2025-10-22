"""
Execution metrics collector.

Tracks order execution and fill quality:
- Order lifecycle (submitted, filled, cancelled, rejected)
- Fill rates and latency
- Slippage analysis
- Execution quality metrics
- Broker/exchange performance
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import deque

from loguru import logger

from .collectors import BaseCollector
from ..models.schemas import Trade, TradeFilter
from ..database import get_db


class ExecutionCollector(BaseCollector):
    """
    Collect order execution and fill metrics.

    Monitors the execution engine and tracks:
    - Order flow and fill statistics
    - Execution quality (slippage, latency)
    - Exchange/broker performance
    """

    def __init__(self):
        super().__init__("execution")

        # Order statistics
        self.orders_submitted = 0
        self.orders_filled = 0
        self.orders_cancelled = 0
        self.orders_rejected = 0

        # Recent trades (limited buffer)
        self.recent_trades: deque = deque(maxlen=1000)

        # Execution quality metrics
        self.avg_fill_latency_ms = 0.0
        self.avg_slippage_bps = 0.0
        self.fill_rate = 0.0

        # Background task
        self.collection_task: Optional[asyncio.Task] = None

        # DuckDB instance
        self.db = get_db()

    async def _start_impl(self):
        """Start execution metrics collection."""
        # TODO: Connect to execution engine and order manager

        # Start background collection
        self.collection_task = asyncio.create_task(self._collect_metrics())

        logger.info("Execution collector started (mock mode)")

    async def _stop_impl(self):
        """Stop execution metrics collection."""
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

        logger.info("Execution collector stopped")

    async def _collect_metrics(self):
        """Background task to collect execution metrics."""
        try:
            while True:
                await asyncio.sleep(1)  # Collect every second

                # TODO: Query execution engine for metrics
                self._generate_mock_execution_metrics()

                # Write to DuckDB
                await self._write_to_database()

                self._increment_metrics_count()
        except asyncio.CancelledError:
            logger.info("Execution collection task cancelled")

    def _generate_mock_execution_metrics(self):
        """Generate mock execution metrics for testing."""
        import random

        # Simulate orders
        new_orders = random.randint(0, 5)
        self.orders_submitted += new_orders
        self.orders_filled += random.randint(0, new_orders)
        self.orders_cancelled += random.randint(0, 1)
        self.orders_rejected += random.randint(0, 1)

        # Calculate fill rate
        if self.orders_submitted > 0:
            self.fill_rate = self.orders_filled / self.orders_submitted

        # Simulate fills
        self.avg_fill_latency_ms = random.uniform(10, 100)
        self.avg_slippage_bps = random.uniform(0, 5)

        # Generate mock trades
        if random.random() > 0.7:  # 30% chance of trade
            mock_trade = {
                "trade_id": f"trade_{self.orders_filled}",
                "symbol": random.choice(["AAPL", "MSFT", "GOOGL"]),
                "side": random.choice(["buy", "sell"]),
                "quantity": random.randint(10, 100),
                "price": random.uniform(100, 200),
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": random.uniform(10, 100),
                "slippage_bps": random.uniform(0, 5)
            }
            self.recent_trades.append(mock_trade)

            # Write trade to database
            asyncio.create_task(self.db.insert_trade(mock_trade))

    async def _write_to_database(self):
        """Write execution metrics to DuckDB."""
        try:
            metrics_data = {
                "timestamp": datetime.utcnow(),
                "orders_submitted": self.orders_submitted,
                "orders_filled": self.orders_filled,
                "orders_cancelled": self.orders_cancelled,
                "orders_rejected": self.orders_rejected,
                "fill_rate": self.fill_rate,
                "avg_latency_ms": self.avg_fill_latency_ms,
                "avg_slippage_bps": self.avg_slippage_bps
            }

            await self.db.insert_execution_metrics(metrics_data)
        except Exception as e:
            logger.error(f"Error writing execution metrics to database: {e}")

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current execution metrics."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "orders_today": self.orders_submitted,
            "fills_today": self.orders_filled,
            "cancelled": self.orders_cancelled,
            "rejected": self.orders_rejected,
            "fill_rate": self.fill_rate,
            "avg_latency_ms": self.avg_fill_latency_ms,
            "avg_slippage_bps": self.avg_slippage_bps
        }

    async def get_trades(
        self,
        filter: TradeFilter,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get trade history with filters."""
        # Filter trades based on criteria
        filtered_trades = list(self.recent_trades)

        # Apply filters
        if filter.symbol:
            filtered_trades = [t for t in filtered_trades if t["symbol"] == filter.symbol]

        if filter.side:
            filtered_trades = [t for t in filtered_trades if t["side"] == filter.side]

        # Apply pagination
        return filtered_trades[offset:offset + limit]

    async def count_trades(self, filter: TradeFilter) -> int:
        """Count trades matching filter."""
        trades = await self.get_trades(filter, limit=10000)
        return len(trades)

    async def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get specific trade by ID."""
        for trade in self.recent_trades:
            if trade["trade_id"] == trade_id:
                return trade
        return None

    async def get_trade_statistics(
        self,
        symbol: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get aggregated trade statistics."""
        # Filter trades by time range and symbol
        filtered_trades = []
        for trade in self.recent_trades:
            trade_time = datetime.fromisoformat(trade["timestamp"])
            if start_time <= trade_time <= end_time:
                if not symbol or trade["symbol"] == symbol:
                    filtered_trades.append(trade)

        if not filtered_trades:
            return {
                "count": 0,
                "total_volume": 0.0,
                "avg_price": 0.0,
                "avg_size": 0.0
            }

        return {
            "count": len(filtered_trades),
            "total_volume": sum(t["quantity"] * t["price"] for t in filtered_trades),
            "avg_price": sum(t["price"] for t in filtered_trades) / len(filtered_trades),
            "avg_size": sum(t["quantity"] for t in filtered_trades) / len(filtered_trades),
            "buy_count": sum(1 for t in filtered_trades if t["side"] == "buy"),
            "sell_count": sum(1 for t in filtered_trades if t["side"] == "sell")
        }

    async def get_execution_quality(self) -> Dict[str, Any]:
        """Get execution quality analysis."""
        return {
            "fill_rate": self.fill_rate,
            "avg_latency_ms": self.avg_fill_latency_ms,
            "avg_slippage_bps": self.avg_slippage_bps,
            "rejection_rate": self.orders_rejected / max(self.orders_submitted, 1),
            "cancellation_rate": self.orders_cancelled / max(self.orders_submitted, 1)
        }
