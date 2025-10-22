#!/usr/bin/env python3
"""
Quick diagnostic to test SimpleMomentumStrategy signal generation
"""
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategies.simple_momentum import SimpleMomentumStrategy

print("=" * 70)
print("SIMPLE MOMENTUM STRATEGY - DIAGNOSTIC TEST")
print("=" * 70)

# Load data
print("\n[1/3] Loading historical data...")
symbols = ['AAPL', 'MSFT', 'GOOGL']
data = {}

for symbol in symbols:
    df = pd.read_parquet(f'data/historical/{symbol}.parquet')
    print(f"  ✓ Loaded {symbol}: {len(df)} bars")
    print(f"    Date range: {df.index[0]} to {df.index[-1]}")
    print(f"    Columns: {list(df.columns)}")
    data[symbol] = df

# Initialize strategy
print("\n[2/3] Initializing SimpleMomentumStrategy...")
strategy = SimpleMomentumStrategy(
    symbols=symbols,
    rsi_period=14,
    rsi_oversold=30,
    rsi_overbought=70,
    position_size=0.10
)

print(f"  ✓ Strategy initialized")
print(f"    RSI Oversold: 30")
print(f"    RSI Overbought: 70")
print(f"    Position Size: 10%")

# Generate signals
print("\n[3/3] Generating signals for each symbol...")
total_signals = 0

for symbol in symbols:
    df = data[symbol]
    print(f"\n{symbol}:")
    print(f"  Data shape: {df.shape}")
    print(f"  Index type: {type(df.index)}")

    try:
        signals = strategy.generate_signals_for_symbol(symbol, df)
        print(f"  Signals generated: {len(signals)}")

        if signals:
            for i, signal in enumerate(signals[:5], 1):  # Show first 5
                print(f"    {i}. {signal.signal_type.value} @ ${signal.price:.2f} "
                      f"(confidence: {signal.confidence:.2f})")
            if len(signals) > 5:
                print(f"    ... and {len(signals) - 5} more signals")
            total_signals += len(signals)
        else:
            print(f"  ⚠️  No signals generated")

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print(f"TOTAL SIGNALS: {total_signals}")
print("=" * 70)

if total_signals == 0:
    print("\n⚠️  ZERO SIGNALS - Testing with sample data...")

    # Test with first symbol's data in detail
    test_symbol = 'AAPL'
    test_df = data[test_symbol].copy()

    print(f"\nDetailed analysis for {test_symbol}:")
    print(f"  Shape: {test_df.shape}")
    print(f"  Columns: {list(test_df.columns)}")
    print(f"\n  First 3 rows:")
    print(test_df.head(3))
    print(f"\n  Last 3 rows:")
    print(test_df.tail(3))

    # Try calling the parent generate_signals directly
    print(f"\n  Testing parent generate_signals method...")
    test_df.attrs['symbol'] = test_symbol
    try:
        parent_signals = strategy.generate_signals(test_df)
        print(f"  Parent method signals: {len(parent_signals)}")
    except Exception as e:
        print(f"  Parent method ERROR: {e}")
        import traceback
        traceback.print_exc()
