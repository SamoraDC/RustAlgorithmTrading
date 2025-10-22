"""
Unit tests for Enhanced Momentum Strategy

Tests cover:
- Indicator calculations
- Signal generation logic
- Risk management
- Position sizing
- Filter mechanisms
- Edge cases
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    SignalQuality,
    RiskParameters,
    IndicatorThresholds,
    TradeRationale
)
from src.strategies.base import SignalType


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')
    np.random.seed(42)

    # Generate realistic price data with trend
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)

    data = pd.DataFrame({
        'open': close_prices + np.random.randn(100) * 0.5,
        'high': close_prices + abs(np.random.randn(100)) * 1,
        'low': close_prices - abs(np.random.randn(100)) * 1,
        'close': close_prices,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    data.attrs['symbol'] = 'TEST'
    return data


@pytest.fixture
def strategy():
    """Create strategy instance with default parameters"""
    return EnhancedMomentumStrategy(
        symbols=['TEST'],
        min_signal_quality=SignalQuality.MODERATE
    )


@pytest.fixture
def aggressive_strategy():
    """Create strategy with aggressive risk parameters"""
    risk_params = RiskParameters(
        max_position_size=0.25,
        risk_per_trade=0.03,
        stop_loss_atr_multiple=1.5,
        take_profit_atr_multiple=4.0
    )
    return EnhancedMomentumStrategy(
        symbols=['TEST'],
        risk_params=risk_params,
        min_signal_quality=SignalQuality.WEAK
    )


class TestIndicatorCalculations:
    """Test technical indicator calculations"""

    def test_calculate_indicators(self, strategy, sample_ohlcv_data):
        """Test that all indicators are calculated correctly"""
        data = strategy.calculate_indicators(sample_ohlcv_data)

        # Check all required indicators exist
        required_cols = [
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'ema_fast', 'ema_slow', 'atr', 'volume_sma', 'volume_ratio'
        ]
        for col in required_cols:
            assert col in data.columns, f"Missing indicator: {col}"

        # Check RSI bounds
        valid_rsi = data['rsi'].dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all(), \
            "RSI values out of bounds"

    def test_rsi_calculation_accuracy(self, strategy, sample_ohlcv_data):
        """Test RSI calculation matches expected values"""
        data = strategy.calculate_indicators(sample_ohlcv_data)

        # RSI should have NaN for first period bars
        assert pd.isna(data['rsi'].iloc[0]), "First RSI should be NaN"

        # After sufficient data, RSI should be calculated
        assert not pd.isna(data['rsi'].iloc[20]), "RSI should be calculated after 20 bars"

    def test_macd_calculation(self, strategy, sample_ohlcv_data):
        """Test MACD calculation"""
        data = strategy.calculate_indicators(sample_ohlcv_data)

        # MACD histogram should equal MACD - Signal
        valid_idx = ~data['macd_histogram'].isna()
        calculated_histogram = data.loc[valid_idx, 'macd'] - data.loc[valid_idx, 'macd_signal']

        np.testing.assert_array_almost_equal(
            data.loc[valid_idx, 'macd_histogram'].values,
            calculated_histogram.values,
            decimal=5
        )


class TestSignalGeneration:
    """Test signal generation logic"""

    def test_generate_signals_returns_list(self, strategy, sample_ohlcv_data):
        """Test that signal generation returns a list"""
        signals = strategy.generate_signals(sample_ohlcv_data)
        assert isinstance(signals, list), "Should return list of signals"

    def test_signal_quality_filtering(self, sample_ohlcv_data):
        """Test that minimum signal quality filter works"""
        # Strategy requiring STRONG signals
        strict_strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.STRONG
        )

        # Strategy accepting WEAK signals
        lenient_strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            min_signal_quality=SignalQuality.WEAK
        )

        strict_signals = strict_strategy.generate_signals(sample_ohlcv_data)
        lenient_signals = lenient_strategy.generate_signals(sample_ohlcv_data)

        # Lenient should generate more or equal signals
        assert len(lenient_signals) >= len(strict_signals), \
            "Lenient strategy should generate more signals"

    def test_volume_filter(self, sample_ohlcv_data):
        """Test volume confirmation filter"""
        # With volume filter
        with_filter = EnhancedMomentumStrategy(
            symbols=['TEST'],
            enable_volume_filter=True,
            min_signal_quality=SignalQuality.WEAK
        )

        # Without volume filter
        without_filter = EnhancedMomentumStrategy(
            symbols=['TEST'],
            enable_volume_filter=False,
            min_signal_quality=SignalQuality.WEAK
        )

        signals_with = with_filter.generate_signals(sample_ohlcv_data)
        signals_without = without_filter.generate_signals(sample_ohlcv_data)

        # Without filter should generate more or equal signals
        assert len(signals_without) >= len(signals_with), \
            "Removing filter should increase signals"

    def test_trend_filter(self, sample_ohlcv_data):
        """Test trend direction filter"""
        # With trend filter
        with_filter = EnhancedMomentumStrategy(
            symbols=['TEST'],
            enable_trend_filter=True,
            min_signal_quality=SignalQuality.WEAK
        )

        # Without trend filter
        without_filter = EnhancedMomentumStrategy(
            symbols=['TEST'],
            enable_trend_filter=False,
            min_signal_quality=SignalQuality.WEAK
        )

        signals_with = with_filter.generate_signals(sample_ohlcv_data)
        signals_without = without_filter.generate_signals(sample_ohlcv_data)

        # Without filter should generate more or equal signals
        assert len(signals_without) >= len(signals_with), \
            "Removing trend filter should increase signals"


class TestRiskManagement:
    """Test risk management functionality"""

    def test_stop_loss_calculation(self, strategy, sample_ohlcv_data):
        """Test stop loss calculation using ATR"""
        data = strategy.calculate_indicators(sample_ohlcv_data)
        row = data.iloc[-1]

        stop_loss, take_profit, _ = strategy.calculate_risk_metrics(
            entry_price=row['close'],
            signal_type=SignalType.BUY,
            atr=row['atr']
        )

        # For BUY, stop loss should be below entry
        assert stop_loss < row['close'], "Stop loss should be below entry for BUY"

        # Stop loss should be approximately ATR * multiple away
        expected_distance = row['atr'] * strategy.risk_params.stop_loss_atr_multiple
        actual_distance = row['close'] - stop_loss

        assert abs(actual_distance - expected_distance) < 0.01, \
            "Stop loss distance incorrect"

    def test_risk_reward_ratio(self, strategy, sample_ohlcv_data):
        """Test risk/reward ratio calculation"""
        data = strategy.calculate_indicators(sample_ohlcv_data)
        row = data.iloc[-1]

        stop_loss, take_profit, risk_reward = strategy.calculate_risk_metrics(
            entry_price=row['close'],
            signal_type=SignalType.BUY,
            atr=row['atr']
        )

        # Calculate expected ratio
        risk = row['close'] - stop_loss
        reward = take_profit - row['close']
        expected_ratio = reward / risk

        assert abs(risk_reward - expected_ratio) < 0.01, \
            "Risk/reward ratio calculation incorrect"

    def test_risk_reward_filter(self, sample_ohlcv_data):
        """Test that signals are filtered by minimum risk/reward"""
        # Strategy with high minimum R:R
        high_rr_strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            risk_params=RiskParameters(min_risk_reward_ratio=3.0),
            min_signal_quality=SignalQuality.WEAK
        )

        # Strategy with low minimum R:R
        low_rr_strategy = EnhancedMomentumStrategy(
            symbols=['TEST'],
            risk_params=RiskParameters(min_risk_reward_ratio=1.0),
            min_signal_quality=SignalQuality.WEAK
        )

        high_signals = high_rr_strategy.generate_signals(sample_ohlcv_data)
        low_signals = low_rr_strategy.generate_signals(sample_ohlcv_data)

        # Lower threshold should allow more signals
        assert len(low_signals) >= len(high_signals), \
            "Lower R:R threshold should generate more signals"


class TestPositionSizing:
    """Test position sizing calculations"""

    def test_position_size_respects_max_limit(self, strategy):
        """Test that position size doesn't exceed maximum"""
        from src.strategies.base import Signal

        account_value = 100000
        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.BUY,
            price=100.0,
            confidence=1.0,
            metadata={
                'stop_loss': 95.0,
                'take_profit': 110.0
            }
        )

        position_size = strategy.calculate_position_size(signal, account_value)
        max_shares = (account_value * strategy.risk_params.max_position_size) / signal.price

        assert position_size <= max_shares, \
            "Position size exceeds maximum allowed"

    def test_position_size_scales_with_confidence(self, strategy):
        """Test that position size scales with signal confidence"""
        from src.strategies.base import Signal

        account_value = 100000

        # High confidence signal
        high_conf_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.BUY,
            price=100.0,
            confidence=0.9,
            metadata={'stop_loss': 95.0}
        )

        # Low confidence signal
        low_conf_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.BUY,
            price=100.0,
            confidence=0.5,
            metadata={'stop_loss': 95.0}
        )

        high_size = strategy.calculate_position_size(high_conf_signal, account_value)
        low_size = strategy.calculate_position_size(low_conf_signal, account_value)

        assert high_size > low_size, \
            "Higher confidence should result in larger position"

    def test_position_size_risk_calculation(self, strategy):
        """Test that position size properly accounts for risk per trade"""
        from src.strategies.base import Signal

        account_value = 100000
        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.BUY,
            price=100.0,
            confidence=1.0,
            metadata={'stop_loss': 95.0}
        )

        position_size = strategy.calculate_position_size(signal, account_value)

        # Calculate maximum risk
        risk_per_share = signal.price - signal.metadata['stop_loss']
        total_risk = position_size * risk_per_share

        # Risk should not exceed risk_per_trade percentage
        max_risk = account_value * strategy.risk_params.risk_per_trade

        assert total_risk <= max_risk * 1.1, \
            f"Total risk (${total_risk:.2f}) exceeds maximum (${max_risk:.2f})"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_dataframe(self, strategy):
        """Test handling of empty data"""
        empty_data = pd.DataFrame()
        signals = strategy.generate_signals(empty_data)
        assert len(signals) == 0, "Empty data should generate no signals"

    def test_insufficient_data(self, strategy):
        """Test handling of insufficient data"""
        small_data = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102],
            'volume': [1000000, 1100000]
        })
        small_data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(small_data)
        assert len(signals) == 0, "Insufficient data should generate no signals"

    def test_missing_columns(self, strategy):
        """Test handling of missing required columns"""
        bad_data = pd.DataFrame({
            'close': [100, 101, 102]
        })

        signals = strategy.generate_signals(bad_data)
        assert len(signals) == 0, "Invalid data should generate no signals"

    def test_nan_values(self, strategy, sample_ohlcv_data):
        """Test handling of NaN values in data"""
        data = sample_ohlcv_data.copy()
        data.loc[data.index[50], 'close'] = np.nan

        # Should not raise exception
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list), "Should handle NaN values gracefully"


class TestPerformanceTracking:
    """Test performance tracking and metrics"""

    def test_signal_counting(self, strategy, sample_ohlcv_data):
        """Test that signals are counted correctly"""
        initial_count = strategy.total_signals_generated
        signals = strategy.generate_signals(sample_ohlcv_data)

        assert strategy.total_signals_generated == initial_count + len(signals), \
            "Signal count incorrect"

    def test_quality_distribution_tracking(self, strategy, sample_ohlcv_data):
        """Test that signal quality distribution is tracked"""
        strategy.generate_signals(sample_ohlcv_data)

        total_by_quality = sum(strategy.signals_by_quality.values())
        assert total_by_quality == strategy.total_signals_generated, \
            "Quality distribution doesn't match total signals"

    def test_performance_summary(self, strategy, sample_ohlcv_data):
        """Test performance summary generation"""
        strategy.generate_signals(sample_ohlcv_data)
        summary = strategy.get_performance_summary()

        required_keys = [
            'total_signals', 'signals_by_quality',
            'current_positions', 'risk_parameters'
        ]
        for key in required_keys:
            assert key in summary, f"Missing key in summary: {key}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
