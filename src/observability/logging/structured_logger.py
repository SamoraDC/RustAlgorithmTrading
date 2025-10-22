"""
Structured Logger - Core logging infrastructure with async capabilities

Provides hierarchical logger with:
- Async non-blocking logging
- Correlation ID tracking
- Performance metrics
- Thread-safe operations
- Graceful degradation
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar

from .formatters import JSONFormatter, StructuredFormatter
from .handlers import AsyncQueueHandler, RotatingFileHandlerAsync
from ..config.logging_config import LoggingConfig

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

# Global logger registry
_logger_registry: Dict[str, 'StructuredLogger'] = {}
_registry_lock = threading.Lock()

# Performance metrics
class LoggerMetrics:
    """Thread-safe performance metrics for logging operations"""

    def __init__(self):
        self._lock = threading.Lock()
        self._total_logs = 0
        self._total_latency = 0.0
        self._max_latency = 0.0
        self._min_latency = float('inf')
        self._error_count = 0

    def record_log(self, latency: float, error: bool = False):
        """Record a log operation with its latency"""
        with self._lock:
            self._total_logs += 1
            self._total_latency += latency
            self._max_latency = max(self._max_latency, latency)
            self._min_latency = min(self._min_latency, latency)
            if error:
                self._error_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        with self._lock:
            avg_latency = (self._total_latency / self._total_logs
                          if self._total_logs > 0 else 0.0)
            return {
                'total_logs': self._total_logs,
                'average_latency_ms': avg_latency * 1000,
                'max_latency_ms': self._max_latency * 1000,
                'min_latency_ms': (self._min_latency * 1000
                                  if self._min_latency != float('inf') else 0.0),
                'error_count': self._error_count,
                'error_rate': (self._error_count / self._total_logs
                              if self._total_logs > 0 else 0.0),
            }

    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._total_logs = 0
            self._total_latency = 0.0
            self._max_latency = 0.0
            self._min_latency = float('inf')
            self._error_count = 0


class StructuredLogger:
    """
    Hierarchical structured logger with async capabilities

    Features:
    - Async non-blocking logging via queue-based handler
    - Correlation ID context tracking
    - Structured JSON formatting
    - Performance metrics (< 1ms overhead)
    - Thread-safe operations
    - Graceful degradation on errors
    """

    def __init__(
        self,
        name: str,
        config: Optional[LoggingConfig] = None,
        parent: Optional['StructuredLogger'] = None
    ):
        """
        Initialize structured logger

        Args:
            name: Logger name (hierarchical, e.g., 'trading.market_data')
            config: Logging configuration (uses default if None)
            parent: Parent logger for hierarchical setup
        """
        self.name = name
        self.config = config or LoggingConfig.get_default()
        self.parent = parent
        self._metrics = LoggerMetrics()

        # Create Python logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self.config.get_level(name))
        self._logger.propagate = False  # Don't propagate to root

        # Set up handlers if not already configured
        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Set up async and file handlers with formatters"""
        # Console handler with structured format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.config.console_level)
        console_handler.setFormatter(StructuredFormatter())
        self._logger.addHandler(console_handler)

        # Async file handler with JSON format
        if self.config.file_output_enabled:
            try:
                file_handler = RotatingFileHandlerAsync(
                    filename=self.config.get_log_file_path(self.name),
                    max_bytes=self.config.max_file_size,
                    backup_count=self.config.backup_count,
                )
                file_handler.setLevel(self.config.file_level)
                file_handler.setFormatter(JSONFormatter())

                # Wrap in async queue handler for non-blocking
                async_handler = AsyncQueueHandler(file_handler)
                self._logger.addHandler(async_handler)
            except Exception as e:
                # Graceful degradation: log to console only
                self._logger.warning(
                    f"Failed to set up file handler: {e}. Logging to console only."
                )

    def _enrich_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enrich log context with correlation ID and other metadata"""
        context = extra or {}

        # Add correlation ID if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            context['correlation_id'] = correlation_id

        # Add logger name
        context['logger_name'] = self.name

        # Add timestamp
        context['timestamp'] = time.time()

        return context

    def _log_with_metrics(
        self,
        level: int,
        msg: str,
        *args,
        exc_info=None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log with performance metrics tracking"""
        start_time = time.perf_counter()
        error = False

        try:
            enriched_context = self._enrich_context(extra)
            self._logger.log(
                level,
                msg,
                *args,
                exc_info=exc_info,
                extra=enriched_context,
                **kwargs
            )
        except Exception as e:
            error = True
            # Graceful degradation: try basic logging
            try:
                self._logger.log(level, f"[DEGRADED] {msg}: {e}")
            except:
                pass  # Silent failure in extreme cases
        finally:
            latency = time.perf_counter() - start_time
            self._metrics.record_log(latency, error)

    # Public logging methods

    def debug(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message"""
        self._log_with_metrics(logging.DEBUG, msg, *args, extra=extra, **kwargs)

    def info(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message"""
        self._log_with_metrics(logging.INFO, msg, *args, extra=extra, **kwargs)

    def warning(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message"""
        self._log_with_metrics(logging.WARNING, msg, *args, extra=extra, **kwargs)

    def error(
        self,
        msg: str,
        *args,
        exc_info=None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log error message with optional exception info"""
        self._log_with_metrics(
            logging.ERROR, msg, *args, exc_info=exc_info, extra=extra, **kwargs
        )

    def critical(
        self,
        msg: str,
        *args,
        exc_info=None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log critical message with optional exception info"""
        self._log_with_metrics(
            logging.CRITICAL, msg, *args, exc_info=exc_info, extra=extra, **kwargs
        )

    def exception(self, msg: str, *args, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log exception with traceback"""
        self._log_with_metrics(
            logging.ERROR, msg, *args, exc_info=True, extra=extra, **kwargs
        )

    # Performance metrics

    def get_metrics(self) -> Dict[str, Any]:
        """Get logger performance metrics"""
        return {
            'logger_name': self.name,
            **self._metrics.get_metrics()
        }

    def reset_metrics(self):
        """Reset performance metrics"""
        self._metrics.reset()

    # Utility methods

    def set_level(self, level: Union[int, str]):
        """Set logging level"""
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        self._logger.setLevel(level)

    def is_enabled_for(self, level: Union[int, str]) -> bool:
        """Check if logger is enabled for given level"""
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        return self._logger.isEnabledFor(level)

    def get_child(self, suffix: str) -> 'StructuredLogger':
        """Create child logger with hierarchical name"""
        child_name = f"{self.name}.{suffix}"
        return get_logger(child_name, config=self.config, parent=self)


def get_logger(
    name: str,
    config: Optional[LoggingConfig] = None,
    parent: Optional[StructuredLogger] = None
) -> StructuredLogger:
    """
    Get or create a structured logger

    Args:
        name: Logger name (hierarchical)
        config: Optional logging configuration
        parent: Optional parent logger

    Returns:
        StructuredLogger instance
    """
    with _registry_lock:
        if name not in _logger_registry:
            _logger_registry[name] = StructuredLogger(name, config, parent)
        return _logger_registry[name]


def get_all_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all registered loggers"""
    with _registry_lock:
        return {
            name: logger.get_metrics()
            for name, logger in _logger_registry.items()
        }


def reset_all_metrics():
    """Reset metrics for all registered loggers"""
    with _registry_lock:
        for logger in _logger_registry.values():
            logger.reset_metrics()
