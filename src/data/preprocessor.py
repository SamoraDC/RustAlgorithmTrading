"""
Data preprocessing module for cleaning and transforming market data
"""

import pandas as pd
import numpy as np
from typing import Optional, List
from loguru import logger


class DataPreprocessor:
    """
    Preprocesses market data for analysis and trading
    """

    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add common technical indicators to price data

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added technical indicators
        """
        df = df.copy()

        # Moving averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()

        # Exponential moving averages
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()

        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # Average True Range (ATR)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()

        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        logger.info("Technical indicators added to DataFrame")
        return df

    @staticmethod
    def calculate_returns(df: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
        """
        Calculate returns for given periods

        Args:
            df: DataFrame with price data
            periods: Number of periods for return calculation

        Returns:
            DataFrame with returns column
        """
        df = df.copy()
        df['returns'] = df['close'].pct_change(periods)
        df['log_returns'] = np.log(df['close'] / df['close'].shift(periods))
        return df

    @staticmethod
    def normalize_data(
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = 'minmax'
    ) -> pd.DataFrame:
        """
        Normalize specified columns

        Args:
            df: Input DataFrame
            columns: Columns to normalize (default: all numeric)
            method: Normalization method ('minmax' or 'zscore')

        Returns:
            DataFrame with normalized columns
        """
        df = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in columns:
            if col in df.columns:
                if method == 'minmax':
                    min_val = df[col].min()
                    max_val = df[col].max()
                    df[f'{col}_norm'] = (df[col] - min_val) / (max_val - min_val)
                elif method == 'zscore':
                    mean = df[col].mean()
                    std = df[col].std()
                    df[f'{col}_norm'] = (df[col] - mean) / std

        logger.info(f"Normalized {len(columns)} columns using {method} method")
        return df

    @staticmethod
    def handle_missing_data(
        df: pd.DataFrame,
        method: str = 'forward_fill'
    ) -> pd.DataFrame:
        """
        Handle missing data in DataFrame

        Args:
            df: Input DataFrame
            method: Method to handle missing data
                   ('forward_fill', 'backward_fill', 'drop', 'interpolate')

        Returns:
            DataFrame with missing data handled
        """
        df = df.copy()

        if method == 'forward_fill':
            df = df.fillna(method='ffill')
        elif method == 'backward_fill':
            df = df.fillna(method='bfill')
        elif method == 'drop':
            df = df.dropna()
        elif method == 'interpolate':
            df = df.interpolate()

        logger.info(f"Missing data handled using {method} method")
        return df

    @staticmethod
    def detect_outliers(
        df: pd.DataFrame,
        column: str,
        threshold: float = 3.0
    ) -> pd.Series:
        """
        Detect outliers using z-score method

        Args:
            df: Input DataFrame
            column: Column to check for outliers
            threshold: Z-score threshold for outlier detection

        Returns:
            Boolean series indicating outliers
        """
        z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
        outliers = z_scores > threshold

        logger.info(f"Found {outliers.sum()} outliers in {column}")
        return outliers

    @staticmethod
    def split_train_test(
        df: pd.DataFrame,
        train_ratio: float = 0.8
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into training and testing sets

        Args:
            df: Input DataFrame
            train_ratio: Ratio of training data (0-1)

        Returns:
            Tuple of (train_df, test_df)
        """
        split_index = int(len(df) * train_ratio)
        train_df = df.iloc[:split_index]
        test_df = df.iloc[split_index:]

        logger.info(f"Split data: train={len(train_df)}, test={len(test_df)}")
        return train_df, test_df
