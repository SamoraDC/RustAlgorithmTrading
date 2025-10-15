"""
Unit tests for BacktestEngine
Tests all core functionality including position management, PnL calculation, and trade execution
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from src.backtesting.engine import BacktestEngine, Trade, Position
from src.strategies.base import Strategy, Signal, SignalType


class MockStrategy(Strategy):
    """Simple mock strategy for testing"""

    def __init__(self, signals_to_generate=None):
        super().__init__("MockStrategy")
        self.signals_to_generate = signals_to_generate or []

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Return predefined signals"""
        return self.signals_to_generate

    def calculate_position_size(self, signal: Signal, account_value: float, current_position: float = 0.0) -> float:
        """Fixed position size of 10 shares"""
        return 10.0


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    np.random.seed(42)

    close_prices = 100 + np.cumsum(np.random.randn(100) * 0.5)

    data = pd.DataFrame({
        'open': close_prices + np.random.randn(100) * 0.1,
        'high': close_prices + abs(np.random.randn(100)) * 0.5,
        'low': close_prices - abs(np.random.randn(100)) * 0.5,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)

    return data


@pytest.fixture
def backtest_engine():
    """Create BacktestEngine instance with test parameters"""
    return BacktestEngine(
        initial_capital=100000.0,
        commission_rate=0.001,
        slippage=0.0005
    )


class TestBacktestEngineInitialization:
    """Test engine initialization"""

    def test_initialization_defaults(self):
        """Test default initialization values"""
        engine = BacktestEngine()
        assert engine.initial_capital == 100000.0
        assert engine.commission_rate == 0.001
        assert engine.slippage == 0.0005
        assert engine.cash == 100000.0
        assert len(engine.positions) == 0
        assert len(engine.trades) == 0

    def test_initialization_custom(self):
        """Test custom initialization values"""
        engine = BacktestEngine(
            initial_capital=50000.0,
            commission_rate=0.002,
            slippage=0.001
        )
        assert engine.initial_capital == 50000.0
        assert engine.commission_rate == 0.002
        assert engine.slippage == 0.001
        assert engine.cash == 50000.0

    def test_initial_state(self, backtest_engine):
        """Test initial engine state"""
        assert backtest_engine.cash == 100000.0
        assert isinstance(backtest_engine.positions, dict)
        assert isinstance(backtest_engine.trades, list)
        assert isinstance(backtest_engine.equity_curve, list)


class TestPositionManagement:
    """Test position opening and closing"""

    def test_open_position(self, backtest_engine):
        """Test opening a new position"""
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=150.0,
            date=datetime.now(),
            side='long'
        )

        assert "AAPL" in backtest_engine.positions
        position = backtest_engine.positions["AAPL"]
        assert position.quantity == 10.0
        assert position.entry_price == 150.0
        assert position.side == 'long'

    def test_close_position_long_profit(self, backtest_engine):
        """Test closing a long position with profit"""
        initial_cash = backtest_engine.cash

        # Open position
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        # Close with profit
        backtest_engine._close_position(
            symbol="AAPL",
            exit_price=110.0,
            exit_date=datetime.now()
        )

        assert "AAPL" not in backtest_engine.positions
        assert len(backtest_engine.trades) == 1

        trade = backtest_engine.trades[0]
        assert trade.side == 'long'
        assert trade.quantity == 10.0
        assert trade.pnl > 0  # Should be profitable (after commission/slippage)

    def test_close_position_long_loss(self, backtest_engine):
        """Test closing a long position with loss"""
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        backtest_engine._close_position(
            symbol="AAPL",
            exit_price=90.0,
            exit_date=datetime.now()
        )

        trade = backtest_engine.trades[0]
        assert trade.pnl < 0  # Should be a loss

    def test_close_position_short(self, backtest_engine):
        """Test closing a short position"""
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=100.0,
            date=datetime.now(),
            side='short'
        )

        # Short profits when price goes down
        backtest_engine._close_position(
            symbol="AAPL",
            exit_price=90.0,
            exit_date=datetime.now()
        )

        trade = backtest_engine.trades[0]
        assert trade.side == 'short'
        assert trade.pnl > 0  # Profitable short

    def test_close_nonexistent_position(self, backtest_engine):
        """Test closing a position that doesn't exist"""
        backtest_engine._close_position(
            symbol="NONEXISTENT",
            exit_price=100.0,
            exit_date=datetime.now()
        )

        assert len(backtest_engine.trades) == 0

    def test_close_all_positions(self, backtest_engine):
        """Test closing all open positions"""
        # Open multiple positions
        for symbol in ["AAPL", "GOOGL", "MSFT"]:
            backtest_engine._open_position(
                symbol=symbol,
                quantity=10.0,
                price=100.0,
                date=datetime.now(),
                side='long'
            )

        assert len(backtest_engine.positions) == 3

        backtest_engine._close_all_positions(price=105.0, date=datetime.now())

        assert len(backtest_engine.positions) == 0
        assert len(backtest_engine.trades) == 3


class TestAccountValueCalculation:
    """Test account value and equity calculations"""

    def test_account_value_no_positions(self, backtest_engine):
        """Test account value with no positions"""
        value = backtest_engine._calculate_account_value(100.0)
        assert value == 100000.0  # Only cash

    def test_account_value_with_position(self, backtest_engine):
        """Test account value with open position"""
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        # Position value: 10 shares * $110 = $1100
        # Cash: $100000 (initial, we didn't deduct in this test)
        value = backtest_engine._calculate_account_value(110.0)
        assert value == backtest_engine.cash + (10.0 * 110.0)

    def test_account_value_multiple_positions(self, backtest_engine):
        """Test account value with multiple positions"""
        backtest_engine._open_position("AAPL", 10.0, 100.0, datetime.now(), 'long')
        backtest_engine._open_position("GOOGL", 5.0, 200.0, datetime.now(), 'long')

        # AAPL: 10 * 110 = 1100
        # GOOGL: 5 * 210 = 1050
        # Total position value = 2150
        value = backtest_engine._calculate_account_value(110.0)
        expected = backtest_engine.cash + 1100.0 + 1050.0
        assert value == pytest.approx(expected)


class TestCommissionAndSlippage:
    """Test commission and slippage calculations"""

    def test_commission_applied_on_close(self, backtest_engine):
        """Test that commission is applied when closing position"""
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=100.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        backtest_engine._close_position(
            symbol="AAPL",
            exit_price=110.0,
            exit_date=datetime.now()
        )

        trade = backtest_engine.trades[0]
        # Commission should be: (100 shares * exit_price * slippage) * commission_rate
        assert trade.commission > 0

    def test_slippage_on_buy(self, backtest_engine):
        """Test slippage applied on buy orders"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0,
            quantity=10.0
        )

        strategy = MockStrategy()
        backtest_engine._execute_signal(signal, strategy)

        # Buy slippage increases price
        if "AAPL" in backtest_engine.positions:
            position = backtest_engine.positions["AAPL"]
            assert position.entry_price > 100.0

    def test_slippage_on_sell(self, backtest_engine):
        """Test slippage applied on sell orders"""
        # First open a position
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        # Close with slippage
        backtest_engine._close_position(
            symbol="AAPL",
            exit_price=110.0,
            exit_date=datetime.now()
        )

        trade = backtest_engine.trades[0]
        # Sell slippage decreases exit price
        assert trade.exit_price < 110.0


class TestSignalExecution:
    """Test signal execution logic"""

    def test_execute_buy_signal(self, backtest_engine):
        """Test executing a buy signal"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0,
            quantity=10.0
        )

        strategy = MockStrategy()
        initial_cash = backtest_engine.cash

        backtest_engine._execute_signal(signal, strategy)

        # Position should be opened
        assert "AAPL" in backtest_engine.positions
        # Cash should decrease
        assert backtest_engine.cash < initial_cash

    def test_execute_sell_signal(self, backtest_engine):
        """Test executing a sell signal"""
        # First open a long position
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=10.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        sell_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.SELL,
            price=110.0,
            quantity=10.0
        )

        strategy = MockStrategy()
        backtest_engine._execute_signal(sell_signal, strategy)

        # Position should be closed
        assert "AAPL" not in backtest_engine.positions
        # Trade should be recorded
        assert len(backtest_engine.trades) == 1

    def test_insufficient_cash(self, backtest_engine):
        """Test handling insufficient cash for trade"""
        # Set very low cash
        backtest_engine.cash = 10.0

        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=1000.0,
            quantity=100.0
        )

        strategy = MockStrategy()
        backtest_engine._execute_signal(signal, strategy)

        # Should not open position due to insufficient cash
        assert "AAPL" not in backtest_engine.positions


class TestBacktestRun:
    """Test complete backtest execution"""

    def test_run_with_no_signals(self, backtest_engine, sample_data):
        """Test backtest with strategy that generates no signals"""
        strategy = MockStrategy(signals_to_generate=[])
        results = backtest_engine.run(strategy, sample_data, "AAPL")

        assert results['total_trades'] == 0
        assert results['final_equity'] == 100000.0  # No trades = no change

    def test_run_with_buy_signal(self, backtest_engine, sample_data):
        """Test backtest with single buy signal"""
        buy_signal = Signal(
            timestamp=sample_data.index[10],
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=sample_data.iloc[10]['close'],
            quantity=10.0
        )

        strategy = MockStrategy(signals_to_generate=[buy_signal])
        results = backtest_engine.run(strategy, sample_data, "AAPL")

        # Should have closed position at end
        assert results['total_trades'] == 1

    def test_run_with_multiple_signals(self, backtest_engine, sample_data):
        """Test backtest with multiple buy/sell signals"""
        signals = [
            Signal(
                timestamp=sample_data.index[10],
                symbol="AAPL",
                signal_type=SignalType.BUY,
                price=sample_data.iloc[10]['close'],
                quantity=10.0
            ),
            Signal(
                timestamp=sample_data.index[20],
                symbol="AAPL",
                signal_type=SignalType.SELL,
                price=sample_data.iloc[20]['close'],
                quantity=10.0
            ),
            Signal(
                timestamp=sample_data.index[30],
                symbol="AAPL",
                signal_type=SignalType.BUY,
                price=sample_data.iloc[30]['close'],
                quantity=10.0
            ),
        ]

        strategy = MockStrategy(signals_to_generate=signals)
        results = backtest_engine.run(strategy, sample_data, "AAPL")

        assert results['total_trades'] >= 2  # At least buy-sell-buy

    def test_run_generates_equity_curve(self, backtest_engine, sample_data):
        """Test that backtest generates equity curve"""
        buy_signal = Signal(
            timestamp=sample_data.index[10],
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=sample_data.iloc[10]['close'],
            quantity=10.0
        )

        strategy = MockStrategy(signals_to_generate=[buy_signal])
        results = backtest_engine.run(strategy, sample_data, "AAPL")

        assert 'equity_curve' in results
        assert not results['equity_curve'].empty
        assert 'equity' in results['equity_curve'].columns
        assert 'cash' in results['equity_curve'].columns

    def test_run_state_reset_between_runs(self, backtest_engine, sample_data):
        """Test that engine state resets between backtest runs"""
        buy_signal = Signal(
            timestamp=sample_data.index[10],
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=sample_data.iloc[10]['close'],
            quantity=10.0
        )

        strategy = MockStrategy(signals_to_generate=[buy_signal])

        # First run
        results1 = backtest_engine.run(strategy, sample_data, "AAPL")

        # Second run should reset state
        results2 = backtest_engine.run(strategy, sample_data, "AAPL")

        # Results should be identical (state was reset)
        assert results1['total_trades'] == results2['total_trades']
        assert results1['final_equity'] == results2['final_equity']


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_data(self, backtest_engine):
        """Test backtest with empty DataFrame"""
        empty_data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        strategy = MockStrategy()

        with pytest.raises(Exception):
            backtest_engine.run(strategy, empty_data, "AAPL")

    def test_single_row_data(self, backtest_engine):
        """Test backtest with single row of data"""
        single_row = pd.DataFrame({
            'open': [100.0],
            'high': [101.0],
            'low': [99.0],
            'close': [100.5],
            'volume': [1000]
        }, index=[datetime.now()])

        strategy = MockStrategy()
        results = backtest_engine.run(strategy, single_row, "AAPL")

        assert results['total_trades'] == 0

    def test_negative_prices(self, backtest_engine):
        """Test handling of negative prices (should not happen in practice)"""
        with pytest.raises(ValueError):
            backtest_engine._open_position(
                symbol="AAPL",
                quantity=10.0,
                price=-100.0,  # Invalid negative price
                date=datetime.now(),
                side='long'
            )

    def test_zero_quantity(self, backtest_engine):
        """Test handling of zero quantity orders"""
        backtest_engine._open_position(
            symbol="AAPL",
            quantity=0.0,
            price=100.0,
            date=datetime.now(),
            side='long'
        )

        # Should not create a meaningful position
        assert backtest_engine.positions["AAPL"].quantity == 0.0


class TestPerformanceMetrics:
    """Test performance metrics calculation"""

    def test_results_structure(self, backtest_engine, sample_data):
        """Test that results contain all required fields"""
        strategy = MockStrategy()
        results = backtest_engine.run(strategy, sample_data, "AAPL")

        required_fields = [
            'symbol', 'initial_capital', 'final_equity',
            'total_trades', 'metrics', 'trades', 'equity_curve'
        ]

        for field in required_fields:
            assert field in results

    def test_final_equity_calculation(self, backtest_engine, sample_data):
        """Test final equity is calculated correctly"""
        strategy = MockStrategy()
        results = backtest_engine.run(strategy, sample_data, "AAPL")

        assert isinstance(results['final_equity'], (int, float))
        assert results['final_equity'] > 0
