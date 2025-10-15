"""
Data fetching module for retrieving market data
"""

from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
from alpaca.data.timeframe import TimeFrame
from loguru import logger

from src.api.alpaca_client import AlpacaClient


class DataFetcher:
    """
    Fetches and manages market data from various sources
    """

    def __init__(self, client: AlpacaClient):
        """
        Initialize data fetcher

        Args:
            client: Alpaca client instance
        """
        self.client = client
        logger.info("DataFetcher initialized")

    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        start: datetime,
        end: datetime,
        timeframe: TimeFrame = TimeFrame.Day
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple symbols

        Args:
            symbols: List of stock symbols
            start: Start date
            end: End date
            timeframe: Data timeframe

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        data = {}

        for symbol in symbols:
            try:
                df = self.client.get_historical_bars(
                    symbol=symbol,
                    start=start,
                    end=end,
                    timeframe=timeframe
                )
                data[symbol] = df
                logger.info(f"Fetched data for {symbol}: {len(df)} bars")
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                data[symbol] = pd.DataFrame()

        return data

    def fetch_last_n_days(
        self,
        symbol: str,
        days: int = 365,
        timeframe: TimeFrame = TimeFrame.Day
    ) -> pd.DataFrame:
        """
        Fetch last N days of data

        Args:
            symbol: Stock symbol
            days: Number of days to fetch
            timeframe: Data timeframe

        Returns:
            DataFrame with historical data
        """
        end = datetime.now()
        start = end - timedelta(days=days)

        return self.client.get_historical_bars(
            symbol=symbol,
            start=start,
            end=end,
            timeframe=timeframe
        )

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Latest close price or None
        """
        try:
            df = self.fetch_last_n_days(symbol, days=1)
            if not df.empty:
                return float(df.iloc[-1]['close'])
            return None
        except Exception as e:
            logger.error(f"Failed to get latest price for {symbol}: {e}")
            return None
