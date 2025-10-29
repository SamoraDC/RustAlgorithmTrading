"""
Regime-Aware Momentum Strategy using RSI, MACD, and Market Regime Detection

This enhanced momentum strategy adapts to market conditions:
- Trending markets: Active momentum trading
- Ranging markets: Hold (no trading)
- Volatile markets: Wider stops, reduced position size
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType
from src.utils.market_regime import (
    MarketRegimeDetector,
    MarketRegime,
    select_strategy_for_regime,
    get_regime_display_name
)


class RegimeAwareMomentumStrategy(Strategy):
    """
    Momentum Strategy with Market Regime Detection

    Adapts trading behavior based on detected market conditions:
    - TRENDING_UP: Long-only momentum trading
    - TRENDING_DOWN: Short-only momentum trading
    - RANGING: No trading (hold)
    - VOLATILE_TRENDING: Wider stops, smaller positions
    - VOLATILE_RANGING: No trading
    """

    def __init__(
        self,
        # Technical indicators
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        # Risk management
        position_size: float = 0.15,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.03,
        # Entry conditions
        macd_histogram_threshold: float = 0.0005,
        # Volume confirmation
        volume_confirmation: bool = True,
        volume_ma_period: int = 20,
        volume_multiplier: float = 1.2,
        # Trailing stops
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.015,
        # ATR position sizing
        use_atr_sizing: bool = False,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        # Market regime detection
        use_regime_detection: bool = True,
        regime_adx_trending: float = 25.0,
        regime_adx_ranging: float = 20.0,
        regime_atr_multiplier: float = 1.5,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize regime-aware momentum strategy"""
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
            'use_regime_detection': use_regime_detection,
            'regime_adx_trending': regime_adx_trending,
            'regime_adx_ranging': regime_adx_ranging,
            'regime_atr_multiplier': regime_atr_multiplier,
        })

        super().__init__(name="RegimeAwareMomentumStrategy", parameters=params)

        # Track active positions
        self.active_positions = {}

        # Initialize market regime detector
        self.regime_detector = None
        if use_regime_detection:
            self.regime_detector = MarketRegimeDetector(
                adx_period=atr_period,
                atr_period=atr_period,
                adx_trending_threshold=regime_adx_trending,
                adx_ranging_threshold=regime_adx_ranging,
                atr_volatility_multiplier=regime_atr_multiplier
            )
            logger.info("✅ Market regime detection enabled")

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate regime-aware momentum signals"""
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        # PHASE 4: Detect market regime
        use_regime_detection = self.get_parameter('use_regime_detection', True)
        current_regime = MarketRegime.UNKNOWN
        regime_config = None
        regime_stop_loss = self.get_parameter('stop_loss_pct', 0.02)
        regime_position_size = self.get_parameter('position_size', 0.15)

        if use_regime_detection and self.regime_detector:
            regimes = self.regime_detector.detect_regime(data)
            data['market_regime'] = regimes
            current_regime = regimes.iloc[-1] if len(regimes) > 0 else MarketRegime.UNKNOWN
            regime_config = select_strategy_for_regime(current_regime)

            logger.info(f"🔍 Market regime: {get_regime_display_name(current_regime)}")
            logger.info(f"📊 Strategy config: {regime_config}")

            # Override stop-loss and position size based on regime
            regime_stop_loss = regime_config.get('stop_loss', 0.02)
            regime_position_size = regime_config.get('position_size', 1.0) * self.get_parameter('position_size', 0.15)

            # If regime says trading is disabled, exit any positions and return
            if not regime_config.get('enabled', False):
                logger.warning(f"⛔ Trading disabled for regime: {current_regime.value}")

                # Generate exit signals for any active positions
                signals = []
                if symbol in self.active_positions:
                    position = self.active_positions[symbol]
                    current_price = float(data.iloc[-1]['close'])

                    signal = Signal(
                        timestamp=data.iloc[-1].name,
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        price=current_price,
                        confidence=1.0,
                        metadata={
                            'exit_reason': 'regime_disabled',
                            'regime': current_regime.value,
                            'entry_price': position['entry_price'],
                            'position_type': position['type']
                        }
                    )
                    signals.append(signal)
                    del self.active_positions[symbol]

                return signals

            # Check if regime allows the specific direction
            direction = regime_config.get('direction', 'neutral')
            if direction == 'neutral':
                logger.warning(f"⚠️ Neutral direction for regime: {current_regime.value}")
                return []

        # Calculate technical indicators
        data = self._calculate_indicators(data)

        # Generate signals with regime awareness
        signals = []
        rsi_oversold = self.get_parameter('rsi_oversold', 30)
        rsi_overbought = self.get_parameter('rsi_overbought', 70)

        for i in range(50, len(data)):  # Start after enough data for indicators
            current = data.iloc[i]
            previous = data.iloc[i - 1]

            if pd.isna(current.get('rsi')) or pd.isna(current.get('macd')):
                continue

            current_price = float(current['close'])
            signal_type = SignalType.HOLD

            # Check regime for this bar
            bar_regime = current.get('market_regime', MarketRegime.UNKNOWN)
            bar_regime_config = select_strategy_for_regime(bar_regime) if bar_regime != MarketRegime.UNKNOWN else regime_config

            # Handle EXIT signals first
            if symbol in self.active_positions:
                exit_signal = self._check_exit_conditions(
                    symbol, i, current, previous, data,
                    regime_stop_loss, bar_regime_config
                )
                if exit_signal:
                    signals.append(exit_signal)
                    continue

            # Generate ENTRY signals if no active position
            if symbol not in self.active_positions and bar_regime_config and bar_regime_config.get('enabled', False):
                entry_signal = self._check_entry_conditions(
                    symbol, i, current, previous, data,
                    bar_regime_config, current_regime
                )
                if entry_signal:
                    signals.append(entry_signal)

        logger.info(f"📈 Generated {len(signals)} signals ({sum(1 for s in signals if s.signal_type == SignalType.EXIT)} exits)")
        return signals

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        # RSI
        rsi_period = self.get_parameter('rsi_period', 14)
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema_fast = self.get_parameter('ema_fast', 12)
        ema_slow = self.get_parameter('ema_slow', 26)
        macd_signal_period = self.get_parameter('macd_signal', 9)

        data['ema_fast'] = data['close'].ewm(span=ema_fast, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=ema_slow, adjust=False).mean()
        data['macd'] = data['ema_fast'] - data['ema_slow']
        data['macd_signal'] = data['macd'].ewm(span=macd_signal_period, adjust=False).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']

        # SMA trend filter
        data['sma_50'] = data['close'].rolling(window=50).mean()

        # Volume MA
        if self.get_parameter('volume_confirmation', True):
            volume_ma_period = self.get_parameter('volume_ma_period', 20)
            data['volume_ma'] = data['volume'].rolling(window=volume_ma_period).mean()

        # ATR
        if self.get_parameter('use_atr_sizing', False):
            atr_period = self.get_parameter('atr_period', 14)
            data['high_low'] = data['high'] - data['low']
            data['high_close'] = abs(data['high'] - data['close'].shift())
            data['low_close'] = abs(data['low'] - data['close'].shift())
            data['true_range'] = data[['high_low', 'high_close', 'low_close']].max(axis=1)
            data['atr'] = data['true_range'].rolling(window=atr_period).mean()

        return data

    def _check_exit_conditions(
        self,
        symbol: str,
        i: int,
        current: pd.Series,
        previous: pd.Series,
        data: pd.DataFrame,
        stop_loss_pct: float,
        regime_config: Dict
    ) -> Optional[Signal]:
        """Check if exit conditions are met"""
        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        entry_time = position['entry_time']
        position_type = position['type']
        current_price = float(current['close'])

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

        # Calculate holding period
        bars_held = i - data.index.get_loc(entry_time)
        min_holding_period = self.get_parameter('min_holding_period', 10)

        # Calculate P&L
        if position_type == 'long':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        # Catastrophic loss check (immediate exit)
        if pnl_pct <= -0.05:
            del self.active_positions[symbol]
            return Signal(
                timestamp=current.name,
                symbol=symbol,
                signal_type=SignalType.EXIT,
                price=current_price,
                confidence=1.0,
                metadata={
                    'exit_reason': 'catastrophic_stop_loss',
                    'pnl_pct': float(pnl_pct),
                    'entry_price': entry_price,
                    'position_type': position_type,
                    'bars_held': bars_held
                }
            )

        # Enforce minimum holding period
        if bars_held < min_holding_period:
            return None

        # Check trailing stop
        exit_triggered = False
        exit_reason = None

        if use_trailing_stop:
            trailing_stop_pct = self.get_parameter('trailing_stop_pct', 0.015)
            if position_type == 'long':
                highest_price = position.get('highest_price', entry_price)
                if current_price < highest_price * (1 - trailing_stop_pct):
                    exit_triggered = True
                    exit_reason = "trailing_stop_loss"
            else:
                lowest_price = position.get('lowest_price', entry_price)
                if current_price > lowest_price * (1 + trailing_stop_pct):
                    exit_triggered = True
                    exit_reason = "trailing_stop_loss"

        # Check fixed stops
        if not exit_triggered:
            take_profit_pct = self.get_parameter('take_profit_pct', 0.03)
            if pnl_pct <= -stop_loss_pct:
                exit_triggered = True
                exit_reason = "stop_loss"
            elif pnl_pct >= take_profit_pct:
                exit_triggered = True
                exit_reason = "take_profit"

        if exit_triggered:
            del self.active_positions[symbol]
            return Signal(
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
                    'bars_held': bars_held
                }
            )

        return None

    def _check_entry_conditions(
        self,
        symbol: str,
        i: int,
        current: pd.Series,
        previous: pd.Series,
        data: pd.DataFrame,
        regime_config: Dict,
        current_regime: MarketRegime
    ) -> Optional[Signal]:
        """Check if entry conditions are met based on regime"""
        current_price = float(current['close'])
        histogram_threshold = self.get_parameter('macd_histogram_threshold', 0.0005)

        # Volume confirmation
        volume_ok = True
        if self.get_parameter('volume_confirmation', True):
            volume_multiplier = self.get_parameter('volume_multiplier', 1.2)
            if 'volume_ma' in data.columns and not pd.isna(current.get('volume_ma')):
                volume_ok = current['volume'] > current['volume_ma'] * volume_multiplier

        if not volume_ok:
            return None

        # Check regime direction
        direction = regime_config.get('direction', 'neutral')
        signal_type = SignalType.HOLD

        # Long signal conditions
        if direction in ['long_only', 'both']:
            if (current['rsi'] > 50 and previous['rsi'] <= 50 and
                current['macd'] > current['macd_signal'] and
                current['macd_histogram'] > histogram_threshold and
                current['close'] > current['sma_50'] and
                not pd.isna(current['sma_50'])):
                signal_type = SignalType.LONG

        # Short signal conditions
        elif direction in ['short_only', 'both']:
            if (current['rsi'] < 50 and previous['rsi'] >= 50 and
                current['macd'] < current['macd_signal'] and
                current['macd_histogram'] < -histogram_threshold and
                current['close'] < current['sma_50'] and
                not pd.isna(current['sma_50'])):
                signal_type = SignalType.SHORT

        if signal_type not in [SignalType.LONG, SignalType.SHORT]:
            return None

        # Calculate confidence
        rsi_strength = abs(current['rsi'] - 50) / 50
        macd_strength = min(abs(current['macd_histogram']) / (current['close'] * 0.01), 1.0)
        volume_strength = 0.5
        if 'volume_ma' in data.columns and not pd.isna(current.get('volume_ma')):
            volume_ratio = current['volume'] / current['volume_ma']
            volume_strength = min(volume_ratio / 2.0, 1.0)

        confidence = min((rsi_strength * 0.4 + macd_strength * 0.3 + volume_strength * 0.3), 1.0)

        # Track position
        self.active_positions[symbol] = {
            'entry_price': current_price,
            'entry_time': current.name,
            'type': 'long' if signal_type == SignalType.LONG else 'short',
            'highest_price': current_price,
            'lowest_price': current_price,
            'regime': current_regime.value
        }

        return Signal(
            timestamp=current.name,
            symbol=symbol,
            signal_type=signal_type,
            price=current_price,
            confidence=float(confidence),
            metadata={
                'rsi': float(current['rsi']),
                'macd': float(current['macd']),
                'macd_histogram': float(current['macd_histogram']),
                'regime': current_regime.value,
                'regime_display': get_regime_display_name(current_regime),
                'volume_ok': volume_ok
            }
        )

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size with regime-aware adjustments"""
        # Get base position size from regime config
        if signal.metadata.get('regime'):
            regime = MarketRegime(signal.metadata['regime'])
            regime_config = select_strategy_for_regime(regime)
            regime_multiplier = regime_config.get('position_size', 1.0)
        else:
            regime_multiplier = 1.0

        position_size_pct = self.get_parameter('position_size', 0.15) * regime_multiplier
        position_value = account_value * position_size_pct
        shares = position_value / signal.price

        # Scale by confidence
        shares *= signal.confidence

        # ATR-based sizing
        if self.get_parameter('use_atr_sizing', False) and signal.metadata.get('atr'):
            atr = signal.metadata['atr']
            atr_pct = atr / signal.price
            volatility_factor = 0.01 / max(atr_pct, 0.005)
            volatility_factor = min(max(volatility_factor, 0.5), 2.0)
            shares *= volatility_factor

        logger.info(f"Position sizing: base={position_size_pct:.1%}, regime_mult={regime_multiplier:.2f}, shares={shares:.2f}")
        return round(shares, 2)
