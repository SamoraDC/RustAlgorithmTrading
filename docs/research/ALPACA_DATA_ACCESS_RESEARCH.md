# Alpaca API Data Access Requirements and Limitations - Research Report

**Research Date:** October 22, 2025
**Researcher:** Research Agent
**Project:** RustAlgorithmTrading
**Status:** ✅ Completed

---

## Executive Summary

This comprehensive research report documents Alpaca API data access requirements, limitations, and common issues affecting the RustAlgorithmTrading project. The findings reveal critical limitations with paper trading accounts that directly impact data availability and quality.

### Key Findings

1. **Paper trading accounts are restricted to IEX data only** (8-10% market coverage)
2. **Feed parameter is optional but critical** for data quality
3. **No data returned errors** are primarily due to IEX coverage limitations
4. **Rate limits** are 200 requests/minute with 10 requests/second burst
5. **API migration** from alpaca-trade-api to alpaca-py requires code updates

---

## 1. Paper Trading Account Data Restrictions

### IEX Data Limitation

**Critical Finding:** Paper trading accounts are entitled to receive **only IEX market data**.

- **Market Coverage:** IEX represents approximately **2-8% of total market volume**
- **Data Quality:** Significantly limited compared to SIP (Securities Information Processor) data
- **Example:** On a typical trading day for AAPL:
  - IEX trades: ~12,630
  - Total market trades: ~535,136
  - Coverage: **2.4%**

### Data Availability Comparison

| Data Source | Market Coverage | Historical Depth | Real-time Access | Cost |
|-------------|----------------|------------------|------------------|------|
| **IEX (Free)** | 2-8% of volume | ~5 years | Delayed 1 minute | Free |
| **SIP (Paid)** | 100% of volume | ~7 years | Real-time | $9/month (Algo Trader Plus) |

### Paper Trading Simulation Limitations

**Important:** Paper trading is only a simulation and provides a good approximation but:
- Does not account for real-world slippage
- May have different execution prices
- Does not reflect actual market microstructure
- Pattern day trader rules still apply ($25k minimum for 4+ day trades in 5 days)

---

## 2. Required Feed Parameter (IEX vs SIP)

### Feed Parameter Configuration

The `feed` parameter in `StockBarsRequest` is **optional but critical** for data quality:

```python
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# IEX feed (free, limited coverage)
request_iex = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Day,
    start=datetime(2024, 1, 1),
    end=datetime.now(),
    feed="iex"  # Optional, limited to IEX data
)

# SIP feed (paid subscription required)
request_sip = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Day,
    start=datetime(2024, 1, 1),
    end=datetime.now(),
    feed="sip"  # Requires subscription
)
```

### Data Source Characteristics

**IEX Feed:**
- Source: Investors Exchange LLC
- Historical depth: ~5 years
- Real-time delay: 1 minute (free tier)
- Coverage: 2-8% of market volume
- Best for: Small-scale testing, hobby projects
- **Note:** IEX data is sourced from SIP feed, not the exchange itself

**SIP Feed:**
- Source: All major exchanges consolidated
- Historical depth: ~7 years
- Real-time delay: None (with subscription)
- Coverage: 100% of market volume
- Best for: Production trading, accurate backtesting
- Requires: Algo Trader Plus subscription ($9/month minimum)

### Historical Data Access Rules

1. **IEX Historical Data:**
   - Free access until the last minute
   - No subscription required
   - Limited market coverage

2. **SIP Historical Data:**
   - 15-minute delay for free tier
   - Real-time with subscription
   - Full market coverage
   - Latest endpoints (snapshots) require subscription

---

## 3. Data Availability

### Symbol Coverage

**All Plans:**
- ✅ US Stocks (NYSE, NASDAQ, AMEX)
- ✅ US ETFs
- ✅ Crypto (Bitcoin, Ethereum, etc.)
- ❌ Forex (not supported)
- ❌ International stocks (not supported)
- ❌ Commodities (not supported)

### Timeframe Support

| Timeframe | IEX | SIP | Notes |
|-----------|-----|-----|-------|
| 1 Minute | ✅ | ✅ | High API call volume |
| 5 Minutes | ✅ | ✅ | Recommended for intraday |
| 15 Minutes | ✅ | ✅ | Good balance |
| 1 Hour | ✅ | ✅ | Lower API calls |
| 1 Day | ✅ | ✅ | Most common |
| 1 Week | ✅ | ✅ | Long-term analysis |
| 1 Month | ✅ | ✅ | Very long-term |

### Historical Depth

- **IEX:** Approximately 5 years of historical data
- **SIP:** Approximately 7 years of historical data
- **Crypto:** Varies by asset, generally 3-4 years

### Data Quality Issues

**Sparse Data on IEX:**
- Low-volume stocks may have missing bars
- Wide bid-ask spreads due to limited liquidity
- Gaps in intraday data during low-activity periods
- Not suitable for accurate backtesting

---

## 4. Rate Limits and Best Practices

### API Rate Limits

**All Account Types:**
- **Per-minute limit:** 200 requests
- **Burst limit:** 10 requests per second
- **Enforcement:** HTTP 429 status code returned when exceeded
- **Retry behavior:** SDK automatically retries with exponential backoff

**Upgraded Accounts:**
- **Algo Trader Plus ($9/month):** 1,000 requests per minute
- **Non-retail accounts:** Up to 1,000 requests per minute (contact Alpaca)

### Best Practices for Rate Limit Management

#### 1. Monitor and Optimize Usage

```python
import time
from collections import deque

class RateLimiter:
    """Simple rate limiter for Alpaca API calls."""

    def __init__(self, max_calls=200, time_window=60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()

    def wait_if_needed(self):
        now = time.time()

        # Remove old calls outside time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()

        # Wait if at limit
        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.calls.append(now)
```

#### 2. Batch Requests

```python
# ❌ BAD: Individual requests for each symbol
for symbol in symbols:
    bars = client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end
    ))

# ✅ GOOD: Batch request for multiple symbols
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols=symbols,  # List of symbols
    timeframe=TimeFrame.Day,
    start=start,
    end=end
))
```

#### 3. Implement Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def get_cached_bars(symbol: str, days: int):
    """Cache historical data to reduce API calls."""
    end = datetime.now()
    start = end - timedelta(days=days)

    return client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end
    ))
```

#### 4. Use WebSocket Streaming

```python
from alpaca.data.live import StockDataStream

# ✅ GOOD: Use WebSocket for real-time data (doesn't count against REST API limits)
stream = StockDataStream(api_key, secret_key)

async def trade_handler(data):
    print(f"Trade: {data.symbol} @ ${data.price}")

stream.subscribe_trades(trade_handler, "AAPL")
stream.run()
```

### Rate Limit Error Handling

```python
from alpaca.common.exceptions import APIError
import time

def fetch_with_retry(request_func, max_retries=3):
    """Retry API calls with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return request_func()
        except APIError as e:
            if e.status_code == 429:  # Rate limit exceeded
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

---

## 5. Common "No Data Returned" Causes and Solutions

### Cause 1: IEX Coverage Limitation

**Problem:** Paper trading accounts only receive IEX data, which covers 2-8% of market volume.

**Symptoms:**
```python
bars = client.get_stock_bars(request)
# Returns empty DataFrame or very few bars
```

**Solution:**
- Upgrade to Algo Trader Plus ($9/month) for SIP data
- Use `feed="sip"` parameter (requires subscription)
- Test with high-volume stocks (AAPL, MSFT, TSLA) that trade more on IEX

### Cause 2: Wrong Endpoint for Market Data

**Problem:** Using trading API endpoint for market data requests.

**Symptoms:**
```python
# ❌ WRONG: 404 Not Found
response = requests.get("https://paper-api.alpaca.markets/v2/stocks/AAPL/bars")
```

**Solution:**
```python
# ✅ CORRECT: Use data.alpaca.markets
# Trading API: https://paper-api.alpaca.markets (for orders, positions)
# Market Data API: https://data.alpaca.markets (for bars, quotes, trades)

from alpaca.data.historical import StockHistoricalDataClient

# Correct client initialization
data_client = StockHistoricalDataClient(api_key, secret_key)
```

### Cause 3: Requesting Unsupported Assets

**Problem:** Attempting to fetch data for assets Alpaca doesn't support.

**Supported:**
- ✅ US Stocks (NYSE, NASDAQ, AMEX)
- ✅ US ETFs
- ✅ Crypto (BTC, ETH, etc.)

**Not Supported:**
- ❌ Forex (USD/JPY, EUR/USD, etc.)
- ❌ International stocks
- ❌ Commodities
- ❌ Options (limited support)

**Solution:**
```python
# ❌ WRONG: Forex pair
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="USD/JPY",  # Not supported
    timeframe=TimeFrame.Day
))

# ✅ CORRECT: US stock
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="AAPL",  # Supported
    timeframe=TimeFrame.Day
))
```

### Cause 4: Date Range Issues

**Problem:** Requesting data outside available historical range or during non-trading periods.

**Symptoms:**
```python
# Empty result for weekend or outside market hours
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="AAPL",
    start=datetime(2025, 10, 18),  # Saturday
    end=datetime(2025, 10, 19)     # Sunday
))
```

**Solution:**
```python
from datetime import datetime, timedelta

def get_trading_days_range(days_back=30):
    """Get valid trading day range."""
    end = datetime.now()
    start = end - timedelta(days=days_back * 1.5)  # Add buffer for weekends/holidays

    return start, end

start, end = get_trading_days_range(30)
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Day,
    start=start,
    end=end
))

# Filter to actual trading days
df = bars.df
df = df[df.index.dayofweek < 5]  # Remove weekends
```

### Cause 5: Missing or Invalid Credentials

**Problem:** API requests fail due to authentication issues.

**Symptoms:**
```python
# 403 Forbidden or 401 Unauthorized
APIError: {'message': 'Forbidden'}
```

**Solution:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Verify credentials are loaded
api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

if not api_key or not secret_key:
    raise ValueError("Alpaca credentials not found in environment")

print(f"API Key: {api_key[:8]}...")  # Verify first 8 chars
print(f"Secret Key: {'*' * 20}")     # Never print full secret

# Test connection
from alpaca.trading.client import TradingClient

client = TradingClient(api_key, secret_key, paper=True)
account = client.get_account()
print(f"✓ Connected: {account.status}")
```

### Cause 6: Requesting Real-Time Data Without Subscription

**Problem:** Trying to access real-time SIP data without paid subscription.

**Symptoms:**
```python
# Limited or delayed data returned
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="AAPL",
    feed="sip",  # Requires subscription for real-time
    start=datetime.now() - timedelta(minutes=5),
    end=datetime.now()
))
```

**Solution:**
- Use IEX feed for free real-time (1-minute delay)
- Ensure historical queries are at least 15 minutes old for SIP
- Upgrade to Algo Trader Plus for real-time SIP access

```python
# ✅ Free real-time with IEX
bars_iex = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="AAPL",
    feed="iex",
    start=datetime.now() - timedelta(days=1),
    end=datetime.now()
))

# ✅ Historical SIP (15-min delay is fine)
bars_sip = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols="AAPL",
    feed="sip",
    start=datetime.now() - timedelta(days=30),
    end=datetime.now() - timedelta(minutes=15)  # At least 15 min old
))
```

---

## 6. API Version Differences and Breaking Changes

### alpaca-trade-api vs alpaca-py

**Critical Migration:** Alpaca deprecated `alpaca-trade-api` in favor of `alpaca-py` (end of 2022).

#### Key Differences

| Feature | alpaca-trade-api (Old) | alpaca-py (New) |
|---------|----------------------|-----------------|
| **Support** | ❌ Deprecated (bugs only) | ✅ Active development |
| **Architecture** | Function-based | Object-oriented |
| **Import name** | `alpaca_trade_api` | `alpaca` |
| **Request style** | Direct parameters | Request objects |
| **Market Data v1** | ✅ Supported | ❌ Removed (breaking change) |
| **Client classes** | Single client | Multiple specialized clients |
| **Documentation** | Basic docstrings | Auto-generated from docstrings |

#### Migration Example

**Old (alpaca-trade-api):**
```python
import alpaca_trade_api as tradeapi

# Single client for everything
api = tradeapi.REST(
    key_id='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY',
    base_url='https://paper-api.alpaca.markets'
)

# Direct function calls
account = api.get_account()
bars = api.get_bars(
    'AAPL',
    tradeapi.TimeFrame.Day,
    start='2024-01-01',
    end='2024-12-31'
)
```

**New (alpaca-py):**
```python
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# Separate clients for trading and data
trading_client = TradingClient(
    api_key='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY',
    paper=True
)

data_client = StockHistoricalDataClient(
    api_key='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY'
)

# Account operations use trading client
account = trading_client.get_account()

# Market data uses data client with request objects
request = StockBarsRequest(
    symbol_or_symbols='AAPL',
    timeframe=TimeFrame.Day,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)
bars = data_client.get_stock_bars(request)
```

### Breaking Changes in alpaca-py

#### 1. Market Data v1 Removal (v2.0.0)

**Impact:** Code using v1 endpoints will fail.

**Solution:** Migrate to Market Data v2 API:
- Use `StockHistoricalDataClient` instead of legacy methods
- Update all market data calls to use request objects
- Change endpoint URLs from v1 to v2

#### 2. Import Path Changes

```python
# ❌ OLD
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame

# ✅ NEW
from alpaca.trading.client import TradingClient
from alpaca.data.timeframe import TimeFrame
```

#### 3. Response Format Changes

**Old:** Returns raw dictionaries
**New:** Returns typed model objects

```python
# alpaca-py returns model objects
account = trading_client.get_account()
print(account.cash)           # ✅ Attribute access
print(account['cash'])        # ❌ Dictionary access fails

# Convert to dict if needed
account_dict = {
    'cash': float(account.cash),
    'equity': float(account.equity),
    'buying_power': float(account.buying_power)
}
```

#### 4. TimeFrame Enum Changes

```python
# ❌ OLD
from alpaca_trade_api.rest import TimeFrame
tf = TimeFrame.Day

# ✅ NEW
from alpaca.data.timeframe import TimeFrame
tf = TimeFrame.Day

# Note: Same name, different import path
```

### Version Compatibility

**Current Project Status:**
- Required version: `alpaca-py>=0.42.2` (in requirements.txt)
- Latest version: 0.42.x+ (as of October 2025)
- Python support: 3.8+

**Recommended:**
```bash
pip install alpaca-py>=0.42.2
```

---

## 7. Authentication Requirements for Market Data

### API Key Types

Alpaca provides two types of API keys:

1. **Paper Trading Keys**
   - Access to paper trading endpoints
   - Access to market data (IEX only on free tier)
   - Separate from live trading keys
   - Safe for development and testing

2. **Live Trading Keys**
   - Access to live trading endpoints
   - Access to market data (same restrictions apply)
   - **WARNING:** Real money at risk

### Authentication Setup

#### Environment Variables (Recommended)

Create `.env` file:
```bash
# Paper Trading (Safe for development)
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Optional: Market data feed preference
ALPACA_FEED=iex  # or 'sip' with subscription
```

Load in Python:
```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")
```

#### Client Initialization

```python
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient

# Trading client (for orders, positions, account)
trading_client = TradingClient(
    api_key=api_key,
    secret_key=secret_key,
    paper=True  # ALWAYS True for safety
)

# Data client (for market data)
data_client = StockHistoricalDataClient(
    api_key=api_key,
    secret_key=secret_key
    # Note: No 'paper' parameter - same keys work for both
)
```

### Security Best Practices

1. **Never hardcode credentials**
   ```python
   # ❌ NEVER DO THIS
   client = TradingClient(
       api_key="PKWT8EA81UL0QP85EYAR",
       secret_key="1xASbdPSlONXPGtGClyUcxULzMeOtDPV7vXCtOTM"
   )

   # ✅ USE ENVIRONMENT VARIABLES
   client = TradingClient(
       api_key=os.getenv("ALPACA_API_KEY"),
       secret_key=os.getenv("ALPACA_SECRET_KEY")
   )
   ```

2. **Add .env to .gitignore**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Use different keys for development and production**

4. **Rotate keys regularly**

5. **Never commit .env files to git**

### Permission Validation

```python
def validate_alpaca_credentials():
    """Validate Alpaca API credentials and permissions."""
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient

    try:
        # Test trading client
        trading_client = TradingClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            paper=True
        )
        account = trading_client.get_account()
        print(f"✓ Trading API: {account.status}")
        print(f"  Account type: {'Paper' if account.status == 'ACTIVE' else 'Unknown'}")

        # Test data client
        data_client = StockHistoricalDataClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY")
        )

        # Try to fetch recent data
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from datetime import datetime, timedelta

        bars = data_client.get_stock_bars(StockBarsRequest(
            symbol_or_symbols="AAPL",
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=5),
            end=datetime.now()
        ))

        bar_count = len(bars.data.get("AAPL", []))
        print(f"✓ Market Data API: {bar_count} bars retrieved")

        return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
```

---

## 8. Recommendations for RustAlgorithmTrading Project

### Immediate Actions

1. **Update Data Fetching Logic**
   ```python
   # Add explicit feed parameter handling
   def get_historical_bars(symbol, start, end, feed="iex"):
       """Fetch historical bars with feed awareness."""
       request = StockBarsRequest(
           symbol_or_symbols=symbol,
           timeframe=TimeFrame.Day,
           start=start,
           end=end,
           feed=feed  # Make feed explicit
       )
       return data_client.get_stock_bars(request)
   ```

2. **Implement Robust Error Handling**
   ```python
   from alpaca.common.exceptions import APIError

   def fetch_with_fallback(symbol, start, end):
       """Try SIP first, fall back to IEX if no subscription."""
       try:
           # Try SIP (better data)
           return get_historical_bars(symbol, start, end, feed="sip")
       except APIError as e:
           if "subscription" in str(e).lower():
               logger.warning(f"SIP not available, falling back to IEX for {symbol}")
               return get_historical_bars(symbol, start, end, feed="iex")
           raise
   ```

3. **Add Data Quality Validation**
   ```python
   def validate_data_quality(bars, symbol):
       """Check if data quality is sufficient."""
       if bars.empty:
           logger.error(f"No data returned for {symbol}")
           return False

       # Check for sufficient data points
       if len(bars) < 10:
           logger.warning(f"Limited data for {symbol}: only {len(bars)} bars")

       # Check for gaps in data
       date_diffs = bars.index.to_series().diff()
       max_gap = date_diffs.max()
       if max_gap > timedelta(days=5):
           logger.warning(f"Data gap detected for {symbol}: {max_gap}")

       return True
   ```

4. **Implement Rate Limiting**
   ```python
   from time import sleep
   from collections import deque

   class AlpacaRateLimiter:
       def __init__(self):
           self.calls = deque(maxlen=200)

       def wait_if_needed(self):
           now = time.time()
           if len(self.calls) >= 200:
               oldest = self.calls[0]
               wait_time = 60 - (now - oldest)
               if wait_time > 0:
                   logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                   sleep(wait_time)
           self.calls.append(now)

   # Use in fetcher
   rate_limiter = AlpacaRateLimiter()

   def fetch_with_rate_limit(symbol, start, end):
       rate_limiter.wait_if_needed()
       return get_historical_bars(symbol, start, end)
   ```

### Medium-Term Improvements

1. **Consider Upgrading to Algo Trader Plus**
   - Cost: $9/month
   - Benefits:
     - SIP data access (100% market coverage)
     - 1,000 requests/minute (5x increase)
     - Real-time data access
     - More accurate backtesting

2. **Implement Data Caching**
   ```python
   import pickle
   from pathlib import Path

   CACHE_DIR = Path("data/cache")
   CACHE_DIR.mkdir(parents=True, exist_ok=True)

   def get_cached_bars(symbol, start, end):
       """Get bars with file-based caching."""
       cache_key = f"{symbol}_{start.date()}_{end.date()}.pkl"
       cache_file = CACHE_DIR / cache_key

       if cache_file.exists():
           logger.info(f"Loading cached data for {symbol}")
           with open(cache_file, 'rb') as f:
               return pickle.load(f)

       # Fetch and cache
       bars = fetch_with_rate_limit(symbol, start, end)
       with open(cache_file, 'wb') as f:
           pickle.dump(bars, f)

       return bars
   ```

3. **Add Data Quality Metrics**
   ```python
   def calculate_data_quality_score(bars):
       """Calculate data quality score (0-100)."""
       if bars.empty:
           return 0

       score = 100

       # Penalize for missing data
       expected_days = (bars.index.max() - bars.index.min()).days
       actual_days = len(bars)
       completeness = actual_days / max(expected_days / 1.5, 1)  # Account for weekends
       score *= completeness

       # Penalize for low volume (IEX indicator)
       avg_volume = bars['volume'].mean()
       if avg_volume < 100000:
           score *= 0.7  # Likely IEX-only data

       return min(score, 100)
   ```

### Long-Term Strategy

1. **Data Source Diversification**
   - Consider alternative data providers (Polygon, Alpha Vantage)
   - Implement provider abstraction layer
   - Use multiple sources for validation

2. **Real-time Data Streaming**
   ```python
   from alpaca.data.live import StockDataStream

   stream = StockDataStream(api_key, secret_key)

   async def handle_bar(bar):
       logger.info(f"Real-time bar: {bar.symbol} ${bar.close}")

   stream.subscribe_bars(handle_bar, "AAPL")
   stream.run()
   ```

3. **Historical Data Management**
   - Build local historical database
   - Incremental updates instead of full refetch
   - DuckDB for efficient time-series queries

---

## 9. Code Review: Current Implementation

### Analysis of src/api/alpaca_client.py

**Strengths:**
✅ Good error handling with try-except blocks
✅ Proper logging with loguru
✅ Environment variable configuration
✅ Separate trading and data clients

**Issues Identified:**

1. **Missing Feed Parameter**
   ```python
   # Current (line 134-139)
   request_params = StockBarsRequest(
       symbol_or_symbols=symbol,
       timeframe=timeframe,
       start=start,
       end=end
   )

   # Recommended: Add feed parameter
   request_params = StockBarsRequest(
       symbol_or_symbols=symbol,
       timeframe=timeframe,
       start=start,
       end=end,
       feed="iex"  # Explicit feed selection
   )
   ```

2. **No Rate Limiting**
   - Current implementation has no rate limiting
   - Risk of hitting 200 requests/minute limit
   - Recommendation: Add rate limiter class

3. **Limited Error Context**
   - Generic error messages don't indicate cause
   - Recommendation: Add specific error types

### Analysis of src/api/alpaca_paper_trading.py

**Strengths:**
✅ Comprehensive functionality
✅ Excellent safety checks (forced paper trading)
✅ Good type hints and documentation
✅ Portfolio metrics calculation
✅ Order validation before submission

**Issues Identified:**

1. **No Feed Parameter in get_historical_bars (line 571-620)**
   ```python
   # Missing feed parameter - add it
   def get_historical_bars(
       self,
       symbol: str,
       start: datetime,
       end: datetime,
       timeframe: TimeFrame = TimeFrame.Day,
       feed: str = "iex"  # ADD THIS
   ) -> List[Dict[str, Any]]:
   ```

2. **No Data Quality Validation**
   - Returns empty list on failure
   - No warning about data limitations
   - Recommendation: Add quality checks

### Analysis of src/data/fetcher.py

**Issues Identified:**

1. **No Error Recovery**
   ```python
   # Line 61-62: Returns empty DataFrame on error
   except Exception as e:
       logger.error(f"Failed to fetch {symbol}: {e}")
       data[symbol] = pd.DataFrame()
   ```

   **Recommendation:** Implement retry logic and data quality validation

2. **No Rate Limiting**
   - Fetches multiple symbols in loop without delay
   - Risk: Exceed 200 requests/minute
   - Recommendation: Add rate limiter

3. **No Caching**
   - Refetches same data repeatedly
   - Wastes API quota
   - Recommendation: Implement caching layer

---

## 10. Testing Recommendations

### Unit Tests

```python
# tests/test_alpaca_data_access.py

import pytest
from datetime import datetime, timedelta
from src.api.alpaca_client import AlpacaClient

def test_iex_data_access():
    """Test IEX data fetching."""
    client = AlpacaClient(paper=True)

    bars = client.get_historical_bars(
        symbol="AAPL",
        start=datetime.now() - timedelta(days=5),
        end=datetime.now(),
        timeframe=TimeFrame.Day
    )

    assert not bars.empty, "Should return data for AAPL"
    assert 'close' in bars.columns
    assert len(bars) > 0

def test_rate_limiting():
    """Test rate limiter prevents 429 errors."""
    client = AlpacaClient(paper=True)
    rate_limiter = AlpacaRateLimiter()

    # Make 10 rapid requests
    for i in range(10):
        rate_limiter.wait_if_needed()
        bars = client.get_historical_bars(
            symbol="AAPL",
            start=datetime.now() - timedelta(days=1),
            end=datetime.now()
        )

    # Should complete without errors

def test_unsupported_asset():
    """Test handling of unsupported assets."""
    client = AlpacaClient(paper=True)

    with pytest.raises(Exception):
        bars = client.get_historical_bars(
            symbol="USD/JPY",  # Forex not supported
            start=datetime.now() - timedelta(days=5),
            end=datetime.now()
        )

def test_data_quality_validation():
    """Test data quality scoring."""
    client = AlpacaClient(paper=True)

    bars = client.get_historical_bars(
        symbol="AAPL",
        start=datetime.now() - timedelta(days=30),
        end=datetime.now()
    )

    score = calculate_data_quality_score(bars)
    assert score > 50, f"Data quality too low: {score}"
```

### Integration Tests

```python
def test_end_to_end_data_pipeline():
    """Test complete data fetching pipeline."""
    from src.api.alpaca_client import AlpacaClient
    from src.data.fetcher import DataFetcher

    client = AlpacaClient(paper=True)
    fetcher = DataFetcher(client)

    # Fetch multiple symbols
    symbols = ["AAPL", "MSFT", "GOOGL"]
    data = fetcher.fetch_multiple_symbols(
        symbols=symbols,
        start=datetime.now() - timedelta(days=30),
        end=datetime.now()
    )

    # Validate results
    for symbol in symbols:
        assert symbol in data
        assert not data[symbol].empty
        assert len(data[symbol]) > 20  # At least 20 trading days
```

---

## 11. Summary and Action Items

### Critical Findings

1. ⚠️ **Paper trading accounts are limited to IEX data** (2-8% market coverage)
2. ⚠️ **Current codebase doesn't specify feed parameter** (defaults to IEX)
3. ⚠️ **No rate limiting implemented** (risk of 429 errors)
4. ⚠️ **No data quality validation** (may use incomplete data)
5. ⚠️ **No caching** (wastes API quota)

### Recommended Action Items

#### High Priority (Immediate)

- [ ] Add `feed` parameter to all `StockBarsRequest` calls
- [ ] Implement rate limiter class
- [ ] Add data quality validation
- [ ] Update error messages to be more descriptive
- [ ] Test with high-volume stocks (AAPL, MSFT, TSLA)

#### Medium Priority (This Week)

- [ ] Implement caching layer for historical data
- [ ] Add retry logic for transient failures
- [ ] Create data quality metrics dashboard
- [ ] Write comprehensive unit tests
- [ ] Document IEX limitations in README

#### Low Priority (Long Term)

- [ ] Consider upgrading to Algo Trader Plus ($9/month)
- [ ] Implement WebSocket streaming for real-time data
- [ ] Build local historical database
- [ ] Add alternative data provider support
- [ ] Implement data quality monitoring

### Cost-Benefit Analysis

**Current Setup (Free Paper Trading + IEX):**
- Cost: $0/month
- Data coverage: 2-8% of market volume
- Rate limit: 200 requests/minute
- Real-time delay: 1 minute
- **Best for:** Initial development, testing, hobby projects

**Algo Trader Plus Upgrade:**
- Cost: $9/month
- Data coverage: 100% of market volume
- Rate limit: 1,000 requests/minute
- Real-time delay: None
- **Best for:** Serious backtesting, production trading

---

## 12. Additional Resources

### Official Documentation

- [Alpaca API Docs](https://docs.alpaca.markets/)
- [alpaca-py SDK](https://alpaca.markets/sdks/python/)
- [Market Data FAQ](https://docs.alpaca.markets/docs/market-data-faq)
- [Paper Trading Guide](https://docs.alpaca.markets/docs/paper-trading)

### Community Resources

- [Alpaca Community Forum](https://forum.alpaca.markets/)
- [alpaca-py GitHub](https://github.com/alpacahq/alpaca-py)
- [API Status Page](https://status.alpaca.markets/)

### Code Examples

- [alpaca-py Examples](https://github.com/alpacahq/alpaca-py/tree/master/examples)
- [Alpaca Blog Tutorials](https://alpaca.markets/learn/)

---

## Appendix A: Environment Configuration

### Complete .env Template

```bash
# Alpaca API Credentials (Paper Trading)
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Market Data Configuration
ALPACA_FEED=iex  # Options: 'iex' (free) or 'sip' (subscription required)
ALPACA_DATA_URL=https://data.alpaca.markets

# Rate Limiting
ALPACA_MAX_REQUESTS_PER_MINUTE=200
ALPACA_MAX_BURST_REQUESTS=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading_system.log

# Application
ENVIRONMENT=development  # Options: development, staging, production
```

### Python Configuration

```python
# config/alpaca_config.py

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AlpacaConfig:
    """Alpaca API configuration."""

    api_key: str = os.getenv("ALPACA_API_KEY", "")
    secret_key: str = os.getenv("ALPACA_SECRET_KEY", "")
    base_url: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    data_url: str = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")
    feed: str = os.getenv("ALPACA_FEED", "iex")
    max_requests_per_minute: int = int(os.getenv("ALPACA_MAX_REQUESTS_PER_MINUTE", "200"))
    max_burst_requests: int = int(os.getenv("ALPACA_MAX_BURST_REQUESTS", "10"))
    paper: bool = True  # Always True for safety

    def validate(self) -> bool:
        """Validate configuration."""
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials not configured")

        if self.feed not in ["iex", "sip"]:
            raise ValueError(f"Invalid feed: {self.feed}")

        return True

# Global config instance
config = AlpacaConfig()
config.validate()
```

---

## Appendix B: Error Code Reference

| Error Code | Meaning | Common Cause | Solution |
|------------|---------|--------------|----------|
| 401 | Unauthorized | Invalid API credentials | Check API key and secret |
| 403 | Forbidden | Missing or invalid headers | Ensure proper authentication |
| 404 | Not Found | Wrong endpoint or unsupported symbol | Verify endpoint URL and symbol |
| 422 | Unprocessable Entity | Invalid request parameters | Check request format |
| 429 | Too Many Requests | Rate limit exceeded | Implement rate limiting |
| 500 | Internal Server Error | Alpaca server issue | Retry with exponential backoff |
| 503 | Service Unavailable | Maintenance or outage | Check status page |

---

## Appendix C: Data Feed Comparison Matrix

| Feature | IEX (Free) | SIP (Paid) | Upgrade Required |
|---------|------------|------------|------------------|
| **Coverage** | 2-8% | 100% | Yes |
| **Real-time access** | 1 min delay | Immediate | Yes |
| **Historical depth** | ~5 years | ~7 years | Yes |
| **Rate limit** | 200/min | 1,000/min | Yes |
| **Snapshot API** | ❌ | ✅ | Yes |
| **Options data** | Limited | Full | Yes |
| **Crypto data** | ✅ | ✅ | No |
| **Cost** | Free | $9/month | Yes |
| **Best for** | Testing | Production | - |

---

## Document Metadata

**Version:** 1.0
**Last Updated:** October 22, 2025
**Author:** Research Agent (Hive Coordination System)
**Review Status:** Completed
**Next Review:** November 22, 2025

**Change Log:**
- 2025-10-22: Initial comprehensive research report created
- 2025-10-22: Added code analysis and recommendations
- 2025-10-22: Added testing recommendations and action items

---

**End of Report**
