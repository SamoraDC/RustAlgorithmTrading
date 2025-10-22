# Alpaca Data Downloader - Quick Start

## Immediate Solution

The downloader was fixed to work with paper trading accounts. Use these commands:

### 1. Test the Fix

```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading
python scripts/test_alpaca_download.py
```

### 2. Download Data

```bash
# Download last 30 days (recommended for testing)
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-09-22 \
  --end 2024-10-22 \
  --feed iex \
  --debug

# Download full year
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-10-22 \
  --feed iex
```

## What Was Fixed

1. **Added `--feed iex`** - Paper accounts require explicit feed parameter
2. **Added `--adjustment all`** - Properly adjust prices for splits/dividends
3. **Added `--debug`** - See detailed error messages
4. **Better error messages** - Tells you exactly what went wrong

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--feed` | `iex` | Data feed (use `iex` for paper accounts) |
| `--adjustment` | `all` | Price adjustments (raw, split, dividend, all) |
| `--debug` | off | Enable detailed logging |

## Output

Data is saved to:
- CSV: `/data/csv/SYMBOL_START_END.csv`
- Parquet: `/data/parquet/SYMBOL_START_END.parquet`

## Troubleshooting

### Still getting "No data returned"?

Try these in order:

1. **Use recent dates** (last 30-90 days):
   ```bash
   python scripts/download_historical_data.py --symbols AAPL --start 2024-09-22 --end 2024-10-22 --feed iex --debug
   ```

2. **Check credentials** in `.env`:
   ```
   ALPACA_API_KEY=PKWT8EA81UL0QP85EYAR
   ALPACA_SECRET_KEY=1xASbdPSlONXPGtGClyUcxULzMeOtDPV7vXCtOTM
   ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
   ```

3. **Try different feed**:
   ```bash
   python scripts/download_historical_data.py --symbols AAPL --start 2024-09-22 --end 2024-10-22 --feed sip --debug
   ```

4. **Verify API access** at https://app.alpaca.markets/

## Success Indicator

When working correctly, you'll see:

```
2024-10-22 15:42:58 - INFO - Fetching data for AAPL (attempt 1/3)
2024-10-22 15:42:59 - INFO - Successfully fetched 21 rows for AAPL
2024-10-22 15:42:59 - INFO - Validated 21 rows for AAPL
2024-10-22 15:42:59 - INFO - Saved CSV: data/csv/AAPL_2024-09-22_2024-10-22.csv
2024-10-22 15:42:59 - INFO - Saved Parquet: data/parquet/AAPL_2024-09-22_2024-10-22.parquet
```

## Next Steps

Once data is downloaded:
1. Verify CSV/Parquet files exist in `/data` directory
2. Check data quality: `head data/csv/AAPL_*.csv`
3. Use data in backtesting engine
