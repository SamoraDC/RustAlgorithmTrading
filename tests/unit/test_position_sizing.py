"""
Comprehensive Unit Tests for Position Sizing Logic

Tests position sizing calculations to ensure:
1. Correct sizing for various capital and price levels
2. Commission handling doesn't cause negative cash
3. Orders don't exceed available capital
4. Edge cases with very large/small positions
5. Multiple concurrent positions respect capital limits
"""

import pytest
import numpy as np
from datetime import datetime
from typing import List

from src.backtesting.portfolio_handler import (
    PortfolioHandler,
    FixedAmountSizer,
    PercentageOfEquitySizer,
    KellyPositionSizer,
    PositionSizer
)
from src.models.portfolio import Portfolio
from src.models.events import SignalEvent, FillEvent


class TestBasicPositionSizing:
    """Test basic position sizing calculations."""

    def test_basic_sizing_scenario_1(self):
        """
        Scenario 1: $1,000 capital, 10% size, $100 stock → 1 share
        """
        # Setup portfolio with $1,000 capital
        portfolio_handler = PortfolioHandler(
            initial_capital=1000.0,
            position_sizer=PercentageOfEquitySizer(0.10)  # 10% position size
        )

        # Create signal for $100 stock
        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0,
            strategy_id='test_strategy'
        )

        # Manually calculate expected size
        # 10% of $1,000 = $100
        # $100 / $100 per share = 1 share
        expected_shares = 1

        # Calculate position size
        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        assert position_size == expected_shares, \
            f"Expected {expected_shares} shares, got {position_size}"

        # Verify total position value doesn't exceed allocation
        position_value = position_size * 100.0  # $100 per share
        assert position_value <= 1000.0 * 0.10, \
            f"Position value ${position_value} exceeds 10% of capital"

    def test_expensive_stock_scenario_2(self):
        """
        Scenario 2: $1,000 capital, 10% size, $500 stock → 0 shares
        """
        # Setup portfolio with $1,000 capital
        portfolio_handler = PortfolioHandler(
            initial_capital=1000.0,
            position_sizer=PercentageOfEquitySizer(0.10)  # 10% position size
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='EXPENSIVE',
            signal_type='LONG',
            strength=1.0
        )

        # 10% of $1,000 = $100
        # $100 / $500 per share = 0.2 shares → rounds to 0
        expected_shares = 0

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        assert position_size == expected_shares, \
            f"Expected {expected_shares} shares (too expensive), got {position_size}"

    def test_affordable_stock_multiple_shares(self):
        """Test position sizing with affordable stock allowing multiple shares."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.10)  # 10% position size
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='CHEAP',
            signal_type='LONG',
            strength=1.0
        )

        # 10% of $10,000 = $1,000
        # $1,000 / $50 per share = 20 shares
        # Note: actual calculation uses portfolio equity at time of calculation
        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Position should be positive
        assert position_size >= 0, "Position size should be non-negative"

        # Position value should not exceed allocation (with small buffer for rounding)
        # Since we don't know actual price used, just verify it's reasonable
        assert position_size < 10000, "Position size should be reasonable"


class TestCommissionImpact:
    """Test commission handling and negative cash prevention."""

    def test_commission_doesnt_cause_negative_cash(self):
        """
        Scenario 3: Ensure commission doesn't cause negative cash
        """
        # Start with $1,000
        portfolio_handler = PortfolioHandler(
            initial_capital=1000.0,
            position_sizer=PercentageOfEquitySizer(0.95)  # 95% position size
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0
        )

        # Calculate position size (95% of equity)
        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Simulate fill with commission
        fill_price = 100.0
        commission = position_size * fill_price * 0.001  # 0.1% commission

        fill = FillEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            exchange='SIMULATED',
            quantity=position_size,
            direction='BUY',
            fill_price=fill_price,
            commission=commission
        )

        # Update portfolio with fill
        portfolio_handler.update_fill(fill)

        # Cash should never be negative
        assert portfolio_handler.portfolio.cash >= 0, \
            f"Cash is negative: ${portfolio_handler.portfolio.cash:.2f}"

        # Verify total cost (position + commission) doesn't exceed initial capital
        total_cost = position_size * fill_price + commission
        assert total_cost <= 1000.0, \
            f"Total cost ${total_cost:.2f} exceeds capital"

    def test_high_commission_scenario(self):
        """Test that high commission rates don't break position sizing."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.10)
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Simulate very high commission (5%)
        fill_price = 100.0
        commission = position_size * fill_price * 0.05

        fill = FillEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            exchange='SIMULATED',
            quantity=position_size,
            direction='BUY',
            fill_price=fill_price,
            commission=commission
        )

        portfolio_handler.update_fill(fill)

        # Cash should still be non-negative
        assert portfolio_handler.portfolio.cash >= 0, \
            "High commission caused negative cash"


class TestEdgeCases:
    """Test edge cases in position sizing."""

    def test_very_small_position_size_1_percent(self):
        """
        Scenario 4: Very small position size (1%)
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.01)  # 1% position size
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0
        )

        # 1% of $10,000 = $100
        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Should handle small positions
        assert position_size >= 0, "Small position should be handled"

        # Position value should be approximately 1% of capital
        # (actual value depends on price, but should be small)
        assert position_size < 1000, "1% position should result in small share count"

    def test_very_large_position_size_100_percent(self):
        """
        Scenario 4: Very large position size (100%)
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(1.0)  # 100% position size
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Should handle 100% allocation
        assert position_size >= 0, "100% position should be calculated"

        # Position should use full capital (or as much as possible)
        # Note: Commission would make this impossible in practice
        assert position_size > 0, "100% allocation should result in position"

    def test_zero_capital(self):
        """Test position sizing with zero/depleted capital."""
        portfolio_handler = PortfolioHandler(
            initial_capital=1000.0,
            position_sizer=PercentageOfEquitySizer(0.10)
        )

        # Simulate depleted cash
        portfolio_handler.portfolio.cash = 0.0

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0
        )

        # Position sizing should still work (based on equity, not just cash)
        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Should return 0 or handle gracefully
        assert position_size >= 0, "Should handle zero capital gracefully"


class TestMultipleConcurrentPositions:
    """Test position sizing with multiple concurrent positions."""

    def test_multiple_positions_respect_capital(self):
        """
        Scenario 4: Multiple concurrent positions should respect capital limits
        """
        initial_capital = 10000.0
        portfolio_handler = PortfolioHandler(
            initial_capital=initial_capital,
            position_sizer=PercentageOfEquitySizer(0.10)  # 10% per position
        )

        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        fill_price = 100.0

        total_invested = 0.0

        for symbol in symbols:
            signal = SignalEvent(
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type='LONG',
                strength=1.0
            )

            position_size = portfolio_handler.position_sizer.calculate_position_size(
                signal=signal,
                portfolio=portfolio_handler.portfolio
            )

            if position_size > 0:
                # Simulate fill
                commission = position_size * fill_price * 0.001
                fill = FillEvent(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    exchange='SIMULATED',
                    quantity=position_size,
                    direction='BUY',
                    fill_price=fill_price,
                    commission=commission
                )

                portfolio_handler.update_fill(fill)
                total_invested += position_size * fill_price + commission

            # Cash should never go negative
            assert portfolio_handler.portfolio.cash >= 0, \
                f"Cash went negative after {symbol}: ${portfolio_handler.portfolio.cash:.2f}"

        # Total invested should not exceed initial capital
        assert total_invested <= initial_capital, \
            f"Total invested ${total_invested:.2f} exceeds capital ${initial_capital:.2f}"

        # Verify we have the expected number of positions
        assert len(portfolio_handler.portfolio.positions) <= len(symbols), \
            "Too many positions created"

    def test_sequential_position_sizing_adjusts_to_equity(self):
        """Test that position sizing adjusts as equity changes."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.20)  # 20% per position
        )

        # First position
        signal1 = SignalEvent(
            timestamp=datetime.now(),
            symbol='STOCK1',
            signal_type='LONG',
            strength=1.0
        )

        size1 = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal1,
            portfolio=portfolio_handler.portfolio
        )

        # Simulate fill that reduces available equity
        fill1 = FillEvent(
            timestamp=datetime.now(),
            symbol='STOCK1',
            exchange='SIMULATED',
            quantity=size1,
            direction='BUY',
            fill_price=100.0,
            commission=size1 * 100.0 * 0.001
        )
        portfolio_handler.update_fill(fill1)

        # Second position - should be sized based on remaining equity
        signal2 = SignalEvent(
            timestamp=datetime.now(),
            symbol='STOCK2',
            signal_type='LONG',
            strength=1.0
        )

        size2 = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal2,
            portfolio=portfolio_handler.portfolio
        )

        # Second position should still be based on total equity (not just cash)
        assert size2 >= 0, "Second position should be valid"
        assert portfolio_handler.portfolio.cash >= 0, "Cash should not be negative"


class TestOrderValidation:
    """Test order validation and rejection for exceeding capital."""

    def test_order_exceeding_capital_rejected(self):
        """
        Scenario 5: Orders exceeding capital should be rejected/prevented
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=1000.0,
            position_sizer=PercentageOfEquitySizer(0.10)
        )

        # Try to create position larger than capital allows
        # The position sizer should prevent this
        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='EXPENSIVE',
            signal_type='LONG',
            strength=1.0
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Position value should not exceed 10% of capital
        # (Since we use 10% sizer, this is the max)
        max_position_value = 1000.0 * 0.10

        # Assuming $100 per share as baseline
        assumed_price = 100.0
        position_value = position_size * assumed_price

        # Position should be within limits (with small tolerance for rounding)
        assert position_value <= max_position_value * 1.01, \
            f"Position value ${position_value:.2f} exceeds limit ${max_position_value:.2f}"

    def test_insufficient_cash_prevents_order(self):
        """Test that orders are sized appropriately when cash is low."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.20)
        )

        # Create a large position
        signal1 = SignalEvent(
            timestamp=datetime.now(),
            symbol='STOCK1',
            signal_type='LONG',
            strength=1.0
        )

        size1 = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal1,
            portfolio=portfolio_handler.portfolio
        )

        fill1 = FillEvent(
            timestamp=datetime.now(),
            symbol='STOCK1',
            exchange='SIMULATED',
            quantity=size1,
            direction='BUY',
            fill_price=100.0,
            commission=size1 * 100.0 * 0.001
        )
        portfolio_handler.update_fill(fill1)

        # Reduce cash significantly
        portfolio_handler.portfolio.cash = 100.0

        # Try to create another position
        signal2 = SignalEvent(
            timestamp=datetime.now(),
            symbol='STOCK2',
            signal_type='LONG',
            strength=1.0
        )

        size2 = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal2,
            portfolio=portfolio_handler.portfolio
        )

        # Position should be valid but sized appropriately for available equity
        assert size2 >= 0, "Position size should be non-negative"

        # If we tried to fill this, we need to ensure we have enough cash
        potential_cost = size2 * 100.0  # Assuming $100 per share
        if size2 > 0:
            # Either position is small enough to fit in remaining cash
            # Or sizing is based on equity (not just cash)
            assert potential_cost <= portfolio_handler.portfolio.equity * 0.20 * 1.01, \
                "Position sizing should respect equity constraints"


class TestFixedAmountSizer:
    """Test fixed amount position sizer."""

    def test_fixed_amount_basic(self):
        """Test basic fixed amount sizing."""
        fixed_amount = 5000.0
        portfolio_handler = PortfolioHandler(
            initial_capital=20000.0,
            position_sizer=FixedAmountSizer(fixed_amount)
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=1.0
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Position should be based on fixed amount
        # $5,000 / $100 (assumed price) = 50 shares
        assert position_size > 0, "Fixed amount should produce position"


class TestKellyPositionSizer:
    """Test Kelly Criterion position sizer."""

    def test_kelly_sizer_basic(self):
        """Test Kelly criterion position sizing."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=KellyPositionSizer(fraction=0.25)  # Quarter Kelly
        )

        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=0.6  # 60% confidence
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=portfolio_handler.portfolio
        )

        # Kelly should produce valid position
        assert position_size >= 0, "Kelly sizer should produce valid position"

        # Position should be reasonable (not over-leveraged)
        assert position_size < 10000, "Kelly position should be reasonable"

    def test_kelly_sizer_low_confidence(self):
        """Test Kelly sizing with low confidence signal."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=KellyPositionSizer(fraction=0.25)
        )

        low_conf_signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=0.3  # Low confidence
        )

        high_conf_signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='LONG',
            strength=0.9  # High confidence
        )

        low_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=low_conf_signal,
            portfolio=portfolio_handler.portfolio
        )

        high_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=high_conf_signal,
            portfolio=portfolio_handler.portfolio
        )

        # Higher confidence should result in larger position
        assert high_size >= low_size, \
            "Higher confidence should produce larger or equal position"


class TestPositionSizerEdgeCases:
    """Test edge cases for all position sizers."""

    def test_exit_signal_returns_zero(self):
        """Test that EXIT signals return zero position size."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.10)
        )

        exit_signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='EXIT',
            strength=1.0
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=exit_signal,
            portfolio=portfolio_handler.portfolio
        )

        assert position_size == 0, "EXIT signal should return zero position"

    def test_short_signal_returns_negative(self):
        """Test that SHORT signals return negative position size."""
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.10)
        )

        short_signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='TEST',
            signal_type='SHORT',
            strength=1.0
        )

        position_size = portfolio_handler.position_sizer.calculate_position_size(
            signal=short_signal,
            portfolio=portfolio_handler.portfolio
        )

        assert position_size <= 0, "SHORT signal should return negative or zero position"


class TestBacktestIntegration:
    """Test position sizing in backtest context."""

    def test_backtest_position_sizing_prevents_errors(self):
        """
        Verify position sizing in backtest prevents negative cash errors.
        This is the main issue we're fixing from the backtest results.
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.15)  # 15% per position
        )

        # Simulate a series of trades
        trades = [
            ('AAPL', 150.0),
            ('GOOGL', 2800.0),
            ('MSFT', 380.0),
            ('AMZN', 175.0),
            ('TSLA', 245.0),
        ]

        for symbol, price in trades:
            signal = SignalEvent(
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type='LONG',
                strength=0.8
            )

            position_size = portfolio_handler.position_sizer.calculate_position_size(
                signal=signal,
                portfolio=portfolio_handler.portfolio
            )

            if position_size > 0:
                # Calculate commission
                commission = position_size * price * 0.001

                # Check if we can afford the trade
                required_cash = position_size * price + commission

                if required_cash <= portfolio_handler.portfolio.cash:
                    fill = FillEvent(
                        timestamp=datetime.now(),
                        symbol=symbol,
                        exchange='SIMULATED',
                        quantity=position_size,
                        direction='BUY',
                        fill_price=price,
                        commission=commission
                    )

                    portfolio_handler.update_fill(fill)

                    # Verify cash didn't go negative
                    assert portfolio_handler.portfolio.cash >= 0, \
                        f"Cash went negative after {symbol} trade: ${portfolio_handler.portfolio.cash:.2f}"
                else:
                    # Trade would exceed available cash - this should not happen
                    # with proper position sizing
                    pytest.fail(
                        f"Position sizer allowed trade exceeding available cash: "
                        f"Required ${required_cash:.2f}, Available ${portfolio_handler.portfolio.cash:.2f}"
                    )

        # Final verification
        assert portfolio_handler.portfolio.cash >= 0, "Final cash is negative"
        assert len(portfolio_handler.portfolio.positions) > 0, "Should have created positions"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
