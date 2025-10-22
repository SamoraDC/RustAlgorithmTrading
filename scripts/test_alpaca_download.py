#!/usr/bin/env python3
"""
Test script for Alpaca data downloader with comprehensive diagnostics
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def test_api_connection():
    """Test basic API connection"""
    print("=" * 80)
    print("TEST 1: API Connection")
    print("=" * 80)

    from alpaca.data.historical import StockHistoricalDataClient

    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    print(f"API Key: {api_key[:8]}..." if api_key else "API Key: NOT FOUND")
    print(f"API Secret: {'*' * 8}..." if api_secret else "API Secret: NOT FOUND")

    if not api_key or not api_secret:
        print("ERROR: API credentials not found")
        return False

    try:
        client = StockHistoricalDataClient(api_key, api_secret)
        print("SUCCESS: Client initialized")
        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize client: {e}")
        return False


def test_data_fetch_with_different_feeds():
    """Test data fetch with different feed parameters"""
    print("\n" + "=" * 80)
    print("TEST 2: Data Fetch with Different Feeds")
    print("=" * 80)

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import Adjustment

    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')
    client = StockHistoricalDataClient(api_key, api_secret)

    # Test with recent dates (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"Date range: {start_date.date()} to {end_date.date()}")

    feeds_to_test = ['iex', 'sip']
    symbol = 'AAPL'

    for feed in feeds_to_test:
        print(f"\nTesting feed: {feed}")
        print("-" * 40)

        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
                feed=feed,
                adjustment=Adjustment.ALL
            )

            bars = client.get_stock_bars(request)

            if bars and symbol in bars:
                df = bars.df
                print(f"SUCCESS: Got {len(df)} rows")
                print(f"Columns: {list(df.columns)}")
                print(f"First row:\n{df.head(1)}")
                return True
            else:
                print(f"WARNING: No data returned for feed={feed}")

        except Exception as e:
            print(f"ERROR with feed={feed}: {e}")

    return False


def test_date_ranges():
    """Test different date ranges"""
    print("\n" + "=" * 80)
    print("TEST 3: Different Date Ranges")
    print("=" * 80)

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import Adjustment

    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')
    client = StockHistoricalDataClient(api_key, api_secret)

    test_ranges = [
        ("Last 7 days", timedelta(days=7)),
        ("Last 30 days", timedelta(days=30)),
        ("Last 90 days", timedelta(days=90)),
    ]

    symbol = 'AAPL'

    for name, delta in test_ranges:
        print(f"\nTesting: {name}")
        print("-" * 40)

        end_date = datetime.now()
        start_date = end_date - delta

        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
                feed='iex',
                adjustment=Adjustment.ALL
            )

            bars = client.get_stock_bars(request)

            if bars and symbol in bars:
                df = bars.df
                print(f"SUCCESS: Got {len(df)} rows for {name}")
            else:
                print(f"WARNING: No data for {name}")

        except Exception as e:
            print(f"ERROR: {e}")


def test_full_download():
    """Test the full download script"""
    print("\n" + "=" * 80)
    print("TEST 4: Full Download Script")
    print("=" * 80)

    from download_historical_data import DownloadConfig, AlpacaDataDownloader

    # Use recent dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    config = DownloadConfig(
        symbols=['AAPL'],
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        timeframe='1Day',
        output_dir='data/test',
        save_csv=True,
        save_parquet=True,
        feed='iex',
        adjustment='all'
    )

    print(f"Config: {config}")

    try:
        downloader = AlpacaDataDownloader(config)
        success = downloader.download_symbol('AAPL')

        if success:
            print("SUCCESS: Download completed")
            return True
        else:
            print("ERROR: Download failed")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("ALPACA DATA DOWNLOADER DIAGNOSTIC TESTS")
    print("=" * 80)

    results = []

    # Test 1: Connection
    results.append(("API Connection", test_api_connection()))

    # Test 2: Different feeds
    results.append(("Data Fetch (Feeds)", test_data_fetch_with_different_feeds()))

    # Test 3: Date ranges
    test_date_ranges()  # Informational only

    # Test 4: Full download
    results.append(("Full Download", test_full_download()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\nALL TESTS PASSED!")
        print("\nYou can now run the downloader with:")
        print("python scripts/download_historical_data.py --symbols AAPL MSFT GOOGL \\")
        print("  --start 2024-01-01 --end 2024-12-31 --feed iex --debug")
    else:
        print("\nSOME TESTS FAILED - Check errors above")
        print("\nCommon fixes:")
        print("1. Verify API credentials in .env file")
        print("2. Try different feed parameter (--feed sip)")
        print("3. Use recent dates (last 5 years)")
        print("4. Check paper trading account data access")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
