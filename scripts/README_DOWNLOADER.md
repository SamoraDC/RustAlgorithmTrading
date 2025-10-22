# Historical Data Downloader - Quick Start

## Quick Usage

### 1. Set up credentials (one-time)

Create `.env` file in project root:
```bash
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
```

### 2. Download data

**Basic - Download 3 symbols for 2024:**
```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31
```

**Using config file:**
```bash
python scripts/download_historical_data.py \
  --config scripts/download_config_example.json
```

**Hourly data:**
```bash
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-10-01 \
  --end 2024-10-22 \
  --timeframe 1Hour
```

### 3. Check output

```bash
ls -lh data/csv/
ls -lh data/parquet/
```

## Output Files

- CSV: `data/csv/AAPL_2024-01-01_2024-12-31.csv`
- Parquet: `data/parquet/AAPL_2024-01-01_2024-12-31.parquet`
- Stats: `data/download_stats_*.json`

## Data Columns

All files include:
- timestamp
- symbol
- open, high, low, close
- volume
- vwap (volume-weighted average price)
- trade_count

## Need Help?

See full documentation: `docs/guides/DATA_DOWNLOADER_GUIDE.md`

## Common Issues

**No credentials:**
```
Error: Alpaca API credentials not found
```
→ Create `.env` file with API keys

**No data returned:**
```
Warning: No data returned for SYMBOL
```
→ Check symbol exists and date range is valid

**Rate limit:**
```
Error: API rate limit exceeded
```
→ Add `--retry-delay 10` to slow down requests
