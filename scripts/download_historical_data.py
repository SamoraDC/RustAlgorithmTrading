#!/usr/bin/env python3
"""
Production-Grade Historical Data Downloader for Alpaca API

Downloads historical market data from Alpaca and saves it in both CSV and Parquet formats.
Includes comprehensive error handling, logging, and progress tracking.

Usage:
    python download_historical_data.py --symbols AAPL MSFT GOOGL --start 2024-01-01 --end 2024-12-31
    python download_historical_data.py --config config.json
"""

import os
import sys
import json
import logging
import argparse
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_downloader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """Configuration for data download"""
    symbols: List[str]
    start_date: str
    end_date: str
    timeframe: str = "1Day"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    output_dir: str = "data"
    save_csv: bool = True
    save_parquet: bool = True
    chunk_size: int = 1000
    retry_attempts: int = 3
    retry_delay: int = 5
    max_retry_delay: int = 60  # Maximum delay cap for exponential backoff
    inter_symbol_delay: float = 1.0  # Delay between symbol downloads to prevent rate limiting
    feed: str = "iex"  # Data feed: 'iex' (free), 'sip' (requires subscription), or 'otc'
    adjustment: str = "all"  # Price adjustments: 'raw', 'split', 'dividend', or 'all'

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DownloadConfig':
        """Create config from dictionary"""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__annotations__})

    @classmethod
    def from_file(cls, config_path: str) -> 'DownloadConfig':
        """Load config from JSON file"""
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)


class AlpacaDataDownloader:
    """
    Production-grade downloader for Alpaca historical data

    Features:
    - Automatic retry with exponential backoff
    - Progress tracking with tqdm
    - Dual format output (CSV + Parquet)
    - Comprehensive error handling
    - Data validation
    - Resume capability
    """

    def __init__(self, config: DownloadConfig):
        """
        Initialize downloader with configuration

        Args:
            config: DownloadConfig object with all settings
        """
        self.config = config
        self.api_key = config.api_key or os.getenv('ALPACA_API_KEY')
        self.api_secret = config.api_secret or os.getenv('ALPACA_SECRET_KEY')

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables "
                "or provide them in the config."
            )

        # Initialize Alpaca client
        self.client = StockHistoricalDataClient(self.api_key, self.api_secret)

        # Setup output directories
        self.output_dir = Path(config.output_dir)
        self.csv_dir = self.output_dir / "csv"
        self.parquet_dir = self.output_dir / "parquet"

        self._create_directories()

        # Statistics tracking
        self.stats = {
            'total_symbols': len(config.symbols),
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_rows': 0,
            'rate_limit_hits': 0,
            'total_retries': 0,
            'start_time': None,
            'end_time': None
        }

        # Rate limit tracking
        self.consecutive_no_data = 0  # Track consecutive "No data" responses
        self.last_rate_limit_info = {}  # Store rate limit headers

        logger.info(f"Initialized AlpacaDataDownloader for {len(config.symbols)} symbols")

    def _create_directories(self) -> None:
        """Create output directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.config.save_csv:
            self.csv_dir.mkdir(parents=True, exist_ok=True)
        if self.config.save_parquet:
            self.parquet_dir.mkdir(parents=True, exist_ok=True)

        # Create logs directory
        Path('logs').mkdir(exist_ok=True)

    def _parse_timeframe(self, timeframe_str: str) -> TimeFrame:
        """
        Parse timeframe string to Alpaca TimeFrame object

        Args:
            timeframe_str: Timeframe string (e.g., "1Day", "1Hour", "5Min")

        Returns:
            TimeFrame object
        """
        timeframe_mapping = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, "Min"),
            "15Min": TimeFrame(15, "Min"),
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day,
        }

        if timeframe_str not in timeframe_mapping:
            logger.warning(f"Unknown timeframe '{timeframe_str}', defaulting to 1Day")
            return TimeFrame.Day

        return timeframe_mapping[timeframe_str]

    def _validate_dataframe(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Validate downloaded data

        Args:
            df: DataFrame to validate
            symbol: Symbol being validated

        Returns:
            True if valid, False otherwise
        """
        required_columns = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}

        if df.empty:
            logger.error(f"No data received for {symbol}")
            return False

        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            logger.error(f"Missing columns for {symbol}: {missing_columns}")
            return False

        # Check for null values
        null_counts = df[list(required_columns)].isnull().sum()
        if null_counts.any():
            logger.warning(f"Null values found in {symbol}: {null_counts[null_counts > 0].to_dict()}")

        # Validate price data
        if (df['high'] < df['low']).any():
            logger.error(f"Invalid price data for {symbol}: high < low")
            return False

        if (df['open'] < 0).any() or (df['close'] < 0).any():
            logger.error(f"Negative prices found for {symbol}")
            return False

        logger.info(f"Validated {len(df)} rows for {symbol}")
        return True

    def _is_rate_limited(self, error: Exception, response=None) -> bool:
        """
        Detect if an error or response indicates rate limiting

        Args:
            error: Exception that occurred
            response: Optional response object with headers

        Returns:
            True if rate limited, False otherwise
        """
        error_str = str(error).lower()

        # Check for HTTP 429 status code
        if "429" in error_str:
            logger.warning("Rate limit detected: HTTP 429 Too Many Requests")
            self.stats['rate_limit_hits'] += 1
            return True

        # Check for rate limit keywords in error message
        rate_limit_keywords = [
            "rate limit",
            "too many requests",
            "quota exceeded",
            "throttle",
            "slow down"
        ]

        if any(keyword in error_str for keyword in rate_limit_keywords):
            logger.warning(f"Rate limit detected in error message: {error_str}")
            self.stats['rate_limit_hits'] += 1
            return True

        # Check response headers if available
        if response and hasattr(response, 'headers'):
            self._check_rate_limit_headers(response.headers)

        return False

    def _check_rate_limit_headers(self, headers: Dict[str, str]) -> None:
        """
        Check and log rate limit information from response headers

        Args:
            headers: Response headers dictionary
        """
        rate_limit_headers = {
            'X-RateLimit-Limit': 'total_limit',
            'X-RateLimit-Remaining': 'remaining',
            'X-RateLimit-Reset': 'reset_time',
            'Retry-After': 'retry_after'
        }

        rate_info = {}
        for header, key in rate_limit_headers.items():
            if header in headers:
                rate_info[key] = headers[header]

        if rate_info:
            self.last_rate_limit_info = rate_info
            logger.info(f"Rate limit info: {rate_info}")

            # Warn if getting close to limit
            if 'remaining' in rate_info and 'total_limit' in rate_info:
                remaining = int(rate_info['remaining'])
                total = int(rate_info['total_limit'])
                percentage = (remaining / total) * 100 if total > 0 else 0

                if percentage < 20:
                    logger.warning(f"Rate limit warning: Only {remaining}/{total} ({percentage:.1f}%) requests remaining")

            # Log reset time if available
            if 'reset_time' in rate_info:
                reset_timestamp = int(rate_info['reset_time'])
                reset_time = datetime.fromtimestamp(reset_timestamp)
                logger.info(f"Rate limit resets at: {reset_time}")

    def _calculate_backoff_delay(self, attempt: int, is_rate_limited: bool = False) -> float:
        """
        Calculate delay with exponential backoff, jitter, and maximum cap

        Args:
            attempt: Current attempt number (0-indexed)
            is_rate_limited: Whether this is due to rate limiting

        Returns:
            Delay in seconds
        """
        # Base exponential backoff
        base_delay = self.config.retry_delay * (2 ** attempt)

        # Apply maximum delay cap
        capped_delay = min(base_delay, self.config.max_retry_delay)

        # Add jitter (random +/- 20%) to prevent thundering herd
        jitter_range = capped_delay * 0.2
        jitter = random.uniform(-jitter_range, jitter_range)
        final_delay = max(1.0, capped_delay + jitter)  # Never less than 1 second

        # If rate limited, use a longer delay
        if is_rate_limited:
            # Check for Retry-After header
            if 'retry_after' in self.last_rate_limit_info:
                retry_after = int(self.last_rate_limit_info['retry_after'])
                final_delay = max(final_delay, retry_after)
                logger.info(f"Using Retry-After header value: {retry_after} seconds")
            else:
                # Use at least 60 seconds for rate limit errors
                final_delay = max(final_delay, 60.0)

        return final_delay

    def _fetch_data_with_retry(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch data with automatic retry logic

        Args:
            symbol: Stock symbol to fetch

        Returns:
            DataFrame with historical data or None on failure
        """
        timeframe = self._parse_timeframe(self.config.timeframe)

        # Map adjustment string to enum
        adjustment_mapping = {
            "raw": Adjustment.RAW,
            "split": Adjustment.SPLIT,
            "dividend": Adjustment.DIVIDEND,
            "all": Adjustment.ALL
        }
        adjustment = adjustment_mapping.get(self.config.adjustment.lower(), Adjustment.ALL)

        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=timeframe,
            start=self.config.start_date,
            end=self.config.end_date,
            feed=self.config.feed,
            adjustment=adjustment
        )

        for attempt in range(self.config.retry_attempts):
            try:
                logger.info(f"Fetching data for {symbol} (attempt {attempt + 1}/{self.config.retry_attempts})")
                logger.debug(f"Request parameters: timeframe={timeframe}, start={self.config.start_date}, "
                           f"end={self.config.end_date}, feed={self.config.feed}, adjustment={adjustment}")

                # Fetch data from Alpaca
                bars = self.client.get_stock_bars(request_params)

                # Detailed debug logging
                logger.debug(f"API Response type: {type(bars)}")
                logger.debug(f"API Response data: {bars}")

                if not bars:
                    self.consecutive_no_data += 1
                    logger.error(f"No response from API for {symbol} (consecutive no-data count: {self.consecutive_no_data})")
                    logger.error(f"This may indicate: 1) Invalid date range, 2) No trading data for period, "
                               f"3) Data feed '{self.config.feed}' not available for paper trading account, "
                               f"4) Potential rate limiting (check if many consecutive failures)")

                    # Warn if many consecutive no-data responses (possible rate limiting)
                    if self.consecutive_no_data >= 3:
                        logger.warning(f"Detected {self.consecutive_no_data} consecutive 'No data' responses - "
                                     f"this may indicate rate limiting. Adding extra delay...")
                        time.sleep(10)  # Add extra delay

                    return None

                # Reset consecutive no-data counter on successful response
                self.consecutive_no_data = 0

                # Convert to DataFrame first
                df = bars.df

                # CRITICAL FIX: Check if DataFrame is empty, not if symbol is in bars object
                if df is None or df.empty:
                    logger.error(f"No data in DataFrame for {symbol}")
                    logger.error(f"DataFrame is {'None' if df is None else 'empty'}")
                    logger.error(f"Possible causes: 1) No trading data for date range 2) Weekend/holiday 3) Invalid date range")
                    return None

                # Reset index to get timestamp as column
                if isinstance(df.index, pd.MultiIndex):
                    df = df.reset_index()
                else:
                    df = df.reset_index()

                # Rename columns to match expected format
                column_mapping = {
                    'timestamp': 'timestamp',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'trade_count': 'trade_count',
                    'vwap': 'vwap'
                }

                # Only rename columns that exist
                existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=existing_columns)

                # Add missing columns with default values
                if 'vwap' not in df.columns:
                    df['vwap'] = (df['high'] + df['low'] + df['close']) / 3
                    logger.info(f"Calculated VWAP for {symbol}")

                if 'trade_count' not in df.columns:
                    df['trade_count'] = 0
                    logger.info(f"Trade count not available for {symbol}, set to 0")

                # Ensure timestamp is datetime
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Add symbol column
                df['symbol'] = symbol

                # Reorder columns
                column_order = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'trade_count']
                df = df[[col for col in column_order if col in df.columns]]

                logger.info(f"Successfully fetched {len(df)} rows for {symbol}")
                return df

            except Exception as e:
                import traceback
                logger.error(f"Error fetching data for {symbol} (attempt {attempt + 1}/{self.config.retry_attempts}): {str(e)}")
                logger.debug(f"Full traceback: {traceback.format_exc()}")

                self.stats['total_retries'] += 1

                # Detect rate limiting
                is_rate_limited = self._is_rate_limited(e)

                # Provide helpful error context
                if "403" in str(e) or "unauthorized" in str(e).lower():
                    logger.error(f"Authorization error - check API credentials")
                elif "404" in str(e):
                    logger.error(f"Symbol {symbol} not found - verify it's a valid ticker")
                elif is_rate_limited:
                    logger.error(f"Rate limit exceeded - using extended backoff delay")
                elif "feed" in str(e).lower():
                    logger.error(f"Data feed error - try changing feed parameter from '{self.config.feed}' to 'sip' or 'iex'")

                if attempt < self.config.retry_attempts - 1:
                    # Calculate delay with exponential backoff, jitter, and cap
                    delay = self._calculate_backoff_delay(attempt, is_rate_limited)
                    logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{self.config.retry_attempts})...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to fetch data for {symbol} after {self.config.retry_attempts} attempts")
                    logger.error(f"Suggestions:")
                    logger.error(f"  1. Verify date range is valid (not weekends/holidays/future dates)")
                    logger.error(f"  2. Try feed='sip' instead of '{self.config.feed}'")
                    logger.error(f"  3. Check if paper trading account has data access")
                    logger.error(f"  4. Use recent dates (last 5 years for free data)")
                    logger.error(f"  5. If seeing many failures, try increasing --inter-symbol-delay")
                    return None

        return None

    def _save_csv(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Save DataFrame to CSV format

        Args:
            df: DataFrame to save
            symbol: Stock symbol

        Returns:
            True if successful, False otherwise
        """
        try:
            csv_path = self.csv_dir / f"{symbol}_{self.config.start_date}_{self.config.end_date}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved CSV: {csv_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving CSV for {symbol}: {str(e)}")
            return False

    def _save_parquet(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Save DataFrame to Parquet format with compression

        Args:
            df: DataFrame to save
            symbol: Stock symbol

        Returns:
            True if successful, False otherwise
        """
        try:
            parquet_path = self.parquet_dir / f"{symbol}_{self.config.start_date}_{self.config.end_date}.parquet"

            # Convert to PyArrow table for better control
            table = pa.Table.from_pandas(df)

            # Write with compression
            pq.write_table(
                table,
                parquet_path,
                compression='snappy',
                use_dictionary=True,
                write_statistics=True
            )

            logger.info(f"Saved Parquet: {parquet_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving Parquet for {symbol}: {str(e)}")
            return False

    def download_symbol(self, symbol: str) -> bool:
        """
        Download data for a single symbol

        Args:
            symbol: Stock symbol to download

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting download for {symbol}")

        # Fetch data
        df = self._fetch_data_with_retry(symbol)

        if df is None or df.empty:
            self.stats['failed_downloads'] += 1
            return False

        # Validate data
        if not self._validate_dataframe(df, symbol):
            self.stats['failed_downloads'] += 1
            return False

        # Save in requested formats
        success = True

        if self.config.save_csv:
            success &= self._save_csv(df, symbol)

        if self.config.save_parquet:
            success &= self._save_parquet(df, symbol)

        if success:
            self.stats['successful_downloads'] += 1
            self.stats['total_rows'] += len(df)
            logger.info(f"Successfully processed {symbol}")
        else:
            self.stats['failed_downloads'] += 1
            logger.error(f"Failed to save data for {symbol}")

        return success

    def download_all(self) -> Dict[str, Any]:
        """
        Download data for all configured symbols

        Returns:
            Dictionary with download statistics
        """
        self.stats['start_time'] = datetime.now()
        logger.info(f"Starting bulk download for {len(self.config.symbols)} symbols")
        logger.info(f"Using inter-symbol delay of {self.config.inter_symbol_delay} seconds to prevent rate limiting")

        # Download with progress bar
        with tqdm(total=len(self.config.symbols), desc="Downloading symbols") as pbar:
            for i, symbol in enumerate(self.config.symbols):
                self.download_symbol(symbol)
                pbar.update(1)

                # Add delay between symbols to prevent rate limiting
                # Skip delay after the last symbol
                if i < len(self.config.symbols) - 1 and self.config.inter_symbol_delay > 0:
                    time.sleep(self.config.inter_symbol_delay)

        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.stats['duration_seconds'] = duration

        # Log summary
        logger.info("=" * 80)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total symbols: {self.stats['total_symbols']}")
        logger.info(f"Successful downloads: {self.stats['successful_downloads']}")
        logger.info(f"Failed downloads: {self.stats['failed_downloads']}")
        logger.info(f"Total rows downloaded: {self.stats['total_rows']}")
        logger.info(f"Rate limit hits: {self.stats['rate_limit_hits']}")
        logger.info(f"Total retries: {self.stats['total_retries']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Average time per symbol: {duration / len(self.config.symbols):.2f} seconds")
        if self.last_rate_limit_info:
            logger.info(f"Last rate limit info: {self.last_rate_limit_info}")
        logger.info("=" * 80)

        # Save statistics
        self._save_statistics()

        return self.stats

    def _save_statistics(self) -> None:
        """Save download statistics to JSON file"""
        try:
            stats_path = self.output_dir / f"download_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            # Convert datetime objects to strings
            stats_json = self.stats.copy()
            if stats_json['start_time']:
                stats_json['start_time'] = stats_json['start_time'].isoformat()
            if stats_json['end_time']:
                stats_json['end_time'] = stats_json['end_time'].isoformat()

            with open(stats_path, 'w') as f:
                json.dump(stats_json, f, indent=2)

            logger.info(f"Saved statistics to {stats_path}")
        except Exception as e:
            logger.error(f"Error saving statistics: {str(e)}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Download historical market data from Alpaca API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download specific symbols
  python download_historical_data.py --symbols AAPL MSFT GOOGL --start 2024-01-01 --end 2024-12-31

  # Use configuration file
  python download_historical_data.py --config config.json

  # Download with custom timeframe
  python download_historical_data.py --symbols AAPL --start 2024-01-01 --end 2024-12-31 --timeframe 1Hour

  # Save only Parquet format
  python download_historical_data.py --symbols AAPL --start 2024-01-01 --end 2024-12-31 --no-csv
        """
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        help='List of stock symbols to download (e.g., AAPL MSFT GOOGL)'
    )

    parser.add_argument(
        '--start',
        '--start-date',
        dest='start_date',
        help='Start date (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--end',
        '--end-date',
        dest='end_date',
        help='End date (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--timeframe',
        default='1Day',
        choices=['1Min', '5Min', '15Min', '1Hour', '1Day'],
        help='Data timeframe (default: 1Day)'
    )

    parser.add_argument(
        '--output-dir',
        default='data',
        help='Output directory for downloaded data (default: data)'
    )

    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='Skip CSV output (Parquet only)'
    )

    parser.add_argument(
        '--no-parquet',
        action='store_true',
        help='Skip Parquet output (CSV only)'
    )

    parser.add_argument(
        '--config',
        help='Path to JSON configuration file'
    )

    parser.add_argument(
        '--retry-attempts',
        type=int,
        default=3,
        help='Number of retry attempts on failure (default: 3)'
    )

    parser.add_argument(
        '--retry-delay',
        type=int,
        default=5,
        help='Initial retry delay in seconds (default: 5)'
    )

    parser.add_argument(
        '--max-retry-delay',
        type=int,
        default=60,
        help='Maximum retry delay cap in seconds (default: 60)'
    )

    parser.add_argument(
        '--inter-symbol-delay',
        type=float,
        default=1.0,
        help='Delay between symbol downloads in seconds to prevent rate limiting (default: 1.0)'
    )

    parser.add_argument(
        '--feed',
        default='iex',
        choices=['iex', 'sip', 'otc'],
        help='Data feed source (default: iex). IEX is free for paper accounts, SIP requires subscription'
    )

    parser.add_argument(
        '--adjustment',
        default='all',
        choices=['raw', 'split', 'dividend', 'all'],
        help='Price adjustment type (default: all)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_arguments()

    # Set debug logging if requested
    if hasattr(args, 'debug') and args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        # Load configuration
        if args.config:
            logger.info(f"Loading configuration from {args.config}")
            config = DownloadConfig.from_file(args.config)
        else:
            # Validate required arguments
            if not args.symbols:
                logger.error("Error: --symbols is required when not using --config")
                sys.exit(1)

            if not args.start_date:
                logger.error("Error: --start-date is required when not using --config")
                sys.exit(1)

            if not args.end_date:
                # CRITICAL FIX: Default to YESTERDAY to ensure complete market data
                # Market data for "today" may not be available until after close
                yesterday = (datetime.now() - timedelta(days=1)).date()
                args.end_date = yesterday.strftime('%Y-%m-%d')
                logger.info(f"No end date specified, using yesterday: {args.end_date}")

            # CRITICAL FIX: Validate and cap end_date to prevent future dates
            end_date_parsed = datetime.strptime(args.end_date, '%Y-%m-%d').date()
            today = datetime.now().date()

            if end_date_parsed > today:
                logger.warning(f"CRITICAL: End date {end_date_parsed} is in the future!")
                logger.warning(f"Today is {today}, capping end_date to yesterday")
                # Use yesterday to ensure complete market data
                yesterday = today - timedelta(days=1)
                args.end_date = yesterday.strftime('%Y-%m-%d')
                logger.info(f"Adjusted end_date to: {args.end_date}")
            elif end_date_parsed == today:
                # Even if end_date is today, use yesterday for complete data
                logger.info(f"End date is today ({today}), adjusting to yesterday for complete data")
                yesterday = today - timedelta(days=1)
                args.end_date = yesterday.strftime('%Y-%m-%d')

            # Validate start_date < end_date
            start_date_parsed = datetime.strptime(args.start_date, '%Y-%m-%d').date()
            if start_date_parsed >= end_date_parsed:
                logger.error(f"CRITICAL: Start date {start_date_parsed} must be before end date {end_date_parsed}")
                sys.exit(1)

            # Create config from arguments
            config = DownloadConfig(
                symbols=args.symbols,
                start_date=args.start_date,
                end_date=args.end_date,
                timeframe=args.timeframe,
                output_dir=args.output_dir,
                save_csv=not args.no_csv,
                save_parquet=not args.no_parquet,
                retry_attempts=args.retry_attempts,
                retry_delay=args.retry_delay,
                max_retry_delay=args.max_retry_delay if hasattr(args, 'max_retry_delay') else 60,
                inter_symbol_delay=args.inter_symbol_delay if hasattr(args, 'inter_symbol_delay') else 1.0,
                feed=args.feed if hasattr(args, 'feed') else 'iex',
                adjustment=args.adjustment if hasattr(args, 'adjustment') else 'all'
            )

        # Validate configuration
        if not config.save_csv and not config.save_parquet:
            logger.error("Error: At least one output format (CSV or Parquet) must be enabled")
            sys.exit(1)

        # Initialize downloader
        downloader = AlpacaDataDownloader(config)

        # Execute download
        stats = downloader.download_all()

        # Exit with appropriate code
        if stats['failed_downloads'] > 0:
            logger.warning(f"Completed with {stats['failed_downloads']} failures")
            sys.exit(1)
        else:
            logger.info("All downloads completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
