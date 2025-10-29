"""
Unit test to verify EXIT signal bug fix.

This test validates that EXIT signals properly close positions
without going through position sizing logic.
"""

from datetime import datetime
from src.backtesting.portfolio_handler import PortfolioHandler, FixedAmountSizer
from src.models.events import SignalEvent, FillEvent
from src.models.portfolio import Portfolio


class TestExitSignalFix:
    """Test suite for EXIT signal handling fix"""

    def test_exit_signal_closes_full_position(self):
        """
        Test that EXIT signal closes the full position regardless of position sizer.

        BUG SCENARIO:
        - Open LONG position with 100 shares
        - Send EXIT signal
        - Expected: Generate SELL order for 100 shares
        - Bug (before fix): Position sizer returned 0, so order_quantity = 0 - 100 = -100
          BUT position sizer logic prevented proper execution
        """
        # Initialize portfolio with $100k
        portfolio_handler = PortfolioHandler(
            initial_capital=100000.0,
            position_sizer=FixedAmountSizer(10000.0),
        )

        # Simulate opening a LONG position by directly updating portfolio
        # (simulating a previous ENTRY signal that was filled)
        portfolio_handler.portfolio.update_position(
            symbol='AAPL',
            quantity=100,  # 100 shares long
            price=150.0,
        )
        portfolio_handler.portfolio.cash -= 100 * 150.0  # Deduct cost

        # Verify position is open
        position = portfolio_handler.portfolio.positions.get('AAPL')
        assert position is not None
        assert position.quantity == 100

        # Create EXIT signal
        exit_signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            signal_type='EXIT',
            strength=1.0,
            strategy_id='test_strategy'
        )

        # Generate orders from EXIT signal
        orders = portfolio_handler.generate_orders(exit_signal)

        # CRITICAL ASSERTIONS: EXIT signal must generate proper close order
        assert len(orders) == 1, "EXIT signal should generate exactly 1 order"

        exit_order = orders[0]
        assert exit_order.direction == 'SELL', "EXIT order must be SELL"
        assert exit_order.quantity == 100, f"EXIT order should close full 100 shares, got {exit_order.quantity}"
        assert exit_order.symbol == 'AAPL'
        assert exit_order.order_type == 'MKT'

        print("✅ EXIT signal correctly generates SELL order for full position")

    def test_exit_signal_with_no_position(self):
        """
        Test that EXIT signal with no position generates no order.
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=100000.0,
            position_sizer=FixedAmountSizer(10000.0),
        )

        # No position exists for AAPL
        assert 'AAPL' not in portfolio_handler.portfolio.positions

        # Create EXIT signal
        exit_signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            signal_type='EXIT',
            strength=1.0,
            strategy_id='test_strategy'
        )

        # Generate orders
        orders = portfolio_handler.generate_orders(exit_signal)

        # Should generate no orders (nothing to exit)
        assert len(orders) == 0, "EXIT signal with no position should generate no orders"

        print("✅ EXIT signal with no position correctly generates no orders")

    def test_long_signal_uses_position_sizer(self):
        """
        Test that LONG signals still go through position sizer.
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=100000.0,
            position_sizer=FixedAmountSizer(10000.0),  # $10k per position
        )

        # Create LONG signal
        long_signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            signal_type='LONG',
            strength=0.8,
            strategy_id='test_strategy'
        )

        # Mock data handler for price
        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 150.0
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        # Generate orders
        orders = portfolio_handler.generate_orders(long_signal)

        # Should generate BUY order sized by position sizer
        assert len(orders) == 1
        order = orders[0]
        assert order.direction == 'BUY'
        # With $10k position size and $150 price, should be ~66 shares (after fees)
        assert 50 <= order.quantity <= 70, f"Expected ~66 shares, got {order.quantity}"

        print("✅ LONG signal correctly uses position sizer")

    def test_exit_signal_bypasses_position_sizer(self):
        """
        Test that EXIT signal bypasses position sizer logic entirely.

        This is the core fix: EXIT signals should NOT call position_sizer.calculate_position_size()
        in the same way as LONG/SHORT signals.
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=100000.0,
            position_sizer=FixedAmountSizer(5000.0),  # Small position size
        )

        # Open large position (larger than position sizer would allow)
        portfolio_handler.portfolio.update_position(
            symbol='AAPL',
            quantity=200,  # 200 shares = $30k position (larger than $5k sizer)
            price=150.0,
        )
        portfolio_handler.portfolio.cash -= 200 * 150.0

        # Create EXIT signal
        exit_signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            signal_type='EXIT',
            strength=1.0,
            strategy_id='test_strategy'
        )

        # Generate orders
        orders = portfolio_handler.generate_orders(exit_signal)

        # CRITICAL: EXIT should close FULL 200 shares, not just the position sizer amount
        assert len(orders) == 1
        exit_order = orders[0]
        assert exit_order.quantity == 200, \
            f"EXIT must close full 200 shares, not position sizer amount (got {exit_order.quantity})"
        assert exit_order.direction == 'SELL'

        print("✅ EXIT signal bypasses position sizer and closes full position")

    def test_exit_after_entry_sequence(self):
        """
        Test complete ENTRY -> EXIT sequence.
        """
        portfolio_handler = PortfolioHandler(
            initial_capital=100000.0,
            position_sizer=FixedAmountSizer(10000.0),
        )

        # Mock data handler
        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 150.0
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        # Step 1: LONG signal
        long_signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            signal_type='LONG',
            strength=0.8,
            strategy_id='test_strategy'
        )

        entry_orders = portfolio_handler.generate_orders(long_signal)
        assert len(entry_orders) == 1
        entry_order = entry_orders[0]
        entry_quantity = entry_order.quantity

        # Step 2: Simulate fill for ENTRY
        entry_fill = FillEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            exchange='ALPACA',
            quantity=entry_quantity,
            direction='BUY',
            fill_price=150.0,
            commission=entry_quantity * 150.0 * 0.001,  # 0.1% commission
        )
        portfolio_handler.update_fill(entry_fill)

        # Verify position is open
        position = portfolio_handler.portfolio.positions.get('AAPL')
        assert position.quantity == entry_quantity

        # Step 3: EXIT signal
        exit_signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol='AAPL',
            signal_type='EXIT',
            strength=1.0,
            strategy_id='test_strategy'
        )

        exit_orders = portfolio_handler.generate_orders(exit_signal)
        assert len(exit_orders) == 1
        exit_order = exit_orders[0]

        # CRITICAL: EXIT order quantity must match ENTRY quantity
        assert exit_order.quantity == entry_quantity, \
            f"EXIT quantity ({exit_order.quantity}) must match ENTRY quantity ({entry_quantity})"
        assert exit_order.direction == 'SELL'

        print(f"✅ Complete ENTRY ({entry_quantity} shares) -> EXIT ({exit_order.quantity} shares) sequence works correctly")


if __name__ == '__main__':
    """Run tests directly"""
    test = TestExitSignalFix()

    print("\n" + "="*60)
    print("🔧 EXIT SIGNAL BUG FIX VERIFICATION")
    print("="*60 + "\n")

    try:
        test.test_exit_signal_closes_full_position()
        test.test_exit_signal_with_no_position()
        test.test_long_signal_uses_position_sizer()
        test.test_exit_signal_bypasses_position_sizer()
        test.test_exit_after_entry_sequence()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - EXIT SIGNAL FIX VERIFIED")
        print("="*60 + "\n")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        raise
