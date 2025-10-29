"""

WEEK 3 ENHANCEMENT: Added ADX trending market filter
- Only trades when ADX >25 (strong trend detected)
- Prevents choppy market whipsaws and improves win rate
Momentum Strategy using RSI and MACD with Risk Management
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType
from src.utils.market_regime import MarketRegimeDetector


class MomentumStrategy(Strategy):
    """
    Momentum Strategy using RSI and MACD indicators with comprehensive risk management

    Generates signals based on momentum indicators alignment with proper exit logic,
    stop-loss, and take-profit mechanisms.

    WEEK 3 UPDATE - Tightened RSI Zones:
    - LONG entries: RSI 60-80 (was 55-85) - Reduced zone by 40%
    - SHORT entries: RSI 20-40 (was 15-45) - Reduced zone by 40%
    - Target: 35-45 trades (was 69 trades in Week 2)
    - Expected win rate improvement from filtering marginal signals

    Parameters:
        rsi_period: RSI period (default: 14)
        rsi_oversold: RSI oversold level (default: 30) - Not used in entry logic
        rsi_overbought: RSI overbought level (default: 70) - Not used in entry logic
        ema_fast: Fast EMA period for MACD (default: 12)
        ema_slow: Slow EMA period for MACD (default: 26)
        macd_signal: MACD signal line period (default: 9)
        position_size: Position size fraction (default: 0.15)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Take profit percentage (default: 0.03 = 3% for 1.5:1 ratio)

    RSI Entry Zones (Week 3):
        LONG: 60 < RSI < 80 (captures strong bullish momentum)
        SHORT: 20 < RSI < 40 (captures strong bearish momentum)
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
        # PHASE 1: Relaxed entry conditions
        macd_histogram_threshold: float = 0.0005,  # Reduced from 0.001
        # PHASE 2: Volume and trailing stops
        volume_confirmation: bool = True,
        volume_ma_period: int = 20,
        volume_multiplier: float = 1.05,  # Volume must be 5% above average (reduced from 1.2 to eliminate 45% fewer signals)
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.015,  # 1.5% trailing stop
        # PHASE 3: ATR-based position sizing
        use_atr_sizing: bool = False,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        # WEEK 3: ADX trending market filter
        use_adx_filter: bool = True,
        adx_period: int = 14,
        adx_threshold: float = 25.0,  # ADX >25 = trending market (good for momentum)
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Momentum strategy with advanced risk management

        PHASE 1 - Relaxed Entry Conditions:
            - Lower histogram threshold (0.0005 vs 0.001)
            - More signals generated

        PHASE 2 - Volume & Trailing Stops:
            - Volume confirmation filter
            - Trailing stop-loss to lock in profits

        PHASE 3 - ATR-Based Sizing:
            - Position sizing based on volatility
            - Risk-adjusted capital allocation
        """
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
            'macd_histogram_threshold': macd_histogram_threshold,
            'volume_confirmation': volume_confirmation,
            'volume_ma_period': volume_ma_period,
            'volume_multiplier': volume_multiplier,
            'use_trailing_stop': use_trailing_stop,
            'trailing_stop_pct': trailing_stop_pct,
            'use_atr_sizing': use_atr_sizing,
            'atr_period': atr_period,
            'atr_multiplier': atr_multiplier,
            'use_adx_filter': use_adx_filter,
            'adx_period': adx_period,
            'adx_threshold': adx_threshold,
        })

        super().__init__(name="MomentumStrategy", parameters=params)

        # WEEK 3: Initialize market regime detector for ADX calculation
        use_adx_filter = params.get('use_adx_filter', True)
        if use_adx_filter:
            self.regime_detector = MarketRegimeDetector(
                adx_period=params.get('adx_period', 14),
                atr_period=params.get('atr_period', 14),
                adx_trending_threshold=params.get('adx_threshold', 25.0),
                adx_ranging_threshold=20.0
            )
            logger.info(f"✅ ADX trending filter ENABLED: threshold={params.get('adx_threshold', 25.0)}")
        else:
            self.regime_detector = None
            logger.warning("⚠️ ADX trending filter DISABLED - strategy will trade in all market conditions")


        # Track active positions for exit signals
        # PHASE 2: Added highest_price for trailing stops
        self.active_positions = {}  # {symbol: {'entry_price': float, 'entry_time': datetime, 'type': 'long'/'short', 'highest_price': float, 'lowest_price': float}}

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

        # CRITICAL FIX: Add 50-period SMA trend filter
        sma_period = self.get_parameter('sma_period', 50)
        data['sma_50'] = data['close'].rolling(window=sma_period).mean()

        # PHASE 2: Add volume moving average for confirmation
        volume_confirmation = self.get_parameter('volume_confirmation', True)
        if volume_confirmation:
            volume_ma_period = self.get_parameter('volume_ma_period', 20)
            data['volume_ma'] = data['volume'].rolling(window=volume_ma_period).mean()
            logger.debug(f"Volume confirmation enabled with {volume_ma_period}-period MA")

        # PHASE 3: Add ATR for volatility-based position sizing
        use_atr_sizing = self.get_parameter('use_atr_sizing', False)
        if use_atr_sizing:
            atr_period = self.get_parameter('atr_period', 14)
            data['high_low'] = data['high'] - data['low']
            data['high_close'] = abs(data['high'] - data['close'].shift())
            data['low_close'] = abs(data['low'] - data['close'].shift())
            data['true_range'] = data[['high_low', 'high_close', 'low_close']].max(axis=1)
            data['atr'] = data['true_range'].rolling(window=atr_period).mean()
            logger.debug(f"ATR-based position sizing enabled with {atr_period}-period ATR")


        # WEEK 3: Calculate ADX for trending market filter
        use_adx_filter = self.get_parameter('use_adx_filter', True)
        if use_adx_filter and self.regime_detector:
            data['adx'] = self.regime_detector.calculate_adx(data)
            adx_threshold = self.get_parameter('adx_threshold', 25.0)
            logger.debug(f"ADX trending filter enabled with threshold={adx_threshold}")

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
                logger.debug(f"⏭️ Skipping bar {i}: NaN indicators (RSI or MACD)")
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # ENHANCED LOGGING: Log current technical indicators
            logger.debug(
                f"📈 Bar {i} ({current.name}): {symbol} @ ${current_price:.2f} | "
                f"RSI={current['rsi']:.1f}, MACD={current['macd']:.4f}, "
                f"Signal={current['macd_signal']:.4f}, Hist={current['macd_histogram']:.5f}, "
                f"SMA50=${current.get('sma_50', 0):.2f}"
            )

            # Check for EXIT signals first (stop-loss / take-profit / trailing stop)
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                entry_price = position['entry_price']
                entry_time = position['entry_time']  # CRITICAL: Define entry_time
                position_type = position['type']

                # PHASE 2: Track highest/lowest price for trailing stops
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

                # CRITICAL FIX: Calculate holding period FIRST to enforce minimum hold time
                bars_held = i - data.index.get_loc(entry_time)
                min_holding_period = self.get_parameter('min_holding_period', 10)  # Hold at least 10 bars

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
                    logger.info(
                        f"🚨 CATASTROPHIC LOSS: {symbol} @ ${current_price:.2f} | "
                        f"Entry=${entry_price:.2f}, P&L={pnl_pct:.2%}, Bars={bars_held}"
                    )

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
                        # Exit if price drops trailing_stop_pct from highest price
                        if current_price < highest_price * (1 - trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop_loss"
                            pnl_from_peak = (current_price - highest_price) / highest_price
                            logger.info(f"📉 Trailing stop: price={current_price:.2f}, peak={highest_price:.2f}, drop={pnl_from_peak:.2%}")
                    else:  # short
                        # Exit if price rises trailing_stop_pct from lowest price
                        if current_price > lowest_price * (1 + trailing_stop_pct):
                            exit_triggered = True
                            exit_reason = "trailing_stop_loss"
                            pnl_from_trough = (lowest_price - current_price) / lowest_price
                            logger.info(f"📈 Trailing stop: price={current_price:.2f}, trough={lowest_price:.2f}, rise={pnl_from_trough:.2%}")

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
                            'rsi': float(current['rsi']),
                            'macd': float(current['macd']),
                            'highest_price': float(highest_price) if position_type == 'long' else None,
                            'lowest_price': float(lowest_price) if position_type == 'short' else None,
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]
                    continue

                # 3. Technical exit signals (only after minimum holding period)
                # These are momentum reversal signals, not risk management
                if bars_held < min_holding_period:
                    continue

                if bars_held >= min_holding_period:
                    if position_type == 'long':
                        # Exit long when momentum reverses: RSI crosses BELOW 50 + MACD bearish
                        if (current['rsi'] < 50 and previous['rsi'] >= 50 and  # RSI momentum lost
                            current['macd'] < current['macd_signal'] and       # MACD bearish
                            current['macd_histogram'] < -0.001):               # Confirmed weakness
                            signal_type = SignalType.EXIT
                    elif position_type == 'short':
                        # Exit short when momentum reverses: RSI crosses ABOVE 50 + MACD bullish
                        if (current['rsi'] > 50 and previous['rsi'] <= 50 and  # RSI momentum recovering
                            current['macd'] > current['macd_signal'] and       # MACD bullish
                            current['macd_histogram'] > 0.001):                # Confirmed strength
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
                # WEEK 3: Check ADX trending market filter FIRST (hard requirement)
                # This is a HARD requirement - if market is not trending, skip ALL signals
                use_adx_filter = self.get_parameter('use_adx_filter', True)
                if use_adx_filter and 'adx' in data.columns:
                    adx_threshold = self.get_parameter('adx_threshold', 25.0)
                    current_adx = current.get('adx', 0)

                    if pd.isna(current_adx) or current_adx < adx_threshold:
                        # Market is not trending - SKIP signal generation
                        if not pd.isna(current_adx):
                            logger.debug(
                                f"⏸️ SKIPPING SIGNAL: {symbol} ADX={current_adx:.1f} <{adx_threshold} "
                                f"(not trending - choppy market detected)"
                            )
                        continue
                    else:
                        # Market is trending - proceed with signal generation
                        logger.debug(f"✅ ADX={current_adx:.1f} >{adx_threshold} (trending market - momentum suitable)")

                # PHASE 1: Get relaxed histogram threshold
                histogram_threshold = self.get_parameter('macd_histogram_threshold', 0.0005)

                # PHASE 2: Check volume confirmation
                # WEEK 2 FIX: Reduced volume threshold from 1.2x to 1.05x (5% above average)
                # Original 1.2x filter eliminated 65% of valid signals in normal volume conditions
                # New 5% threshold is sufficient to filter out truly low-volume periods while
                # preserving signals during normal trading activity
                volume_ok = True
                if volume_confirmation:
                    volume_multiplier = self.get_parameter('volume_multiplier', 1.05)
                    if 'volume_ma' in data.columns and not pd.isna(current.get('volume_ma')):
                        volume_ok = current['volume'] > current['volume_ma'] * volume_multiplier
                        if not volume_ok:
                            logger.debug(f"Volume filter blocked entry: vol={current['volume']}, ma={current['volume_ma']}, required={current['volume_ma'] * volume_multiplier}")

                # CRITICAL FIX: Trend-following entries instead of contrarian
                # PHASE 1: RELAXED histogram threshold (0.0005 instead of 0.001)

                # WEEK 2 FIX: Relaxed entry conditions using "3 of 5" scoring system
                # Instead of requiring ALL conditions (AND logic = 0.035% probability),
                # we require at least 3 of 5 conditions (increased probability to ~5%)
                #
                # CRITICAL FIX Week 2: Changed from crossover to level-based logic
                # OLD: current['rsi'] > 50 and previous['rsi'] <= 50 (only triggers once)
                # NEW: RSI in bullish zone (55-85) allows signals throughout uptrend

                # LONG CONDITIONS: Check each condition independently
                # WEEK 3.5 FIX: Moderate RSI zones (Goldilocks approach)
                # Week 2: 55-85 LONG zone → 69 trades (too many, 73% above target)
                # Week 3: 60-80 LONG zone → 15 trades (too few, signal starvation)
                # Week 3.5: 58-82 LONG zone → Target 35-45 trades (GOLDILOCKS - just right)
                # Rationale: Middle ground between Week 2 (too loose) and Week 3 (too tight)
                rsi_long_cond = current['rsi'] > 58 and current['rsi'] < 82  # GOLDILOCKS bullish zone
                macd_long_cond = current['macd'] > current['macd_signal']
                hist_long_cond = current['macd_histogram'] > histogram_threshold
                trend_long_cond = current['close'] > current['sma_50'] and not pd.isna(current['sma_50'])

                # Count how many LONG conditions are met (out of 5)
                long_conditions_met = sum([
                    rsi_long_cond,      # 1. RSI in bullish zone (55-85)
                    macd_long_cond,     # 2. MACD above signal line (bullish)
                    hist_long_cond,     # 3. MACD histogram > threshold (strong bullish)
                    trend_long_cond,    # 4. Price above 50-period SMA (uptrend)
                    volume_ok           # 5. Volume above average (confirmation)
                ])

                # LONG SIGNAL: Require at least 3 of 5 conditions (60% agreement)
                if long_conditions_met >= 3:
                    signal_type = SignalType.LONG
                    # WEEK 3: Include ADX in signal logging
                    current_adx = current.get('adx', 0) if 'adx' in data.columns else None
                    adx_str = f", ADX={current_adx:.1f}" if current_adx and not pd.isna(current_adx) else ""
                    logger.info(
                        f"🟢 LONG SIGNAL ({long_conditions_met}/5 conditions): {symbol} @ ${current_price:.2f} | "
                        f"RSI={current['rsi']:.1f} {'✓' if rsi_long_cond else '✗'}, "
                        f"MACD {'✓' if macd_long_cond else '✗'}, "
                        f"Hist={'✓' if hist_long_cond else '✗'} ({current['macd_histogram']:.5f}), "
                        f"Trend {'✓' if trend_long_cond else '✗'}, "
                        f"Volume {'✓' if volume_ok else '✗'}{adx_str}"
                    )
                elif long_conditions_met >= 2:
                    # Log near-misses (2/5 conditions) for analysis
                    logger.debug(
                        f"🟡 LONG near-miss ({long_conditions_met}/5): RSI={rsi_long_cond}, "
                        f"MACD={macd_long_cond}, Hist={hist_long_cond}, "
                        f"Trend={trend_long_cond}, Volume={volume_ok}"
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

                # SHORT CONDITIONS: Check each condition independently
                # CRITICAL FIX Week 2: Changed from crossover to level-based logic
                # OLD: current['rsi'] < 50 and previous['rsi'] >= 50 (only triggers once)
                # NEW: RSI in bearish zone (15-45) allows signals throughout downtrend
                # WEEK 3.5 NOTE: SHORT signals remain DISABLED (see lines 466-483)
                # Week 2: 15-45 SHORT zone → 72.7% loss rate
                # Week 3: 20-40 SHORT zone → Still disabled (72.7% loss rate)
                # Week 3.5: Keep SHORT disabled - focus on LONG + mean reversion
                rsi_short_cond = current['rsi'] < 40 and current['rsi'] > 20  # Bearish zone (UNUSED - shorts disabled)
                macd_short_cond = current['macd'] < current['macd_signal']
                hist_short_cond = current['macd_histogram'] < -histogram_threshold
                trend_short_cond = current['close'] < current['sma_50'] and not pd.isna(current['sma_50'])

                # Count how many SHORT conditions are met (out of 5)
                short_conditions_met = sum([
                    rsi_short_cond,     # 1. RSI in bearish zone (15-45)
                    macd_short_cond,    # 2. MACD below signal line (bearish)
                    hist_short_cond,    # 3. MACD histogram < -threshold (strong bearish)
                    trend_short_cond,   # 4. Price below 50-period SMA (downtrend)
                    volume_ok           # 5. Volume above average (confirmation)
                ])

                # WEEK 3 FIX: SHORT SIGNALS DISABLED DUE TO 72.7% LOSS RATE
                # Log when SHORT condition is met but skipped
                if short_conditions_met >= 3:
                    logger.warning(
                        f"🚫 SHORT SIGNAL BLOCKED (WEEK 3 FIX): {symbol} @ ${current_price:.2f} | "
                        f"({short_conditions_met}/5 conditions) | "
                        f"RSI={current['rsi']:.1f} {'✓' if rsi_short_cond else '✗'}, "
                        f"MACD {'✓' if macd_short_cond else '✗'}, "
                        f"Hist={'✓' if hist_short_cond else '✗'} ({current['macd_histogram']:.5f}), "
                        f"Trend {'✓' if trend_short_cond else '✗'}, "
                        f"Volume {'✓' if volume_ok else '✗'} | "
                        f"Reason: 72.7% loss rate in Week 2 backtesting"
                    )
                elif short_conditions_met >= 2:
                    # Log near-misses (2/5 conditions) for analysis
                    logger.debug(
                        f"🟡 SHORT near-miss (blocked, {short_conditions_met}/5): RSI={rsi_short_cond}, "
                        f"MACD={macd_short_cond}, Hist={hist_short_cond}, "
                        f"Trend={trend_short_cond}, Volume={volume_ok}"
                    )

                # ORIGINAL SHORT SIGNAL CODE (DISABLED):
                # if short_conditions_met >= 3:
                #     signal_type = SignalType.SHORT
                #     logger.info(
                #         f"🔴 SHORT SIGNAL ({short_conditions_met}/5 conditions): {symbol} @ ${current_price:.2f} | "
                #         f"RSI={current['rsi']:.1f} {'✓' if rsi_short_cond else '✗'}, "
                #         f"MACD {'✓' if macd_short_cond else '✗'}, "
                #         f"Hist={'✓' if hist_short_cond else '✗'} ({current['macd_histogram']:.5f}), "
                #         f"Trend {'✓' if trend_short_cond else '✗'}, "
                #         f"Volume {'✓' if volume_ok else '✗'}"
                #     )

                if signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Calculate confidence based on indicator strength
                    rsi_strength = abs(current['rsi'] - 50) / 50  # 0 to 1
                    macd_strength = min(abs(current['macd_histogram']) / (current['close'] * 0.01), 1.0)

                    # PHASE 2: Add volume strength to confidence
                    volume_strength = 0.5  # Default neutral
                    if volume_confirmation and 'volume_ma' in data.columns and not pd.isna(current.get('volume_ma')):
                        volume_ratio = current['volume'] / current['volume_ma']
                        volume_strength = min(volume_ratio / 2.0, 1.0)  # Normalize to 0-1

                    confidence = min((rsi_strength * 0.4 + macd_strength * 0.3 + volume_strength * 0.3), 1.0)

                    # PHASE 3: Calculate ATR-based position size multiplier
                    atr_multiplier = 1.0
                    if use_atr_sizing and 'atr' in data.columns and not pd.isna(current.get('atr')):
                        atr_multiplier = self.get_parameter('atr_multiplier', 1.5)
                        # Store ATR for position sizing
                        current_atr = current['atr']
                    else:
                        current_atr = None

                    # WEEK 3: Include ADX in signal metadata
                    current_adx = current.get('adx', None) if 'adx' in data.columns else None

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
                            'volume': float(current.get('volume', 0)),
                            'volume_ma': float(current.get('volume_ma', 0)) if 'volume_ma' in data.columns else None,
                            'volume_ratio': float(current['volume'] / current['volume_ma']) if 'volume_ma' in data.columns and not pd.isna(current.get('volume_ma')) else None,
                            'atr': float(current_atr) if current_atr is not None else None,
                            'adx': float(current_adx) if current_adx is not None and not pd.isna(current_adx) else None,
                            'histogram_threshold': float(histogram_threshold),
                        }
                    )
                    signals.append(signal)

                    # Track position (PHASE 2: Initialize highest/lowest price)
                    self.active_positions[symbol] = {
                        'entry_price': current_price,
                        'entry_time': current.name,
                        'type': 'long' if signal_type == SignalType.LONG else 'short',
                        'highest_price': current_price,  # For trailing stop
                        'lowest_price': current_price,   # For trailing stop (short)
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

        PHASE 3: ATR-based position sizing for volatility adjustment
        - Uses 15% of account value per position by default
        - Scaled by confidence
        - Optionally adjusted by ATR (lower volatility = larger position)
        """
        position_size_pct = self.get_parameter('position_size', 0.15)
        position_value = account_value * position_size_pct
        shares = position_value / signal.price

        # Scale by confidence
        shares *= signal.confidence

        # PHASE 3: ATR-based position sizing (volatility adjustment)
        use_atr_sizing = self.get_parameter('use_atr_sizing', False)
        if use_atr_sizing and signal.metadata.get('atr') is not None:
            atr = signal.metadata['atr']
            atr_pct = atr / signal.price  # ATR as percentage of price

            # Risk-adjusted sizing: Higher volatility = smaller position
            # Example: If ATR is 2% of price, reduce position by 2x
            # If ATR is 1% of price, reduce position by 1x
            volatility_factor = 0.01 / max(atr_pct, 0.005)  # 1% reference / current ATR%
            volatility_factor = min(volatility_factor, 2.0)  # Cap at 2x
            volatility_factor = max(volatility_factor, 0.5)  # Floor at 0.5x

            shares *= volatility_factor
            logger.debug(f"ATR sizing: ATR={atr:.2f}, ATR%={atr_pct:.2%}, vol_factor={volatility_factor:.2f}, final_shares={shares:.2f}")

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
