"""
Momentum Strategy using RSI and MACD with Risk Management
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class MomentumStrategy(Strategy):
    """
    Momentum Strategy using RSI and MACD indicators with comprehensive risk management

    Generates signals based on momentum indicators alignment with proper exit logic,
    stop-loss, and take-profit mechanisms.

    Parameters:
        rsi_period: RSI period (default: 14)
        rsi_oversold: RSI oversold level (default: 30)
        rsi_overbought: RSI overbought level (default: 70)
        ema_fast: Fast EMA period for MACD (default: 12)
        ema_slow: Slow EMA period for MACD (default: 26)
        macd_signal: MACD signal line period (default: 9)
        position_size: Position size fraction (default: 0.15)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Take profit percentage (default: 0.03 = 3% for 1.5:1 ratio)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        position_size: float = 0.15,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.03,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Momentum strategy with risk management"""
        params = parameters or {}
        params.update({
            'rsi_period': rsi_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'macd_signal': macd_signal,
            'position_size': position_size,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
        })

        super().__init__(name="MomentumStrategy", parameters=params)

        # Track active positions for exit signals
        self.active_positions = {}  # {symbol: {'entry_price': float, 'entry_time': datetime, 'type': 'long'/'short'}}

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate momentum-based signals with exit logic and risk management"""
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

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
        macd_signal_period = self.get_parameter('macd_signal', 9)

        data['ema_fast'] = data['close'].ewm(span=ema_fast, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=ema_slow, adjust=False).mean()
        data['macd'] = data['ema_fast'] - data['ema_slow']
        data['macd_signal'] = data['macd'].ewm(span=macd_signal_period, adjust=False).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']

        # Get parameters
        signals = []
        rsi_oversold = self.get_parameter('rsi_oversold', 30)
        rsi_overbought = self.get_parameter('rsi_overbought', 70)
        stop_loss_pct = self.get_parameter('stop_loss_pct', 0.02)
        take_profit_pct = self.get_parameter('take_profit_pct', 0.03)

        for i in range(max(rsi_period, ema_slow, macd_signal_period) + 1, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current['rsi']) or pd.isna(current['macd']):
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # Check for EXIT signals first (stop-loss / take-profit)
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                entry_price = position['entry_price']
                position_type = position['type']

                # Calculate P&L
                if position_type == 'long':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # short
                    pnl_pct = (entry_price - current_price) / entry_price

                # Check stop-loss or take-profit
                if pnl_pct <= -stop_loss_pct or pnl_pct >= take_profit_pct:
                    signal_type = SignalType.EXIT
                    exit_reason = "stop_loss" if pnl_pct <= -stop_loss_pct else "take_profit"

                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        confidence=1.0,
                        metadata={
                            'exit_reason': exit_reason,
                            'pnl_pct': float(pnl_pct),
                            'entry_price': entry_price,
                            'position_type': position_type,
                            'rsi': float(current['rsi']),
                            'macd': float(current['macd']),
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

                # Check for technical exit signals (momentum reversal)
                if position_type == 'long':
                    # Exit long if RSI becomes overbought and MACD turns down
                    if (current['rsi'] > rsi_overbought and
                        current['macd'] < current['macd_signal'] and
                        previous['macd'] >= previous['macd_signal']):
                        signal_type = SignalType.EXIT
                elif position_type == 'short':
                    # Exit short if RSI becomes oversold and MACD turns up
                    if (current['rsi'] < rsi_oversold and
                        current['macd'] > current['macd_signal'] and
                        previous['macd'] <= previous['macd_signal']):
                        signal_type = SignalType.EXIT

                if signal_type == SignalType.EXIT:
                    pnl_pct = (current_price - entry_price) / entry_price if position_type == 'long' else (entry_price - current_price) / entry_price
                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        confidence=0.8,
                        metadata={
                            'exit_reason': 'technical',
                            'pnl_pct': float(pnl_pct),
                            'entry_price': entry_price,
                            'position_type': position_type,
                            'rsi': float(current['rsi']),
                            'macd': float(current['macd']),
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

            # Generate ENTRY signals only if no active position
            if symbol not in self.active_positions:
                # Long signal: RSI rising from oversold + MACD bullish
                if (current['rsi'] > rsi_oversold and
                    previous['rsi'] <= rsi_oversold and
                    current['macd'] > current['macd_signal']):
                    signal_type = SignalType.LONG

                # Short signal: RSI falling from overbought + MACD bearish
                elif (current['rsi'] < rsi_overbought and
                      previous['rsi'] >= rsi_overbought and
                      current['macd'] < current['macd_signal']):
                    signal_type = SignalType.SHORT

                if signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Calculate confidence based on indicator strength
                    rsi_strength = abs(current['rsi'] - 50) / 50  # 0 to 1
                    macd_strength = min(abs(current['macd_histogram']) / (current['close'] * 0.01), 1.0)
                    confidence = min((rsi_strength * 0.6 + macd_strength * 0.4), 1.0)

                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        confidence=float(confidence),
                        metadata={
                            'rsi': float(current['rsi']),
                            'macd': float(current['macd']),
                            'macd_signal': float(current['macd_signal']),
                            'macd_histogram': float(current['macd_histogram']),
                        }
                    )
                    signals.append(signal)

                    # Track position
                    self.active_positions[symbol] = {
                        'entry_price': current_price,
                        'entry_time': current.name,
                        'type': 'long' if signal_type == SignalType.LONG else 'short'
                    }

        logger.info(f"Generated {len(signals)} signals for Momentum strategy (including {sum(1 for s in signals if s.signal_type == SignalType.EXIT)} exits)")
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """
        Calculate position size with conservative risk management

        Uses 15% of account value per position, scaled by confidence
        """
        position_size_pct = self.get_parameter('position_size', 0.15)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price
        shares *= signal.confidence
        return round(shares, 2)

    def get_unrealized_pnl(self, symbol: str, current_price: float) -> Optional[float]:
        """
        Calculate unrealized P&L for an active position

        Args:
            symbol: Stock symbol
            current_price: Current market price

        Returns:
            P&L percentage or None if no position
        """
        if symbol not in self.active_positions:
            return None

        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        position_type = position['type']

        if position_type == 'long':
            return (current_price - entry_price) / entry_price
        else:  # short
            return (entry_price - current_price) / entry_price
