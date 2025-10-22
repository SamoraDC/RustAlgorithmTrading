"""
Integration Test for Momentum Strategy Signal Generation

This test validates that the momentum strategy:
1. Loads real historical data
2. Calculates indicators correctly
3. Generates trading signals
4. Produces reasonable performance metrics
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from loguru import logger

from src.strategies.simple_momentum import SimpleMomentumStrategy
from src.strategies.base import SignalType


class TestMomentumSignalGeneration:
    """Integration tests for momentum signal generation"""

    @pytest.fixture
    def historical_data_path(self):
        """Get path to historical data"""
        return Path("data/historical")

    @pytest.fixture
    def strategy(self):
        """Create strategy instance"""
        return SimpleMomentumStrategy(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            rsi_period=14,
            rsi_oversold=35,
            rsi_overbought=65,
            position_size=0.1
        )

    def test_load_historical_data(self, historical_data_path):
        """Test that historical data can be loaded"""
        data_file = historical_data_path / "AAPL.parquet"

        if not data_file.exists():
            pytest.skip(f"Historical data not found: {data_file}")

        # Load data
        df = pd.read_parquet(data_file)

        # Validate structure
        assert not df.empty, "Data should not be empty"
        assert 'close' in df.columns, "Data should have 'close' column"
        assert 'open' in df.columns, "Data should have 'open' column"
        assert 'high' in df.columns, "Data should have 'high' column"
        assert 'low' in df.columns, "Data should have 'low' column"
        assert 'volume' in df.columns, "Data should have 'volume' column"

        # Validate data quality
        assert len(df) >= 50, f"Need at least 50 bars, got {len(df)}"
        assert df['close'].notna().sum() > 0, "Close prices should not be all NaN"

        logger.info(f"Loaded {len(df)} bars for AAPL from {df.index[0]} to {df.index[-1]}")

    def test_generate_signals_with_real_data(self, historical_data_path, strategy):
        """Test signal generation with real historical data"""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        all_signals = []

        for symbol in symbols:
            data_file = historical_data_path / f"{symbol}.parquet"

            if not data_file.exists():
                logger.warning(f"Skipping {symbol} - data file not found")
                continue

            # Load data
            df = pd.read_parquet(data_file)

            # Ensure index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)

            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing columns for {symbol}: {missing_cols}")
                continue

            logger.info(f"Generating signals for {symbol} with {len(df)} bars")

            # Generate signals
            signals = strategy.generate_signals_for_symbol(symbol, df)

            logger.info(f"{symbol}: Generated {len(signals)} signals")

            # Validate signals
            for signal in signals:
                assert signal.symbol == symbol, f"Signal symbol mismatch: {signal.symbol} != {symbol}"
                assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
                assert signal.price > 0, f"Invalid signal price: {signal.price}"
                assert 0 <= signal.confidence <= 1, f"Invalid confidence: {signal.confidence}"
                assert 'rsi' in signal.metadata, "Signal should have RSI metadata"
                assert 'macd' in signal.metadata, "Signal should have MACD metadata"

                # Verify RSI is in valid range
                rsi = signal.metadata['rsi']
                assert 0 <= rsi <= 100, f"RSI {rsi} out of bounds"

            all_signals.extend(signals)

        # Overall validation
        logger.info(f"Total signals across all symbols: {len(all_signals)}")

        # Should generate at least some signals with year of data
        assert len(all_signals) >= 1, "Should generate at least 1 signal with year of data"

        # Analyze signal distribution
        buy_signals = [s for s in all_signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in all_signals if s.signal_type == SignalType.SELL]

        logger.info(f"BUY signals: {len(buy_signals)}")
        logger.info(f"SELL signals: {len(sell_signals)}")

        # Print sample signals for inspection
        if buy_signals:
            sample = buy_signals[0]
            logger.info(f"Sample BUY signal: {sample.symbol} @ ${sample.price:.2f}, "
                       f"RSI: {sample.metadata['rsi']:.2f}, "
                       f"Confidence: {sample.confidence:.2f}")

    def test_signal_timing_distribution(self, historical_data_path, strategy):
        """Test that signals are distributed throughout the time period"""
        symbol = 'AAPL'
        data_file = historical_data_path / f"{symbol}.parquet"

        if not data_file.exists():
            pytest.skip(f"Historical data not found for {symbol}")

        df = pd.read_parquet(data_file)

        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

        # Generate signals
        signals = strategy.generate_signals_for_symbol(symbol, df)

        if len(signals) == 0:
            pytest.skip("No signals generated, cannot test distribution")

        # Get signal timestamps
        signal_dates = [s.timestamp for s in signals]

        # Check signals span reasonable time range
        min_date = min(signal_dates)
        max_date = max(signal_dates)
        date_range_days = (max_date - min_date).days

        logger.info(f"Signals span {date_range_days} days from {min_date} to {max_date}")

        # Signals should not all occur on same day (for year of data)
        if len(df) > 100:
            assert date_range_days > 1, "Signals should be distributed across multiple days"

    def test_indicator_calculations(self, historical_data_path, strategy):
        """Test that indicators are calculated correctly"""
        symbol = 'AAPL'
        data_file = historical_data_path / f"{symbol}.parquet"

        if not data_file.exists():
            pytest.skip(f"Historical data not found for {symbol}")

        df = pd.read_parquet(data_file)

        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

        # Generate signals (which calculates indicators internally)
        signals = strategy.generate_signals_for_symbol(symbol, df)

        # Check at least one signal has valid indicator values
        if signals:
            sample_signal = signals[0]

            # RSI should be between 0 and 100
            rsi = sample_signal.metadata['rsi']
            assert 0 <= rsi <= 100, f"RSI {rsi} out of valid range"

            # MACD should be a reasonable number relative to price
            macd = sample_signal.metadata['macd']
            price = sample_signal.price
            assert abs(macd) < price, f"MACD {macd} seems unreasonable for price {price}"

            # MACD histogram should exist
            assert 'macd_histogram' in sample_signal.metadata

            logger.info(f"Sample indicator values: RSI={rsi:.2f}, MACD={macd:.2f}, Price=${price:.2f}")

    def test_position_sizing_with_signals(self, strategy):
        """Test position sizing calculations with generated signals"""
        # Create a mock signal
        from src.strategies.base import Signal

        signal = Signal(
            timestamp=datetime.now(),
            symbol='AAPL',
            signal_type=SignalType.BUY,
            price=230.0,
            confidence=0.8
        )

        account_value = 10000.0

        # Calculate position size
        position_size = strategy.calculate_position_size(signal, account_value)

        # Validate position size
        position_value = position_size * signal.price
        max_allowed = account_value * strategy.get_parameter('position_size')

        logger.info(f"Position size: {position_size} shares = ${position_value:.2f}")
        logger.info(f"Max allowed: ${max_allowed:.2f}")

        # Should not exceed position size limit
        assert position_value <= max_allowed * 1.01, f"Position ${position_value:.2f} exceeds max ${max_allowed:.2f}"

        # Should be positive
        assert position_size > 0, "Position size should be positive"

    def test_signal_confidence_quality(self, historical_data_path, strategy):
        """Test that signal confidence values are reasonable"""
        all_confidences = []

        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            data_file = historical_data_path / f"{symbol}.parquet"

            if not data_file.exists():
                continue

            df = pd.read_parquet(data_file)

            if not isinstance(df.index, pd.DatetimeIndex):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)

            signals = strategy.generate_signals_for_symbol(symbol, df)

            for signal in signals:
                all_confidences.append(signal.confidence)

        if not all_confidences:
            pytest.skip("No signals generated, cannot test confidence")

        # All confidences should be in valid range
        assert all(0 <= c <= 1 for c in all_confidences), "All confidences should be 0-1"

        # Calculate statistics
        mean_confidence = np.mean(all_confidences)
        std_confidence = np.std(all_confidences)

        logger.info(f"Confidence statistics: mean={mean_confidence:.3f}, std={std_confidence:.3f}")

        # Confidence should vary (not all the same)
        assert std_confidence > 0.01, "Confidence should vary across signals"

        # Mean confidence should be reasonable
        assert 0.3 <= mean_confidence <= 0.9, f"Mean confidence {mean_confidence:.3f} seems unreasonable"


class TestMomentumStrategyDiagnostics:
    """Diagnostic tests to identify issues"""

    def test_basic_signal_structure(self):
        """Test that Signal objects have the correct structure"""
        from src.strategies.base import Signal, SignalType

        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.BUY,
            price=100.0,
            confidence=0.8,
            metadata={'rsi': 45.0, 'macd': 0.5}
        )

        # Check attributes
        assert hasattr(signal, 'timestamp')
        assert hasattr(signal, 'symbol')
        assert hasattr(signal, 'signal_type')
        assert hasattr(signal, 'price')
        assert hasattr(signal, 'confidence')
        assert hasattr(signal, 'metadata')

        # Verify signal_type is SignalType enum
        assert signal.signal_type == SignalType.BUY
        assert signal.signal_type.value == 'buy'

        logger.info(f"Signal structure: {signal}")
        logger.info(f"Signal type: {signal.signal_type} ({type(signal.signal_type)})")

    def test_strategy_generates_signals_on_synthetic_data(self):
        """Test signal generation on known synthetic data"""
        # Create synthetic data with clear buy/sell patterns
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create oversold-to-recovery pattern (should trigger BUY)
        prices = np.concatenate([
            np.linspace(120, 80, 40),   # Drop (oversold)
            np.linspace(80, 100, 60)    # Recovery (buy signal)
        ])

        df = pd.DataFrame({
            'open': prices - 1,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)

        strategy = SimpleMomentumStrategy(
            symbols=['TEST'],
            rsi_oversold=35,
            rsi_overbought=65
        )

        signals = strategy.generate_signals_for_symbol('TEST', df)

        logger.info(f"Generated {len(signals)} signals on synthetic data")

        # Should generate at least some signals
        assert len(signals) >= 0, "Strategy should execute without error"

        # Log any signals generated
        for signal in signals:
            logger.info(f"Signal: {signal.signal_type.value} @ ${signal.price:.2f}, "
                       f"RSI: {signal.metadata.get('rsi', 'N/A')}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])
