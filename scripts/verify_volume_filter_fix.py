#!/usr/bin/env python3
"""
Verify Volume Filter Fix Impact
Compares signal generation with old (1.2x) vs new (1.05x) volume threshold
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

from src.strategies.momentum import MomentumStrategy
from src.data.alpaca_client import AlpacaDataClient


def test_volume_filter_impact():
    """Compare signal generation between old and new volume thresholds"""

    print("\n" + "="*70)
    print("VOLUME FILTER FIX VERIFICATION")
    print("="*70)

    # Initialize data client
    client = AlpacaDataClient()

    # Get 3 months of data for testing
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

    results = {
        'old_threshold': {'total_signals': 0, 'by_symbol': {}},
        'new_threshold': {'total_signals': 0, 'by_symbol': {}},
    }

    for symbol in symbols:
        print(f"\n{'─'*70}")
        print(f"Testing {symbol}...")
        print(f"{'─'*70}")

        # Fetch data
        try:
            data = client.get_bars(
                symbol=symbol,
                timeframe='1Day',
                start=start_date,
                end=end_date
            )

            if data is None or len(data) < 50:
                print(f"❌ Insufficient data for {symbol}")
                continue

            data.attrs['symbol'] = symbol

        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")
            continue

        # Test with OLD threshold (1.2x)
        print("\n🔴 OLD THRESHOLD (1.2x - 20% above average)")
        strategy_old = MomentumStrategy(
            volume_confirmation=True,
            volume_multiplier=1.2,
            macd_histogram_threshold=0.0005
        )

        signals_old = strategy_old.generate_signals(data)
        entry_signals_old = [s for s in signals_old if s.signal_type.name in ['LONG', 'SHORT']]

        print(f"  Total signals: {len(signals_old)}")
        print(f"  Entry signals: {len(entry_signals_old)}")

        results['old_threshold']['by_symbol'][symbol] = len(entry_signals_old)
        results['old_threshold']['total_signals'] += len(entry_signals_old)

        # Test with NEW threshold (1.05x)
        print("\n🟢 NEW THRESHOLD (1.05x - 5% above average)")
        strategy_new = MomentumStrategy(
            volume_confirmation=True,
            volume_multiplier=1.05,
            macd_histogram_threshold=0.0005
        )

        signals_new = strategy_new.generate_signals(data)
        entry_signals_new = [s for s in signals_new if s.signal_type.name in ['LONG', 'SHORT']]

        print(f"  Total signals: {len(signals_new)}")
        print(f"  Entry signals: {len(entry_signals_new)}")

        results['new_threshold']['by_symbol'][symbol] = len(entry_signals_new)
        results['new_threshold']['total_signals'] += len(entry_signals_new)

        # Compare
        increase = len(entry_signals_new) - len(entry_signals_old)
        increase_pct = (increase / len(entry_signals_old) * 100) if len(entry_signals_old) > 0 else 0

        print(f"\n📊 COMPARISON:")
        print(f"  Signal increase: {increase:+d} ({increase_pct:+.1f}%)")
        if increase > 0:
            print(f"  ✅ {increase} more trading opportunities captured!")
        elif increase == 0:
            print(f"  ⚠️  No change in signal count")
        else:
            print(f"  ❌ Unexpected decrease in signals")

    # Final summary
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)

    old_total = results['old_threshold']['total_signals']
    new_total = results['new_threshold']['total_signals']
    total_increase = new_total - old_total
    total_increase_pct = (total_increase / old_total * 100) if old_total > 0 else 0

    print(f"\n📈 OLD THRESHOLD (1.2x): {old_total} total entry signals")
    print(f"📈 NEW THRESHOLD (1.05x): {new_total} total entry signals")
    print(f"\n🎯 IMPROVEMENT: {total_increase:+d} signals ({total_increase_pct:+.1f}%)")

    print(f"\n{'Symbol':<10} {'Old (1.2x)':<12} {'New (1.05x)':<12} {'Change':<12} {'Change %':<12}")
    print("─"*70)

    for symbol in symbols:
        if symbol in results['old_threshold']['by_symbol']:
            old = results['old_threshold']['by_symbol'][symbol]
            new = results['new_threshold']['by_symbol'][symbol]
            change = new - old
            change_pct = (change / old * 100) if old > 0 else 0

            print(f"{symbol:<10} {old:<12} {new:<12} {change:+12d} {change_pct:+11.1f}%")

    print("="*70)

    # Validation
    if total_increase >= old_total * 0.30:  # 30% increase expected
        print("\n✅ SUCCESS: Volume filter fix achieved expected 30%+ signal increase!")
        return True
    elif total_increase > 0:
        print(f"\n⚠️  PARTIAL SUCCESS: {total_increase_pct:.1f}% increase (expected 30%+)")
        return True
    else:
        print("\n❌ FAILED: No signal increase detected")
        return False


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    success = test_volume_filter_impact()
    sys.exit(0 if success else 1)
