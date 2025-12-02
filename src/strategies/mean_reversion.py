"""
Mean Reversion Strategy using Bollinger Bands with Risk Management

This strategy trades mean reversion by:
- BUY when price touches lower Bollinger Band (oversold)
- SELL when price touches upper Bollinger Band (overbought)
- EXIT when price returns to middle band (mean)
- Stop-loss: -2% | Take-profit: +3%
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class MeanReversion(Strategy):
    """
    Mean Reversion Strategy using Bollinger Bands with comprehensive risk management

    Entry Logic:
        - LONG: Price touches lower band (2σ) → Expect reversion UP
        - SHORT: Price touches upper band (2σ) → Expect reversion DOWN

    Exit Logic:
        - Price returns to middle band (20 SMA) → EXIT
        - Stop-loss: -2% from entry
        - Take-profit: +3% from entry

    Parameters:
        bb_period: Bollinger Bands period (default: 20)
        bb_std: Number of standard deviations (default: 2.0)
        position_size: Position size fraction (default: 0.15)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Take profit percentage (default: 0.03 = 3%)
        touch_threshold: Threshold for "touching" bands (default: 1.001 = 0.1%)
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        position_size: float = 0.15,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.03,
        touch_threshold: float = 1.001,  # 0.1% threshold for touching bands
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Mean Reversion strategy with risk management

        Args:
            bb_period: Bollinger Bands period
            bb_std: Number of standard deviations
            position_size: Fraction of account per position
            stop_loss_pct: Stop loss as percentage (0.02 = 2%)
            take_profit_pct: Take profit as percentage (0.03 = 3%)
            touch_threshold: Multiplier for band touch detection (1.001 = 0.1% tolerance)
        """
        params = parameters or {}
        params.update({
            'bb_period': bb_period,
            'bb_std': bb_std,
            'position_size': position_size,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'touch_threshold': touch_threshold,
        })

        super().__init__(name="MeanReversion", parameters=params)

        # Track active positions for exit signals
        self.active_positions = {}  # {symbol: {'entry_price': float, 'entry_time': datetime, 'type': 'long'/'short'}}

    def generate_signals_for_symbol(self, symbol: str, data: pd.DataFrame) -> list[Signal]:
        """
        Generate signals for a specific symbol

        Args:
            symbol: Stock symbol
            data: DataFrame with price data for the symbol

        Returns:
            List of Signal objects
        """
        # Set symbol attribute on dataframe
        data = data.copy()
        data.attrs['symbol'] = symbol
        return self.generate_signals(data)

    def generate_signals(self, data: pd.DataFrame, latest_only: bool = True) -> list[Signal]:
        """
        Generate mean reversion signals with exit logic and risk management

        Args:
            data: DataFrame with OHLCV data
            latest_only: If True, only generate signal for the latest bar (default: True)

        Returns list of Signal objects with proper entry/exit logic
        """
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        # Calculate Bollinger Bands
        bb_period = self.get_parameter('bb_period', 20)
        bb_std = self.get_parameter('bb_std', 2.0)

        data['sma_20'] = data['close'].rolling(window=bb_period).mean()
        rolling_std = data['close'].rolling(window=bb_period).std()
        data['upper_band'] = data['sma_20'] + (rolling_std * bb_std)
        data['lower_band'] = data['sma_20'] - (rolling_std * bb_std)

        # Get parameters
        signals = []
        stop_loss_pct = self.get_parameter('stop_loss_pct', 0.02)
        take_profit_pct = self.get_parameter('take_profit_pct', 0.03)
        touch_threshold = self.get_parameter('touch_threshold', 1.001)

        # CRITICAL FIX: Determine range - only process latest bar for live trading
        min_bars = bb_period + 1
        if latest_only and len(data) > min_bars:
            start_idx = len(data) - 1
        else:
            start_idx = min_bars

        for i in range(start_idx, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current['sma_20']) or pd.isna(current['upper_band']):
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # Check for EXIT signals first (stop-loss / take-profit / mean reversion)
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                position_type = position['type']

                # Calculate holding period
                bars_held = i - data.index.get_loc(entry_time)

                # Calculate P&L
                if position_type == 'long':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # short
                    pnl_pct = (entry_price - current_price) / entry_price

                # Check stop-loss and take-profit
                exit_triggered = False
                exit_reason = None

                if pnl_pct <= -stop_loss_pct:
                    exit_triggered = True
                    exit_reason = "stop_loss"
                elif pnl_pct >= take_profit_pct:
                    exit_triggered = True
                    exit_reason = "take_profit"

                # Check mean reversion exit: price returns to middle band
                if not exit_triggered:
                    if position_type == 'long':
                        # Exit long when price reaches or crosses above middle band
                        if current_price >= current['sma_20']:
                            exit_triggered = True
                            exit_reason = "mean_reversion"
                    elif position_type == 'short':
                        # Exit short when price reaches or crosses below middle band
                        if current_price <= current['sma_20']:
                            exit_triggered = True
                            exit_reason = "mean_reversion"

                if exit_triggered:
                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        price=current_price,
                        confidence=1.0,
                        metadata={
                            'exit_reason': exit_reason,
                            'pnl_pct': float(pnl_pct),
                            'entry_price': entry_price,
                            'position_type': position_type,
                            'bars_held': bars_held,
                            'sma_20': float(current['sma_20']),
                            'upper_band': float(current['upper_band']),
                            'lower_band': float(current['lower_band']),
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

            # Generate ENTRY signals only if no active position
            if symbol not in self.active_positions:
                # Long signal: Price touches lower band (oversold, expect reversion UP)
                if current_price <= current['lower_band'] * touch_threshold:
                    signal_type = SignalType.LONG
                    logger.info(
                        f"LONG signal (mean reversion): price={current_price:.2f}, "
                        f"lower_band={current['lower_band']:.2f}, "
                        f"middle={current['sma_20']:.2f}"
                    )

                # Short signal: Price touches upper band (overbought, expect reversion DOWN)
                elif current_price >= current['upper_band'] * (2 - touch_threshold):
                    signal_type = SignalType.SHORT
                    logger.info(
                        f"SHORT signal (mean reversion): price={current_price:.2f}, "
                        f"upper_band={current['upper_band']:.2f}, "
                        f"middle={current['sma_20']:.2f}"
                    )

                if signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Calculate confidence based on distance from middle band
                    bb_width = current['upper_band'] - current['lower_band']
                    distance_from_middle = abs(current_price - current['sma_20'])

                    # Higher confidence when further from mean (more extreme)
                    confidence = min(distance_from_middle / (bb_width / 2), 1.0)
                    confidence = max(confidence, 0.5)  # Floor at 0.5

                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        confidence=float(confidence),
                        metadata={
                            'sma_20': float(current['sma_20']),
                            'upper_band': float(current['upper_band']),
                            'lower_band': float(current['lower_band']),
                            'bb_width': float(bb_width),
                            'distance_from_mean': float(distance_from_middle),
                        }
                    )
                    signals.append(signal)

                    # Track position
                    self.active_positions[symbol] = {
                        'entry_price': current_price,
                        'entry_time': current.name,
                        'type': 'long' if signal_type == SignalType.LONG else 'short',
                    }

        logger.info(
            f"Generated {len(signals)} signals for Mean Reversion strategy "
            f"(including {sum(1 for s in signals if s.signal_type == SignalType.EXIT)} exits)"
        )
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """
        Calculate position size with conservative risk management

        Uses 15% of account value per position by default, scaled by confidence
        """
        position_size_pct = self.get_parameter('position_size', 0.15)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price

        # Scale by confidence
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
