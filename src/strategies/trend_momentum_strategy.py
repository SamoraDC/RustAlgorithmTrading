"""
Trend-Momentum Strategy - Optimized for Strong Trending Markets

This strategy is designed to capture strong trends while minimizing drawdowns.
It's long-biased in uptrending markets and uses shorts only in clear downtrends.

Key Features:
1. Long when price > EMA and momentum is positive
2. Exit when trend weakens significantly
3. Short only in confirmed downtrends (stricter conditions)
4. Position sizing based on trend strength

Target: Sharpe Ratio >= 1.2
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class TrendMomentumStrategy(Strategy):
    """
    Simple trend-momentum strategy optimized for trending markets.

    Logic:
    - LONG: Price > EMA(20) AND RSI > 40 AND MACD > 0
    - EXIT LONG: Price < EMA(20) OR RSI < 30 OR stop-loss
    - SHORT: Price < EMA(20) AND RSI < 55 AND MACD < 0 AND confirmed downtrend
    - EXIT SHORT: Price > EMA(20) OR RSI > 70 OR stop-loss
    """

    def __init__(
        self,
        # Entry parameters
        ema_period: int = 20,
        rsi_long_min: float = 40,
        rsi_short_max: float = 55,

        # Exit parameters
        rsi_exit_long: float = 30,
        rsi_exit_short: float = 70,

        # Risk management
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.08,
        trailing_stop_pct: float = 0.02,

        # Position sizing
        position_size: float = 0.20,  # Larger positions for trending

        # Short selling
        enable_shorts: bool = True,
        short_size_multiplier: float = 0.6,  # Smaller shorts

        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize Trend-Momentum Strategy."""
        params = parameters or {}
        params.update({
            'ema_period': ema_period,
            'rsi_long_min': rsi_long_min,
            'rsi_short_max': rsi_short_max,
            'rsi_exit_long': rsi_exit_long,
            'rsi_exit_short': rsi_exit_short,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'trailing_stop_pct': trailing_stop_pct,
            'position_size': position_size,
            'enable_shorts': enable_shorts,
            'short_size_multiplier': short_size_multiplier,
        })

        super().__init__(name="TrendMomentumStrategy", parameters=params)

        # Position tracking
        self.active_positions: Dict[str, Dict] = {}

        logger.info(
            f"Initialized TrendMomentumStrategy | "
            f"EMA: {ema_period}, Position Size: {position_size:.0%}"
        )

    def generate_signals_for_symbol(self, symbol: str, data: pd.DataFrame) -> List[Signal]:
        """Generate signals for a specific symbol."""
        data = data.copy()
        data.attrs['symbol'] = symbol
        return self.generate_signals(data)

    def generate_signals(self, data: pd.DataFrame, latest_only: bool = True) -> List[Signal]:
        """Generate trend-momentum trading signals."""
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        # Need minimum data for indicators
        ema_period = self.get_parameter('ema_period', 20)
        min_bars = max(ema_period, 26) + 5  # 26 for MACD, +5 buffer

        if len(data) < min_bars:
            return []

        # Calculate indicators
        data = self._calculate_indicators(data, ema_period)

        signals = []

        # Determine processing range
        if latest_only and len(data) > min_bars:
            start_idx = len(data) - 1
        else:
            start_idx = min_bars

        for i in range(start_idx, len(data)):
            current = data.iloc[i]
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

            # Generate entry signals
            entry_signal = self._generate_entry_signal(
                symbol=symbol,
                current=current,
                price=current_price,
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
                }

        if signals:
            logger.info(f"Generated {len(signals)} signals for {symbol}")

        return signals

    def _calculate_indicators(self, data: pd.DataFrame, ema_period: int) -> pd.DataFrame:
        """Calculate indicators."""
        # EMA
        data['ema'] = data['close'].ewm(span=ema_period).mean()
        data['ema_50'] = data['close'].ewm(span=50).mean()

        # Price above/below EMA
        data['above_ema'] = data['close'] > data['ema']

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

        # Momentum
        data['momentum'] = data['close'].pct_change(10)

        # Trend strength (price distance from EMA as percentage)
        data['trend_strength'] = (data['close'] - data['ema']) / data['ema']

        return data

    def _generate_entry_signal(
        self,
        symbol: str,
        current: pd.Series,
        price: float,
        idx: int
    ) -> Optional[Signal]:
        """Generate entry signal based on trend-momentum."""
        rsi = current.get('rsi', 50)
        macd_hist = current.get('macd_hist', 0)
        above_ema = current.get('above_ema', False)
        momentum = current.get('momentum', 0)
        trend_strength = current.get('trend_strength', 0)

        if pd.isna(rsi) or pd.isna(macd_hist):
            return None

        rsi_long_min = self.get_parameter('rsi_long_min', 40)
        rsi_short_max = self.get_parameter('rsi_short_max', 55)
        enable_shorts = self.get_parameter('enable_shorts', True)
        position_size = self.get_parameter('position_size', 0.20)

        signal_type = None
        confidence = 0.0
        entry_reason = []

        # LONG CONDITIONS - Simple and clear
        if above_ema and rsi > rsi_long_min and macd_hist > 0:
            signal_type = SignalType.LONG

            # Confidence based on trend strength and momentum
            conf = 0.6
            if momentum > 0.02:
                conf += 0.1
                entry_reason.append("strong_momentum")
            if trend_strength > 0.01:
                conf += 0.1
                entry_reason.append("above_ema_trend")
            if rsi < 70:  # Not overbought
                conf += 0.1
                entry_reason.append("healthy_rsi")

            confidence = min(conf, 0.95)
            entry_reason.insert(0, "bullish_trend")

        # SHORT CONDITIONS - Stricter
        elif enable_shorts and not above_ema and rsi < rsi_short_max and macd_hist < 0:
            # Additional confirmation for shorts
            ema_50 = current.get('ema_50', np.nan)
            ema_20 = current.get('ema', np.nan)

            # Only short if EMA20 < EMA50 (confirmed downtrend)
            if not pd.isna(ema_50) and not pd.isna(ema_20) and ema_20 < ema_50:
                signal_type = SignalType.SHORT

                conf = 0.5
                if momentum < -0.02:
                    conf += 0.15
                    entry_reason.append("strong_down_momentum")
                if trend_strength < -0.01:
                    conf += 0.1
                    entry_reason.append("below_ema_trend")
                if rsi > 30:  # Not oversold
                    conf += 0.1
                    entry_reason.append("healthy_rsi")

                confidence = min(conf, 0.85)
                entry_reason.insert(0, "bearish_trend")

        if signal_type is None:
            return None

        # Position size adjustment
        if signal_type == SignalType.SHORT:
            position_size *= self.get_parameter('short_size_multiplier', 0.6)

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
                'strategy': 'trend_momentum',
                'rsi': float(rsi),
                'macd_hist': float(macd_hist),
                'trend_strength': float(trend_strength),
                'momentum': float(momentum) if not pd.isna(momentum) else 0,
                'entry_reasons': entry_reason,
                'position_size_pct': float(position_size)
            }
        )

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
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        stop_loss = self.get_parameter('stop_loss_pct', 0.03)
        take_profit = self.get_parameter('take_profit_pct', 0.08)
        trailing_stop = self.get_parameter('trailing_stop_pct', 0.02)
        rsi_exit_long = self.get_parameter('rsi_exit_long', 30)
        rsi_exit_short = self.get_parameter('rsi_exit_short', 70)

        rsi = current.get('rsi', 50)
        above_ema = current.get('above_ema', True)

        exit_reason = None

        # Stop-loss (immediate)
        if pnl_pct <= -stop_loss:
            exit_reason = 'stop_loss'

        # Take-profit
        elif pnl_pct >= take_profit:
            exit_reason = 'take_profit'

        # Trailing stop (after profit)
        elif bars_held >= 3 and pnl_pct > 0.01:
            if pos_type == 'long':
                drawdown = (pos['highest_price'] - current_price) / pos['highest_price']
                if drawdown >= trailing_stop:
                    exit_reason = 'trailing_stop'
            else:
                drawup = (current_price - pos['lowest_price']) / pos['lowest_price']
                if drawup >= trailing_stop:
                    exit_reason = 'trailing_stop'

        # Trend reversal exit
        elif bars_held >= 2:
            if pos_type == 'long' and not above_ema and rsi < rsi_exit_long:
                exit_reason = 'trend_reversal'
            elif pos_type == 'short' and above_ema and rsi > rsi_exit_short:
                exit_reason = 'trend_reversal'

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
            self.get_parameter('position_size', 0.20)
        )

        position_value = account_value * position_size_pct
        shares = position_value / signal.price
        shares *= signal.confidence

        return round(shares, 2)
