"""
Structured Logging Module

Provides hierarchical, async-capable structured logging with correlation tracking,
specialized log streams, and performance optimization.
"""

from .structured_logger import StructuredLogger, get_logger
from .correlations import correlation_id
from .formatters import JSONFormatter, StructuredFormatter
from .handlers import AsyncQueueHandler, RotatingFileHandlerAsync
from .streams import (
    MarketDataLogger,
    StrategyLogger,
    RiskLogger,
    ExecutionLogger,
    SystemLogger,
)
from .decorators import (
    log_execution_time,
    log_trade_decision,
    log_error_with_context,
)

__all__ = [
    "StructuredLogger",
    "get_logger",
    "correlation_id",
    "JSONFormatter",
    "StructuredFormatter",
    "AsyncQueueHandler",
    "RotatingFileHandlerAsync",
    "MarketDataLogger",
    "StrategyLogger",
    "RiskLogger",
    "ExecutionLogger",
    "SystemLogger",
    "log_execution_time",
    "log_trade_decision",
    "log_error_with_context",
]
