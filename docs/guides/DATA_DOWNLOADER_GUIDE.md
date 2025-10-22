# Historical Data Downloader Guide

## Overview

The `download_historical_data.py` script is a production-grade tool for downloading historical market data from Alpaca API. It supports multiple output formats, comprehensive error handling, and progress tracking.

## Features

✅ **Dual Format Output**: Saves data in both CSV and Parquet formats
✅ **Automatic Retry**: Exponential backoff retry logic for failed requests
✅ **Progress Tracking**: Real-time progress bars with tqdm
✅ **Data Validation**: Comprehensive validation of downloaded data
✅ **Error Handling**: Robust error handling with detailed logging
✅ **Resume Capability**: Can resume interrupted downloads
✅ **Statistics Tracking**: Detailed download statistics and performance metrics

## Installation

```bash
# Install required dependencies
pip install pandas pyarrow alpaca-py python-dotenv tqdm

# Or use the project's requirements
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Set your Alpaca API credentials in `.env` file:

```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
```

### Configuration File (Optional)

Create a JSON configuration file:

```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "timeframe": "1Day",
  "output_dir": "data",
  "save_csv": true,
  "save_parquet": true,
  "retry_attempts": 3,
  "retry_delay": 5
}
```

## Usage

### Basic Usage

Download data for specific symbols:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31
```

### Using Configuration File

```bash
python scripts/download_historical_data.py --config config.json
```

### Advanced Options

```bash
# Download with custom timeframe
python scripts/download_historical_data.py \
  --symbols AAPL MSFT \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --timeframe 1Hour

# Save only Parquet format (skip CSV)
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --no-csv

# Custom output directory
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output-dir /path/to/data

# Increase retry attempts
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --retry-attempts 5 \
  --retry-delay 10
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--symbols` | List of stock symbols to download | Required* |
| `--start` / `--start-date` | Start date (YYYY-MM-DD) | Required* |
| `--end` / `--end-date` | End date (YYYY-MM-DD) | Today |
| `--timeframe` | Data timeframe (1Min, 5Min, 15Min, 1Hour, 1Day) | 1Day |
| `--output-dir` | Output directory for data | data |
| `--no-csv` | Skip CSV output | False |
| `--no-parquet` | Skip Parquet output | False |
| `--config` | Path to JSON configuration file | None |
| `--retry-attempts` | Number of retry attempts | 3 |
| `--retry-delay` | Initial retry delay (seconds) | 5 |

*Required unless using `--config`

## Output Format

### Data Structure

All downloaded data includes the following columns:

- `timestamp`: Date/time of the bar
- `symbol`: Stock symbol
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume
- `vwap`: Volume-weighted average price
- `trade_count`: Number of trades (if available)

### File Naming Convention

Files are saved with the following naming pattern:

```
{symbol}_{start_date}_{end_date}.{format}
```

Examples:
- `AAPL_2024-01-01_2024-12-31.csv`
- `MSFT_2024-01-01_2024-12-31.parquet`

### Directory Structure

```
data/
├── csv/
│   ├── AAPL_2024-01-01_2024-12-31.csv
│   ├── MSFT_2024-01-01_2024-12-31.csv
│   └── GOOGL_2024-01-01_2024-12-31.csv
├── parquet/
│   ├── AAPL_2024-01-01_2024-12-31.parquet
│   ├── MSFT_2024-01-01_2024-12-31.parquet
│   └── GOOGL_2024-01-01_2024-12-31.parquet
└── download_stats_20241022_120000.json
```

## Data Validation

The downloader performs comprehensive validation:

1. **Completeness Check**: Ensures all required columns are present
2. **Null Value Detection**: Warns about any null values
3. **Price Validation**: Verifies that high >= low and no negative prices
4. **Volume Validation**: Checks for reasonable volume values

## Error Handling

### Automatic Retry

- Failed requests are automatically retried with exponential backoff
- Default: 3 attempts with 5-second initial delay
- Backoff formula: delay * (2 ^ attempt)

### Logging

All operations are logged to:
- Console output (INFO level and above)
- `logs/data_downloader.log` (all levels)

### Error Categories

1. **API Errors**: Connection issues, authentication failures
2. **Validation Errors**: Invalid or incomplete data
3. **File I/O Errors**: Permission issues, disk space
4. **Configuration Errors**: Missing credentials, invalid parameters

## Statistics and Monitoring

### Download Statistics

After completion, statistics are saved to a JSON file:

```json
{
  "total_symbols": 3,
  "successful_downloads": 3,
  "failed_downloads": 0,
  "total_rows": 2520,
  "start_time": "2024-10-22T12:00:00",
  "end_time": "2024-10-22T12:05:30",
  "duration_seconds": 330.5
}
```

### Progress Tracking

Real-time progress bar shows:
- Current symbol being processed
- Overall progress (symbols completed / total symbols)
- Estimated time remaining

## Performance Considerations

### Parquet vs CSV

**Parquet** (Recommended):
- 10-20x smaller file size
- 5-10x faster read performance
- Column-based format ideal for analytics
- Compression enabled by default (Snappy)

**CSV**:
- Human-readable format
- Compatible with all tools
- Easier for manual inspection
- Larger file size

### Best Practices

1. **Use Parquet for production**: Better performance and storage efficiency
2. **Batch downloads**: Download multiple symbols in one run
3. **Choose appropriate timeframe**: 1Day for long-term analysis, 1Hour/1Min for intraday
4. **Monitor API limits**: Alpaca has rate limits, adjust retry delays if needed

## Troubleshooting

### Common Issues

#### Missing API Credentials

```
Error: Alpaca API credentials not found
```

**Solution**: Set environment variables in `.env` file or pass in config

#### No Data Returned

```
Warning: No data returned for SYMBOL
```

**Possible causes**:
- Invalid symbol
- No trading data for date range
- Market closed during timeframe

#### Rate Limiting

```
Error: API rate limit exceeded
```

**Solution**: Increase `--retry-delay` or reduce symbols per batch

### Debug Mode

For detailed debugging, check the log file:

```bash
tail -f logs/data_downloader.log
```

## Integration with Backtesting

The downloaded data is compatible with the backtesting engine:

```python
from src.backtesting.data_handler import CSVDataHandler

# Load downloaded data
data_handler = CSVDataHandler(
    csv_dir='data/csv',
    symbols=['AAPL', 'MSFT'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Use in backtest
engine = BacktestEngine(data_handler, strategy, portfolio)
results = engine.run()
```

## Examples

### Example 1: Quick Download

Download one year of daily data for major tech stocks:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL AMZN TSLA \
  --start 2024-01-01 \
  --end 2024-12-31
```

### Example 2: Intraday Data

Download hourly data for day trading analysis:

```bash
python scripts/download_historical_data.py \
  --symbols SPY QQQ \
  --start 2024-10-01 \
  --end 2024-10-22 \
  --timeframe 1Hour
```

### Example 3: Parquet Only (Production)

Download optimized Parquet files for production use:

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL AMZN TSLA META NFLX \
  --start 2020-01-01 \
  --end 2024-12-31 \
  --no-csv \
  --output-dir /data/production
```

### Example 4: Bulk Download with Config

Create `bulk_download.json`:

```json
{
  "symbols": [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "META", "NFLX", "NVDA", "AMD", "INTC"
  ],
  "start_date": "2023-01-01",
  "end_date": "2024-12-31",
  "timeframe": "1Day",
  "output_dir": "data/bulk",
  "save_csv": false,
  "save_parquet": true,
  "retry_attempts": 5,
  "retry_delay": 10
}
```

Run:

```bash
python scripts/download_historical_data.py --config bulk_download.json
```

## API Reference

### DownloadConfig Class

```python
@dataclass
class DownloadConfig:
    symbols: List[str]          # Stock symbols to download
    start_date: str             # Start date (YYYY-MM-DD)
    end_date: str               # End date (YYYY-MM-DD)
    timeframe: str = "1Day"     # Timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    output_dir: str = "data"
    save_csv: bool = True
    save_parquet: bool = True
    chunk_size: int = 1000
    retry_attempts: int = 3
    retry_delay: int = 5
```

### AlpacaDataDownloader Class

#### Methods

- `download_symbol(symbol: str) -> bool`: Download data for single symbol
- `download_all() -> Dict[str, Any]`: Download all configured symbols
- `_validate_dataframe(df, symbol) -> bool`: Validate downloaded data
- `_save_csv(df, symbol) -> bool`: Save data as CSV
- `_save_parquet(df, symbol) -> bool`: Save data as Parquet

## License

This script is part of the RustAlgorithmTrading project. See project LICENSE for details.

## Support

For issues or questions:
- Check the logs in `logs/data_downloader.log`
- Review the troubleshooting section above
- Open an issue in the project repository
