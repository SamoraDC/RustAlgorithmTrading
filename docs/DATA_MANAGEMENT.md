# Data Management Guide

## Overview

The trading system implements intelligent data management with automatic downloading, caching, and validation of market data from Alpaca API.

## Key Features

- **Automatic Data Download**: Missing data is downloaded automatically
- **Smart Caching**: Data is cached locally in both CSV and Parquet formats
- **Data Freshness**: Automatic refresh of data older than 7 days
- **Retry Logic**: Exponential backoff for API failures
- **Fallback Mechanisms**: Shorter date ranges on failure
- **Format Validation**: Comprehensive data validation

## Data Directory Structure

```
data/
├── historical/          # Historical market data
│   ├── AAPL.csv        # CSV format (compatibility)
│   ├── AAPL.parquet    # Parquet format (performance)
│   ├── MSFT.csv
│   ├── MSFT.parquet
│   └── ...
├── backtest_results/    # Backtesting outputs
├── simulation_results/  # Monte Carlo simulation outputs
└── live_trading/        # Live trading logs
```

## Manual Data Download

### Download Specific Symbols

```bash
# Download 1 year of daily data
python scripts/download_market_data.py \
  --symbols AAPL MSFT GOOGL \
  --days 365 \
  --output-dir data

# Download with specific date range
python scripts/download_market_data.py \
  --symbols TSLA \
  --days 180 \
  --output-dir data
```

### Download Using Configuration File

```bash
# Create config/data_download.json with your settings
python scripts/download_market_data.py --config config/data_download.json
```

### Configuration File Example

```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "days_back": 365,
  "output_dir": "data",
  "save_csv": true,
  "save_parquet": true,
  "retry_attempts": 3,
  "retry_delay": 5
}
```

## Automatic Data Management

The system automatically handles data in several ways:

### 1. Data Handler Auto-Download

When `HistoricalDataHandler` detects missing data, it automatically:

1. Checks for existing data files
2. Attempts to download missing symbols
3. Validates downloaded data
4. Falls back to manual instructions if download fails

Example:

```python
from backtesting.data_handler import HistoricalDataHandler

# Automatically downloads missing data
handler = HistoricalDataHandler(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    data_dir=Path('data/historical'),
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

### 2. Shell Script Integration

The `autonomous_trading_system.sh` includes a data preparation phase:

```bash
# Run with automatic data download
./scripts/autonomous_trading_system.sh --mode=full

# Run backtesting only (includes data download)
./scripts/autonomous_trading_system.sh --mode=backtest-only
```

The script:
- Checks for existing data files
- Verifies data freshness (< 7 days old)
- Downloads missing or stale data
- Falls back to 90-day range on failure
- Validates all required symbols exist

## Data Validation

All downloaded data is validated for:

- **Required Columns**: timestamp, open, high, low, close, volume
- **Price Integrity**: high >= low, no negative prices
- **Data Quality**: No null values in critical columns
- **Time Series**: Sorted by timestamp, no duplicates

## Error Handling

The system handles errors gracefully:

### API Failures

- **Retry Logic**: 3 attempts with exponential backoff
- **Fallback Dates**: Shorter time ranges on failure
- **Clear Messages**: Actionable error messages

### Missing Data

```python
# If data is missing, you'll see:
# ERROR: No data file found for AAPL
# Please download data using: python scripts/download_market_data.py --symbols AAPL
```

### Invalid Data

```python
# If data is corrupt, you'll see:
# ERROR: Invalid price data for AAPL: high < low
# WARNING: Found 5 null timestamps for MSFT
```

## Configuration Options

### Environment Variables

Add to `.env` file:

```bash
# Data management
DATA_DIR=data
DATA_HISTORICAL_DIR=data/historical
DATA_AUTO_DOWNLOAD=true
DATA_MAX_AGE_DAYS=7
DATA_DEFAULT_SYMBOLS=AAPL,MSFT,GOOGL
DATA_DAYS_BACK=365

# Alpaca API (required)
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

### Python Configuration

```python
from config.config import get_config

config = get_config()

# Access data settings
data_dir = config.get('data.data_dir')
auto_download = config.get('data.auto_download')
max_age = config.get('data.max_age_days')
```

## Performance Optimization

### Parquet vs CSV

- **Parquet**: 10x faster loading, 50% smaller files
- **CSV**: Human-readable, universal compatibility
- **Recommendation**: Use Parquet for production, CSV for debugging

### Data Freshness

- **Default**: 7 days before refresh
- **Customizable**: Set `DATA_MAX_AGE_DAYS` in `.env`
- **Manual Refresh**: Delete files to force re-download

## Troubleshooting

### Issue: "No data returned from API"

**Solutions:**
1. Check API credentials in `.env`
2. Verify date range is valid (not weekends/future)
3. Check API rate limits
4. Try shorter date range (90 days)

### Issue: "Failed to download market data"

**Solutions:**
1. Check internet connection
2. Verify Alpaca account is active
3. Check for API maintenance
4. Run manual download with debug:
   ```bash
   python scripts/download_market_data.py --symbols AAPL --days 30
   ```

### Issue: "Missing required columns"

**Solutions:**
1. Re-download data
2. Delete corrupted files
3. Check Alpaca API changes

## Best Practices

1. **Regular Updates**: Let system auto-refresh weekly
2. **Backup Data**: Keep backups of historical data
3. **Monitor Logs**: Check `logs/trading.log` for issues
4. **Test Downloads**: Test with single symbol first
5. **Rate Limits**: Respect Alpaca API limits (200/min)

## API Limits

Alpaca API limits:
- **Free Tier**: IEX feed, 200 requests/minute
- **Data History**: Up to 5 years for free accounts
- **Real-time**: 15-minute delay on free tier

## Next Steps

- [Backtesting Guide](BACKTESTING.md)
- [Configuration Reference](CONFIGURATION.md)
- [API Documentation](API.md)
