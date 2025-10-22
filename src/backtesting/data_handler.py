"""
Historical data handler for backtesting.
"""

import sys
from datetime import datetime, timezone
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

        Raises:
            ValueError: If symbols is empty or invalid
            TypeError: If parameters have incorrect types
            FileNotFoundError: If data directory doesn't exist
        """
        # Validate parameters
        if not symbols:
            raise ValueError("symbols list cannot be empty")

        if not isinstance(symbols, list):
            raise TypeError(f"symbols must be a list, got {type(symbols).__name__}")

        if not all(isinstance(s, str) for s in symbols):
            raise TypeError("All symbols must be strings")

        # Convert and validate data_dir
        try:
            self.data_dir = Path(data_dir)
        except (TypeError, ValueError) as e:
            raise TypeError(f"data_dir must be a valid path: {e}")

        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            # Create directory if it doesn't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created data directory: {self.data_dir}")

        # Validate date parameters
        if start_date is not None and not isinstance(start_date, datetime):
            raise TypeError(f"start_date must be datetime or None, got {type(start_date).__name__}")

        if end_date is not None and not isinstance(end_date, datetime):
            raise TypeError(f"end_date must be datetime or None, got {type(end_date).__name__}")

        if start_date and end_date and start_date >= end_date:
            raise ValueError(f"start_date ({start_date}) must be before end_date ({end_date})")

        self.symbols = symbols

        # TIMEZONE FIX: Ensure dates are timezone-aware (UTC) for consistent comparisons
        # This prevents "can't compare offset-naive and offset-aware datetimes" errors
        if start_date is not None:
            self.start_date = start_date if start_date.tzinfo is not None else start_date.replace(tzinfo=timezone.utc)
        else:
            self.start_date = None

        if end_date is not None:
            self.end_date = end_date if end_date.tzinfo is not None else end_date.replace(tzinfo=timezone.utc)
        else:
            self.end_date = None

        self.symbol_data: Dict[str, pd.DataFrame] = {}
        self.latest_bars: Dict[str, list[Bar]] = {s: [] for s in symbols}
        self.continue_backtest = True
        self.bar_index = 0

        self._load_data()

        logger.info(
            f"Loaded historical data for {len(symbols)} symbols "
            f"from {start_date} to {end_date}"
        )

    def _check_data_availability(self, symbol: str) -> bool:
        """
        Check if data is available for a symbol.

        Args:
            symbol: Symbol to check

        Returns:
            True if data exists and is valid
        """
        parquet_path = self.data_dir / f"{symbol}.parquet"
        csv_path = self.data_dir / f"{symbol}.csv"

        if parquet_path.exists() or csv_path.exists():
            # Check if file has data
            try:
                if parquet_path.exists():
                    df = pd.read_parquet(parquet_path)
                else:
                    df = pd.read_csv(csv_path, nrows=5)

                if len(df) > 0:
                    return True
            except Exception as e:
                logger.debug(f"Error checking {symbol}: {e}")

        return False

    def _attempt_auto_download(self) -> bool:
        """
        Attempt to automatically download missing data.

        Returns:
            True if download was attempted
        """
        try:
            import subprocess
            from datetime import datetime, timedelta

            logger.info("Attempting to auto-download missing data...")

            # Calculate date range
            if self.start_date and self.end_date:
                days_back = (self.end_date - self.start_date).days
            else:
                days_back = 365

            # Run download script
            download_script = Path(__file__).parent.parent.parent / "scripts" / "download_market_data.py"

            if not download_script.exists():
                logger.warning(f"Download script not found: {download_script}")
                return False

            cmd = [
                sys.executable,
                str(download_script),
                "--symbols",
                *self.symbols,
                "--days",
                str(days_back),
                "--output-dir",
                str(self.data_dir.parent)
            ]

            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                logger.info("Auto-download completed successfully")
                return True
            else:
                logger.error(f"Auto-download failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Auto-download timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Error during auto-download: {e}")
            return False

    def _load_data(self):
        """
        Load historical data for all symbols.

        Raises:
            ValueError: If data format is invalid or required columns are missing
            FileNotFoundError: If data files are missing and auto-download fails
            Exception: If file reading fails
        """
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        # Check data availability
        missing_symbols = [s for s in self.symbols if not self._check_data_availability(s)]

        if missing_symbols:
            logger.warning(f"Missing data for {len(missing_symbols)} symbols: {missing_symbols}")
            logger.info("Attempting automatic data download...")

            if self._attempt_auto_download():
                # Re-check availability after download
                still_missing = [s for s in missing_symbols if not self._check_data_availability(s)]
                if still_missing:
                    logger.error(
                        f"Still missing data for {len(still_missing)} symbols after auto-download: {still_missing}"
                    )
            else:
                logger.error(
                    "Auto-download failed. Please run manually:\n"
                    f"  python scripts/download_market_data.py --symbols {' '.join(missing_symbols)}"
                )

        for symbol in self.symbols:
            try:
                # Try Parquet first, fall back to CSV
                parquet_path = self.data_dir / f"{symbol}.parquet"
                csv_path = self.data_dir / f"{symbol}.csv"

                if parquet_path.exists():
                    try:
                        df = pd.read_parquet(parquet_path)
                        logger.debug(f"Loaded {symbol} from Parquet: {parquet_path}")
                    except Exception as e:
                        logger.error(f"Failed to read Parquet file {parquet_path}: {e}")
                        raise ValueError(f"Invalid Parquet file for {symbol}: {e}")
                elif csv_path.exists():
                    try:
                        df = pd.read_csv(csv_path, parse_dates=['timestamp'])
                        logger.debug(f"Loaded {symbol} from CSV: {csv_path}")
                    except Exception as e:
                        logger.error(f"Failed to read CSV file {csv_path}: {e}")
                        raise ValueError(f"Invalid CSV file for {symbol}: {e}")
                else:
                    logger.error(
                        f"No data file found for {symbol}. "
                        f"Please download data using: python scripts/download_market_data.py --symbols {symbol}"
                    )
                    raise FileNotFoundError(
                        f"No data file found for {symbol} "
                        f"(checked: {parquet_path}, {csv_path})"
                    )
                    continue

                # Validate required columns
                missing_cols = [col for col in required_columns if col not in df.columns]
                if missing_cols:
                    raise ValueError(
                        f"Missing required columns for {symbol}: {missing_cols}. "
                        f"Available columns: {list(df.columns)}"
                    )

                # Validate timestamp column
                if df['timestamp'].isna().any():
                    logger.warning(f"Found {df['timestamp'].isna().sum()} null timestamps for {symbol}")
                    df = df.dropna(subset=['timestamp'])

                # Filter by date range (ensure timestamps are timezone-aware for comparison)
                if self.start_date:
                    # Make timestamp column timezone-aware if needed
                    if df['timestamp'].dt.tz is None:
                        df['timestamp'] = df['timestamp'].dt.tz_localize(timezone.utc)
                    df = df[df['timestamp'] >= self.start_date]
                if self.end_date:
                    # Make timestamp column timezone-aware if needed
                    if df['timestamp'].dt.tz is None:
                        df['timestamp'] = df['timestamp'].dt.tz_localize(timezone.utc)
                    df = df[df['timestamp'] <= self.end_date]

                if len(df) == 0:
                    logger.warning(
                        f"No data for {symbol} in date range "
                        f"{self.start_date} to {self.end_date}"
                    )
                    continue

                # Ensure sorted by timestamp
                df = df.sort_values('timestamp').reset_index(drop=True)

                # Validate data integrity
                if df['high'].lt(df['low']).any():
                    logger.warning(f"Found invalid bars for {symbol} where high < low")

                self.symbol_data[symbol] = df

                logger.info(
                    f"Loaded {len(df)} bars for {symbol} "
                    f"from {df['timestamp'].min()} to {df['timestamp'].max()}"
                )

            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {e}")
                raise

    def update_bars(self):
        """
        Update latest bars for all symbols.

        This method advances the data replay by one bar for each symbol.

        Raises:
            ValueError: If bar data is invalid
        """
        for symbol in self.symbols:
            if symbol not in self.symbol_data:
                logger.debug(f"No data loaded for {symbol}, skipping update")
                continue

            df = self.symbol_data[symbol]

            if self.bar_index >= len(df):
                self.continue_backtest = False
                logger.debug(f"Reached end of data for {symbol} at index {self.bar_index}")
                continue

            try:
                # Get next bar
                row = df.iloc[self.bar_index]

                # Validate bar data
                if pd.isna(row['open']) or pd.isna(row['close']):
                    logger.warning(
                        f"Invalid bar data for {symbol} at index {self.bar_index}: "
                        f"open={row['open']}, close={row['close']}"
                    )
                    continue

                bar = Bar(
                    symbol=symbol,
                    timestamp=row['timestamp'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume']),
                    vwap=float(row['vwap']) if 'vwap' in row and pd.notna(row['vwap']) else None,
                    trade_count=int(row['trade_count']) if 'trade_count' in row and pd.notna(row['trade_count']) else None,
                )

                self.latest_bars[symbol].append(bar)

            except (ValueError, TypeError) as e:
                logger.error(
                    f"Error creating bar for {symbol} at index {self.bar_index}: {e}"
                )
                raise ValueError(f"Invalid bar data for {symbol}: {e}")

        self.bar_index += 1

    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        """
        Get most recent bar for symbol.

        Args:
            symbol: Symbol to query

        Returns:
            Latest bar or None

        Raises:
            TypeError: If symbol is not a string
        """
        if not isinstance(symbol, str):
            raise TypeError(f"symbol must be a string, got {type(symbol).__name__}")

        try:
            return self.latest_bars[symbol][-1]
        except IndexError:
            logger.debug(f"No bars available for {symbol}")
            return None
        except KeyError:
            logger.warning(f"Unknown symbol: {symbol}. Available symbols: {list(self.symbols)}")
            return None

    def get_latest_bars(self, symbol: str, n: int = 1) -> list[Bar]:
        """
        Get N most recent bars for symbol.

        Args:
            symbol: Symbol to query
            n: Number of bars to retrieve

        Returns:
            List of bars (oldest to newest)

        Raises:
            TypeError: If parameters have incorrect types
            ValueError: If n is not positive
        """
        if not isinstance(symbol, str):
            raise TypeError(f"symbol must be a string, got {type(symbol).__name__}")

        if not isinstance(n, int):
            raise TypeError(f"n must be an integer, got {type(n).__name__}")

        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")

        try:
            bars = self.latest_bars[symbol][-n:]
            if len(bars) < n:
                logger.debug(f"Requested {n} bars for {symbol}, but only {len(bars)} available")
            return bars
        except KeyError:
            logger.warning(f"Unknown symbol: {symbol}. Available symbols: {list(self.symbols)}")
            return []

    def get_latest_bar_value(self, symbol: str, field: str) -> Optional[float]:
        """
        Get specific field value from latest bar.

        Args:
            symbol: Symbol to query
            field: Field name (open, high, low, close, volume)

        Returns:
            Field value or None

        Raises:
            TypeError: If parameters have incorrect types
            ValueError: If field name is invalid
        """
        if not isinstance(symbol, str):
            raise TypeError(f"symbol must be a string, got {type(symbol).__name__}")

        if not isinstance(field, str):
            raise TypeError(f"field must be a string, got {type(field).__name__}")

        valid_fields = ['open', 'high', 'low', 'close', 'volume', 'vwap', 'trade_count', 'timestamp']
        if field not in valid_fields:
            raise ValueError(f"Invalid field '{field}'. Valid fields: {valid_fields}")

        bar = self.get_latest_bar(symbol)
        if bar:
            value = getattr(bar, field, None)
            if value is None:
                logger.debug(f"Field '{field}' is None for {symbol}")
            return value
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

        Raises:
            TypeError: If parameters have incorrect types
            ValueError: If field name is invalid or n is not positive
        """
        if not isinstance(field, str):
            raise TypeError(f"field must be a string, got {type(field).__name__}")

        valid_fields = ['open', 'high', 'low', 'close', 'volume', 'vwap', 'trade_count']
        if field not in valid_fields:
            raise ValueError(f"Invalid field '{field}'. Valid fields: {valid_fields}")

        # get_latest_bars will validate symbol and n
        bars = self.get_latest_bars(symbol, n)
        values = []
        for bar in bars:
            if hasattr(bar, field):
                val = getattr(bar, field)
                if val is not None:
                    values.append(val)
            else:
                logger.warning(f"Bar for {symbol} missing field '{field}'")

        return values
