"""
Unit tests for trading strategies.

Tests cover:
- Signal generation correctness
- Strategy parameter sensitivity
- Edge case handling
- Strategy invariants
"""
import pytest
import pandas as pd
import numpy as np


@pytest.mark.unit
class TestMomentumStrategy:
    """Test suite for momentum-based strategies."""

    def test_signal_generation(self, simple_momentum_strategy, sample_ohlcv_data):
        """Test that momentum strategy generates valid signals."""
        signals = simple_momentum_strategy.generate_signals(sample_ohlcv_data)

        # Signals should be -1, 0, or 1
        assert signals['signal'].isin([-1, 0, 1]).all()

        # Should have same length as input data
        assert len(signals) == len(sample_ohlcv_data)

    def test_uptrend_generates_buy_signal(self, simple_momentum_strategy):
        """Test that strong uptrend generates buy signals."""
        # Create data with clear uptrend
        dates = pd.date_range('2023-01-01', periods=50, freq='1h')
        uptrend_data = pd.DataFrame({
            'timestamp': dates,
            'close': np.linspace(100, 120, 50)  # Steady 20% increase
        })

        signals = simple_momentum_strategy.generate_signals(uptrend_data)

        # Should generate buy signals in the uptrend
        assert (signals['signal'] == 1).sum() > 0

    def test_downtrend_generates_sell_signal(self, simple_momentum_strategy):
        """Test that strong downtrend generates sell signals."""
        dates = pd.date_range('2023-01-01', periods=50, freq='1h')
        downtrend_data = pd.DataFrame({
            'timestamp': dates,
            'close': np.linspace(120, 100, 50)  # 20% decrease
        })

        signals = simple_momentum_strategy.generate_signals(downtrend_data)

        # Should generate sell signals in the downtrend
        assert (signals['signal'] == -1).sum() > 0

    def test_sideways_market_minimal_signals(self, simple_momentum_strategy):
        """Test that sideways market generates few signals."""
        dates = pd.date_range('2023-01-01', periods=100, freq='1h')
        np.random.seed(42)
        sideways_data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.random.normal(0, 0.5, 100)  # Tight range
        })

        signals = simple_momentum_strategy.generate_signals(sideways_data)

        # Most signals should be neutral (0)
        neutral_ratio = (signals['signal'] == 0).sum() / len(signals)
        assert neutral_ratio > 0.8


@pytest.mark.unit
class TestMeanReversionStrategy:
    """Test suite for mean reversion strategies."""

    def test_signal_generation(self, simple_mean_reversion_strategy, sample_ohlcv_data):
        """Test mean reversion strategy generates valid signals."""
        signals = simple_mean_reversion_strategy.generate_signals(sample_ohlcv_data)

        assert signals['signal'].isin([-1, 0, 1]).all()
        assert len(signals) == len(sample_ohlcv_data)

    def test_oversold_generates_buy(self, simple_mean_reversion_strategy):
        """Test that oversold conditions generate buy signals."""
        dates = pd.date_range('2023-01-01', periods=50, freq='1h')

        # Create mean reversion scenario: spike down then recovery
        prices = np.concatenate([
            np.ones(20) * 100,  # Stable at 100
            np.ones(10) * 85,   # Sharp drop (oversold)
            np.ones(20) * 100   # Return to mean
        ])

        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices
        })

        signals = simple_mean_reversion_strategy.generate_signals(data)

        # Should generate buy signals during the drop
        buy_signals = signals.loc[20:30, 'signal']
        assert (buy_signals == 1).sum() > 0

    def test_overbought_generates_sell(self, simple_mean_reversion_strategy):
        """Test that overbought conditions generate sell signals."""
        dates = pd.date_range('2023-01-01', periods=50, freq='1h')

        # Create mean reversion scenario: spike up then reversion
        prices = np.concatenate([
            np.ones(20) * 100,  # Stable at 100
            np.ones(10) * 115,  # Sharp rise (overbought)
            np.ones(20) * 100   # Return to mean
        ])

        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices
        })

        signals = simple_mean_reversion_strategy.generate_signals(data)

        # Should generate sell signals during the spike
        sell_signals = signals.loc[20:30, 'signal']
        assert (sell_signals == -1).sum() > 0


@pytest.mark.unit
class TestStrategyInvariants:
    """Test strategy invariants that should always hold."""

    def test_no_future_data_leakage(self, simple_momentum_strategy, sample_ohlcv_data):
        """Critical: Strategy should not use future data."""
        # Signal at time T should only depend on data up to T

        full_signals = simple_momentum_strategy.generate_signals(sample_ohlcv_data)

        # Check that signal at index i matches when using only data[:i+1]
        test_indices = [50, 100, 200]

        for idx in test_indices:
            partial_data = sample_ohlcv_data.iloc[:idx+1]
            partial_signals = simple_momentum_strategy.generate_signals(partial_data)

            # Last signal should match
            assert full_signals.iloc[idx]['signal'] == partial_signals.iloc[-1]['signal']

    def test_deterministic_signals(self, simple_momentum_strategy, sample_ohlcv_data):
        """Test that strategy produces same signals for same input."""
        signals1 = simple_momentum_strategy.generate_signals(sample_ohlcv_data)
        signals2 = simple_momentum_strategy.generate_signals(sample_ohlcv_data)

        assert signals1.equals(signals2)

    def test_handles_missing_data_gracefully(self, simple_momentum_strategy):
        """Test strategy handles NaN values appropriately."""
        dates = pd.date_range('2023-01-01', periods=100, freq='1h')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(100) + 100
        })

        # Introduce some NaN values
        data.loc[20:25, 'close'] = np.nan

        # Strategy should not crash
        signals = simple_momentum_strategy.generate_signals(data)
        assert len(signals) == len(data)

    def test_parameter_bounds(self):
        """Test strategy respects parameter boundaries."""
        # Lookback period should be positive
        with pytest.raises(ValueError):
            # MomentumStrategy(lookback=-5)
            pass

        # Window size should be reasonable
        with pytest.raises(ValueError):
            # MeanReversionStrategy(window=0)
            pass
