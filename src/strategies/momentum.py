"""
Momentum Strategy using RSI and MACD
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class MomentumStrategy(Strategy):
    """
    Momentum Strategy using RSI and MACD indicators

    Generates signals based on momentum indicators alignment

    Parameters:
        rsi_period: RSI period (default: 14)
        rsi_oversold: RSI oversold level (default: 40)
        rsi_overbought: RSI overbought level (default: 60)
        ema_fast: Fast EMA period for MACD (default: 12)
        ema_slow: Slow EMA period for MACD (default: 26)
        macd_signal: MACD signal line period (default: 9)
        position_size: Position size fraction (default: 0.95)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 40,
        rsi_overbought: float = 60,
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        position_size: float = 0.95,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Momentum strategy"""
        params = parameters or {}
        params.update({
            'rsi_period': rsi_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'macd_signal': macd_signal,
            'position_size': position_size,
        })

        super().__init__(name="MomentumStrategy", parameters=params)

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate momentum-based signals"""
        if not self.validate_data(data):
            return []

        data = data.copy()

        # Calculate RSI
        rsi_period = self.get_parameter('rsi_period', 14)
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))

        # Calculate MACD
        ema_fast = self.get_parameter('ema_fast', 12)
        ema_slow = self.get_parameter('ema_slow', 26)
        macd_signal = self.get_parameter('macd_signal', 9)

        data['ema_fast'] = data['close'].ewm(span=ema_fast, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=ema_slow, adjust=False).mean()
        data['macd'] = data['ema_fast'] - data['ema_slow']
        data['macd_signal'] = data['macd'].ewm(span=macd_signal, adjust=False).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']

        # Generate signals
        signals = []
        rsi_oversold = self.get_parameter('rsi_oversold', 40)
        rsi_overbought = self.get_parameter('rsi_overbought', 60)

        for i in range(max(rsi_period, ema_slow, macd_signal) + 1, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current['rsi']) or pd.isna(current['macd']):
                continue

            signal_type = SignalType.HOLD

            # Buy signal: RSI rising from oversold + MACD crosses above signal
            if (current['rsi'] > rsi_oversold and
                previous['rsi'] <= rsi_oversold and
                current['macd'] > current['macd_signal'] and
                previous['macd'] <= previous['macd_signal']):
                signal_type = SignalType.BUY

            # Sell signal: RSI falling from overbought + MACD crosses below signal
            elif (current['rsi'] < rsi_overbought and
                  previous['rsi'] >= rsi_overbought and
                  current['macd'] < current['macd_signal'] and
                  previous['macd'] >= previous['macd_signal']):
                signal_type = SignalType.SELL

            if signal_type != SignalType.HOLD:
                # Calculate confidence based on indicator strength
                rsi_strength = abs(current['rsi'] - 50) / 50  # 0 to 1
                macd_strength = abs(current['macd_histogram']) / current['close']
                confidence = min((rsi_strength + macd_strength) / 2, 1.0)

                signal = Signal(
                    timestamp=current.name,
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type=signal_type,
                    price=float(current['close']),
                    confidence=float(confidence),
                    metadata={
                        'rsi': float(current['rsi']),
                        'macd': float(current['macd']),
                        'macd_signal': float(current['macd_signal']),
                        'macd_histogram': float(current['macd_histogram']),
                    }
                )
                signals.append(signal)

        logger.info(f"Generated {len(signals)} signals for Momentum strategy")
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
