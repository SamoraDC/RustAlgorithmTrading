"""
WEEK 3 PRIORITY 1 FIX: Test Immediate Stop-Loss Exit (Bypass Holding Period)

CRITICAL FINDING FROM WEEK 2:
- Current: Cannot exit for 10 bars (50 minutes) even when stop-loss hit
- Problem: Losses grow from -2% to -5.49% while waiting
- Expected fix impact: -5.49% → -2.0% average loss

This test validates that stop-losses trigger IMMEDIATELY without waiting for
the minimum holding period, while take-profits still require the holding period.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.momentum import MomentumStrategy
from src.strategies.momentum_simplified import SimplifiedMomentumStrategy
from src.strategies.base import SignalType


def create_test_data(
    num_bars: int = 100,
    initial_price: float = 100.0,
    trend: str = "flat"
) -> pd.DataFrame:
    """
    Create test market data with specific price movements

    Args:
        num_bars: Number of bars to generate
        initial_price: Starting price
        trend: Price trend ('up', 'down', 'flat', 'volatile')

    Returns:
        DataFrame with OHLCV data
    """
    timestamps = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')

    if trend == "up":
        prices = initial_price + np.cumsum(np.random.uniform(0.1, 0.5, num_bars))
    elif trend == "down":
        prices = initial_price - np.cumsum(np.random.uniform(0.1, 0.5, num_bars))
    elif trend == "volatile":
        prices = initial_price + np.cumsum(np.random.uniform(-1.0, 1.0, num_bars))
    else:  # flat
        prices = initial_price + np.random.uniform(-0.5, 0.5, num_bars)

    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.uniform(100000, 500000, num_bars)
    })
    data.set_index('timestamp', inplace=True)
    data.attrs['symbol'] = 'TEST'

    return data


class TestImmediateStopLossExit:
    """Test suite for Week 3 Priority 1 fix: Immediate stop-loss exit"""

    def test_stop_loss_bypasses_holding_period(self):
        """
        WEEK 3 TEST: Stop-loss triggers IMMEDIATELY (bypasses holding period)

        Setup:
        - Enter long position at $100
        - Price drops to $97.80 (-2.2%) after just 3 bars
        - min_holding_period = 10 bars

        Expected:
        - EXIT signal generated at bar 3 (stop-loss at -2%)
        - Does NOT wait for 10 bars
        - exit_reason = 'stop_loss'
        - holding_period_bypassed = True
        """
        strategy = MomentumStrategy(
            stop_loss_pct=0.02,  # 2% stop-loss
            take_profit_pct=0.03,  # 3% take-profit
            min_holding_period=10,  # Require 10 bars holding
            rsi_period=14,
            ema_fast=12,
            ema_slow=26,
            macd_signal=9,
            volume_confirmation=False  # Disable for test simplicity
        )

        # Create data: Entry at $100, then drop to $97.80 at bar 3
        num_bars = 50
        data = create_test_data(num_bars=num_bars, initial_price=100.0, trend="flat")

        # Simulate entry conditions (RSI > 55, MACD bullish)
        data.loc[data.index[30], 'close'] = 100.0  # Entry bar

        # Generate signals to trigger entry
        signals = strategy.generate_signals(data.iloc[:31])

        # Force an entry position for testing (simulate entry at bar 30)
        entry_time = data.index[30]
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': entry_time,
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 100.0
        }

        # Now simulate price drop to trigger stop-loss (after 3 bars)
        data.loc[data.index[33], 'close'] = 97.80  # -2.2% loss

        # Generate signals with stop-loss trigger
        exit_signals = strategy.generate_signals(data.iloc[30:35])

        # Find EXIT signals
        exit_exits = [s for s in exit_signals if s.signal_type == SignalType.EXIT]

        # ASSERTIONS for WEEK 3 FIX:
        assert len(exit_exits) > 0, "Stop-loss should trigger EXIT signal"

        exit_signal = exit_exits[0]
        assert exit_signal.metadata['exit_reason'] == 'stop_loss', \
            f"Exit reason should be 'stop_loss', got {exit_signal.metadata['exit_reason']}"

        bars_held = exit_signal.metadata['bars_held']
        assert bars_held < 10, \
            f"Stop-loss should trigger before min_holding_period (10 bars), got {bars_held} bars"

        # Week 3 specific metadata
        assert exit_signal.metadata.get('holding_period_bypassed') is True, \
            "Stop-loss should bypass holding period"

        pnl_pct = exit_signal.metadata['pnl_pct']
        assert pnl_pct <= -0.02, \
            f"P&L should be at or below -2% stop-loss, got {pnl_pct:.2%}"

        print(f"\n✅ WEEK 3 TEST PASSED: Stop-loss triggered at bar {bars_held} "
              f"(bypassed {10 - bars_held} bars) with {pnl_pct:.2%} loss")

    def test_take_profit_requires_holding_period(self):
        """
        WEEK 3 TEST: Take-profit REQUIRES holding period (asymmetric logic)

        Setup:
        - Enter long position at $100
        - Price rises to $103.20 (+3.2%) after just 3 bars
        - min_holding_period = 10 bars

        Expected:
        - NO EXIT signal at bar 3 (must wait for holding period)
        - EXIT signal generated at bar 10+ when take-profit reached
        - exit_reason = 'take_profit'
        - holding_period_bypassed = False
        """
        strategy = MomentumStrategy(
            stop_loss_pct=0.02,
            take_profit_pct=0.03,  # 3% take-profit
            min_holding_period=10,
            volume_confirmation=False
        )

        num_bars = 50
        data = create_test_data(num_bars=num_bars, initial_price=100.0, trend="up")

        # Force entry position
        entry_time = data.index[30]
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': entry_time,
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 100.0
        }

        # Price rises to +3.2% at bar 33 (3 bars after entry)
        data.loc[data.index[33], 'close'] = 103.20

        # Try to exit early (should be blocked)
        early_signals = strategy.generate_signals(data.iloc[30:35])
        early_exits = [s for s in early_signals if s.signal_type == SignalType.EXIT]

        assert len(early_exits) == 0, \
            "Take-profit should NOT trigger before holding period"

        # Now wait until bar 40 (10 bars held)
        data.loc[data.index[40], 'close'] = 103.20

        # Should trigger take-profit now
        late_signals = strategy.generate_signals(data.iloc[30:42])
        late_exits = [s for s in late_signals if s.signal_type == SignalType.EXIT]

        assert len(late_exits) > 0, \
            "Take-profit should trigger after holding period"

        exit_signal = late_exits[0]
        assert exit_signal.metadata['exit_reason'] == 'take_profit', \
            "Exit should be take-profit after holding period"

        bars_held = exit_signal.metadata['bars_held']
        assert bars_held >= 10, \
            f"Take-profit should only trigger after min_holding_period, got {bars_held} bars"

        print(f"\n✅ WEEK 3 TEST PASSED: Take-profit correctly enforced "
              f"holding period ({bars_held} bars)")

    def test_trailing_stop_bypasses_holding_period(self):
        """
        WEEK 3 TEST: Trailing stop triggers IMMEDIATELY (risk management)

        Setup:
        - Enter long at $100
        - Price rises to $102 (peak)
        - Price drops to $100.97 (1.5% below peak) after 5 bars
        - min_holding_period = 10 bars

        Expected:
        - EXIT signal at bar 5 (trailing stop triggered)
        - Does NOT wait for 10 bars
        - exit_reason = 'trailing_stop_loss'
        """
        strategy = MomentumStrategy(
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            min_holding_period=10,
            use_trailing_stop=True,
            trailing_stop_pct=0.015,  # 1.5% trailing stop
            volume_confirmation=False
        )

        num_bars = 50
        data = create_test_data(num_bars=num_bars, initial_price=100.0, trend="flat")

        # Force entry
        entry_time = data.index[30]
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': entry_time,
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 100.0
        }

        # Price rises to $102 (peak at bar 33)
        data.loc[data.index[33], 'close'] = 102.0

        # Update highest price
        signals = strategy.generate_signals(data.iloc[30:34])

        # Price drops to trigger trailing stop at bar 35
        data.loc[data.index[35], 'close'] = 100.47  # 1.5% below peak ($102 * 0.985)

        trailing_signals = strategy.generate_signals(data.iloc[30:37])
        trailing_exits = [s for s in trailing_signals if s.signal_type == SignalType.EXIT]

        assert len(trailing_exits) > 0, \
            "Trailing stop should trigger EXIT"

        exit_signal = trailing_exits[0]
        assert exit_signal.metadata['exit_reason'] == 'trailing_stop_loss', \
            f"Exit should be trailing stop, got {exit_signal.metadata['exit_reason']}"

        bars_held = exit_signal.metadata['bars_held']
        assert bars_held < 10, \
            f"Trailing stop should bypass holding period, got {bars_held} bars"

        print(f"\n✅ WEEK 3 TEST PASSED: Trailing stop triggered at bar {bars_held} "
              f"(bypassed holding period)")

    def test_catastrophic_loss_immediate_exit(self):
        """
        WEEK 3 TEST: Catastrophic loss (-5%) triggers immediate exit

        This is the most critical test - validates that extreme losses
        trigger immediate exit to prevent -5.49% average losses.
        """
        strategy = MomentumStrategy(
            stop_loss_pct=0.02,
            min_holding_period=10,
            volume_confirmation=False
        )

        num_bars = 50
        data = create_test_data(num_bars=num_bars, initial_price=100.0, trend="down")

        # Force entry
        entry_time = data.index[30]
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': entry_time,
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 100.0
        }

        # Simulate catastrophic drop to -5.2%
        data.loc[data.index[32], 'close'] = 94.80  # -5.2% loss after just 2 bars

        catastrophic_signals = strategy.generate_signals(data.iloc[30:34])
        catastrophic_exits = [s for s in catastrophic_signals if s.signal_type == SignalType.EXIT]

        assert len(catastrophic_exits) > 0, \
            "Catastrophic loss should trigger immediate EXIT"

        exit_signal = catastrophic_exits[0]
        assert exit_signal.metadata['exit_reason'] == 'catastrophic_stop_loss', \
            "Exit should be catastrophic stop-loss"

        bars_held = exit_signal.metadata['bars_held']
        assert bars_held < 10, \
            f"Catastrophic loss should bypass holding period, got {bars_held} bars"

        pnl_pct = exit_signal.metadata['pnl_pct']
        assert pnl_pct <= -0.05, \
            f"P&L should be <= -5%, got {pnl_pct:.2%}"

        print(f"\n✅ WEEK 3 TEST PASSED: Catastrophic loss triggered at bar {bars_held} "
              f"with {pnl_pct:.2%} loss (prevented -5.49% average)")

    def test_simplified_strategy_immediate_stops(self):
        """
        WEEK 3 TEST: Verify simplified strategy also has immediate stop-loss
        """
        strategy = SimplifiedMomentumStrategy(
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            min_holding_period=10,
            use_trailing_stop=True
        )

        num_bars = 50
        data = create_test_data(num_bars=num_bars, initial_price=100.0, trend="flat")

        # Force entry
        entry_time = data.index[30]
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': entry_time,
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 100.0
        }

        # Price drops to -2.2%
        data.loc[data.index[33], 'close'] = 97.80

        exit_signals = strategy.generate_signals(data.iloc[30:35])
        exits = [s for s in exit_signals if s.signal_type == SignalType.EXIT]

        assert len(exits) > 0, \
            "Simplified strategy should also have immediate stop-loss"

        exit_signal = exits[0]
        assert exit_signal.metadata['exit_reason'] == 'stop_loss'

        bars_held = exit_signal.metadata['bars_held']
        assert bars_held < 10, \
            f"Simplified strategy stop-loss should bypass holding period, got {bars_held} bars"

        print(f"\n✅ WEEK 3 TEST PASSED: Simplified strategy stop-loss triggered "
              f"at bar {bars_held}")


if __name__ == '__main__':
    """Run tests with pytest"""
    pytest.main([__file__, '-v', '--tb=short'])
