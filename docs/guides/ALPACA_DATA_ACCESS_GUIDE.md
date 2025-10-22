# Alpaca API Data Access Guide

> **Comprehensive guide to accessing market data via Alpaca Markets API for algorithmic trading**

## Table of Contents

1. [Authentication & Setup](#1-authentication--setup)
2. [Real-time Data Access](#2-real-time-data-access)
3. [Historical Data Access](#3-historical-data-access)
4. [Data Download Workflow](#4-data-download-workflow)
5. [Integration with Trading System](#5-integration-with-trading-system)
6. [Code Examples](#6-code-examples)
7. [Best Practices](#7-best-practices)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Authentication & Setup

### 1.1 API Credentials

Alpaca Markets uses API key-based authentication with two components:

- **API Key ID**: Public identifier (safe to log)
- **Secret Key**: Private credential (never commit to version control)

### 1.2 Environment Configuration

#### Paper vs Live Trading

| Environment | API URL | Data Feed | Purpose |
|-------------|---------|-----------|---------|
| **Paper** | `https://paper-api.alpaca.markets` | Real-time market data | Development & testing |
| **Live** | `https://api.alpaca.markets` | Real-time market data | Production trading |

**Important**: Always start with paper trading to validate your implementation.

#### Obtaining API Keys

1. Sign up at [alpaca.markets](https://alpaca.markets)
2. Navigate to **Dashboard → API Keys**
3. Click **Generate New Key**
4. Select environment (Paper or Live)
5. **Save both keys immediately** (secret shown only once)

### 1.3 Client Initialization

#### Python Implementation

```python
# .env file configuration
ALPACA_API_KEY=YOUR_API_KEY_ID
ALPACA_SECRET_KEY=YOUR_SECRET_KEY
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Python client initialization
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from dotenv import load_dotenv
import os

load_dotenv()

# Trading client for account/orders
trading_client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True  # Set to False for live trading
)

# Data client for market data
data_client = StockHistoricalDataClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY")
)
```

#### Rust Implementation

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};

pub struct AlpacaDataClient {
    client: Client,
    api_key: String,
    secret_key: String,
    base_url: String,
}

impl AlpacaDataClient {
    pub fn new(api_key: String, secret_key: String, paper: bool) -> Self {
        let base_url = if paper {
            "https://data.alpaca.markets".to_string()
        } else {
            "https://data.alpaca.markets".to_string()
        };

        Self {
            client: Client::new(),
            api_key,
            secret_key,
            base_url,
        }
    }

    fn create_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert("APCA-API-KEY-ID", self.api_key.parse().unwrap());
        headers.insert("APCA-API-SECRET-KEY", self.secret_key.parse().unwrap());
        headers
    }
}
```

---

## 2. Real-time Data Access

### 2.1 Latest Quotes

Get the most recent bid/ask for a symbol.

#### Python Example

```python
from alpaca.data.requests import StockLatestQuoteRequest

# Request latest quote
request = StockLatestQuoteRequest(symbol_or_symbols="AAPL")
latest_quote = data_client.get_stock_latest_quote(request)

# Access quote data
quote = latest_quote["AAPL"]
print(f"Bid: ${quote.bid_price} x {quote.bid_size}")
print(f"Ask: ${quote.ask_price} x {quote.ask_size}")
print(f"Spread: ${quote.ask_price - quote.bid_price:.2f}")
```

**Response Structure**:
```python
{
    "AAPL": {
        "bid_price": 175.23,
        "bid_size": 100,
        "ask_price": 175.26,
        "ask_size": 200,
        "timestamp": "2024-10-22T14:30:00.123456Z"
    }
}
```

### 2.2 Latest Trades

Get the most recent trade execution.

```python
from alpaca.data.requests import StockLatestTradeRequest

request = StockLatestTradeRequest(symbol_or_symbols="AAPL")
latest_trade = data_client.get_stock_latest_trade(request)

trade = latest_trade["AAPL"]
print(f"Price: ${trade.price}")
print(f"Size: {trade.size} shares")
print(f"Timestamp: {trade.timestamp}")
```

### 2.3 WebSocket Streaming (Real-time)

For live trading strategies, use WebSocket for sub-second latency.

#### Python WebSocket Example

```python
from alpaca.data.live import StockDataStream

# Initialize WebSocket stream
stream = StockDataStream(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY")
)

# Define callbacks
async def trade_callback(trade):
    print(f"Trade: {trade.symbol} @ ${trade.price} ({trade.size} shares)")

async def quote_callback(quote):
    print(f"Quote: {quote.symbol} - Bid: ${quote.bid_price} Ask: ${quote.ask_price}")

async def bar_callback(bar):
    print(f"Bar: {bar.symbol} - O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close}")

# Subscribe to streams
stream.subscribe_trades(trade_callback, "AAPL", "MSFT", "GOOGL")
stream.subscribe_quotes(quote_callback, "AAPL", "MSFT")
stream.subscribe_bars(bar_callback, "AAPL")  # 1-minute bars

# Start streaming (blocking)
stream.run()
```

#### Rust WebSocket Example

```rust
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures_util::{StreamExt, SinkExt};
use serde_json::json;

pub async fn connect_websocket(api_key: &str, secret_key: &str) -> Result<()> {
    let url = "wss://stream.data.alpaca.markets/v2/sip";
    let (ws_stream, _) = connect_async(url).await?;
    let (mut write, mut read) = ws_stream.split();

    // Authenticate
    let auth_msg = json!({
        "action": "auth",
        "key": api_key,
        "secret": secret_key
    });
    write.send(Message::Text(auth_msg.to_string())).await?;

    // Wait for auth confirmation
    if let Some(Ok(Message::Text(msg))) = read.next().await {
        println!("Auth response: {}", msg);
    }

    // Subscribe to trades and quotes
    let subscribe_msg = json!({
        "action": "subscribe",
        "trades": ["AAPL", "MSFT"],
        "quotes": ["AAPL", "MSFT"],
        "bars": ["AAPL"]
    });
    write.send(Message::Text(subscribe_msg.to_string())).await?;

    // Process incoming messages
    while let Some(Ok(Message::Text(msg))) = read.next().await {
        process_market_data(&msg);
    }

    Ok(())
}

fn process_market_data(msg: &str) {
    if let Ok(data) = serde_json::from_str::<Vec<serde_json::Value>>(msg) {
        for item in data {
            match item["T"].as_str() {
                Some("t") => println!("Trade: {:?}", item),
                Some("q") => println!("Quote: {:?}", item),
                Some("b") => println!("Bar: {:?}", item),
                _ => {}
            }
        }
    }
}
```

---

## 3. Historical Data Access

### 3.1 StockBarsRequest (OHLCV Data)

The primary method for retrieving historical candlestick data.

#### Available Timeframes

| Timeframe | Use Case | Data Points/Day |
|-----------|----------|-----------------|
| `TimeFrame.Minute` | High-frequency trading | 390 (6.5 hours) |
| `TimeFrame.Hour` | Intraday strategies | 6-7 |
| `TimeFrame.Day` | Swing trading | 1 |
| `TimeFrame.Week` | Position trading | 1/5 |
| `TimeFrame.Month` | Long-term analysis | 1/20 |

#### Python Example - Multiple Timeframes

```python
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# 1-minute bars for today
request_1min = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Minute,
    start=datetime.now().replace(hour=9, minute=30),
    end=datetime.now()
)

# 1-hour bars for last 30 days
request_1hour = StockBarsRequest(
    symbol_or_symbols=["AAPL", "MSFT", "GOOGL"],
    timeframe=TimeFrame.Hour,
    start=datetime.now() - timedelta(days=30),
    end=datetime.now()
)

# 1-day bars for 5 years
request_1day = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=5*365),
    end=datetime.now()
)

# Fetch data
bars_1min = data_client.get_stock_bars(request_1min)
bars_1hour = data_client.get_stock_bars(request_1hour)
bars_1day = data_client.get_stock_bars(request_1day)

# Convert to DataFrame
df_1min = bars_1min.df
df_1hour = bars_1hour.df
df_1day = bars_1day.df
```

### 3.2 Date Range Handling

#### Timezone Considerations

Alpaca returns timestamps in UTC. Convert to US/Eastern for market hours:

```python
import pytz

# Convert UTC to US/Eastern
eastern = pytz.timezone('US/Eastern')
df['timestamp_et'] = df.index.tz_convert(eastern)

# Filter market hours (9:30 AM - 4:00 PM ET)
market_hours = df.between_time('09:30', '16:00')
```

#### Dynamic Date Ranges

```python
from datetime import datetime, timedelta

def get_last_n_trading_days(symbol: str, n_days: int) -> pd.DataFrame:
    """
    Fetch last N trading days (excludes weekends/holidays)
    """
    end = datetime.now()
    # Request extra days to account for weekends
    start = end - timedelta(days=n_days * 1.5)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end
    )

    bars = data_client.get_stock_bars(request)
    df = bars.df

    # Return only the last n_days
    return df.tail(n_days)
```

### 3.3 Pagination for Large Datasets

Alpaca limits responses to 10,000 bars per request. Use pagination for larger datasets:

```python
def fetch_all_bars_paginated(symbol: str, start: datetime, end: datetime,
                             timeframe: TimeFrame) -> pd.DataFrame:
    """
    Fetch all bars with automatic pagination
    """
    all_bars = []
    current_start = start

    while current_start < end:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=current_start,
            end=end,
            limit=10000  # Max per request
        )

        bars = data_client.get_stock_bars(request)
        df = bars.df

        if df.empty:
            break

        all_bars.append(df)

        # Update start to last timestamp + 1 interval
        current_start = df.index[-1] + timedelta(minutes=1)

        print(f"Fetched {len(df)} bars, total: {sum(len(b) for b in all_bars)}")

    return pd.concat(all_bars) if all_bars else pd.DataFrame()
```

---

## 4. Data Download Workflow

### 4.1 Bulk Historical Data Download

Complete workflow for downloading and storing historical data.

```python
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

class DataDownloader:
    """
    Bulk historical data downloader with caching
    """

    def __init__(self, data_client, cache_dir: str = "data/cache"):
        self.data_client = data_client
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_historical_data(
        self,
        symbols: list[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: TimeFrame = TimeFrame.Day
    ) -> dict[str, pd.DataFrame]:
        """
        Download historical data for multiple symbols
        """
        results = {}

        for symbol in symbols:
            print(f"Downloading {symbol}...")

            # Check cache first
            cached_file = self.cache_dir / f"{symbol}_{timeframe.value}_{start_date.date()}_{end_date.date()}.parquet"

            if cached_file.exists():
                print(f"  Loading from cache: {cached_file}")
                df = pd.read_parquet(cached_file)
            else:
                # Download from API
                df = self._fetch_with_retry(symbol, start_date, end_date, timeframe)

                # Save to cache
                df.to_parquet(cached_file)
                print(f"  Saved to cache: {cached_file}")

            results[symbol] = df

        return results

    def _fetch_with_retry(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: TimeFrame,
        max_retries: int = 3
    ) -> pd.DataFrame:
        """
        Fetch data with automatic retry on failure
        """
        for attempt in range(max_retries):
            try:
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=timeframe,
                    start=start,
                    end=end
                )

                bars = self.data_client.get_stock_bars(request)
                df = bars.df

                print(f"  Fetched {len(df)} bars")
                return df

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"  Failed after {max_retries} attempts: {e}")
                    raise

        return pd.DataFrame()
```

### 4.2 CSV/Parquet Export

#### Parquet Format (Recommended)

Parquet provides 10-20x compression and faster read/write vs CSV.

```python
import pandas as pd

# Export to Parquet
df.to_parquet('data/AAPL_daily.parquet', compression='snappy')

# Read from Parquet
df = pd.read_parquet('data/AAPL_daily.parquet')

# Multi-symbol export
for symbol, df in data.items():
    df.to_parquet(f'data/{symbol}_daily.parquet')
```

#### CSV Format (Human-readable)

```python
# Export to CSV
df.to_csv('data/AAPL_daily.csv', index=True)

# Read from CSV with datetime index
df = pd.read_csv('data/AAPL_daily.csv', index_col=0, parse_dates=True)
```

### 4.3 Data Storage Best Practices

#### Directory Structure

```
data/
├── cache/                          # Raw API responses
│   ├── AAPL_1Day_2020-01-01_2024-10-22.parquet
│   └── MSFT_1Day_2020-01-01_2024-10-22.parquet
├── processed/                      # Cleaned data with features
│   ├── AAPL_features.parquet
│   └── MSFT_features.parquet
└── backtest/                       # Backtest-ready datasets
    └── momentum_strategy_data.parquet
```

#### Data Versioning

```python
from datetime import datetime

def save_with_version(df: pd.DataFrame, symbol: str, data_type: str):
    """
    Save data with timestamp version
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/{data_type}/{symbol}_{timestamp}.parquet"
    df.to_parquet(filename)
    print(f"Saved: {filename}")

    # Also save as 'latest'
    latest_filename = f"data/{data_type}/{symbol}_latest.parquet"
    df.to_parquet(latest_filename)
```

### 4.4 Error Handling and Retry Logic

```python
import time
from typing import Optional

def fetch_with_exponential_backoff(
    func,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0
) -> Optional[any]:
    """
    Execute function with exponential backoff retry
    """
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                raise

            # Check if rate limited
            if "rate limit" in str(e).lower():
                delay = min(delay * 2, max_delay)
                print(f"Rate limited, waiting {delay}s...")
            else:
                delay = initial_delay
                print(f"Error: {e}, retrying in {delay}s...")

            time.sleep(delay)

    return None

# Usage
df = fetch_with_exponential_backoff(
    lambda: data_client.get_stock_bars(request)
)
```

---

## 5. Integration with Trading System

### 5.1 Feeding Data to Backtesting Engine

```python
from src.backtesting.engine import BacktestEngine
from src.strategies.momentum import MomentumStrategy

# Download historical data
downloader = DataDownloader(data_client)
data = downloader.download_historical_data(
    symbols=["AAPL", "MSFT", "GOOGL"],
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2024, 10, 22),
    timeframe=TimeFrame.Day
)

# Initialize backtest engine
engine = BacktestEngine(
    initial_capital=100000,
    commission=0.001,  # 0.1% per trade
    slippage=0.0005    # 0.05% slippage
)

# Load data into engine
for symbol, df in data.items():
    engine.add_data(symbol, df)

# Run strategy
strategy = MomentumStrategy(lookback=20)
results = engine.run(strategy)

print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

### 5.2 Expected Data Formats

The backtesting engine expects DataFrames with this structure:

```python
# Required columns
required_columns = ['open', 'high', 'low', 'close', 'volume']

# Optional columns (calculated by preprocessor)
optional_columns = [
    'vwap',           # Volume-weighted average price
    'trade_count',    # Number of trades
    'returns',        # Daily returns
    'log_returns'     # Log returns
]

# Example DataFrame structure
"""
                           open    high     low   close    volume      vwap  trade_count
timestamp
2024-10-22 09:30:00  175.23  175.45  175.10  175.32  1250000  175.28        15234
2024-10-22 09:31:00  175.32  175.55  175.28  175.50  1100000  175.42        14567
"""
```

### 5.3 Cache Management

Implement intelligent caching to avoid redundant API calls:

```python
class CacheManager:
    """
    Manages data cache with TTL (time-to-live)
    """

    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.ttl = timedelta(hours=ttl_hours)

    def is_cache_valid(self, cache_file: Path) -> bool:
        """
        Check if cache file exists and is not expired
        """
        if not cache_file.exists():
            return False

        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        return file_age < self.ttl

    def get_or_fetch(
        self,
        cache_key: str,
        fetch_func,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Get data from cache or fetch if not available
        """
        cache_file = self.cache_dir / f"{cache_key}.parquet"

        if not force_refresh and self.is_cache_valid(cache_file):
            print(f"Loading from cache: {cache_key}")
            return pd.read_parquet(cache_file)

        print(f"Fetching fresh data: {cache_key}")
        df = fetch_func()

        # Save to cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file)

        return df
```

### 5.4 Update Strategies

#### Incremental Updates

Only fetch new data since last update:

```python
def update_data_incrementally(symbol: str, existing_df: pd.DataFrame) -> pd.DataFrame:
    """
    Update existing data with new bars
    """
    # Get last timestamp from existing data
    last_timestamp = existing_df.index[-1]

    # Fetch only new data
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=last_timestamp + timedelta(days=1),
        end=datetime.now()
    )

    new_bars = data_client.get_stock_bars(request)
    new_df = new_bars.df

    if not new_df.empty:
        # Concatenate and deduplicate
        updated_df = pd.concat([existing_df, new_df])
        updated_df = updated_df[~updated_df.index.duplicated(keep='last')]
        updated_df = updated_df.sort_index()

        print(f"Added {len(new_df)} new bars")
        return updated_df

    return existing_df
```

#### Scheduled Updates

```python
import schedule
import time

def scheduled_data_update():
    """
    Update data daily after market close (4:00 PM ET + buffer)
    """
    symbols = ["AAPL", "MSFT", "GOOGL"]

    for symbol in symbols:
        # Load existing data
        cache_file = f"data/cache/{symbol}_daily_latest.parquet"
        if Path(cache_file).exists():
            df = pd.read_parquet(cache_file)
            df = update_data_incrementally(symbol, df)
        else:
            # First download
            df = download_full_history(symbol)

        # Save updated data
        df.to_parquet(cache_file)
        print(f"Updated {symbol}: {len(df)} total bars")

# Schedule daily update at 5:00 PM ET
schedule.every().day.at("17:00").do(scheduled_data_update)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

---

## 6. Code Examples

### 6.1 Complete Python Example - Download & Backtest

```python
#!/usr/bin/env python3
"""
Complete workflow: Download data → Preprocess → Backtest
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Initialize client
load_dotenv()
data_client = StockHistoricalDataClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY")
)

# 1. Download data
print("Step 1: Downloading historical data...")
symbols = ["AAPL", "MSFT", "GOOGL"]
start_date = datetime.now() - timedelta(days=365*3)  # 3 years
end_date = datetime.now()

all_data = {}
for symbol in symbols:
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )

    bars = data_client.get_stock_bars(request)
    df = bars.df

    # Save to cache
    df.to_parquet(f"data/cache/{symbol}_daily.parquet")
    all_data[symbol] = df
    print(f"  {symbol}: {len(df)} bars downloaded")

# 2. Preprocess data
print("\nStep 2: Preprocessing data...")
for symbol, df in all_data.items():
    # Calculate returns
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

    # Add moving averages
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()

    # Remove NaN values
    df = df.dropna()

    all_data[symbol] = df
    print(f"  {symbol}: {len(df)} bars after preprocessing")

# 3. Run backtest
print("\nStep 3: Running backtest...")
from src.backtesting.engine import BacktestEngine
from src.strategies.momentum import MomentumStrategy

engine = BacktestEngine(initial_capital=100000)
for symbol, df in all_data.items():
    engine.add_data(symbol, df)

strategy = MomentumStrategy(fast_period=20, slow_period=50)
results = engine.run(strategy)

print(f"\nBacktest Results:")
print(f"  Total Return: {results['total_return']:.2%}")
print(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"  Max Drawdown: {results['max_drawdown']:.2%}")
print(f"  Win Rate: {results['win_rate']:.2%}")
```

### 6.2 Rust Example - High-Performance Data Fetcher

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Deserialize)]
pub struct Bar {
    pub t: String,      // Timestamp
    pub o: f64,         // Open
    pub h: f64,         // High
    pub l: f64,         // Low
    pub c: f64,         // Close
    pub v: u64,         // Volume
    pub vw: f64,        // VWAP
}

#[derive(Debug, Deserialize)]
pub struct BarsResponse {
    pub bars: HashMap<String, Vec<Bar>>,
}

pub struct AlpacaDataFetcher {
    client: Client,
    api_key: String,
    secret_key: String,
}

impl AlpacaDataFetcher {
    pub fn new(api_key: String, secret_key: String) -> Self {
        Self {
            client: Client::new(),
            api_key,
            secret_key,
        }
    }

    pub async fn fetch_bars(
        &self,
        symbol: &str,
        timeframe: &str,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
    ) -> Result<Vec<Bar>, Box<dyn std::error::Error>> {
        let url = format!(
            "https://data.alpaca.markets/v2/stocks/{}/bars",
            symbol
        );

        let response = self.client
            .get(&url)
            .header("APCA-API-KEY-ID", &self.api_key)
            .header("APCA-API-SECRET-KEY", &self.secret_key)
            .query(&[
                ("timeframe", timeframe),
                ("start", &start.to_rfc3339()),
                ("end", &end.to_rfc3339()),
            ])
            .send()
            .await?;

        let data: BarsResponse = response.json().await?;
        Ok(data.bars.get(symbol).cloned().unwrap_or_default())
    }

    pub async fn fetch_multiple_symbols(
        &self,
        symbols: &[&str],
        timeframe: &str,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
    ) -> Result<HashMap<String, Vec<Bar>>, Box<dyn std::error::Error>> {
        let mut results = HashMap::new();

        for symbol in symbols {
            let bars = self.fetch_bars(symbol, timeframe, start, end).await?;
            results.insert(symbol.to_string(), bars);
            println!("Fetched {} bars for {}", bars.len(), symbol);
        }

        Ok(results)
    }
}

// Usage example
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let fetcher = AlpacaDataFetcher::new(
        env::var("ALPACA_API_KEY")?,
        env::var("ALPACA_SECRET_KEY")?,
    );

    let start = Utc::now() - chrono::Duration::days(365);
    let end = Utc::now();

    let data = fetcher.fetch_multiple_symbols(
        &["AAPL", "MSFT", "GOOGL"],
        "1Day",
        start,
        end,
    ).await?;

    println!("Downloaded data for {} symbols", data.len());

    Ok(())
}
```

### 6.3 Error Handling Pattern

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AlpacaDataError(Exception):
    """Custom exception for Alpaca data operations"""
    pass

def safe_fetch_bars(
    client,
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: TimeFrame,
    max_retries: int = 3
) -> Optional[pd.DataFrame]:
    """
    Safely fetch bars with comprehensive error handling
    """
    for attempt in range(max_retries):
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start,
                end=end
            )

            bars = client.get_stock_bars(request)
            df = bars.df

            # Validate data
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            # Check for missing values
            if df.isnull().any().any():
                logger.warning(f"Missing values detected in {symbol} data")
                df = df.fillna(method='ffill')  # Forward fill

            logger.info(f"Successfully fetched {len(df)} bars for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed for {symbol}: {e}")

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                raise AlpacaDataError(f"Failed to fetch {symbol} after {max_retries} attempts") from e

    return None
```

---

## 7. Best Practices

### 7.1 Data Quality Checks

Always validate downloaded data:

```python
def validate_ohlcv_data(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Validate OHLCV data integrity

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    # Check required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        issues.append(f"Missing columns: {missing_cols}")

    # Check for negative values
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns and (df[col] < 0).any():
            issues.append(f"Negative values in {col}")

    # Check OHLC relationship: High >= Low, High >= Open, High >= Close
    if 'high' in df.columns and 'low' in df.columns:
        if (df['high'] < df['low']).any():
            issues.append("High < Low detected")
        if (df['high'] < df['open']).any():
            issues.append("High < Open detected")
        if (df['high'] < df['close']).any():
            issues.append("High < Close detected")

    # Check for duplicate timestamps
    if df.index.duplicated().any():
        issues.append("Duplicate timestamps detected")

    # Check for gaps in data
    expected_freq = pd.infer_freq(df.index)
    if expected_freq:
        date_range = pd.date_range(df.index[0], df.index[-1], freq=expected_freq)
        missing_dates = set(date_range) - set(df.index)
        if missing_dates:
            issues.append(f"{len(missing_dates)} missing timestamps")

    return len(issues) == 0, issues
```

### 7.2 Rate Limiting

Respect API rate limits to avoid throttling:

```python
import time
from functools import wraps

class RateLimiter:
    """
    Simple rate limiter for API calls
    """

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Remove old calls outside the period
            self.calls = [call for call in self.calls if call > now - self.period]

            # Check if we've hit the limit
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    print(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    self.calls = []

            # Make the call
            self.calls.append(time.time())
            return func(*args, **kwargs)

        return wrapper

# Usage
@RateLimiter(max_calls=200, period=60.0)  # 200 calls per minute
def fetch_data(symbol):
    return data_client.get_stock_bars(request)
```

### 7.3 Data Normalization

Ensure consistent data format across all symbols:

```python
def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize OHLCV data to standard format
    """
    # Ensure lowercase column names
    df.columns = df.columns.str.lower()

    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Sort by timestamp
    df = df.sort_index()

    # Remove duplicates (keep last)
    df = df[~df.index.duplicated(keep='last')]

    # Ensure numeric types
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop any remaining NaN values
    df = df.dropna()

    return df
```

### 7.4 Memory Management

Efficient memory usage for large datasets:

```python
def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce DataFrame memory footprint
    """
    # Convert float64 to float32 (50% memory reduction)
    float_cols = df.select_dtypes(include=['float64']).columns
    df[float_cols] = df[float_cols].astype('float32')

    # Convert int64 to int32 where safe
    int_cols = df.select_dtypes(include=['int64']).columns
    for col in int_cols:
        if df[col].max() < 2**31 and df[col].min() > -2**31:
            df[col] = df[col].astype('int32')

    return df

# Usage
df = optimize_dataframe_memory(df)
print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
```

---

## 8. Troubleshooting

### 8.1 Common Issues

#### Issue: "403 Forbidden" Error

**Cause**: Invalid API credentials or trading account not approved

**Solution**:
```python
# Verify credentials are correct
print(f"API Key: {os.getenv('ALPACA_API_KEY')[:8]}...")
print(f"Secret Key: {os.getenv('ALPACA_SECRET_KEY')[:8]}...")

# Check account status
account = trading_client.get_account()
print(f"Account Status: {account.status}")
print(f"Trading Blocked: {account.trading_blocked}")
```

#### Issue: "429 Too Many Requests" Error

**Cause**: Exceeded rate limit (200 requests/minute for live trading)

**Solution**:
```python
# Add rate limiting
import time

def rate_limited_fetch(symbols, delay=0.5):
    """Fetch with delay between requests"""
    results = {}
    for symbol in symbols:
        results[symbol] = fetch_data(symbol)
        time.sleep(delay)  # 0.5s delay = max 120 req/min
    return results
```

#### Issue: Empty DataFrame Returned

**Cause**: No data available for requested period (e.g., weekends, holidays)

**Solution**:
```python
# Check if data is empty and adjust date range
def smart_fetch(symbol, days=365):
    """Fetch with automatic date adjustment"""
    end = datetime.now()
    start = end - timedelta(days=days)

    df = fetch_data(symbol, start, end)

    if df.empty:
        # Try extending date range
        print(f"No data for {symbol}, trying longer period...")
        start = end - timedelta(days=days * 2)
        df = fetch_data(symbol, start, end)

    return df
```

#### Issue: WebSocket Connection Drops

**Cause**: Network issues or idle timeout

**Solution**:
```python
async def robust_websocket_connection(api_key, secret_key):
    """WebSocket with automatic reconnection"""
    while True:
        try:
            async with websockets.connect("wss://stream.data.alpaca.markets/v2/sip") as ws:
                # Authenticate
                await ws.send(json.dumps({
                    "action": "auth",
                    "key": api_key,
                    "secret": secret_key
                }))

                # Subscribe
                await ws.send(json.dumps({
                    "action": "subscribe",
                    "trades": ["AAPL", "MSFT"]
                }))

                # Receive messages
                while True:
                    msg = await ws.recv()
                    process_message(msg)

        except Exception as e:
            print(f"WebSocket error: {e}, reconnecting in 5s...")
            await asyncio.sleep(5)
```

### 8.2 Data Quality Issues

#### Issue: Missing Timestamps

```python
def fill_missing_timestamps(df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
    """
    Fill missing timestamps with forward-filled values
    """
    # Create complete date range
    full_range = pd.date_range(df.index[0], df.index[-1], freq=freq)

    # Reindex and forward fill
    df = df.reindex(full_range, method='ffill')

    return df
```

#### Issue: Outliers in Price Data

```python
def detect_and_remove_outliers(df: pd.DataFrame, column: str = 'close', threshold: float = 3.0) -> pd.DataFrame:
    """
    Detect and remove outliers using z-score
    """
    z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
    outliers = z_scores > threshold

    if outliers.any():
        print(f"Removed {outliers.sum()} outliers from {column}")
        df = df[~outliers]

    return df
```

### 8.3 Debugging Tips

Enable detailed logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_download.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Use in code
logger.debug(f"Requesting data for {symbol} from {start} to {end}")
logger.info(f"Received {len(df)} bars")
logger.warning(f"Missing data for {missing_dates}")
logger.error(f"Failed to fetch {symbol}: {error}")
```

---

## Summary

This guide covers the complete workflow for accessing Alpaca market data:

1. **Authentication**: Set up API credentials securely
2. **Real-time Data**: WebSocket streaming for live trading
3. **Historical Data**: Efficient bulk downloads with pagination
4. **Data Management**: Caching, versioning, and storage strategies
5. **Integration**: Feed data into backtesting and trading systems
6. **Best Practices**: Quality checks, error handling, optimization

### Next Steps

- **Explore**: [ALPACA_API.md](/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/api/ALPACA_API.md) for trading operations
- **Build**: Implement your first data pipeline
- **Optimize**: Profile and optimize for production use
- **Deploy**: Set up automated data updates

### Additional Resources

- [Alpaca Data API Docs](https://alpaca.markets/docs/api-documentation/api-v2/market-data/)
- [alpaca-py SDK](https://github.com/alpacahq/alpaca-py)
- [System Architecture](/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/architecture/python-rust-separation.md)

---

**Last Updated**: 2024-10-22 | **Version**: 1.0 | **Maintainer**: Research Agent
