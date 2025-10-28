"""
Portfolio and position tracking models.
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import Field, computed_field

from .base import BaseModel


class Position(BaseModel):
    """Individual position tracking."""
    symbol: str
    quantity: int
    average_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    realized_pnl: float = 0.0

    @computed_field
    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        return self.quantity * self.current_price

    @computed_field
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L."""
        return self.quantity * (self.current_price - self.average_price)

    @computed_field
    @property
    def total_pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @computed_field
    @property
    def pnl_percentage(self) -> float:
        """Calculate P&L as percentage of cost basis."""
        cost_basis = abs(self.quantity * self.average_price)
        if cost_basis == 0:
            return 0.0
        return (self.total_pnl / cost_basis) * 100.0


class Portfolio(BaseModel):
    """Portfolio tracking with positions and cash."""
    initial_capital: float = Field(gt=0)
    cash: float = Field(ge=0)  # Changed from gt=0 to ge=0 to allow zero cash
    positions: Dict[str, Position] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    @property
    def equity(self) -> float:
        """Calculate total equity (cash + positions)."""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value

    @computed_field
    @property
    def total_pnl(self) -> float:
        """Calculate total P&L across all positions."""
        return sum(pos.total_pnl for pos in self.positions.values())

    @computed_field
    @property
    def return_percentage(self) -> float:
        """Calculate total return percentage."""
        return ((self.equity - self.initial_capital) / self.initial_capital) * 100.0

    def update_position(self, symbol: str, quantity: int, price: float):
        """
        Update position with new fill.

        Args:
            symbol: Symbol being traded
            quantity: Quantity (positive for buy, negative for sell)
            price: Fill price

        Raises:
            ValueError: If updating would result in negative cash
        """
        # CRITICAL FIX: Check if we have enough cash BEFORE updating
        cash_impact = quantity * price

        if quantity > 0:  # BUY
            if cash_impact > self.cash:
                raise ValueError(
                    f"Insufficient cash: need ${cash_impact:,.2f} but only have ${self.cash:,.2f}"
                )

        if symbol in self.positions:
            pos = self.positions[symbol]
            new_quantity = pos.quantity + quantity

            if new_quantity == 0:
                # Position closed
                pos.realized_pnl += quantity * (price - pos.average_price)
                del self.positions[symbol]
            elif (pos.quantity > 0 and quantity > 0) or (pos.quantity < 0 and quantity < 0):
                # Adding to position
                total_cost = (pos.quantity * pos.average_price) + (quantity * price)
                pos.average_price = total_cost / new_quantity
                pos.quantity = new_quantity
            else:
                # Reducing position
                if abs(quantity) <= abs(pos.quantity):
                    pos.realized_pnl += -quantity * (price - pos.average_price)
                    pos.quantity = new_quantity
                else:
                    # Flip position
                    pos.realized_pnl += -pos.quantity * (price - pos.average_price)
                    pos.quantity = new_quantity
                    pos.average_price = price
        else:
            # New position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                current_price=price
            )

        # Update cash
        self.cash -= quantity * price

        # Final validation
        if self.cash < 0:
            raise ValueError(f"Cash went negative: ${self.cash:,.2f}")


class PerformanceMetrics(BaseModel):
    """Performance metrics for strategy evaluation."""
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0

    @computed_field
    @property
    def average_trade(self) -> float:
        """Calculate average trade P&L."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades * self.average_win +
                self.losing_trades * self.average_loss) / self.total_trades
