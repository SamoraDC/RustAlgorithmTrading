# Alpaca API Integration Guide

## Overview

Alpaca Markets provides a developer-first API for algorithmic trading with commission-free trading, extensive historical data, and robust paper trading capabilities.

## Key Capabilities (2025)

### Asset Classes Supported
- **US Equities**: All major exchanges (NYSE, NASDAQ, AMEX)
- **Cryptocurrencies**: 24/7 trading for major cryptocurrencies
- **Options**: Up to Level 3 options trading
- Real-time and historical data for all asset classes

### Account Types

#### 1. Live Trading Account
- Real money trading
- Commission-free for self-directed accounts
- Margin accounts available (up to 4× intraday, 2× overnight)
- Short selling capability
- Separate API keys for security

#### 2. Paper Trading Account
- **Free** for all users
- Simulates market in real-time
- Unlimited testing capability
- Options trading enabled by default
- Same API specification as live trading
- Different API keys (prevents accidental live trades)

## Trading Features

### Margin Trading
- **Intraday Buying Power**: Up to 4×
- **Overnight Buying Power**: Up to 2×
- Pattern Day Trader (PDT) rules apply
- Real-time margin calculations

### Order Types Supported

**Standard Orders**:
- Market orders
- Limit orders
- Stop orders
- Stop-limit orders

**Advanced Orders**:
- Bracket orders (take-profit + stop-loss)
- One-Cancels-Other (OCO)
- One-Triggers-Other (OTO)
- Trailing stop orders
- Time-in-force options (Day, GTC, IOC, FOK)

### Short Selling
- Locate shares before shorting
- Real-time availability checks
- Automatic borrow fee calculation

## Market Data API

### Performance Specifications
- **API Rate Limit**: Up to 10,000 calls/minute
- **Historical Data**: 7+ years available
- **Latency**: Low-latency real-time feeds
- **WebSocket Support**: Real-time streaming data

### Data Types Available

#### 1. Historical Bar Data
- Multiple timeframes (1min, 5min, 15min, 1hour, 1day)
- OHLCV (Open, High, Low, Close, Volume)
- Adjusted for splits and dividends
- Available via RESTful API

#### 2. Quote Data
- Bid/ask prices and sizes
- Real-time and historical
- Market depth information

#### 3. Trade Data
- Individual trade ticks
- Price and volume
- Exchange information
- Timestamps with microsecond precision

#### 4. Options Data
- Real-time option chains
- Greeks calculations
- Historical options data
- Implied volatility

### Data Access Patterns

```python
# Pseudo-code example
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# Initialize client
client = StockHistoricalDataClient(api_key, secret_key)

# Request historical data
request_params = StockBarsRequest(
    symbol_or_symbols=['AAPL', 'MSFT'],
    timeframe=TimeFrame.Day,
    start=datetime(2020, 1, 1),
    end=datetime(2025, 1, 1)
)

# Get data
bars = client.get_stock_bars(request_params)
```

## API Architecture

### RESTful API
- HTTPS protocol
- JSON request/response format
- OAuth 2.0 authentication
- Rate limiting per endpoint

### WebSocket Streaming
- Real-time market data
- Order updates
- Trade confirmations
- Account updates

### Endpoints

**Trading Endpoints**:
- `/v2/orders` - Order management
- `/v2/positions` - Position tracking
- `/v2/account` - Account information
- `/v2/assets` - Asset information

**Market Data Endpoints**:
- `/v2/stocks/bars` - Historical bars
- `/v2/stocks/trades` - Trade data
- `/v2/stocks/quotes` - Quote data
- `/v2/options/bars` - Options data

## Python SDK: alpaca-py

### Installation

```bash
# Using uv (recommended)
uv pip install alpaca-py

# Additional dependencies for full functionality
uv pip install pandas numpy python-dotenv
```

### Basic Usage Pattern

```python
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Initialize client
trading_client = TradingClient(
    api_key='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY',
    paper=True  # Use paper trading
)

# Place market order
order_data = MarketOrderRequest(
    symbol='AAPL',
    qty=10,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY
)

order = trading_client.submit_order(order_data)
```

## Paper Trading Best Practices

### 1. Environment Separation
- Use separate API keys for paper and live
- Set environment variables for configuration
- Never hardcode credentials

```python
# .env file approach
ALPACA_API_KEY_PAPER=your_paper_key
ALPACA_SECRET_KEY_PAPER=your_paper_secret
ALPACA_API_KEY_LIVE=your_live_key
ALPACA_SECRET_KEY_LIVE=your_live_secret
```

### 2. Paper Trading Limitations
- Simulated fills (not actual market depth)
- May not reflect actual slippage
- Order fills might be more optimistic
- Use for logic testing, not precise execution modeling

### 3. Transition to Live Trading
- Run paper trading for minimum 30 days
- Verify all edge cases
- Test error handling
- Monitor fill quality differences
- Start with small position sizes

## Backtesting with Alpaca Data

### Advantages
- **7+ years** of historical data
- High-quality, survivorship-bias considerations
- Same data source as live trading
- Multiple asset classes

### Integration with Backtesting Libraries

```python
# Example: Using Alpaca data with backtesting.py
from alpaca.data.historical import StockHistoricalDataClient
import pandas as pd
from backtesting import Backtest, Strategy

# Fetch Alpaca data
def get_alpaca_data(symbol, start, end):
    client = StockHistoricalDataClient(api_key, secret_key)
    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=start,
        end=end
    )
    bars = client.get_stock_bars(request)

    # Convert to pandas DataFrame for backtesting.py
    df = bars.df
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    return df

# Use with backtesting framework
data = get_alpaca_data('AAPL', datetime(2020,1,1), datetime(2025,1,1))
bt = Backtest(data, YourStrategy, cash=10000)
stats = bt.run()
```

## Rate Limiting and Best Practices

### Rate Limits
- **Trading API**: 200 requests/minute
- **Market Data API**: 10,000 requests/minute
- Implement exponential backoff on errors
- Cache frequently accessed data

### Optimization Strategies

1. **Batch Requests**: Request multiple symbols at once
2. **WebSocket for Real-Time**: Reduce polling
3. **Local Caching**: Store historical data locally
4. **Efficient Timeframes**: Request appropriate granularity

## Cost Structure

### Free Tier
- Paper trading (unlimited)
- Historical market data API access
- Real-time data with account
- No commission on trades (live account)

### Paid Tiers
- **Alpaca Market Data**: Enhanced real-time data
- **Premium Data Feeds**: Professional-grade data
- No monthly account fees for basic accounts

## Integration Architecture for Algorithmic Trading

### Recommended Structure

```
trading_system/
├── config/
│   ├── alpaca_config.py      # API credentials, endpoints
│   └── trading_params.py     # Strategy parameters
├── data/
│   ├── data_fetcher.py        # Alpaca data retrieval
│   ├── data_processor.py      # Data cleaning, transformation
│   └── cache_manager.py       # Local data caching
├── strategies/
│   ├── base_strategy.py       # Abstract base class
│   └── specific_strategies/   # Individual strategy implementations
├── execution/
│   ├── order_manager.py       # Order placement and management
│   ├── position_manager.py    # Position tracking
│   └── risk_manager.py        # Risk controls
├── backtesting/
│   ├── backtest_engine.py     # Backtesting framework
│   └── performance_metrics.py # Performance analysis
└── monitoring/
    ├── logger.py              # Logging system
    └── alerting.py            # Error alerts
```

## Error Handling

### Common Errors

1. **Insufficient Buying Power**: Check account before placing orders
2. **Market Closed**: Verify market hours
3. **Invalid Symbol**: Validate symbols against `/v2/assets`
4. **Rate Limit Exceeded**: Implement retry with backoff
5. **Order Rejected**: Handle various rejection reasons

### Robust Error Handling Pattern

```python
from alpaca.common.exceptions import APIError
import time

def place_order_with_retry(order_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            order = trading_client.submit_order(order_data)
            return order
        except APIError as e:
            if e.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            elif e.status_code >= 500:  # Server error
                time.sleep(1)
            else:
                # Client error, don't retry
                raise
    raise Exception(f"Failed after {max_retries} retries")
```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for credentials
3. **Implement IP whitelisting** when possible
4. **Rotate API keys** regularly
5. **Monitor API usage** for anomalies
6. **Use paper trading** for development
7. **Implement two-factor authentication** on Alpaca account

## Advanced Features

### 1. Real-Time Streaming

```python
from alpaca.data.live import StockDataStream

# WebSocket streaming
stream = StockDataStream(api_key, secret_key)

@stream.on_bar('AAPL')
async def on_bar(bar):
    print(f"Received bar: {bar}")

stream.run()
```

### 2. Options Trading

```python
from alpaca.trading.requests import LimitOrderRequest

# Options order example
order_data = LimitOrderRequest(
    symbol='AAPL250117C00150000',  # Options symbol format
    qty=1,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
    limit_price=5.50
)
```

### 3. Portfolio Management

```python
# Get all positions
positions = trading_client.get_all_positions()

# Get account info
account = trading_client.get_account()

print(f"Buying Power: ${account.buying_power}")
print(f"Portfolio Value: ${account.portfolio_value}")
```

## Testing Strategy

### 1. Unit Tests
- Test individual components
- Mock Alpaca API responses
- Verify order logic

### 2. Integration Tests
- Test with paper trading account
- Verify end-to-end workflows
- Monitor actual API interactions

### 3. Load Tests
- Test rate limit handling
- Verify system under high load
- Stress test WebSocket connections

## Resources

### Official Documentation
- Main Docs: https://docs.alpaca.markets/
- API Reference: https://docs.alpaca.markets/reference/
- Python SDK: https://github.com/alpacahq/alpaca-trade-api-python

### Community Resources
- Alpaca Slack Community
- GitHub Examples Repository
- Medium Articles and Tutorials

## Summary Checklist

- [ ] Register for Alpaca account (paper and/or live)
- [ ] Generate API keys (separate for paper/live)
- [ ] Install alpaca-py SDK
- [ ] Set up environment variables for credentials
- [ ] Test connection with paper trading
- [ ] Fetch historical data for backtesting
- [ ] Implement error handling and retry logic
- [ ] Set up logging and monitoring
- [ ] Test order placement in paper environment
- [ ] Validate strategy with paper trading (30+ days)
- [ ] Review performance metrics and slippage
- [ ] Gradually transition to live trading (small sizes)
