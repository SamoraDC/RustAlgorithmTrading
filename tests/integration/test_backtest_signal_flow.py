"""
Integration tests for end-to-end signal flow in backtesting

Tests the complete flow from data → strategy → signals → portfolio → execution
to identify bottlenecks causing 0% win rate.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversion
from src.strategies.base import SignalType
from src.backtesting.portfolio_handler import PortfolioHandler, FixedAmountSizer
from src.models.events import SignalEvent, OrderEvent, FillEvent


class TestSignalToOrderFlow:
    """Test signal → order conversion in portfolio handler"""

    def test_long_signal_generates_buy_order(self):
        """Verify LONG signals generate BUY orders"""
        portfolio_handler = PortfolioHandler(
            initial_capital=100000,
            position_sizer=FixedAmountSizer(10000)
        )

        # Create a LONG signal
        signal = SignalEvent(
            timestamp=datetime(2024, 1, 15),
            symbol='TEST',
            signal_type='LONG',
            strategy_id='test_strategy',
            strength=0.8,
        )

        # Set up mock data handler
        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 100.0
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        # Generate orders
        orders = portfolio_handler.generate_orders(signal)

        # ASSERT: Should generate exactly 1 BUY order
        assert len(orders) == 1, f"Expected 1 order, got {len(orders)}"
        order = orders[0]
        assert order.direction == 'BUY', f"Expected BUY order, got {order.direction}"
        assert order.quantity > 0, "Order quantity must be positive"

        logger.info(f"✅ LONG signal → BUY {order.quantity} shares")

    def test_short_signal_generates_sell_order(self):
        """Verify SHORT signals generate SELL orders"""
        portfolio_handler = PortfolioHandler(
            initial_capital=100000,
            position_sizer=FixedAmountSizer(10000)
        )

        # Create a SHORT signal
        signal = SignalEvent(
            timestamp=datetime(2024, 1, 15),
            symbol='TEST',
            signal_type='SHORT',
            strategy_id='test_strategy',
            strength=0.8,
        )

        # Set up mock data handler
        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 100.0
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        # Generate orders
        orders = portfolio_handler.generate_orders(signal)

        # ASSERT: Should generate exactly 1 SELL order
        assert len(orders) == 1, f"Expected 1 order, got {len(orders)}"
        order = orders[0]
        assert order.direction == 'SELL', f"Expected SELL order, got {order.direction}"
        assert order.quantity > 0, "Order quantity must be positive"

        logger.info(f"✅ SHORT signal → SELL {order.quantity} shares")

    def test_exit_signal_closes_position(self):
        """Verify EXIT signals close existing positions"""
        portfolio_handler = PortfolioHandler(
            initial_capital=100000,
            position_sizer=FixedAmountSizer(10000)
        )

        # Set up mock data handler
        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 105.0
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        # First, open a position with LONG signal
        long_signal = SignalEvent(
            timestamp=datetime(2024, 1, 10),
            symbol='TEST',
            signal_type='LONG',
            strategy_id='test_strategy',
            strength=0.8,
        )

        orders = portfolio_handler.generate_orders(long_signal)
        assert len(orders) == 1, "Should generate initial LONG order"

        # Simulate fill
        fill = FillEvent(
            timestamp=datetime(2024, 1, 10),
            symbol='TEST',
            exchange='TEST',
            quantity=orders[0].quantity,
            direction='BUY',
            fill_price=100.0,
            commission=10.0,
        )
        portfolio_handler.update_fill(fill)

        # Now send EXIT signal
        exit_signal = SignalEvent(
            timestamp=datetime(2024, 1, 15),
            symbol='TEST',
            signal_type='EXIT',
            strategy_id='test_strategy',
            strength=1.0,
        )

        exit_orders = portfolio_handler.generate_orders(exit_signal)

        # ASSERT: Should generate exactly 1 SELL order to close position
        assert len(exit_orders) == 1, f"Expected 1 exit order, got {len(exit_orders)}"
        exit_order = exit_orders[0]
        assert exit_order.direction == 'SELL', f"Expected SELL to exit, got {exit_order.direction}"
        assert exit_order.quantity == orders[0].quantity, (
            f"Exit order quantity {exit_order.quantity} should match entry {orders[0].quantity}"
        )

        logger.info(f"✅ EXIT signal → SELL {exit_order.quantity} shares (closing position)")


class TestEndToEndBacktestFlow:
    """Test complete backtest flow with real strategies"""

    def test_momentum_strategy_full_flow(self):
        """Test Momentum strategy from data to P&L"""
        # Initialize strategy
        strategy = MomentumStrategy(
            macd_histogram_threshold=0.0005,
            volume_confirmation=False,
            use_trailing_stop=False,
            min_holding_period=5,
        )

        # Create synthetic market data
        dates = pd.date_range(start='2024-01-01', end='2024-02-01', freq='1D')
        n_bars = len(dates)

        # Uptrend: 100 → 120
        prices = np.linspace(100, 120, n_bars)
        prices += np.random.normal(0, 1, n_bars)  # Small noise

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

        logger.info(f"📊 Generated {len(signals)} signals from Momentum strategy")

        # ASSERT: Should generate at least 1 signal
        assert len(signals) > 0, "Momentum strategy generated 0 signals"

        # Initialize portfolio
        portfolio_handler = PortfolioHandler(
            initial_capital=100000,
            position_sizer=FixedAmountSizer(10000)
        )

        # Mock data handler
        class MockDataHandler:
            def __init__(self, data_df):
                self.data = data_df
                self.current_idx = 0

            def get_latest_bar(self, symbol):
                if self.current_idx < len(self.data):
                    row = self.data.iloc[self.current_idx]

                    class Bar:
                        def __init__(self, row_data):
                            self.close = float(row_data['close'])
                            self.timestamp = row_data.name

                    return Bar(row)
                return None

        portfolio_handler.data_handler = MockDataHandler(data)

        # Process each signal
        total_orders = 0
        total_fills = 0

        for signal in signals:
            # Update data handler index
            signal_idx = data.index.get_loc(signal.timestamp)
            portfolio_handler.data_handler.current_idx = signal_idx

            # Convert signal to SignalEvent
            signal_event = SignalEvent(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                strategy_id='momentum',
                strength=signal.confidence,
            )

            # Generate orders
            orders = portfolio_handler.generate_orders(signal_event)
            total_orders += len(orders)

            # Simulate fills
            for order in orders:
                fill_price = signal.price * (1.0005 if order.direction == 'BUY' else 0.9995)
                fill = FillEvent(
                    timestamp=signal.timestamp,
                    symbol=signal.symbol,
                    exchange='TEST',
                    quantity=order.quantity,
                    direction=order.direction,
                    fill_price=fill_price,
                    commission=fill_price * order.quantity * 0.001,
                )

                portfolio_handler.update_fill(fill)
                total_fills += 1

            # Clear reserved cash after processing bar
            portfolio_handler.clear_reserved_cash()

        # ASSERT: Orders and fills should be generated
        assert total_orders > 0, f"No orders generated from {len(signals)} signals"
        assert total_fills > 0, f"No fills executed from {total_orders} orders"

        # Check final portfolio state
        final_equity = portfolio_handler.portfolio.equity
        initial_capital = portfolio_handler.initial_capital
        total_return = (final_equity - initial_capital) / initial_capital

        logger.info(f"📈 Backtest complete:")
        logger.info(f"   Signals: {len(signals)}")
        logger.info(f"   Orders: {total_orders}")
        logger.info(f"   Fills: {total_fills}")
        logger.info(f"   Initial capital: ${initial_capital:,.2f}")
        logger.info(f"   Final equity: ${final_equity:,.2f}")
        logger.info(f"   Total return: {total_return:.2%}")

        logger.info(f"✅ Momentum strategy full flow executed successfully")

    def test_mean_reversion_strategy_full_flow(self):
        """Test Mean Reversion strategy from data to P&L"""
        # Initialize strategy
        strategy = MeanReversion(
            bb_period=20,
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
        )

        # Create oscillating market data
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1D')
        time = np.arange(len(dates))
        prices = 100 + 15 * np.sin(time / 10)  # Large oscillations

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

        # Generate signals
        signals = strategy.generate_signals(data)

        logger.info(f"📊 Generated {len(signals)} signals from Mean Reversion strategy")

        # ASSERT: Should generate at least 1 signal
        assert len(signals) > 0, "Mean Reversion strategy generated 0 signals"

        # Initialize portfolio
        portfolio_handler = PortfolioHandler(
            initial_capital=100000,
            position_sizer=FixedAmountSizer(10000)
        )

        # Mock data handler
        class MockDataHandler:
            def __init__(self, data_df):
                self.data = data_df
                self.current_idx = 0

            def get_latest_bar(self, symbol):
                if self.current_idx < len(self.data):
                    row = self.data.iloc[self.current_idx]

                    class Bar:
                        def __init__(self, row_data):
                            self.close = float(row_data['close'])
                            self.timestamp = row_data.name

                    return Bar(row)
                return None

        portfolio_handler.data_handler = MockDataHandler(data)

        # Process each signal
        total_orders = 0
        total_fills = 0

        for signal in signals:
            # Update data handler index
            signal_idx = data.index.get_loc(signal.timestamp)
            portfolio_handler.data_handler.current_idx = signal_idx

            # Convert signal to SignalEvent
            signal_event = SignalEvent(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                strategy_id='mean_reversion',
                strength=signal.confidence,
            )

            # Generate orders
            orders = portfolio_handler.generate_orders(signal_event)
            total_orders += len(orders)

            # Simulate fills
            for order in orders:
                fill_price = signal.price * (1.0005 if order.direction == 'BUY' else 0.9995)
                fill = FillEvent(
                    timestamp=signal.timestamp,
                    symbol=signal.symbol,
                    exchange='TEST',
                    quantity=order.quantity,
                    direction=order.direction,
                    fill_price=fill_price,
                    commission=fill_price * order.quantity * 0.001,
                )

                portfolio_handler.update_fill(fill)
                total_fills += 1

            # Clear reserved cash after processing bar
            portfolio_handler.clear_reserved_cash()

        # ASSERT: Orders and fills should be generated
        assert total_orders > 0, f"No orders generated from {len(signals)} signals"
        assert total_fills > 0, f"No fills executed from {total_orders} orders"

        # Check final portfolio state
        final_equity = portfolio_handler.portfolio.equity
        initial_capital = portfolio_handler.initial_capital
        total_return = (final_equity - initial_capital) / initial_capital

        logger.info(f"📈 Backtest complete:")
        logger.info(f"   Signals: {len(signals)}")
        logger.info(f"   Orders: {total_orders}")
        logger.info(f"   Fills: {total_fills}")
        logger.info(f"   Initial capital: ${initial_capital:,.2f}")
        logger.info(f"   Final equity: ${final_equity:,.2f}")
        logger.info(f"   Total return: {total_return:.2%}")

        logger.info(f"✅ Mean Reversion strategy full flow executed successfully")


class TestSignalExecutionBottlenecks:
    """Identify bottlenecks preventing signals from executing"""

    def test_cash_constraint_bottleneck(self):
        """Test if insufficient cash blocks signal execution"""
        # Start with very low capital
        portfolio_handler = PortfolioHandler(
            initial_capital=1000,  # Very low
            position_sizer=FixedAmountSizer(10000)  # Wants $10k position
        )

        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 200.0  # Expensive stock
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        signal = SignalEvent(
            timestamp=datetime(2024, 1, 15),
            symbol='TEST',
            signal_type='LONG',
            strategy_id='test',
            strength=0.8,
        )

        orders = portfolio_handler.generate_orders(signal)

        # ASSERT: Should either generate smaller order or skip
        logger.info(f"Cash constraint test: generated {len(orders)} orders with $1k capital")

        if len(orders) > 0:
            order = orders[0]
            estimated_cost = order.quantity * 200 * 1.002  # With fees
            assert estimated_cost <= 1000, (
                f"Order cost ${estimated_cost:.2f} exceeds available cash $1000"
            )
            logger.info(f"✅ Order adjusted for cash constraint: {order.quantity} shares")
        else:
            logger.info(f"✅ Signal skipped due to insufficient cash (expected)")

    def test_position_sizer_bottleneck(self):
        """Test if position sizer returns 0 shares"""
        portfolio_handler = PortfolioHandler(
            initial_capital=100000,
            position_sizer=FixedAmountSizer(10)  # Tiny position size
        )

        class MockDataHandler:
            def get_latest_bar(self, symbol):
                class Bar:
                    close = 200.0
                return Bar()

        portfolio_handler.data_handler = MockDataHandler()

        signal = SignalEvent(
            timestamp=datetime(2024, 1, 15),
            symbol='TEST',
            signal_type='LONG',
            strategy_id='test',
            strength=0.8,
        )

        orders = portfolio_handler.generate_orders(signal)

        logger.info(f"Position sizer test: {len(orders)} orders with $10 target position")

        # This might generate 0 orders if position size rounds to 0
        if len(orders) == 0:
            logger.warning("⚠️ Position sizer returned 0 shares - potential bottleneck!")


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s', '--tb=short'])
