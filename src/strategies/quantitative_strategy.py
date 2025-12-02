"""
Quantitative Trading Strategy - Statistical Approach

This strategy uses statistical methods and multiple signal confirmation
to achieve higher Sharpe ratios with both long and short operations.

Key Features:
1. Multi-timeframe momentum analysis
2. Statistical edge detection (z-score based entries)
3. Regime-aware long/short decisions
4. Dynamic position sizing based on volatility
5. Asymmetric risk management (tighter stops for shorts)

Target: Sharpe Ratio >= 1.2
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from dataclasses import dataclass

from src.strategies.base import Strategy, Signal, SignalType


@dataclass
class MarketContext:
    """Market context for decision making."""
    trend: str  # 'bullish', 'bearish', 'neutral'
    trend_strength: float  # 0-1
    volatility_regime: str  # 'low', 'normal', 'high'
    mean_reversion_signal: float  # -1 to 1
    momentum_signal: float  # -1 to 1
    volume_signal: float  # 0 to 1


class QuantitativeStrategy(Strategy):
    """
    Statistical quantitative strategy for high Sharpe ratio trading.

    Signal Generation:
    - Uses z-scores of price deviations from moving averages
    - Combines momentum and mean-reversion signals
    - Confirms with volume analysis
    - Regime filtering for long vs short

    Position Management:
    - Volatility-adjusted position sizing
    - Asymmetric stops (tighter for shorts)
    - Time-based exits
    """

    def __init__(
        self,
        # Signal thresholds
        zscore_entry_threshold: float = 1.5,
        zscore_exit_threshold: float = 0.5,
        momentum_threshold: float = 0.02,

        # Position sizing
        base_position_size: float = 0.12,
        max_position_size: float = 0.20,
        min_position_size: float = 0.05,

        # Risk management
        long_stop_loss: float = 0.025,
        short_stop_loss: float = 0.020,  # Tighter for shorts
        take_profit: float = 0.045,
        trailing_stop: float = 0.015,

        # Regime parameters
        volatility_lookback: int = 20,
        trend_lookback: int = 50,
        momentum_lookback: int = 10,

        # Short selling conditions
        enable_shorts: bool = True,
        short_volatility_max: float = 0.025,  # Max volatility for shorts
        short_trend_required: bool = True,  # Require downtrend for shorts

        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Quantitative Strategy."""
        params = parameters or {}
        params.update({
            'zscore_entry_threshold': zscore_entry_threshold,
            'zscore_exit_threshold': zscore_exit_threshold,
            'momentum_threshold': momentum_threshold,
            'base_position_size': base_position_size,
            'max_position_size': max_position_size,
            'min_position_size': min_position_size,
            'long_stop_loss': long_stop_loss,
            'short_stop_loss': short_stop_loss,
            'take_profit': take_profit,
            'trailing_stop': trailing_stop,
            'volatility_lookback': volatility_lookback,
            'trend_lookback': trend_lookback,
            'momentum_lookback': momentum_lookback,
            'enable_shorts': enable_shorts,
            'short_volatility_max': short_volatility_max,
            'short_trend_required': short_trend_required,
        })

        super().__init__(name="QuantitativeStrategy", parameters=params)

        # Position tracking
        self.active_positions: Dict[str, Dict] = {}

        logger.info(
            f"Initialized QuantitativeStrategy | "
            f"Z-score threshold: {zscore_entry_threshold}, "
            f"Shorts enabled: {enable_shorts}"
        )

    def generate_signals_for_symbol(self, symbol: str, data: pd.DataFrame) -> List[Signal]:
        """Generate signals for a specific symbol."""
        data = data.copy()
        data.attrs['symbol'] = symbol
        return self.generate_signals(data)

    def generate_signals(self, data: pd.DataFrame, latest_only: bool = True) -> List[Signal]:
        """Generate quantitative trading signals."""
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        # Need minimum data for indicators
        min_bars = max(
            self.get_parameter('trend_lookback', 50),
            self.get_parameter('volatility_lookback', 20)
        ) + 5

        if len(data) < min_bars:
            return []

        # Calculate all indicators
        data = self._calculate_indicators(data)

        signals = []

        # Determine processing range
        if latest_only and len(data) > min_bars:
            start_idx = len(data) - 1
        else:
            start_idx = min_bars

        for i in range(start_idx, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i - 1]
            current_price = float(current['close'])

            # Check for exit signals first
            exit_signal = self._check_exit(symbol, current_price, current, i, data)
            if exit_signal:
                signals.append(exit_signal)
                continue

            # Skip if we have a position
            if symbol in self.active_positions:
                self._update_position_tracking(symbol, current_price)
                continue

            # Get market context
            context = self._analyze_market_context(data.iloc[:i+1])

            # Generate entry signals
            entry_signal = self._generate_entry_signal(
                symbol=symbol,
                current=current,
                previous=previous,
                price=current_price,
                context=context,
                idx=i
            )

            if entry_signal:
                signals.append(entry_signal)

                # Track position
                self.active_positions[symbol] = {
                    'entry_price': current_price,
                    'entry_time': current.name,
                    'entry_idx': i,
                    'type': 'long' if entry_signal.signal_type == SignalType.LONG else 'short',
                    'highest_price': current_price,
                    'lowest_price': current_price,
                    'context': context
                }

        if signals:
            logger.info(f"Generated {len(signals)} signals for {symbol}")

        return signals

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        vol_lookback = self.get_parameter('volatility_lookback', 20)
        trend_lookback = self.get_parameter('trend_lookback', 50)
        mom_lookback = self.get_parameter('momentum_lookback', 10)

        # Returns
        data['returns'] = data['close'].pct_change()

        # Moving averages - use configurable lookback
        short_ma = min(vol_lookback, 20)
        long_ma = min(trend_lookback, 50)
        data['sma_20'] = data['close'].rolling(short_ma).mean()
        data['sma_50'] = data['close'].rolling(long_ma).mean()
        data['ema_10'] = data['close'].ewm(span=min(10, mom_lookback)).mean()
        data['ema_20'] = data['close'].ewm(span=short_ma).mean()

        # Z-score (price deviation from SMA)
        rolling_mean = data['close'].rolling(vol_lookback).mean()
        rolling_std = data['close'].rolling(vol_lookback).std()
        data['zscore'] = (data['close'] - rolling_mean) / rolling_std

        # Volatility
        data['volatility'] = data['returns'].rolling(vol_lookback).std()
        data['volatility_pct'] = data['volatility'] / data['close'].rolling(vol_lookback).mean()

        # Momentum (rate of change)
        data['momentum'] = data['close'].pct_change(mom_lookback)
        data['momentum_accel'] = data['momentum'].diff()

        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        data['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = data['close'].ewm(span=12).mean()
        ema26 = data['close'].ewm(span=26).mean()
        data['macd'] = ema12 - ema26
        data['macd_signal'] = data['macd'].ewm(span=9).mean()
        data['macd_hist'] = data['macd'] - data['macd_signal']

        # Bollinger Bands
        bb_sma = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        data['bb_upper'] = bb_sma + (2 * bb_std)
        data['bb_lower'] = bb_sma - (2 * bb_std)
        data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'] + 1e-10)

        # Volume analysis
        data['volume_sma'] = data['volume'].rolling(20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_sma']

        # ADX for trend strength
        data = self._calculate_adx(data)

        return data

    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate ADX."""
        high = data['high']
        low = data['low']
        close = data['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # Smoothed
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / (atr + 1e-10))
        minus_di = 100 * (minus_dm.rolling(period).mean() / (atr + 1e-10))

        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        data['adx'] = dx.rolling(period).mean()
        data['plus_di'] = plus_di
        data['minus_di'] = minus_di

        return data

    def _analyze_market_context(self, data: pd.DataFrame) -> MarketContext:
        """Analyze current market context."""
        current = data.iloc[-1]

        # Trend analysis
        if current['close'] > current['sma_50'] and current['ema_10'] > current['ema_20']:
            trend = 'bullish'
        elif current['close'] < current['sma_50'] and current['ema_10'] < current['ema_20']:
            trend = 'bearish'
        else:
            trend = 'neutral'

        # Trend strength from ADX
        adx = current.get('adx', 0)
        if pd.isna(adx):
            adx = 0
        trend_strength = min(adx / 50, 1.0)

        # Volatility regime
        vol = current.get('volatility_pct', 0.02)
        if pd.isna(vol):
            vol = 0.02
        if vol < 0.01:
            volatility_regime = 'low'
        elif vol > 0.025:
            volatility_regime = 'high'
        else:
            volatility_regime = 'normal'

        # Mean reversion signal (from z-score)
        zscore = current.get('zscore', 0)
        if pd.isna(zscore):
            zscore = 0
        mean_reversion_signal = -np.clip(zscore / 3, -1, 1)  # Negative z-score = buy signal

        # Momentum signal
        momentum = current.get('momentum', 0)
        if pd.isna(momentum):
            momentum = 0
        momentum_signal = np.clip(momentum * 20, -1, 1)

        # Volume signal
        vol_ratio = current.get('volume_ratio', 1)
        if pd.isna(vol_ratio):
            vol_ratio = 1
        volume_signal = min(vol_ratio / 2, 1.0)

        return MarketContext(
            trend=trend,
            trend_strength=trend_strength,
            volatility_regime=volatility_regime,
            mean_reversion_signal=mean_reversion_signal,
            momentum_signal=momentum_signal,
            volume_signal=volume_signal
        )

    def _generate_entry_signal(
        self,
        symbol: str,
        current: pd.Series,
        previous: pd.Series,
        price: float,
        context: MarketContext,
        idx: int
    ) -> Optional[Signal]:
        """Generate entry signal based on market context."""
        zscore_threshold = self.get_parameter('zscore_entry_threshold', 1.5)
        momentum_threshold = self.get_parameter('momentum_threshold', 0.02)
        enable_shorts = self.get_parameter('enable_shorts', True)
        short_vol_max = self.get_parameter('short_volatility_max', 0.025)
        short_trend_required = self.get_parameter('short_trend_required', True)

        zscore = current.get('zscore', 0)
        if pd.isna(zscore):
            return None

        momentum = current.get('momentum', 0)
        if pd.isna(momentum):
            momentum = 0

        rsi = current.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50

        macd_hist = current.get('macd_hist', 0)
        if pd.isna(macd_hist):
            macd_hist = 0

        vol = current.get('volatility_pct', 0.02)
        if pd.isna(vol):
            vol = 0.02

        signal_type = None
        confidence = 0.0
        entry_reason = []

        # TREND-FOLLOWING LONG CONDITIONS
        # Focus on catching strong trends with multiple confirmations
        long_score = 0

        # Get price data for moving average comparison
        sma_20 = current.get('sma_20', np.nan)
        sma_50 = current.get('sma_50', np.nan)
        current_price = current.get('close', 0)

        # Strong trend confirmation (primary)
        if context.trend == 'bullish' and context.trend_strength > 0.25:
            long_score += 2
            entry_reason.append("bullish_trend")

        # Price above moving averages (trend confirmation)
        if not pd.isna(sma_20) and not pd.isna(sma_50):
            if current_price > sma_20 > sma_50:
                long_score += 1.5
                entry_reason.append("price_above_MAs")
            elif current_price > sma_20:
                long_score += 0.5

        # MACD bullish (momentum confirmation)
        if macd_hist > 0 and momentum > 0:
            long_score += 1
            entry_reason.append("bullish_momentum")

        # RSI in healthy range (not overbought)
        if 30 < rsi < 70:
            long_score += 0.5
            entry_reason.append(f"healthy_rsi={rsi:.0f}")

        # Volume confirmation
        if context.volume_signal > 0.6:
            long_score += 0.5
            entry_reason.append("good_volume")

        # Require strong confirmation for long
        if long_score >= 3.0:
            signal_type = SignalType.LONG
            confidence = min(long_score / 5, 0.95)

        # TREND-FOLLOWING SHORT CONDITIONS
        if signal_type is None and enable_shorts:
            short_score = 0

            # Strong bearish trend (primary)
            if context.trend == 'bearish' and context.trend_strength > 0.25:
                short_score += 2
                entry_reason.append("bearish_trend")

            # Price below moving averages
            if not pd.isna(sma_20) and not pd.isna(sma_50):
                if current_price < sma_20 < sma_50:
                    short_score += 1.5
                    entry_reason.append("price_below_MAs")
                elif current_price < sma_20:
                    short_score += 0.5

            # MACD bearish (momentum confirmation)
            if macd_hist < 0 and momentum < 0:
                short_score += 1
                entry_reason.append("bearish_momentum")

            # RSI in healthy range (not oversold)
            if 30 < rsi < 70:
                short_score += 0.5
                entry_reason.append(f"healthy_rsi={rsi:.0f}")

            # Low volatility preferred for shorts
            if vol <= short_vol_max:
                short_score += 0.5
                entry_reason.append("low_volatility")

            # Require strong confirmation for short
            if short_score >= 3.0:
                signal_type = SignalType.SHORT
                confidence = min(short_score / 5, 0.90)

        if signal_type is None:
            return None

        # Calculate position size
        position_size = self._calculate_position_size(confidence, context, signal_type)

        logger.info(
            f"[{symbol}] {signal_type.name} SIGNAL: price=${price:.2f}, "
            f"confidence={confidence:.1%}, reasons=[{', '.join(entry_reason[:3])}]"
        )

        return Signal(
            timestamp=current.name,
            symbol=symbol,
            signal_type=signal_type,
            price=price,
            confidence=float(confidence),
            metadata={
                'strategy': 'quantitative',
                'zscore': float(zscore),
                'momentum': float(momentum),
                'rsi': float(rsi),
                'volatility': float(vol),
                'trend': context.trend,
                'trend_strength': float(context.trend_strength),
                'entry_reasons': entry_reason,
                'position_size_pct': float(position_size)
            }
        )

    def _calculate_position_size(
        self,
        confidence: float,
        context: MarketContext,
        signal_type: SignalType
    ) -> float:
        """Calculate position size based on confidence and context."""
        base_size = self.get_parameter('base_position_size', 0.12)
        max_size = self.get_parameter('max_position_size', 0.20)
        min_size = self.get_parameter('min_position_size', 0.05)

        size = base_size

        # Scale by confidence
        size *= (0.5 + confidence)

        # Reduce for high volatility
        if context.volatility_regime == 'high':
            size *= 0.7
        elif context.volatility_regime == 'low':
            size *= 1.1

        # Reduce shorts slightly
        if signal_type == SignalType.SHORT:
            size *= 0.85

        # Strong trend bonus
        if context.trend_strength > 0.6:
            size *= 1.1

        return max(min_size, min(max_size, size))

    def _update_position_tracking(self, symbol: str, current_price: float):
        """Update position tracking for trailing stops."""
        if symbol not in self.active_positions:
            return

        pos = self.active_positions[symbol]
        if pos['type'] == 'long':
            pos['highest_price'] = max(pos['highest_price'], current_price)
        else:
            pos['lowest_price'] = min(pos['lowest_price'], current_price)

    def _check_exit(
        self,
        symbol: str,
        current_price: float,
        current: pd.Series,
        idx: int,
        data: pd.DataFrame
    ) -> Optional[Signal]:
        """Check exit conditions."""
        if symbol not in self.active_positions:
            return None

        pos = self.active_positions[symbol]
        entry_price = pos['entry_price']
        pos_type = pos['type']
        entry_idx = pos['entry_idx']
        bars_held = idx - entry_idx

        # Calculate P&L
        if pos_type == 'long':
            pnl_pct = (current_price - entry_price) / entry_price
            stop_loss = self.get_parameter('long_stop_loss', 0.025)
        else:
            pnl_pct = (entry_price - current_price) / entry_price
            stop_loss = self.get_parameter('short_stop_loss', 0.020)

        take_profit = self.get_parameter('take_profit', 0.045)
        trailing_stop = self.get_parameter('trailing_stop', 0.015)
        zscore_exit = self.get_parameter('zscore_exit_threshold', 0.5)

        exit_reason = None

        # Stop-loss (immediate)
        if pnl_pct <= -stop_loss:
            exit_reason = 'stop_loss'

        # Take-profit (after min hold)
        elif pnl_pct >= take_profit and bars_held >= 3:
            exit_reason = 'take_profit'

        # Trailing stop (after profit)
        elif bars_held >= 5 and pnl_pct > 0:
            if pos_type == 'long':
                drawdown = (pos['highest_price'] - current_price) / pos['highest_price']
                if drawdown >= trailing_stop:
                    exit_reason = 'trailing_stop'
            else:
                drawup = (current_price - pos['lowest_price']) / pos['lowest_price']
                if drawup >= trailing_stop:
                    exit_reason = 'trailing_stop'

        # Mean reversion exit
        zscore = current.get('zscore', 0)
        if not pd.isna(zscore) and bars_held >= 5:
            if pos_type == 'long' and zscore > zscore_exit:
                exit_reason = 'mean_reversion'
            elif pos_type == 'short' and zscore < -zscore_exit:
                exit_reason = 'mean_reversion'

        # Time-based exit
        if bars_held >= 25:
            exit_reason = 'time_exit'

        if exit_reason:
            del self.active_positions[symbol]

            logger.info(
                f"[{symbol}] EXIT ({exit_reason}): P&L={pnl_pct:.2%}, bars={bars_held}"
            )

            return Signal(
                timestamp=current.name,
                symbol=symbol,
                signal_type=SignalType.EXIT,
                price=current_price,
                confidence=1.0,
                metadata={
                    'exit_reason': exit_reason,
                    'pnl_pct': float(pnl_pct),
                    'bars_held': bars_held,
                    'entry_price': entry_price,
                    'position_type': pos_type
                }
            )

        return None

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size from signal."""
        position_size_pct = signal.metadata.get(
            'position_size_pct',
            self.get_parameter('base_position_size', 0.12)
        )

        position_value = account_value * position_size_pct
        shares = position_value / signal.price
        shares *= signal.confidence

        return round(shares, 2)
