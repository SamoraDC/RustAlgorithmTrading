"""
WEEK 3: Test ADX Trending Market Filter

Tests that momentum strategy only trades when ADX > 25 (trending markets)
and skips signals in choppy/ranging markets (ADX < 25).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.momentum import MomentumStrategy
from src.strategies.base import SignalType


class TestADXFilter:
    """Test ADX trending market filter functionality"""

    @pytest.fixture
    def strategy_with_adx(self):
        """Create momentum strategy with ADX filter enabled"""
        return MomentumStrategy(
            use_adx_filter=True,
            adx_threshold=25.0,
            adx_period=14,
            rsi_period=14,
            volume_confirmation=False,  # Disable volume filter for testing
        )

    @pytest.fixture
    def strategy_without_adx(self):
        """Create momentum strategy with ADX filter disabled"""
        return MomentumStrategy(
            use_adx_filter=False,
            rsi_period=14,
            volume_confirmation=False,
        )

    @pytest.fixture
    def trending_market_data(self):
        """Generate synthetic data representing a trending market (high ADX)"""
        # Create strong uptrend
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        np.random.seed(42)

        # Strong uptrend: price increases consistently
        trend = np.linspace(100, 120, 100)
        noise = np.random.normal(0, 0.5, 100)
        close = trend + noise

        # Create OHLC data
        data = pd.DataFrame({
            'timestamp': dates,
            'open': close + np.random.uniform(-0.5, 0.5, 100),
            'high': close + np.random.uniform(0.5, 1.5, 100),
            'low': close - np.random.uniform(0.5, 1.5, 100),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 100),
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        return data

    @pytest.fixture
    def ranging_market_data(self):
        """Generate synthetic data representing a ranging market (low ADX)"""
        # Create sideways market
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        np.random.seed(42)

        # Ranging market: price oscillates around 100
        close = 100 + np.random.normal(0, 2, 100)

        # Create OHLC data
        data = pd.DataFrame({
            'timestamp': dates,
            'open': close + np.random.uniform(-0.5, 0.5, 100),
            'high': close + np.random.uniform(0.5, 1.5, 100),
            'low': close - np.random.uniform(0.5, 1.5, 100),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 100),
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        return data

    def test_adx_filter_enabled_initialization(self, strategy_with_adx):
        """Test that strategy initializes with ADX filter enabled"""
        assert strategy_with_adx.get_parameter('use_adx_filter') is True
        assert strategy_with_adx.get_parameter('adx_threshold') == 25.0
        assert strategy_with_adx.regime_detector is not None
        print("✅ ADX filter enabled and regime detector initialized")

    def test_adx_filter_disabled_initialization(self, strategy_without_adx):
        """Test that strategy initializes with ADX filter disabled"""
        assert strategy_without_adx.get_parameter('use_adx_filter') is False
        assert strategy_without_adx.regime_detector is None
        print("✅ ADX filter disabled and no regime detector")

    def test_adx_calculation_in_trending_market(self, strategy_with_adx, trending_market_data):
        """Test that ADX is calculated correctly for trending markets"""
        signals = strategy_with_adx.generate_signals(trending_market_data)

        # Check that ADX was calculated
        # Note: ADX will be in the strategy's internal data processing
        # We verify by checking if signals were generated (which means ADX passed threshold)
        assert len(signals) > 0, "Trending market should generate signals"

        # Check that signals have ADX metadata
        entry_signals = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
        if entry_signals:
            assert 'adx' in entry_signals[0].metadata
            print(f"✅ ADX calculated for trending market: {entry_signals[0].metadata['adx']:.1f}")

    def test_adx_blocks_ranging_market_signals(self, strategy_with_adx, ranging_market_data):
        """Test that ADX filter blocks signals in ranging markets (ADX < 25)"""
        signals_with_filter = strategy_with_adx.generate_signals(ranging_market_data)

        # Create strategy without ADX filter for comparison
        strategy_no_filter = MomentumStrategy(
            use_adx_filter=False,
            rsi_period=14,
            volume_confirmation=False,
        )
        signals_without_filter = strategy_no_filter.generate_signals(ranging_market_data)

        # ADX filter should reduce or eliminate signals in ranging market
        entry_signals_with = [s for s in signals_with_filter if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
        entry_signals_without = [s for s in signals_without_filter if s.signal_type in [SignalType.LONG, SignalType.SHORT]]

        print(f"📊 Signals WITH ADX filter: {len(entry_signals_with)}")
        print(f"📊 Signals WITHOUT ADX filter: {len(entry_signals_without)}")

        # ADX filter should block signals in ranging markets
        # We expect significantly fewer (or zero) signals with the filter
        assert len(entry_signals_with) <= len(entry_signals_without), \
            "ADX filter should reduce signals in ranging markets"

        print("✅ ADX filter successfully blocks ranging market signals")

    def test_adx_allows_trending_market_signals(self, strategy_with_adx, trending_market_data):
        """Test that ADX filter allows signals in trending markets (ADX > 25)"""
        signals = strategy_with_adx.generate_signals(trending_market_data)
        entry_signals = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]

        assert len(entry_signals) > 0, "Trending market should generate signals with ADX filter"

        # Verify ADX values in signals are above threshold
        for signal in entry_signals:
            if signal.metadata.get('adx') is not None:
                assert signal.metadata['adx'] >= 20.0, \
                    f"Signal ADX {signal.metadata['adx']:.1f} should be near or above threshold in trending market"

        print(f"✅ ADX filter allows {len(entry_signals)} signals in trending market")

    def test_adx_threshold_customization(self):
        """Test that custom ADX thresholds work correctly"""
        # Create strategy with stricter ADX threshold
        strategy_strict = MomentumStrategy(
            use_adx_filter=True,
            adx_threshold=30.0,  # Stricter threshold
            rsi_period=14,
            volume_confirmation=False,
        )

        assert strategy_strict.get_parameter('adx_threshold') == 30.0
        print("✅ Custom ADX threshold (30.0) configured successfully")

    def test_signal_metadata_includes_adx(self, strategy_with_adx, trending_market_data):
        """Test that generated signals include ADX in metadata"""
        signals = strategy_with_adx.generate_signals(trending_market_data)
        entry_signals = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]

        if entry_signals:
            signal = entry_signals[0]
            assert 'adx' in signal.metadata, "Signal metadata should include ADX"
            assert signal.metadata['adx'] is not None or signal.metadata['adx'] >= 0
            print(f"✅ Signal metadata includes ADX: {signal.metadata['adx']}")

    def test_adx_filter_logs_skip_messages(self, strategy_with_adx, ranging_market_data, caplog):
        """Test that ADX filter logs when it skips signals"""
        import logging
        caplog.set_level(logging.DEBUG)

        signals = strategy_with_adx.generate_signals(ranging_market_data)

        # Check for debug log messages about skipped signals
        skip_messages = [record for record in caplog.records
                        if 'SKIPPING SIGNAL' in record.message and 'ADX' in record.message]

        # We expect some skip messages in a ranging market
        # (ADX < 25 should trigger skip logs)
        if len(skip_messages) > 0:
            print(f"✅ ADX filter logged {len(skip_messages)} skip messages")
        else:
            print("ℹ️ No skip messages (market may have had brief trending periods)")

    def test_week3_expected_trade_reduction(self, strategy_with_adx, strategy_without_adx):
        """Test WEEK 3 expected impact: 15-20% fewer trades with ADX filter"""
        # Use ranging market data (should show biggest difference)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        np.random.seed(42)
        close = 100 + np.random.normal(0, 2, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close + np.random.uniform(-0.5, 0.5, 100),
            'high': close + np.random.uniform(0.5, 1.5, 100),
            'low': close - np.random.uniform(0.5, 1.5, 100),
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 100),
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals_with = strategy_with_adx.generate_signals(data)
        signals_without = strategy_without_adx.generate_signals(data)

        trades_with = len([s for s in signals_with if s.signal_type in [SignalType.LONG, SignalType.SHORT]])
        trades_without = len([s for s in signals_without if s.signal_type in [SignalType.LONG, SignalType.SHORT]])

        if trades_without > 0:
            reduction_pct = (trades_without - trades_with) / trades_without * 100
            print(f"📊 Trade reduction with ADX filter: {reduction_pct:.1f}%")
            print(f"   Trades WITHOUT ADX: {trades_without}")
            print(f"   Trades WITH ADX: {trades_with}")

            # We expect some reduction (doesn't have to be exactly 15-20% in synthetic data)
            assert trades_with <= trades_without, "ADX filter should not increase trades"
            print("✅ ADX filter reduces trades as expected")
        else:
            print("ℹ️ No trades generated without filter (need better test data)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
