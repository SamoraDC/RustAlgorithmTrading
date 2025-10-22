# Alpaca Data Downloader Fix

## Problem

The historical data downloader was connecting to Alpaca API successfully but returning no data for requested symbols (AAPL, MSFT, GOOGL).

## Root Cause

Paper trading accounts require specific API parameters that were missing:

1. **Feed parameter** - Alpaca offers multiple data feeds (IEX, SIP, OTC). Paper accounts typically have free access to IEX feed only.
2. **Adjustment parameter** - Price adjustments for splits and dividends were not specified.
3. **Limited error messages** - The script didn't provide enough detail about why requests failed.

## Solution

### Changes Applied

#### 1. Added Feed and Adjustment Parameters

**File**: `/scripts/download_historical_data.py`

```python
# Added to DownloadConfig dataclass
feed: str = "iex"  # Data feed: 'iex' (free), 'sip' (requires subscription), or 'otc'
adjustment: str = "all"  # Price adjustments: 'raw', 'split', 'dividend', or 'all'
```

#### 2. Updated API Request

```python
from alpaca.data.enums import Adjustment

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
    feed=self.config.feed,  # NEW
    adjustment=adjustment   # NEW
)
```

#### 3. Enhanced Error Logging

Added detailed debug logging:
- Request parameters
- API response details
- Specific error context (403, 404, rate limits, etc.)
- Actionable suggestions for common issues

```python
logger.debug(f"Request parameters: timeframe={timeframe}, start={self.config.start_date}, "
           f"end={self.config.end_date}, feed={self.config.feed}, adjustment={adjustment}")

if not bars:
    logger.error(f"No response from API for {symbol}")
    logger.error(f"This may indicate: 1) Invalid date range, 2) No trading data for period, "
               f"3) Data feed '{self.config.feed}' not available for paper trading account")
```

#### 4. New CLI Arguments

```bash
--feed {iex,sip,otc}     # Data feed source (default: iex)
--adjustment {raw,split,dividend,all}  # Price adjustment type (default: all)
--debug                  # Enable debug logging
```

## Usage

### Basic Usage (with new parameters)

```bash
python scripts/download_historical_data.py \
  --symbols AAPL MSFT GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --feed iex \
  --adjustment all
```

### With Debug Logging

```bash
python scripts/download_historical_data.py \
  --symbols AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --feed iex \
  --debug
```

### Test Different Feeds

```bash
# Try IEX feed (free for paper accounts)
python scripts/download_historical_data.py --symbols AAPL --start 2024-01-01 --end 2024-12-31 --feed iex

# Try SIP feed (requires subscription)
python scripts/download_historical_data.py --symbols AAPL --start 2024-01-01 --end 2024-12-31 --feed sip
```

## Testing

A comprehensive test script is provided:

```bash
python scripts/test_alpaca_download.py
```

This script tests:
1. API connection
2. Different data feeds (IEX, SIP)
3. Various date ranges
4. Full download workflow

## Common Issues and Solutions

### Issue: "No data returned"

**Solutions:**
1. Use `--feed iex` explicitly (free for paper accounts)
2. Verify date range is not weekends/holidays/future dates
3. Use recent dates (last 5 years for free historical data)
4. Enable debug mode: `--debug`

### Issue: 403 Unauthorized

**Solutions:**
1. Verify API credentials in `.env` file
2. Check that credentials match paper or live account type

### Issue: Feed not available

**Solutions:**
1. Paper accounts: Use `--feed iex`
2. Live accounts: May use `--feed sip` (requires subscription)

## Data Feeds Comparison

| Feed | Access | Cost | Coverage |
|------|--------|------|----------|
| IEX | Free with paper accounts | Free | Major exchanges |
| SIP | Requires subscription | Paid | All exchanges (consolidated) |
| OTC | Limited availability | Varies | Over-the-counter |

## Technical Details

### Request Parameters

```python
StockBarsRequest(
    symbol_or_symbols=['AAPL'],      # Symbols to fetch
    timeframe=TimeFrame.Day,          # Bar timeframe
    start='2024-01-01',               # Start date (ISO format)
    end='2024-12-31',                 # End date (ISO format)
    feed='iex',                       # Data feed source
    adjustment=Adjustment.ALL         # Price adjustments
)
```

### Adjustment Types

- **raw**: No adjustments
- **split**: Adjust for stock splits only
- **dividend**: Adjust for dividends only
- **all**: Adjust for both splits and dividends (recommended)

## Files Modified

1. `/scripts/download_historical_data.py` - Main downloader with fixes
2. `/scripts/test_alpaca_download.py` - New test script (created)
3. `/docs/fixes/ALPACA_DOWNLOADER_FIX.md` - This documentation (created)

## Validation

Run the test script to verify all fixes:

```bash
python scripts/test_alpaca_download.py
```

Expected output:
```
TEST SUMMARY
================================================================================
API Connection: PASS
Data Fetch (Feeds): PASS
Full Download: PASS

ALL TESTS PASSED!
```

## Next Steps

1. Run test script to validate fixes
2. Download sample data with debug enabled
3. Verify CSV/Parquet files are created
4. Check data quality and date ranges

## References

- [Alpaca API Documentation](https://docs.alpaca.markets/docs/market-data)
- [Alpaca Python SDK](https://github.com/alpacahq/alpaca-py)
- Data Feeds: https://docs.alpaca.markets/docs/market-data#data-feeds
