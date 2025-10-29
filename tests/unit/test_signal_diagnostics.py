"""
Comprehensive diagnostic tests for signal validation and debugging

Tests signal generation, validation, entry/exit matching, and position tracking
to identify root causes of 0% win rate issues.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversion
from src.strategies.base import SignalType


class TestSignalGeneration:
    """Test that strategies generate signals with proper configuration"""

    def test_momentum_generates_signals_with_relaxed_params(self):
        """Verify Momentum strategy generates >0 signals with relaxed parameters"""
        # Create strategy with PHASE 1 relaxed parameters
        strategy = MomentumStrategy(
            rsi_period=14,
            rsi_oversold=30,
            rsi_overbought=70,
            macd_histogram_threshold=0.0005,  # Relaxed threshold
            volume_confirmation=False,  # Disable volume filter initially
            use_trailing_stop=False,  # Disable for initial test
            use_atr_sizing=False,  # Disable for initial test
        )

        # Create synthetic data with clear momentum signals
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1D')
        n_bars = len(dates)

        # Create uptrend: price rises from 100 to 150
        prices = np.linspace(100, 150, n_bars)
        # Add some noise
        prices += np.random.normal(0, 2, n_bars)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, n_bars)
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        # Generate signals
        signals = strategy.generate_signals(data)

        # ASSERT: Strategy should generate at least 1 signal
        assert len(signals) > 0, (
            f"Momentum strategy generated {len(signals)} signals, expected >0. "
            f"This indicates signal generation is broken."
        )

        # Log signal details for debugging
        logger.info(f"✅ Momentum strategy generated {len(signals)} signals")
        for sig in signals:
            logger.info(
                f"  Signal: {sig.signal_type} @ ${sig.price:.2f} on {sig.timestamp}, "
                f"confidence={sig.confidence:.2f}"
            )

    def test_mean_reversion_generates_signals(self):
        """Verify Mean Reversion strategy generates >0 signals"""
        strategy = MeanReversion(
            bb_period=20,
            bb_std=2.0,
            position_size=0.15,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
        )

        # Create synthetic data with oscillating prices (perfect for mean reversion)
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1D')
        n_bars = len(dates)

        # Create oscillating price around 100 with amplitude 10
        time = np.arange(n_bars)
        prices = 100 + 10 * np.sin(time / 5)  # Oscillate with period ~31 days

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, n_bars)
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        # Generate signals
        signals = strategy.generate_signals(data)

        # ASSERT: Strategy should generate at least 1 signal
        assert len(signals) > 0, (
            f"Mean Reversion strategy generated {len(signals)} signals, expected >0. "
            f"This indicates signal generation is broken."
        )

        # Log signal details
        logger.info(f"✅ Mean Reversion strategy generated {len(signals)} signals")
        for sig in signals:
            logger.info(
                f"  Signal: {sig.signal_type} @ ${sig.price:.2f} on {sig.timestamp}, "
                f"confidence={sig.confidence:.2f}"
            )


class TestSignalTypeValidation:
    """Validate signal types are correct (LONG/SHORT/EXIT)"""

    def test_momentum_signal_types_are_valid(self):
        """Verify all Momentum signals have valid signal types"""
        strategy = MomentumStrategy(
            macd_histogram_threshold=0.0005,
            volume_confirmation=False,
            use_trailing_stop=False,
        )

        # Create uptrend data
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1D')
        prices = np.linspace(100, 150, len(dates))

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(data)

        # ASSERT: All signals should have valid types
        valid_types = [SignalType.LONG, SignalType.SHORT, SignalType.EXIT]
        for sig in signals:
            assert sig.signal_type in valid_types, (
                f"Invalid signal type: {sig.signal_type}, expected one of {valid_types}"
            )

        logger.info(f"✅ All {len(signals)} Momentum signals have valid types")

    def test_mean_reversion_signal_types_are_valid(self):
        """Verify all Mean Reversion signals have valid signal types"""
        strategy = MeanReversion()

        # Create oscillating data
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1D')
        time = np.arange(len(dates))
        prices = 100 + 10 * np.sin(time / 5)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(data)

        # ASSERT: All signals should have valid types
        valid_types = [SignalType.LONG, SignalType.SHORT, SignalType.EXIT]
        for sig in signals:
            assert sig.signal_type in valid_types, (
                f"Invalid signal type: {sig.signal_type}, expected one of {valid_types}"
            )

        logger.info(f"✅ All {len(signals)} Mean Reversion signals have valid types")


class TestEntryExitMatching:
    """Test that entry signals have corresponding exit signals"""

    def test_momentum_entries_have_exits(self):
        """Verify each LONG/SHORT entry has a corresponding EXIT signal"""
        strategy = MomentumStrategy(
            macd_histogram_threshold=0.0005,
            volume_confirmation=False,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            min_holding_period=5,  # Short period for testing
        )

        # Create trending data with reversal
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1D')
        n_bars = len(dates)

        # Uptrend followed by downtrend
        uptrend = np.linspace(100, 130, n_bars // 2)
        downtrend = np.linspace(130, 110, n_bars // 2)
        prices = np.concatenate([uptrend, downtrend])

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, n_bars)
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(data)

        # Count entry and exit signals
        entries = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
        exits = [s for s in signals if s.signal_type == SignalType.EXIT]

        logger.info(f"Momentum: {len(entries)} entries, {len(exits)} exits")

        # ASSERT: Should have at least some exits
        # Note: May not be 1:1 due to end of data, but should have exits
        if len(entries) > 0:
            assert len(exits) > 0, (
                f"Strategy generated {len(entries)} entries but {len(exits)} exits. "
                f"EXIT signals are missing!"
            )

            # Check that exits follow entries
            for exit_sig in exits:
                # Find prior entry
                prior_entries = [e for e in entries if e.timestamp < exit_sig.timestamp]
                assert len(prior_entries) > 0, (
                    f"EXIT signal at {exit_sig.timestamp} has no prior ENTRY signal"
                )

        logger.info(f"✅ Momentum entry/exit matching validated")

    def test_mean_reversion_entries_have_exits(self):
        """Verify each LONG/SHORT entry has a corresponding EXIT signal"""
        strategy = MeanReversion(
            bb_period=20,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
        )

        # Create oscillating data
        dates = pd.date_range(start='2024-01-01', end='2024-04-01', freq='1D')
        time = np.arange(len(dates))
        prices = 100 + 15 * np.sin(time / 10)  # Large amplitude for clear signals

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(data)

        # Count entry and exit signals
        entries = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
        exits = [s for s in signals if s.signal_type == SignalType.EXIT]

        logger.info(f"Mean Reversion: {len(entries)} entries, {len(exits)} exits")

        # ASSERT: Should have at least some exits
        if len(entries) > 0:
            assert len(exits) > 0, (
                f"Strategy generated {len(entries)} entries but {len(exits)} exits. "
                f"EXIT signals are missing!"
            )

            # Check that exits follow entries
            for exit_sig in exits:
                prior_entries = [e for e in entries if e.timestamp < exit_sig.timestamp]
                assert len(prior_entries) > 0, (
                    f"EXIT signal at {exit_sig.timestamp} has no prior ENTRY signal"
                )

        logger.info(f"✅ Mean Reversion entry/exit matching validated")


class TestPositionTrackingState:
    """Test that active_positions dictionary tracks positions correctly"""

    def test_momentum_position_tracking(self):
        """Verify Momentum strategy tracks positions in active_positions dict"""
        strategy = MomentumStrategy(
            macd_histogram_threshold=0.0005,
            volume_confirmation=False,
            min_holding_period=5,
        )

        # Create trending data
        dates = pd.date_range(start='2024-01-01', end='2024-02-01', freq='1D')
        prices = np.linspace(100, 120, len(dates))

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        # Initial state: no positions
        assert len(strategy.active_positions) == 0, "Should start with no positions"

        # Generate signals
        signals = strategy.generate_signals(data)

        # After signal generation, check position tracking
        logger.info(f"Active positions after signal generation: {strategy.active_positions}")

        # If we generated entry signals, position should be tracked
        entries = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
        exits = [s for s in signals if s.signal_type == SignalType.EXIT]

        if len(entries) > len(exits):
            # We have open positions
            assert 'TEST' in strategy.active_positions, (
                "Strategy generated entries but didn't track position in active_positions"
            )

            position = strategy.active_positions['TEST']
            assert 'entry_price' in position, "Position missing entry_price"
            assert 'entry_time' in position, "Position missing entry_time"
            assert 'type' in position, "Position missing type"

            logger.info(f"✅ Position tracked: {position}")
        else:
            # All positions closed
            assert 'TEST' not in strategy.active_positions or len(strategy.active_positions) == 0, (
                "All positions should be closed after matching entries and exits"
            )

    def test_mean_reversion_position_tracking(self):
        """Verify Mean Reversion strategy tracks positions correctly"""
        strategy = MeanReversion(bb_period=20)

        # Create oscillating data
        dates = pd.date_range(start='2024-01-01', end='2024-02-01', freq='1D')
        time = np.arange(len(dates))
        prices = 100 + 10 * np.sin(time / 5)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        # Initial state: no positions
        assert len(strategy.active_positions) == 0, "Should start with no positions"

        # Generate signals
        signals = strategy.generate_signals(data)

        # After signal generation, check position tracking
        logger.info(f"Active positions after signal generation: {strategy.active_positions}")

        entries = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
        exits = [s for s in signals if s.signal_type == SignalType.EXIT]

        if len(entries) > len(exits):
            # We have open positions
            assert 'TEST' in strategy.active_positions, (
                "Strategy generated entries but didn't track position in active_positions"
            )

            position = strategy.active_positions['TEST']
            assert 'entry_price' in position, "Position missing entry_price"
            assert 'entry_time' in position, "Position missing entry_time"
            assert 'type' in position, "Position missing type"

            logger.info(f"✅ Position tracked: {position}")


class TestSignalMetadata:
    """Test that signals contain required metadata"""

    def test_momentum_signal_metadata(self):
        """Verify Momentum signals have complete metadata"""
        strategy = MomentumStrategy(
            macd_histogram_threshold=0.0005,
            volume_confirmation=False,
        )

        dates = pd.date_range(start='2024-01-01', end='2024-02-01', freq='1D')
        prices = np.linspace(100, 120, len(dates))

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(data)

        if len(signals) > 0:
            for sig in signals:
                # Check basic fields
                assert sig.timestamp is not None, "Signal missing timestamp"
                assert sig.symbol is not None, "Signal missing symbol"
                assert sig.price > 0, "Signal price must be positive"
                assert 0 <= sig.confidence <= 1, "Confidence must be in [0, 1]"

                # Check metadata
                assert sig.metadata is not None, "Signal missing metadata"

                if sig.signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Entry signals should have indicators
                    assert 'rsi' in sig.metadata, "Entry signal missing RSI in metadata"
                    assert 'macd' in sig.metadata, "Entry signal missing MACD in metadata"

                if sig.signal_type == SignalType.EXIT:
                    # Exit signals should have exit_reason and pnl_pct
                    assert 'exit_reason' in sig.metadata, "Exit signal missing exit_reason"
                    assert 'pnl_pct' in sig.metadata, "Exit signal missing pnl_pct"
                    assert 'entry_price' in sig.metadata, "Exit signal missing entry_price"

            logger.info(f"✅ All {len(signals)} Momentum signals have complete metadata")

    def test_mean_reversion_signal_metadata(self):
        """Verify Mean Reversion signals have complete metadata"""
        strategy = MeanReversion(bb_period=20)

        dates = pd.date_range(start='2024-01-01', end='2024-02-01', freq='1D')
        time = np.arange(len(dates))
        prices = 100 + 10 * np.sin(time / 5)

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        })
        data.set_index('timestamp', inplace=True)
        data.attrs['symbol'] = 'TEST'

        signals = strategy.generate_signals(data)

        if len(signals) > 0:
            for sig in signals:
                # Check basic fields
                assert sig.timestamp is not None, "Signal missing timestamp"
                assert sig.symbol is not None, "Signal missing symbol"
                assert sig.price > 0, "Signal price must be positive"
                assert 0 <= sig.confidence <= 1, "Confidence must be in [0, 1]"

                # Check metadata
                assert sig.metadata is not None, "Signal missing metadata"

                if sig.signal_type in [SignalType.LONG, SignalType.SHORT]:
                    # Entry signals should have BB bands
                    assert 'sma_20' in sig.metadata, "Entry signal missing SMA in metadata"
                    assert 'upper_band' in sig.metadata, "Entry signal missing upper_band"
                    assert 'lower_band' in sig.metadata, "Entry signal missing lower_band"

                if sig.signal_type == SignalType.EXIT:
                    # Exit signals should have exit_reason and pnl_pct
                    assert 'exit_reason' in sig.metadata, "Exit signal missing exit_reason"
                    assert 'pnl_pct' in sig.metadata, "Exit signal missing pnl_pct"
                    assert 'entry_price' in sig.metadata, "Exit signal missing entry_price"

            logger.info(f"✅ All {len(signals)} Mean Reversion signals have complete metadata")


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s', '--tb=short'])
