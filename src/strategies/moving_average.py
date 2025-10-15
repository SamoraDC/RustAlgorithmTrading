"""
Moving Average Crossover Strategy
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class MovingAverageCrossover(Strategy):
    """
    Moving Average Crossover Strategy

    Generates BUY signal when fast MA crosses above slow MA
    Generates SELL signal when fast MA crosses below slow MA

    Parameters:
        fast_period: Fast moving average period (default: 20)
        slow_period: Slow moving average period (default: 50)
        position_size: Position size as fraction of account (default: 0.95)
    """

    def __init__(
        self,
        fast_period: int = 20,
        slow_period: int = 50,
        position_size: float = 0.95,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Moving Average Crossover strategy

        Args:
            fast_period: Fast MA period
            slow_period: Slow MA period
            position_size: Position size fraction
            parameters: Additional parameters
        """
        params = parameters or {}
        params.update({
            'fast_period': fast_period,
            'slow_period': slow_period,
            'position_size': position_size,
        })

        super().__init__(name="MovingAverageCrossover", parameters=params)

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """
        Generate crossover signals

        Args:
            data: DataFrame with OHLCV data

        Returns:
            List of trading signals
        """
        if not self.validate_data(data):
            return []

        data = data.copy()
        fast_period = self.get_parameter('fast_period', 20)
        slow_period = self.get_parameter('slow_period', 50)

        # Calculate moving averages
        data['fast_ma'] = data['close'].rolling(window=fast_period).mean()
        data['slow_ma'] = data['close'].rolling(window=slow_period).mean()

        # Generate signals
        signals = []

        for i in range(slow_period, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            # Skip if NaN values
            if pd.isna(current['fast_ma']) or pd.isna(current['slow_ma']):
                continue

            signal_type = SignalType.HOLD

            # Bullish crossover (fast crosses above slow)
            if (previous['fast_ma'] <= previous['slow_ma'] and
                current['fast_ma'] > current['slow_ma']):
                signal_type = SignalType.BUY

            # Bearish crossover (fast crosses below slow)
            elif (previous['fast_ma'] >= previous['slow_ma'] and
                  current['fast_ma'] < current['slow_ma']):
                signal_type = SignalType.SELL

            if signal_type != SignalType.HOLD:
                # Calculate signal confidence based on MA separation
                ma_diff = abs(current['fast_ma'] - current['slow_ma'])
                confidence = min(ma_diff / current['close'], 1.0)

                signal = Signal(
                    timestamp=current.name,
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type=signal_type,
                    price=float(current['close']),
                    confidence=float(confidence),
                    metadata={
                        'fast_ma': float(current['fast_ma']),
                        'slow_ma': float(current['slow_ma']),
                        'ma_diff': float(ma_diff),
                    }
                )
                signals.append(signal)

        logger.info(f"Generated {len(signals)} signals for MA Crossover strategy")
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """
        Calculate position size based on account value

        Args:
            signal: Trading signal
            account_value: Current account value
            current_position: Current position size

        Returns:
            Suggested position size (number of shares)
        """
        position_size_pct = self.get_parameter('position_size', 0.95)
        position_value = account_value * position_size_pct

        # Calculate number of shares
        shares = position_value / signal.price

        # Adjust for signal confidence
        shares *= signal.confidence

        return round(shares, 2)
