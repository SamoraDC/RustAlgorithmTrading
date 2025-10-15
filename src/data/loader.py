"""
Data loading and preprocessing pipeline.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np
from loguru import logger


class DataLoader:
    """
    Unified data loader for OHLCV market data.

    Supports:
    - CSV/Parquet formats
    - Multiple data sources
    - Data validation and cleaning
    - Resampling and aggregation
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        cache_enabled: bool = True,
    ):
        """
        Initialize data loader.

        Args:
            data_dir: Directory containing data files
            cache_enabled: Enable in-memory caching
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data')
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, pd.DataFrame] = {}

        logger.info(f"Initialized DataLoader (data_dir={self.data_dir})")

    def load_ohlcv(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timeframe: str = '1D',
        source: str = 'csv',
    ) -> pd.DataFrame:
        """
        Load OHLCV data for symbol.

        Args:
            symbol: Symbol to load
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe (1D, 1H, etc.)
            source: Data source (csv, parquet)

        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{timeframe}_{source}"

        # Check cache
        if self.cache_enabled and cache_key in self.cache:
            df = self.cache[cache_key]
            logger.debug(f"Loaded {symbol} from cache ({len(df)} bars)")
        else:
            # Load from file
            df = self._load_from_file(symbol, source)

            if self.cache_enabled:
                self.cache[cache_key] = df

        # Filter by date range
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        # Resample if needed
        if timeframe != '1D':
            df = self._resample_data(df, timeframe)

        logger.info(
            f"Loaded {len(df)} bars for {symbol} "
            f"from {df.index.min()} to {df.index.max()}"
        )

        return df

    def load_multiple(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timeframe: str = '1D',
    ) -> Dict[str, pd.DataFrame]:
        """
        Load data for multiple symbols.

        Args:
            symbols: List of symbols
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe

        Returns:
            Dictionary of symbol -> DataFrame
        """
        data = {}

        for symbol in symbols:
            try:
                df = self.load_ohlcv(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe,
                )
                data[symbol] = df
            except Exception as e:
                logger.error(f"Failed to load {symbol}: {e}")

        logger.info(f"Loaded data for {len(data)}/{len(symbols)} symbols")
        return data

    def _load_from_file(self, symbol: str, source: str) -> pd.DataFrame:
        """
        Load data from file.

        Args:
            symbol: Symbol to load
            source: File format (csv, parquet)

        Returns:
            DataFrame with data
        """
        if source == 'parquet':
            file_path = self.data_dir / f"{symbol}.parquet"
            df = pd.read_parquet(file_path)
        else:
            file_path = self.data_dir / f"{symbol}.csv"
            df = pd.read_csv(file_path, parse_dates=['timestamp'])
            df.set_index('timestamp', inplace=True)

        # Validate and clean data
        df = self._validate_data(df)

        return df

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean OHLCV data.

        Args:
            df: DataFrame to validate

        Returns:
            Cleaned DataFrame
        """
        # Required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]

        # Sort by index
        df = df.sort_index()

        # Validate OHLC relationships
        invalid_high = df['high'] < df[['open', 'close', 'low']].max(axis=1)
        invalid_low = df['low'] > df[['open', 'close', 'high']].min(axis=1)

        if invalid_high.any() or invalid_low.any():
            logger.warning(f"Found {invalid_high.sum() + invalid_low.sum()} invalid OHLC bars")
            # Fix invalid bars
            df.loc[invalid_high, 'high'] = df[['open', 'close', 'low']].max(axis=1)
            df.loc[invalid_low, 'low'] = df[['open', 'close', 'high']].min(axis=1)

        # Remove negative prices
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            df = df[df[col] > 0]

        # Remove negative volume
        df = df[df['volume'] >= 0]

        # Forward fill missing values (conservative)
        df = df.ffill()

        return df

    def _resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample data to different timeframe.

        Args:
            df: DataFrame to resample
            timeframe: Target timeframe (1H, 4H, 1D, etc.)

        Returns:
            Resampled DataFrame
        """
        # Convert timeframe to pandas offset
        timeframe_map = {
            '1min': '1T',
            '5min': '5T',
            '15min': '15T',
            '1H': '1H',
            '4H': '4H',
            '1D': '1D',
            '1W': '1W',
        }

        freq = timeframe_map.get(timeframe, timeframe)

        # Resample OHLCV
        resampled = df.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        })

        # Remove NaN rows
        resampled = resampled.dropna()

        logger.debug(f"Resampled to {timeframe}: {len(df)} -> {len(resampled)} bars")

        return resampled

    def save_data(
        self,
        symbol: str,
        data: pd.DataFrame,
        format: str = 'parquet',
    ):
        """
        Save data to file.

        Args:
            symbol: Symbol name
            data: DataFrame to save
            format: File format (csv, parquet)
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if format == 'parquet':
            file_path = self.data_dir / f"{symbol}.parquet"
            data.to_parquet(file_path)
        else:
            file_path = self.data_dir / f"{symbol}.csv"
            data.to_csv(file_path)

        logger.info(f"Saved {len(data)} bars for {symbol} to {file_path}")

    def clear_cache(self):
        """Clear data cache."""
        self.cache.clear()
        logger.info("Data cache cleared")
