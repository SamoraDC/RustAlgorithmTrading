"""
Integration tests for signal validation in the full backtest flow.

Tests cover:
- End-to-end signal generation through backtest engine
- Signal type conversion from Strategy to SignalEvent
- Validation that only valid signal types are processed
- Error handling for invalid signal types
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.backtesting.engine import BacktestEngine
from src.backtesting.data_handler import HistoricalDataHandler
from src.backtesting.execution_handler import SimulatedExecutionHandler
from src.backtesting.portfolio_handler import PortfolioHandler
from src.strategies.momentum import MomentumStrategy
from src.strategies.base import Strategy, Signal, SignalType
from src.models.events import SignalEvent


class MockDataHandler:
    """Mock data handler for testing"""

    def __init__(self, data: pd.DataFrame, symbols: list):
        self.data = data
        self.symbols = symbols
        self.continue_backtest = True
        self.current_index = 0

    def update_bars(self):
        """Update to next bar"""
        self.current_index += 1
        if self.current_index >= len(self.data):
            self.continue_backtest = False

    def get_latest_bars(self, symbol: str, n: int = 1):
        """Get latest N bars"""
        if self.current_index == 0:
            return []

        end_idx = min(self.current_index, len(self.data))
        start_idx = max(0, end_idx - n)

        bars_df = self.data.iloc[start_idx:end_idx]

        # Convert to bar objects (simplified)
        bars = []
        for idx, row in bars_df.iterrows():
            bar = type('Bar', (), {
                'timestamp': idx,
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            })()
            bars.append(bar)

        return bars


class TestBacktestSignalValidation:
    """Integration tests for signal validation in backtest flow"""

    def create_test_data(self, periods=100) -> pd.DataFrame:
        """Create test market data"""
        dates = pd.date_range(end=datetime.utcnow(), periods=periods, freq='1D')

        base_price = 100.0
        trend = np.linspace(0, 20, periods)
        oscillation = 10 * np.sin(np.linspace(0, 4 * np.pi, periods))
        prices = base_price + trend + oscillation

        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, periods)
        }, index=dates)

        return df

    def test_backtest_processes_valid_signal_types(self):
        """Test that backtest engine processes signals with valid types"""
        # Create test data
        data = self.create_test_data(periods=100)
        symbols = ['AAPL']

        # Initialize components
        data_handler = MockDataHandler(data, symbols)
        execution_handler = SimulatedExecutionHandler()
        portfolio_handler = PortfolioHandler(initial_capital=100000.0)
        strategy = MomentumStrategy()

        # Create engine
        engine = BacktestEngine(
            data_handler=data_handler,
            execution_handler=execution_handler,
            portfolio_handler=portfolio_handler,
            strategy=strategy
        )

        # Run backtest - should complete without validation errors
        results = engine.run()

        # Verify results structure
        assert 'metrics' in results
        assert 'execution_stats' in results
        assert results['execution_stats']['events_processed'] > 0

    def test_signal_event_creation_from_strategy_signals(self):
        """Test conversion from Strategy Signal to SignalEvent"""
        # Create a strategy signal
        strategy_signal = Signal(
            timestamp=datetime.utcnow(),
            symbol="AAPL",
            signal_type=SignalType.LONG,
            price=150.0,
            confidence=0.85,
            metadata={'rsi': 35.0}
        )

        # Simulate conversion in backtest engine
        signal_event = SignalEvent(
            timestamp=strategy_signal.timestamp,
            symbol=strategy_signal.symbol,
            signal_type=strategy_signal.signal_type.value,  # Convert enum to string
            strength=strategy_signal.confidence,
            strategy_id="test_strategy"
        )

        # Verify conversion
        assert signal_event.signal_type == "LONG"
        assert signal_event.symbol == "AAPL"
        assert signal_event.strength == 0.85
        assert signal_event.strategy_id == "test_strategy"

    def test_signal_event_rejects_invalid_type_from_strategy(self):
        """Test that invalid signal types are caught during conversion"""
        # Create a strategy signal with invalid type (simulating a bug)
        strategy_signal = Signal(
            timestamp=datetime.utcnow(),
            symbol="AAPL",
            signal_type=SignalType.HOLD,  # HOLD is not valid for SignalEvent
            price=150.0,
            confidence=0.5
        )

        # Attempting to create SignalEvent with HOLD should fail
        with pytest.raises(ValidationError) as exc_info:
            signal_event = SignalEvent(
                timestamp=strategy_signal.timestamp,
                symbol=strategy_signal.symbol,
                signal_type=strategy_signal.signal_type.value,
                strength=strategy_signal.confidence,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message

    def test_multiple_signal_types_in_backtest(self):
        """Test backtest processes multiple different signal types"""
        # Create signals of different types
        signals = [
            Signal(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type=SignalType.LONG,
                price=150.0,
                confidence=0.8
            ),
            Signal(
                timestamp=datetime.utcnow() + timedelta(hours=1),
                symbol="AAPL",
                signal_type=SignalType.SHORT,
                price=155.0,
                confidence=0.9
            ),
            Signal(
                timestamp=datetime.utcnow() + timedelta(hours=2),
                symbol="AAPL",
                signal_type=SignalType.EXIT,
                price=152.0,
                confidence=1.0
            ),
        ]

        # Convert all to SignalEvents
        signal_events = []
        for signal in signals:
            event = SignalEvent(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                signal_type=signal.signal_type.value,
                strength=signal.confidence,
                strategy_id="test"
            )
            signal_events.append(event)

        # Verify all converted successfully
        assert len(signal_events) == 3
        assert signal_events[0].signal_type == "LONG"
        assert signal_events[1].signal_type == "SHORT"
        assert signal_events[2].signal_type == "EXIT"

    def test_signal_validation_catches_case_sensitivity(self):
        """Test that signal validation is case-sensitive"""
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="long",  # lowercase should fail
                strength=0.8,
                strategy_id="test"
            )

        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="Long",  # mixed case should fail
                strength=0.8,
                strategy_id="test"
            )

    def test_backtest_signal_count_accuracy(self):
        """Test that backtest correctly counts generated signals"""
        data = self.create_test_data(periods=100)
        symbols = ['AAPL']

        data_handler = MockDataHandler(data, symbols)
        execution_handler = SimulatedExecutionHandler()
        portfolio_handler = PortfolioHandler(initial_capital=100000.0)
        strategy = MomentumStrategy()

        engine = BacktestEngine(
            data_handler=data_handler,
            execution_handler=execution_handler,
            portfolio_handler=portfolio_handler,
            strategy=strategy
        )

        results = engine.run()

        # Verify signal count is tracked
        assert 'execution_stats' in results
        assert 'signals_generated' in results['execution_stats']
        assert results['execution_stats']['signals_generated'] >= 0


class TestSignalTypeEdgeCases:
    """Test edge cases in signal type handling"""

    def test_signal_with_none_type(self):
        """Test that None signal type is rejected"""
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type=None,
                strength=0.8,
                strategy_id="test"
            )

    def test_signal_with_numeric_type(self):
        """Test that numeric signal type is rejected"""
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type=123,
                strength=0.8,
                strategy_id="test"
            )

    def test_signal_with_special_characters(self):
        """Test that signal types with special characters are rejected"""
        invalid_types = ["LONG!", "SHORT@", "EXIT#", "L O N G", "LONG\n"]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError):
                SignalEvent(
                    timestamp=datetime.utcnow(),
                    symbol="AAPL",
                    signal_type=invalid_type,
                    strength=0.8,
                    strategy_id="test"
                )

    def test_signal_strength_edge_cases(self):
        """Test signal strength boundary conditions"""
        # Exactly 0.0 should work
        signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol="AAPL",
            signal_type="LONG",
            strength=0.0,
            strategy_id="test"
        )
        assert signal.strength == 0.0

        # Exactly 1.0 should work
        signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol="AAPL",
            signal_type="LONG",
            strength=1.0,
            strategy_id="test"
        )
        assert signal.strength == 1.0

        # Just below 0 should fail
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=-0.0001,
                strategy_id="test"
            )

        # Just above 1 should fail
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=1.0001,
                strategy_id="test"
            )


class TestSignalValidationPerformance:
    """Test that signal validation doesn't significantly impact performance"""

    def test_rapid_signal_creation(self):
        """Test creating many signals rapidly"""
        import time

        num_signals = 1000
        start_time = time.time()

        signals = []
        for i in range(num_signals):
            signal = SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG" if i % 3 == 0 else "SHORT" if i % 3 == 1 else "EXIT",
                strength=0.8,
                strategy_id="test"
            )
            signals.append(signal)

        elapsed = time.time() - start_time

        # Should be able to create 1000 signals quickly (< 1 second)
        assert elapsed < 1.0
        assert len(signals) == num_signals

    def test_validation_error_performance(self):
        """Test that validation errors don't slow down system significantly"""
        import time

        num_attempts = 100
        start_time = time.time()

        for i in range(num_attempts):
            try:
                SignalEvent(
                    timestamp=datetime.utcnow(),
                    symbol="AAPL",
                    signal_type="INVALID",
                    strength=0.8,
                    strategy_id="test"
                )
            except ValidationError:
                pass  # Expected

        elapsed = time.time() - start_time

        # Even with validation errors, should complete quickly
        assert elapsed < 1.0
