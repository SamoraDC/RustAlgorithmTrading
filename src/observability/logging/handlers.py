"""
Async Log Handlers - Non-blocking handlers with queue-based processing

Provides:
- AsyncQueueHandler: Queue-based async handler wrapper
- RotatingFileHandlerAsync: Async-aware rotating file handler
"""

import logging
import logging.handlers
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional


class AsyncQueueHandler(logging.Handler):
    """
    Async queue-based handler for non-blocking logging

    Buffers log records in a queue and processes them in a background thread,
    ensuring < 1ms overhead for the logging call itself.
    """

    def __init__(
        self,
        target_handler: logging.Handler,
        queue_size: int = 10000,
        batch_size: int = 100,
        flush_interval: float = 0.1,
    ):
        """
        Initialize async queue handler

        Args:
            target_handler: Handler to process records asynchronously
            queue_size: Maximum queue size (blocks when full)
            batch_size: Number of records to process per batch
            flush_interval: Time between batch processing (seconds)
        """
        super().__init__()
        self.target_handler = target_handler
        self.queue = queue.Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # Processing thread
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="AsyncLogWorker"
        )
        self._worker_thread.start()

        # Statistics
        self._queued_count = 0
        self._processed_count = 0
        self._dropped_count = 0
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        """
        Emit log record (async, non-blocking)

        Adds record to queue for background processing. If queue is full,
        drops the record and increments dropped count for graceful degradation.
        """
        try:
            # Non-blocking put with immediate return
            self.queue.put_nowait(record)
            with self._lock:
                self._queued_count += 1
        except queue.Full:
            # Graceful degradation: drop record and track
            with self._lock:
                self._dropped_count += 1

    def _process_queue(self):
        """Background worker thread to process queued records"""
        batch = []
        last_flush = time.time()

        while not self._stop_event.is_set():
            try:
                # Get record with timeout
                try:
                    record = self.queue.get(timeout=self.flush_interval)
                    batch.append(record)
                except queue.Empty:
                    pass

                # Process batch if full or interval elapsed
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_flush >= self.flush_interval)
                )

                if should_flush:
                    self._process_batch(batch)
                    batch.clear()
                    last_flush = current_time

            except Exception as e:
                # Continue processing on error
                self.handleError(record if 'record' in locals() else None)

        # Process remaining records on shutdown
        if batch:
            self._process_batch(batch)

    def _process_batch(self, batch: list):
        """Process a batch of records through target handler"""
        for record in batch:
            try:
                self.target_handler.emit(record)
                with self._lock:
                    self._processed_count += 1
            except Exception:
                self.handleError(record)

    def flush(self):
        """Flush all pending records"""
        # Wait for queue to empty
        timeout = 5.0
        start = time.time()
        while not self.queue.empty() and time.time() - start < timeout:
            time.sleep(0.01)

        self.target_handler.flush()

    def close(self):
        """Close handler and wait for worker thread"""
        self._stop_event.set()
        self._worker_thread.join(timeout=5.0)
        self.target_handler.close()
        super().close()

    def get_stats(self) -> dict:
        """Get handler statistics"""
        with self._lock:
            return {
                'queued_count': self._queued_count,
                'processed_count': self._processed_count,
                'dropped_count': self._dropped_count,
                'queue_size': self.queue.qsize(),
                'drop_rate': (self._dropped_count / self._queued_count
                             if self._queued_count > 0 else 0.0),
            }


class RotatingFileHandlerAsync(logging.handlers.RotatingFileHandler):
    """
    Async-aware rotating file handler with directory creation

    Extends standard RotatingFileHandler with:
    - Automatic directory creation
    - Thread-safe rotation
    - Graceful error handling
    """

    def __init__(
        self,
        filename: str,
        max_bytes: int = 100 * 1024 * 1024,  # 100 MB
        backup_count: int = 10,
        encoding: Optional[str] = 'utf-8',
        delay: bool = False,
    ):
        """
        Initialize rotating file handler

        Args:
            filename: Log file path
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep
            encoding: File encoding
            delay: Delay file opening until first record
        """
        # Ensure directory exists
        log_dir = Path(filename).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize parent
        super().__init__(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
            delay=delay,
        )

        # Thread-safe rotation
        self._rotation_lock = threading.Lock()

    def doRollover(self):
        """Perform thread-safe log rotation"""
        with self._rotation_lock:
            try:
                super().doRollover()
            except Exception as e:
                # Graceful degradation: log error but continue
                self.handleError(None)

    def emit(self, record: logging.LogRecord):
        """
        Emit record with graceful error handling

        Handles disk full and permission errors gracefully.
        """
        try:
            super().emit(record)
        except OSError as e:
            # Disk full or permission error - graceful degradation
            if e.errno in (28, 13):  # ENOSPC or EACCES
                # Skip this record, don't crash
                pass
            else:
                raise
        except Exception:
            self.handleError(record)


class SyslogHandlerAsync(logging.handlers.SysLogHandler):
    """
    Async-aware syslog handler for remote logging

    Sends logs to syslog server with error handling and reconnection.
    """

    def __init__(
        self,
        address: tuple = ('localhost', 514),
        facility: int = logging.handlers.SysLogHandler.LOG_USER,
        socktype: int = None,
    ):
        """
        Initialize syslog handler

        Args:
            address: (host, port) tuple for syslog server
            facility: Syslog facility
            socktype: Socket type (SOCK_DGRAM or SOCK_STREAM)
        """
        super().__init__(address=address, facility=facility, socktype=socktype)
        self._error_count = 0
        self._max_errors = 10

    def emit(self, record: logging.LogRecord):
        """Emit with error tracking and circuit breaker"""
        try:
            super().emit(record)
            self._error_count = 0  # Reset on success
        except Exception:
            self._error_count += 1
            if self._error_count >= self._max_errors:
                # Circuit breaker: stop trying after too many errors
                self.close()
            else:
                self.handleError(record)


class NullHandler(logging.Handler):
    """
    Null handler that discards all records

    Useful for disabling logging in certain scenarios.
    """

    def emit(self, record: logging.LogRecord):
        """Discard record"""
        pass

    def handle(self, record: logging.LogRecord) -> bool:
        """Discard record"""
        return True
