# Historical Data Download Guide

Complete guide for downloading historical market data from Alpaca Markets API for backtesting and analysis.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Usage Examples](#usage-examples)
4. [Configuration Options](#configuration-options)
5. [Data Format Specifications](#data-format-specifications)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)
8. [Advanced Usage](#advanced-usage)

---

## Quick Start

Download historical data for AAPL, MSFT, and GOOGL for the current year:

```bash
# Navigate to project root
cd /path/to/RustAlgorithmTrading

# Activate virtual environment
source .venv/bin/activate

# Download data (defaults to current year)
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31
```

That's it! Your data will be saved in:
- `data/csv/` - CSV format files
- `data/parquet/` - Parquet format files (compressed, optimized)

---

## Prerequisites

### 1. API Credentials

You need Alpaca Markets API credentials. Sign up for a free account at [alpaca.markets](https://alpaca.markets).

Set your credentials in `.env` file:

```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
```

### 2. Python Dependencies

Ensure all required packages are installed:

```bash
pip install -r requirements.txt
```

Required packages:
- `alpaca-py>=0.42.2` - Alpaca API client
- `pandas>=2.0.0` - Data manipulation
- `pyarrow` - Parquet file support
- `tqdm` - Progress bars
- `python-dotenv` - Environment variable loading

### 3. Directory Structure

The script automatically creates necessary directories:
```
data/
├── csv/          # CSV format files
├── parquet/      # Parquet format files (compressed)
└── *.json        # Download statistics
logs/
└── data_downloader.log  # Download logs
```

---

## Usage Examples

### Example 1: Basic Download

Download single symbol with date range:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --end 2024-12-31
```

### Example 2: Multiple Symbols

Download multiple symbols at once:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL TSLA AMZN \
  --start 2024-01-01 \
  --end 2024-12-31
```

### Example 3: Custom Timeframe

Download intraday data (hourly bars):

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --timeframe 1Hour
```

Available timeframes:
- `1Min` - 1-minute bars
- `5Min` - 5-minute bars
- `15Min` - 15-minute bars
- `1Hour` - Hourly bars
- `1Day` - Daily bars (default)

### Example 4: Custom Output Directory

Save data to a specific directory:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output-dir data/custom_location
```

### Example 5: CSV Only (No Parquet)

Download only CSV files:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --no-parquet
```

### Example 6: Parquet Only (No CSV)

Download only Parquet files (recommended for large datasets):

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --no-csv
```

### Example 7: Configuration File

Create a JSON configuration file for complex setups:

**config.json:**
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "timeframe": "1Day",
  "output_dir": "data",
  "save_csv": true,
  "save_parquet": true,
  "retry_attempts": 5,
  "retry_delay": 10
}
```

Then run:

```bash
python scripts/download_historical_data.py --config config.json
```

### Example 8: Historical Data (Multi-Year)

Download several years of data:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2020-01-01 \
  --end 2024-12-31
```

### Example 9: Recent Data Only

Download last 30 days (end date defaults to today):

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-10-01
```

---

## Configuration Options

### Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--symbols` | List | Required | Stock symbols to download (e.g., AAPL MSFT) |
| `--start`, `--start-date` | String | Required | Start date in YYYY-MM-DD format |
| `--end`, `--end-date` | String | Today | End date in YYYY-MM-DD format |
| `--timeframe` | Choice | `1Day` | Data timeframe: 1Min, 5Min, 15Min, 1Hour, 1Day |
| `--output-dir` | String | `data` | Output directory for downloaded data |
| `--no-csv` | Flag | False | Skip CSV output (Parquet only) |
| `--no-parquet` | Flag | False | Skip Parquet output (CSV only) |
| `--config` | String | None | Path to JSON configuration file |
| `--retry-attempts` | Integer | 3 | Number of retry attempts on failure |
| `--retry-delay` | Integer | 5 | Initial retry delay in seconds |

### Configuration File Format

JSON configuration file structure:

```json
{
  "symbols": ["AAPL", "MSFT"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "timeframe": "1Day",
  "api_key": "optional_override",
  "api_secret": "optional_override",
  "output_dir": "data",
  "save_csv": true,
  "save_parquet": true,
  "chunk_size": 1000,
  "retry_attempts": 3,
  "retry_delay": 5
}
```

---

## Data Format Specifications

### CSV Format

Downloaded CSV files follow this structure:

**Filename:** `{SYMBOL}_{START_DATE}_{END_DATE}.csv`

**Example:** `AAPL_2024-01-01_2024-12-31.csv`

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime | Bar timestamp (UTC) |
| `symbol` | string | Stock symbol |
| `open` | float | Opening price |
| `high` | float | Highest price |
| `low` | float | Lowest price |
| `close` | float | Closing price |
| `volume` | float | Trading volume |
| `vwap` | float | Volume-weighted average price |
| `trade_count` | integer | Number of trades (if available) |

**Sample CSV:**
```csv
timestamp,symbol,open,high,low,close,volume,vwap,trade_count
2024-01-02 00:00:00,AAPL,184.22,185.88,183.43,185.64,52164400,184.95,245678
2024-01-03 00:00:00,AAPL,184.35,185.40,182.00,184.25,61276800,183.87,287432
```

### Parquet Format

Parquet files use the same schema but with optimizations:

**Features:**
- Snappy compression (70-90% size reduction)
- Dictionary encoding for symbol column
- Column-based storage (faster queries)
- Statistics for each column
- Type preservation (no string-to-number conversion needed)

**Filename:** `{SYMBOL}_{START_DATE}_{END_DATE}.parquet`

**Reading Parquet:**
```python
import pandas as pd

# Read Parquet file
df = pd.read_parquet('data/parquet/AAPL_2024-01-01_2024-12-31.parquet')

# Timestamps are automatically parsed
print(df.dtypes)
```

### Data Validation

The downloader performs comprehensive validation:

1. **Schema Validation**
   - Ensures all required columns exist
   - Validates data types

2. **Price Validation**
   - Checks high >= low
   - Ensures positive prices
   - Detects and logs anomalies

3. **Timestamp Validation**
   - Removes null timestamps
   - Ensures chronological order
   - Validates date range

4. **Completeness Check**
   - Logs missing data
   - Reports gaps in timeline
   - Counts total rows

---

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

**Error:**
```
ValueError: Alpaca API credentials not found
```

**Solution:**
- Ensure `.env` file exists with valid credentials
- Check that `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are set
- Verify credentials at [alpaca.markets](https://alpaca.markets)

```bash
# Check if .env file exists
cat .env

# Verify environment variables are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ALPACA_API_KEY'))"
```

#### 2. No Data Returned

**Error:**
```
WARNING - No data returned for SYMBOL
```

**Possible Causes:**
- Symbol doesn't exist or is delisted
- Date range is outside available data
- Market was closed (weekends, holidays)
- Free tier data limitations

**Solutions:**
- Verify symbol is valid: Check [finance.yahoo.com](https://finance.yahoo.com)
- Adjust date range to include trading days
- Check Alpaca data availability for your account tier
- Try a different, well-known symbol (e.g., AAPL, MSFT)

#### 3. Rate Limiting

**Error:**
```
Error fetching data: 429 Too Many Requests
```

**Solution:**
The script handles rate limiting automatically with exponential backoff. If you still encounter issues:

```bash
# Increase retry delay
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --retry-attempts 5 \
  --retry-delay 10
```

#### 4. Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'alpaca'
```

**Solution:**
```bash
# Install all dependencies
pip install -r requirements.txt

# Or install specific package
pip install alpaca-py
```

#### 5. File Permission Errors

**Error:**
```
PermissionError: [Errno 13] Permission denied: 'data/csv'
```

**Solution:**
```bash
# Ensure directories are writable
mkdir -p data/csv data/parquet logs
chmod -R 755 data logs

# Or run with appropriate permissions
sudo python scripts/download_historical_data.py ...
```

#### 6. Invalid Date Format

**Error:**
```
ValueError: Invalid date format
```

**Solution:**
Use YYYY-MM-DD format:
```bash
# Correct
--start 2024-01-01

# Wrong
--start 01/01/2024
--start 2024-1-1
```

#### 7. Memory Errors (Large Datasets)

**Error:**
```
MemoryError: Unable to allocate array
```

**Solutions:**
- Download smaller date ranges
- Use Parquet only (more memory efficient)
- Split symbols into batches
- Increase system memory

```bash
# Download in smaller chunks
python scripts/download_historical_data.py \
  --symbols AAPL MSFT \
  --start 2024-01-01 \
  --end 2024-06-30

python scripts/download_historical_data.py \
  --symbols AAPL MSFT \
  --start 2024-07-01 \
  --end 2024-12-31
```

### Debug Mode

Enable detailed logging:

```bash
# Check log file for errors
tail -f logs/data_downloader.log

# Run with verbose output
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  2>&1 | tee debug.log
```

### Verify Downloaded Data

```python
import pandas as pd

# Check CSV file
df_csv = pd.read_csv('data/csv/AAPL_2024-01-01_2024-12-31.csv')
print(f"Rows: {len(df_csv)}")
print(f"Columns: {df_csv.columns.tolist()}")
print(f"Date range: {df_csv['timestamp'].min()} to {df_csv['timestamp'].max()}")
print(f"\nFirst few rows:\n{df_csv.head()}")

# Check Parquet file
df_parquet = pd.read_parquet('data/parquet/AAPL_2024-01-01_2024-12-31.parquet')
print(f"\nParquet rows: {len(df_parquet)}")
```

---

## Best Practices

### 1. Data Management

**Use Parquet for Production:**
```bash
# Parquet is faster and uses 70-90% less disk space
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --no-csv
```

**Organize by Timeframe:**
```bash
# Keep different timeframes separate
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --timeframe 1Day \
  --output-dir data/daily

python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --timeframe 1Hour \
  --output-dir data/hourly
```

### 2. Scheduling Downloads

**Cron Job (Daily Update):**

```bash
# Add to crontab (crontab -e)
0 18 * * 1-5 cd /path/to/project && python scripts/download_historical_data.py --symbols AAPL MSFT --start $(date -d "1 day ago" +\%Y-\%m-\%d)
```

**Shell Script:**

```bash
#!/bin/bash
# daily_download.sh

SYMBOLS="AAPL MSFT GOOGL TSLA AMZN"
START_DATE=$(date -d "1 day ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

python scripts/download_historical_data.py \
  --symbols $SYMBOLS \
  --start $START_DATE \
  --end $END_DATE \
  --no-csv
```

### 3. Batch Processing

For large symbol lists, create configuration files:

```bash
# technology_stocks.json
{
  "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "INTC"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "timeframe": "1Day",
  "save_csv": false,
  "save_parquet": true
}

# Download all tech stocks
python scripts/download_historical_data.py --config technology_stocks.json
```

### 4. Storage Optimization

**Parquet vs CSV Size Comparison:**
- CSV: ~100 MB per year of daily data per symbol
- Parquet: ~10-30 MB per year of daily data per symbol

**Recommended Storage Structure:**
```
data/
├── daily/
│   └── parquet/
│       ├── AAPL_2024-01-01_2024-12-31.parquet
│       └── MSFT_2024-01-01_2024-12-31.parquet
├── hourly/
│   └── parquet/
│       └── AAPL_2024-01-01_2024-12-31.parquet
└── minute/
    └── parquet/
        └── AAPL_2024-10-01_2024-10-31.parquet
```

### 5. Data Quality Checks

Always verify downloaded data:

```python
import pandas as pd

def validate_data(filepath):
    df = pd.read_parquet(filepath)

    # Check for missing values
    print(f"Missing values:\n{df.isnull().sum()}")

    # Check for invalid prices
    invalid = df[df['high'] < df['low']]
    print(f"Invalid bars (high < low): {len(invalid)}")

    # Check date continuity
    dates = pd.to_datetime(df['timestamp']).dt.date.unique()
    print(f"Total trading days: {len(dates)}")

    return df

df = validate_data('data/parquet/AAPL_2024-01-01_2024-12-31.parquet')
```

---

## Advanced Usage

### 1. Integration with Backtesting Engine

The downloaded data works seamlessly with the backtesting engine:

```python
from pathlib import Path
from src.backtesting.data_handler import HistoricalDataHandler

# Initialize data handler
data_handler = HistoricalDataHandler(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    data_dir=Path('data/parquet'),
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Data is automatically loaded from parquet files
# Format: {SYMBOL}_2024-01-01_2024-12-31.parquet
```

### 2. Custom Data Processing

Process downloaded data:

```python
import pandas as pd

# Load data
df = pd.read_parquet('data/parquet/AAPL_2024-01-01_2024-12-31.parquet')

# Calculate technical indicators
df['SMA_20'] = df['close'].rolling(window=20).mean()
df['SMA_50'] = df['close'].rolling(window=50).mean()
df['daily_return'] = df['close'].pct_change()

# Save processed data
df.to_parquet('data/processed/AAPL_with_indicators.parquet')
```

### 3. Multi-Timeframe Analysis

Download and combine multiple timeframes:

```python
import pandas as pd

# Download daily data
# python scripts/download_historical_data.py --symbols AAPL --start 2024-01-01 --timeframe 1Day --output-dir data/daily

# Download hourly data
# python scripts/download_historical_data.py --symbols AAPL --start 2024-01-01 --timeframe 1Hour --output-dir data/hourly

# Load both
daily = pd.read_parquet('data/daily/parquet/AAPL_2024-01-01_2024-12-31.parquet')
hourly = pd.read_parquet('data/hourly/parquet/AAPL_2024-01-01_2024-12-31.parquet')

print(f"Daily bars: {len(daily)}")
print(f"Hourly bars: {len(hourly)}")
```

### 4. Monitoring Download Statistics

The script saves detailed statistics:

```python
import json
from pathlib import Path

# Find latest stats file
stats_files = sorted(Path('data').glob('download_stats_*.json'))
latest_stats = stats_files[-1]

# Load statistics
with open(latest_stats) as f:
    stats = json.load(f)

print(f"Total symbols: {stats['total_symbols']}")
print(f"Successful: {stats['successful_downloads']}")
print(f"Failed: {stats['failed_downloads']}")
print(f"Total rows: {stats['total_rows']}")
print(f"Duration: {stats['duration_seconds']:.2f}s")
```

### 5. Parallel Downloads

For large symbol lists, consider parallel processing:

```bash
# Create separate config files
cat > batch1.json << EOF
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
EOF

cat > batch2.json << EOF
{
  "symbols": ["TSLA", "AMZN", "NVDA"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
EOF

# Run in parallel
python scripts/download_historical_data.py --config batch1.json &
python scripts/download_historical_data.py --config batch2.json &
wait
```

---

## API Limits

### Alpaca Free Tier

- **Rate Limit:** 200 requests per minute
- **Data History:** Up to 5 years of historical data
- **Symbols:** All US stocks
- **Timeframes:** 1Min, 5Min, 15Min, 1Hour, 1Day

### Alpaca Unlimited Tier

- **Rate Limit:** Higher limits (varies by plan)
- **Data History:** Full historical data
- **Additional Features:** Real-time data, level 2 quotes

For details, visit: [alpaca.markets/docs](https://alpaca.markets/docs)

---

## Quick Reference

### Most Common Commands

```bash
# Single symbol, current year
python scripts/download_historical_data.py --symbols AAPL --start 2024-01-01

# Multiple symbols, custom date range
python scripts/download_historical_data.py --symbols AAPL MSFT GOOGL --start 2024-01-01 --end 2024-12-31

# Hourly data, Parquet only
python scripts/download_historical_data.py --symbols AAPL --start 2024-01-01 --timeframe 1Hour --no-csv

# From configuration file
python scripts/download_historical_data.py --config my_config.json
```

### File Locations

- **Download Script:** `scripts/download_historical_data.py`
- **CSV Output:** `data/csv/{SYMBOL}_{START}_{END}.csv`
- **Parquet Output:** `data/parquet/{SYMBOL}_{START}_{END}.parquet`
- **Logs:** `logs/data_downloader.log`
- **Statistics:** `data/download_stats_*.json`

---

## Support

### Documentation
- [Alpaca API Docs](https://alpaca.markets/docs)
- [Alpaca Python SDK](https://github.com/alpacahq/alpaca-py)
- Project README: `README.md`

### Issues
- Check logs: `logs/data_downloader.log`
- Review statistics: `data/download_stats_*.json`
- Test with simple download: `--symbols AAPL --start 2024-01-01`

### Contact
For project-specific issues, check the project repository or contact the maintainers.

---

## Summary

The historical data downloader is a production-grade tool that:

- Downloads data from Alpaca Markets API
- Supports multiple timeframes (1Min to 1Day)
- Saves in dual formats (CSV and Parquet)
- Includes comprehensive error handling
- Validates all downloaded data
- Provides detailed logging and statistics
- Supports configuration files
- Handles retries automatically

Get started with:
```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31
```

Your data will be ready for backtesting and analysis!
