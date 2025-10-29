"""
Test Asymmetric Holding Period Logic

This test verifies that:
1. Stop-losses exit IMMEDIATELY (no holding period delay)
2. Take-profits require minimum holding period
3. Trailing stops exit immediately
4. Technical exits require minimum holding period

Expected Impact:
- Reduce average loss from -5.49% to -2.0%
- Faster response to adverse moves
- Better risk management
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.momentum import MomentumStrategy
from src.strategies.momentum_simplified import SimplifiedMomentumStrategy
from src.strategies.base import SignalType


def create_test_data(bars: int = 100, start_price: float = 100.0) -> pd.DataFrame:
    """Create test market data"""
    dates = pd.date_range(start='2024-01-01 09:30', periods=bars, freq='5min')

    data = pd.DataFrame({
        'timestamp': dates,
        'open': start_price,
        'high': start_price * 1.01,
        'low': start_price * 0.99,
        'close': start_price,
        'volume': 1000000,
    })
    data.set_index('timestamp', inplace=True)
    data.attrs['symbol'] = 'TEST'

    return data


class TestAsymmetricHoldingPeriod:
    """Test asymmetric holding period for stop-losses vs take-profits"""

    @pytest.mark.parametrize("strategy_class", [MomentumStrategy, SimplifiedMomentumStrategy])
    def test_immediate_stop_loss_no_delay(self, strategy_class):
        """
        CRITICAL TEST: Stop-loss should exit IMMEDIATELY without waiting for min_holding_period

        Scenario:
        - Entry at $100
        - Price drops to $98 (triggering 2% stop-loss)
        - bars_held = 3 (less than min_holding_period of 10)
        - Expected: IMMEDIATE EXIT (no delay)
        """
        strategy = strategy_class(
            min_holding_period=10,  # Require 10 bars hold
            stop_loss_pct=0.02,     # 2% stop-loss
            take_profit_pct=0.03,   # 3% take-profit
            use_trailing_stop=False  # Disable for this test
        )

        # Create data with price drop triggering stop-loss
        data = create_test_data(bars=50, start_price=100.0)

        # Simulate entry signal at bar 20
        entry_idx = 20
        data.loc[data.index[entry_idx], 'rsi'] = 55  # Above 50 for LONG entry

        # Simulate stop-loss trigger at bar 23 (3 bars later, less than min_holding_period)
        stop_loss_idx = 23
        data.loc[data.index[stop_loss_idx], 'close'] = 98.0  # -2% from entry

        # Manually create position to test exit logic
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': data.index[entry_idx],
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 98.0,
        }

        # Generate signals
        signals = strategy.generate_signals(data)

        # Filter exit signals
        exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]

        # Assertions
        assert len(exit_signals) > 0, "Should generate EXIT signal on stop-loss"

        stop_loss_exits = [s for s in exit_signals if s.metadata.get('exit_reason') == 'stop_loss']
        assert len(stop_loss_exits) > 0, "Should exit due to stop-loss"

        # Verify exit happened BEFORE min_holding_period
        exit_signal = stop_loss_exits[0]
        assert exit_signal.metadata['bars_held'] < 10, \
            f"Stop-loss should exit immediately (bars_held={exit_signal.metadata['bars_held']} < 10)"

        # Verify P&L is close to -2% (not -5%)
        assert exit_signal.metadata['pnl_pct'] >= -0.025, \
            f"Stop-loss should prevent large losses (P&L={exit_signal.metadata['pnl_pct']:.2%})"

    @pytest.mark.parametrize("strategy_class", [MomentumStrategy, SimplifiedMomentumStrategy])
    def test_delayed_take_profit_requires_holding_period(self, strategy_class):
        """
        TEST: Take-profit should REQUIRE minimum holding period before exit

        Scenario:
        - Entry at $100
        - Price rises to $103 (triggering 3% take-profit)
        - bars_held = 5 (less than min_holding_period of 10)
        - Expected: HOLD (wait for min_holding_period)
        """
        strategy = strategy_class(
            min_holding_period=10,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            use_trailing_stop=False
        )

        data = create_test_data(bars=50, start_price=100.0)

        # Entry at bar 20
        entry_idx = 20

        # Take-profit trigger at bar 25 (5 bars, less than min_holding)
        take_profit_idx = 25
        data.loc[data.index[take_profit_idx], 'close'] = 103.0  # +3% from entry

        # Manually create position
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': data.index[entry_idx],
            'type': 'long',
            'highest_price': 103.0,
            'lowest_price': 100.0,
        }

        signals = strategy.generate_signals(data)

        # At bar 25 (5 bars held), should NOT exit
        early_exits = [s for s in signals
                      if s.signal_type == SignalType.EXIT
                      and s.timestamp == data.index[take_profit_idx]
                      and s.metadata.get('exit_reason') == 'take_profit']

        assert len(early_exits) == 0, \
            "Take-profit should NOT exit before min_holding_period (5 < 10)"

    @pytest.mark.parametrize("strategy_class", [MomentumStrategy, SimplifiedMomentumStrategy])
    def test_immediate_catastrophic_loss(self, strategy_class):
        """
        TEST: Catastrophic loss (-5%) should exit IMMEDIATELY

        Scenario:
        - Entry at $100
        - Price crashes to $95 (-5%)
        - bars_held = 1
        - Expected: IMMEDIATE EXIT
        """
        strategy = strategy_class(
            min_holding_period=10,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            use_trailing_stop=False
        )

        data = create_test_data(bars=50, start_price=100.0)

        entry_idx = 20
        crash_idx = 21
        data.loc[data.index[crash_idx], 'close'] = 95.0  # -5% crash

        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': data.index[entry_idx],
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 95.0,
        }

        signals = strategy.generate_signals(data)

        catastrophic_exits = [s for s in signals
                             if s.signal_type == SignalType.EXIT
                             and s.metadata.get('exit_reason') == 'catastrophic_stop_loss']

        assert len(catastrophic_exits) > 0, "Should exit immediately on catastrophic loss"
        assert catastrophic_exits[0].metadata['bars_held'] == 1, \
            "Catastrophic loss should exit after just 1 bar"

    @pytest.mark.parametrize("strategy_class", [MomentumStrategy, SimplifiedMomentumStrategy])
    def test_trailing_stop_immediate_exit(self, strategy_class):
        """
        TEST: Trailing stop should exit IMMEDIATELY (risk management tool)

        Scenario:
        - Entry at $100
        - Price rises to $105 (highest_price)
        - Price drops to $103.425 (1.5% below peak)
        - bars_held = 4
        - Expected: IMMEDIATE EXIT via trailing stop
        """
        strategy = strategy_class(
            min_holding_period=10,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            use_trailing_stop=True,
            trailing_stop_pct=0.015  # 1.5% trailing
        )

        data = create_test_data(bars=50, start_price=100.0)

        entry_idx = 20
        peak_idx = 22
        trail_stop_idx = 24

        data.loc[data.index[peak_idx], 'close'] = 105.0
        data.loc[data.index[trail_stop_idx], 'close'] = 103.4  # 1.5% below peak

        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': data.index[entry_idx],
            'type': 'long',
            'highest_price': 105.0,
            'lowest_price': 100.0,
        }

        signals = strategy.generate_signals(data)

        trailing_exits = [s for s in signals
                         if s.signal_type == SignalType.EXIT
                         and s.metadata.get('exit_reason') == 'trailing_stop_loss']

        assert len(trailing_exits) > 0, "Should exit immediately on trailing stop"
        assert trailing_exits[0].metadata['bars_held'] < 10, \
            f"Trailing stop should exit before min_holding (bars={trailing_exits[0].metadata['bars_held']})"

    @pytest.mark.parametrize("strategy_class", [MomentumStrategy, SimplifiedMomentumStrategy])
    def test_technical_exit_requires_holding_period(self, strategy_class):
        """
        TEST: Technical exits (RSI/MACD reversal) should require holding period

        These are trend signals, not risk management, so they should respect holding period
        """
        strategy = strategy_class(
            min_holding_period=10,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            use_trailing_stop=False
        )

        data = create_test_data(bars=50, start_price=100.0)

        # Add indicator data for technical reversal
        data['rsi'] = 50.0
        data['macd'] = 0.0
        data['macd_signal'] = 0.0
        data['macd_histogram'] = 0.0

        entry_idx = 20
        reversal_idx = 25  # 5 bars, less than min

        # Simulate technical reversal at bar 25
        data.loc[data.index[reversal_idx], 'rsi'] = 45.0  # Below 50
        data.loc[data.index[reversal_idx], 'macd'] = -0.01
        data.loc[data.index[reversal_idx], 'macd_signal'] = 0.01
        data.loc[data.index[reversal_idx], 'macd_histogram'] = -0.002

        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': data.index[entry_idx],
            'type': 'long',
            'highest_price': 100.0,
            'lowest_price': 99.0,
        }

        signals = strategy.generate_signals(data)

        # Should NOT exit at bar 25 (technical signal before holding period)
        technical_exits = [s for s in signals
                          if s.signal_type == SignalType.EXIT
                          and s.timestamp == data.index[reversal_idx]
                          and s.metadata.get('exit_reason') == 'technical_reversal']

        assert len(technical_exits) == 0, \
            "Technical exits should wait for min_holding_period"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
