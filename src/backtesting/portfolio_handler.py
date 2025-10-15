"""
Portfolio handler for position and cash management during backtesting.
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from src.models.portfolio import Portfolio, Position
from src.models.events import SignalEvent, OrderEvent, FillEvent


class PortfolioHandler:
    """
    Manages portfolio state during backtesting.

    Tracks positions, cash, and equity over time. Generates orders based on
    trading signals and position sizing rules.
    """

    def __init__(
        self,
        initial_capital: float,
        position_sizer: Optional['PositionSizer'] = None,
    ):
        """
        Initialize portfolio handler.

        Args:
            initial_capital: Starting capital
            position_sizer: Position sizing strategy (defaults to FixedAmountSizer)
        """
        self.initial_capital = initial_capital
        self.position_sizer = position_sizer or FixedAmountSizer(10000.0)

        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            cash=initial_capital,
        )

        # Track equity curve
        self.equity_curve: List[Dict] = []
        self.holdings_history: List[Dict] = []

        logger.info(f"Initialized PortfolioHandler with ${initial_capital:,.2f}")

    def update_timeindex(self, timestamp: datetime):
        """
        Update portfolio timestamp and record equity snapshot.

        Args:
            timestamp: Current timestamp
        """
        self.portfolio.timestamp = timestamp

        # Record equity curve point
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.portfolio.equity,
            'cash': self.portfolio.cash,
            'total_pnl': self.portfolio.total_pnl,
            'return_pct': self.portfolio.return_percentage,
        })

    def generate_orders(self, signal: SignalEvent) -> List[OrderEvent]:
        """
        Generate orders from trading signal.

        Args:
            signal: Trading signal

        Returns:
            List of order events
        """
        orders = []

        # Calculate target position based on signal
        target_quantity = self.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=self.portfolio,
        )

        # Get current position
        current_position = self.portfolio.positions.get(signal.symbol)
        current_quantity = current_position.quantity if current_position else 0

        # Calculate order quantity
        order_quantity = target_quantity - current_quantity

        if order_quantity == 0:
            return orders

        # Create order
        order = OrderEvent(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            order_type='MKT',
            quantity=abs(order_quantity),
            direction='BUY' if order_quantity > 0 else 'SELL',
        )

        orders.append(order)

        logger.debug(
            f"Generated {order.direction} order for {order.quantity} {signal.symbol} "
            f"(current: {current_quantity}, target: {target_quantity})"
        )

        return orders

    def update_fill(self, fill: FillEvent):
        """
        Update portfolio with fill event.

        Args:
            fill: Fill event
        """
        # Update position
        self.portfolio.update_position(
            symbol=fill.symbol,
            quantity=fill.quantity,
            price=fill.fill_price,
        )

        # Deduct commission
        self.portfolio.cash -= fill.commission

        # Record holdings
        self.holdings_history.append({
            'timestamp': fill.timestamp,
            'symbol': fill.symbol,
            'quantity': fill.quantity,
            'price': fill.fill_price,
            'commission': fill.commission,
            'cash': self.portfolio.cash,
            'equity': self.portfolio.equity,
        })

        logger.debug(
            f"Updated portfolio with fill: {fill.quantity} {fill.symbol} "
            f"@ {fill.fill_price:.2f} (cash: ${self.portfolio.cash:,.2f})"
        )

    def get_equity_curve(self) -> pd.DataFrame:
        """Get equity curve as DataFrame."""
        return pd.DataFrame(self.equity_curve)

    def get_holdings(self) -> pd.DataFrame:
        """Get holdings history as DataFrame."""
        return pd.DataFrame(self.holdings_history)


class PositionSizer:
    """Base class for position sizing strategies."""

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio
    ) -> int:
        """
        Calculate target position size.

        Args:
            signal: Trading signal
            portfolio: Current portfolio state

        Returns:
            Target position quantity (positive for long, negative for short)
        """
        raise NotImplementedError


class FixedAmountSizer(PositionSizer):
    """Fixed notional amount position sizer."""

    def __init__(self, amount: float):
        """
        Initialize sizer.

        Args:
            amount: Fixed dollar amount per position
        """
        self.amount = amount

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio
    ) -> int:
        """Calculate position size based on fixed amount."""
        # Get current price (would come from market data in real implementation)
        current_position = portfolio.positions.get(signal.symbol)
        price = current_position.current_price if current_position else 100.0

        if signal.signal_type == 'LONG':
            return int(self.amount / price)
        elif signal.signal_type == 'SHORT':
            return -int(self.amount / price)
        else:  # EXIT
            return 0


class PercentageOfEquitySizer(PositionSizer):
    """Position sizer based on percentage of portfolio equity."""

    def __init__(self, percentage: float):
        """
        Initialize sizer.

        Args:
            percentage: Percentage of equity to allocate (0-1)
        """
        self.percentage = percentage

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio
    ) -> int:
        """Calculate position size based on equity percentage."""
        amount = portfolio.equity * self.percentage

        current_position = portfolio.positions.get(signal.symbol)
        price = current_position.current_price if current_position else 100.0

        if signal.signal_type == 'LONG':
            return int(amount / price)
        elif signal.signal_type == 'SHORT':
            return -int(amount / price)
        else:
            return 0


class KellyPositionSizer(PositionSizer):
    """Kelly Criterion position sizer."""

    def __init__(self, fraction: float = 0.25):
        """
        Initialize Kelly sizer.

        Args:
            fraction: Fraction of Kelly to use (for safety)
        """
        self.fraction = fraction

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio
    ) -> int:
        """Calculate position size using Kelly Criterion."""
        # Kelly formula: f = (bp - q) / b
        # where b = odds, p = win probability, q = 1-p
        # For this implementation, use signal strength as proxy for probability

        win_prob = signal.strength
        loss_prob = 1 - win_prob
        win_loss_ratio = 2.0  # Assume 2:1 reward:risk

        kelly_fraction = (win_prob * win_loss_ratio - loss_prob) / win_loss_ratio
        kelly_fraction = max(0, min(kelly_fraction, 1.0))  # Clamp to [0, 1]
        kelly_fraction *= self.fraction  # Apply fractional Kelly

        amount = portfolio.equity * kelly_fraction

        current_position = portfolio.positions.get(signal.symbol)
        price = current_position.current_price if current_position else 100.0

        if signal.signal_type == 'LONG':
            return int(amount / price)
        elif signal.signal_type == 'SHORT':
            return -int(amount / price)
        else:
            return 0
