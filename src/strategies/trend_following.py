"""
Trend Following Strategy using ADX + Multiple EMAs

This strategy captures strong trends by:
- Identifying trend strength with ADX (Average Directional Index)
- Using EMA crossovers for entry timing (9/21/50)
- Following trends until exhaustion
- Stop-loss: -2.5% | Take-profit: +5% (wider for trend capture)
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class TrendFollowingStrategy(Strategy):
    """
    Trend Following Strategy using ADX and EMA crossovers

    Entry Logic:
        - LONG: ADX > 25 (strong trend) + 9 EMA > 21 EMA > 50 EMA (bullish alignment)
        - SHORT: ADX > 25 (strong trend) + 9 EMA < 21 EMA < 50 EMA (bearish alignment)

    Exit Logic:
        - ADX < 20 (trend weakening)
        - EMA crossover reversal
        - Stop-loss: -2.5%
        - Take-profit: +5%

    Parameters:
        ema_fast: Fast EMA period (default: 9)
        ema_medium: Medium EMA period (default: 21)
        ema_slow: Slow EMA period (default: 50)
        adx_period: ADX period (default: 14)
        adx_threshold: Minimum ADX for trend (default: 25)
        position_size: Position size fraction (default: 0.20 - higher for trends)
        stop_loss_pct: Stop loss percentage (default: 0.025 = 2.5%)
        take_profit_pct: Take profit percentage (default: 0.05 = 5%)
        min_holding_period: Minimum bars to hold (default: 15)
    """

    def __init__(
        self,
        ema_fast: int = 9,
        ema_medium: int = 21,
        ema_slow: int = 50,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        position_size: float = 0.20,
        stop_loss_pct: float = 0.025,
        take_profit_pct: float = 0.05,
        min_holding_period: int = 15,
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.02,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Trend Following strategy"""
        params = parameters or {}
        params.update({
            'ema_fast': ema_fast,
            'ema_medium': ema_medium,
            'ema_slow': ema_slow,
            'adx_period': adx_period,
            'adx_threshold': adx_threshold,
            'position_size': position_size,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'min_holding_period': min_holding_period,
            'use_trailing_stop': use_trailing_stop,
            'trailing_stop_pct': trailing_stop_pct,
        })

        super().__init__(name="TrendFollowing", parameters=params)

        # Track active positions
        self.active_positions = {}

    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate ADX (Average Directional Index)"""
        df = data.copy()

        # True Range
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)

        # Directional Movement
        df['dm_plus'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0),
            0
        )
        df['dm_minus'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0),
            0
        )

        # Smoothed TR and DM
        df['tr_smooth'] = df['tr'].rolling(window=period).sum()
        df['dm_plus_smooth'] = df['dm_plus'].rolling(window=period).sum()
        df['dm_minus_smooth'] = df['dm_minus'].rolling(window=period).sum()

        # Directional Indicators
        df['di_plus'] = 100 * (df['dm_plus_smooth'] / df['tr_smooth'])
        df['di_minus'] = 100 * (df['dm_minus_smooth'] / df['tr_smooth'])

        # DX and ADX
        df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
        df['adx'] = df['dx'].rolling(window=period).mean()

        return df

    def generate_signals(self, data: pd.DataFrame, latest_only: bool = True) -> list[Signal]:
        """Generate trend following signals

        Args:
            data: DataFrame with OHLCV data
            latest_only: If True, only generate signal for the latest bar (default: True)
        """
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        # Calculate EMAs
        ema_fast = self.get_parameter('ema_fast', 9)
        ema_medium = self.get_parameter('ema_medium', 21)
        ema_slow = self.get_parameter('ema_slow', 50)
        adx_period = self.get_parameter('adx_period', 14)

        data['ema_fast'] = data['close'].ewm(span=ema_fast, adjust=False).mean()
        data['ema_medium'] = data['close'].ewm(span=ema_medium, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=ema_slow, adjust=False).mean()

        # Calculate ADX
        data = self.calculate_adx(data, period=adx_period)

        signals = []
        stop_loss_pct = self.get_parameter('stop_loss_pct', 0.025)
        take_profit_pct = self.get_parameter('take_profit_pct', 0.05)
        min_holding_period = self.get_parameter('min_holding_period', 15)
        adx_threshold = self.get_parameter('adx_threshold', 25.0)

        # CRITICAL FIX: Determine range - only process latest bar for live trading
        min_bars = max(ema_slow, adx_period * 2) + 1
        if latest_only and len(data) > min_bars:
            start_idx = len(data) - 1
        else:
            start_idx = min_bars

        for i in range(start_idx, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current['adx']) or pd.isna(current['ema_slow']):
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # Check for EXIT signals
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                position_type = position['type']

                # Track highest/lowest for trailing stops
                use_trailing_stop = self.get_parameter('use_trailing_stop', True)
                if use_trailing_stop:
                    if position_type == 'long':
                        highest_price = position.get('highest_price', entry_price)
                        highest_price = max(highest_price, current_price)
                        self.active_positions[symbol]['highest_price'] = highest_price
                    else:
                        lowest_price = position.get('lowest_price', entry_price)
                        lowest_price = min(lowest_price, current_price)
                        self.active_positions[symbol]['lowest_price'] = lowest_price

                bars_held = i - data.index.get_loc(entry_time)

                # Calculate P&L
                if position_type == 'long':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price

                exit_triggered = False
                exit_reason = None

                # Stop-loss (immediate)
                if pnl_pct <= -stop_loss_pct:
                    exit_triggered = True
                    exit_reason = "stop_loss"

                # Trailing stop
                elif use_trailing_stop:
                    trailing_stop_pct = self.get_parameter('trailing_stop_pct', 0.02)
                    if position_type == 'long':
                        if current_price < highest_price * (1 - trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop"
                    else:
                        if current_price > lowest_price * (1 + trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop"

                # Take-profit (after holding period)
                if not exit_triggered and bars_held >= min_holding_period:
                    if pnl_pct >= take_profit_pct:
                        exit_triggered = True
                        exit_reason = "take_profit"

                # Trend weakness exit (ADX drops below 20)
                if not exit_triggered and bars_held >= min_holding_period:
                    if current['adx'] < 20:
                        exit_triggered = True
                        exit_reason = "trend_weakness"

                # EMA reversal exit
                if not exit_triggered and bars_held >= min_holding_period:
                    if position_type == 'long':
                        # Exit if fast EMA crosses below medium EMA
                        if current['ema_fast'] < current['ema_medium'] and previous['ema_fast'] >= previous['ema_medium']:
                            exit_triggered = True
                            exit_reason = "ema_reversal"
                    else:
                        # Exit if fast EMA crosses above medium EMA
                        if current['ema_fast'] > current['ema_medium'] and previous['ema_fast'] <= previous['ema_medium']:
                            exit_triggered = True
                            exit_reason = "ema_reversal"

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
                            'adx': float(current['adx']),
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

            # Generate ENTRY signals (only if no active position)
            if symbol not in self.active_positions:
                # Check ADX for strong trend
                if current['adx'] < adx_threshold:
                    continue

                # LONG: Strong uptrend with EMA alignment
                long_ema_aligned = (
                    current['ema_fast'] > current['ema_medium'] and
                    current['ema_medium'] > current['ema_slow']
                )
                long_crossover = (
                    current['ema_fast'] > current['ema_medium'] and
                    previous['ema_fast'] <= previous['ema_medium']
                )

                if long_ema_aligned or long_crossover:
                    signal_type = SignalType.LONG
                    logger.info(
                        f"LONG (trend): ADX={current['adx']:.1f}, "
                        f"EMAs: {current['ema_fast']:.2f} > {current['ema_medium']:.2f} > {current['ema_slow']:.2f}"
                    )

                # SHORT: Strong downtrend with EMA alignment
                short_ema_aligned = (
                    current['ema_fast'] < current['ema_medium'] and
                    current['ema_medium'] < current['ema_slow']
                )
                short_crossover = (
                    current['ema_fast'] < current['ema_medium'] and
                    previous['ema_fast'] >= previous['ema_medium']
                )

                if short_ema_aligned or short_crossover:
                    signal_type = SignalType.SHORT
                    logger.info(
                        f"SHORT (trend): ADX={current['adx']:.1f}, "
                        f"EMAs: {current['ema_fast']:.2f} < {current['ema_medium']:.2f} < {current['ema_slow']:.2f}"
                    )

                if signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Calculate confidence based on ADX strength
                    adx_strength = min((current['adx'] - adx_threshold) / (50 - adx_threshold), 1.0)
                    confidence = max(0.6, adx_strength)

                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        confidence=float(confidence),
                        metadata={
                            'adx': float(current['adx']),
                            'ema_fast': float(current['ema_fast']),
                            'ema_medium': float(current['ema_medium']),
                            'ema_slow': float(current['ema_slow']),
                            'di_plus': float(current['di_plus']),
                            'di_minus': float(current['di_minus']),
                        }
                    )
                    signals.append(signal)

                    # Track position
                    self.active_positions[symbol] = {
                        'entry_price': current_price,
                        'entry_time': current.name,
                        'type': 'long' if signal_type == SignalType.LONG else 'short',
                        'highest_price': current_price,
                        'lowest_price': current_price,
                    }

        logger.info(f"Generated {len(signals)} signals for Trend Following strategy")
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size with confidence scaling"""
        position_size_pct = self.get_parameter('position_size', 0.20)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price
        shares *= signal.confidence
        return round(shares, 2)
