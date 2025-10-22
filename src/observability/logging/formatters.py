"""
Log Formatters - JSON and Structured formatters for different output formats

Provides:
- JSONFormatter: Machine-readable JSON logs
- StructuredFormatter: Human-readable structured logs
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for machine-readable structured logs

    Outputs logs as single-line JSON objects with consistent schema:
    {
        "timestamp": "2025-10-21T22:10:00.000Z",
        "level": "INFO",
        "logger": "trading.market_data",
        "message": "Price update received",
        "correlation_id": "req-123",
        "extra": {...}
    }
    """

    def __init__(self, include_exc_info: bool = True):
        """
        Initialize JSON formatter

        Args:
            include_exc_info: Include exception traceback in output
        """
        super().__init__()
        self.include_exc_info = include_exc_info

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string"""
        log_data = self._build_log_data(record)

        try:
            return json.dumps(log_data, default=str)
        except (TypeError, ValueError) as e:
            # Fallback to simple format on serialization error
            return json.dumps({
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': record.levelname,
                'logger': record.name,
                'message': str(record.getMessage()),
                'serialization_error': str(e)
            })

    def _build_log_data(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Build log data dictionary from record"""
        # Base log data
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        # Add custom fields from extra
        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            log_data['extra'] = extra_fields

        # Add exception info if present
        if record.exc_info and self.include_exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        return log_data

    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract custom fields from record"""
        # Standard fields to skip
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName',
            'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info', 'correlation_id', 'logger_name',
            'timestamp'
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in skip_fields:
                try:
                    # Attempt to serialize to ensure it's JSON-compatible
                    json.dumps(value, default=str)
                    extra[key] = value
                except:
                    extra[key] = str(value)

        return extra


class StructuredFormatter(logging.Formatter):
    """
    Human-readable structured formatter with colored output

    Output format:
    [2025-10-21 22:10:00.000] INFO [trading.market_data] [req-123] Price update received
      → extra_field: value
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }

    def __init__(self, use_colors: bool = True, include_extra: bool = True):
        """
        Initialize structured formatter

        Args:
            use_colors: Enable ANSI color codes
            include_extra: Include extra fields in output
        """
        super().__init__()
        self.use_colors = use_colors
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable structured text"""
        # Format timestamp
        timestamp = datetime.utcfromtimestamp(record.created).strftime(
            '%Y-%m-%d %H:%M:%S.%f'
        )[:-3]  # Truncate to milliseconds

        # Format level with optional color
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, '')
            reset = self.COLORS['RESET']
            level = f"{color}{level}{reset}"

        # Format logger name
        logger_name = f"[{record.name}]"

        # Format correlation ID if present
        correlation_id = ""
        if hasattr(record, 'correlation_id'):
            correlation_id = f"[{record.correlation_id}]"

        # Main log line
        main_line = (
            f"[{timestamp}] {level} {logger_name} {correlation_id} "
            f"{record.getMessage()}"
        )

        lines = [main_line]

        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = self._extract_extra_fields(record)
            for key, value in extra_fields.items():
                lines.append(f"  → {key}: {value}")

        # Add exception info if present
        if record.exc_info:
            exc_text = ''.join(traceback.format_exception(*record.exc_info))
            for line in exc_text.splitlines():
                lines.append(f"  {line}")

        return '\n'.join(lines)

    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract custom fields from record"""
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName',
            'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info', 'correlation_id', 'logger_name',
            'timestamp'
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in skip_fields:
                extra[key] = value

        return extra


class CompactJSONFormatter(JSONFormatter):
    """
    Compact JSON formatter with minimal fields for high-throughput scenarios

    Only includes: timestamp, level, logger, message, correlation_id
    """

    def _build_log_data(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Build minimal log data dictionary"""
        log_data = {
            'ts': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'lvl': record.levelname[0],  # Single letter: D, I, W, E, C
            'lgr': record.name.split('.')[-1],  # Last component only
            'msg': record.getMessage(),
        }

        if hasattr(record, 'correlation_id'):
            log_data['cid'] = record.correlation_id

        return log_data
