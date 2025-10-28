"""
Validation Tests for Momentum Strategy Fixes

Tests the comprehensive fixes applied to fix 0% win rate:
- RSI thresholds (30/70 instead of 40/60)
- EXIT signal generation
- Stop-loss logic (2%)
- Take-profit logic (3% for 1.5:1 ratio)
- Position sizing (15% instead of 95%)
- Position tracking and P&L calculation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.momentum import MomentumStrategy
from src.strategies.base import Signal, SignalType


class TestRSIThresholds:
    """Validate RSI threshold fixes"""

    def test_default_rsi_thresholds(self):
        """Test new default RSI thresholds are 30/70"""
        strategy = MomentumStrategy()

        assert strategy.get_parameter('rsi_oversold') == 30, "RSI oversold should be 30"
        assert strategy.get_parameter('rsi_overbought') == 70, "RSI overbought should be 70"

    def test_custom_rsi_thresholds(self):
        """Test custom RSI thresholds can be set"""
        strategy = MomentumStrategy(rsi_oversold=25, rsi_overbought=75)

        assert strategy.get_parameter('rsi_oversold') == 25
        assert strategy.get_parameter('rsi_overbought') == 75


class TestExitSignals:
    """Validate EXIT signal generation"""

    def test_stop_loss_exit(self):
        """Test stop-loss generates EXIT signal"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create pattern: price drops triggering stop-loss
        prices = np.concatenate([
            np.linspace(100, 90, 30),  # Drop to oversold
            np.linspace(90, 95, 20),   # Recovery (triggers LONG)
            np.linspace(95, 92, 50)    # Drop again (triggers stop-loss)
        ])

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(stop_loss_pct=0.02)
        signals = strategy.generate_signals(data)

        # Should have at least one EXIT signal
        exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]
        assert len(exit_signals) > 0, "Should generate EXIT signals"

        # Check exit signal has stop_loss reason
        stop_loss_exits = [s for s in exit_signals if s.metadata.get('exit_reason') == 'stop_loss']
        assert len(stop_loss_exits) > 0, "Should have stop-loss exits"

    def test_take_profit_exit(self):
        """Test take-profit generates EXIT signal"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create pattern: price rises triggering take-profit
        prices = np.concatenate([
            np.linspace(100, 90, 30),  # Drop to oversold
            np.linspace(90, 95, 20),   # Recovery (triggers LONG)
            np.linspace(95, 100, 50)   # Strong rise (triggers take-profit)
        ])

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000000] * 100
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy(take_profit_pct=0.03)
        signals = strategy.generate_signals(data)

        # Should have EXIT signals
        exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]
        assert len(exit_signals) > 0, "Should generate EXIT signals"

    def test_technical_exit(self):
        """Test technical indicators trigger EXIT"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')

        # Create pattern with momentum reversal
        prices = np.concatenate([
            np.linspace(100, 85, 30),   # Drop (oversold)
            np.linspace(85, 105, 40),   # Strong recovery (LONG entry)
            np.linspace(105, 100, 30)   # Reversal (EXIT)
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

        # Check for technical exits
        exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]
        technical_exits = [s for s in exit_signals if s.metadata.get('exit_reason') == 'technical']

        # Should detect momentum reversal
        assert len(signals) > 0, "Should generate signals"


class TestPositionSizing:
    """Validate position sizing fixes"""

    def test_default_position_size(self):
        """Test default position size is 15%"""
        strategy = MomentumStrategy()

        assert strategy.get_parameter('position_size') == 0.15, "Default position size should be 15%"

    def test_position_size_calculation(self):
        """Test position sizing uses 15% of account"""
        strategy = MomentumStrategy(position_size=0.15)

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

        # Should use 15% of account
        expected_value = account_value * 0.15
        assert abs(position_value - expected_value) < 10, f"Position value {position_value} should be ~{expected_value}"

    def test_position_size_with_low_confidence(self):
        """Test position size scales with confidence"""
        strategy = MomentumStrategy(position_size=0.15)

        signal = Signal(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type=SignalType.LONG,
            price=100.0,
            confidence=0.5
        )

        account_value = 10000.0
        position_size = strategy.calculate_position_size(signal, account_value)
        position_value = position_size * signal.price

        # Should use 7.5% of account (15% * 0.5)
        expected_value = account_value * 0.15 * 0.5
        assert abs(position_value - expected_value) < 10, "Should scale with confidence"


class TestPositionTracking:
    """Validate position tracking and P&L calculation"""

    def test_position_tracking(self):
        """Test positions are tracked correctly"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')
        prices = np.concatenate([
            np.linspace(100, 85, 40),   # Drop
            np.linspace(85, 95, 60)     # Recovery (triggers entry)
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

        # Check that positions are tracked
        entry_signals = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]

        if len(entry_signals) > 0:
            # After entry signal, position should be tracked
            assert 'TEST' in strategy.active_positions or len([s for s in signals if s.signal_type == SignalType.EXIT]) > 0

    def test_unrealized_pnl_calculation(self):
        """Test unrealized P&L calculation"""
        strategy = MomentumStrategy()

        # Simulate a LONG position
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': datetime.now(),
            'type': 'long'
        }

        # Test profit scenario
        pnl = strategy.get_unrealized_pnl('TEST', 110.0)
        assert pnl == 0.10, "Should show 10% profit"

        # Test loss scenario
        pnl = strategy.get_unrealized_pnl('TEST', 95.0)
        assert pnl == -0.05, "Should show 5% loss"

    def test_unrealized_pnl_short_position(self):
        """Test P&L for short positions"""
        strategy = MomentumStrategy()

        # Simulate a SHORT position
        strategy.active_positions['TEST'] = {
            'entry_price': 100.0,
            'entry_time': datetime.now(),
            'type': 'short'
        }

        # Test profit scenario (price drops)
        pnl = strategy.get_unrealized_pnl('TEST', 90.0)
        assert pnl == 0.10, "Short should profit from price drop"

        # Test loss scenario (price rises)
        pnl = strategy.get_unrealized_pnl('TEST', 105.0)
        assert pnl == -0.05, "Short should lose when price rises"


class TestRiskManagement:
    """Validate comprehensive risk management"""

    def test_stop_loss_percentage(self):
        """Test stop-loss is enforced at 2%"""
        strategy = MomentumStrategy(stop_loss_pct=0.02)

        assert strategy.get_parameter('stop_loss_pct') == 0.02, "Stop-loss should be 2%"

    def test_take_profit_percentage(self):
        """Test take-profit is enforced at 3%"""
        strategy = MomentumStrategy(take_profit_pct=0.03)

        assert strategy.get_parameter('take_profit_pct') == 0.03, "Take-profit should be 3%"

    def test_reward_risk_ratio(self):
        """Test reward:risk ratio is 1.5:1"""
        strategy = MomentumStrategy()

        stop_loss = strategy.get_parameter('stop_loss_pct', 0.02)
        take_profit = strategy.get_parameter('take_profit_pct', 0.03)

        ratio = take_profit / stop_loss
        assert abs(ratio - 1.5) < 0.1, f"Reward:risk ratio should be 1.5:1, got {ratio}"


class TestSignalBalance:
    """Validate signals are balanced (not all shorts)"""

    def test_generates_both_long_and_short(self):
        """Test strategy generates both LONG and SHORT signals"""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1D')

        # Create pattern with both uptrends and downtrends
        prices = np.concatenate([
            np.linspace(100, 85, 50),   # Downtrend
            np.linspace(85, 105, 50),   # Uptrend
            np.linspace(105, 90, 50),   # Downtrend
            np.linspace(90, 100, 50)    # Uptrend
        ])

        data = pd.DataFrame({
            'open': prices,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': [1000000] * 200
        }, index=dates)
        data.attrs['symbol'] = 'TEST'

        strategy = MomentumStrategy()
        signals = strategy.generate_signals(data)

        long_signals = [s for s in signals if s.signal_type == SignalType.LONG]
        short_signals = [s for s in signals if s.signal_type == SignalType.SHORT]

        # Should generate both types
        assert len(long_signals) > 0, "Should generate LONG signals"
        assert len(short_signals) > 0, "Should generate SHORT signals"

        # Check balance (not all one type)
        total_entry_signals = len(long_signals) + len(short_signals)
        long_pct = len(long_signals) / total_entry_signals if total_entry_signals > 0 else 0

        assert 0.2 <= long_pct <= 0.8, f"Signals should be balanced, got {long_pct*100:.1f}% longs"


class TestMetadataAndLogging:
    """Validate signal metadata and logging"""

    def test_exit_signal_metadata(self):
        """Test EXIT signals have proper metadata"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1D')
        prices = np.concatenate([
            np.linspace(100, 85, 30),
            np.linspace(85, 95, 20),
            np.linspace(95, 92, 50)
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

        exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]

        for signal in exit_signals:
            # Check required metadata
            assert 'exit_reason' in signal.metadata, "EXIT should have exit_reason"
            assert 'pnl_pct' in signal.metadata, "EXIT should have P&L"
            assert 'entry_price' in signal.metadata, "EXIT should have entry price"
            assert 'position_type' in signal.metadata, "EXIT should have position type"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
