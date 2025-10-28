"""
Statistical Arbitrage Strategy using Cointegration

This strategy identifies pairs of stocks that are cointegrated (move together in the long run)
and trades mean reversion when they diverge.

Based on:
- Engle-Granger cointegration test
- Ornstein-Uhlenbeck mean reversion model
- Kalman filter for dynamic hedge ratio estimation
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from loguru import logger

from src.strategies.base import Strategy, Signal, SignalType


class StatisticalArbitrageStrategy(Strategy):
    """
    Pairs trading strategy using cointegration

    The strategy:
    1. Tests pairs for cointegration
    2. Calculates spread as residual from cointegration regression
    3. Trades when spread deviates from mean
    4. Exits when spread reverts

    Parameters:
        entry_threshold: Z-score threshold for entry (default: 2.0)
        exit_threshold: Z-score threshold for exit (default: 0.5)
        lookback_period: Period for calculating statistics (default: 60)
        position_size_pct: Position size as % of account (default: 0.1)
        max_holding_period: Maximum bars to hold (default: 20)
    """

    def __init__(
        self,
        name: str = "StatisticalArbitrage",
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize statistical arbitrage strategy"""
        default_params = {
            'entry_threshold': 2.0,
            'exit_threshold': 0.5,
            'lookback_period': 60,
            'position_size_pct': 0.1,
            'max_holding_period': 20,
            'min_half_life': 1,      # Minimum mean reversion speed
            'max_half_life': 30,     # Maximum mean reversion speed
            'confidence_level': 0.05  # p-value for cointegration test
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, default_params)
        self.hedge_ratio = None
        self.spread_mean = None
        self.spread_std = None
        self.entry_bars = {}

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Generate signals for pairs trading

        Args:
            data: DataFrame with prices for both stocks
                Columns should include: close, close_y (for the pair)

        Returns:
            List of trading signals
        """
        if not self._validate_pair_data(data):
            return []

        signals = []
        symbol = data.attrs.get('symbol', 'UNKNOWN')

        # Check for cointegration
        if not self._test_cointegration(data):
            logger.warning(f"Pair {symbol} is not cointegrated")
            return []

        # Calculate spread
        spread = self._calculate_spread(data)

        if spread is None or len(spread) < self.get_parameter('lookback_period', 60):
            return []

        # Calculate half-life of mean reversion
        half_life = self._calculate_half_life(spread)
        min_hl = self.get_parameter('min_half_life', 1)
        max_hl = self.get_parameter('max_half_life', 30)

        if half_life < min_hl or half_life > max_hl:
            logger.info(f"Half-life {half_life:.1f} outside acceptable range")
            return []

        logger.info(f"Spread half-life: {half_life:.1f} bars")

        # Generate signals based on z-score
        lookback = self.get_parameter('lookback_period', 60)
        entry_threshold = self.get_parameter('entry_threshold', 2.0)
        exit_threshold = self.get_parameter('exit_threshold', 0.5)
        max_holding = self.get_parameter('max_holding_period', 20)

        for i in range(lookback, len(data)):
            current_time = data.index[i]
            current_price = data.iloc[i]['close']

            # Calculate rolling statistics
            window = spread[i-lookback:i]
            z_score = (spread.iloc[i] - window.mean()) / window.std()

            # Check if should exit
            if symbol in self.entry_bars:
                bars_held = i - self.entry_bars[symbol]['bar']
                entry_side = self.entry_bars[symbol]['side']

                # Exit conditions
                exit_signal = False
                exit_reason = ''

                if abs(z_score) < exit_threshold:
                    exit_signal = True
                    exit_reason = 'mean_reversion'
                elif bars_held >= max_holding:
                    exit_signal = True
                    exit_reason = 'max_holding_period'
                elif (entry_side == 'long' and z_score > entry_threshold) or \
                     (entry_side == 'short' and z_score < -entry_threshold):
                    exit_signal = True
                    exit_reason = 'stop_loss'

                if exit_signal:
                    signals.append(Signal(
                        timestamp=current_time,
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        price=current_price,
                        confidence=min(abs(z_score) / entry_threshold, 1.0),
                        metadata={
                            'z_score': z_score,
                            'spread': spread.iloc[i],
                            'reason': exit_reason,
                            'bars_held': bars_held
                        }
                    ))
                    del self.entry_bars[symbol]
                    continue

            # Entry conditions
            if symbol not in self.entry_bars:
                if z_score > entry_threshold:
                    # Spread too high - short spread (short stock A, long stock B)
                    signals.append(Signal(
                        timestamp=current_time,
                        symbol=symbol,
                        signal_type=SignalType.SHORT,
                        price=current_price,
                        confidence=min(z_score / entry_threshold, 1.0),
                        metadata={
                            'z_score': z_score,
                            'spread': spread.iloc[i],
                            'hedge_ratio': self.hedge_ratio,
                            'reason': 'spread_too_high'
                        }
                    ))
                    self.entry_bars[symbol] = {'bar': i, 'side': 'short'}

                elif z_score < -entry_threshold:
                    # Spread too low - long spread (long stock A, short stock B)
                    signals.append(Signal(
                        timestamp=current_time,
                        symbol=symbol,
                        signal_type=SignalType.LONG,
                        price=current_price,
                        confidence=min(abs(z_score) / entry_threshold, 1.0),
                        metadata={
                            'z_score': z_score,
                            'spread': spread.iloc[i],
                            'hedge_ratio': self.hedge_ratio,
                            'reason': 'spread_too_low'
                        }
                    ))
                    self.entry_bars[symbol] = {'bar': i, 'side': 'long'}

        logger.info(f"Generated {len(signals)} statistical arbitrage signals")
        return signals

    def _validate_pair_data(self, data: pd.DataFrame) -> bool:
        """Validate that data contains both series"""
        required = ['close', 'close_y']
        missing = [col for col in required if col not in data.columns]

        if missing:
            # Try alternative names
            if 'price_y' in data.columns:
                data['close_y'] = data['price_y']
            else:
                logger.error(f"Missing required columns for pairs: {missing}")
                return False

        return True

    def _test_cointegration(self, data: pd.DataFrame) -> bool:
        """
        Test if two series are cointegrated using Engle-Granger test

        Args:
            data: DataFrame with both price series

        Returns:
            True if cointegrated at specified confidence level
        """
        series1 = data['close'].values
        series2 = data['close_y'].values

        try:
            # Engle-Granger cointegration test
            score, pvalue, _ = coint(series1, series2)

            confidence = self.get_parameter('confidence_level', 0.05)
            is_cointegrated = pvalue < confidence

            logger.info(
                f"Cointegration test: score={score:.4f}, "
                f"p-value={pvalue:.4f}, cointegrated={is_cointegrated}"
            )

            return is_cointegrated

        except Exception as e:
            logger.error(f"Cointegration test failed: {e}")
            return False

    def _calculate_spread(self, data: pd.DataFrame) -> Optional[pd.Series]:
        """
        Calculate spread between two series

        Uses OLS regression to find hedge ratio, then calculates:
        spread = stock_a - hedge_ratio * stock_b

        Args:
            data: DataFrame with both price series

        Returns:
            Spread series
        """
        try:
            series1 = data['close'].values
            series2 = data['close_y'].values

            # OLS regression to find hedge ratio
            from scipy.stats import linregress
            slope, intercept, r_value, p_value, std_err = linregress(series2, series1)

            self.hedge_ratio = slope

            # Calculate spread
            spread = series1 - self.hedge_ratio * series2

            logger.info(
                f"Hedge ratio: {self.hedge_ratio:.4f}, "
                f"R²: {r_value**2:.4f}"
            )

            return pd.Series(spread, index=data.index)

        except Exception as e:
            logger.error(f"Error calculating spread: {e}")
            return None

    def _calculate_half_life(self, spread: pd.Series) -> float:
        """
        Calculate mean reversion half-life using Ornstein-Uhlenbeck model

        The half-life tells us how quickly the spread reverts to its mean.

        Args:
            spread: Spread series

        Returns:
            Half-life in number of bars
        """
        try:
            # Lag the spread
            spread_lag = spread.shift(1)
            spread_diff = spread - spread_lag

            # Remove NaN
            spread_lag = spread_lag.dropna()
            spread_diff = spread_diff.dropna()

            # Ensure same length
            min_len = min(len(spread_lag), len(spread_diff))
            spread_lag = spread_lag.iloc[-min_len:]
            spread_diff = spread_diff.iloc[-min_len:]

            # AR(1) regression
            from scipy.stats import linregress
            slope, intercept, _, _, _ = linregress(spread_lag.values, spread_diff.values)

            # Half-life = -ln(2) / ln(1 + slope)
            if slope < 0:
                half_life = -np.log(2) / np.log(1 + slope)
            else:
                half_life = np.inf

            return half_life

        except Exception as e:
            logger.warning(f"Error calculating half-life: {e}")
            return np.inf

    def calculate_position_size(
        self,
        signal: Signal,
        account_value: float,
        current_position: float = 0.0
    ) -> float:
        """
        Calculate position size for pairs trade

        Args:
            signal: Trading signal
            account_value: Current account value
            current_position: Current position

        Returns:
            Position size
        """
        position_pct = self.get_parameter('position_size_pct', 0.1)

        # Scale by confidence
        adjusted_pct = position_pct * signal.confidence

        target_value = account_value * adjusted_pct
        shares = target_value / signal.price

        return shares
