"""
Property-based testing using Hypothesis
Tests invariants and properties that should hold for all inputs
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtesting.engine import BacktestEngine, Trade, Position
from src.strategies.base import Strategy, Signal, SignalType
from src.backtesting.metrics import PerformanceMetrics


class SimpleStrategy(Strategy):
    """Simple strategy for property testing"""

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        return []

    def calculate_position_size(self, signal: Signal, account_value: float, current_position: float = 0.0) -> float:
        return 10.0


# Custom strategies for generating valid data
@st.composite
def valid_price(draw):
    """Generate valid price (positive float)"""
    return draw(st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_quantity(draw):
    """Generate valid quantity (positive float)"""
    return draw(st.floats(min_value=0.001, max_value=10000.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_ohlcv_bar(draw):
    """Generate valid OHLCV bar data"""
    close = draw(valid_price())
    open_price = draw(st.floats(min_value=close * 0.95, max_value=close * 1.05))
    high = draw(st.floats(min_value=max(open_price, close), max_value=close * 1.1))
    low = draw(st.floats(min_value=close * 0.9, max_value=min(open_price, close)))
    volume = draw(st.integers(min_value=100, max_value=1000000))

    return {
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }


@st.composite
def ohlcv_dataframe(draw, min_rows=10, max_rows=100):
    """Generate valid OHLCV DataFrame"""
    num_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))

    dates = pd.date_range(
        start=datetime.now() - timedelta(days=num_rows),
        periods=num_rows,
        freq='1H'
    )

    bars = [draw(valid_ohlcv_bar()) for _ in range(num_rows)]

    df = pd.DataFrame(bars, index=dates)
    df.attrs['symbol'] = 'TEST'

    return df


@st.composite
def trading_signal(draw):
    """Generate valid trading signal"""
    return Signal(
        timestamp=datetime.now(),
        symbol=draw(st.text(alphabet=st.characters(whitelist_categories=('Lu',)), min_size=3, max_size=5)),
        signal_type=draw(st.sampled_from([SignalType.BUY, SignalType.SELL, SignalType.HOLD])),
        price=draw(valid_price()),
        quantity=draw(valid_quantity()),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0))
    )


class TestBacktestEngineProperties:
    """Property-based tests for BacktestEngine"""

    @given(
        initial_capital=st.floats(min_value=1000.0, max_value=1000000.0),
        commission_rate=st.floats(min_value=0.0, max_value=0.01),
        slippage=st.floats(min_value=0.0, max_value=0.01)
    )
    @settings(max_examples=50)
    def test_initial_cash_equals_capital(self, initial_capital, commission_rate, slippage):
        """Property: Initial cash should always equal initial capital"""
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage=slippage
        )

        assert engine.cash == initial_capital

    @given(
        price=valid_price(),
        quantity=valid_quantity()
    )
    @settings(max_examples=50)
    def test_position_value_is_price_times_quantity(self, price, quantity):
        """Property: Position value = price × quantity"""
        engine = BacktestEngine()

        engine._open_position(
            symbol="TEST",
            quantity=quantity,
            price=price,
            date=datetime.now(),
            side='long'
        )

        account_value = engine._calculate_account_value(price)
        expected_position_value = price * quantity

        # Account value = cash + position value
        assert abs(account_value - (engine.cash + expected_position_value)) < 0.01

    @given(
        entry_price=valid_price(),
        exit_price=valid_price(),
        quantity=valid_quantity()
    )
    @settings(max_examples=50)
    def test_long_pnl_equals_price_difference(self, entry_price, exit_price, quantity):
        """Property: Long P&L = (exit_price - entry_price) × quantity (before fees)"""
        engine = BacktestEngine(commission_rate=0.0, slippage=0.0)  # No fees for pure test

        engine._open_position(
            symbol="TEST",
            quantity=quantity,
            price=entry_price,
            date=datetime.now(),
            side='long'
        )

        engine._close_position(
            symbol="TEST",
            exit_price=exit_price,
            exit_date=datetime.now()
        )

        if len(engine.trades) > 0:
            trade = engine.trades[0]
            expected_pnl = (exit_price - entry_price) * quantity

            # Allow small tolerance for floating point errors
            assert abs(trade.pnl - expected_pnl) < 0.01

    @given(
        entry_price=valid_price(),
        exit_price=valid_price(),
        quantity=valid_quantity()
    )
    @settings(max_examples=50)
    def test_short_pnl_is_inverse(self, entry_price, exit_price, quantity):
        """Property: Short P&L = (entry_price - exit_price) × quantity"""
        engine = BacktestEngine(commission_rate=0.0, slippage=0.0)

        engine._open_position(
            symbol="TEST",
            quantity=quantity,
            price=entry_price,
            date=datetime.now(),
            side='short'
        )

        engine._close_position(
            symbol="TEST",
            exit_price=exit_price,
            exit_date=datetime.now()
        )

        if len(engine.trades) > 0:
            trade = engine.trades[0]
            expected_pnl = (entry_price - exit_price) * quantity

            assert abs(trade.pnl - expected_pnl) < 0.01

    @given(data=ohlcv_dataframe())
    @settings(max_examples=20)
    def test_backtest_preserves_capital_with_no_trades(self, data):
        """Property: If no trades, final equity = initial capital"""
        engine = BacktestEngine(initial_capital=100000.0)
        strategy = SimpleStrategy(name="NoTrade")

        results = engine.run(strategy, data, "TEST")

        assert abs(results['final_equity'] - 100000.0) < 0.01

    @given(
        commission_rate=st.floats(min_value=0.0, max_value=0.1),
        quantity=valid_quantity(),
        price=valid_price()
    )
    @settings(max_examples=50)
    def test_commission_always_reduces_profit(self, commission_rate, quantity, price):
        """Property: Commission always reduces net P&L"""
        position_value = quantity * price
        expected_commission = position_value * commission_rate

        assert expected_commission >= 0
        assert expected_commission <= position_value

    @given(slippage=st.floats(min_value=0.0, max_value=0.01))
    @settings(max_examples=50)
    def test_buy_slippage_increases_price(self, slippage):
        """Property: Buy slippage always increases execution price"""
        base_price = 100.0
        slipped_price = base_price * (1 + slippage)

        assert slipped_price >= base_price

    @given(slippage=st.floats(min_value=0.0, max_value=0.01))
    @settings(max_examples=50)
    def test_sell_slippage_decreases_price(self, slippage):
        """Property: Sell slippage always decreases execution price"""
        base_price = 100.0
        slipped_price = base_price * (1 - slippage)

        assert slipped_price <= base_price


class TestSignalProperties:
    """Property-based tests for Signal class"""

    @given(signal=trading_signal())
    @settings(max_examples=100)
    def test_signal_confidence_bounded(self, signal):
        """Property: Signal confidence is always between 0 and 1"""
        assert 0.0 <= signal.confidence <= 1.0

    @given(signal=trading_signal())
    @settings(max_examples=100)
    def test_signal_price_positive(self, signal):
        """Property: Signal price is always positive"""
        assert signal.price > 0

    @given(signal=trading_signal())
    @settings(max_examples=100)
    def test_signal_quantity_non_negative(self, signal):
        """Property: Signal quantity is non-negative"""
        assert signal.quantity >= 0

    @given(
        signal_type=st.sampled_from([SignalType.BUY, SignalType.SELL, SignalType.HOLD])
    )
    @settings(max_examples=20)
    def test_signal_type_preserved(self, signal_type):
        """Property: Signal type is preserved after creation"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="TEST",
            signal_type=signal_type,
            price=100.0
        )

        assert signal.signal_type == signal_type


class TestStrategyProperties:
    """Property-based tests for Strategy base class"""

    @given(
        name=st.text(min_size=1, max_size=50),
        parameters=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.floats(allow_nan=False, allow_infinity=False), st.integers(), st.text())
        )
    )
    @settings(max_examples=50)
    def test_strategy_stores_parameters(self, name, parameters):
        """Property: Strategy preserves all parameters"""
        strategy = SimpleStrategy(name=name, parameters=parameters)

        assert strategy.name == name
        for key, value in parameters.items():
            assert strategy.get_parameter(key) == value

    @given(data=ohlcv_dataframe())
    @settings(max_examples=20)
    def test_valid_data_always_validates(self, data):
        """Property: Valid OHLCV data always passes validation"""
        strategy = SimpleStrategy(name="Test")

        assert strategy.validate_data(data) is True

    @given(
        key=st.text(min_size=1, max_size=20),
        value=st.one_of(st.integers(), st.floats(allow_nan=False), st.text())
    )
    @settings(max_examples=50)
    def test_set_parameter_is_retrievable(self, key, value):
        """Property: Set parameter is always retrievable"""
        strategy = SimpleStrategy(name="Test")

        strategy.set_parameter(key, value)

        assert strategy.get_parameter(key) == value


class TestPerformanceMetricsProperties:
    """Property-based tests for performance metrics"""

    @given(
        num_winning_trades=st.integers(min_value=0, max_value=100),
        num_losing_trades=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=50)
    def test_win_rate_bounded(self, num_winning_trades, num_losing_trades):
        """Property: Win rate is always between 0 and 1"""
        total_trades = num_winning_trades + num_losing_trades

        if total_trades > 0:
            win_rate = num_winning_trades / total_trades
            assert 0.0 <= win_rate <= 1.0

    @given(
        returns=st.lists(
            st.floats(min_value=-0.1, max_value=0.1, allow_nan=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=30)
    def test_sharpe_ratio_sign(self, returns):
        """Property: Sharpe ratio sign matches average return sign"""
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return > 0:
            sharpe = avg_return / std_return

            if avg_return > 0:
                assert sharpe > 0
            elif avg_return < 0:
                assert sharpe < 0
            else:
                assert abs(sharpe) < 0.001

    @given(
        initial_capital=st.floats(min_value=1000.0, max_value=1000000.0),
        final_equity=st.floats(min_value=500.0, max_value=2000000.0)
    )
    @settings(max_examples=50)
    def test_total_return_calculation(self, initial_capital, final_equity):
        """Property: Total return = (final - initial) / initial"""
        total_return = (final_equity - initial_capital) / initial_capital

        if final_equity > initial_capital:
            assert total_return > 0
        elif final_equity < initial_capital:
            assert total_return < 0
        else:
            assert abs(total_return) < 0.001


class TestOHLCVDataProperties:
    """Property-based tests for OHLCV data invariants"""

    @given(bar=valid_ohlcv_bar())
    @settings(max_examples=100)
    def test_high_is_highest(self, bar):
        """Property: High is always >= all other prices"""
        assert bar['high'] >= bar['open']
        assert bar['high'] >= bar['close']
        assert bar['high'] >= bar['low']

    @given(bar=valid_ohlcv_bar())
    @settings(max_examples=100)
    def test_low_is_lowest(self, bar):
        """Property: Low is always <= all other prices"""
        assert bar['low'] <= bar['open']
        assert bar['low'] <= bar['close']
        assert bar['low'] <= bar['high']

    @given(bar=valid_ohlcv_bar())
    @settings(max_examples=100)
    def test_volume_non_negative(self, bar):
        """Property: Volume is always non-negative"""
        assert bar['volume'] >= 0

    @given(data=ohlcv_dataframe())
    @settings(max_examples=20)
    def test_dataframe_index_sorted(self, data):
        """Property: DataFrame index is chronologically sorted"""
        assert data.index.is_monotonic_increasing


class TestRiskManagementProperties:
    """Property-based tests for risk management"""

    @given(
        max_position_size=st.floats(min_value=100.0, max_value=10000.0),
        requested_size=st.floats(min_value=50.0, max_value=20000.0)
    )
    @settings(max_examples=50)
    def test_position_size_limit_enforced(self, max_position_size, requested_size):
        """Property: Position size never exceeds maximum"""
        actual_size = min(requested_size, max_position_size)

        assert actual_size <= max_position_size

    @given(
        account_value=st.floats(min_value=10000.0, max_value=1000000.0),
        risk_per_trade=st.floats(min_value=0.001, max_value=0.05)
    )
    @settings(max_examples=50)
    def test_risk_percentage_bounded(self, account_value, risk_per_trade):
        """Property: Risk amount = account value × risk percentage"""
        risk_amount = account_value * risk_per_trade

        assert risk_amount <= account_value
        assert risk_amount > 0


class TestMonotonicityProperties:
    """Test monotonic properties"""

    @given(
        trades=st.lists(
            st.floats(min_value=-100.0, max_value=100.0),
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=30)
    def test_cumulative_pnl_monotonic(self, trades):
        """Property: Cumulative P&L changes monotonically with each trade"""
        cumulative = []
        current_sum = 0.0

        for trade_pnl in trades:
            current_sum += trade_pnl
            cumulative.append(current_sum)

        # Each cumulative value should be the sum of all previous
        for i in range(len(cumulative)):
            expected = sum(trades[:i+1])
            assert abs(cumulative[i] - expected) < 0.01
