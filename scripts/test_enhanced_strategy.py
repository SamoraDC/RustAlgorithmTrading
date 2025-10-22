#!/usr/bin/env python3
"""
Quick diagnostic to test EnhancedMomentumStrategy signal generation
"""
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    RiskParameters,
    IndicatorThresholds,
    SignalQuality
)

print("=" * 70)
print("ENHANCED MOMENTUM STRATEGY - DIAGNOSTIC TEST")
print("=" * 70)

# Load data
print("\n[1/4] Loading historical data...")
symbols = ['AAPL', 'MSFT', 'GOOGL']
data = {}

for symbol in symbols:
    df = pd.read_parquet(f'data/historical/{symbol}.parquet')
    print(f"  ✓ Loaded {symbol}: {len(df)} bars")
    data[symbol] = df

# Initialize strategy
print("\n[2/4] Initializing Enhanced Momentum Strategy...")
risk_params = RiskParameters(
    max_position_size=0.15,
    risk_per_trade=0.02,
    max_portfolio_exposure=0.60
)

indicator_thresholds = IndicatorThresholds(
    rsi_period=14,
    rsi_oversold=30,
    rsi_overbought=70
)

strategy = EnhancedMomentumStrategy(
    symbols=symbols,
    risk_params=risk_params,
    indicator_thresholds=indicator_thresholds,
    min_signal_quality=SignalQuality.MODERATE,
    enable_volume_filter=False,
    enable_trend_filter=False
)

print(f"  ✓ Strategy initialized")
print(f"    Min signal quality: {SignalQuality.MODERATE}")
print(f"    Volume filter: OFF")
print(f"    Trend filter: OFF")

# Generate signals
print("\n[3/4] Generating signals for each symbol...")
total_signals = 0

for symbol in symbols:
    df = data[symbol]
    print(f"\n{symbol}:")
    print(f"  Data shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")

    try:
        signals = strategy.generate_signals(df)
        print(f"  Signals generated: {len(signals)}")

        if signals:
            for i, signal in enumerate(signals, 1):
                print(f"    {i}. {signal.signal_type.value} @ ${signal.price:.2f} "
                      f"(confidence: {signal.confidence:.2f}, quality: {signal.metadata.get('quality', 'N/A')})")
                total_signals += 1
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
    print("\n⚠️  ZERO SIGNALS - Possible causes:")
    print("  1. Strategy thresholds too conservative")
    print("  2. Not enough historical data for indicators")
    print("  3. Market conditions don't match strategy criteria")
    print("  4. Logic error in signal generation")
