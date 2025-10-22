"""
Metric data structures for internal use.

These models represent the actual metric data collected
by each collector type.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class MarketDataMetric(BaseModel):
    """Market data metric for a symbol."""
    symbol: str
    timestamp: datetime

    # Price data
    last_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    vwap: Optional[float] = None

    # Volume data
    volume: Optional[int] = None
    trade_count: Optional[int] = None

    # Spread and liquidity
    spread_bps: Optional[float] = Field(None, description="Spread in basis points")
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None

    # Order book
    order_book_imbalance: Optional[float] = Field(
        None,
        description="Order book imbalance (-1 to 1)"
    )


class StrategyMetric(BaseModel):
    """Strategy performance metric."""
    strategy_name: str
    timestamp: datetime

    # P&L
    realized_pnl: float = Field(description="Realized P&L")
    unrealized_pnl: float = Field(description="Unrealized P&L")
    total_pnl: float = Field(description="Total P&L")
    daily_pnl: float = Field(description="Daily P&L")

    # Positions
    open_positions: int = Field(description="Number of open positions")
    position_notional: float = Field(description="Total position notional value")

    # Performance
    win_rate: Optional[float] = Field(None, description="Win rate (0-1)")
    profit_factor: Optional[float] = Field(None, description="Profit factor")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")

    # Signal generation
    signals_generated: int = Field(default=0, description="Total signals generated")
    signals_approved: int = Field(default=0, description="Signals approved by risk")
    signals_rejected: int = Field(default=0, description="Signals rejected by risk")


class ExecutionMetric(BaseModel):
    """Order execution metric."""
    timestamp: datetime

    # Order statistics
    orders_submitted: int = Field(default=0)
    orders_filled: int = Field(default=0)
    orders_cancelled: int = Field(default=0)
    orders_rejected: int = Field(default=0)

    # Fill quality
    fill_rate: float = Field(description="Fill rate (filled/submitted)")
    avg_fill_latency_ms: float = Field(description="Average fill latency (ms)")
    avg_slippage_bps: float = Field(description="Average slippage (bps)")

    # Execution quality
    market_impact_bps: Optional[float] = Field(
        None,
        description="Average market impact (bps)"
    )
    implementation_shortfall: Optional[float] = Field(
        None,
        description="Implementation shortfall"
    )


class SystemMetric(BaseModel):
    """System health metric."""
    timestamp: datetime

    # Resource usage
    cpu_percent: float = Field(description="CPU usage percentage")
    memory_percent: float = Field(description="Memory usage percentage")
    disk_percent: float = Field(description="Disk usage percentage")

    # Network
    network_bytes_sent: Optional[int] = None
    network_bytes_recv: Optional[int] = None

    # Process
    process_count: Optional[int] = None
    thread_count: Optional[int] = None

    # Latency
    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None

    # Health status
    health_status: str = Field(description="Overall health: healthy, degraded, unhealthy")
    active_alerts: int = Field(default=0, description="Number of active alerts")
