"""
Unit tests for signal type validation in events.

Tests cover:
- SignalEvent validation with correct signal types (LONG, SHORT, EXIT)
- SignalEvent validation rejecting incorrect signal types
- Edge cases and boundary conditions
- Validation error messages
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.events import SignalEvent, EventType


class TestSignalEventValidation:
    """Test suite for SignalEvent signal_type validation"""

    def test_valid_signal_type_long(self):
        """Test SignalEvent accepts valid LONG signal type"""
        signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol="AAPL",
            signal_type="LONG",
            strength=0.8,
            strategy_id="test_strategy"
        )
        assert signal.signal_type == "LONG"
        assert signal.event_type == EventType.SIGNAL
        assert signal.symbol == "AAPL"
        assert signal.strength == 0.8
        assert signal.strategy_id == "test_strategy"

    def test_valid_signal_type_short(self):
        """Test SignalEvent accepts valid SHORT signal type"""
        signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol="GOOGL",
            signal_type="SHORT",
            strength=0.9,
            strategy_id="momentum"
        )
        assert signal.signal_type == "SHORT"
        assert signal.event_type == EventType.SIGNAL

    def test_valid_signal_type_exit(self):
        """Test SignalEvent accepts valid EXIT signal type"""
        signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol="MSFT",
            signal_type="EXIT",
            strength=1.0,
            strategy_id="mean_reversion"
        )
        assert signal.signal_type == "EXIT"
        assert signal.event_type == EventType.SIGNAL

    def test_invalid_signal_type_buy(self):
        """Test SignalEvent rejects BUY (should be LONG)"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="BUY",
                strength=0.8,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message
        assert "LONG" in error_message
        assert "SHORT" in error_message
        assert "EXIT" in error_message

    def test_invalid_signal_type_sell(self):
        """Test SignalEvent rejects SELL (should be SHORT or EXIT)"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="SELL",
                strength=0.8,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message

    def test_invalid_signal_type_hold(self):
        """Test SignalEvent rejects HOLD (not a valid signal)"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="HOLD",
                strength=0.0,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message

    def test_invalid_signal_type_random_string(self):
        """Test SignalEvent rejects arbitrary string"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="INVALID_SIGNAL",
                strength=0.5,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message

    def test_invalid_signal_type_empty_string(self):
        """Test SignalEvent rejects empty string"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="",
                strength=0.5,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message

    def test_invalid_signal_type_lowercase(self):
        """Test SignalEvent rejects lowercase signal types (case sensitive)"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="long",
                strength=0.8,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "Signal type must be one of" in error_message

    def test_signal_strength_validation_valid(self):
        """Test signal strength must be between 0 and 1"""
        # Valid strengths
        for strength in [0.0, 0.5, 1.0]:
            signal = SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=strength,
                strategy_id="test"
            )
            assert signal.strength == strength

    def test_signal_strength_validation_invalid_negative(self):
        """Test signal strength rejects negative values"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=-0.1,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "greater than or equal to 0" in error_message

    def test_signal_strength_validation_invalid_too_high(self):
        """Test signal strength rejects values > 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=1.1,
                strategy_id="test"
            )

        error_message = str(exc_info.value)
        assert "less than or equal to 1" in error_message

    def test_signal_event_immutable_event_type(self):
        """Test that event_type field is frozen and cannot be changed"""
        signal = SignalEvent(
            timestamp=datetime.utcnow(),
            symbol="AAPL",
            signal_type="LONG",
            strength=0.8,
            strategy_id="test"
        )

        # Pydantic frozen field should prevent modification
        with pytest.raises(ValidationError):
            signal.event_type = EventType.MARKET

    def test_signal_event_required_fields(self):
        """Test that all required fields must be provided"""
        # Missing symbol
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                signal_type="LONG",
                strength=0.8,
                strategy_id="test"
            )

        # Missing signal_type
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                strength=0.8,
                strategy_id="test"
            )

        # Missing strength
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strategy_id="test"
            )

        # Missing strategy_id
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=0.8
            )

    def test_signal_event_timestamp_default(self):
        """Test that timestamp has a default value if not provided"""
        before = datetime.utcnow()
        signal = SignalEvent(
            symbol="AAPL",
            signal_type="LONG",
            strength=0.8,
            strategy_id="test"
        )
        after = datetime.utcnow()

        assert before <= signal.timestamp <= after

    def test_multiple_signals_different_types(self):
        """Test creating multiple signals with different valid types"""
        signals = [
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="AAPL",
                signal_type="LONG",
                strength=0.8,
                strategy_id="test"
            ),
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="GOOGL",
                signal_type="SHORT",
                strength=0.9,
                strategy_id="test"
            ),
            SignalEvent(
                timestamp=datetime.utcnow(),
                symbol="MSFT",
                signal_type="EXIT",
                strength=1.0,
                strategy_id="test"
            ),
        ]

        assert len(signals) == 3
        assert signals[0].signal_type == "LONG"
        assert signals[1].signal_type == "SHORT"
        assert signals[2].signal_type == "EXIT"
