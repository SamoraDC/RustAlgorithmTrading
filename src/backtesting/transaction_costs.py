"""
Advanced transaction cost modeling for realistic backtesting

Includes:
- Market impact modeling
- Slippage based on order book depth
- Time-varying spreads
- Commission structures
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class TransactionCost:
    """Complete transaction cost breakdown"""
    commission: float
    slippage: float
    market_impact: float
    total: float
    metadata: Dict[str, Any]


class TransactionCostModel:
    """
    Advanced transaction cost modeling

    Models realistic trading costs including:
    - Fixed and variable commissions
    - Market impact (price movement from order)
    - Slippage (execution price deviation)
    - Bid-ask spread

    Attributes:
        fixed_commission: Fixed cost per trade
        variable_commission_rate: Percentage commission
        min_commission: Minimum commission per trade
        impact_model: Market impact model type
    """

    def __init__(
        self,
        fixed_commission: float = 0.0,
        variable_commission_rate: float = 0.0005,  # 5 bps
        min_commission: float = 1.0,
        impact_coefficient: float = 0.1,
        spread_model: str = 'fixed'
    ):
        """
        Initialize transaction cost model

        Args:
            fixed_commission: Fixed cost per trade
            variable_commission_rate: Variable commission rate
            min_commission: Minimum commission
            impact_coefficient: Market impact sensitivity
            spread_model: Bid-ask spread model ('fixed', 'volume', 'volatility')
        """
        self.fixed_commission = fixed_commission
        self.variable_commission_rate = variable_commission_rate
        self.min_commission = min_commission
        self.impact_coefficient = impact_coefficient
        self.spread_model = spread_model

        logger.info(
            f"TransactionCostModel initialized: "
            f"fixed=${fixed_commission}, rate={variable_commission_rate:.4f}, "
            f"impact_coef={impact_coefficient}"
        )

    def calculate_cost(
        self,
        price: float,
        quantity: float,
        side: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> TransactionCost:
        """
        Calculate total transaction costs for an order

        Args:
            price: Order price
            quantity: Order quantity (shares)
            side: 'buy' or 'sell'
            market_data: Additional market data (volume, volatility, etc.)

        Returns:
            TransactionCost object with breakdown
        """
        market_data = market_data or {}

        # Calculate commission
        commission = self._calculate_commission(price, quantity)

        # Calculate slippage
        slippage = self._calculate_slippage(price, quantity, side, market_data)

        # Calculate market impact
        market_impact = self._calculate_market_impact(price, quantity, market_data)

        total = commission + slippage + market_impact

        return TransactionCost(
            commission=commission,
            slippage=slippage,
            market_impact=market_impact,
            total=total,
            metadata={
                'price': price,
                'quantity': quantity,
                'side': side,
                'notional': price * quantity
            }
        )

    def _calculate_commission(self, price: float, quantity: float) -> float:
        """
        Calculate commission cost

        Args:
            price: Order price
            quantity: Order quantity

        Returns:
            Commission cost in dollars
        """
        notional = price * quantity
        variable = notional * self.variable_commission_rate
        total = self.fixed_commission + variable

        return max(total, self.min_commission)

    def _calculate_slippage(
        self,
        price: float,
        quantity: float,
        side: str,
        market_data: Dict[str, Any]
    ) -> float:
        """
        Calculate slippage cost based on spread and order size

        Args:
            price: Order price
            quantity: Order quantity
            side: 'buy' or 'sell'
            market_data: Market data including spread info

        Returns:
            Slippage cost in dollars
        """
        # Get spread
        spread = self._get_spread(price, market_data)

        # Half spread for crossing
        half_spread = spread / 2.0

        # Additional slippage based on order size
        avg_volume = market_data.get('avg_volume', 1000000)
        volume_ratio = quantity / avg_volume if avg_volume > 0 else 0.01

        # Larger orders get worse slippage
        size_penalty = min(volume_ratio * 0.1, 0.02)  # Cap at 2%

        total_slippage_pct = half_spread + size_penalty

        return quantity * price * total_slippage_pct

    def _calculate_market_impact(
        self,
        price: float,
        quantity: float,
        market_data: Dict[str, Any]
    ) -> float:
        """
        Calculate market impact using square-root model

        Market impact follows: impact = σ * (Q/V)^0.5
        where σ is volatility, Q is order size, V is average volume

        Args:
            price: Order price
            quantity: Order quantity
            market_data: Market data including volume and volatility

        Returns:
            Market impact cost in dollars
        """
        # Get market parameters
        avg_volume = market_data.get('avg_volume', 1000000)
        volatility = market_data.get('volatility', 0.02)  # Default 2% daily vol

        # Volume ratio
        volume_ratio = quantity / avg_volume if avg_volume > 0 else 0.01

        # Square-root impact model
        impact_pct = self.impact_coefficient * volatility * np.sqrt(volume_ratio)

        return quantity * price * impact_pct

    def _get_spread(self, price: float, market_data: Dict[str, Any]) -> float:
        """
        Calculate bid-ask spread based on model

        Args:
            price: Current price
            market_data: Market data

        Returns:
            Spread as percentage
        """
        if self.spread_model == 'fixed':
            # Fixed spread (10 bps)
            return 0.001

        elif self.spread_model == 'volume':
            # Spread inversely proportional to volume
            avg_volume = market_data.get('avg_volume', 1000000)
            base_spread = 0.001
            volume_factor = 1000000 / max(avg_volume, 100000)
            return base_spread * volume_factor

        elif self.spread_model == 'volatility':
            # Spread proportional to volatility
            volatility = market_data.get('volatility', 0.02)
            return volatility * 0.1  # 10% of daily volatility

        else:
            return 0.001


class OrderBookSlippageModel:
    """
    Slippage model based on order book depth

    Uses actual order book data to simulate realistic execution
    """

    def __init__(self, depth_levels: int = 10):
        """
        Initialize order book slippage model

        Args:
            depth_levels: Number of order book levels to consider
        """
        self.depth_levels = depth_levels
        logger.info(f"OrderBookSlippageModel initialized with {depth_levels} levels")

    def calculate_execution_price(
        self,
        order_quantity: float,
        side: str,
        order_book: Dict[str, List[tuple]]
    ) -> tuple[float, float]:
        """
        Calculate execution price by walking the order book

        Args:
            order_quantity: Quantity to execute
            side: 'buy' or 'sell'
            order_book: Dict with 'bids' and 'asks' as list of (price, size) tuples

        Returns:
            Tuple of (average_execution_price, slippage_cost)
        """
        # Select appropriate side
        levels = order_book['asks'] if side == 'buy' else order_book['bids']

        remaining = order_quantity
        total_cost = 0.0

        for price, size in levels[:self.depth_levels]:
            if remaining <= 0:
                break

            fill_qty = min(remaining, size)
            total_cost += fill_qty * price
            remaining -= fill_qty

        if remaining > 0:
            # Not enough liquidity - use last price with penalty
            last_price = levels[-1][0] if levels else 0
            penalty = 1.02 if side == 'buy' else 0.98
            total_cost += remaining * last_price * penalty

        avg_price = total_cost / order_quantity if order_quantity > 0 else 0

        # Best price for comparison
        best_price = levels[0][0] if levels else avg_price
        slippage = abs(avg_price - best_price) * order_quantity

        return avg_price, slippage
