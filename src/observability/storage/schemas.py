"""
Storage Schema Definitions

Defines data models and SQL schemas for time-series and operational storage.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
import json


class TimeInterval(str, Enum):
    """Time interval for aggregations"""
    SECOND = "1s"
    MINUTE = "1m"
    HOUR = "1h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1mo"

    @property
    def seconds(self) -> int:
        """Get interval in seconds"""
        mapping = {
            "1s": 1,
            "1m": 60,
            "1h": 3600,
            "1d": 86400,
            "1w": 604800,
            "1mo": 2592000,
        }
        return mapping[self.value]

    @property
    def duckdb_interval(self) -> str:
        """Get DuckDB interval expression"""
        mapping = {
            "1s": "1 second",
            "1m": "1 minute",
            "1h": "1 hour",
            "1d": "1 day",
            "1w": "1 week",
            "1mo": "1 month",
        }
        return mapping[self.value]


@dataclass
class MetricRecord:
    """Trading metric record"""
    timestamp: datetime
    metric_name: str
    value: float
    symbol: Optional[str] = None
    labels: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "timestamp": self.timestamp,
            "metric_name": self.metric_name,
            "value": self.value,
            "symbol": self.symbol,
            "labels": json.dumps(self.labels) if self.labels else None,
        }


@dataclass
class CandleRecord:
    """OHLCV candle record"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)


@dataclass
class PerformanceRecord:
    """Portfolio performance record"""
    timestamp: datetime
    portfolio_value: float
    pnl: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_trades: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)


# DuckDB Schema Definitions
DUCKDB_SCHEMAS = {
    "trading_metrics": """
        CREATE TABLE IF NOT EXISTS trading_metrics (
            timestamp TIMESTAMP NOT NULL,
            metric_name VARCHAR NOT NULL,
            value DOUBLE NOT NULL,
            symbol VARCHAR,
            labels JSON
        );

        -- Create indexes for fast queries
        CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON trading_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_metrics_name
            ON trading_metrics(metric_name);
        CREATE INDEX IF NOT EXISTS idx_metrics_symbol
            ON trading_metrics(symbol);
    """,

    "candles": """
        CREATE TABLE IF NOT EXISTS candles (
            timestamp TIMESTAMP NOT NULL,
            symbol VARCHAR NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume BIGINT NOT NULL,
            PRIMARY KEY (timestamp, symbol)
        );

        -- Optimize for time-series queries
        CREATE INDEX IF NOT EXISTS idx_candles_symbol_time
            ON candles(symbol, timestamp);
    """,

    "performance_history": """
        CREATE TABLE IF NOT EXISTS performance_history (
            timestamp TIMESTAMP NOT NULL PRIMARY KEY,
            portfolio_value DOUBLE NOT NULL,
            pnl DOUBLE NOT NULL,
            sharpe_ratio DOUBLE,
            max_drawdown DOUBLE,
            win_rate DOUBLE,
            total_trades INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_performance_timestamp
            ON performance_history(timestamp);
    """,
}


# SQLite Schema for operational data
SQLITE_SCHEMAS = {
    "trade_log": """
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP NOT NULL,
            symbol VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            order_id VARCHAR,
            status VARCHAR NOT NULL,
            metadata TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_trade_timestamp
            ON trade_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_trade_symbol
            ON trade_log(symbol);
    """,

    "system_events": """
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP NOT NULL,
            event_type VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            message TEXT NOT NULL,
            details TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON system_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_type
            ON system_events(event_type);
    """,
}
