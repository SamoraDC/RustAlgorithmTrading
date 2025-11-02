#!/usr/bin/env python3
"""
Simple Alpaca API connectivity test
Tests basic authentication and data retrieval
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_alpaca_api():
    """Test Alpaca API connectivity and data retrieval"""

    # Check credentials
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    print("=" * 70)
    print("ALPACA API CONNECTIVITY TEST")
    print("=" * 70)

    if not api_key or not api_secret:
        print("❌ ERROR: API credentials not found in .env file")
        print("   Please set ALPACA_API_KEY and ALPACA_SECRET_KEY")
        return False

    print(f"✓ API Key found: {api_key[:8]}...{api_key[-4:]}")
    print(f"✓ API Secret found: {api_secret[:8]}...{api_secret[-4:]}")
    print()

    try:
        import pandas as pd
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        # Initialize client
        print("Initializing Alpaca client...")
        client = StockHistoricalDataClient(api_key, api_secret)
        print("✓ Client initialized successfully")
        print()

        # Test with recent date range
        end_date = datetime.now() - timedelta(days=2)  # 2 days ago for sure market close
        start_date = end_date - timedelta(days=7)  # 1 week range

        print(f"Test Parameters:")
        print(f"  Symbol: AAPL")
        print(f"  Start Date: {start_date.date()}")
        print(f"  End Date: {end_date.date()}")
        print(f"  Timeframe: 1 Day")
        print()

        # Create request
        request = StockBarsRequest(
            symbol_or_symbols=["AAPL"],
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )

        print("Fetching market data from Alpaca API...")
        bars = client.get_stock_bars(request)

        if not bars:
            print("❌ ERROR: No response from API")
            print("   This could indicate:")
            print("   1. Invalid API credentials")
            print("   2. API endpoint issue")
            print("   3. Network connectivity problem")
            return False

        print("✓ Received response from API")
        print(f"  Response type: {type(bars)}")
        print()

        # Get data - BarSet object has a df property directly
        df = bars.df

        # Check if we got any data
        if df is None or df.empty:
            print("❌ ERROR: Response is empty or None")
            print("   This could indicate:")
            print("   1. No trading data for date range (weekends, holidays)")
            print("   2. Date range in the future")
            print("   3. Symbol not available for paper trading")
            return False

        # Check if AAPL is in the dataframe
        if isinstance(df.index, pd.MultiIndex):
            symbols_in_df = df.index.get_level_values('symbol').unique().tolist()
        else:
            symbols_in_df = df['symbol'].unique().tolist() if 'symbol' in df.columns else []

        if 'AAPL' not in str(symbols_in_df):
            print(f"❌ ERROR: AAPL not found in dataframe")
            print(f"   Symbols found: {symbols_in_df}")
            return False
        print(f"✓ Successfully retrieved data for AAPL")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        print()

        if len(df) > 0:
            print("Sample data (first 3 rows):")
            print(df.head(3))
            print()
            print("=" * 70)
            print("✅ SUCCESS: Alpaca API is working correctly!")
            print("=" * 70)
            return True
        else:
            print("⚠️  WARNING: API responded but returned 0 rows")
            print("   Try adjusting the date range")
            return False

    except ImportError as e:
        print(f"❌ ERROR: Missing dependency: {e}")
        print("   Run: uv sync")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_alpaca_api()
    sys.exit(0 if success else 1)
