"""
Event-driven architecture event types for backtesting.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseModel


class EventType(str, Enum):
    """Event type enumeration."""
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


class Event(BaseModel):
    """Base event class."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarketEvent(Event):
    """Market data update event."""
    event_type: EventType = Field(default=EventType.MARKET, frozen=True)
    symbol: str
    price: float
    volume: Optional[float] = None

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class SignalEvent(Event):
    """Trading signal event."""
    event_type: EventType = Field(default=EventType.SIGNAL, frozen=True)
    symbol: str
    signal_type: str  # 'LONG', 'SHORT', 'EXIT'
    strength: float = Field(ge=0.0, le=1.0)
    strategy_id: str

    @field_validator('signal_type')
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        allowed = {'LONG', 'SHORT', 'EXIT'}
        if v not in allowed:
            raise ValueError(f"Signal type must be one of {allowed}")
        return v


class OrderEvent(Event):
    """Order placement event."""
    event_type: EventType = Field(default=EventType.ORDER, frozen=True)
    symbol: str
    order_type: str  # 'MKT', 'LMT'
    quantity: int
    direction: str  # 'BUY', 'SELL'
    price: Optional[float] = None

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in {'BUY', 'SELL'}:
            raise ValueError("Direction must be 'BUY' or 'SELL'")
        return v


class FillEvent(Event):
    """Order fill event."""
    event_type: EventType = Field(default=EventType.FILL, frozen=True)
    symbol: str
    exchange: str
    quantity: int
    direction: str  # 'BUY', 'SELL'
    fill_price: float
    commission: float = 0.0

    @field_validator('fill_price', 'commission')
    @classmethod
    def validate_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v
