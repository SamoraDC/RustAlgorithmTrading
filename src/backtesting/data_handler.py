"""
Historical data handler for backtesting.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from loguru import logger

from src.models.market import Bar
from src.models.events import MarketEvent


class HistoricalDataHandler:
    """
    Handles historical market data replay for backtesting.

    Supports CSV and Parquet formats with efficient data loading and bar generation.
    """

    def __init__(
        self,
        symbols: list[str],
        data_dir: Path,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Initialize historical data handler.

        Args:
            symbols: List of symbols to load
            data_dir: Directory containing historical data files
            start_date: Start date for data
            end_date: End date for data
        """
        self.symbols = symbols
        self.data_dir = Path(data_dir)
        self.start_date = start_date
        self.end_date = end_date

        self.symbol_data: Dict[str, pd.DataFrame] = {}
        self.latest_bars: Dict[str, list[Bar]] = {s: [] for s in symbols}
        self.continue_backtest = True
        self.bar_index = 0

        self._load_data()

        logger.info(
            f"Loaded historical data for {len(symbols)} symbols "
            f"from {start_date} to {end_date}"
        )

    def _load_data(self):
        """Load historical data for all symbols."""
        for symbol in self.symbols:
            # Try Parquet first, fall back to CSV
            parquet_path = self.data_dir / f"{symbol}.parquet"
            csv_path = self.data_dir / f"{symbol}.csv"

            if parquet_path.exists():
                df = pd.read_parquet(parquet_path)
            elif csv_path.exists():
                df = pd.read_csv(csv_path, parse_dates=['timestamp'])
            else:
                logger.warning(f"No data file found for {symbol}")
                continue

            # Filter by date range
            if self.start_date:
                df = df[df['timestamp'] >= self.start_date]
            if self.end_date:
                df = df[df['timestamp'] <= self.end_date]

            # Ensure sorted by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)

            self.symbol_data[symbol] = df

            logger.info(
                f"Loaded {len(df)} bars for {symbol} "
                f"from {df['timestamp'].min()} to {df['timestamp'].max()}"
            )

    def update_bars(self):
        """
        Update latest bars for all symbols.

        This method advances the data replay by one bar for each symbol.
        """
        for symbol in self.symbols:
            if symbol not in self.symbol_data:
                continue

            df = self.symbol_data[symbol]

            if self.bar_index >= len(df):
                self.continue_backtest = False
                continue

            # Get next bar
            row = df.iloc[self.bar_index]

            bar = Bar(
                symbol=symbol,
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume'],
                vwap=row.get('vwap'),
                trade_count=row.get('trade_count'),
            )

            self.latest_bars[symbol].append(bar)

        self.bar_index += 1

    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        """
        Get most recent bar for symbol.

        Args:
            symbol: Symbol to query

        Returns:
            Latest bar or None
        """
        try:
            return self.latest_bars[symbol][-1]
        except (IndexError, KeyError):
            return None

    def get_latest_bars(self, symbol: str, n: int = 1) -> list[Bar]:
        """
        Get N most recent bars for symbol.

        Args:
            symbol: Symbol to query
            n: Number of bars to retrieve

        Returns:
            List of bars (oldest to newest)
        """
        try:
            return self.latest_bars[symbol][-n:]
        except KeyError:
            return []

    def get_latest_bar_value(self, symbol: str, field: str) -> Optional[float]:
        """
        Get specific field value from latest bar.

        Args:
            symbol: Symbol to query
            field: Field name (open, high, low, close, volume)

        Returns:
            Field value or None
        """
        bar = self.get_latest_bar(symbol)
        if bar:
            return getattr(bar, field, None)
        return None

    def get_latest_bars_values(
        self, symbol: str, field: str, n: int = 1
    ) -> list[float]:
        """
        Get field values from N most recent bars.

        Args:
            symbol: Symbol to query
            field: Field name
            n: Number of bars

        Returns:
            List of field values
        """
        bars = self.get_latest_bars(symbol, n)
        return [getattr(bar, field) for bar in bars if hasattr(bar, field)]
