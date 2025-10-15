"""
Simulated execution handler for backtesting.
"""

from datetime import datetime
from typing import Optional
import numpy as np
from loguru import logger

from src.models.events import OrderEvent, FillEvent


class SimulatedExecutionHandler:
    """
    Simulates order execution with realistic market impact and transaction costs.

    Features:
    - Configurable commission rates
    - Slippage modeling (fixed or percentage-based)
    - Partial fill simulation
    - Market impact modeling
    """

    def __init__(
        self,
        commission_rate: float = 0.001,  # 10 bps
        slippage_bps: float = 5.0,  # 5 basis points
        market_impact_bps: float = 2.0,  # 2 basis points per $1M notional
        partial_fill_probability: float = 0.0,  # No partial fills by default
    ):
        """
        Initialize execution handler.

        Args:
            commission_rate: Commission as fraction of trade value
            slippage_bps: Average slippage in basis points
            market_impact_bps: Market impact per $1M notional
            partial_fill_probability: Probability of partial fill (0-1)
        """
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps
        self.market_impact_bps = market_impact_bps
        self.partial_fill_probability = partial_fill_probability

        logger.info(
            f"Initialized SimulatedExecutionHandler with "
            f"commission={commission_rate:.4f}, "
            f"slippage={slippage_bps}bps, "
            f"impact={market_impact_bps}bps/$1M"
        )

    def execute_order(self, order: OrderEvent) -> Optional[FillEvent]:
        """
        Simulate order execution.

        Args:
            order: Order to execute

        Returns:
            Fill event or None if order rejected
        """
        # Simulate partial fills
        fill_quantity = order.quantity
        if np.random.random() < self.partial_fill_probability:
            fill_quantity = int(order.quantity * np.random.uniform(0.5, 1.0))
            logger.debug(f"Partial fill: {fill_quantity}/{order.quantity}")

        # Calculate fill price with slippage and market impact
        fill_price = self._calculate_fill_price(order, fill_quantity)

        # Calculate commission
        commission = self._calculate_commission(fill_price, fill_quantity)

        fill = FillEvent(
            timestamp=datetime.utcnow(),
            symbol=order.symbol,
            exchange='SIMULATED',
            quantity=fill_quantity if order.direction == 'BUY' else -fill_quantity,
            direction=order.direction,
            fill_price=fill_price,
            commission=commission,
        )

        logger.debug(
            f"Executed {order.direction} {fill_quantity} {order.symbol} "
            f"@ {fill_price:.2f} (commission: {commission:.2f})"
        )

        return fill

    def _calculate_fill_price(self, order: OrderEvent, quantity: int) -> float:
        """
        Calculate realistic fill price with slippage and market impact.

        Args:
            order: Order event
            quantity: Fill quantity

        Returns:
            Fill price
        """
        # Base price (use limit price or market price)
        if order.order_type == 'LMT' and order.price:
            base_price = order.price
        else:
            # In real backtest, this would come from market data
            # For now, use order price or a placeholder
            base_price = order.price if order.price else 100.0

        # Calculate slippage (random within range)
        slippage_factor = np.random.normal(self.slippage_bps / 10000.0, self.slippage_bps / 20000.0)

        # Calculate market impact based on notional value
        notional = abs(quantity * base_price)
        impact_factor = (notional / 1_000_000) * (self.market_impact_bps / 10000.0)

        # Apply slippage and impact (worse price for buyer, better for seller)
        if order.direction == 'BUY':
            fill_price = base_price * (1 + slippage_factor + impact_factor)
        else:
            fill_price = base_price * (1 - slippage_factor - impact_factor)

        return max(fill_price, 0.01)  # Ensure positive price

    def _calculate_commission(self, price: float, quantity: int) -> float:
        """
        Calculate commission for trade.

        Args:
            price: Fill price
            quantity: Trade quantity

        Returns:
            Commission amount
        """
        notional = abs(price * quantity)
        return notional * self.commission_rate
