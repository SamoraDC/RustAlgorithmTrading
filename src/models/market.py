"""
Market data models for OHLCV bars, trades, and quotes.
"""

from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseModel


class Bar(BaseModel):
    """OHLCV bar data."""
    symbol: str
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    vwap: Optional[float] = None
    trade_count: Optional[int] = None

    @field_validator('high')
    @classmethod
    def validate_high(cls, v: float, info) -> float:
        if 'low' in info.data and v < info.data['low']:
            raise ValueError("High must be >= low")
        return v

    @field_validator('open', 'close')
    @classmethod
    def validate_price(cls, v: float, info) -> float:
        if 'low' in info.data and 'high' in info.data:
            if not (info.data['low'] <= v <= info.data['high']):
                raise ValueError("Price must be between low and high")
        return v


class Trade(BaseModel):
    """Individual trade tick."""
    symbol: str
    timestamp: datetime
    price: float = Field(gt=0)
    size: float = Field(gt=0)
    exchange: str
    conditions: Optional[list[str]] = None


class Quote(BaseModel):
    """Bid/Ask quote data."""
    symbol: str
    timestamp: datetime
    bid_price: float = Field(gt=0)
    bid_size: float = Field(gt=0)
    ask_price: float = Field(gt=0)
    ask_size: float = Field(gt=0)

    @field_validator('ask_price')
    @classmethod
    def validate_spread(cls, v: float, info) -> float:
        if 'bid_price' in info.data and v < info.data['bid_price']:
            raise ValueError("Ask price must be >= bid price")
        return v

    @property
    def mid_price(self) -> float:
        """Calculate mid price."""
        return (self.bid_price + self.ask_price) / 2.0

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        return self.ask_price - self.bid_price

    @property
    def spread_bps(self) -> float:
        """Calculate spread in basis points."""
        return (self.spread / self.mid_price) * 10000.0
