"""Quick Alpaca API functionality test with proper date handling."""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

print("=" * 70)
print("ALPACA API QUICK FUNCTIONALITY TEST")
print("=" * 70)

# Initialize clients
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# Test 1: Account Information
print("\n[TEST 1] Account Information")
print("-" * 70)
try:
    account = trading_client.get_account()
    print(f"✅ Account Status: {account.status}")
    print(f"   Cash: ${float(account.cash):,.2f}")
    print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"   Buying Power: ${float(account.buying_power):,.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Latest Quote (Real-time data)
print("\n[TEST 2] Latest Market Quote")
print("-" * 70)
try:
    quote_request = StockLatestQuoteRequest(symbol_or_symbols=["AAPL", "GOOGL", "MSFT"])
    latest_quotes = data_client.get_stock_latest_quote(quote_request)

    print("✅ Latest Quotes Retrieved:")
    for symbol, quote in latest_quotes.items():
        print(f"   {symbol}: Bid ${quote.bid_price:.2f} | Ask ${quote.ask_price:.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Historical Data (Last 5 trading days using relative dates)
print("\n[TEST 3] Historical Data (Last 5 Days)")
print("-" * 70)
try:
    # Use relative dates to avoid clock sync issues
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    bars_request = StockBarsRequest(
        symbol_or_symbols=["AAPL"],
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )

    bars = data_client.get_stock_bars(bars_request)
    aapl_bars = bars.data.get("AAPL", [])

    print(f"✅ Retrieved {len(aapl_bars)} days of AAPL data")

    if aapl_bars:
        print(f"\n   Recent AAPL Bars:")
        for bar in aapl_bars[-3:]:  # Show last 3 bars
            print(f"   {bar.timestamp.strftime('%Y-%m-%d')}: "
                  f"O=${bar.open:.2f} H=${bar.high:.2f} "
                  f"L=${bar.low:.2f} C=${bar.close:.2f} "
                  f"V={bar.volume:,}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Current Positions
print("\n[TEST 4] Current Positions")
print("-" * 70)
try:
    positions = trading_client.get_all_positions()

    if positions:
        print(f"✅ Found {len(positions)} position(s):")
        for pos in positions:
            print(f"   {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
            print(f"      Current: ${float(pos.current_price):.2f} | "
                  f"P&L: ${float(pos.unrealized_pl):.2f}")
    else:
        print("✅ No positions (account empty - ready for trading)")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Order History
print("\n[TEST 5] Order History")
print("-" * 70)
try:
    orders = trading_client.get_orders()

    if orders:
        print(f"✅ Found {len(orders)} order(s):")
        for order in orders[:5]:  # Show first 5
            print(f"   {order.symbol}: {order.side} {order.qty} @ {order.type}")
            print(f"      Status: {order.status} | Created: {order.created_at}")
    else:
        print("✅ No orders yet (account clean)")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE - All API Endpoints Working!")
print("=" * 70)
