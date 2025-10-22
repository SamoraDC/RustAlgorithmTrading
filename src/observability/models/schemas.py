"""
Pydantic schemas for API request/response models.

Defines the data structures for:
- API endpoints
- WebSocket messages
- Database queries
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class TimeRange(str, Enum):
    """Predefined time ranges for queries."""
    HOUR_1 = "1h"
    HOURS_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"


class AggregationInterval(str, Enum):
    """Data aggregation intervals."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    DAY_1 = "1d"


# Metrics Models

class MetricsSnapshot(BaseModel):
    """Current metrics snapshot across all collectors."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "timestamp": "2025-10-21T22:00:00Z",
            "market_data": {"AAPL": {"last": 150.25, "bid": 150.24, "ask": 150.26}},
            "strategy": {"total_pnl": 1250.50, "daily_pnl": 125.75},
            "execution": {"fill_rate": 0.95, "avg_latency_ms": 45.3},
            "system": {"cpu_percent": 35.2, "memory_percent": 62.1}
        }
    })

    timestamp: datetime
    market_data: Dict[str, Any]
    strategy: Dict[str, Any]
    execution: Dict[str, Any]
    system: Dict[str, Any]


class MetricsHistoryRequest(BaseModel):
    """Request for historical metrics query."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "time_range": "24h",
            "metric_types": ["market_data", "strategy"],
            "symbols": ["AAPL", "MSFT"],
            "interval": "5m"
        }
    })

    time_range: Optional[TimeRange] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metric_types: Optional[List[str]] = Field(
        None,
        description="Filter by metric types (market_data, strategy, execution, system)"
    )
    symbols: Optional[List[str]] = Field(None, description="Filter by symbols")
    interval: AggregationInterval = Field(
        AggregationInterval.MINUTE_5,
        description="Aggregation interval"
    )


class MetricsHistoryResponse(BaseModel):
    """Response with historical metrics data."""
    start_time: datetime
    end_time: datetime
    interval: AggregationInterval
    data: List[Dict[str, Any]]
    count: int


# Trade Models

class Trade(BaseModel):
    """Individual trade execution."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trade_id": "trade_12345",
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "price": 150.25,
            "timestamp": "2025-10-21T22:00:00Z",
            "latency_ms": 45.3,
            "slippage_bps": 1.2,
            "pnl": 125.50
        }
    })

    trade_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float
    timestamp: datetime
    latency_ms: Optional[float] = None
    slippage_bps: Optional[float] = None
    pnl: Optional[float] = None
    strategy: Optional[str] = None
    order_id: Optional[str] = None


class TradeFilter(BaseModel):
    """Filters for trade history queries."""
    symbol: Optional[str] = None
    side: Optional[str] = None  # "buy" or "sell"
    start_time: datetime
    end_time: datetime
    strategy: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None


class TradeHistoryResponse(BaseModel):
    """Paginated trade history response."""
    trades: List[Trade]
    total: int
    limit: int
    offset: int


# System Health Models

class ComponentStatus(BaseModel):
    """Status of a system component."""
    status: str  # "healthy", "degraded", "unhealthy", "error"
    usage_percent: Optional[float] = None
    message: Optional[str] = None
    last_updated: Optional[datetime] = None


class SystemHealth(BaseModel):
    """Comprehensive system health status."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "healthy",
            "components": {
                "cpu": {"status": "healthy", "usage_percent": 35.2},
                "memory": {"status": "healthy", "usage_percent": 62.1}
            },
            "resources": {"cpu": 35.2, "memory": 62.1, "disk": 45.8},
            "connections": {
                "market_data": "connected",
                "execution": "connected",
                "database": "connected"
            }
        }
    })

    status: str  # "healthy", "degraded", "unhealthy"
    components: Dict[str, ComponentStatus]
    resources: Dict[str, float]
    connections: Dict[str, str]
    alerts: Optional[List[Dict[str, Any]]] = None


class PerformanceMetrics(BaseModel):
    """System performance metrics."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "latency_p50": 10.5,
            "latency_p95": 45.2,
            "latency_p99": 98.7,
            "throughput_per_sec": 1250.5,
            "cpu_usage": 35.2,
            "memory_usage": 62.1,
            "queue_depth": 15
        }
    })

    latency_p50: float = Field(description="50th percentile latency (ms)")
    latency_p95: float = Field(description="95th percentile latency (ms)")
    latency_p99: float = Field(description="99th percentile latency (ms)")
    throughput_per_sec: float = Field(description="Throughput (operations/sec)")
    cpu_usage: float = Field(description="CPU usage percentage")
    memory_usage: float = Field(description="Memory usage percentage")
    queue_depth: int = Field(description="Current queue depth")


# WebSocket Message Models

class WebSocketMessage(BaseModel):
    """Base WebSocket message format."""
    type: str
    timestamp: datetime
    data: Dict[str, Any]


class MetricsUpdate(WebSocketMessage):
    """Real-time metrics update message."""
    type: str = "metrics_update"
    data: MetricsSnapshot


class TradeNotification(WebSocketMessage):
    """Real-time trade notification."""
    type: str = "trade_notification"
    data: Trade


class AlertNotification(WebSocketMessage):
    """Real-time alert notification."""
    type: str = "alert_notification"
    data: Dict[str, Any]
