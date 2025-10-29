"""
Diagnostic test for signal execution bug

This test isolates the signal generation and execution flow to identify
why backtests show 0% win rate with "Generated 0 signals" logs.

Bug hypothesis: EXIT signals are being generated without corresponding ENTRY signals,
or there's a mismatch in signal type conversion between Strategy and Engine.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversion
from src.backtesting.portfolio_handler import PortfolioHandler, FixedAmountSizer
from src.models.events import SignalEvent


class TestSignalExecutionBug:
    """Test suite to diagnose signal execution bug"""

    @pytest.fixture
    def sample_data(self):
        """Generate sample market data with clear trend"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create strong uptrend with clear momentum signals
        base_price = 100
        prices = base_price + np.cumsum(np.random.randn(100) * 0.5 + 0.2)  # Upward drift

        df = pd.DataFrame({
            'open': prices - 0.5,
            'high': prices + 1.0,
            'low': prices - 1.0,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)

        df.attrs['symbol'] = 'TEST'
        return df

    def test_momentum_signal_generation(self, sample_data):
        """Test if MomentumStrategy generates signals correctly"""
        strategy = MomentumStrategy(
            rsi_period=14,
            ema_fast=12,
            ema_slow=26,
            macd_signal=9,
            position_size=0.15
        )

        # Generate signals
        signals = strategy.generate_signals(sample_data)

        logger.info(f"Generated {len(signals)} signals for momentum strategy")

        # Diagnostic: Count signal types
        signal_types = {}
        for signal in signals:
            sig_type = signal.signal_type.value
            signal_types[sig_type] = signal_types.get(sig_type, 0) + 1

        logger.info(f"Signal breakdown: {signal_types}")

        # Assertions
        assert len(signals) > 0, "No signals generated - this is the bug!"

        # Check if EXIT signals exist without ENTRY signals
        entry_signals = signal_types.get('LONG', 0) + signal_types.get('SHORT', 0)
        exit_signals = signal_types.get('EXIT', 0)

        logger.info(f"Entry signals: {entry_signals}, Exit signals: {exit_signals}")

        # EXIT signals should not exceed ENTRY signals
        assert exit_signals <= entry_signals, \
            f"More EXIT ({exit_signals}) than ENTRY ({entry_signals}) signals - state management bug!"

    def test_mean_reversion_signal_generation(self, sample_data):
        """Test if MeanReversion strategy generates signals correctly"""
        strategy = MeanReversion(
            bb_period=20,
            bb_std=2.0,
            position_size=0.15
        )

        # Generate signals
        signals = strategy.generate_signals_for_symbol('TEST', sample_data)

        logger.info(f"Generated {len(signals)} signals for mean reversion strategy")

        # Diagnostic: Count signal types
        signal_types = {}
        for signal in signals:
            sig_type = signal.signal_type.value
            signal_types[sig_type] = signal_types.get(sig_type, 0) + 1

        logger.info(f"Signal breakdown: {signal_types}")

        # Assertions
        assert len(signals) > 0, "No signals generated - this is the bug!"

        # Check if EXIT signals exist without ENTRY signals
        entry_signals = signal_types.get('LONG', 0) + signal_types.get('SHORT', 0)
        exit_signals = signal_types.get('EXIT', 0)

        logger.info(f"Entry signals: {entry_signals}, Exit signals: {exit_signals}")

        # EXIT signals should not exceed ENTRY signals
        assert exit_signals <= entry_signals, \
            f"More EXIT ({exit_signals}) than ENTRY ({entry_signals}) signals - state management bug!"

    def test_signal_event_conversion(self):
        """Test SignalEvent creation from Strategy Signal"""
        from src.strategies.base import Signal, SignalType

        # Create Strategy Signal
        strategy_signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=0.8
        )

        # Convert to SignalEvent (as done in engine.py:194-201)
        signal_event = SignalEvent(
            timestamp=strategy_signal.timestamp,
            symbol=strategy_signal.symbol,
            signal_type=strategy_signal.signal_type.value,  # This is the key conversion
            strength=strategy_signal.confidence,
            strategy_id='TestStrategy'
        )

        logger.info(f"Strategy signal type: {strategy_signal.signal_type.value}")
        logger.info(f"SignalEvent signal type: {signal_event.signal_type}")

        # Verify conversion
        assert signal_event.signal_type == 'LONG'
        assert signal_event.strength == 0.8

    def test_portfolio_handler_exit_signal_without_position(self):
        """Test if portfolio_handler correctly handles EXIT signals without open positions"""
        portfolio = PortfolioHandler(
            initial_capital=100000.0,
            position_sizer=FixedAmountSizer(10000.0)
        )

        # Create EXIT signal when no position exists
        exit_signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='EXIT',
            strength=1.0,
            strategy_id='TestStrategy'
        )

        # Generate orders from EXIT signal (should return empty list)
        orders = portfolio.generate_orders(exit_signal)

        logger.info(f"Orders generated from EXIT signal (no position): {len(orders)}")

        # Should be empty - this is CORRECT behavior
        assert len(orders) == 0, "EXIT signal without position should not generate orders"

    def test_signal_state_tracking(self, sample_data):
        """Test if strategy correctly tracks active positions"""
        strategy = MomentumStrategy(
            rsi_period=14,
            ema_fast=12,
            ema_slow=26,
            macd_signal=9
        )

        # Generate signals
        signals = strategy.generate_signals(sample_data)

        logger.info(f"Active positions after signal generation: {strategy.active_positions}")

        # Check position state consistency
        entry_count = sum(1 for s in signals if s.signal_type.value in ['LONG', 'SHORT'])
        exit_count = sum(1 for s in signals if s.signal_type.value == 'EXIT')

        # After all signals processed, positions should be empty if exits match entries
        # OR have 1 position if final entry has no corresponding exit
        assert len(strategy.active_positions) <= 1, \
            f"Position tracking error: {len(strategy.active_positions)} positions still active"

        logger.info(f"Entry count: {entry_count}, Exit count: {exit_count}")
        logger.info(f"Net positions: {entry_count - exit_count}")

    def test_signal_filtering_conditions(self, sample_data):
        """Test if signals are being filtered out by technical conditions"""
        strategy = MomentumStrategy(
            rsi_period=14,
            ema_fast=12,
            ema_slow=26,
            macd_signal=9,
            macd_histogram_threshold=0.0005,  # Relaxed threshold
            volume_confirmation=False,  # Disable volume filter
            use_trailing_stop=False  # Simplify exit logic
        )

        # Generate signals with relaxed conditions
        signals = strategy.generate_signals(sample_data)

        logger.info(f"Signals with relaxed conditions: {len(signals)}")

        # Should generate more signals with relaxed conditions
        assert len(signals) > 0, "Even with relaxed conditions, no signals generated!"

        # Now test with strict conditions
        strategy_strict = MomentumStrategy(
            rsi_period=14,
            ema_fast=12,
            ema_slow=26,
            macd_signal=9,
            macd_histogram_threshold=0.01,  # Very strict
            volume_confirmation=True,  # Enable volume filter
            volume_multiplier=5.0  # Extremely high volume requirement
        )

        signals_strict = strategy_strict.generate_signals(sample_data)

        logger.info(f"Signals with strict conditions: {len(signals_strict)}")

        # Strict conditions should generate fewer signals
        assert len(signals_strict) <= len(signals), \
            "Strict conditions generated more signals than relaxed - logic error!"

    def test_minimum_holding_period_bug(self, sample_data):
        """Test if minimum holding period is blocking all exits"""
        strategy = MomentumStrategy(
            rsi_period=14,
            ema_fast=12,
            ema_slow=26,
            macd_signal=9
        )

        # Generate signals
        signals = strategy.generate_signals(sample_data)

        # Filter for positions that had entries
        entries = [s for s in signals if s.signal_type.value in ['LONG', 'SHORT']]
        exits = [s for s in signals if s.signal_type.value == 'EXIT']

        logger.info(f"Entries: {len(entries)}, Exits: {len(exits)}")

        # If entries > 0 but exits == 0, minimum holding period might be too strict
        if len(entries) > 0 and len(exits) == 0:
            logger.warning("⚠️ Entries without exits - possible minimum holding period bug")

            # Check if last entry is still within holding period
            if len(entries) > 0:
                last_entry = entries[-1]
                last_bar_time = sample_data.index[-1]
                bars_since_entry = len(sample_data[sample_data.index > last_entry.timestamp])

                min_hold_period = strategy.get_parameter('min_holding_period', 10)
                logger.info(f"Last entry: {last_entry.timestamp}, Bars since: {bars_since_entry}, Min hold: {min_hold_period}")

                if bars_since_entry < min_hold_period:
                    logger.info("✅ Position still in minimum holding period - this is expected")
                else:
                    logger.error("❌ Position exceeded holding period but no exit - BUG!")
                    assert False, "Position held beyond minimum period without exit signal"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
