"""
Validation script for Enhanced Momentum Strategy

This script validates that the enhanced momentum strategy is properly implemented
and can be imported and used correctly.

Run with: python3 scripts/validate_enhanced_momentum.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all components can be imported"""
    print("Testing imports...")

    try:
        from src.strategies.enhanced_momentum import (
            EnhancedMomentumStrategy,
            SignalQuality,
            RiskParameters,
            IndicatorThresholds,
            TradeRationale
        )
        from src.strategies.base import SignalType
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_strategy_creation():
    """Test that strategy can be instantiated"""
    print("\nTesting strategy creation...")

    try:
        from src.strategies.enhanced_momentum import (
            EnhancedMomentumStrategy,
            SignalQuality
        )

        strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.MODERATE
        )

        print(f"✓ Strategy created: {strategy}")
        print(f"  - Name: {strategy.name}")
        print(f"  - Symbols: {strategy.symbols}")
        print(f"  - Min Quality: {strategy.min_signal_quality.value}")
        return True
    except Exception as e:
        print(f"✗ Strategy creation failed: {e}")
        return False


def test_risk_parameters():
    """Test custom risk parameters"""
    print("\nTesting custom risk parameters...")

    try:
        from src.strategies.enhanced_momentum import (
            EnhancedMomentumStrategy,
            RiskParameters,
            SignalQuality
        )

        custom_risk = RiskParameters(
            max_position_size=0.20,
            risk_per_trade=0.025,
            stop_loss_atr_multiple=2.5
        )

        strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            risk_params=custom_risk,
            min_signal_quality=SignalQuality.STRONG
        )

        print("✓ Custom risk parameters applied")
        print(f"  - Max Position: {strategy.risk_params.max_position_size:.1%}")
        print(f"  - Risk/Trade: {strategy.risk_params.risk_per_trade:.2%}")
        print(f"  - Stop Loss ATR: {strategy.risk_params.stop_loss_atr_multiple}x")
        return True
    except Exception as e:
        print(f"✗ Risk parameter test failed: {e}")
        return False


def test_indicator_calculation():
    """Test that indicators can be calculated"""
    print("\nTesting indicator calculation...")

    try:
        import pandas as pd
        import numpy as np
        from src.strategies.enhanced_momentum import EnhancedMomentumStrategy, SignalQuality

        # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')
        data = pd.DataFrame({
            'open': 100 + np.random.randn(100),
            'high': 102 + np.random.randn(100),
            'low': 98 + np.random.randn(100),
            'close': 100 + np.random.randn(100),
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.WEAK
        )

        # Calculate indicators
        result = strategy.calculate_indicators(data)

        required_indicators = ['rsi', 'macd', 'macd_signal', 'ema_fast', 'ema_slow', 'atr']
        missing = [ind for ind in required_indicators if ind not in result.columns]

        if missing:
            print(f"✗ Missing indicators: {missing}")
            return False

        print("✓ All indicators calculated successfully")
        print(f"  - RSI range: {result['rsi'].min():.1f} to {result['rsi'].max():.1f}")
        print(f"  - MACD calculated: {len(result['macd'].dropna())} valid values")
        print(f"  - ATR calculated: {len(result['atr'].dropna())} valid values")
        return True
    except Exception as e:
        print(f"✗ Indicator calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generation():
    """Test signal generation"""
    print("\nTesting signal generation...")

    try:
        import pandas as pd
        import numpy as np
        from src.strategies.enhanced_momentum import EnhancedMomentumStrategy, SignalQuality

        # Create trending data for better signals
        dates = pd.date_range(start='2024-01-01', periods=150, freq='1D')
        np.random.seed(42)

        # Generate uptrend with volatility
        close_prices = 100 + np.cumsum(np.random.randn(150) * 2 + 0.1)

        data = pd.DataFrame({
            'open': close_prices + np.random.randn(150) * 0.5,
            'high': close_prices + abs(np.random.randn(150)) * 1,
            'low': close_prices - abs(np.random.randn(150)) * 1,
            'close': close_prices,
            'volume': np.random.randint(1000000, 5000000, 150)
        }, index=dates)

        # Ensure OHLC consistency
        data['high'] = data[['high', 'open', 'close']].max(axis=1)
        data['low'] = data[['low', 'open', 'close']].min(axis=1)
        data.attrs['symbol'] = 'TEST'

        strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.WEAK,  # Lower threshold for testing
            enable_volume_filter=False,  # Disable for testing
            enable_trend_filter=False
        )

        signals = strategy.generate_signals(data)

        print(f"✓ Signal generation successful")
        print(f"  - Generated {len(signals)} signals")

        if signals:
            print(f"  - First signal: {signals[0].signal_type.value} @ ${signals[0].price:.2f}")
            print(f"  - Quality: {signals[0].metadata.get('quality', 'N/A')}")
            print(f"  - Confidence: {signals[0].confidence:.2%}")

        return True
    except Exception as e:
        print(f"✗ Signal generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_position_sizing():
    """Test position sizing"""
    print("\nTesting position sizing...")

    try:
        from src.strategies.enhanced_momentum import EnhancedMomentumStrategy, SignalQuality
        from src.strategies.base import Signal, SignalType
        from datetime import datetime

        strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.MODERATE
        )

        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.BUY,
            price=100.0,
            confidence=0.8,
            metadata={
                'stop_loss': 95.0,
                'take_profit': 110.0,
                'quality': 'moderate'
            }
        )

        account_value = 100000
        position_size = strategy.calculate_position_size(signal, account_value)

        print("✓ Position sizing successful")
        print(f"  - Account Value: ${account_value:,}")
        print(f"  - Entry Price: ${signal.price:.2f}")
        print(f"  - Stop Loss: ${signal.metadata['stop_loss']:.2f}")
        print(f"  - Position Size: {position_size:.2f} shares")
        print(f"  - Position Value: ${position_size * signal.price:,.2f}")

        # Verify constraints
        max_position = account_value * strategy.risk_params.max_position_size
        assert position_size * signal.price <= max_position * 1.01, "Position exceeds max"

        print("  - Constraints: PASSED")
        return True
    except Exception as e:
        print(f"✗ Position sizing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_summary():
    """Test performance summary"""
    print("\nTesting performance summary...")

    try:
        import pandas as pd
        import numpy as np
        from src.strategies.enhanced_momentum import EnhancedMomentumStrategy, SignalQuality

        strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.WEAK
        )

        # Generate some signals
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')
        data = pd.DataFrame({
            'open': 100 + np.random.randn(100),
            'high': 102 + np.random.randn(100),
            'low': 98 + np.random.randn(100),
            'close': 100 + np.random.randn(100),
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy.generate_signals(data)
        summary = strategy.get_performance_summary()

        print("✓ Performance summary generated")
        print(f"  - Total Signals: {summary['total_signals']}")
        print(f"  - Quality Distribution: {summary['signals_by_quality']}")
        print(f"  - Risk Parameters: {summary['risk_parameters']}")
        return True
    except Exception as e:
        print(f"✗ Performance summary failed: {e}")
        return False


def main():
    """Run all validation tests"""
    print("="*80)
    print("Enhanced Momentum Strategy Validation")
    print("="*80)

    tests = [
        test_imports,
        test_strategy_creation,
        test_risk_parameters,
        test_indicator_calculation,
        test_signal_generation,
        test_position_sizing,
        test_performance_summary
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*80)
    print("Validation Summary")
    print("="*80)

    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - Strategy is ready for use!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed - Please review errors above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
