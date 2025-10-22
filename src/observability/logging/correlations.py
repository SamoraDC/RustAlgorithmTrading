"""
Correlation ID Context Manager - Track requests across async operations

Provides correlation_id context manager for distributed tracing and
log aggregation across async operations and service boundaries.
"""

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator, Optional

# Context variable for correlation ID (thread-safe and async-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


@contextmanager
def correlation_id(cid: Optional[str] = None) -> Generator[str, None, None]:
    """
    Context manager for correlation ID tracking

    Sets a correlation ID for the current context (thread + async task).
    All logs within this context will include the correlation ID.

    Args:
        cid: Correlation ID to use (generates new UUID if None)

    Yields:
        The correlation ID being used

    Example:
        >>> with correlation_id() as cid:
        ...     logger.info("Processing request")  # Includes correlation_id
        ...     await process_data()  # Nested calls inherit correlation_id

        >>> with correlation_id("custom-id-123") as cid:
        ...     logger.info("Processing with custom ID")
    """
    # Generate new correlation ID if not provided
    if cid is None:
        cid = generate_correlation_id()

    # Set in context variable
    token = correlation_id_var.set(cid)

    try:
        yield cid
    finally:
        # Reset to previous value
        correlation_id_var.reset(token)


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context

    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def set_correlation_id(cid: str) -> None:
    """
    Set correlation ID in current context

    Args:
        cid: Correlation ID to set
    """
    correlation_id_var.set(cid)


def generate_correlation_id(prefix: str = "req") -> str:
    """
    Generate a new correlation ID

    Args:
        prefix: Prefix for the correlation ID

    Returns:
        New correlation ID in format: prefix-uuid

    Example:
        >>> generate_correlation_id("trade")
        'trade-550e8400-e29b-41d4-a716-446655440000'
    """
    return f"{prefix}-{uuid.uuid4()}"


class CorrelationContext:
    """
    Class-based correlation context for more control

    Useful for manual context management or when context manager
    syntax is not suitable.

    Example:
        >>> ctx = CorrelationContext()
        >>> ctx.enter()
        >>> logger.info("Processing")  # Has correlation ID
        >>> ctx.exit()
        >>> logger.info("Done")  # No correlation ID
    """

    def __init__(self, cid: Optional[str] = None):
        """
        Initialize correlation context

        Args:
            cid: Correlation ID (generates new if None)
        """
        self.cid = cid or generate_correlation_id()
        self._token = None

    def enter(self) -> str:
        """Enter correlation context"""
        self._token = correlation_id_var.set(self.cid)
        return self.cid

    def exit(self) -> None:
        """Exit correlation context"""
        if self._token is not None:
            correlation_id_var.reset(self._token)
            self._token = None

    def __enter__(self) -> str:
        """Support context manager protocol"""
        return self.enter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager protocol"""
        self.exit()
        return False


def extract_correlation_id_from_headers(headers: dict) -> Optional[str]:
    """
    Extract correlation ID from HTTP headers

    Looks for common correlation ID headers:
    - X-Correlation-ID
    - X-Request-ID
    - X-Trace-ID

    Args:
        headers: HTTP headers dictionary

    Returns:
        Correlation ID if found, None otherwise
    """
    header_names = [
        'X-Correlation-ID',
        'X-Request-ID',
        'X-Trace-ID',
        'x-correlation-id',
        'x-request-id',
        'x-trace-id',
    ]

    for header in header_names:
        if header in headers:
            return headers[header]

    return None


def inject_correlation_id_into_headers(
    headers: dict,
    cid: Optional[str] = None
) -> dict:
    """
    Inject correlation ID into HTTP headers

    Adds X-Correlation-ID header with current or provided correlation ID.

    Args:
        headers: HTTP headers dictionary to modify
        cid: Correlation ID to inject (uses current if None)

    Returns:
        Modified headers dictionary
    """
    if cid is None:
        cid = get_correlation_id()

    if cid is not None:
        headers['X-Correlation-ID'] = cid

    return headers
