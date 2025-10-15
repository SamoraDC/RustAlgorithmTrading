"""Test Alpaca API connection and credentials."""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# Load environment variables
load_dotenv("../.env")

# Get credentials
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

print("=" * 60)
print("ALPACA API CONNECTION TEST")
print("=" * 60)
print(f"\nBase URL: {BASE_URL}")
print(f"API Key: {API_KEY[:8]}...")
print(f"Secret Key: {'*' * 20}")

# Test Trading Client
print("\n" + "-" * 60)
print("Testing Trading Client...")
print("-" * 60)

try:
    trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
    account = trading_client.get_account()

    print("✅ Trading Client Connected Successfully!")
    print(f"\nAccount Details:")
    print(f"  Status: {account.status}")
    print(f"  Cash: ${float(account.cash):,.2f}")
    print(f"  Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"  Buying Power: ${float(account.buying_power):,.2f}")
    print(f"  Day Trading Buying Power: ${float(account.daytrading_buying_power):,.2f}")

except Exception as e:
    print(f"❌ Trading Client Error: {e}")

# Test Data Client
print("\n" + "-" * 60)
print("Testing Historical Data Client...")
print("-" * 60)

try:
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

    # Fetch recent data for AAPL
    request_params = StockBarsRequest(
        symbol_or_symbols=["AAPL"],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=10),
        end=datetime.now()
    )

    bars = data_client.get_stock_bars(request_params)
    aapl_bars = bars.data.get("AAPL", [])

    print("✅ Data Client Connected Successfully!")
    print(f"\nRetrieved {len(aapl_bars)} days of AAPL data")

    if aapl_bars:
        latest = aapl_bars[-1]
        print(f"\nLatest AAPL Bar:")
        print(f"  Date: {latest.timestamp}")
        print(f"  Open: ${latest.open:.2f}")
        print(f"  High: ${latest.high:.2f}")
        print(f"  Low: ${latest.low:.2f}")
        print(f"  Close: ${latest.close:.2f}")
        print(f"  Volume: {latest.volume:,}")

except Exception as e:
    print(f"❌ Data Client Error: {e}")

print("\n" + "=" * 60)
print("CONNECTION TEST COMPLETE")
print("=" * 60)
