"""
Mean Reversion Strategy using Bollinger Bands
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class MeanReversion(Strategy):
    """
    Mean Reversion Strategy using Bollinger Bands

    Generates BUY signal when price touches lower band
    Generates SELL signal when price touches upper band

    Parameters:
        bb_period: Bollinger Bands period (default: 20)
        bb_std: Number of standard deviations (default: 2)
        rsi_period: RSI period for confirmation (default: 14)
        rsi_oversold: RSI oversold threshold (default: 30)
        rsi_overbought: RSI overbought threshold (default: 70)
        position_size: Position size as fraction of account (default: 0.95)
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        position_size: float = 0.95,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Mean Reversion strategy"""
        params = parameters or {}
        params.update({
            'bb_period': bb_period,
            'bb_std': bb_std,
            'rsi_period': rsi_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'position_size': position_size,
        })

        super().__init__(name="MeanReversion", parameters=params)

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate mean reversion signals"""
        if not self.validate_data(data):
            return []

        data = data.copy()

        # Calculate Bollinger Bands
        bb_period = self.get_parameter('bb_period', 20)
        bb_std = self.get_parameter('bb_std', 2.0)

        data['bb_middle'] = data['close'].rolling(window=bb_period).mean()
        rolling_std = data['close'].rolling(window=bb_period).std()
        data['bb_upper'] = data['bb_middle'] + (rolling_std * bb_std)
        data['bb_lower'] = data['bb_middle'] - (rolling_std * bb_std)

        # Calculate RSI
        rsi_period = self.get_parameter('rsi_period', 14)
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))

        # Generate signals
        signals = []
        rsi_oversold = self.get_parameter('rsi_oversold', 30)
        rsi_overbought = self.get_parameter('rsi_overbought', 70)

        for i in range(bb_period + rsi_period, len(data)):
            current = data.iloc[i]

            if pd.isna(current['bb_lower']) or pd.isna(current['rsi']):
                continue

            signal_type = SignalType.HOLD

            # Long signal: price at/below lower band and RSI oversold
            if (current['close'] <= current['bb_lower'] and
                current['rsi'] <= rsi_oversold):
                signal_type = SignalType.LONG

            # Short signal: price at/above upper band and RSI overbought
            elif (current['close'] >= current['bb_upper'] and
                  current['rsi'] >= rsi_overbought):
                signal_type = SignalType.SHORT

            if signal_type != SignalType.HOLD:
                # Calculate confidence based on how far from mean
                bb_width = current['bb_upper'] - current['bb_lower']
                distance_from_middle = abs(current['close'] - current['bb_middle'])
                confidence = min(distance_from_middle / (bb_width / 2), 1.0)

                signal = Signal(
                    timestamp=current.name,
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type=signal_type,
                    price=float(current['close']),
                    confidence=float(confidence),
                    metadata={
                        'bb_upper': float(current['bb_upper']),
                        'bb_middle': float(current['bb_middle']),
                        'bb_lower': float(current['bb_lower']),
                        'rsi': float(current['rsi']),
                    }
                )
                signals.append(signal)

        logger.info(f"Generated {len(signals)} signals for Mean Reversion strategy")
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size"""
        position_size_pct = self.get_parameter('position_size', 0.95)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price
        shares *= signal.confidence
        return round(shares, 2)
