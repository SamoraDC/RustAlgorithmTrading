"""
Feature Engineering Pipeline for ML Trading Strategies

This module implements comprehensive feature engineering for market data,
including technical indicators, statistical features, and temporal features.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, MinMaxScaler


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""
    lookback_periods: List[int] = None
    technical_indicators: List[str] = None
    statistical_features: List[str] = None
    scaling_method: str = 'standard'  # 'standard', 'minmax', 'robust'
    fill_na_method: str = 'forward'  # 'forward', 'backward', 'mean', 'zero'

    def __post_init__(self):
        if self.lookback_periods is None:
            self.lookback_periods = [5, 10, 20, 50]
        if self.technical_indicators is None:
            self.technical_indicators = ['sma', 'ema', 'rsi', 'macd', 'bbands']
        if self.statistical_features is None:
            self.statistical_features = ['returns', 'volatility', 'volume_ratio']


class FeatureEngineer:
    """
    Feature engineering pipeline for market data.

    This class transforms raw OHLCV data into feature-rich datasets
    suitable for machine learning models.

    Features:
    - Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
    - Statistical features (returns, volatility, skewness, kurtosis)
    - Temporal features (hour, day of week, month)
    - Lag features (historical values)
    - Rolling statistics (mean, std, min, max)

    Example:
        >>> fe = FeatureEngineer()
        >>> features_df = fe.engineer_features(ohlcv_data)
        >>> X, y = fe.prepare_ml_dataset(features_df, target_col='next_return')
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        """
        Initialize feature engineer.

        Args:
            config: Feature engineering configuration
        """
        self.config = config or FeatureConfig()
        self.scaler = self._create_scaler()
        self.feature_names: List[str] = []

    def _create_scaler(self):
        """Create appropriate scaler based on config."""
        if self.config.scaling_method == 'standard':
            return StandardScaler()
        elif self.config.scaling_method == 'minmax':
            return MinMaxScaler()
        else:
            from sklearn.preprocessing import RobustScaler
            return RobustScaler()

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all features from raw OHLCV data.

        Args:
            df: DataFrame with OHLCV columns (open, high, low, close, volume)

        Returns:
            DataFrame with engineered features
        """
        df = df.copy()

        # Technical indicators
        if 'sma' in self.config.technical_indicators:
            df = self._add_sma_features(df)
        if 'ema' in self.config.technical_indicators:
            df = self._add_ema_features(df)
        if 'rsi' in self.config.technical_indicators:
            df = self._add_rsi_features(df)
        if 'macd' in self.config.technical_indicators:
            df = self._add_macd_features(df)
        if 'bbands' in self.config.technical_indicators:
            df = self._add_bollinger_bands(df)

        # Statistical features
        if 'returns' in self.config.statistical_features:
            df = self._add_return_features(df)
        if 'volatility' in self.config.statistical_features:
            df = self._add_volatility_features(df)
        if 'volume_ratio' in self.config.statistical_features:
            df = self._add_volume_features(df)

        # Temporal features
        df = self._add_temporal_features(df)

        # Lag features
        df = self._add_lag_features(df)

        # Handle missing values
        df = self._handle_missing_values(df)

        # Store feature names
        self.feature_names = [col for col in df.columns
                            if col not in ['open', 'high', 'low', 'close', 'volume']]

        return df

    def _add_sma_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Simple Moving Average features."""
        for period in self.config.lookback_periods:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'close_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
        return df

    def _add_ema_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Exponential Moving Average features."""
        for period in self.config.lookback_periods:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            df[f'close_ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
        return df

    def _add_rsi_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Relative Strength Index features."""
        for period in [14, 28]:  # Standard RSI periods
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        return df

    def _add_macd_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD (Moving Average Convergence Divergence) features."""
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df

    def _add_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands features."""
        for period in [20, 50]:
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            df[f'bb_upper_{period}'] = sma + (2 * std)
            df[f'bb_lower_{period}'] = sma - (2 * std)
            df[f'bb_position_{period}'] = (df['close'] - df[f'bb_lower_{period}']) / \
                                          (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}'])
        return df

    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add return-based features."""
        # Simple returns
        df['returns'] = df['close'].pct_change()

        # Log returns
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # Multi-period returns
        for period in self.config.lookback_periods:
            df[f'returns_{period}d'] = df['close'].pct_change(periods=period)

        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based features."""
        for period in self.config.lookback_periods:
            # Historical volatility
            df[f'volatility_{period}d'] = df['returns'].rolling(window=period).std()

            # Parkinson volatility (uses high/low)
            df[f'parkinson_vol_{period}d'] = np.sqrt(
                (1 / (4 * period * np.log(2))) *
                (np.log(df['high'] / df['low']) ** 2).rolling(window=period).sum()
            )
        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        for period in self.config.lookback_periods:
            # Volume ratio (current vs average)
            df[f'volume_ratio_{period}d'] = df['volume'] / \
                df['volume'].rolling(window=period).mean()

            # Volume-weighted average price
            df[f'vwap_{period}d'] = (df['close'] * df['volume']).rolling(window=period).sum() / \
                df['volume'].rolling(window=period).sum()

        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        if isinstance(df.index, pd.DatetimeIndex):
            df['hour'] = df.index.hour
            df['day_of_week'] = df.index.dayofweek
            df['day_of_month'] = df.index.day
            df['month'] = df.index.month
            df['quarter'] = df.index.quarter

            # Cyclical encoding for temporal features
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add lagged features."""
        lag_periods = [1, 2, 3, 5]

        for lag in lag_periods:
            df[f'close_lag_{lag}'] = df['close'].shift(lag)
            df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
            df[f'returns_lag_{lag}'] = df['returns'].shift(lag)

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values based on config."""
        if self.config.fill_na_method == 'forward':
            df = df.fillna(method='ffill')
        elif self.config.fill_na_method == 'backward':
            df = df.fillna(method='bfill')
        elif self.config.fill_na_method == 'mean':
            df = df.fillna(df.mean())
        elif self.config.fill_na_method == 'zero':
            df = df.fillna(0)

        # Drop remaining NaN values
        df = df.dropna()

        return df

    def prepare_ml_dataset(
        self,
        df: pd.DataFrame,
        target_col: str = 'next_return',
        feature_cols: Optional[List[str]] = None,
        scale_features: bool = True
    ) -> tuple:
        """
        Prepare dataset for ML training.

        Args:
            df: DataFrame with features
            target_col: Name of target column
            feature_cols: List of feature columns (if None, use all engineered features)
            scale_features: Whether to scale features

        Returns:
            Tuple of (X, y) arrays
        """
        # Create target variable if not exists
        if target_col not in df.columns:
            if target_col == 'next_return':
                df['next_return'] = df['close'].pct_change().shift(-1)
            elif target_col == 'next_close':
                df['next_close'] = df['close'].shift(-1)

        # Select features
        if feature_cols is None:
            feature_cols = self.feature_names

        # Prepare X and y
        X = df[feature_cols].values
        y = df[target_col].values

        # Remove rows with NaN in target
        mask = ~np.isnan(y)
        X = X[mask]
        y = y[mask]

        # Scale features
        if scale_features:
            X = self.scaler.fit_transform(X)

        return X, y

    def get_feature_importance_names(self) -> List[str]:
        """Get list of feature names for importance analysis."""
        return self.feature_names
