"""
Event models for real-time notifications.

Events are used for:
- WebSocket streaming
- Event-driven triggers
- Logging and auditing
"""
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events in the system."""
    # Metric events
    METRIC_UPDATE = "metric_update"
    METRIC_THRESHOLD = "metric_threshold"

    # Trade events
    TRADE_EXECUTED = "trade_executed"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"

    # Strategy events
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_APPROVED = "signal_approved"
    SIGNAL_REJECTED = "signal_rejected"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"

    # System events
    SYSTEM_ALERT = "system_alert"
    COMPONENT_ERROR = "component_error"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"


class BaseEvent(BaseModel):
    """Base event model."""
    event_id: str = Field(description="Unique event identifier")
    event_type: EventType
    timestamp: datetime
    source: str = Field(description="Source component")
    metadata: Optional[Dict[str, Any]] = None


class MetricEvent(BaseEvent):
    """Metric update or threshold event."""
    metric_name: str
    metric_value: float
    threshold: Optional[float] = None
    exceeded: bool = False


class TradeEvent(BaseEvent):
    """Trade execution event."""
    trade_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float
    strategy: Optional[str] = None
    pnl: Optional[float] = None


class OrderEvent(BaseEvent):
    """Order lifecycle event."""
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str  # "market", "limit", "stop", etc.
    status: str  # "new", "filled", "cancelled", "rejected"
    reason: Optional[str] = None


class AlertEvent(BaseEvent):
    """System alert event."""
    alert_type: str  # "warning", "error", "critical"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    details: Optional[Dict[str, Any]] = None
    acknowledged: bool = False


class StrategyEvent(BaseEvent):
    """Strategy-related event."""
    strategy_name: str
    event_data: Dict[str, Any]


class SystemEvent(BaseEvent):
    """System-level event."""
    component: str
    status: str  # "healthy", "degraded", "unhealthy", "error"
    message: str
    details: Optional[Dict[str, Any]] = None
