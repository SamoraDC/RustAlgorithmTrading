"""
Market data metrics collector.

Collects and aggregates metrics from market data feeds:
- Price data (bid, ask, last, VWAP)
- Volume and trade counts
- Spread analysis
- Order book depth
- Market microstructure metrics
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from loguru import logger

from .collectors import BaseCollector
from ..database import get_db
from .rust_bridge import get_rust_metrics_bridge


class MarketDataCollector(BaseCollector):
    """
    Collect market data metrics for real-time monitoring.

    Integrates with market data feeds to track:
    - Real-time prices and volumes
    - Spread and liquidity metrics
    - Trade flow and market depth
    """

    def __init__(self):
        super().__init__("market_data")

        # Tracked symbols and their metrics
        self.symbols: Dict[str, Dict[str, Any]] = {}

        # Aggregated metrics
        self.total_trades = 0
        self.total_volume = 0.0

        # Background task for metric aggregation
        self.aggregation_task: Optional[asyncio.Task] = None

        # DuckDB instance
        self.db = get_db()

        # Batch buffer for efficient writes
        self.batch_buffer: List[Dict[str, Any]] = []
        self.batch_size = 100

    async def _start_impl(self):
        """Start market data collection."""
        # Get Rust metrics bridge
        self.rust_bridge = get_rust_metrics_bridge()
        await self.rust_bridge.start()

        # Start background aggregation task
        self.aggregation_task = asyncio.create_task(self._aggregate_metrics())

        logger.info("Market data collector started - connected to Rust service on port 9091")

    async def _stop_impl(self):
        """Stop market data collection."""
        if self.aggregation_task:
            self.aggregation_task.cancel()
            try:
                await self.aggregation_task
            except asyncio.CancelledError:
                pass

        logger.info("Market data collector stopped")

    async def _aggregate_metrics(self):
        """Background task to aggregate metrics periodically."""
        try:
            while True:
                await asyncio.sleep(1)  # Aggregate every second

                # Scrape metrics from Rust market-data service
                rust_metrics = await self.rust_bridge.scrape_service(
                    "market_data",
                    "http://127.0.0.1:9091/metrics"
                )

                if rust_metrics:
                    # Process and store metrics
                    await self._process_rust_metrics(rust_metrics)
                    self._increment_metrics_count()
                else:
                    # Fallback to mock data if Rust service unavailable
                    logger.debug("Rust service unavailable, using mock data")
                    self._generate_mock_metrics()

                # Write to DuckDB in batches
                await self._flush_to_database()

        except asyncio.CancelledError:
            logger.info("Market data aggregation task cancelled")
            # Flush remaining data
            await self._flush_to_database()

    def _generate_mock_metrics(self):
        """Generate mock market data for testing."""
        import random

        mock_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

        for symbol in mock_symbols:
            if symbol not in self.symbols:
                self.symbols[symbol] = {
                    "last_price": 100.0 + random.uniform(-10, 10),
                    "bid": 0,
                    "ask": 0,
                    "volume": 0,
                    "trades": 0
                }

            # Simulate price changes
            self.symbols[symbol]["last_price"] += random.uniform(-0.5, 0.5)
            self.symbols[symbol]["bid"] = self.symbols[symbol]["last_price"] - random.uniform(0.01, 0.1)
            self.symbols[symbol]["ask"] = self.symbols[symbol]["last_price"] + random.uniform(0.01, 0.1)
            self.symbols[symbol]["volume"] += random.randint(100, 1000)
            self.symbols[symbol]["trades"] += random.randint(1, 10)

            self.total_trades += random.randint(1, 10)
            self.total_volume += random.uniform(1000, 10000)

            # Add to batch buffer for database write
            self.batch_buffer.append({
                "timestamp": datetime.utcnow(),
                "symbol": symbol,
                "last_price": self.symbols[symbol]["last_price"],
                "bid": self.symbols[symbol]["bid"],
                "ask": self.symbols[symbol]["ask"],
                "volume": self.symbols[symbol]["volume"],
                "trades": self.symbols[symbol]["trades"],
                "spread_bps": (self.symbols[symbol]["ask"] - self.symbols[symbol]["bid"]) /
                             self.symbols[symbol]["last_price"] * 10000
            })

    async def _flush_to_database(self):
        """Flush batch buffer to DuckDB."""
        if len(self.batch_buffer) >= self.batch_size or not self.started:
            if self.batch_buffer:
                try:
                    await self.db.insert_market_data(self.batch_buffer)
                    self.batch_buffer.clear()
                except Exception as e:
                    logger.error(f"Error flushing market data to database: {e}")

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current market data metrics."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "symbols": self.symbols,
            "total_trades": self.total_trades,
            "total_volume": self.total_volume,
            "symbols_tracked": len(self.symbols)
        }

    async def get_tracked_symbols(self) -> List[str]:
        """Get list of symbols being tracked."""
        return list(self.symbols.keys())

    async def get_symbol_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific symbol."""
        return self.symbols.get(symbol)

    async def add_symbol(self, symbol: str):
        """Start tracking a new symbol."""
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                "last_price": 0.0,
                "bid": 0.0,
                "ask": 0.0,
                "volume": 0,
                "trades": 0,
                "added_at": datetime.utcnow().isoformat()
            }
            logger.info(f"Added symbol {symbol} to market data collector")

    async def remove_symbol(self, symbol: str):
        """Stop tracking a symbol."""
        if symbol in self.symbols:
            del self.symbols[symbol]
            logger.info(f"Removed symbol {symbol} from market data collector")

    async def _process_rust_metrics(self, rust_metrics: Dict[str, Any]):
        """
        Process metrics scraped from Rust service.

        Args:
            rust_metrics: Parsed metrics from Rust service
        """
        timestamp = rust_metrics.get("timestamp", datetime.utcnow())

        # Process counters
        for metric_key, metric_data in rust_metrics.get("counters", {}).items():
            metric_name = metric_data["name"]
            value = metric_data["value"]
            labels = metric_data.get("labels", {})

            # Extract symbol from labels if present
            symbol = labels.get("symbol", "UNKNOWN")

            # Update internal tracking
            if "ticks_received" in metric_name or "ticks_processed" in metric_name:
                if symbol not in self.symbols:
                    self.symbols[symbol] = {
                        "last_price": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                        "volume": 0,
                        "trades": int(value)
                    }
                else:
                    self.symbols[symbol]["trades"] = int(value)

        # Process gauges (current values)
        for metric_key, metric_data in rust_metrics.get("gauges", {}).items():
            metric_name = metric_data["name"]
            value = metric_data["value"]
            labels = metric_data.get("labels", {})

            symbol = labels.get("symbol", "UNKNOWN")

            if "price" in metric_name:
                if symbol not in self.symbols:
                    self.symbols[symbol] = {
                        "last_price": value,
                        "bid": 0.0,
                        "ask": 0.0,
                        "volume": 0,
                        "trades": 0
                    }
                else:
                    self.symbols[symbol]["last_price"] = value

        # Add processed data to batch buffer
        for symbol, data in self.symbols.items():
            self.batch_buffer.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "last_price": data["last_price"],
                "bid": data.get("bid", 0.0),
                "ask": data.get("ask", 0.0),
                "volume": data.get("volume", 0),
                "trades": data.get("trades", 0),
                "spread_bps": (data.get("ask", 0.0) - data.get("bid", 0.0)) /
                             max(data["last_price"], 0.01) * 10000
            })
