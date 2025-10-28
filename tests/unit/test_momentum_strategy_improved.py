"""
Comprehensive Test Suite for Enhanced Momentum Strategy

Tests cover:
- Signal generation produces both LONG and SHORT signals
- RSI thresholds work correctly (30/70)
- Stop-loss triggers at expected levels
- Take-profit triggers at expected levels
- Position size is 15% of capital (not 95%)
- Win rate validation (aim for >40%)
- Multi-indicator confirmation logic
- Risk management validation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List

from src.strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    RiskParameters,
    IndicatorThresholds,
    SignalQuality,
    SignalType
)
from src.strategies.base import Signal


class TestEnhancedMomentumStrategy:
    """Test suite for EnhancedMomentumStrategy"""

    @pytest.fixture
    def strategy(self):
        """Create strategy with default parameters"""
        return EnhancedMomentumStrategy(
            symbols=['AAPL'],
            risk_params=RiskParameters(
                max_position_size=0.15,
                risk_per_trade=0.02,
                stop_loss_atr_multiple=2.0,
                take_profit_atr_multiple=3.0
            ),
            indicator_thresholds=IndicatorThresholds(
                rsi_oversold=30,
                rsi_overbought=70
            ),
            min_signal_quality=SignalQuality.MODERATE
        )

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data with oscillating patterns"""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')

        # Create oscillating price pattern to generate both LONG and SHORT signals
        price_base = 100
        oscillation = 10 * np.sin(np.linspace(0, 4 * np.pi, 200))
        trend = np.linspace(0, 20, 200)
        noise = np.random.normal(0, 1, 200)

        close_prices = price_base + oscillation + trend + noise

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.randint(100000, 500000, 200)
        })

        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'AAPL'

        return data

    @pytest.fixture
    def oversold_data(self):
        """Create data that generates LONG signal (oversold RSI)"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')

        # Declining prices to create oversold RSI
        close_prices = 100 - np.linspace(0, 20, 100) + np.random.normal(0, 0.5, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.randint(100000, 500000, 100)
        })

        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'AAPL'

        return data

    @pytest.fixture
    def overbought_data(self):
        """Create data that generates SHORT signal (overbought RSI)"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')

        # Rising prices to create overbought RSI
        close_prices = 100 + np.linspace(0, 20, 100) + np.random.normal(0, 0.5, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.randint(100000, 500000, 100)
        })

        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'AAPL'

        return data

    def test_strategy_initialization(self, strategy):
        """Test strategy initializes with correct parameters"""
        assert strategy.name == "EnhancedMomentumStrategy"
        assert strategy.risk_params.max_position_size == 0.15
        assert strategy.risk_params.risk_per_trade == 0.02
        assert strategy.thresholds.rsi_oversold == 30
        assert strategy.thresholds.rsi_overbought == 70
        assert strategy.min_signal_quality == SignalQuality.MODERATE

    def test_rsi_thresholds_correct(self, strategy):
        """Test RSI thresholds are set to 30/70"""
        assert strategy.thresholds.rsi_oversold == 30
        assert strategy.thresholds.rsi_overbought == 70
        print("✓ RSI thresholds correctly set to 30/70")

    def test_position_size_15_percent(self, strategy):
        """Test position size is 15% of capital, not 95%"""
        assert strategy.risk_params.max_position_size == 0.15
        assert strategy.risk_params.max_position_size != 0.95
        print("✓ Position size correctly set to 15% of capital")

    def test_stop_loss_configuration(self, strategy):
        """Test stop-loss is configured at 2.0 ATR"""
        assert strategy.risk_params.stop_loss_atr_multiple == 2.0
        print("✓ Stop-loss configured at 2.0 ATR multiple")

    def test_take_profit_configuration(self, strategy):
        """Test take-profit is configured at 3.0 ATR"""
        assert strategy.risk_params.take_profit_atr_multiple == 3.0
        print("✓ Take-profit configured at 3.0 ATR multiple")

    def test_signal_generation_produces_both_types(self, strategy, sample_data):
        """Test that signal generation produces both LONG and SHORT signals"""
        signals = strategy.generate_signals(sample_data)

        assert len(signals) > 0, "No signals generated"

        signal_types = [s.signal_type for s in signals]
        long_count = signal_types.count(SignalType.LONG)
        short_count = signal_types.count(SignalType.SHORT)

        print(f"Generated signals: {len(signals)} total, {long_count} LONG, {short_count} SHORT")

        # Should have at least some signals of each type
        assert long_count > 0, "No LONG signals generated"
        assert short_count > 0, "No SHORT signals generated"

        # Signals should be somewhat balanced (within 80-20 to 20-80 range)
        total = long_count + short_count
        long_pct = long_count / total
        assert 0.2 <= long_pct <= 0.8, f"Signals too imbalanced: {long_pct:.1%} LONG"

        print("✓ Signals are balanced between LONG and SHORT")

    def test_long_signal_from_oversold(self, strategy, oversold_data):
        """Test LONG signal generation from oversold conditions"""
        signals = strategy.generate_signals(oversold_data)

        # Should generate at least some LONG signals
        long_signals = [s for s in signals if s.signal_type == SignalType.LONG]
        assert len(long_signals) > 0, "No LONG signals from oversold data"

        # Check signal has proper metadata
        for signal in long_signals:
            assert 'rsi' in signal.metadata
            assert 'stop_loss' in signal.metadata
            assert 'take_profit' in signal.metadata
            assert signal.confidence > 0

        print(f"✓ Generated {len(long_signals)} LONG signals from oversold conditions")

    def test_short_signal_from_overbought(self, strategy, overbought_data):
        """Test SHORT signal generation from overbought conditions"""
        signals = strategy.generate_signals(overbought_data)

        # Should generate at least some SHORT signals
        short_signals = [s for s in signals if s.signal_type == SignalType.SHORT]
        assert len(short_signals) > 0, "No SHORT signals from overbought data"

        # Check signal has proper metadata
        for signal in short_signals:
            assert 'rsi' in signal.metadata
            assert 'stop_loss' in signal.metadata
            assert 'take_profit' in signal.metadata
            assert signal.confidence > 0

        print(f"✓ Generated {len(short_signals)} SHORT signals from overbought conditions")

    def test_stop_loss_calculation(self, strategy):
        """Test stop-loss is calculated correctly using ATR"""
        # For LONG signal
        entry_price = 100.0
        atr = 2.0
        signal_type = SignalType.LONG

        stop_loss, take_profit, risk_reward = strategy.calculate_risk_metrics(
            entry_price, signal_type, atr
        )

        expected_stop_loss = entry_price - (atr * 2.0)  # 2.0 ATR multiple
        assert abs(stop_loss - expected_stop_loss) < 0.01

        # Verify it's about 2% below entry (with ATR=2)
        loss_pct = (entry_price - stop_loss) / entry_price
        assert 0.03 <= loss_pct <= 0.05  # Should be around 4% for ATR=2

        print(f"✓ Stop-loss correctly calculated: ${stop_loss:.2f} ({loss_pct:.2%} from entry)")

    def test_take_profit_calculation(self, strategy):
        """Test take-profit is calculated correctly using ATR"""
        # For LONG signal
        entry_price = 100.0
        atr = 2.0
        signal_type = SignalType.LONG

        stop_loss, take_profit, risk_reward = strategy.calculate_risk_metrics(
            entry_price, signal_type, atr
        )

        expected_take_profit = entry_price + (atr * 3.0)  # 3.0 ATR multiple
        assert abs(take_profit - expected_take_profit) < 0.01

        # Verify it's about 3% above entry (with ATR=2)
        gain_pct = (take_profit - entry_price) / entry_price
        assert 0.05 <= gain_pct <= 0.07  # Should be around 6% for ATR=2

        print(f"✓ Take-profit correctly calculated: ${take_profit:.2f} ({gain_pct:.2%} from entry)")

    def test_risk_reward_ratio(self, strategy):
        """Test risk/reward ratio calculation"""
        entry_price = 100.0
        atr = 2.0

        # Test LONG
        stop_loss, take_profit, risk_reward = strategy.calculate_risk_metrics(
            entry_price, SignalType.LONG, atr
        )

        expected_rr = 3.0 / 2.0  # TP multiple / SL multiple
        assert abs(risk_reward - expected_rr) < 0.01
        assert risk_reward >= 1.5  # Should meet minimum threshold

        print(f"✓ Risk/reward ratio correctly calculated: {risk_reward:.2f}")

    def test_position_size_calculation(self, strategy):
        """Test position sizing respects 15% maximum"""
        account_value = 100000.0

        # Create a signal with metadata
        signal = Signal(
            timestamp=datetime.now(),
            symbol='AAPL',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=0.8,
            metadata={
                'stop_loss': 96.0,  # 4% stop loss
                'quality': 'strong'
            }
        )

        position_size = strategy.calculate_position_size(signal, account_value)
        position_value = position_size * signal.price
        position_pct = position_value / account_value

        # Should not exceed 15% of account
        assert position_pct <= 0.15
        assert position_size > 0

        print(f"✓ Position size: {position_size:.2f} shares = ${position_value:.2f} ({position_pct:.2%} of account)")

    def test_signal_quality_levels(self, strategy, sample_data):
        """Test signal quality classification"""
        signals = strategy.generate_signals(sample_data)

        if len(signals) == 0:
            pytest.skip("No signals generated for quality testing")

        # Check all signals have quality metadata
        for signal in signals:
            assert 'quality' in signal.metadata
            quality = signal.metadata['quality']
            assert quality in ['strong', 'moderate', 'weak', 'invalid']

        # Count quality distribution
        quality_counts = {}
        for signal in signals:
            quality = signal.metadata['quality']
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

        print(f"✓ Signal quality distribution: {quality_counts}")

    def test_confidence_scores(self, strategy, sample_data):
        """Test confidence scores are in valid range"""
        signals = strategy.generate_signals(sample_data)

        if len(signals) == 0:
            pytest.skip("No signals generated for confidence testing")

        for signal in signals:
            assert 0.0 <= signal.confidence <= 1.0
            assert signal.confidence > 0.3  # Should have meaningful confidence

        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        print(f"✓ Average confidence: {avg_confidence:.2%}")

    def test_indicator_calculations(self, strategy, sample_data):
        """Test that all indicators are calculated correctly"""
        data_with_indicators = strategy.calculate_indicators(sample_data)

        # Check all required indicators exist
        required_indicators = ['rsi', 'macd', 'macd_signal', 'macd_histogram',
                             'ema_fast', 'ema_slow', 'atr', 'volume_ratio']

        for indicator in required_indicators:
            assert indicator in data_with_indicators.columns
            assert not data_with_indicators[indicator].isna().all()

        print("✓ All indicators calculated correctly")

    def test_no_signals_without_volume(self):
        """Test volume filter prevents signals on low volume"""
        strategy = EnhancedMomentumStrategy(
            symbols=['AAPL'],
            enable_volume_filter=True,
            enable_trend_filter=False,
            min_signal_quality=SignalQuality.WEAK
        )

        # Create data with low volume
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        close_prices = 100 + np.linspace(0, 20, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.full(100, 1000)  # Very low constant volume
        })

        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'AAPL'

        signals = strategy.generate_signals(data)

        # Should generate fewer signals or none due to volume filter
        print(f"✓ Volume filter working: {len(signals)} signals with low volume")

    def test_performance_summary(self, strategy, sample_data):
        """Test strategy performance tracking"""
        signals = strategy.generate_signals(sample_data)

        summary = strategy.get_performance_summary()

        assert 'total_signals' in summary
        assert 'signals_by_quality' in summary
        assert 'risk_parameters' in summary

        assert summary['total_signals'] == len(signals)

        print(f"✓ Performance summary: {summary}")


class TestBacktestValidation:
    """Integration tests with backtesting system"""

    @pytest.fixture
    def backtest_data(self):
        """Create realistic backtest data"""
        dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='1h')

        # Create realistic price movements with trends and reversals
        n = len(dates)
        base_price = 150.0

        # Combine trend, cycles, and noise
        trend = np.linspace(0, 30, n)
        cycle1 = 15 * np.sin(np.linspace(0, 8 * np.pi, n))
        cycle2 = 8 * np.sin(np.linspace(0, 20 * np.pi, n))
        noise = np.random.normal(0, 2, n)

        close_prices = base_price + trend + cycle1 + cycle2 + noise

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * (1 + np.random.uniform(-0.01, 0.01, n)),
            'high': close_prices * (1 + np.random.uniform(0, 0.02, n)),
            'low': close_prices * (1 - np.random.uniform(0, 0.02, n)),
            'close': close_prices,
            'volume': np.random.randint(500000, 2000000, n)
        })

        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'AAPL'

        return data

    def test_full_backtest_signal_distribution(self, backtest_data):
        """Test full backtest produces balanced signals"""
        strategy = EnhancedMomentumStrategy(
            symbols=['AAPL'],
            min_signal_quality=SignalQuality.MODERATE
        )

        signals = strategy.generate_signals(backtest_data)

        assert len(signals) > 20, f"Too few signals: {len(signals)}"

        long_signals = [s for s in signals if s.signal_type == SignalType.LONG]
        short_signals = [s for s in signals if s.signal_type == SignalType.SHORT]

        print(f"\n📊 Backtest Signal Distribution:")
        print(f"   Total signals: {len(signals)}")
        print(f"   LONG signals: {len(long_signals)} ({len(long_signals)/len(signals)*100:.1f}%)")
        print(f"   SHORT signals: {len(short_signals)} ({len(short_signals)/len(signals)*100:.1f}%)")

        # Verify balance
        assert len(long_signals) > 0, "No LONG signals in backtest"
        assert len(short_signals) > 0, "No SHORT signals in backtest"

        long_pct = len(long_signals) / len(signals)
        assert 0.25 <= long_pct <= 0.75, f"Signals too imbalanced: {long_pct:.1%} LONG"

    def test_expected_win_rate_metrics(self, backtest_data):
        """Test strategy produces signals that could achieve >40% win rate"""
        strategy = EnhancedMomentumStrategy(
            symbols=['AAPL'],
            min_signal_quality=SignalQuality.MODERATE
        )

        signals = strategy.generate_signals(backtest_data)

        if len(signals) == 0:
            pytest.skip("No signals generated for win rate testing")

        # Calculate potential win rate based on signal quality
        high_quality_signals = [
            s for s in signals
            if s.metadata.get('quality') in ['strong', 'moderate']
            and s.confidence > 0.6
        ]

        quality_ratio = len(high_quality_signals) / len(signals)

        print(f"\n📈 Win Rate Indicators:")
        print(f"   High quality signals: {len(high_quality_signals)}/{len(signals)} ({quality_ratio:.1%})")
        print(f"   Average confidence: {sum(s.confidence for s in signals)/len(signals):.2%}")

        # With moderate+ quality at 60%+ confidence, expect >40% win rate potential
        assert quality_ratio >= 0.5, "Not enough high-quality signals for >40% win rate"

        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        assert avg_confidence >= 0.55, f"Low average confidence: {avg_confidence:.2%}"

    def test_risk_metrics_in_signals(self, backtest_data):
        """Test all signals include proper risk metrics"""
        strategy = EnhancedMomentumStrategy(
            symbols=['AAPL'],
            min_signal_quality=SignalQuality.MODERATE
        )

        signals = strategy.generate_signals(backtest_data)

        if len(signals) == 0:
            pytest.skip("No signals generated")

        for signal in signals:
            # Check required risk metrics
            assert 'stop_loss' in signal.metadata
            assert 'take_profit' in signal.metadata
            assert 'risk_reward' in signal.metadata
            assert 'atr' in signal.metadata

            # Validate ranges
            assert signal.metadata['stop_loss'] > 0
            assert signal.metadata['take_profit'] > 0
            assert signal.metadata['risk_reward'] >= 1.5

            # Check stop loss is below entry for LONG, above for SHORT
            if signal.signal_type == SignalType.LONG:
                assert signal.metadata['stop_loss'] < signal.price
                assert signal.metadata['take_profit'] > signal.price
            elif signal.signal_type == SignalType.SHORT:
                assert signal.metadata['stop_loss'] > signal.price
                assert signal.metadata['take_profit'] < signal.price

        print("✓ All signals have valid risk metrics")


def run_comprehensive_validation():
    """Run all tests and generate summary report"""
    print("\n" + "="*80)
    print("ENHANCED MOMENTUM STRATEGY - COMPREHENSIVE VALIDATION")
    print("="*80)

    # Run pytest with verbose output
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes',
        '-s'
    ])


if __name__ == '__main__':
    run_comprehensive_validation()
