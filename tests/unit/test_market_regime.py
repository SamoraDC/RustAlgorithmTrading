"""
Unit tests for market regime detection module
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils.market_regime import (
    MarketRegimeDetector,
    MarketRegime,
    select_strategy_for_regime,
    get_regime_display_name
)


@pytest.fixture
def sample_trending_up_data():
    """Generate sample data for trending up market"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    # Create uptrend with noise
    trend = np.linspace(100, 150, 100)
    noise = np.random.normal(0, 2, 100)
    close = trend + noise

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close - np.random.uniform(0.5, 2, 100),
        'high': close + np.random.uniform(0.5, 3, 100),
        'low': close - np.random.uniform(0.5, 3, 100),
        'close': close,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    data.set_index('timestamp', inplace=True)
    return data


@pytest.fixture
def sample_trending_down_data():
    """Generate sample data for trending down market"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    # Create downtrend with noise
    trend = np.linspace(150, 100, 100)
    noise = np.random.normal(0, 2, 100)
    close = trend + noise

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close + np.random.uniform(0.5, 2, 100),
        'high': close + np.random.uniform(0.5, 3, 100),
        'low': close - np.random.uniform(0.5, 3, 100),
        'close': close,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    data.set_index('timestamp', inplace=True)
    return data


@pytest.fixture
def sample_ranging_data():
    """Generate sample data for ranging market"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    # Create sideways movement
    close = 100 + np.random.normal(0, 3, 100)

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close - np.random.uniform(0.5, 1, 100),
        'high': close + np.random.uniform(0.5, 2, 100),
        'low': close - np.random.uniform(0.5, 2, 100),
        'close': close,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    data.set_index('timestamp', inplace=True)
    return data


@pytest.fixture
def sample_volatile_data():
    """Generate sample data for volatile market"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    # Create high volatility movement
    close = 100 + np.random.normal(0, 10, 100)

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close - np.random.uniform(2, 8, 100),
        'high': close + np.random.uniform(2, 10, 100),
        'low': close - np.random.uniform(2, 10, 100),
        'close': close,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    data.set_index('timestamp', inplace=True)
    return data


class TestMarketRegimeDetector:
    """Test MarketRegimeDetector class"""

    def test_initialization(self):
        """Test detector initialization"""
        detector = MarketRegimeDetector()
        assert detector.adx_period == 14
        assert detector.atr_period == 14
        assert detector.adx_trending_threshold == 25.0
        assert detector.adx_ranging_threshold == 20.0
        assert detector.atr_volatility_multiplier == 1.5

    def test_custom_parameters(self):
        """Test detector with custom parameters"""
        detector = MarketRegimeDetector(
            adx_period=20,
            atr_period=20,
            adx_trending_threshold=30.0,
            adx_ranging_threshold=15.0,
            atr_volatility_multiplier=2.0
        )
        assert detector.adx_period == 20
        assert detector.atr_period == 20
        assert detector.adx_trending_threshold == 30.0
        assert detector.adx_ranging_threshold == 15.0
        assert detector.atr_volatility_multiplier == 2.0

    def test_calculate_atr(self, sample_trending_up_data):
        """Test ATR calculation"""
        detector = MarketRegimeDetector()
        atr = detector.calculate_atr(sample_trending_up_data)

        assert isinstance(atr, pd.Series)
        assert len(atr) == len(sample_trending_up_data)
        assert not atr.iloc[-20:].isna().all()  # Should have values after warmup
        assert (atr.dropna() > 0).all()  # ATR should be positive

    def test_calculate_adx(self, sample_trending_up_data):
        """Test ADX calculation"""
        detector = MarketRegimeDetector()
        adx = detector.calculate_adx(sample_trending_up_data)

        assert isinstance(adx, pd.Series)
        assert len(adx) == len(sample_trending_up_data)
        assert not adx.iloc[-20:].isna().all()  # Should have values after warmup
        assert ((adx.dropna() >= 0) & (adx.dropna() <= 100)).all()  # ADX range 0-100

    def test_calculate_trend_direction_uptrend(self, sample_trending_up_data):
        """Test trend direction for uptrend"""
        detector = MarketRegimeDetector()
        trend = detector.calculate_trend_direction(sample_trending_up_data)

        assert isinstance(trend, pd.Series)
        assert len(trend) == len(sample_trending_up_data)

        # Most recent values should indicate uptrend (+1)
        recent_trend = trend.iloc[-20:].dropna()
        uptrend_pct = (recent_trend == 1).sum() / len(recent_trend)
        assert uptrend_pct > 0.5  # More than 50% should be uptrend

    def test_calculate_trend_direction_downtrend(self, sample_trending_down_data):
        """Test trend direction for downtrend"""
        detector = MarketRegimeDetector()
        trend = detector.calculate_trend_direction(sample_trending_down_data)

        # Most recent values should indicate downtrend (-1)
        recent_trend = trend.iloc[-20:].dropna()
        downtrend_pct = (recent_trend == -1).sum() / len(recent_trend)
        assert downtrend_pct > 0.5  # More than 50% should be downtrend

    def test_detect_regime_trending_up(self, sample_trending_up_data):
        """Test regime detection for trending up market"""
        detector = MarketRegimeDetector(
            adx_trending_threshold=20.0,  # Lower threshold for test data
        )
        regimes = detector.detect_regime(sample_trending_up_data)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_trending_up_data)

        # Check that we have some regime classifications
        non_unknown = regimes[regimes != MarketRegime.UNKNOWN]
        assert len(non_unknown) > 0

    def test_detect_regime_ranging(self, sample_ranging_data):
        """Test regime detection for ranging market"""
        detector = MarketRegimeDetector()
        regimes = detector.detect_regime(sample_ranging_data)

        # Should detect some ranging periods
        ranging_count = (regimes == MarketRegime.RANGING).sum()
        assert ranging_count > 0

    def test_detect_regime_volatile(self, sample_volatile_data):
        """Test regime detection for volatile market"""
        detector = MarketRegimeDetector(
            atr_volatility_multiplier=1.2  # Lower threshold to catch volatility
        )
        regimes = detector.detect_regime(sample_volatile_data)

        # Should detect some volatile periods
        volatile_regimes = [
            MarketRegime.VOLATILE_TRENDING_UP,
            MarketRegime.VOLATILE_TRENDING_DOWN,
            MarketRegime.VOLATILE_RANGING
        ]
        volatile_count = regimes.isin(volatile_regimes).sum()
        assert volatile_count > 0

    def test_get_regime_stats(self, sample_trending_up_data):
        """Test regime statistics calculation"""
        detector = MarketRegimeDetector()
        regimes = detector.detect_regime(sample_trending_up_data)
        stats = detector.get_regime_stats(regimes)

        assert isinstance(stats, dict)
        assert len(stats) == len(MarketRegime)

        # All percentages should sum to 100%
        total_pct = sum(stats.values())
        assert abs(total_pct - 100.0) < 0.01

        # All values should be between 0 and 100
        for pct in stats.values():
            assert 0 <= pct <= 100

    def test_get_current_regime(self, sample_trending_up_data):
        """Test getting current regime and indicators"""
        detector = MarketRegimeDetector()
        current_regime, indicators = detector.get_current_regime(sample_trending_up_data)

        assert isinstance(current_regime, MarketRegime)
        assert isinstance(indicators, dict)

        # Check indicator keys
        assert 'adx' in indicators
        assert 'atr' in indicators
        assert 'trend' in indicators
        assert 'close' in indicators

        # Check indicator values
        assert indicators['adx'] >= 0
        assert indicators['atr'] > 0
        assert indicators['trend'] in [-1, 0, 1]
        assert indicators['close'] > 0


class TestRegimeStrategySelection:
    """Test strategy selection based on regime"""

    def test_trending_up_strategy(self):
        """Test strategy config for trending up"""
        config = select_strategy_for_regime(MarketRegime.TRENDING_UP)

        assert config['strategy'] == 'momentum'
        assert config['direction'] == 'long_only'
        assert config['enabled'] is True
        assert config['stop_loss'] == 0.02
        assert config['position_size'] == 1.0

    def test_trending_down_strategy(self):
        """Test strategy config for trending down"""
        config = select_strategy_for_regime(MarketRegime.TRENDING_DOWN)

        assert config['strategy'] == 'momentum'
        assert config['direction'] == 'short_only'
        assert config['enabled'] is True
        assert config['stop_loss'] == 0.02

    def test_ranging_strategy(self):
        """Test strategy config for ranging market - DISABLED after Week 2 failure"""
        config = select_strategy_for_regime(MarketRegime.RANGING)

        # Mean reversion disabled due to Week 2 backtest: 0% win rate, -283% annual return
        assert config['strategy'] == 'hold'
        assert config['direction'] == 'neutral'
        assert config['enabled'] is False
        assert config['position_size'] == 0.0  # No position
        assert config['stop_loss'] == 0.03

    def test_volatile_trending_up_strategy(self):
        """Test strategy config for volatile trending up"""
        config = select_strategy_for_regime(MarketRegime.VOLATILE_TRENDING_UP)

        assert config['strategy'] == 'momentum'
        assert config['direction'] == 'long_only'
        assert config['enabled'] is True
        assert config['stop_loss'] == 0.05  # Wider stop
        assert config['position_size'] == 0.5  # Smaller position

    def test_volatile_trending_down_strategy(self):
        """Test strategy config for volatile trending down"""
        config = select_strategy_for_regime(MarketRegime.VOLATILE_TRENDING_DOWN)

        assert config['strategy'] == 'momentum'
        assert config['direction'] == 'short_only'
        assert config['enabled'] is True
        assert config['stop_loss'] == 0.05
        assert config['position_size'] == 0.5

    def test_volatile_ranging_strategy(self):
        """Test strategy config for volatile ranging"""
        config = select_strategy_for_regime(MarketRegime.VOLATILE_RANGING)

        assert config['strategy'] == 'hold'
        assert config['enabled'] is False

    def test_unknown_regime_strategy(self):
        """Test strategy config for unknown regime"""
        config = select_strategy_for_regime(MarketRegime.UNKNOWN)

        assert config['strategy'] == 'hold'
        assert config['enabled'] is False


class TestRegimeDisplayNames:
    """Test display name functions"""

    def test_all_regimes_have_display_names(self):
        """Test that all regimes have display names"""
        for regime in MarketRegime:
            display_name = get_regime_display_name(regime)
            assert isinstance(display_name, str)
            assert len(display_name) > 0

    def test_trending_up_display(self):
        """Test trending up display name"""
        name = get_regime_display_name(MarketRegime.TRENDING_UP)
        assert "Trending Up" in name or "📈" in name

    def test_trending_down_display(self):
        """Test trending down display name"""
        name = get_regime_display_name(MarketRegime.TRENDING_DOWN)
        assert "Trending Down" in name or "📉" in name

    def test_ranging_display(self):
        """Test ranging display name"""
        name = get_regime_display_name(MarketRegime.RANGING)
        assert "Ranging" in name or "↔" in name

    def test_volatile_display(self):
        """Test volatile regimes have volatility indicator"""
        name = get_regime_display_name(MarketRegime.VOLATILE_TRENDING_UP)
        assert "Volatile" in name or "⚡" in name


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_insufficient_data(self):
        """Test with insufficient data"""
        dates = pd.date_range(start='2024-01-01', periods=10, freq='1H')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [100] * 10,
            'high': [101] * 10,
            'low': [99] * 10,
            'close': [100] * 10,
            'volume': [1000] * 10
        })
        data.set_index('timestamp', inplace=True)

        detector = MarketRegimeDetector()
        regimes = detector.detect_regime(data)

        # Should return series with mostly NaN or UNKNOWN
        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(data)

    def test_missing_columns(self):
        """Test with missing required columns"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.uniform(90, 110, 50)
        })
        data.set_index('timestamp', inplace=True)

        detector = MarketRegimeDetector()

        # Should handle missing columns gracefully or raise appropriate error
        with pytest.raises((KeyError, ValueError)):
            regimes = detector.detect_regime(data)

    def test_zero_volatility(self):
        """Test with zero volatility (flat prices)"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [100] * 50,
            'high': [100] * 50,
            'low': [100] * 50,
            'close': [100] * 50,
            'volume': [1000] * 50
        })
        data.set_index('timestamp', inplace=True)

        detector = MarketRegimeDetector()
        regimes = detector.detect_regime(data)

        # Should handle zero volatility gracefully
        assert isinstance(regimes, pd.Series)

    def test_nan_values_in_data(self):
        """Test with NaN values in data"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        close = np.random.uniform(90, 110, 50)
        close[10:15] = np.nan  # Insert NaN values

        data = pd.DataFrame({
            'timestamp': dates,
            'open': close - 1,
            'high': close + 1,
            'low': close - 1,
            'close': close,
            'volume': [1000] * 50
        })
        data.set_index('timestamp', inplace=True)

        detector = MarketRegimeDetector()
        regimes = detector.detect_regime(data)

        # Should handle NaN values gracefully
        assert isinstance(regimes, pd.Series)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
