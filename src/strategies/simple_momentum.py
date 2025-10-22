"""
Simple Momentum Strategy for Backtesting

Simplified wrapper around MomentumStrategy for easy backtesting integration.
Uses default RSI and MACD parameters optimized for paper trading.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from loguru import logger

from .momentum import MomentumStrategy
from .base import Strategy, Signal


class SimpleMomentumStrategy(MomentumStrategy):
    """
    Simplified Momentum Strategy for backtesting.

    This strategy wraps the full MomentumStrategy with simplified parameters
    optimized for backtesting and paper trading.

    Parameters:
        symbols: List of trading symbols
        rsi_period: RSI lookback period (default: 14)
        rsi_oversold: RSI oversold threshold (default: 35)
        rsi_overbought: RSI overbought threshold (default: 65)
        position_size: Position sizing as fraction of capital (default: 0.1 = 10%)
    """

    def __init__(
        self,
        symbols: List[str],
        rsi_period: int = 14,
        rsi_oversold: float = 35,
        rsi_overbought: float = 65,
        position_size: float = 0.1
    ):
        """
        Initialize Simple Momentum Strategy

        Args:
            symbols: List of symbols to trade
            rsi_period: RSI calculation period
            rsi_oversold: RSI oversold level for buy signals
            rsi_overbought: RSI overbought level for sell signals
            position_size: Position size as fraction of account (0.1 = 10%)
        """
        # Store symbols for multi-symbol backtesting
        self.symbols = symbols

        # Initialize parent MomentumStrategy with optimized parameters
        super().__init__(
            rsi_period=rsi_period,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought,
            ema_fast=12,  # Standard MACD fast period
            ema_slow=26,  # Standard MACD slow period
            macd_signal=9,  # Standard MACD signal period
            position_size=position_size
        )

        # Update name to reflect simplified version
        self.name = "SimpleMomentumStrategy"

        logger.info(
            f"SimpleMomentumStrategy initialized for symbols: {symbols} "
            f"(RSI: {rsi_period}, Oversold: {rsi_oversold}, Overbought: {rsi_overbought}, "
            f"Position: {position_size*100}%)"
        )

    def get_symbols(self) -> List[str]:
        """Get list of symbols this strategy trades"""
        return self.symbols

    def generate_signals_for_symbol(self, symbol: str, data: pd.DataFrame) -> List[Signal]:
        """
        Generate signals for a specific symbol

        Args:
            symbol: Trading symbol
            data: OHLCV data for the symbol

        Returns:
            List of trading signals
        """
        # Set symbol metadata in dataframe
        data = data.copy()
        data.attrs['symbol'] = symbol

        # Use parent's signal generation logic
        return self.generate_signals(data)

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """
        Calculate position size for a signal

        Overrides parent to add additional safety checks for backtesting.

        Args:
            signal: Trading signal
            account_value: Current account value
            current_position: Current position in shares

        Returns:
            Position size in shares
        """
        # Get base position size from parent
        position_shares = super().calculate_position_size(signal, account_value, current_position)

        # Additional safety: Don't over-leverage
        max_position_value = account_value * self.get_parameter('position_size', 0.1)
        max_shares = max_position_value / signal.price

        # Return minimum of calculated and max allowed
        final_shares = min(abs(position_shares), max_shares)

        # Maintain sign (long vs short)
        if position_shares < 0:
            final_shares = -final_shares

        return round(final_shares, 2)

    def __repr__(self) -> str:
        return (
            f"SimpleMomentumStrategy(symbols={self.symbols}, "
            f"rsi_period={self.get_parameter('rsi_period')}, "
            f"position_size={self.get_parameter('position_size')})"
        )
