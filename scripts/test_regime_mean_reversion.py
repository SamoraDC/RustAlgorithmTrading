#!/usr/bin/env python3
"""
Test script to verify mean reversion strategy is enabled for ranging markets

This script demonstrates:
1. Detection of ranging market regime
2. Automatic selection of mean reversion strategy
3. Proper configuration for ranging markets (position size, stop loss)
4. Logging of regime switches
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.market_regime import (
    MarketRegimeDetector,
    MarketRegime,
    select_strategy_for_regime,
    get_regime_display_name
)
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def generate_ranging_market_data(periods: int = 200) -> pd.DataFrame:
    """Generate synthetic ranging (sideways) market data"""
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')

    # Create sideways movement with oscillations
    base_price = 100.0
    noise = np.random.normal(0, 2.5, periods)  # Random noise
    oscillation = 5 * np.sin(np.linspace(0, 4 * np.pi, periods))  # Sine wave pattern

    close_prices = base_price + oscillation + noise

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices - np.random.uniform(0.2, 1.0, periods),
        'high': close_prices + np.random.uniform(0.5, 2.0, periods),
        'low': close_prices - np.random.uniform(0.5, 2.0, periods),
        'close': close_prices,
        'volume': np.random.uniform(10000, 50000, periods)
    })

    data.set_index('timestamp', inplace=True)
    return data


def generate_trending_market_data(periods: int = 200, direction: str = 'up') -> pd.DataFrame:
    """Generate synthetic trending market data"""
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')

    if direction == 'up':
        trend = np.linspace(100, 150, periods)
    else:
        trend = np.linspace(150, 100, periods)

    noise = np.random.normal(0, 2, periods)
    close_prices = trend + noise

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices - np.random.uniform(0.2, 1.0, periods),
        'high': close_prices + np.random.uniform(0.5, 2.0, periods),
        'low': close_prices - np.random.uniform(0.5, 2.0, periods),
        'close': close_prices,
        'volume': np.random.uniform(10000, 50000, periods)
    })

    data.set_index('timestamp', inplace=True)
    return data


def test_ranging_market_detection():
    """Test that ranging markets are detected correctly"""
    logger.info("=" * 80)
    logger.info("TEST 1: Ranging Market Detection and Strategy Selection")
    logger.info("=" * 80)

    # Generate ranging market data
    data = generate_ranging_market_data(periods=200)

    # Initialize detector
    detector = MarketRegimeDetector(
        adx_period=14,
        atr_period=14,
        adx_trending_threshold=25.0,
        adx_ranging_threshold=20.0
    )

    # Detect regimes
    regimes = detector.detect_regime(data)
    current_regime, indicators = detector.get_current_regime(data)

    # Get regime statistics
    stats = detector.get_regime_stats(regimes)

    logger.info(f"\n📊 REGIME DETECTION RESULTS:")
    logger.info(f"Current Regime: {get_regime_display_name(current_regime)}")
    logger.info(f"ADX: {indicators['adx']:.2f} (threshold: 20.0 for ranging)")
    logger.info(f"ATR: {indicators['atr']:.2f}")
    logger.info(f"Current Price: ${indicators['close']:.2f}")

    logger.info(f"\n📈 REGIME DISTRIBUTION:")
    for regime_name, percentage in stats.items():
        if percentage > 0:
            logger.info(f"  {regime_name}: {percentage:.1f}%")

    # Check strategy selection
    strategy_config = select_strategy_for_regime(current_regime)

    logger.info(f"\n🎯 STRATEGY SELECTION FOR {get_regime_display_name(current_regime)}:")
    logger.info(f"  Strategy: {strategy_config['strategy']}")
    logger.info(f"  Direction: {strategy_config['direction']}")
    logger.info(f"  Enabled: {strategy_config['enabled']}")
    logger.info(f"  Position Size: {strategy_config['position_size'] * 100:.0f}%")
    logger.info(f"  Stop Loss: {strategy_config['stop_loss'] * 100:.0f}%")

    # Verify fix
    ranging_count = stats.get('ranging', 0)
    if ranging_count > 30:  # At least 30% ranging
        if current_regime == MarketRegime.RANGING:
            if strategy_config['strategy'] == 'mean_reversion' and strategy_config['enabled']:
                logger.success("\n✅ TEST PASSED: Mean reversion is ENABLED for ranging markets!")
                return True
            else:
                logger.error(f"\n❌ TEST FAILED: Mean reversion should be enabled but got: {strategy_config}")
                return False
        else:
            logger.warning(f"\n⚠️  Current regime is not RANGING: {current_regime.value}")
    else:
        logger.warning(f"\n⚠️  Not enough ranging periods detected: {ranging_count:.1f}%")

    return False


def test_regime_transitions():
    """Test regime transitions from trending to ranging"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Regime Transitions (Trending → Ranging)")
    logger.info("=" * 80)

    # Create combined data: trending then ranging
    trending_data = generate_trending_market_data(periods=100, direction='up')
    ranging_data = generate_ranging_market_data(periods=100)

    # Combine datasets
    combined_data = pd.concat([trending_data, ranging_data])

    # Initialize detector
    detector = MarketRegimeDetector()

    # Detect regimes over time
    regimes = detector.detect_regime(combined_data)

    # Find regime transitions
    regime_changes = []
    for i in range(1, len(regimes)):
        if regimes.iloc[i] != regimes.iloc[i-1]:
            regime_changes.append({
                'timestamp': regimes.index[i],
                'from': regimes.iloc[i-1],
                'to': regimes.iloc[i],
            })

    logger.info(f"\n🔄 DETECTED {len(regime_changes)} REGIME TRANSITIONS:")
    for idx, change in enumerate(regime_changes[:10], 1):  # Show first 10
        from_display = get_regime_display_name(change['from'])
        to_display = get_regime_display_name(change['to'])
        logger.info(f"  {idx}. {from_display} → {to_display}")

        # Check if transition to ranging enables mean reversion
        if change['to'] in [MarketRegime.RANGING, MarketRegime.VOLATILE_RANGING]:
            config = select_strategy_for_regime(change['to'])
            if config['strategy'] == 'mean_reversion' and config['enabled']:
                logger.success(f"     ✅ Mean reversion ENABLED (position size: {config['position_size']*100:.0f}%)")
            else:
                logger.error(f"     ❌ Mean reversion should be enabled!")

    return True


def test_all_regime_strategies():
    """Test strategy selection for all regime types"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Complete Strategy Configuration Matrix")
    logger.info("=" * 80)

    logger.info("\n📋 STRATEGY CONFIGURATION FOR ALL REGIMES:")

    for regime in MarketRegime:
        config = select_strategy_for_regime(regime)
        display_name = get_regime_display_name(regime)

        status = "✅ ENABLED" if config['enabled'] else "❌ DISABLED"
        logger.info(f"\n{display_name}:")
        logger.info(f"  Strategy: {config['strategy']}")
        logger.info(f"  Direction: {config['direction']}")
        logger.info(f"  Status: {status}")
        logger.info(f"  Position: {config['position_size']*100:.0f}%")
        logger.info(f"  Stop Loss: {config['stop_loss']*100:.0f}%")

        # Verify ranging markets enable mean reversion
        if regime == MarketRegime.RANGING:
            if config['strategy'] == 'mean_reversion' and config['enabled']:
                logger.success("  🎯 CORRECT: Mean reversion enabled!")
            else:
                logger.error(f"  ❌ BUG: Should enable mean reversion, got: {config['strategy']}")

    return True


def main():
    """Run all tests"""
    logger.info("🚀 TESTING MEAN REVERSION STRATEGY FOR RANGING MARKETS")
    logger.info("=" * 80)

    results = []

    # Test 1: Ranging market detection
    try:
        result = test_ranging_market_detection()
        results.append(('Ranging Market Detection', result))
    except Exception as e:
        logger.error(f"Test 1 failed with error: {e}")
        results.append(('Ranging Market Detection', False))

    # Test 2: Regime transitions
    try:
        result = test_regime_transitions()
        results.append(('Regime Transitions', result))
    except Exception as e:
        logger.error(f"Test 2 failed with error: {e}")
        results.append(('Regime Transitions', False))

    # Test 3: All regime strategies
    try:
        result = test_all_regime_strategies()
        results.append(('Strategy Configuration Matrix', result))
    except Exception as e:
        logger.error(f"Test 3 failed with error: {e}")
        results.append(('Strategy Configuration Matrix', False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    logger.info(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        logger.success("\n🎉 ALL TESTS PASSED! Mean reversion is working for ranging markets!")
        return 0
    else:
        logger.error(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
