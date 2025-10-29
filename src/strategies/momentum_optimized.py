"""
Optimized Momentum Strategy - Parameter Tuned for Better Performance

Key Optimizations:
- Stop-loss: 3% (from 2%) - Less noise-induced exits
- Take-profit: 5% (from 3%) - Let winners run longer
- RSI thresholds: 45/55 (from 50) - Catch momentum earlier
- MACD histogram: 0.0003 (from 0.0005) - More sensitive to momentum shifts
- Minimum holding: 5 bars (from 10) - Faster exits when needed
- Volume filter: DISABLED - Was too restrictive
- SMA filter: DISABLED temporarily - Testing if over-optimized
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class MomentumOptimizedStrategy(Strategy):
    """
    Optimized Momentum Strategy with relaxed parameters for better trade generation

    Target Metrics:
    - Win rate: >35% (from 0%)
    - Trades: 15-30 (from 5)
    - Return: >0% (from negative)

    Parameters:
        rsi_period: RSI period (default: 14)
        rsi_buy_threshold: RSI buy threshold (default: 45, was 50)
        rsi_sell_threshold: RSI sell threshold (default: 55, was 50)
        ema_fast: Fast EMA period for MACD (default: 12)
        ema_slow: Slow EMA period for MACD (default: 26)
        macd_signal: MACD signal line period (default: 9)
        position_size: Position size fraction (default: 0.15)
        stop_loss_pct: Stop loss percentage (default: 0.03 = 3%, was 2%)
        take_profit_pct: Take profit percentage (default: 0.05 = 5%, was 3%)
        macd_histogram_threshold: MACD histogram threshold (default: 0.0003, was 0.0005)
        min_holding_period: Minimum bars to hold (default: 5, was 10)
        volume_confirmation: Volume filter DISABLED (default: False)
        use_sma_filter: SMA trend filter DISABLED temporarily (default: False)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_buy_threshold: float = 45,  # OPTIMIZED: Lower threshold to catch momentum earlier
        rsi_sell_threshold: float = 55,  # OPTIMIZED: Higher threshold for shorts
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        position_size: float = 0.15,
        stop_loss_pct: float = 0.03,  # OPTIMIZED: 3% (from 2%) - less noise
        take_profit_pct: float = 0.05,  # OPTIMIZED: 5% (from 3%) - let winners run
        macd_histogram_threshold: float = 0.0003,  # OPTIMIZED: More sensitive (from 0.0005)
        min_holding_period: int = 5,  # OPTIMIZED: Faster exits (from 10)
        volume_confirmation: bool = False,  # OPTIMIZED: DISABLED - was too restrictive
        use_sma_filter: bool = False,  # OPTIMIZED: DISABLED temporarily for testing
        sma_period: int = 50,
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.015,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Optimized Momentum strategy

        Key Changes:
        1. Stop-loss increased to 3% (less noise-induced exits)
        2. Take-profit increased to 5% (let winners run)
        3. RSI thresholds: 45/55 (catch momentum earlier)
        4. MACD histogram: 0.0003 (more sensitive)
        5. Minimum holding: 5 bars (faster exits)
        6. Volume filter: DISABLED (too restrictive)
        7. SMA filter: DISABLED temporarily (test if over-optimized)
        """
        params = parameters or {}
        params.update({
            'rsi_period': rsi_period,
            'rsi_buy_threshold': rsi_buy_threshold,
            'rsi_sell_threshold': rsi_sell_threshold,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'macd_signal': macd_signal,
            'position_size': position_size,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'macd_histogram_threshold': macd_histogram_threshold,
            'min_holding_period': min_holding_period,
            'volume_confirmation': volume_confirmation,
            'use_sma_filter': use_sma_filter,
            'sma_period': sma_period,
            'use_trailing_stop': use_trailing_stop,
            'trailing_stop_pct': trailing_stop_pct,
        })

        super().__init__(name="MomentumOptimizedStrategy", parameters=params)

        # Track active positions for exit signals
        self.active_positions = {}  # {symbol: {'entry_price': float, 'entry_time': datetime, 'type': 'long'/'short', 'highest_price': float, 'lowest_price': float}}

        logger.info(f"Initialized {self.name} with optimized parameters:")
        logger.info(f"  Stop-loss: {stop_loss_pct:.1%}, Take-profit: {take_profit_pct:.1%}")
        logger.info(f"  RSI thresholds: {rsi_buy_threshold}/{rsi_sell_threshold}")
        logger.info(f"  MACD histogram: {macd_histogram_threshold}")
        logger.info(f"  Min holding: {min_holding_period} bars")
        logger.info(f"  Volume filter: {volume_confirmation}, SMA filter: {use_sma_filter}")

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate optimized momentum-based signals"""
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

        # OPTIONAL: Calculate SMA trend filter (disabled by default)
        use_sma_filter = self.get_parameter('use_sma_filter', False)
        if use_sma_filter:
            sma_period = self.get_parameter('sma_period', 50)
            data['sma_50'] = data['close'].rolling(window=sma_period).mean()
            logger.debug(f"SMA filter enabled with {sma_period}-period MA")

        # Get parameters
        signals = []
        rsi_buy_threshold = self.get_parameter('rsi_buy_threshold', 45)
        rsi_sell_threshold = self.get_parameter('rsi_sell_threshold', 55)
        stop_loss_pct = self.get_parameter('stop_loss_pct', 0.03)
        take_profit_pct = self.get_parameter('take_profit_pct', 0.05)
        min_holding_period = self.get_parameter('min_holding_period', 5)

        for i in range(max(rsi_period, ema_slow, macd_signal_period) + 1, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current['rsi']) or pd.isna(current['macd']):
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # Check for EXIT signals first (stop-loss / take-profit / trailing stop)
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                position_type = position['type']

                # Track highest/lowest price for trailing stops
                use_trailing_stop = self.get_parameter('use_trailing_stop', True)
                if use_trailing_stop:
                    if position_type == 'long':
                        highest_price = position.get('highest_price', entry_price)
                        highest_price = max(highest_price, current_price)
                        self.active_positions[symbol]['highest_price'] = highest_price
                    else:  # short
                        lowest_price = position.get('lowest_price', entry_price)
                        lowest_price = min(lowest_price, current_price)
                        self.active_positions[symbol]['lowest_price'] = lowest_price

                # Calculate holding period
                bars_held = i - data.index.get_loc(entry_time)

                # Calculate P&L
                if position_type == 'long':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # short
                    pnl_pct = (entry_price - current_price) / entry_price

                # OPTIMIZED: Minimum holding period reduced to 5 bars (from 10)
                # Exception: Catastrophic loss (-5%) can exit immediately
                catastrophic_loss_pct = -0.05

                if bars_held < min_holding_period:
                    # ONLY allow exit on catastrophic loss
                    if pnl_pct <= catastrophic_loss_pct:
                        signal_type = SignalType.EXIT
                        signal = Signal(
                            timestamp=current.name,
                            symbol=symbol,
                            signal_type=signal_type,
                            price=current_price,
                            confidence=1.0,
                            metadata={
                                'exit_reason': 'catastrophic_stop_loss',
                                'pnl_pct': float(pnl_pct),
                                'entry_price': entry_price,
                                'position_type': position_type,
                                'bars_held': bars_held,
                                'rsi': float(current['rsi']),
                                'macd': float(current['macd']),
                            }
                        )
                        signals.append(signal)
                        del self.active_positions[symbol]
                        continue
                    # Otherwise, HOLD
                    continue

                # AFTER minimum holding period: Check stops
                exit_triggered = False
                exit_reason = None

                # Trailing stop-loss
                if use_trailing_stop and bars_held >= min_holding_period:
                    trailing_stop_pct = self.get_parameter('trailing_stop_pct', 0.015)

                    if position_type == 'long':
                        if current_price < highest_price * (1 - trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop_loss"
                            logger.info(f"Trailing stop triggered: price={current_price:.2f}, peak={highest_price:.2f}")
                    else:  # short
                        if current_price > lowest_price * (1 + trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop_loss"
                            logger.info(f"Trailing stop triggered: price={current_price:.2f}, trough={lowest_price:.2f}")

                # Fixed stop-loss or take-profit (OPTIMIZED thresholds)
                if not exit_triggered and bars_held >= min_holding_period:
                    if pnl_pct <= -stop_loss_pct:
                        exit_triggered = True
                        exit_reason = "stop_loss"
                    elif pnl_pct >= take_profit_pct:
                        exit_triggered = True
                        exit_reason = "take_profit"

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
                            'rsi': float(current['rsi']),
                            'macd': float(current['macd']),
                            'highest_price': float(highest_price) if position_type == 'long' else None,
                            'lowest_price': float(lowest_price) if position_type == 'short' else None,
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

                # Technical exit signals (after minimum holding period)
                if bars_held >= min_holding_period:
                    if position_type == 'long':
                        # OPTIMIZED: Exit long when RSI crosses below sell threshold
                        if (current['rsi'] < rsi_sell_threshold and previous['rsi'] >= rsi_sell_threshold and
                            current['macd'] < current['macd_signal'] and
                            current['macd_histogram'] < -0.001):
                            signal_type = SignalType.EXIT
                    elif position_type == 'short':
                        # OPTIMIZED: Exit short when RSI crosses above buy threshold
                        if (current['rsi'] > rsi_buy_threshold and previous['rsi'] <= rsi_buy_threshold and
                            current['macd'] > current['macd_signal'] and
                            current['macd_histogram'] > 0.001):
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
                            'exit_reason': 'technical_reversal',
                            'pnl_pct': float(pnl_pct),
                            'entry_price': entry_price,
                            'position_type': position_type,
                            'bars_held': bars_held,
                            'rsi': float(current['rsi']),
                            'macd': float(current['macd']),
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

            # Generate ENTRY signals only if no active position
            if symbol not in self.active_positions:
                # OPTIMIZED: More sensitive histogram threshold
                histogram_threshold = self.get_parameter('macd_histogram_threshold', 0.0003)

                # OPTIMIZED: Volume filter DISABLED (was too restrictive)
                volume_confirmation = self.get_parameter('volume_confirmation', False)
                volume_ok = True  # Default to True since filter is disabled

                # OPTIMIZED: SMA filter DISABLED temporarily
                sma_ok = True
                if use_sma_filter and 'sma_50' in data.columns and not pd.isna(current.get('sma_50')):
                    sma_ok = True  # Will check in entry conditions if enabled

                # OPTIMIZED: Long signal with lower RSI threshold (45 instead of 50)
                if (current['rsi'] > rsi_buy_threshold and previous['rsi'] <= rsi_buy_threshold and
                    current['macd'] > current['macd_signal'] and
                    current['macd_histogram'] > histogram_threshold):

                    # Optional SMA filter
                    if not use_sma_filter or (use_sma_filter and current['close'] > current.get('sma_50', 0)):
                        signal_type = SignalType.LONG
                        logger.info(f"OPTIMIZED LONG: RSI={current['rsi']:.1f} (>{rsi_buy_threshold}), MACD_hist={current['macd_histogram']:.5f} (>{histogram_threshold:.5f})")

                # OPTIMIZED: Short signal with higher RSI threshold (55 instead of 50)
                elif (current['rsi'] < rsi_sell_threshold and previous['rsi'] >= rsi_sell_threshold and
                      current['macd'] < current['macd_signal'] and
                      current['macd_histogram'] < -histogram_threshold):

                    # Optional SMA filter
                    if not use_sma_filter or (use_sma_filter and current['close'] < current.get('sma_50', float('inf'))):
                        signal_type = SignalType.SHORT
                        logger.info(f"OPTIMIZED SHORT: RSI={current['rsi']:.1f} (<{rsi_sell_threshold}), MACD_hist={current['macd_histogram']:.5f} (<{-histogram_threshold:.5f})")

                if signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Calculate confidence based on indicator strength
                    rsi_strength = abs(current['rsi'] - 50) / 50
                    macd_strength = min(abs(current['macd_histogram']) / (current['close'] * 0.01), 1.0)
                    confidence = min((rsi_strength * 0.5 + macd_strength * 0.5), 1.0)

                    signal = Signal(
                        timestamp=current.name,
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        confidence=float(confidence),
                        metadata={
                            'rsi': float(current['rsi']),
                            'rsi_threshold': rsi_buy_threshold if signal_type == SignalType.LONG else rsi_sell_threshold,
                            'macd': float(current['macd']),
                            'macd_signal': float(current['macd_signal']),
                            'macd_histogram': float(current['macd_histogram']),
                            'histogram_threshold': float(histogram_threshold),
                            'volume': float(current.get('volume', 0)),
                            'optimization_version': 'v1_relaxed_params',
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

        logger.info(f"Generated {len(signals)} signals for {self.name} (including {sum(1 for s in signals if s.signal_type == SignalType.EXIT)} exits)")
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size with conservative risk management"""
        position_size_pct = self.get_parameter('position_size', 0.15)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price

        # Scale by confidence
        shares *= signal.confidence

        return round(shares, 2)

    def get_unrealized_pnl(self, symbol: str, current_price: float) -> Optional[float]:
        """Calculate unrealized P&L for an active position"""
        if symbol not in self.active_positions:
            return None

        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        position_type = position['type']

        if position_type == 'long':
            return (current_price - entry_price) / entry_price
        else:  # short
            return (entry_price - current_price) / entry_price
