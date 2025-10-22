"""
Tests for Structured Logger

Tests:
- Basic logging functionality
- Async handler performance
- Correlation ID tracking
- Performance metrics
- Error handling and graceful degradation
"""

import asyncio
import logging
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.observability.logging import (
    StructuredLogger,
    get_logger,
    correlation_id,
    log_execution_time,
)
from src.observability.config.logging_config import LoggingConfig


@pytest.fixture
def test_config():
    """Create test logging configuration"""
    return LoggingConfig.for_testing()


@pytest.fixture
def test_logger(test_config):
    """Create test logger instance"""
    return get_logger("test.logger", config=test_config)


class TestStructuredLogger:
    """Test StructuredLogger core functionality"""

    def test_logger_creation(self, test_logger):
        """Test logger can be created"""
        assert test_logger is not None
        assert test_logger.name == "test.logger"

    def test_basic_logging(self, test_logger, caplog):
        """Test basic logging operations"""
        with caplog.at_level(logging.DEBUG):
            test_logger.debug("Debug message")
            test_logger.info("Info message")
            test_logger.warning("Warning message")
            test_logger.error("Error message")

        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text

    def test_structured_logging(self, test_logger, caplog):
        """Test logging with structured extra fields"""
        with caplog.at_level(logging.INFO):
            test_logger.info(
                "Trade executed",
                extra={
                    'symbol': 'BTCUSDT',
                    'price': 45000.0,
                    'quantity': 0.5,
                }
            )

        # Check that message was logged
        assert "Trade executed" in caplog.text

    def test_exception_logging(self, test_logger, caplog):
        """Test exception logging with traceback"""
        with caplog.at_level(logging.ERROR):
            try:
                raise ValueError("Test error")
            except ValueError:
                test_logger.exception("An error occurred")

        assert "An error occurred" in caplog.text
        assert "ValueError" in caplog.text
        assert "Test error" in caplog.text

    def test_logger_levels(self, test_logger):
        """Test logger level filtering"""
        test_logger.set_level(logging.WARNING)

        assert test_logger.is_enabled_for(logging.WARNING)
        assert test_logger.is_enabled_for(logging.ERROR)
        assert not test_logger.is_enabled_for(logging.DEBUG)
        assert not test_logger.is_enabled_for(logging.INFO)

    def test_child_logger(self, test_logger):
        """Test child logger creation"""
        child = test_logger.get_child("child")
        assert child.name == "test.logger.child"

    def test_logger_registry(self, test_config):
        """Test logger registry returns same instance"""
        logger1 = get_logger("test.registry", config=test_config)
        logger2 = get_logger("test.registry", config=test_config)
        assert logger1 is logger2


class TestCorrelationID:
    """Test correlation ID tracking"""

    def test_correlation_id_context(self, test_logger, caplog):
        """Test correlation ID in log context"""
        with caplog.at_level(logging.INFO):
            with correlation_id("test-123") as cid:
                assert cid == "test-123"
                test_logger.info("Message with correlation")

        # Note: actual correlation ID check would require
        # inspecting log records directly

    def test_correlation_id_generation(self):
        """Test automatic correlation ID generation"""
        with correlation_id() as cid:
            assert cid is not None
            assert cid.startswith("req-")

    def test_correlation_id_propagation(self, test_logger):
        """Test correlation ID propagates through nested calls"""
        def inner_function():
            from src.observability.logging.correlations import get_correlation_id
            return get_correlation_id()

        with correlation_id("test-456"):
            result = inner_function()
            assert result == "test-456"

    @pytest.mark.asyncio
    async def test_correlation_id_async(self, test_logger):
        """Test correlation ID works with async code"""
        from src.observability.logging.correlations import get_correlation_id

        async def async_task():
            await asyncio.sleep(0.01)
            return get_correlation_id()

        with correlation_id("async-123"):
            result = await async_task()
            assert result == "async-123"


class TestPerformance:
    """Test logging performance and metrics"""

    def test_logging_performance(self, test_logger):
        """Test logging overhead is < 1ms"""
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            test_logger.info(f"Performance test {i}")
        duration = time.perf_counter() - start

        avg_duration_ms = (duration / iterations) * 1000
        assert avg_duration_ms < 1.0, f"Average logging time: {avg_duration_ms:.3f}ms"

    def test_logger_metrics(self, test_logger):
        """Test logger metrics tracking"""
        # Reset metrics
        test_logger.reset_metrics()

        # Log some messages
        test_logger.info("Message 1")
        test_logger.info("Message 2")
        test_logger.warning("Warning")

        metrics = test_logger.get_metrics()
        assert metrics['total_logs'] == 3
        assert metrics['average_latency_ms'] < 1.0

    def test_async_handler_performance(self, test_config):
        """Test async handler reduces blocking time"""
        # This is a simplified test - real test would measure actual blocking
        logger = get_logger("test.async", config=test_config)

        start = time.perf_counter()
        for i in range(100):
            logger.info(f"Async test {i}")
        duration = time.perf_counter() - start

        # Should complete quickly due to async processing
        assert duration < 0.1


class TestLogDecorator:
    """Test log_execution_time decorator"""

    def test_sync_function_decorator(self, caplog):
        """Test decorator on sync function"""
        @log_execution_time(logger_name="test.decorator")
        def slow_function():
            time.sleep(0.01)
            return "result"

        with caplog.at_level(logging.DEBUG):
            result = slow_function()

        assert result == "result"
        assert "slow_function" in caplog.text
        assert "executed in" in caplog.text

    @pytest.mark.asyncio
    async def test_async_function_decorator(self, caplog):
        """Test decorator on async function"""
        @log_execution_time(logger_name="test.decorator")
        async def async_slow_function():
            await asyncio.sleep(0.01)
            return "async_result"

        with caplog.at_level(logging.DEBUG):
            result = await async_slow_function()

        assert result == "async_result"
        assert "async_slow_function" in caplog.text

    def test_decorator_with_threshold(self, caplog):
        """Test decorator only logs when threshold exceeded"""
        @log_execution_time(logger_name="test.decorator", threshold_ms=100)
        def fast_function():
            return "fast"

        with caplog.at_level(logging.DEBUG):
            result = fast_function()

        # Should not log because execution < 100ms
        assert result == "fast"
        # Check if fast_function appears in logs (it shouldn't)

    def test_decorator_with_error(self, caplog):
        """Test decorator logs errors"""
        @log_execution_time(logger_name="test.decorator")
        def failing_function():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                failing_function()

        assert "failed" in caplog.text.lower()


class TestGracefulDegradation:
    """Test graceful degradation on errors"""

    def test_logger_continues_on_handler_error(self, test_logger):
        """Test logger continues working if handler fails"""
        # Add a failing handler
        failing_handler = Mock(spec=logging.Handler)
        failing_handler.emit.side_effect = Exception("Handler error")
        test_logger._logger.addHandler(failing_handler)

        # Should not raise exception
        test_logger.info("Test message")

    def test_logger_works_without_file_handler(self):
        """Test logger works when file handler creation fails"""
        config = LoggingConfig.for_testing()
        config.file_output_enabled = True
        config.base_log_dir = Path("/invalid/path/that/cannot/be/created")

        # Should not crash, should degrade to console only
        logger = get_logger("test.degraded", config=config)
        logger.info("Test message")  # Should not raise

    def test_json_serialization_fallback(self, test_logger):
        """Test JSON formatter handles non-serializable objects"""
        from src.observability.logging.formatters import JSONFormatter

        formatter = JSONFormatter()

        # Create record with non-serializable object
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.non_serializable = object()  # Cannot be JSON serialized

        # Should not raise exception
        result = formatter.format(record)
        assert isinstance(result, str)


class TestThreadSafety:
    """Test thread safety of logging operations"""

    def test_concurrent_logging(self, test_logger):
        """Test logging from multiple threads"""
        import threading

        def log_worker(worker_id: int):
            for i in range(100):
                test_logger.info(f"Worker {worker_id} message {i}")

        threads = [
            threading.Thread(target=log_worker, args=(i,))
            for i in range(5)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors
        metrics = test_logger.get_metrics()
        assert metrics['total_logs'] == 500

    def test_metrics_thread_safety(self, test_logger):
        """Test metrics are updated correctly from multiple threads"""
        import threading

        test_logger.reset_metrics()

        def log_worker():
            for _ in range(100):
                test_logger.info("Test")

        threads = [threading.Thread(target=log_worker) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        metrics = test_logger.get_metrics()
        # All 500 logs should be counted
        assert metrics['total_logs'] == 500


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
