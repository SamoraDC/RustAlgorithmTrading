#!/usr/bin/env python3
"""
Quick validation script for momentum strategy fixes

Runs a simple test to verify:
1. RSI thresholds are correct (30/70)
2. EXIT signals are generated
3. Stop-loss/take-profit work
4. Position size is 15%
5. Signals are balanced
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, '/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading')

from src.strategies.momentum import MomentumStrategy
from src.strategies.base import SignalType


def create_test_data():
    """Create test data with clear patterns"""
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1D')

    # Pattern: down -> up -> down -> up (should trigger all signal types)
    prices = np.concatenate([
        np.linspace(100, 85, 50),   # Downtrend to oversold
        np.linspace(85, 105, 50),   # Strong uptrend (LONG entry)
        np.linspace(105, 90, 50),   # Reversal down (EXIT, then SHORT entry)
        np.linspace(90, 100, 50)    # Recovery (EXIT)
    ])

    data = pd.DataFrame({
        'open': prices,
        'high': prices + 2,
        'low': prices - 2,
        'close': prices,
        'volume': [1000000] * 200
    }, index=dates)
    data.attrs['symbol'] = 'TEST'

    return data


def validate_parameters():
    """Validate strategy parameters are correct"""
    print("=" * 60)
    print("VALIDATING MOMENTUM STRATEGY PARAMETERS")
    print("=" * 60)

    strategy = MomentumStrategy()

    tests = [
        ("RSI Oversold", strategy.get_parameter('rsi_oversold'), 30),
        ("RSI Overbought", strategy.get_parameter('rsi_overbought'), 70),
        ("Position Size", strategy.get_parameter('position_size'), 0.15),
        ("Stop Loss %", strategy.get_parameter('stop_loss_pct'), 0.02),
        ("Take Profit %", strategy.get_parameter('take_profit_pct'), 0.03),
    ]

    all_passed = True
    for name, actual, expected in tests:
        passed = actual == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}: {actual} (expected {expected})")
        all_passed = all_passed and passed

    print()
    return all_passed


def validate_signals():
    """Validate signal generation"""
    print("=" * 60)
    print("VALIDATING SIGNAL GENERATION")
    print("=" * 60)

    data = create_test_data()
    strategy = MomentumStrategy()
    signals = strategy.generate_signals(data)

    long_signals = [s for s in signals if s.signal_type == SignalType.LONG]
    short_signals = [s for s in signals if s.signal_type == SignalType.SHORT]
    exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]

    print(f"Total signals generated: {len(signals)}")
    print(f"  - LONG signals: {len(long_signals)}")
    print(f"  - SHORT signals: {len(short_signals)}")
    print(f"  - EXIT signals: {len(exit_signals)}")
    print()

    tests = [
        ("Generates signals", len(signals) > 0),
        ("Generates LONG signals", len(long_signals) > 0),
        ("Generates SHORT signals", len(short_signals) > 0),
        ("Generates EXIT signals", len(exit_signals) > 0),
    ]

    all_passed = True
    for name, condition in tests:
        status = "✅ PASS" if condition else "❌ FAIL"
        print(f"{status} {name}")
        all_passed = all_passed and condition

    # Check signal balance
    entry_signals = len(long_signals) + len(short_signals)
    if entry_signals > 0:
        long_pct = len(long_signals) / entry_signals * 100
        balanced = 20 <= long_pct <= 80
        status = "✅ PASS" if balanced else "❌ FAIL"
        print(f"{status} Signal balance: {long_pct:.1f}% LONG (should be 20-80%)")
        all_passed = all_passed and balanced

    print()
    return all_passed


def validate_exit_metadata():
    """Validate EXIT signal metadata"""
    print("=" * 60)
    print("VALIDATING EXIT SIGNAL METADATA")
    print("=" * 60)

    data = create_test_data()
    strategy = MomentumStrategy()
    signals = strategy.generate_signals(data)

    exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]

    if not exit_signals:
        print("❌ FAIL No EXIT signals to validate")
        return False

    required_fields = ['exit_reason', 'pnl_pct', 'entry_price', 'position_type']

    all_passed = True
    for i, signal in enumerate(exit_signals[:3]):  # Check first 3
        print(f"\nExit Signal {i+1}:")
        for field in required_fields:
            has_field = field in signal.metadata
            status = "✅" if has_field else "❌"
            value = signal.metadata.get(field, 'MISSING')
            print(f"  {status} {field}: {value}")
            all_passed = all_passed and has_field

    print()
    return all_passed


def validate_position_sizing():
    """Validate position sizing calculation"""
    print("=" * 60)
    print("VALIDATING POSITION SIZING")
    print("=" * 60)

    strategy = MomentumStrategy(position_size=0.15)

    from src.strategies.base import Signal

    signal = Signal(
        timestamp=datetime.now(),
        symbol='TEST',
        signal_type=SignalType.LONG,
        price=100.0,
        confidence=1.0
    )

    account_value = 10000.0
    position_size = strategy.calculate_position_size(signal, account_value)
    position_value = position_size * signal.price

    expected_value = account_value * 0.15
    difference = abs(position_value - expected_value)

    passed = difference < 10
    status = "✅ PASS" if passed else "❌ FAIL"

    print(f"Account value: ${account_value:,.2f}")
    print(f"Position size: {position_size} shares")
    print(f"Position value: ${position_value:,.2f}")
    print(f"Expected (15%): ${expected_value:,.2f}")
    print(f"{status} Difference: ${difference:.2f}")
    print()

    return passed


def validate_reward_risk_ratio():
    """Validate reward:risk ratio is 1.5:1"""
    print("=" * 60)
    print("VALIDATING REWARD:RISK RATIO")
    print("=" * 60)

    strategy = MomentumStrategy()

    stop_loss = strategy.get_parameter('stop_loss_pct')
    take_profit = strategy.get_parameter('take_profit_pct')
    ratio = take_profit / stop_loss

    expected_ratio = 1.5
    passed = abs(ratio - expected_ratio) < 0.1

    status = "✅ PASS" if passed else "❌ FAIL"

    print(f"Stop Loss: {stop_loss * 100}%")
    print(f"Take Profit: {take_profit * 100}%")
    print(f"Reward:Risk Ratio: {ratio:.2f}:1")
    print(f"{status} Expected: 1.5:1")
    print()

    return passed


def main():
    """Run all validations"""
    print("\n" + "=" * 60)
    print("MOMENTUM STRATEGY FIX VALIDATION")
    print("=" * 60)
    print()

    results = {
        "Parameters": validate_parameters(),
        "Signal Generation": validate_signals(),
        "Exit Metadata": validate_exit_metadata(),
        "Position Sizing": validate_position_sizing(),
        "Reward:Risk Ratio": validate_reward_risk_ratio(),
    }

    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        all_passed = all_passed and passed

    print()
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ Momentum strategy fixes are working correctly")
        print("\nNext steps:")
        print("1. Run comprehensive backtests")
        print("2. Validate win rate >40%")
        print("3. Measure Sharpe ratio improvement")
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("Please review the errors above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
