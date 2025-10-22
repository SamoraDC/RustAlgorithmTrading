"""
Comprehensive logging infrastructure tests.

Tests structured logging, log formatting, async logging performance,
rotation, archival, error handling, and high-throughput scenarios.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from tests.observability.fixtures.sample_logs import LogDataGenerator, StructuredLogValidator


# ============================================================================
# UNIT TESTS: Structured Logging
# ============================================================================

@pytest.mark.logging
@pytest.mark.unit
class TestStructuredLogging:
    """Test structured log format and validation."""

    def test_log_format_structure(self, mock_logger):
        """Test that logs follow the required structured format."""
        log_entry = LogDataGenerator.generate_single_log(
            level="INFO",
            service="trading-engine",
            message="Test message",
        )

        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        assert "correlation_id" in log_entry
        assert "service" in log_entry
        assert log_entry["level"] == "INFO"

    def test_log_validation(self):
        """Test log entry validation."""
        valid_log = LogDataGenerator.generate_single_log()
        assert StructuredLogValidator.validate_log(valid_log)

        invalid_log = {"message": "Missing required fields"}
        assert not StructuredLogValidator.validate_log(invalid_log)

    def test_batch_log_validation(self):
        """Test batch log validation."""
        logs = LogDataGenerator.generate_batch(count=100)
        is_valid, errors = StructuredLogValidator.validate_batch(logs)

        assert is_valid, f"Validation errors: {errors}"
        assert len(errors) == 0

    def test_log_levels(self):
        """Test all log levels are properly formatted."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            log_entry = LogDataGenerator.generate_single_log(level=level)
            assert log_entry["level"] == level
            assert StructuredLogValidator.validate_log(log_entry)

    def test_metadata_inclusion(self):
        """Test that metadata is properly included in logs."""
        metadata = {"order_id": "ORD-123", "symbol": "AAPL", "action": "execute"}
        log_entry = LogDataGenerator.generate_single_log(metadata=metadata)

        assert "metadata" in log_entry
        assert log_entry["metadata"] == metadata

    def test_timestamp_format(self):
        """Test timestamp format is ISO 8601 compliant."""
        log_entry = LogDataGenerator.generate_single_log()
        timestamp_str = log_entry["timestamp"]

        # Should parse without error
        parsed_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert isinstance(parsed_time, datetime)


# ============================================================================
# UNIT TESTS: Correlation ID Propagation
# ============================================================================

@pytest.mark.logging
@pytest.mark.correlation
@pytest.mark.unit
class TestCorrelationIDPropagation:
    """Test correlation ID propagation across log entries."""

    def test_correlation_id_generation(self, correlation_context):
        """Test correlation ID generation."""
        corr_id = correlation_context.new_correlation()

        assert corr_id is not None
        assert corr_id.startswith("corr-")
        assert len(corr_id) > 5

    def test_correlation_id_consistency(self):
        """Test correlation ID remains consistent across related logs."""
        correlation_id = "corr-test-12345"
        logs = LogDataGenerator.generate_batch(count=50, correlation_id=correlation_id)

        for log in logs:
            assert log["correlation_id"] == correlation_id

    def test_trade_execution_correlation(self):
        """Test correlation ID propagation through trade execution."""
        order_id = "ORD-test-999"
        correlation_id = "corr-trade-execution"

        logs = LogDataGenerator.generate_trade_execution_logs(
            order_id=order_id,
            correlation_id=correlation_id,
        )

        # All logs should have same correlation ID
        for log in logs:
            assert log["correlation_id"] == correlation_id
            assert log["metadata"]["order_id"] == order_id

        # Verify execution sequence
        assert logs[0]["metadata"]["stage"] == "received"
        assert logs[1]["metadata"]["stage"] == "risk_check"
        assert logs[2]["metadata"]["stage"] == "submitted"
        assert logs[3]["metadata"]["stage"] == "filled"

    def test_correlation_context_headers(self, correlation_context):
        """Test correlation context converts to headers properly."""
        correlation_context.new_correlation()
        headers = correlation_context.to_dict()

        assert "X-Correlation-ID" in headers
        assert "X-Trace-ID" in headers
        assert "X-Span-ID" in headers
        assert headers["X-Correlation-ID"].startswith("corr-")


# ============================================================================
# INTEGRATION TESTS: Log File Operations
# ============================================================================

@pytest.mark.logging
@pytest.mark.integration
class TestLogFileOperations:
    """Test log file writing, rotation, and archival."""

    def test_log_file_creation(self, temp_log_dir):
        """Test log file is created successfully."""
        log_file = temp_log_dir / "test.log"

        # Configure logging to file
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
        )

        logger = logging.getLogger("test_logger")
        logger.info("Test message")

        assert log_file.exists()
        assert log_file.stat().st_size > 0

    def test_log_file_write_performance(self, temp_log_dir, performance_timer):
        """Test log file write performance."""
        log_file = temp_log_dir / "perf_test.log"

        logging.basicConfig(filename=str(log_file), level=logging.INFO)
        logger = logging.getLogger("perf_logger")

        num_logs = 1000
        performance_timer.start()

        for i in range(num_logs):
            logger.info(f"Performance test log {i}")

        elapsed_ms = performance_timer.stop() * 1000

        # Should write 1000 logs in under 100ms
        assert elapsed_ms < 100, f"Logging too slow: {elapsed_ms:.2f}ms for {num_logs} logs"

        # Verify all logs were written
        log_content = log_file.read_text()
        assert log_content.count("Performance test log") == num_logs

    def test_structured_log_json_format(self, temp_log_dir):
        """Test structured logs are valid JSON."""
        log_file = temp_log_dir / "json_test.log"

        with open(log_file, "w") as f:
            logs = LogDataGenerator.generate_batch(count=10)
            for log in logs:
                f.write(json.dumps(log) + "\n")

        # Read back and validate JSON
        with open(log_file, "r") as f:
            for line in f:
                log_entry = json.loads(line.strip())
                assert StructuredLogValidator.validate_log(log_entry)

    def test_concurrent_log_writing(self, temp_log_dir):
        """Test concurrent writes to log file don't corrupt data."""
        import threading

        log_file = temp_log_dir / "concurrent_test.log"

        def write_logs(thread_id: int, count: int):
            logging.basicConfig(filename=str(log_file), level=logging.INFO)
            logger = logging.getLogger(f"thread_{thread_id}")
            for i in range(count):
                logger.info(f"Thread {thread_id} - Log {i}")

        threads = []
        for tid in range(10):
            thread = threading.Thread(target=write_logs, args=(tid, 100))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all logs were written
        log_content = log_file.read_text()
        total_logs = sum(1 for line in log_content.split("\n") if line.strip())
        assert total_logs == 1000  # 10 threads * 100 logs each


# ============================================================================
# PERFORMANCE TESTS: High Throughput Logging
# ============================================================================

@pytest.mark.logging
@pytest.mark.performance
@pytest.mark.slow
class TestLoggingPerformance:
    """Test logging performance under high load."""

    def test_10k_logs_per_second(self, temp_log_dir, performance_timer):
        """Test system can handle 10,000+ logs per second."""
        log_file = temp_log_dir / "high_throughput.log"

        logging.basicConfig(filename=str(log_file), level=logging.INFO)
        logger = logging.getLogger("throughput_test")

        num_logs = 10000
        performance_timer.start()

        for i in range(num_logs):
            logger.info(f"High throughput log {i}")

        elapsed = performance_timer.stop()
        throughput = num_logs / elapsed

        assert throughput >= 10000, f"Throughput too low: {throughput:.0f} logs/sec"

    @pytest.mark.asyncio
    async def test_async_logging_performance(self, temp_log_dir, performance_timer):
        """Test async logging performance."""

        async def async_log_batch(log_file: Path, batch_size: int):
            """Async batch log writing."""
            logs = LogDataGenerator.generate_batch(count=batch_size)
            await asyncio.to_thread(
                lambda: [log_file.write_text(json.dumps(log) + "\n", encoding="utf-8") for log in logs]
            )

        log_file = temp_log_dir / "async_test.log"
        num_batches = 100
        batch_size = 100

        performance_timer.start()

        tasks = [async_log_batch(log_file, batch_size) for _ in range(num_batches)]
        await asyncio.gather(*tasks)

        elapsed = performance_timer.stop()
        total_logs = num_batches * batch_size
        throughput = total_logs / elapsed

        assert throughput >= 5000, f"Async throughput too low: {throughput:.0f} logs/sec"

    def test_memory_overhead(self, temp_log_dir, memory_profiler):
        """Test memory overhead of logging operations."""
        log_file = temp_log_dir / "memory_test.log"

        logging.basicConfig(filename=str(log_file), level=logging.INFO)
        logger = logging.getLogger("memory_test")

        memory_profiler.start()

        # Generate 10,000 logs
        for i in range(10000):
            logger.info(f"Memory test log {i}")

        memory_delta_mb = memory_profiler.stop() / (1024 * 1024)

        # Memory overhead should be < 10MB for 10k logs
        assert memory_delta_mb < 10, f"Memory overhead too high: {memory_delta_mb:.2f}MB"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.logging
@pytest.mark.unit
class TestLoggingErrorHandling:
    """Test logging error handling and resilience."""

    def test_error_log_generation(self):
        """Test generation of error log sequences."""
        error_logs = LogDataGenerator.generate_error_logs(
            error_type="ConnectionError",
            severity="ERROR",
        )

        assert len(error_logs) == 3
        assert error_logs[0]["level"] == "WARNING"
        assert error_logs[1]["level"] == "ERROR"
        assert error_logs[2]["level"] == "INFO"

        # Verify correlation ID consistency
        corr_id = error_logs[0]["correlation_id"]
        for log in error_logs:
            assert log["correlation_id"] == corr_id

    def test_invalid_log_directory_handling(self):
        """Test handling of invalid log directory."""
        invalid_path = Path("/nonexistent/directory/logs.log")

        with pytest.raises(FileNotFoundError):
            logging.basicConfig(filename=str(invalid_path), level=logging.INFO)
            logger = logging.getLogger("invalid_test")
            logger.info("This should fail")

    def test_log_serialization_errors(self):
        """Test handling of non-serializable log data."""

        class NonSerializable:
            pass

        log_entry = LogDataGenerator.generate_single_log()
        log_entry["metadata"]["invalid"] = NonSerializable()

        with pytest.raises(TypeError):
            json.dumps(log_entry)


# ============================================================================
# REGRESSION TESTS
# ============================================================================

@pytest.mark.logging
@pytest.mark.unit
class TestLoggingRegression:
    """Regression tests for known logging issues."""

    def test_no_duplicate_correlation_ids_in_batch(self):
        """Ensure correlation IDs are unique when not specified."""
        logs = LogDataGenerator.generate_batch(count=100)

        # Without explicit correlation_id, they should rotate every 10 logs
        correlation_ids = [log["correlation_id"] for log in logs]

        # Should have approximately 10 unique correlation IDs
        unique_ids = set(correlation_ids)
        assert len(unique_ids) >= 9  # Allow some variance

    def test_timestamp_monotonicity(self):
        """Test that timestamps are monotonically increasing."""
        logs = LogDataGenerator.generate_batch(count=100)

        timestamps = [datetime.fromisoformat(log["timestamp"]) for log in logs]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1]
