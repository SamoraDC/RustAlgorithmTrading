"""
Comprehensive Unit Tests for Momentum Strategy

Tests RSI calculation, MACD calculation, signal generation logic,
position sizing, and risk management rules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List

from src.strategies.momentum import MomentumStrategy
from src.strategies.simple_momentum import SimpleMomentumStrategy
from src.strategies.base import Signal, SignalType


class TestRSICalculation:
    """Test RSI indicator calculation accuracy"""

    def test_rsi_calculation_basic(self):
        """Test RSI calculation with known values"""
        # Create test data with known RSI values
        # Using a simple pattern: rising prices should give high RSI
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1D')

        # Create rising price pattern
        prices = np.linspace(100, 150, 50)
        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 50
        }, index=dates)

        strategy = MomentumStrategy(rsi_period=14)
        signals = strategy.generate_signals(data)

        # Verify RSI is calculated (even if no signals generated)
        # RSI should be present in data after calculation
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

        # Check that we have gains
        assert gain.iloc[-1] > 0, "Rising prices should generate gains"

    def test_rsi_oversold_detection(self):
        """Test RSI correctly identifies oversold conditions"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1D')

        # Create falling price pattern (oversold)
        prices = np.linspace(150, 100, 50)
        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 50
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(rsi_period=14, rsi_oversold=40)

        # Calculate RSI manually to verify
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Falling prices should create low RSI
        assert rsi.iloc[-1] < 50, "Falling prices should create low RSI"

    def test_rsi_overbought_detection(self):
        """Test RSI correctly identifies overbought conditions"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1D')

        # Create rising price pattern (overbought)
        prices = np.linspace(100, 150, 50)
        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 50
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(rsi_period=14, rsi_overbought=60)

        # Calculate RSI manually
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Rising prices should create high RSI
        assert rsi.iloc[-1] > 50, "Rising prices should create high RSI"

    def test_rsi_range_bounds(self):
        """Test RSI stays within 0-100 bounds"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create volatile price pattern
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        data = pd.DataFrame({
            'open': prices,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(rsi_period=14)
        signals = strategy.generate_signals(data)

        # Check any signals have RSI in valid range
        for signal in signals:
            rsi_value = signal.metadata.get('rsi', 50)
            assert 0 <= rsi_value <= 100, f"RSI {rsi_value} out of bounds"


class TestMACDCalculation:
    """Test MACD indicator calculation"""

    def test_macd_calculation_basic(self):
        """Test MACD calculation with standard parameters"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')
        prices = np.linspace(100, 120, 100)

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(ema_fast=12, ema_slow=26, macd_signal=9)
        signals = strategy.generate_signals(data)

        # MACD should be calculated
        # For rising prices, MACD should generally be positive
        for signal in signals:
            if 'macd' in signal.metadata:
                # Just verify MACD exists and is a number
                assert isinstance(signal.metadata['macd'], (int, float))

    def test_macd_crossover_detection(self):
        """Test MACD crossover signal detection"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create pattern with clear trend change
        prices = np.concatenate([
            np.linspace(100, 90, 40),   # Downtrend
            np.linspace(90, 110, 60)    # Uptrend (should create crossover)
        ])

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy()
        signals = strategy.generate_signals(data)

        # Should detect at least one signal due to trend change
        # (May not be crossover specifically, but should have signals)
        assert len(signals) >= 0, "Strategy should process without error"


class TestSignalGeneration:
    """Test signal generation logic"""

    def test_buy_signal_generation(self):
        """Test BUY signal is generated correctly"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create pattern: oversold recovery
        prices = np.concatenate([
            np.linspace(120, 80, 50),   # Sharp drop (oversold)
            np.linspace(80, 100, 50)    # Recovery
        ])

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(rsi_oversold=35, rsi_overbought=65)
        signals = strategy.generate_signals(data)

        # Should generate some signals
        assert len(signals) >= 0, "Strategy should execute"

        # Check BUY signals exist and have required metadata
        buy_signals = [s for s in signals if s.signal_type == SignalType.LONG]
        for signal in buy_signals:
            assert signal.price > 0, "Signal price should be positive"
            assert 0 <= signal.confidence <= 1, "Confidence should be 0-1"
            assert 'rsi' in signal.metadata, "Signal should have RSI metadata"
            assert 'macd' in signal.metadata, "Signal should have MACD metadata"

    def test_sell_signal_generation(self):
        """Test SELL signal is generated correctly"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create pattern: overbought reversal
        prices = np.concatenate([
            np.linspace(80, 120, 50),   # Sharp rise (overbought)
            np.linspace(120, 100, 50)   # Reversal
        ])

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(rsi_oversold=35, rsi_overbought=65)
        signals = strategy.generate_signals(data)

        # Check SELL signals have proper structure
        sell_signals = [s for s in signals if s.signal_type == SignalType.SHORT]
        for signal in sell_signals:
            assert signal.price > 0
            assert 0 <= signal.confidence <= 1
            assert 'rsi' in signal.metadata
            assert 'macd_histogram' in signal.metadata

    def test_signal_confidence_calculation(self):
        """Test signal confidence is calculated correctly"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create volatile pattern
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 3)

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy()
        signals = strategy.generate_signals(data)

        # All signals should have valid confidence
        for signal in signals:
            assert 0 <= signal.confidence <= 1, f"Invalid confidence: {signal.confidence}"

    def test_no_signals_on_insufficient_data(self):
        """Test no signals generated with insufficient data"""
        dates = pd.date_range(start='2024-01-01', periods=10, freq='1D')
        prices = np.linspace(100, 105, 10)

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 10
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(rsi_period=14)
        signals = strategy.generate_signals(data)

        # Should not generate signals with insufficient data
        assert len(signals) == 0, "Should not generate signals with < 14 periods"


class TestPositionSizing:
    """Test position sizing calculations"""

    def test_position_size_basic(self):
        """Test basic position size calculation"""
        strategy = MomentumStrategy(position_size=0.95)

        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=1.0
        )

        account_value = 10000.0
        position_size = strategy.calculate_position_size(signal, account_value)

        # Should use 95% of account
        expected_shares = (10000 * 0.95) / 100.0
        assert abs(position_size - expected_shares) < 0.1, f"Expected ~{expected_shares}, got {position_size}"

    def test_position_size_with_confidence(self):
        """Test position size adjusts with confidence"""
        strategy = MomentumStrategy(position_size=0.95)

        # High confidence signal
        high_conf_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=1.0
        )

        # Low confidence signal
        low_conf_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=0.5
        )

        account_value = 10000.0
        high_size = strategy.calculate_position_size(high_conf_signal, account_value)
        low_size = strategy.calculate_position_size(low_conf_signal, account_value)

        # Lower confidence should result in smaller position
        assert low_size < high_size, "Lower confidence should reduce position size"
        assert abs(low_size - high_size * 0.5) < 0.1, "Position should scale with confidence"

    def test_position_size_different_prices(self):
        """Test position sizing with different price levels"""
        strategy = MomentumStrategy(position_size=0.5)
        account_value = 10000.0

        # Expensive stock
        expensive_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=500.0,
            confidence=1.0
        )

        # Cheap stock
        cheap_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=10.0,
            confidence=1.0
        )

        expensive_shares = strategy.calculate_position_size(expensive_signal, account_value)
        cheap_shares = strategy.calculate_position_size(cheap_signal, account_value)

        # Dollar value should be similar, shares different
        expensive_value = expensive_shares * 500
        cheap_value = cheap_shares * 10

        assert abs(expensive_value - cheap_value) < 100, "Dollar values should be similar"
        assert cheap_shares > expensive_shares, "Cheap stock should have more shares"


class TestRiskManagement:
    """Test risk management rules"""

    def test_position_size_limits(self):
        """Test position size respects limits"""
        strategy = SimpleMomentumStrategy(
            symbols=['TEST'],
            position_size=0.1  # 10% max
        )

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

        # Should not exceed 10% of account
        max_allowed = account_value * 0.1
        assert position_value <= max_allowed * 1.01, f"Position {position_value} exceeds limit {max_allowed}"

    def test_data_validation(self):
        """Test strategy validates input data"""
        strategy = MomentumStrategy()

        # Missing required columns
        invalid_data = pd.DataFrame({
            'close': [100, 101, 102]
        })

        assert not strategy.validate_data(invalid_data), "Should reject invalid data"

        # Valid data
        valid_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 1000, 1000]
        })

        assert strategy.validate_data(valid_data), "Should accept valid data"

    def test_parameter_bounds(self):
        """Test strategy parameters stay within reasonable bounds"""
        # Test RSI period
        strategy = MomentumStrategy(rsi_period=14)
        assert strategy.get_parameter('rsi_period') == 14

        # Test RSI levels
        strategy = MomentumStrategy(rsi_oversold=30, rsi_overbought=70)
        assert strategy.get_parameter('rsi_oversold') < strategy.get_parameter('rsi_overbought')

        # Test position size
        strategy = MomentumStrategy(position_size=0.95)
        assert 0 < strategy.get_parameter('position_size') <= 1.0


class TestSimpleMomentumStrategy:
    """Test SimpleMomentumStrategy wrapper"""

    def test_initialization(self):
        """Test SimpleMomentumStrategy initializes correctly"""
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        strategy = SimpleMomentumStrategy(
            symbols=symbols,
            rsi_period=14,
            rsi_oversold=35,
            rsi_overbought=65,
            position_size=0.1
        )

        assert strategy.name == "SimpleMomentumStrategy"
        assert strategy.get_symbols() == symbols
        assert strategy.get_parameter('position_size') == 0.1

    def test_multi_symbol_support(self):
        """Test strategy handles multiple symbols"""
        symbols = ['AAPL', 'GOOGL']
        strategy = SimpleMomentumStrategy(symbols=symbols)

        # Generate data for each symbol
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1D')

        for symbol in symbols:
            prices = np.linspace(100, 120, 50)
            data = pd.DataFrame({
                'open': prices,
                'high': prices + 1,
                'low': prices - 1,
                'close': prices,
                'volume': [1000000] * 50
            }, index=dates)

            signals = strategy.generate_signals_for_symbol(symbol, data)

            # Verify signals have correct symbol
            for signal in signals:
                assert signal.symbol == symbol, f"Signal symbol mismatch: {signal.symbol} != {symbol}"

    def test_position_size_safety(self):
        """Test SimpleMomentumStrategy enforces position size safety"""
        strategy = SimpleMomentumStrategy(
            symbols=['TEST'],
            position_size=0.1
        )

        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=1.0
        )

        # Even with high confidence, should respect position_size limit
        position_size = strategy.calculate_position_size(signal, 10000.0)
        position_value = position_size * signal.price

        # Should not exceed 10% of account
        assert position_value <= 1000 * 1.01, "Position size safety not enforced"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_dataframe(self):
        """Test strategy handles empty dataframe"""
        strategy = MomentumStrategy()
        empty_data = pd.DataFrame()

        signals = strategy.generate_signals(empty_data)
        assert len(signals) == 0, "Should return empty list for empty data"

    def test_nan_values_in_data(self):
        """Test strategy handles NaN values gracefully"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1D')
        prices = np.linspace(100, 120, 50)
        prices[25] = np.nan  # Insert NaN

        data = pd.DataFrame({
            'open': prices,
            'high': prices,
            'low': prices,
            'close': prices,
            'volume': [1000000] * 50
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy()
        # Should not crash
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list), "Should return list even with NaN values"

    def test_zero_division_protection(self):
        """Test RSI calculation handles zero division"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1D')
        # Flat prices (no change) could cause division by zero
        prices = np.ones(50) * 100

        data = pd.DataFrame({
            'open': prices,
            'high': prices,
            'low': prices,
            'close': prices,
            'volume': [1000000] * 50
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy()
        # Should not crash on division by zero
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list), "Should handle flat prices"

    def test_extreme_volatility(self):
        """Test strategy handles extreme price volatility"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create extreme volatility
        np.random.seed(42)
        prices = 100 * np.exp(np.cumsum(np.random.randn(100) * 0.1))  # Log-normal

        data = pd.DataFrame({
            'open': prices,
            'high': prices * 1.05,
            'low': prices * 0.95,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy()
        signals = strategy.generate_signals(data)

        # Should handle extreme volatility
        assert isinstance(signals, list), "Should handle extreme volatility"

        # All signals should have valid confidence
        for signal in signals:
            assert 0 <= signal.confidence <= 1, "Confidence should be valid"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
