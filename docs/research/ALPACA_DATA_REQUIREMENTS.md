# Alpaca API Data Fetching Requirements - Research Findings

**Research Agent Report**
**Date:** 2025-10-22
**Memory Key:** `hive/research/alpaca_data_requirements`

---

## Executive Summary

This document provides comprehensive research on Alpaca API data fetching requirements, storage formats, data structures, and best practices for the Rust Algorithm Trading system.

---

## 1. Current Alpaca API Implementation Analysis

### 1.1 API Client Structure
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/api/alpaca_client.py`

**Key Components:**
- **Library:** `alpaca-py >= 0.42.2` (official Python SDK)
- **Clients:**
  - `TradingClient` - Order management and account operations
  - `StockHistoricalDataClient` - Historical market data retrieval

**Authentication:**
```python
ALPACA_API_KEY       # Required: API key from environment
ALPACA_SECRET_KEY    # Required: Secret key from environment
ALPACA_BASE_URL      # Default: https://paper-api.alpaca.markets
```

### 1.2 Data Fetching Method
**Primary Method:** `get_historical_bars()`

```python
def get_historical_bars(
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: TimeFrame = TimeFrame.Day
) -> pd.DataFrame
```

**Supported Timeframes:**
- `TimeFrame.Minute` - 1-minute bars
- `TimeFrame.Hour` - 1-hour bars
- `TimeFrame.Day` - Daily bars (default)
- Custom timeframes available via SDK

**Return Format:**
- Returns pandas DataFrame via `bars.df` property
- Multi-index structure: `(symbol, timestamp)`

---

## 2. Required Data Format and Column Structure

### 2.1 Core OHLCV Columns (Required)

Based on analysis of `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/data_handler.py`:

```python
REQUIRED_COLUMNS = [
    'timestamp',    # datetime - Bar timestamp (index or column)
    'open',         # float > 0 - Opening price
    'high',         # float > 0 - Highest price (must be >= low)
    'low',          # float > 0 - Lowest price
    'close',        # float > 0 - Closing price (must be between low-high)
    'volume'        # float >= 0 - Trading volume
]
```

### 2.2 Optional Enhanced Columns

```python
OPTIONAL_COLUMNS = [
    'vwap',         # float - Volume-weighted average price
    'trade_count'   # int - Number of trades in bar
]
```

### 2.3 Data Model Validation

**Pydantic Model:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/models/market.py`

```python
class Bar(BaseModel):
    symbol: str
    timestamp: datetime
    open: float = Field(gt=0)          # Greater than 0
    high: float = Field(gt=0)          # Greater than 0
    low: float = Field(gt=0)           # Greater than 0
    close: float = Field(gt=0)         # Greater than 0
    volume: float = Field(ge=0)        # Greater or equal to 0
    vwap: Optional[float] = None
    trade_count: Optional[int] = None
```

**Validation Rules:**
1. `high >= low` (enforced)
2. `low <= open <= high` (enforced)
3. `low <= close <= high` (enforced)
4. All prices must be positive
5. Volume must be non-negative

---

## 3. Storage Formats and Strategy

### 3.1 Supported Formats

**Primary Format: Parquet** (Recommended)
- **Location:** `/data/parquet/{symbol}.parquet`
- **Advantages:**
  - 5-10x faster read performance
  - 70-80% smaller file size vs CSV
  - Columnar storage optimized for analytics
  - Native timestamp/datetime support
  - Compression built-in
- **Implementation:**
  ```python
  df.to_parquet(f"data/parquet/{symbol}.parquet")
  df = pd.read_parquet(f"data/parquet/{symbol}.parquet")
  ```

**Secondary Format: CSV** (Fallback)
- **Location:** `/data/csv/{symbol}.csv`
- **Advantages:**
  - Human-readable
  - Universal compatibility
  - Easy debugging
- **Disadvantages:**
  - Larger file size
  - Slower read/write
  - Type inference issues
- **Implementation:**
  ```python
  df.to_csv(f"data/csv/{symbol}.csv")
  df = pd.read_csv(f"data/csv/{symbol}.csv", parse_dates=['timestamp'])
  ```

### 3.2 Data Loading Priority

**Current Implementation:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/data_handler.py`

```python
# Priority order:
1. Try Parquet first: data/parquet/{symbol}.parquet
2. Fallback to CSV: data/csv/{symbol}.csv
3. Warn if neither exists
```

### 3.3 Directory Structure

```
data/
├── csv/              # CSV format storage (fallback)
│   ├── AAPL.csv
│   ├── GOOGL.csv
│   └── MSFT.csv
├── parquet/          # Parquet format storage (primary)
│   ├── AAPL.parquet
│   ├── GOOGL.parquet
│   └── MSFT.parquet
├── historical/       # Raw historical data backups
├── backtest_results/ # Backtest output data
├── live_trading/     # Live trading logs
└── *.duckdb         # DuckDB database files
```

---

## 4. Alpaca API Data Characteristics

### 4.1 DataFrame Structure from Alpaca

**Alpaca Returns:**
```python
# Multi-index DataFrame
bars.df
# Index: MultiIndex[(symbol, timestamp)]
# Columns: ['open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap']
```

**Transformation Required:**
```python
# Need to flatten for storage
df = bars.df.reset_index()
# Now: Index: RangeIndex, Columns: ['symbol', 'timestamp', 'open', ...]
```

### 4.2 Data Quality and Validation

**Implemented Validations:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/data_handler.py`

```python
# 1. Check for null timestamps
if df['timestamp'].isna().any():
    df = df.dropna(subset=['timestamp'])

# 2. Ensure chronological order
df = df.sort_values('timestamp').reset_index(drop=True)

# 3. Validate OHLC relationships
if df['high'].lt(df['low']).any():
    logger.warning("Invalid bars where high < low")

# 4. Date range filtering
if start_date:
    df = df[df['timestamp'] >= start_date]
if end_date:
    df = df[df['timestamp'] <= end_date]
```

### 4.3 Data Cleaning Pipeline

**From:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/data/loader.py`

```python
# Validation steps in _validate_data():
1. Remove duplicate timestamps
2. Sort by timestamp
3. Validate OHLC relationships (high >= max(open, close, low))
4. Fix invalid bars automatically
5. Remove negative prices
6. Remove negative volume
7. Forward-fill missing values
```

---

## 5. Data Download Strategy and Best Practices

### 5.1 Recommended Download Strategy

**Implementation Pattern:**

```python
from datetime import datetime, timedelta
from alpaca.data.timeframe import TimeFrame
from src.api.alpaca_client import AlpacaClient
from src.data.loader import DataLoader

def download_and_save_data(
    symbols: List[str],
    days_back: int = 365,
    timeframe: TimeFrame = TimeFrame.Day,
    output_format: str = 'parquet'
):
    """
    Download historical data from Alpaca and save to disk.

    Args:
        symbols: List of ticker symbols
        days_back: Days of historical data (max 5 years for free tier)
        timeframe: Bar timeframe (Day, Hour, Minute)
        output_format: 'parquet' or 'csv'
    """
    client = AlpacaClient()
    loader = DataLoader(data_dir='data')

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    for symbol in symbols:
        try:
            # Fetch from Alpaca
            df = client.get_historical_bars(
                symbol=symbol,
                start=start_date,
                end=end_date,
                timeframe=timeframe
            )

            # Reset index to flatten MultiIndex
            df = df.reset_index()

            # Validate and clean
            df = validate_ohlcv_data(df)

            # Save in preferred format
            if output_format == 'parquet':
                loader.save_data(symbol, df, format='parquet')
            else:
                loader.save_data(symbol, df, format='csv')

            logger.info(f"Saved {len(df)} bars for {symbol}")

        except Exception as e:
            logger.error(f"Failed to download {symbol}: {e}")
```

### 5.2 Batch Download Considerations

**Rate Limits:**
- **Free Tier:** 200 requests/minute per API key
- **Unlimited Plan:** Higher limits
- **Best Practice:** Add rate limiting with exponential backoff

**Memory Management:**
- Process symbols in batches of 10-20
- Clear cache after each batch
- Use chunked downloads for large date ranges

**Error Handling:**
```python
# Retry strategy for transient failures
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def download_with_retry(symbol, start, end, timeframe):
    return client.get_historical_bars(symbol, start, end, timeframe)
```

### 5.3 Data Versioning and Updates

**Strategy:**
```python
# Directory structure for versioning
data/
├── parquet/
│   ├── v1_AAPL.parquet      # Original download
│   ├── v2_AAPL.parquet      # Updated with recent data
│   └── AAPL.parquet         # Latest symlink
└── historical/
    └── 2025-10-22/          # Dated backups
        └── AAPL.parquet
```

**Incremental Updates:**
```python
def update_historical_data(symbol: str):
    """Update existing data with new bars."""
    # 1. Load existing data
    existing_df = pd.read_parquet(f"data/parquet/{symbol}.parquet")
    last_date = existing_df['timestamp'].max()

    # 2. Fetch only new data
    new_df = client.get_historical_bars(
        symbol=symbol,
        start=last_date + timedelta(days=1),
        end=datetime.now(),
        timeframe=TimeFrame.Day
    )

    # 3. Merge and deduplicate
    combined_df = pd.concat([existing_df, new_df])
    combined_df = combined_df.drop_duplicates(subset=['timestamp'])
    combined_df = combined_df.sort_values('timestamp')

    # 4. Save updated data
    combined_df.to_parquet(f"data/parquet/{symbol}.parquet")
```

---

## 6. Integration with Backtesting System

### 6.1 Data Handler Integration

**Current Implementation:** `HistoricalDataHandler` class

**Usage Pattern:**
```python
from pathlib import Path
from src.backtesting.data_handler import HistoricalDataHandler

# Initialize with data directory
data_handler = HistoricalDataHandler(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    data_dir=Path('data/parquet'),
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Data automatically loaded in priority order:
# 1. data/parquet/{symbol}.parquet
# 2. data/csv/{symbol}.csv (fallback)

# Replay bars during backtest
while data_handler.continue_backtest:
    data_handler.update_bars()
    latest_bar = data_handler.get_latest_bar('AAPL')
    # Process bar...
```

### 6.2 Caching Strategy

**From:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/data/loader.py`

```python
class DataLoader:
    def __init__(self, cache_enabled: bool = True):
        self.cache: Dict[str, pd.DataFrame] = {}

    def load_ohlcv(self, symbol, ...):
        cache_key = f"{symbol}_{timeframe}_{source}"

        # Check cache first
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]

        # Load from disk
        df = self._load_from_file(symbol, source)

        # Cache for future use
        if self.cache_enabled:
            self.cache[cache_key] = df

        return df
```

---

## 7. Data Preprocessing and Technical Indicators

### 7.1 Available Preprocessing

**From:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/data/preprocessor.py`

**Technical Indicators:**
```python
from src.data.preprocessor import DataPreprocessor

# Add technical indicators
df = DataPreprocessor.add_technical_indicators(df)

# Adds:
- Moving averages (SMA 20, 50, 200)
- Exponential MA (EMA 12, 26)
- MACD (line, signal, histogram)
- RSI (14-period)
- Bollinger Bands (20-period, 2 std)
- ATR (14-period)
- Volume indicators
```

**Data Cleaning:**
```python
# Handle missing data
df = DataPreprocessor.handle_missing_data(df, method='forward_fill')

# Calculate returns
df = DataPreprocessor.calculate_returns(df, periods=1)

# Normalize features
df = DataPreprocessor.normalize_data(df, columns=['close', 'volume'])

# Detect outliers
outliers = DataPreprocessor.detect_outliers(df, 'close', threshold=3.0)

# Train/test split
train_df, test_df = DataPreprocessor.split_train_test(df, train_ratio=0.8)
```

---

## 8. Best Practices and Recommendations

### 8.1 Data Storage Best Practices

✅ **DO:**
1. **Use Parquet as primary format** - 5-10x performance improvement
2. **Store raw data separately** - Keep original downloads in `data/historical/`
3. **Version control schema** - Document column structure changes
4. **Implement data validation** - Validate OHLCV relationships before storage
5. **Use compression** - Parquet automatically compresses (snappy by default)
6. **Maintain metadata** - Store download date, timeframe, source in filename

❌ **DON'T:**
1. Store unvalidated data directly
2. Mix timeframes in same file
3. Hardcode file paths (use Path objects)
4. Skip error handling for missing data
5. Load all symbols into memory at once

### 8.2 Download Best Practices

✅ **DO:**
1. **Implement retry logic** - Handle transient API failures
2. **Use rate limiting** - Respect Alpaca API limits (200 req/min)
3. **Download during off-hours** - Better performance, fewer rate limit issues
4. **Log all downloads** - Track what was fetched and when
5. **Validate after download** - Check data completeness and quality

❌ **DON'T:**
1. Download same data multiple times
2. Ignore API rate limits
3. Skip data validation
4. Mix paper and live API data
5. Store credentials in code

### 8.3 Data Quality Monitoring

**Implement Checks:**
```python
def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Run comprehensive data quality checks."""
    quality_report = {
        'total_bars': len(df),
        'date_range': (df['timestamp'].min(), df['timestamp'].max()),
        'missing_values': df.isnull().sum().to_dict(),
        'invalid_bars': {
            'high_lt_low': (df['high'] < df['low']).sum(),
            'negative_prices': (df[['open', 'high', 'low', 'close']] < 0).any().any(),
            'zero_volume': (df['volume'] == 0).sum()
        },
        'duplicates': df.duplicated(subset=['timestamp']).sum(),
        'gaps': detect_missing_timestamps(df)
    }
    return quality_report
```

---

## 9. Sample Data Download Script

### 9.1 Complete Implementation

```python
#!/usr/bin/env python3
"""
Download historical data from Alpaca and save to optimized storage.

Usage:
    python scripts/download_alpaca_data.py --symbols AAPL GOOGL MSFT --days 365
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
import pandas as pd
from loguru import logger
from alpaca.data.timeframe import TimeFrame

from src.api.alpaca_client import AlpacaClient
from src.data.loader import DataLoader
from src.data.preprocessor import DataPreprocessor


def download_historical_data(
    symbols: List[str],
    days_back: int = 365,
    timeframe: TimeFrame = TimeFrame.Day,
    output_format: str = 'parquet',
    data_dir: Path = Path('data')
):
    """
    Download and save historical market data.

    Args:
        symbols: List of ticker symbols
        days_back: Days of historical data to download
        timeframe: Bar timeframe (Day, Hour, Minute)
        output_format: Storage format ('parquet' or 'csv')
        data_dir: Base data directory
    """
    # Initialize clients
    client = AlpacaClient()
    loader = DataLoader(data_dir=data_dir)

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    logger.info(f"Downloading {len(symbols)} symbols from {start_date} to {end_date}")

    success_count = 0
    failed_symbols = []

    for i, symbol in enumerate(symbols, 1):
        try:
            logger.info(f"[{i}/{len(symbols)}] Fetching {symbol}...")

            # Fetch from Alpaca
            df = client.get_historical_bars(
                symbol=symbol,
                start=start_date,
                end=end_date,
                timeframe=timeframe
            )

            # Reset index to flatten MultiIndex
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()

            # Validate data
            if 'timestamp' not in df.columns:
                df = df.reset_index()

            # Clean and validate
            df = validate_and_clean_data(df, symbol)

            # Save to disk
            if output_format == 'parquet':
                output_dir = data_dir / 'parquet'
            else:
                output_dir = data_dir / 'csv'

            output_dir.mkdir(parents=True, exist_ok=True)
            loader.save_data(symbol, df, format=output_format)

            logger.success(f"✓ {symbol}: {len(df)} bars saved")
            success_count += 1

        except Exception as e:
            logger.error(f"✗ {symbol}: {e}")
            failed_symbols.append(symbol)

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Download Complete:")
    logger.info(f"  Success: {success_count}/{len(symbols)}")
    logger.info(f"  Failed: {len(failed_symbols)}")
    if failed_symbols:
        logger.warning(f"  Failed symbols: {', '.join(failed_symbols)}")


def validate_and_clean_data(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Validate and clean OHLCV data."""
    # Required columns
    required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Add symbol if missing
    if 'symbol' not in df.columns:
        df['symbol'] = symbol

    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Remove duplicates
    df = df.drop_duplicates(subset=['timestamp'])

    # Validate OHLC relationships
    invalid_high = df['high'] < df[['open', 'close', 'low']].max(axis=1)
    invalid_low = df['low'] > df[['open', 'close', 'high']].min(axis=1)

    if invalid_high.any() or invalid_low.any():
        logger.warning(f"{symbol}: Found {invalid_high.sum() + invalid_low.sum()} invalid bars")
        # Fix automatically
        df.loc[invalid_high, 'high'] = df[['open', 'close', 'low']].max(axis=1)
        df.loc[invalid_low, 'low'] = df[['open', 'close', 'high']].min(axis=1)

    # Remove invalid prices
    df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]
    df = df[df['volume'] >= 0]

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download Alpaca historical data')
    parser.add_argument('--symbols', nargs='+', required=True, help='Stock symbols')
    parser.add_argument('--days', type=int, default=365, help='Days of history')
    parser.add_argument('--format', default='parquet', choices=['parquet', 'csv'])
    parser.add_argument('--timeframe', default='Day', help='Bar timeframe')

    args = parser.parse_args()

    # Map timeframe string to TimeFrame enum
    timeframe_map = {
        'Minute': TimeFrame.Minute,
        'Hour': TimeFrame.Hour,
        'Day': TimeFrame.Day
    }
    timeframe = timeframe_map.get(args.timeframe, TimeFrame.Day)

    download_historical_data(
        symbols=args.symbols,
        days_back=args.days,
        timeframe=timeframe,
        output_format=args.format
    )
```

---

## 10. Troubleshooting and Common Issues

### 10.1 API Connection Issues

**Problem:** `Failed to initialize Alpaca client`

**Solutions:**
```bash
# Check environment variables
echo $ALPACA_API_KEY
echo $ALPACA_SECRET_KEY

# Verify credentials are valid
python -c "from src.api.alpaca_client import AlpacaClient; client = AlpacaClient(); print(client.get_account())"

# Check API status
curl https://status.alpaca.markets/
```

### 10.2 Data Format Issues

**Problem:** `Missing required columns`

**Solution:**
```python
# Check what Alpaca returns
df = client.get_historical_bars(symbol='AAPL', ...)
print(df.columns)
print(df.index)

# If MultiIndex, reset it
if isinstance(df.index, pd.MultiIndex):
    df = df.reset_index()
```

### 10.3 Memory Issues

**Problem:** `Out of memory when loading large datasets`

**Solutions:**
```python
# 1. Use chunked loading
def load_large_dataset_chunked(symbol: str, chunk_size: int = 10000):
    for chunk in pd.read_parquet(f'{symbol}.parquet', chunksize=chunk_size):
        process_chunk(chunk)

# 2. Use DuckDB for out-of-memory processing
import duckdb
con = duckdb.connect()
result = con.execute("""
    SELECT * FROM 'data/parquet/AAPL.parquet'
    WHERE timestamp >= '2024-01-01'
""").df()

# 3. Clear cache regularly
loader.clear_cache()
```

---

## 11. Next Steps and Implementation Priorities

### 11.1 Immediate Actions

1. **Create download script** (Priority: HIGH)
   - Implement `scripts/download_alpaca_data.py`
   - Add retry logic and rate limiting
   - Include data validation

2. **Standardize storage format** (Priority: HIGH)
   - Migrate existing CSV files to Parquet
   - Update documentation for data directories
   - Create backup strategy

3. **Implement data quality monitoring** (Priority: MEDIUM)
   - Add validation checks before backtests
   - Create data quality dashboard
   - Log data issues for review

### 11.2 Future Enhancements

1. **Automated data updates**
   - Daily cron job to fetch new bars
   - Incremental update strategy
   - Data staleness monitoring

2. **Multi-source data aggregation**
   - Support for additional data providers
   - Data source comparison and validation
   - Fallback mechanisms

3. **Advanced storage optimization**
   - Partitioned Parquet files by date
   - Delta Lake for ACID transactions
   - Time-series specific optimizations

---

## Appendix A: File Locations Reference

### Key Files
```
src/api/alpaca_client.py          # Main Alpaca API client
src/data/loader.py                 # Data loading utilities
src/data/fetcher.py                # Data fetching module
src/data/preprocessor.py           # Data cleaning and preprocessing
src/backtesting/data_handler.py    # Backtest data handler
src/models/market.py               # OHLCV data models
```

### Data Directories
```
data/csv/                          # CSV format storage
data/parquet/                      # Parquet format storage (recommended)
data/historical/                   # Historical backups
data/backtest_results/             # Backtest outputs
```

### Configuration
```
.env                               # API credentials
requirements.txt                   # Python dependencies (alpaca-py>=0.42.2)
```

---

## Appendix B: Data Schema Reference

### Parquet Schema
```
symbol:       string
timestamp:    timestamp[ns, tz=UTC]
open:         double
high:         double
low:          double
close:        double
volume:       double
vwap:         double (optional)
trade_count:  int64 (optional)
```

### CSV Schema
```
Column      | Type     | Constraints
------------|----------|----------------------------------
symbol      | string   | Not null
timestamp   | datetime | Not null, ISO8601 format
open        | float    | > 0
high        | float    | > 0, >= low
low         | float    | > 0
close       | float    | > 0, between low-high
volume      | float    | >= 0
vwap        | float    | Optional
trade_count | int      | Optional
```

---

## Research Metadata

**Sources Analyzed:**
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/api/alpaca_client.py`
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/data_handler.py`
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/data/loader.py`
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/data/preprocessor.py`
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/models/market.py`
- `requirements.txt` (alpaca-py version)

**Total Files Analyzed:** 18
**Code Patterns Identified:** 6
**Data Formats Validated:** 2 (CSV, Parquet)

---

**End of Research Report**
