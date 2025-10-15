"""
Order Book Imbalance Strategy

Based on research showing that order book imbalance predicts short-term price movements.
The strategy uses the ratio of bid vs ask volume at various depth levels.

References:
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events
- Cao, C., Hansch, O., & Wang, X. (2009). The information content of an open limit-order book
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


@dataclass
class OrderBookSnapshot:
    """Order book snapshot at a point in time"""
    timestamp: pd.Timestamp
    bids: List[tuple[float, float]]  # List of (price, size)
    asks: List[tuple[float, float]]
    mid_price: float


class OrderBookImbalanceStrategy(Strategy):
    """
    Order book imbalance trading strategy

    The strategy:
    1. Calculates order book imbalance at multiple depth levels
    2. Generates buy signals when bid volume dominates (bullish)
    3. Generates sell signals when ask volume dominates (bearish)

    Parameters:
        depth_levels: Number of order book levels to analyze (default: 5)
        imbalance_threshold: Threshold for signal generation (default: 0.6)
        position_size_pct: Position size as % of account (default: 0.1)
        holding_period: Bars to hold position (default: 5)
    """

    def __init__(
        self,
        name: str = "OrderBookImbalance",
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize order book imbalance strategy"""
        default_params = {
            'depth_levels': 5,
            'imbalance_threshold': 0.6,
            'position_size_pct': 0.1,
            'holding_period': 5,
            'min_spread_bps': 1,  # Minimum spread in basis points
            'max_spread_bps': 50  # Maximum spread in basis points
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, default_params)
        self.entry_bars = {}  # Track when we entered positions

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Generate signals based on order book imbalance

        Args:
            data: DataFrame with columns:
                - close: Price
                - volume: Volume
                - bid_prices_N: Bid prices at level N
                - bid_sizes_N: Bid sizes at level N
                - ask_prices_N: Ask prices at level N
                - ask_sizes_N: Ask sizes at level N

        Returns:
            List of trading signals
        """
        if not self.validate_data(data):
            return []

        signals = []
        symbol = data.attrs.get('symbol', 'UNKNOWN')
        depth = self.get_parameter('depth_levels', 5)
        threshold = self.get_parameter('imbalance_threshold', 0.6)
        holding_period = self.get_parameter('holding_period', 5)

        for i in range(len(data)):
            current_time = data.index[i]
            current_price = data.iloc[i]['close']

            # Check if we should exit existing position
            if symbol in self.entry_bars:
                bars_held = i - self.entry_bars[symbol]
                if bars_held >= holding_period:
                    signals.append(Signal(
                        timestamp=current_time,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=current_price,
                        confidence=0.8,
                        metadata={'reason': 'holding_period_exit'}
                    ))
                    del self.entry_bars[symbol]
                    continue

            # Try to extract order book data
            try:
                bids = self._extract_order_book_side(data.iloc[i], 'bid', depth)
                asks = self._extract_order_book_side(data.iloc[i], 'ask', depth)

                if not bids or not asks:
                    continue

                # Calculate imbalance
                imbalance = self._calculate_imbalance(bids, asks, depth)

                # Check spread
                spread_bps = self._calculate_spread_bps(bids[0][0], asks[0][0])
                min_spread = self.get_parameter('min_spread_bps', 1)
                max_spread = self.get_parameter('max_spread_bps', 50)

                if spread_bps < min_spread or spread_bps > max_spread:
                    continue

                # Generate signals
                if imbalance > threshold and symbol not in self.entry_bars:
                    # Strong bid side - buy signal
                    signals.append(Signal(
                        timestamp=current_time,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=current_price,
                        confidence=min(imbalance, 1.0),
                        metadata={
                            'imbalance': imbalance,
                            'spread_bps': spread_bps,
                            'reason': 'bid_imbalance'
                        }
                    ))
                    self.entry_bars[symbol] = i

                elif imbalance < (1 - threshold) and symbol not in self.entry_bars:
                    # Strong ask side - sell signal
                    signals.append(Signal(
                        timestamp=current_time,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=current_price,
                        confidence=min(1 - imbalance, 1.0),
                        metadata={
                            'imbalance': imbalance,
                            'spread_bps': spread_bps,
                            'reason': 'ask_imbalance'
                        }
                    ))
                    self.entry_bars[symbol] = i

            except Exception as e:
                logger.debug(f"Error processing bar {i}: {e}")
                continue

        logger.info(f"Generated {len(signals)} order book imbalance signals")
        return signals

    def _extract_order_book_side(
        self,
        row: pd.Series,
        side: str,
        depth: int
    ) -> List[tuple[float, float]]:
        """
        Extract order book levels from data row

        Args:
            row: Data row
            side: 'bid' or 'ask'
            depth: Number of levels

        Returns:
            List of (price, size) tuples
        """
        levels = []

        for i in range(depth):
            price_col = f'{side}_price_{i}'
            size_col = f'{side}_size_{i}'

            # Try alternative column names
            if price_col not in row:
                price_col = f'{side}_prices_{i}'
            if size_col not in row:
                size_col = f'{side}_sizes_{i}'

            if price_col in row and size_col in row:
                price = row[price_col]
                size = row[size_col]

                if pd.notna(price) and pd.notna(size) and size > 0:
                    levels.append((float(price), float(size)))

        return levels

    def _calculate_imbalance(
        self,
        bids: List[tuple[float, float]],
        asks: List[tuple[float, float]],
        depth: int
    ) -> float:
        """
        Calculate order book imbalance ratio

        Imbalance = bid_volume / (bid_volume + ask_volume)

        Args:
            bids: List of (price, size) for bids
            asks: List of (price, size) for asks
            depth: Depth to consider

        Returns:
            Imbalance ratio (0-1, 0.5 is balanced)
        """
        # Sum volume at each level
        bid_volume = sum(size for _, size in bids[:depth])
        ask_volume = sum(size for _, size in asks[:depth])

        total_volume = bid_volume + ask_volume

        if total_volume == 0:
            return 0.5  # Neutral

        return bid_volume / total_volume

    def _calculate_spread_bps(self, bid_price: float, ask_price: float) -> float:
        """
        Calculate bid-ask spread in basis points

        Args:
            bid_price: Best bid price
            ask_price: Best ask price

        Returns:
            Spread in basis points
        """
        mid = (bid_price + ask_price) / 2.0
        if mid == 0:
            return 0

        spread = ask_price - bid_price
        return (spread / mid) * 10000  # Convert to bps

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """
        Calculate position size based on confidence and account value

        Args:
            signal: Trading signal
            account_value: Current account value
            current_position: Current position size

        Returns:
            Position size in shares
        """
        position_pct = self.get_parameter('position_size_pct', 0.1)

        # Scale by confidence
        adjusted_pct = position_pct * signal.confidence

        target_value = account_value * adjusted_pct
        shares = target_value / signal.price

        return shares
