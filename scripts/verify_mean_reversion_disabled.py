#!/usr/bin/env python3
"""
Verification Script: Mean Reversion Strategy Disabled
Week 3 Priority 1 Implementation

Verifies that mean reversion strategy is properly disabled in RANGING regime.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.market_regime import MarketRegime, select_strategy_for_regime


def verify_mean_reversion_disabled():
    """Verify mean reversion strategy is disabled"""

    print("=" * 80)
    print("WEEK 3 PRIORITY 1: MEAN REVERSION STRATEGY VERIFICATION")
    print("=" * 80)

    # Get RANGING regime configuration
    ranging_config = select_strategy_for_regime(MarketRegime.RANGING)

    print("\n📊 RANGING Regime Configuration:")
    print("-" * 80)
    for key, value in ranging_config.items():
        print(f"  {key:20s}: {value}")

    # Verification checks
    print("\n✅ Verification Checks:")
    print("-" * 80)

    checks = [
        ("Strategy is 'hold' (not 'mean_reversion')",
         ranging_config['strategy'] == 'hold'),

        ("Direction is 'neutral' (not 'both')",
         ranging_config['direction'] == 'neutral'),

        ("Strategy is disabled (enabled=False)",
         ranging_config['enabled'] is False),

        ("Position size is 0.0 (no positions)",
         ranging_config['position_size'] == 0.0),

        ("Stop loss is 0.03 (3%)",
         ranging_config['stop_loss'] == 0.03),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not result:
            all_passed = False

    # Get VOLATILE_RANGING configuration
    print("\n📊 VOLATILE_RANGING Regime Configuration:")
    print("-" * 80)
    volatile_ranging_config = select_strategy_for_regime(MarketRegime.VOLATILE_RANGING)
    for key, value in volatile_ranging_config.items():
        print(f"  {key:20s}: {value}")

    # Summary
    print("\n" + "=" * 80)
    print("WEEK 2 BACKTEST RESULTS (Reason for Disable):")
    print("=" * 80)
    print("  Win Rate:         0% (0 wins out of 63 trades)")
    print("  Annualized Return: -283%")
    print("  Total Trades:     63 (all losing)")
    print("  Root Cause:       Enters at BB extremes, market continues trending")

    print("\n" + "=" * 80)
    print("EXPECTED IMPACT:")
    print("=" * 80)
    print("  ✅ Eliminate -283% annualized loss source")
    print("  ✅ Reduce total trades (remove 63 losing trades)")
    print("  ✅ Improve overall win rate")
    print("  ✅ Reduce maximum drawdown")

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ VERIFICATION PASSED - Mean reversion strategy successfully disabled")
    else:
        print("❌ VERIFICATION FAILED - Some checks did not pass")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = verify_mean_reversion_disabled()
    sys.exit(0 if success else 1)
