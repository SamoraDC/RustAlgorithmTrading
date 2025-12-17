"""
ML Ensemble Strategy - Advanced Quantitative Trading Strategy

This strategy combines multiple ML models with regime detection to achieve
higher Sharpe ratios through:
1. Ensemble voting from multiple classifiers (Random Forest, Gradient Boosting, XGBoost)
2. Confidence-based signal filtering (only trade when confidence > threshold)
3. Dynamic position sizing based on model agreement
4. Regime-aware long/short decisions
5. Advanced feature engineering with 50+ technical features

Target: Sharpe Ratio >= 1.2
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from loguru import logger
from dataclasses import dataclass

from src.strategies.base import Strategy, Signal, SignalType
from src.strategies.ml.features.feature_engineering import FeatureEngineer, FeatureConfig
from src.strategies.ml.models.trend_classifier import TrendClassifier

# Try importing XGBoost
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("XGBoost not available, using only sklearn models")


@dataclass
class RegimeState:
    """Market regime state."""
    regime: str  # 'trending_up', 'trending_down', 'ranging', 'volatile'
    strength: float  # 0-1
    adx: float
    volatility: float
    trend_direction: int  # 1=up, -1=down, 0=neutral


class MLEnsembleStrategy(Strategy):
    """
    Advanced ML Ensemble Strategy for high Sharpe ratio trading.

    Key Features:
    - Multi-model ensemble (RF + GBM + XGBoost)
    - Confidence filtering (>65% required for trades)
    - Regime-aware long/short decisions
    - Dynamic position sizing
    - Walk-forward model updates

    Long Signals:
    - Ensemble predicts UP with >65% confidence
    - Regime is trending_up OR (ranging with mean-reversion signal)
    - ADX confirms trend strength

    Short Signals:
    - Ensemble predicts DOWN with >70% confidence (higher threshold for shorts)
    - Regime is trending_down (shorts ONLY in confirmed downtrends)
    - Volatility within acceptable range (not extreme)
    """

    def __init__(
        self,
        # Confidence thresholds
        long_confidence_threshold: float = 0.60,
        short_confidence_threshold: float = 0.65,

        # Position sizing
        base_position_size: float = 0.15,
        max_position_size: float = 0.25,
        min_position_size: float = 0.05,

        # Risk management
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
        trailing_stop_pct: float = 0.015,

        # Regime parameters
        adx_trending_threshold: float = 25.0,
        adx_strong_trend: float = 35.0,
        volatility_max: float = 0.04,  # Max daily volatility for shorts

        # Model parameters
        train_window: int = 120,  # Days for training
        retrain_frequency: int = 20,  # Retrain every N days
        min_samples_for_training: int = 60,

        # Ensemble weights
        rf_weight: float = 0.35,
        gbm_weight: float = 0.35,
        xgb_weight: float = 0.30,

        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize ML Ensemble Strategy."""
        params = parameters or {}
        params.update({
            'long_confidence_threshold': long_confidence_threshold,
            'short_confidence_threshold': short_confidence_threshold,
            'base_position_size': base_position_size,
            'max_position_size': max_position_size,
            'min_position_size': min_position_size,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'trailing_stop_pct': trailing_stop_pct,
            'adx_trending_threshold': adx_trending_threshold,
            'adx_strong_trend': adx_strong_trend,
            'volatility_max': volatility_max,
            'train_window': train_window,
            'retrain_frequency': retrain_frequency,
            'min_samples_for_training': min_samples_for_training,
            'rf_weight': rf_weight,
            'gbm_weight': gbm_weight,
            'xgb_weight': xgb_weight,
        })

        super().__init__(name="MLEnsembleStrategy", parameters=params)

        # Initialize models
        self.models: Dict[str, TrendClassifier] = {}
        self.model_weights: Dict[str, float] = {}
        self._init_models()

        # Feature engineering
        self.feature_engineer = FeatureEngineer(FeatureConfig(
            lookback_periods=[5, 10, 20, 50],
            technical_indicators=['sma', 'ema', 'rsi', 'macd', 'bbands'],
            statistical_features=['returns', 'volatility', 'volume_ratio'],
            scaling_method='standard'
        ))

        # Training state
        self.is_trained = False
        self.last_train_idx = 0
        self.feature_names: List[str] = []
        self.scaler = None

        # Position tracking
        self.active_positions: Dict[str, Dict] = {}

        # Performance tracking
        self.predictions_made = 0
        self.correct_predictions = 0

        logger.info(
            f"Initialized MLEnsembleStrategy | "
            f"Long threshold: {long_confidence_threshold:.0%}, "
            f"Short threshold: {short_confidence_threshold:.0%}"
        )

    def _init_models(self):
        """Initialize ensemble models."""
        rf_weight = self.get_parameter('rf_weight', 0.35)
        gbm_weight = self.get_parameter('gbm_weight', 0.35)
        xgb_weight = self.get_parameter('xgb_weight', 0.30)

        # Random Forest - good for capturing non-linear patterns
        self.models['random_forest'] = TrendClassifier(
            model_type='random_forest',
            n_estimators=200,
            max_depth=8,
            min_samples_split=10,
            class_weight='balanced'
        )
        self.model_weights['random_forest'] = rf_weight

        # Gradient Boosting - good for sequential patterns
        self.models['gradient_boosting'] = TrendClassifier(
            model_type='gradient_boosting',
            n_estimators=150,
            learning_rate=0.05,
            max_depth=5
        )
        self.model_weights['gradient_boosting'] = gbm_weight

        # XGBoost if available
        if HAS_XGBOOST:
            self.models['xgboost'] = XGBoostClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=5
            )
            self.model_weights['xgboost'] = xgb_weight
        else:
            # Redistribute weight to other models
            total = rf_weight + gbm_weight
            self.model_weights['random_forest'] = rf_weight / total
            self.model_weights['gradient_boosting'] = gbm_weight / total

        logger.info(f"Initialized {len(self.models)} ensemble models")

    def train_models(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Train all ensemble models on historical data.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Training metrics for each model
        """
        min_samples = self.get_parameter('min_samples_for_training', 60)

        if len(data) < min_samples:
            logger.warning(f"Insufficient data for training: {len(data)} < {min_samples}")
            return {}

        # Engineer features
        features_df = self.feature_engineer.engineer_features(data.copy())

        # Prepare ML dataset
        X, y = self.feature_engineer.prepare_ml_dataset(
            features_df,
            target_col='next_return',
            scale_features=True
        )

        if len(X) < min_samples:
            logger.warning(f"Insufficient samples after feature engineering: {len(X)}")
            return {}

        # Store feature names and scaler
        self.feature_names = self.feature_engineer.feature_names
        self.scaler = self.feature_engineer.scaler

        # Train each model
        all_metrics = {}
        for name, model in self.models.items():
            try:
                metrics = model.train(X, y)
                all_metrics[name] = metrics
                logger.info(f"Trained {name}: accuracy={metrics.get('train_accuracy', 0):.3f}")
            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")

        self.is_trained = True
        self.last_train_idx = len(data)

        return all_metrics

    def _calculate_regime(self, data: pd.DataFrame) -> RegimeState:
        """
        Calculate current market regime.

        Args:
            data: Recent OHLCV data

        Returns:
            RegimeState with regime classification
        """
        if len(data) < 50:
            return RegimeState('unknown', 0.0, 0.0, 0.0, 0)

        # Calculate ADX
        adx = self._calculate_adx(data)

        # Calculate volatility (20-day)
        returns = data['close'].pct_change()
        volatility = returns.rolling(20).std().iloc[-1]

        # Calculate trend direction using 20/50 EMA
        ema_20 = data['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = data['close'].ewm(span=50).mean().iloc[-1]
        price = data['close'].iloc[-1]

        trend_direction = 0
        if price > ema_20 > ema_50:
            trend_direction = 1
        elif price < ema_20 < ema_50:
            trend_direction = -1

        # Classify regime
        adx_trending = self.get_parameter('adx_trending_threshold', 25.0)
        adx_strong = self.get_parameter('adx_strong_trend', 35.0)
        vol_max = self.get_parameter('volatility_max', 0.04)

        if adx > adx_strong:
            if trend_direction > 0:
                regime = 'trending_up'
                strength = min(adx / 50, 1.0)
            elif trend_direction < 0:
                regime = 'trending_down'
                strength = min(adx / 50, 1.0)
            else:
                regime = 'volatile'
                strength = 0.5
        elif adx > adx_trending:
            if trend_direction > 0:
                regime = 'trending_up'
                strength = 0.6
            elif trend_direction < 0:
                regime = 'trending_down'
                strength = 0.6
            else:
                regime = 'ranging'
                strength = 0.5
        else:
            if volatility > vol_max:
                regime = 'volatile'
                strength = min(volatility / vol_max, 1.0)
            else:
                regime = 'ranging'
                strength = 0.7

        return RegimeState(
            regime=regime,
            strength=strength,
            adx=adx,
            volatility=volatility,
            trend_direction=trend_direction
        )

    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX (Average Directional Index)."""
        df = data.copy()

        # True Range
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)

        # Directional Movement
        df['dm_plus'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0), 0
        )
        df['dm_minus'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0), 0
        )

        # Smoothed
        df['tr_smooth'] = df['tr'].rolling(window=period).sum()
        df['dm_plus_smooth'] = df['dm_plus'].rolling(window=period).sum()
        df['dm_minus_smooth'] = df['dm_minus'].rolling(window=period).sum()

        # DI
        df['di_plus'] = 100 * (df['dm_plus_smooth'] / df['tr_smooth'])
        df['di_minus'] = 100 * (df['dm_minus_smooth'] / df['tr_smooth'])

        # DX and ADX
        df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'] + 1e-10)
        df['adx'] = df['dx'].rolling(window=period).mean()

        return df['adx'].iloc[-1] if not pd.isna(df['adx'].iloc[-1]) else 0.0

    def _get_ensemble_prediction(self, X: np.ndarray) -> Tuple[int, float, Dict[str, float]]:
        """
        Get weighted ensemble prediction.

        Args:
            X: Feature array (1, n_features)

        Returns:
            Tuple of (prediction, confidence, per_model_probs)
        """
        if not self.is_trained:
            return 1, 0.0, {}  # Neutral with zero confidence

        weighted_probs = np.zeros(3)  # [down, neutral, up]
        model_probs = {}

        for name, model in self.models.items():
            if not model.is_trained:
                continue

            try:
                probs = model.predict_proba(X)[0]
                weight = self.model_weights.get(name, 0.33)
                weighted_probs += probs * weight
                model_probs[name] = {
                    'down': probs[0],
                    'neutral': probs[1],
                    'up': probs[2]
                }
            except Exception as e:
                logger.debug(f"Model {name} prediction failed: {e}")

        # Normalize
        if weighted_probs.sum() > 0:
            weighted_probs /= weighted_probs.sum()

        prediction = np.argmax(weighted_probs)
        confidence = weighted_probs[prediction]

        return prediction, confidence, model_probs

    def _should_retrain(self, current_idx: int) -> bool:
        """Check if models should be retrained."""
        retrain_freq = self.get_parameter('retrain_frequency', 20)
        return current_idx - self.last_train_idx >= retrain_freq

    def generate_signals_for_symbol(self, symbol: str, data: pd.DataFrame) -> List[Signal]:
        """
        Generate signals for a specific symbol.

        Args:
            symbol: Stock symbol
            data: DataFrame with price data for the symbol

        Returns:
            List of Signal objects
        """
        data = data.copy()
        data.attrs['symbol'] = symbol
        return self.generate_signals(data)

    def generate_signals(self, data: pd.DataFrame, latest_only: bool = True) -> List[Signal]:
        """
        Generate ML-based trading signals.

        Args:
            data: DataFrame with OHLCV data
            latest_only: If True, only generate signal for latest bar

        Returns:
            List of Signal objects
        """
        if not self.validate_data(data):
            return []

        data = data.copy()
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        train_window = self.get_parameter('train_window', 120)
        min_samples = self.get_parameter('min_samples_for_training', 60)

        # Check if we have enough data
        if len(data) < min_samples:
            logger.debug(f"Insufficient data for {symbol}: {len(data)} bars")
            return []

        # Train or retrain models if needed
        if not self.is_trained or self._should_retrain(len(data)):
            train_data = data.tail(train_window) if len(data) > train_window else data
            self.train_models(train_data)

        if not self.is_trained:
            return []

        signals = []

        # Determine processing range
        min_bars = 60  # Need enough history for features
        if latest_only and len(data) > min_bars:
            start_idx = len(data) - 1
        else:
            start_idx = min_bars

        for i in range(start_idx, len(data)):
            current_data = data.iloc[:i+1]
            current_bar = data.iloc[i]
            current_price = float(current_bar['close'])

            # Check for exit signals first
            exit_signal = self._check_exit_conditions(symbol, current_price, current_bar, i, data)
            if exit_signal:
                signals.append(exit_signal)
                continue

            # Skip if we have a position
            if symbol in self.active_positions:
                continue

            # Get regime
            regime = self._calculate_regime(current_data.tail(60))

            # Engineer features for current bar
            try:
                features_df = self.feature_engineer.engineer_features(current_data.tail(60).copy())
                if len(features_df) == 0:
                    continue

                # Get features for last bar
                feature_cols = [col for col in features_df.columns
                              if col not in ['open', 'high', 'low', 'close', 'volume', 'next_return']]
                X = features_df[feature_cols].iloc[[-1]].values

                # Scale features
                if self.scaler is not None:
                    X = self.scaler.transform(X)

            except Exception as e:
                logger.debug(f"Feature engineering failed: {e}")
                continue

            # Get ensemble prediction
            prediction, confidence, model_probs = self._get_ensemble_prediction(X)

            # Generate signal based on prediction and regime
            signal = self._generate_signal_from_prediction(
                symbol=symbol,
                timestamp=current_bar.name,
                price=current_price,
                prediction=prediction,
                confidence=confidence,
                regime=regime,
                model_probs=model_probs
            )

            if signal:
                signals.append(signal)

                # Track position
                self.active_positions[symbol] = {
                    'entry_price': current_price,
                    'entry_time': current_bar.name,
                    'entry_idx': i,
                    'type': 'long' if signal.signal_type == SignalType.LONG else 'short',
                    'highest_price': current_price,
                    'lowest_price': current_price,
                    'confidence': confidence,
                    'regime': regime.regime
                }

        if signals:
            logger.info(f"Generated {len(signals)} ML signals for {symbol}")

        return signals

    def _generate_signal_from_prediction(
        self,
        symbol: str,
        timestamp: datetime,
        price: float,
        prediction: int,
        confidence: float,
        regime: RegimeState,
        model_probs: Dict[str, Dict[str, float]]
    ) -> Optional[Signal]:
        """
        Generate trading signal from ML prediction.

        Args:
            symbol: Stock symbol
            timestamp: Signal timestamp
            price: Current price
            prediction: Model prediction (0=down, 1=neutral, 2=up)
            confidence: Prediction confidence
            regime: Current market regime
            model_probs: Per-model probabilities

        Returns:
            Signal object or None
        """
        long_threshold = self.get_parameter('long_confidence_threshold', 0.60)
        short_threshold = self.get_parameter('short_confidence_threshold', 0.65)
        vol_max = self.get_parameter('volatility_max', 0.04)

        signal_type = None

        # LONG signal conditions
        if prediction == 2 and confidence >= long_threshold:
            # Long in trending up or ranging markets
            if regime.regime in ['trending_up', 'ranging']:
                signal_type = SignalType.LONG
                logger.info(
                    f"[{symbol}] LONG SIGNAL: confidence={confidence:.1%}, "
                    f"regime={regime.regime}, ADX={regime.adx:.1f}"
                )
            elif regime.regime == 'volatile' and confidence >= 0.70:
                # Higher threshold for volatile markets
                signal_type = SignalType.LONG
                logger.info(
                    f"[{symbol}] LONG (volatile): confidence={confidence:.1%}"
                )

        # SHORT signal conditions (stricter)
        elif prediction == 0 and confidence >= short_threshold:
            # Only short in confirmed downtrends with acceptable volatility
            if regime.regime == 'trending_down' and regime.volatility <= vol_max:
                signal_type = SignalType.SHORT
                logger.info(
                    f"[{symbol}] SHORT SIGNAL: confidence={confidence:.1%}, "
                    f"regime={regime.regime}, ADX={regime.adx:.1f}, vol={regime.volatility:.3f}"
                )
            elif regime.regime == 'ranging' and confidence >= 0.75 and regime.trend_direction < 0:
                # Very high confidence shorts in ranging with bearish bias
                signal_type = SignalType.SHORT
                logger.info(
                    f"[{symbol}] SHORT (ranging): confidence={confidence:.1%}"
                )

        if signal_type is None:
            return None

        # Calculate dynamic position size
        position_size = self._calculate_dynamic_position_size(confidence, regime)

        return Signal(
            timestamp=timestamp,
            symbol=symbol,
            signal_type=signal_type,
            price=price,
            confidence=float(confidence),
            metadata={
                'strategy': 'ml_ensemble',
                'prediction': int(prediction),
                'regime': regime.regime,
                'regime_strength': float(regime.strength),
                'adx': float(regime.adx),
                'volatility': float(regime.volatility),
                'position_size_pct': float(position_size),
                'model_agreement': self._calculate_model_agreement(model_probs, prediction),
                'model_probs': model_probs
            }
        )

    def _calculate_dynamic_position_size(self, confidence: float, regime: RegimeState) -> float:
        """
        Calculate position size based on confidence and regime.

        Higher confidence = larger position
        Strong trend = larger position
        High volatility = smaller position
        """
        base_size = self.get_parameter('base_position_size', 0.15)
        max_size = self.get_parameter('max_position_size', 0.25)
        min_size = self.get_parameter('min_position_size', 0.05)

        # Start with base size
        size = base_size

        # Confidence multiplier (0.6 -> 0.8x, 0.8 -> 1.2x)
        confidence_mult = 0.5 + confidence  # 0.6 -> 1.1, 0.8 -> 1.3
        size *= confidence_mult

        # Regime multiplier
        if regime.regime in ['trending_up', 'trending_down']:
            size *= (1.0 + regime.strength * 0.3)  # Up to 30% increase
        elif regime.regime == 'volatile':
            size *= 0.7  # 30% reduction in volatile markets

        # Volatility adjustment (reduce for high vol)
        vol_max = self.get_parameter('volatility_max', 0.04)
        if regime.volatility > vol_max * 0.5:
            vol_ratio = regime.volatility / vol_max
            size *= max(0.5, 1.0 - vol_ratio * 0.5)

        # Clamp to limits
        return max(min_size, min(max_size, size))

    def _calculate_model_agreement(self, model_probs: Dict[str, Dict[str, float]], prediction: int) -> float:
        """Calculate how much models agree on the prediction."""
        if not model_probs:
            return 0.0

        pred_key = {0: 'down', 1: 'neutral', 2: 'up'}[prediction]
        agreements = [probs.get(pred_key, 0) for probs in model_probs.values()]

        return np.mean(agreements) if agreements else 0.0

    def _check_exit_conditions(
        self,
        symbol: str,
        current_price: float,
        current_bar: pd.Series,
        idx: int,
        data: pd.DataFrame
    ) -> Optional[Signal]:
        """Check if position should be exited."""
        if symbol not in self.active_positions:
            return None

        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        position_type = position['type']
        entry_idx = position['entry_idx']

        # Update tracking prices
        if position_type == 'long':
            position['highest_price'] = max(position['highest_price'], current_price)
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # short
            position['lowest_price'] = min(position['lowest_price'], current_price)
            pnl_pct = (entry_price - current_price) / entry_price

        bars_held = idx - entry_idx

        stop_loss = self.get_parameter('stop_loss_pct', 0.02)
        take_profit = self.get_parameter('take_profit_pct', 0.04)
        trailing_stop = self.get_parameter('trailing_stop_pct', 0.015)

        exit_reason = None

        # Stop-loss (immediate)
        if pnl_pct <= -stop_loss:
            exit_reason = 'stop_loss'

        # Take-profit (after minimum hold)
        elif pnl_pct >= take_profit and bars_held >= 3:
            exit_reason = 'take_profit'

        # Trailing stop
        elif bars_held >= 5:
            if position_type == 'long':
                drawdown = (position['highest_price'] - current_price) / position['highest_price']
                if drawdown >= trailing_stop and pnl_pct > 0:
                    exit_reason = 'trailing_stop'
            else:  # short
                drawup = (current_price - position['lowest_price']) / position['lowest_price']
                if drawup >= trailing_stop and pnl_pct > 0:
                    exit_reason = 'trailing_stop'

        # Time-based exit (max hold 30 bars)
        elif bars_held >= 30:
            exit_reason = 'time_exit'

        if exit_reason:
            del self.active_positions[symbol]

            logger.info(
                f"[{symbol}] EXIT ({exit_reason}): P&L={pnl_pct:.2%}, "
                f"bars_held={bars_held}, confidence={position['confidence']:.1%}"
            )

            return Signal(
                timestamp=current_bar.name,
                symbol=symbol,
                signal_type=SignalType.EXIT,
                price=current_price,
                confidence=1.0,
                metadata={
                    'exit_reason': exit_reason,
                    'pnl_pct': float(pnl_pct),
                    'bars_held': bars_held,
                    'entry_price': entry_price,
                    'position_type': position_type,
                    'entry_confidence': position['confidence'],
                    'entry_regime': position['regime']
                }
            )

        return None

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """Calculate position size from signal metadata."""
        position_size_pct = signal.metadata.get(
            'position_size_pct',
            self.get_parameter('base_position_size', 0.15)
        )

        position_value = account_value * position_size_pct
        shares = position_value / signal.price

        # Scale by confidence
        shares *= signal.confidence

        return round(shares, 2)


class XGBoostClassifier:
    """XGBoost classifier wrapper for ensemble."""

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        random_state: int = 42
    ):
        """Initialize XGBoost classifier."""
        if not HAS_XGBOOST:
            raise ImportError("XGBoost not available")

        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=random_state,
            use_label_encoder=False,
            eval_metric='mlogloss'
        )
        self.is_trained = False
        self.neutral_threshold = 0.001

    def create_trend_labels(self, returns: np.ndarray) -> np.ndarray:
        """Create trend labels from returns."""
        labels = np.ones_like(returns, dtype=int)  # Default neutral
        labels[returns > self.neutral_threshold] = 2  # Up
        labels[returns < -self.neutral_threshold] = 0  # Down
        return labels

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train XGBoost model."""
        if np.max(y) <= 2 and np.min(y) >= 0:
            y_labels = y.astype(int)
        else:
            y_labels = self.create_trend_labels(y)

        self.model.fit(X, y_labels)
        self.is_trained = True

        y_pred = self.model.predict(X)
        from sklearn.metrics import accuracy_score

        return {'train_accuracy': accuracy_score(y_labels, y_pred)}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict classes."""
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities."""
        return self.model.predict_proba(X)
