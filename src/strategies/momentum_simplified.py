"""
Simplified Momentum Strategy - Strategy 2 Test
Removes SMA filter and volume confirmation to reduce over-optimization
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class SimplifiedMomentumStrategy(Strategy):
    """
    Simplified Momentum Strategy using RSI and MACD indicators

    SIMPLIFIED VERSION - Removes:
    - 50 SMA trend filter (allow trades regardless of trend)
    - Volume confirmation (volume_confirmation = False)

    KEEPS:
    - RSI 50 crossings for momentum detection
    - MACD and signal line crossovers
    - MACD histogram threshold (0.0005)
    - Stop-loss and take-profit logic
    - Minimum holding period

    Expected Impact:
    - More signals generated (20-50 trades vs current 5)
    - Better win rate (removing over-optimization)
    - More robust across different market conditions

    Parameters:
        rsi_period: RSI period (default: 14)
        ema_fast: Fast EMA period for MACD (default: 12)
        ema_slow: Slow EMA period for MACD (default: 26)
        macd_signal: MACD signal line period (default: 9)
        macd_histogram_threshold: Histogram threshold (default: 0.0005)
        position_size: Position size fraction (default: 0.15)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Take profit percentage (default: 0.03 = 3%)
        min_holding_period: Minimum bars to hold (default: 10)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        macd_histogram_threshold: float = 0.0005,
        position_size: float = 0.15,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.03,
        min_holding_period: int = 10,
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.015,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Simplified Momentum strategy"""
        params = parameters or {}
        params.update({
            'rsi_period': rsi_period,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'macd_signal': macd_signal,
            'macd_histogram_threshold': macd_histogram_threshold,
            'position_size': position_size,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'min_holding_period': min_holding_period,
            'use_trailing_stop': use_trailing_stop,
            'trailing_stop_pct': trailing_stop_pct,
        })

        super().__init__(name="SimplifiedMomentumStrategy", parameters=params)

        # Track active positions
        self.active_positions = {}

    def generate_signals(self, data: pd.DataFrame, latest_only: bool = True) -> list[Signal]:
        """Generate simplified momentum-based signals

        Args:
            data: DataFrame with OHLCV data
            latest_only: If True, only generate signal for the latest bar (default: True)
                        Set to False for full historical backtesting analysis
        """
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

        # NO SMA FILTER - REMOVED
        # NO VOLUME FILTER - REMOVED

        signals = []
        stop_loss_pct = self.get_parameter('stop_loss_pct', 0.02)
        take_profit_pct = self.get_parameter('take_profit_pct', 0.03)
        min_holding_period = self.get_parameter('min_holding_period', 10)

        # CRITICAL FIX: Determine range - only process latest bar for live trading
        min_bars = max(rsi_period, ema_slow, macd_signal_period) + 1
        if latest_only and len(data) > min_bars:
            # Only process the latest bar
            start_idx = len(data) - 1
        else:
            # Process all historical bars (for analysis only)
            start_idx = min_bars

        for i in range(start_idx, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current['rsi']) or pd.isna(current['macd']):
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # Check for EXIT signals (stop-loss / take-profit / trailing stop)
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

                # ASYMMETRIC HOLDING PERIOD LOGIC:
                # - Stop-losses: IMMEDIATE exit (protect capital, prevent -5.49% losses)
                # - Take-profits: REQUIRE minimum holding period (avoid premature exits)
                # - Trailing stops: IMMEDIATE exit (risk management tool)
                #
                # RATIONALE: Stop-losses are risk management - delays can turn -2% into -5.49%.
                # Take-profits benefit from holding to capture full trend momentum.

                exit_triggered = False
                exit_reason = None

                # 1. IMMEDIATE EXITS (no holding period required for risk management):

                # Catastrophic loss check (immediate exit at -5%)
                catastrophic_loss_pct = -0.05
                if pnl_pct <= catastrophic_loss_pct:
                    exit_triggered = True
                    exit_reason = 'catastrophic_stop_loss'

                # Fixed stop-loss (IMMEDIATE exit at -2% - no delay)
                elif pnl_pct <= -stop_loss_pct:
                    exit_triggered = True
                    exit_reason = "stop_loss"
                    logger.info(
                        f"⚠️ IMMEDIATE STOP-LOSS: {symbol} @ ${current_price:.2f} | "
                        f"Entry=${entry_price:.2f}, P&L={pnl_pct:.2%}, Bars={bars_held}"
                    )

                # Trailing stop-loss (IMMEDIATE exit to lock in profits)
                elif use_trailing_stop:
                    trailing_stop_pct = self.get_parameter('trailing_stop_pct', 0.015)

                    if position_type == 'long':
                        if current_price < highest_price * (1 - trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop_loss"
                    else:  # short
                        if current_price > lowest_price * (1 + trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop_loss"

                # 2. DELAYED EXITS (require minimum holding period to capture momentum):

                # Take-profit (only after minimum holding period to avoid premature exits)
                if not exit_triggered and bars_held >= min_holding_period:
                    if pnl_pct >= take_profit_pct:
                        exit_triggered = True
                        exit_reason = "take_profit"
                        logger.info(
                            f"✅ TAKE-PROFIT (after {bars_held} bars): {symbol} @ ${current_price:.2f} | "
                            f"Entry=${entry_price:.2f}, P&L={pnl_pct:.2%}"
                        )

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
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

                # 3. Technical exit signals (only after minimum holding period)
                # These are momentum reversal signals, not risk management
                if bars_held < min_holding_period:
                    continue

                if position_type == 'long':
                    if (current['rsi'] < 50 and previous['rsi'] >= 50 and
                        current['macd'] < current['macd_signal'] and
                        current['macd_histogram'] < -0.001):
                        signal_type = SignalType.EXIT
                elif position_type == 'short':
                    if (current['rsi'] > 50 and previous['rsi'] <= 50 and
                        current['macd'] > current['macd_signal'] and
                        current['macd_histogram'] > 0.001):
                        signal_type = SignalType.EXIT

                if signal_type == SignalType.EXIT:
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
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

            # Generate ENTRY signals (SIMPLIFIED - NO SMA, NO VOLUME)
            # WEEK 2 FIX: Apply "2 of 3" scoring for simplified version (less conditions available)
            if symbol not in self.active_positions:
                histogram_threshold = self.get_parameter('macd_histogram_threshold', 0.0005)

                # LONG CONDITIONS (simplified - only 3 conditions, no SMA/volume)
                # CRITICAL FIX Week 2: Changed RSI from crossover to level-based logic
                # OLD: current['rsi'] > 50 and previous['rsi'] <= 50 (only triggers once)
                # NEW: RSI in bullish zone (55-85) allows signals throughout uptrend
                rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85  # Bullish zone, not overbought
                macd_long_cond = current['macd'] > current['macd_signal']
                hist_long_cond = current['macd_histogram'] > histogram_threshold

                # Count LONG conditions met (out of 3)
                long_conditions_met = sum([
                    rsi_long_cond,      # 1. RSI in bullish zone (55-85)
                    macd_long_cond,     # 2. MACD bullish
                    hist_long_cond      # 3. Histogram threshold
                ])

                # SIMPLIFIED LONG: Require at least 2 of 3 conditions
                if long_conditions_met >= 2:
                    signal_type = SignalType.LONG
                    logger.info(
                        f"[{symbol}] LONG SIGNAL ({long_conditions_met}/3): "
                        f"Price=${current_price:.2f}, "
                        f"RSI={current['rsi']:.1f} {'✓' if rsi_long_cond else '✗'}, "
                        f"MACD {'✓' if macd_long_cond else '✗'}, "
                        f"Hist={'✓' if hist_long_cond else '✗'} ({current['macd_histogram']:.5f})"
                    )
                else:
                    # Debug: Log when close but not enough conditions
                    if long_conditions_met == 1:
                        logger.debug(
                            f"[{symbol}] Near LONG ({long_conditions_met}/3): "
                            f"RSI={current['rsi']:.1f} {'✓' if rsi_long_cond else '✗'}, "
                            f"MACD {'✓' if macd_long_cond else '✗'}, "
                            f"Hist={'✓' if hist_long_cond else '✗'}"
                        )

                # ============================================================
                # WEEK 3 FIX: SHORT SIGNALS DISABLED
                # ============================================================
                # CRITICAL FINDING FROM WEEK 2 BACKTESTING:
                # - SHORT signals: 72.7% loss rate (8 of 11 trades lost)
                # - Average loss: -3% to -5% per trade
                # - Root cause: Momentum indicators LAG price movements
                # - Issue: Strategy enters shorts RIGHT BEFORE prices bounce
                #
                # IMPACT OF DISABLING SHORTS:
                # - Eliminate 72.7% losing trade type
                # - Reduce total trades by ~15-20%
                # - Improve overall win rate significantly
                # - Reduce drawdown from failed shorts
                #
                # TODO WEEK 4: Re-enable shorts with market regime detection
                # - Only short in confirmed bear markets
                # - Add additional filters (VIX, trend strength, etc.)
                # ============================================================

                # SHORT CONDITIONS (simplified - only 3 conditions, no SMA/volume)
                # CRITICAL FIX Week 2: Changed RSI from crossover to level-based logic
                # OLD: current['rsi'] < 50 and previous['rsi'] >= 50 (only triggers once)
                # NEW: RSI in bearish zone (15-45) allows signals throughout downtrend
                rsi_short_cond = current['rsi'] < 45 and current['rsi'] > 15  # Bearish zone, not oversold
                macd_short_cond = current['macd'] < current['macd_signal']
                hist_short_cond = current['macd_histogram'] < -histogram_threshold

                # Count SHORT conditions met (out of 3)
                short_conditions_met = sum([
                    rsi_short_cond,     # 1. RSI in bearish zone (15-45)
                    macd_short_cond,    # 2. MACD bearish
                    hist_short_cond     # 3. Histogram threshold
                ])

                # WEEK 3 FIX: SHORT SIGNALS DISABLED DUE TO 72.7% LOSS RATE
                # Log when SHORT condition is met but skipped
                if short_conditions_met >= 2:
                    logger.warning(
                        f"🚫 SHORT SIGNAL BLOCKED (WEEK 3 FIX): "
                        f"({short_conditions_met}/3): "
                        f"RSI={current['rsi']:.1f} {'✓' if rsi_short_cond else '✗'}, "
                        f"MACD {'✓' if macd_short_cond else '✗'}, "
                        f"Hist={'✓' if hist_short_cond else '✗'} ({current['macd_histogram']:.5f}) | "
                        f"Reason: 72.7% loss rate in Week 2 backtesting"
                    )

                # ORIGINAL SHORT SIGNAL CODE (DISABLED):
                # if short_conditions_met >= 2:
                #     signal_type = SignalType.SHORT
                #     logger.info(
                #         f"SIMPLIFIED SHORT ({short_conditions_met}/3): "
                #         f"RSI={current['rsi']:.1f} {'✓' if rsi_short_cond else '✗'}, "
                #         f"MACD {'✓' if macd_short_cond else '✗'}, "
                #         f"Hist={'✓' if hist_short_cond else '✗'} ({current['macd_histogram']:.5f})"
                #     )

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
                            'macd': float(current['macd']),
                            'macd_signal': float(current['macd_signal']),
                            'macd_histogram': float(current['macd_histogram']),
                            'histogram_threshold': float(histogram_threshold),
                            'strategy': 'simplified_momentum',
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

        logger.info(f"Generated {len(signals)} signals for Simplified Momentum strategy")
        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size with confidence scaling"""
        position_size_pct = self.get_parameter('position_size', 0.15)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price
        shares *= signal.confidence
        return round(shares, 2)
