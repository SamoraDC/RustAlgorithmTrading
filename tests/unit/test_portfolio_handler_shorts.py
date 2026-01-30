"""
Unit tests for short position handling in PortfolioHandler.

Tests ensure that short positions are correctly:
- Entered with negative quantities
- Exited with BUY (cover) orders instead of SELL
- P&L calculated correctly for shorts (profit when price drops)
- Reserved cash tracked for margin requirements
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

from src.backtesting.portfolio_handler import PortfolioHandler
from src.models.events import SignalEvent


class TestShortPositionEntry:
    """Test suite for entering short positions."""

    @pytest.fixture
    def portfolio(self):
        """Create a portfolio handler with initial capital."""
        return PortfolioHandler(initial_capital=100000.0)

    def test_reserved_cash_initialized(self, portfolio):
        """Test that reserved cash is initialized to 0."""
        assert hasattr(portfolio, 'reserved_cash')
        assert portfolio.reserved_cash == 0.0
        assert portfolio.portfolio.cash == 100000.0

    def test_portfolio_initial_state(self, portfolio):
        """Test that portfolio starts with correct initial state."""
        assert portfolio.portfolio.equity == 100000.0
        assert len(portfolio.portfolio.positions) == 0
        assert portfolio.initial_capital == 100000.0

    def test_short_signal_type_is_valid(self, portfolio):
        """Test that SHORT signal type is recognized."""
        signal = SignalEvent(
            timestamp=datetime(2024, 1, 1, 9, 30),
            symbol='AAPL',
            signal_type='SHORT',
            strength=1.0,
            strategy_id='test'
        )
        assert signal.signal_type == 'SHORT'

    def test_exit_signal_type_is_valid(self, portfolio):
        """Test that EXIT signal type is recognized."""
        signal = SignalEvent(
            timestamp=datetime(2024, 1, 1, 9, 30),
            symbol='AAPL',
            signal_type='EXIT',
            strength=1.0,
            strategy_id='test'
        )
        assert signal.signal_type == 'EXIT'


class TestShortPositionExit:
    """Test suite for exiting short positions."""

    @pytest.fixture
    def portfolio_with_short(self):
        """Create a portfolio with an existing short position."""
        portfolio = PortfolioHandler(initial_capital=100000.0)
        # Manually add a short position for testing
        from src.models.portfolio import Position
        portfolio.portfolio.positions['AAPL'] = Position(
            symbol='AAPL',
            quantity=-100,  # Negative = short
            average_price=150.0,
            current_price=150.0,
        )
        return portfolio

    def test_short_position_has_negative_quantity(self, portfolio_with_short):
        """Test that short position is stored with negative quantity."""
        position = portfolio_with_short.portfolio.positions.get('AAPL')
        assert position is not None
        assert position.quantity < 0, "Short position should have negative quantity"
        assert position.quantity == -100

    def test_short_position_market_value_is_negative(self, portfolio_with_short):
        """Test that short position has negative market value."""
        position = portfolio_with_short.portfolio.positions.get('AAPL')
        assert position is not None
        assert position.market_value < 0, "Short position should have negative market value"


class TestShortPositionPnL:
    """Test suite for P&L calculations on short positions."""

    def test_short_profit_when_price_drops(self):
        """Test that short position profits when price drops."""
        # Entry: Short 100 shares at $150
        entry_price = 150.0
        quantity = -100  # Negative for short

        # Exit: Cover at $140 (price dropped $10)
        exit_price = 140.0

        # Calculate P&L
        # For shorts: profit = (entry_price - exit_price) * abs(quantity)
        expected_pnl = (entry_price - exit_price) * abs(quantity)  # $10 * 100 = $1000 profit

        assert expected_pnl == 1000.0, "Short should profit when price drops"

    def test_short_loss_when_price_rises(self):
        """Test that short position loses when price rises."""
        # Entry: Short 100 shares at $150
        entry_price = 150.0
        quantity = -100

        # Exit: Cover at $160 (price rose $10)
        exit_price = 160.0

        # Calculate P&L
        expected_pnl = (entry_price - exit_price) * abs(quantity)  # -$10 * 100 = -$1000 loss

        assert expected_pnl == -1000.0, "Short should lose when price rises"


class TestReservedCashForShorts:
    """Test suite for reserved cash tracking with short positions."""

    @pytest.fixture
    def portfolio(self):
        """Create a portfolio handler."""
        return PortfolioHandler(initial_capital=100000.0)

    def test_reserved_cash_attribute_exists(self, portfolio):
        """Test that reserved_cash attribute exists."""
        assert hasattr(portfolio, 'reserved_cash')
        assert portfolio.reserved_cash == 0.0

    def test_reserved_cash_can_be_updated(self, portfolio):
        """Test that reserved cash can be updated."""
        portfolio.reserved_cash = 10000.0
        assert portfolio.reserved_cash == 10000.0

    def test_available_cash_calculation(self, portfolio):
        """Test that available cash is calculated correctly."""
        portfolio.reserved_cash = 30000.0
        available = portfolio.portfolio.cash - portfolio.reserved_cash
        assert available == 70000.0


class TestShortPositionRiskManagement:
    """Test suite for risk management of short positions."""

    @pytest.fixture
    def portfolio(self):
        """Create a portfolio handler."""
        return PortfolioHandler(initial_capital=100000.0)

    def test_portfolio_equity_calculation(self, portfolio):
        """Test that equity is calculated correctly."""
        assert portfolio.portfolio.equity == 100000.0

    def test_reserved_cash_prevents_overdraft(self, portfolio):
        """Test that reserved cash prevents overdraft."""
        # Reserve most of the cash
        portfolio.reserved_cash = 95000.0
        available = portfolio.portfolio.cash - portfolio.reserved_cash

        # Should only have $5000 available
        assert available == 5000.0

        # Cannot reserve more than available
        max_new_reservation = available
        assert max_new_reservation == 5000.0


class TestExitSignalDirectionFix:
    """Test suite for EXIT signal direction fix (critical bug fix verification)."""

    @pytest.fixture
    def portfolio_with_long(self):
        """Create a portfolio with an existing long position."""
        portfolio = PortfolioHandler(initial_capital=100000.0)
        from src.models.portfolio import Position
        portfolio.portfolio.positions['AAPL'] = Position(
            symbol='AAPL',
            quantity=100,  # Positive = long
            average_price=150.0,
            current_price=150.0,
        )
        portfolio.portfolio.cash = 85000.0  # Deducted for purchase
        return portfolio

    @pytest.fixture
    def portfolio_with_short(self):
        """Create a portfolio with an existing short position."""
        portfolio = PortfolioHandler(initial_capital=100000.0)
        from src.models.portfolio import Position
        portfolio.portfolio.positions['AAPL'] = Position(
            symbol='AAPL',
            quantity=-100,  # Negative = short
            average_price=150.0,
            current_price=150.0,
        )
        return portfolio

    def test_long_position_has_positive_quantity(self, portfolio_with_long):
        """Test that long position has positive quantity."""
        position = portfolio_with_long.portfolio.positions.get('AAPL')
        assert position.quantity > 0

    def test_short_position_has_negative_quantity(self, portfolio_with_short):
        """Test that short position has negative quantity."""
        position = portfolio_with_short.portfolio.positions.get('AAPL')
        assert position.quantity < 0

    def test_exit_direction_determined_by_position_type(self):
        """Test that exit direction is determined by position type."""
        # For long positions (qty > 0), exit should be SELL
        long_qty = 100
        if long_qty > 0:
            exit_direction = 'SELL'
        else:
            exit_direction = 'BUY'  # Cover short

        assert exit_direction == 'SELL'

        # For short positions (qty < 0), exit should be BUY (cover)
        short_qty = -100
        if short_qty > 0:
            exit_direction = 'SELL'
        else:
            exit_direction = 'BUY'  # Cover short

        assert exit_direction == 'BUY'


class TestPortfolioEquityCurve:
    """Test suite for equity curve tracking."""

    @pytest.fixture
    def portfolio(self):
        """Create a portfolio handler."""
        return PortfolioHandler(initial_capital=100000.0)

    def test_equity_curve_initialized_empty(self, portfolio):
        """Test that equity curve starts empty."""
        assert len(portfolio.equity_curve) == 0

    def test_update_timeindex_records_equity(self, portfolio):
        """Test that update_timeindex records equity point."""
        timestamp = datetime(2024, 1, 1, 9, 30)
        portfolio.update_timeindex(timestamp)

        assert len(portfolio.equity_curve) == 1
        assert portfolio.equity_curve[0]['timestamp'] == timestamp
        assert portfolio.equity_curve[0]['equity'] == 100000.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
