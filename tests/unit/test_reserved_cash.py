"""
Unit tests for reserved cash race condition fix.

Tests verify that the reserved cash mechanism prevents cash overdraft
when multiple orders are generated in the same bar.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.backtesting.portfolio_handler import PortfolioHandler, PercentageOfEquitySizer
from src.models.events import SignalEvent
from src.models.portfolio import Portfolio


class TestReservedCash:
    """Test suite for reserved cash tracking."""

    def test_reserved_cash_initialized_to_zero(self):
        """Test that reserved cash starts at zero."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.1),
        )

        assert handler.reserved_cash == 0.0

    def test_single_buy_order_reserves_cash(self):
        """Test that a BUY order reserves cash."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.1),
        )

        # Mock data handler
        mock_bar = Mock()
        mock_bar.close = 100.0
        handler.data_handler = Mock()
        handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

        # Generate signal
        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='AAPL',
            signal_type='LONG',
            strength=0.8,
            strategy_id='test',
        )

        # Generate orders
        orders = handler.generate_orders(signal)

        # Verify order generated
        assert len(orders) == 1
        assert orders[0].direction == 'BUY'

        # Verify cash is reserved
        assert handler.reserved_cash > 0
        print(f"Reserved cash: ${handler.reserved_cash:,.2f}")

        # Verify available cash reduced
        available_cash = handler.portfolio.cash - handler.reserved_cash
        assert available_cash < handler.portfolio.cash

    def test_multiple_orders_respect_reserved_cash(self):
        """Test that multiple orders don't over-allocate cash."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.3),  # 30% per position
        )

        # Mock data handler
        handler.data_handler = Mock()

        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
        price = 100.0

        total_allocated = 0

        for symbol in symbols:
            # Mock latest bar
            mock_bar = Mock()
            mock_bar.close = price
            handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

            # Generate signal
            signal = SignalEvent(
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type='LONG',
                strength=0.8,
                strategy_id='test',
            )

            # Generate orders
            orders = handler.generate_orders(signal)

            if orders:
                order = orders[0]
                order_value = order.quantity * price
                total_allocated += order_value
                print(
                    f"{symbol}: {order.quantity} shares x ${price} = ${order_value:,.2f}, "
                    f"reserved: ${handler.reserved_cash:,.2f}"
                )

        # Verify total doesn't exceed initial capital
        print(f"\nTotal allocated: ${total_allocated:,.2f}")
        print(f"Initial capital: ${handler.initial_capital:,.2f}")
        print(f"Reserved cash: ${handler.reserved_cash:,.2f}")

        # Account for commissions and slippage in reserved cash
        # Reserved cash should be slightly more than allocated (includes fees)
        assert handler.reserved_cash >= total_allocated
        assert handler.reserved_cash <= handler.initial_capital

    def test_clear_reserved_cash(self):
        """Test that clearing reserved cash resets to zero."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.1),
        )

        # Mock data handler
        mock_bar = Mock()
        mock_bar.close = 100.0
        handler.data_handler = Mock()
        handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

        # Generate signal to reserve cash
        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='AAPL',
            signal_type='LONG',
            strength=0.8,
            strategy_id='test',
        )

        orders = handler.generate_orders(signal)
        assert len(orders) == 1
        assert handler.reserved_cash > 0

        initial_reserved = handler.reserved_cash

        # Clear reserved cash
        handler.clear_reserved_cash()

        # Verify cleared
        assert handler.reserved_cash == 0.0
        print(f"Cleared ${initial_reserved:,.2f} reserved cash")

    def test_order_adjustment_when_exceeding_available_cash(self):
        """Test that orders are adjusted when they exceed available cash."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.4),  # 40% per position
        )

        # Mock data handler
        handler.data_handler = Mock()

        symbols = ['AAPL', 'GOOGL', 'MSFT']
        price = 100.0

        orders_generated = []

        for symbol in symbols:
            # Mock latest bar
            mock_bar = Mock()
            mock_bar.close = price
            handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

            # Generate signal
            signal = SignalEvent(
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type='LONG',
                strength=0.8,
                strategy_id='test',
            )

            # Generate orders
            orders = handler.generate_orders(signal)
            orders_generated.extend(orders)

            if orders:
                order = orders[0]
                print(
                    f"{symbol}: {order.quantity} shares, "
                    f"reserved: ${handler.reserved_cash:,.2f}, "
                    f"available: ${handler.portfolio.cash - handler.reserved_cash:,.2f}"
                )

        # Verify orders were generated
        assert len(orders_generated) > 0

        # Verify total reserved doesn't exceed capital
        assert handler.reserved_cash <= handler.initial_capital

        # Verify available cash never went negative
        available = handler.portfolio.cash - handler.reserved_cash
        assert available >= 0

    def test_expensive_stock_order_rejection(self):
        """Test that orders for very expensive stocks are rejected."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.1),
        )

        # Mock data handler with expensive stock
        mock_bar = Mock()
        mock_bar.close = 50000.0  # $50k per share, only have $10k
        handler.data_handler = Mock()
        handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

        # Generate signal
        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='BRK.A',
            signal_type='LONG',
            strength=0.8,
            strategy_id='test',
        )

        # Generate orders
        orders = handler.generate_orders(signal)

        # Verify order rejected (empty list or 0 quantity)
        assert len(orders) == 0 or orders[0].quantity == 0
        print(f"Order rejected: stock too expensive (${mock_bar.close:,.2f}/share)")

    def test_sell_orders_dont_require_cash_reservation(self):
        """Test that SELL orders don't reserve cash."""
        from src.models.portfolio import Position

        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.1),
        )

        # Mock data handler
        mock_bar = Mock()
        mock_bar.close = 100.0
        handler.data_handler = Mock()
        handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

        # Add a real position (not a Mock) - use portfolio.update_position
        handler.portfolio.update_position(
            symbol='AAPL',
            quantity=10,
            price=100.0,
        )

        # Generate EXIT signal
        signal = SignalEvent(
            timestamp=datetime.now(),
            symbol='AAPL',
            signal_type='EXIT',
            strength=0.8,
            strategy_id='test',
        )

        initial_reserved = handler.reserved_cash

        # Generate orders
        orders = handler.generate_orders(signal)

        # Verify SELL order generated
        if orders:
            assert orders[0].direction == 'SELL'
            # Verify reserved cash unchanged (SELL doesn't reserve)
            assert handler.reserved_cash == initial_reserved
            print(f"SELL order generated without reserving cash")

    def test_available_cash_calculation(self):
        """Test that available cash is correctly calculated."""
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.1),
        )

        # Initially, available = portfolio cash
        available = handler.portfolio.cash - handler.reserved_cash
        assert available == 10000.0

        # Reserve some cash
        handler.reserved_cash = 3000.0

        # Available should decrease
        available = handler.portfolio.cash - handler.reserved_cash
        assert available == 7000.0

        # Clear reservation
        handler.clear_reserved_cash()
        available = handler.portfolio.cash - handler.reserved_cash
        assert available == 10000.0


class TestRaceConditionScenario:
    """Test the specific race condition scenario."""

    def test_race_condition_prevented(self):
        """
        Test that the race condition is prevented when multiple orders
        are generated in the same bar.

        Without the fix, this would allow $15k in orders with only $10k cash.
        With the fix, orders should be adjusted to stay within budget.
        """
        handler = PortfolioHandler(
            initial_capital=10000.0,
            position_sizer=PercentageOfEquitySizer(0.5),  # 50% per position (aggressive)
        )

        # Mock data handler
        handler.data_handler = Mock()

        # Three signals arrive in same bar, each requesting 50% allocation
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        price = 100.0

        all_orders = []
        total_committed = 0

        for symbol in symbols:
            # Mock latest bar
            mock_bar = Mock()
            mock_bar.close = price
            handler.data_handler.get_latest_bar = Mock(return_value=mock_bar)

            # Generate signal
            signal = SignalEvent(
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type='LONG',
                strength=0.8,
                strategy_id='test',
            )

            # Generate orders
            orders = handler.generate_orders(signal)
            all_orders.extend(orders)

            if orders:
                order = orders[0]
                order_value = order.quantity * price
                total_committed += order_value

                print(
                    f"\n{symbol}:"
                    f"\n  Requested: 50% of ${handler.portfolio.cash:,.2f} = ${handler.portfolio.cash * 0.5:,.2f}"
                    f"\n  Available: ${handler.portfolio.cash - handler.reserved_cash + order_value:,.2f}"
                    f"\n  Generated: {order.quantity} shares x ${price} = ${order_value:,.2f}"
                    f"\n  Reserved: ${handler.reserved_cash:,.2f}"
                    f"\n  Remaining: ${handler.portfolio.cash - handler.reserved_cash:,.2f}"
                )

        print(f"\n\nSummary:")
        print(f"  Initial capital: ${handler.initial_capital:,.2f}")
        print(f"  Total committed: ${total_committed:,.2f}")
        print(f"  Total reserved: ${handler.reserved_cash:,.2f}")
        print(f"  Orders generated: {len(all_orders)}")

        # CRITICAL: Total committed should not exceed initial capital
        assert total_committed <= handler.initial_capital, (
            f"Race condition not prevented! "
            f"Committed ${total_committed:,.2f} with only ${handler.initial_capital:,.2f} available"
        )

        # Reserved cash should account for fees
        assert handler.reserved_cash >= total_committed

        # Available cash should never go negative
        available = handler.portfolio.cash - handler.reserved_cash
        assert available >= 0, f"Available cash went negative: ${available:,.2f}"

        print(f"\n✅ Race condition prevented!")
        print(f"   Without fix: Would have committed ${handler.portfolio.cash * 0.5 * 3:,.2f} (150% of capital)")
        print(f"   With fix: Actually committed ${total_committed:,.2f} ({total_committed/handler.initial_capital*100:.1f}% of capital)")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
