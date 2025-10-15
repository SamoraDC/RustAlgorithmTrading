"""
Unit tests for base Strategy class and Signal functionality
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.strategies.base import Strategy, Signal, SignalType


class ConcreteStrategy(Strategy):
    """Concrete implementation for testing abstract Strategy class"""

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Simple signal generation for testing"""
        signals = []
        for i, (idx, row) in enumerate(data.iterrows()):
            if i % 10 == 0:  # Generate signal every 10 rows
                signals.append(Signal(
                    timestamp=idx,
                    symbol=data.attrs.get('symbol', 'TEST'),
                    signal_type=SignalType.BUY if i % 20 == 0 else SignalType.SELL,
                    price=row['close'],
                    confidence=0.8
                ))
        return signals

    def calculate_position_size(self, signal: Signal, account_value: float, current_position: float = 0.0) -> float:
        """Simple fixed position sizing"""
        return 10.0


@pytest.fixture
def sample_data():
    """Sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1h')
    np.random.seed(42)

    data = pd.DataFrame({
        'open': 100 + np.random.randn(50),
        'high': 102 + np.random.randn(50),
        'low': 98 + np.random.randn(50),
        'close': 100 + np.random.randn(50),
        'volume': np.random.randint(1000, 5000, 50)
    }, index=dates)

    data.attrs['symbol'] = 'AAPL'
    return data


class TestSignalCreation:
    """Test Signal dataclass"""

    def test_signal_creation_basic(self):
        """Test basic signal creation"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=150.0
        )

        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.price == 150.0
        assert signal.quantity == 0.0
        assert signal.confidence == 1.0
        assert signal.metadata == {}

    def test_signal_creation_full(self):
        """Test signal creation with all fields"""
        metadata = {'reason': 'oversold', 'indicator': 'RSI'}

        signal = Signal(
            timestamp=datetime.now(),
            symbol="GOOGL",
            signal_type=SignalType.SELL,
            price=2800.0,
            quantity=5.0,
            confidence=0.85,
            metadata=metadata
        )

        assert signal.symbol == "GOOGL"
        assert signal.signal_type == SignalType.SELL
        assert signal.price == 2800.0
        assert signal.quantity == 5.0
        assert signal.confidence == 0.85
        assert signal.metadata == metadata

    def test_signal_types(self):
        """Test all signal types"""
        buy_signal = Signal(datetime.now(), "AAPL", SignalType.BUY, 100.0)
        sell_signal = Signal(datetime.now(), "AAPL", SignalType.SELL, 100.0)
        hold_signal = Signal(datetime.now(), "AAPL", SignalType.HOLD, 100.0)

        assert buy_signal.signal_type == SignalType.BUY
        assert sell_signal.signal_type == SignalType.SELL
        assert hold_signal.signal_type == SignalType.HOLD

    def test_signal_metadata_initialization(self):
        """Test that metadata defaults to empty dict"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0
        )

        assert isinstance(signal.metadata, dict)
        assert len(signal.metadata) == 0


class TestStrategyInitialization:
    """Test Strategy initialization"""

    def test_initialization_basic(self):
        """Test basic strategy initialization"""
        strategy = ConcreteStrategy(name="TestStrategy")

        assert strategy.name == "TestStrategy"
        assert strategy.parameters == {}
        assert strategy.signals == []
        assert strategy.positions == {}

    def test_initialization_with_parameters(self):
        """Test initialization with parameters"""
        params = {
            'lookback': 20,
            'threshold': 0.02,
            'risk_pct': 0.01
        }

        strategy = ConcreteStrategy(name="ParamStrategy", parameters=params)

        assert strategy.name == "ParamStrategy"
        assert strategy.parameters == params
        assert strategy.get_parameter('lookback') == 20
        assert strategy.get_parameter('threshold') == 0.02

    def test_initialization_none_parameters(self):
        """Test initialization with None parameters"""
        strategy = ConcreteStrategy(name="NoneParams", parameters=None)

        assert strategy.parameters == {}


class TestParameterManagement:
    """Test parameter getter/setter methods"""

    def test_get_parameter_existing(self):
        """Test getting existing parameter"""
        params = {'key1': 'value1', 'key2': 42}
        strategy = ConcreteStrategy(name="Test", parameters=params)

        assert strategy.get_parameter('key1') == 'value1'
        assert strategy.get_parameter('key2') == 42

    def test_get_parameter_nonexistent(self):
        """Test getting non-existent parameter"""
        strategy = ConcreteStrategy(name="Test")

        assert strategy.get_parameter('nonexistent') is None

    def test_get_parameter_with_default(self):
        """Test getting parameter with default value"""
        strategy = ConcreteStrategy(name="Test")

        result = strategy.get_parameter('missing', default='default_value')
        assert result == 'default_value'

    def test_set_parameter(self):
        """Test setting parameter"""
        strategy = ConcreteStrategy(name="Test")

        strategy.set_parameter('new_key', 'new_value')

        assert strategy.get_parameter('new_key') == 'new_value'
        assert strategy.parameters['new_key'] == 'new_value'

    def test_set_parameter_update_existing(self):
        """Test updating existing parameter"""
        strategy = ConcreteStrategy(name="Test", parameters={'key': 'old'})

        strategy.set_parameter('key', 'new')

        assert strategy.get_parameter('key') == 'new'


class TestDataValidation:
    """Test data validation methods"""

    def test_validate_valid_data(self, sample_data):
        """Test validation with valid data"""
        strategy = ConcreteStrategy(name="Test")

        assert strategy.validate_data(sample_data) is True

    def test_validate_missing_column(self, sample_data):
        """Test validation with missing required column"""
        strategy = ConcreteStrategy(name="Test")

        # Remove a required column
        incomplete_data = sample_data.drop(columns=['volume'])

        assert strategy.validate_data(incomplete_data) is False

    def test_validate_missing_multiple_columns(self):
        """Test validation with multiple missing columns"""
        strategy = ConcreteStrategy(name="Test")

        # Create data with only some columns
        partial_data = pd.DataFrame({
            'open': [100, 101, 102],
            'close': [101, 102, 103]
        })

        assert strategy.validate_data(partial_data) is False

    def test_validate_empty_dataframe(self):
        """Test validation with empty DataFrame"""
        strategy = ConcreteStrategy(name="Test")

        empty_data = pd.DataFrame()

        assert strategy.validate_data(empty_data) is False


class TestSignalGeneration:
    """Test signal generation"""

    def test_generate_signals(self, sample_data):
        """Test signal generation produces signals"""
        strategy = ConcreteStrategy(name="Test")

        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, list)
        assert len(signals) > 0
        assert all(isinstance(s, Signal) for s in signals)

    def test_generated_signals_have_correct_symbol(self, sample_data):
        """Test generated signals have correct symbol"""
        strategy = ConcreteStrategy(name="Test")

        signals = strategy.generate_signals(sample_data)

        for signal in signals:
            assert signal.symbol == 'AAPL'

    def test_generated_signals_have_valid_prices(self, sample_data):
        """Test generated signals have valid prices"""
        strategy = ConcreteStrategy(name="Test")

        signals = strategy.generate_signals(sample_data)

        for signal in signals:
            assert signal.price > 0
            # Price should be from the data
            assert signal.price in sample_data['close'].values


class TestPositionLogic:
    """Test position entry/exit logic"""

    def test_should_enter_buy_signal(self):
        """Test should_enter with BUY signal"""
        strategy = ConcreteStrategy(name="Test")

        buy_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0
        )

        assert strategy.should_enter(buy_signal) is True

    def test_should_enter_sell_signal(self):
        """Test should_enter with SELL signal"""
        strategy = ConcreteStrategy(name="Test")

        sell_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.SELL,
            price=100.0
        )

        assert strategy.should_enter(sell_signal) is True

    def test_should_enter_hold_signal(self):
        """Test should_enter with HOLD signal"""
        strategy = ConcreteStrategy(name="Test")

        hold_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.HOLD,
            price=100.0
        )

        assert strategy.should_enter(hold_signal) is False

    def test_should_exit_long_with_sell(self):
        """Test should_exit long position with SELL signal"""
        strategy = ConcreteStrategy(name="Test")

        sell_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.SELL,
            price=100.0
        )

        # Positive position = long
        assert strategy.should_exit(sell_signal, current_position=10.0) is True

    def test_should_exit_short_with_buy(self):
        """Test should_exit short position with BUY signal"""
        strategy = ConcreteStrategy(name="Test")

        buy_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0
        )

        # Negative position = short
        assert strategy.should_exit(buy_signal, current_position=-10.0) is True

    def test_should_exit_no_position(self):
        """Test should_exit with no position"""
        strategy = ConcreteStrategy(name="Test")

        sell_signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.SELL,
            price=100.0
        )

        assert strategy.should_exit(sell_signal, current_position=0.0) is False


class TestPositionSizing:
    """Test position sizing"""

    def test_calculate_position_size(self):
        """Test position size calculation"""
        strategy = ConcreteStrategy(name="Test")

        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0
        )

        position_size = strategy.calculate_position_size(
            signal=signal,
            account_value=100000.0,
            current_position=0.0
        )

        assert position_size == 10.0  # Fixed size in our implementation

    def test_position_size_with_existing_position(self):
        """Test position sizing with existing position"""
        strategy = ConcreteStrategy(name="Test")

        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0
        )

        position_size = strategy.calculate_position_size(
            signal=signal,
            account_value=100000.0,
            current_position=5.0
        )

        assert position_size == 10.0


class TestStrategyState:
    """Test strategy state management"""

    def test_reset(self):
        """Test strategy reset"""
        strategy = ConcreteStrategy(name="Test")

        # Add some state
        strategy.signals = [Signal(datetime.now(), "AAPL", SignalType.BUY, 100.0)]
        strategy.positions = {"AAPL": 10.0}

        # Reset
        strategy.reset()

        assert strategy.signals == []
        assert strategy.positions == {}

    def test_reset_preserves_parameters(self):
        """Test that reset preserves parameters"""
        params = {'key': 'value'}
        strategy = ConcreteStrategy(name="Test", parameters=params)

        strategy.reset()

        assert strategy.parameters == params
        assert strategy.name == "Test"


class TestStrategyRepresentation:
    """Test strategy string representation"""

    def test_repr(self):
        """Test __repr__ method"""
        params = {'lookback': 20, 'threshold': 0.02}
        strategy = ConcreteStrategy(name="TestStrategy", parameters=params)

        repr_str = repr(strategy)

        assert "Strategy" in repr_str
        assert "TestStrategy" in repr_str
        assert "lookback" in repr_str
        assert "threshold" in repr_str


class TestEdgeCases:
    """Test edge cases"""

    def test_empty_data_signal_generation(self):
        """Test signal generation with empty data"""
        strategy = ConcreteStrategy(name="Test")

        empty_data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        empty_data.attrs['symbol'] = 'AAPL'

        signals = strategy.generate_signals(empty_data)

        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_confidence_bounds(self):
        """Test signal confidence is bounded [0, 1]"""
        signal_low = Signal(datetime.now(), "AAPL", SignalType.BUY, 100.0, confidence=0.0)
        signal_high = Signal(datetime.now(), "AAPL", SignalType.BUY, 100.0, confidence=1.0)

        assert 0.0 <= signal_low.confidence <= 1.0
        assert 0.0 <= signal_high.confidence <= 1.0

    def test_signal_with_none_metadata(self):
        """Test signal handles None metadata correctly"""
        signal = Signal(
            timestamp=datetime.now(),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            price=100.0,
            metadata=None
        )

        assert isinstance(signal.metadata, dict)
        assert len(signal.metadata) == 0
