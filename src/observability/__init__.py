"""
Observability Module - Comprehensive Logging, Metrics, and Monitoring

This module provides production-grade observability infrastructure for the
algorithmic trading system, including:
- Structured logging with correlation tracking
- Performance metrics and monitoring
- Distributed tracing capabilities
- Log aggregation and analysis
- Real-time FastAPI backend with WebSocket streaming
- Metric collectors for market data, strategy, execution, and system health

Author: Trading System Team
Version: 1.0.0
"""

from .logging import (
    get_logger,
    StructuredLogger,
    correlation_id,
    log_execution_time,
    log_trade_decision,
    log_error_with_context,
    MarketDataLogger,
    StrategyLogger,
    RiskLogger,
    ExecutionLogger,
    SystemLogger,
)

# Import FastAPI backend components
from .api import app, WebSocketManager
from .metrics import (
    BaseCollector,
    MarketDataCollector,
    StrategyCollector,
    ExecutionCollector,
    SystemCollector
)
from .models import (
    MetricsSnapshot,
    Trade,
    SystemHealth,
    PerformanceMetrics
)

__all__ = [
    # Logging
    "get_logger",
    "StructuredLogger",
    "correlation_id",
    "log_execution_time",
    "log_trade_decision",
    "log_error_with_context",
    "MarketDataLogger",
    "StrategyLogger",
    "RiskLogger",
    "ExecutionLogger",
    "SystemLogger",
    # API
    "app",
    "WebSocketManager",
    # Collectors
    "BaseCollector",
    "MarketDataCollector",
    "StrategyCollector",
    "ExecutionCollector",
    "SystemCollector",
    # Models
    "MetricsSnapshot",
    "Trade",
    "SystemHealth",
    "PerformanceMetrics"
]

__version__ = "1.0.0"
