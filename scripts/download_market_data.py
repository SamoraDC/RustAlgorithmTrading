#!/usr/bin/env python3
"""
Market Data Download Script with Auto-Retry and Smart Fallback

This script downloads historical market data from Alpaca API with:
- Automatic retry logic with exponential backoff
- Data validation and error handling
- Progress tracking and logging
- Support for multiple symbols and date ranges
- Dual format output (CSV + Parquet)

Usage:
    python download_market_data.py --symbols AAPL MSFT GOOGL --days 365
    python download_market_data.py --config download_config.json
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd
import pyarrow.parquet as pq
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MarketDataDownloader:
    """
    Smart market data downloader with auto-retry and validation.

    Features:
    - Automatic data availability checking
    - Smart fallback to available date ranges
    - Comprehensive error handling
    - Data format validation
    - Progress tracking
    """

    def __init__(
        self,
        symbols: List[str],
        data_dir: Path,
        days_back: int = 365,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ):
        """
        Initialize market data downloader.

        Args:
            symbols: List of stock symbols to download
            data_dir: Directory to save data files
            days_back: Number of days of historical data
            api_key: Alpaca API key (or from env)
            api_secret: Alpaca API secret (or from env)
        """
        self.symbols = symbols
        self.data_dir = Path(data_dir)
        self.days_back = days_back

        # Get API credentials
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.api_secret = api_secret or os.getenv('ALPACA_SECRET_KEY')

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )

        # Initialize Alpaca client
        self.client = StockHistoricalDataClient(self.api_key, self.api_secret)

        # Create output directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "historical").mkdir(exist_ok=True)

        # Statistics
        self.stats = {
            'successful': 0,
            'failed': 0,
            'total_rows': 0
        }

        logger.info(f"Initialized downloader for {len(symbols)} symbols")

    def _get_date_range(self) -> tuple[datetime, datetime]:
        """
        Calculate optimal date range for download.

        Returns:
            Tuple of (start_date, end_date)
        """
        # CRITICAL FIX: Get current date and ensure we NEVER use future dates
        # Use date() to strip time component for consistent comparison
        today = datetime.now().date()

        # Calculate end_date: ALWAYS use yesterday to ensure market data is available
        # Market data for "today" may not be complete until after market close
        end_date = datetime.combine(today - timedelta(days=1), datetime.min.time())

        # Calculate start_date
        start_date = end_date - timedelta(days=self.days_back)

        # Adjust for market days only (weekends)
        # Move start date back if it's a weekend
        while start_date.weekday() >= 5:  # Saturday=5, Sunday=6
            start_date -= timedelta(days=1)

        # Move end date back if it's a weekend
        while end_date.weekday() >= 5:
            end_date -= timedelta(days=1)

        # DOUBLE VALIDATION: ensure end_date never exceeds today
        today_datetime = datetime.combine(today, datetime.min.time())
        if end_date > today_datetime:
            logger.warning(f"CRITICAL: End date {end_date.date()} exceeds today {today}, forcing to yesterday")
            end_date = today_datetime - timedelta(days=1)
            # Re-adjust if yesterday was a weekend
            while end_date.weekday() >= 5:
                end_date -= timedelta(days=1)

        logger.info(f"Date range: {start_date.date()} to {end_date.date()} (today is {today})")
        return start_date, end_date

    def _fetch_symbol_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        retry_count: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single symbol with retry logic.

        Args:
            symbol: Stock symbol
            start_date: Start date for data
            end_date: End date for data
            retry_count: Number of retry attempts

        Returns:
            DataFrame with market data or None on failure
        """
        for attempt in range(retry_count):
            try:
                logger.info(f"Fetching {symbol} (attempt {attempt + 1}/{retry_count})")

                request = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )

                bars = self.client.get_stock_bars(request)

                if not bars:
                    logger.warning(f"No response from API for {symbol}")
                    # Try with shorter date range on first attempt only
                    if attempt == 0 and self.days_back > 90:
                        logger.info(f"Retrying {symbol} with 90-day range")
                        new_start = end_date - timedelta(days=90)
                        remaining_retries = max(1, retry_count - 1)
                        return self._fetch_symbol_data(symbol, new_start, end_date, remaining_retries)
                    continue

                # Convert to DataFrame
                df = bars.df

                # CRITICAL FIX: Check if DataFrame is empty, not if symbol is in bars object
                if df is None or df.empty:
                    logger.warning(f"No data returned for {symbol} (empty DataFrame)")
                    # Try with shorter date range on first attempt only
                    if attempt == 0 and self.days_back > 90:
                        logger.info(f"Retrying {symbol} with 90-day range")
                        new_start = end_date - timedelta(days=90)
                        remaining_retries = max(1, retry_count - 1)
                        return self._fetch_symbol_data(symbol, new_start, end_date, remaining_retries)
                    continue

                if isinstance(df.index, pd.MultiIndex):
                    df = df.reset_index()
                else:
                    df = df.reset_index()

                # Standardize columns
                df = df.rename(columns={
                    'timestamp': 'timestamp',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'trade_count': 'trade_count',
                    'vwap': 'vwap'
                })

                # Add missing columns
                if 'vwap' not in df.columns:
                    df['vwap'] = (df['high'] + df['low'] + df['close']) / 3

                if 'trade_count' not in df.columns:
                    df['trade_count'] = 0

                # Ensure timestamp is datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Add symbol column
                df['symbol'] = symbol

                # Reorder columns
                columns = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'trade_count']
                df = df[[col for col in columns if col in df.columns]]

                logger.info(f"Successfully fetched {len(df)} rows for {symbol}")
                return df

            except Exception as e:
                error_message = str(e)
                logger.error(f"Error fetching {symbol} (attempt {attempt + 1}): {e}")

                # Detect rate limit errors
                if "rate limit" in error_message.lower() or "429" in error_message:
                    logger.warning(f"Rate limit detected for {symbol}")
                    if attempt < retry_count - 1:
                        import time
                        # Longer delay for rate limits with exponential backoff
                        delay = min(60, 5 * (2 ** attempt))  # 5s, 10s, 20s, capped at 60s
                        logger.info(f"Rate limit: waiting {delay} seconds before retry...")
                        time.sleep(delay)
                elif "403" in error_message or "forbidden" in error_message.lower():
                    logger.error(f"Authentication error - check ALPACA_API_KEY and ALPACA_SECRET_KEY in .env")
                    return None  # Don't retry auth errors
                elif attempt < retry_count - 1:
                    import time
                    delay = 5 * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                    logger.info(f"Retrying in {delay} seconds (exponential backoff)...")
                    time.sleep(delay)

        logger.error(f"Failed to fetch {symbol} after {retry_count} attempts")
        logger.error(f"Possible causes: 1) Invalid date range 2) API credentials 3) Symbol not found 4) Rate limiting")
        return None

    def _validate_data(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Validate downloaded data.

        Args:
            df: DataFrame to validate
            symbol: Symbol being validated

        Returns:
            True if valid, False otherwise
        """
        if df is None or df.empty:
            logger.error(f"No data for {symbol}")
            return False

        required_columns = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        missing = required_columns - set(df.columns)

        if missing:
            logger.error(f"Missing columns for {symbol}: {missing}")
            return False

        # Check for invalid prices
        if (df['high'] < df['low']).any():
            logger.error(f"Invalid price data for {symbol}: high < low")
            return False

        if (df['open'] < 0).any() or (df['close'] < 0).any():
            logger.error(f"Negative prices for {symbol}")
            return False

        logger.debug(f"Validated {len(df)} rows for {symbol}")
        return True

    def _save_data(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Save data in both CSV and Parquet formats.

        Args:
            df: DataFrame to save
            symbol: Stock symbol

        Returns:
            True if successful
        """
        try:
            # Save CSV (for compatibility)
            csv_path = self.data_dir / "historical" / f"{symbol}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved CSV: {csv_path}")

            # Save Parquet (for performance)
            parquet_path = self.data_dir / "historical" / f"{symbol}.parquet"
            df.to_parquet(parquet_path, compression='snappy', index=False)
            logger.info(f"Saved Parquet: {parquet_path}")

            return True

        except Exception as e:
            logger.error(f"Error saving {symbol}: {e}")
            return False

    def download_symbol(self, symbol: str) -> bool:
        """
        Download data for a single symbol.

        Args:
            symbol: Stock symbol

        Returns:
            True if successful
        """
        logger.info(f"Processing {symbol}...")

        start_date, end_date = self._get_date_range()
        df = self._fetch_symbol_data(symbol, start_date, end_date)

        if not self._validate_data(df, symbol):
            self.stats['failed'] += 1
            return False

        if not self._save_data(df, symbol):
            self.stats['failed'] += 1
            return False

        self.stats['successful'] += 1
        self.stats['total_rows'] += len(df)
        return True

    def download_all(self) -> Dict[str, Any]:
        """
        Download data for all symbols.

        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting download for {len(self.symbols)} symbols")
        start_time = datetime.now()

        for symbol in self.symbols:
            self.download_symbol(symbol)

        duration = (datetime.now() - start_time).total_seconds()

        # Summary
        logger.info("=" * 60)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total symbols: {len(self.symbols)}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Total rows: {self.stats['total_rows']}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 60)

        return self.stats


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Download market data from Alpaca API'
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['AAPL', 'MSFT', 'GOOGL'],
        help='Stock symbols to download'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days of historical data'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='data',
        help='Output directory for data files'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to JSON configuration file'
    )

    args = parser.parse_args()

    try:
        # Load config if provided
        if args.config:
            with open(args.config, 'r') as f:
                config = json.load(f)
                args.symbols = config.get('symbols', args.symbols)
                args.days = config.get('days_back', args.days)
                args.output_dir = config.get('output_dir', args.output_dir)

        # Initialize downloader
        downloader = MarketDataDownloader(
            symbols=args.symbols,
            data_dir=Path(args.output_dir),
            days_back=args.days
        )

        # Execute download
        stats = downloader.download_all()

        # Exit with appropriate code
        if stats['failed'] > 0:
            logger.warning(f"Completed with {stats['failed']} failures")
            sys.exit(1)
        else:
            logger.info("All downloads completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
