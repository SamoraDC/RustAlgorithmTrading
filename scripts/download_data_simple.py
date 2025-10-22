#!/usr/bin/env python3
"""
Simple Market Data Downloader - Uses the same working approach as test_alpaca_quick.py
"""
import os
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Load environment variables
load_dotenv()

# Get credentials
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Initialize client
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# Configuration
SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
DAYS_BACK = 365
OUTPUT_DIR = Path("data/historical")

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("SIMPLE DATA DOWNLOADER")
print("=" * 70)
print(f"Symbols: {', '.join(SYMBOLS)}")
print(f"Days back: {DAYS_BACK}")
print(f"Output: {OUTPUT_DIR}")
print()

# Calculate date range (same approach as test_alpaca_quick.py)
end_date = datetime.now()
start_date = end_date - timedelta(days=DAYS_BACK)

print(f"Date range: {start_date.date()} to {end_date.date()}")
print()

# Download data for each symbol
for symbol in SYMBOLS:
    print(f"Downloading {symbol}...", end=" ", flush=True)

    try:
        # Create request (exactly like test_alpaca_quick.py)
        bars_request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )

        # Fetch data
        bars = data_client.get_stock_bars(bars_request)

        # Extract data using .data.get() (same as working test)
        symbol_bars = bars.data.get(symbol, [])

        if not symbol_bars:
            print("❌ No data returned")
            continue

        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': bar.timestamp,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'trade_count': getattr(bar, 'trade_count', 0),
            'vwap': getattr(bar, 'vwap', (bar.high + bar.low + bar.close) / 3)
        } for bar in symbol_bars])

        # Sort by timestamp
        df = df.sort_values('timestamp')

        # Save to CSV
        csv_path = OUTPUT_DIR / f"{symbol}.csv"
        df.to_csv(csv_path, index=False)

        # Save to Parquet
        parquet_path = OUTPUT_DIR / f"{symbol}.parquet"
        df.to_parquet(parquet_path, index=False)

        print(f"✅ {len(df)} bars ({df['timestamp'].min().date()} to {df['timestamp'].max().date()})")
        print(f"   Saved to {csv_path} and {parquet_path}")

    except Exception as e:
        print(f"❌ Error: {e}")

print()
print("=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)

# Verify files were created
print("\nFiles created:")
for symbol in SYMBOLS:
    csv_path = OUTPUT_DIR / f"{symbol}.csv"
    parquet_path = OUTPUT_DIR / f"{symbol}.parquet"

    if csv_path.exists():
        size_kb = csv_path.stat().st_size / 1024
        print(f"  ✅ {symbol}.csv ({size_kb:.1f} KB)")
    else:
        print(f"  ❌ {symbol}.csv (not found)")

    if parquet_path.exists():
        size_kb = parquet_path.stat().st_size / 1024
        print(f"  ✅ {symbol}.parquet ({size_kb:.1f} KB)")
    else:
        print(f"  ❌ {symbol}.parquet (not found)")
