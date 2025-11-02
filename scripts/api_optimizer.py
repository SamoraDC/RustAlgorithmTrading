"""
API Optimization Utilities
Implements request batching, caching, circuit breaker patterns, and rate limiting.
"""

import time
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from functools import wraps
import threading


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket algorithm for rate limiting.
    Limits requests to stay within API rate limits (e.g., 200 requests/minute).
    """

    def __init__(self, max_requests: int, time_window: float = 60.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window: Time window in seconds (default: 60 seconds)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.min_interval = time_window / max_requests  # Minimum time between requests
        self.tokens = max_requests
        self.last_update = time.time()
        self.lock = threading.Lock()

        logger.info(
            f"RateLimiter initialized: {max_requests} requests per {time_window}s "
            f"(min interval: {self.min_interval:.3f}s)"
        )

    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * (self.max_requests / self.time_window)
        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_update = now

    def acquire(self, tokens: int = 1, block: bool = True) -> bool:
        """
        Acquire tokens for making requests.

        Args:
            tokens: Number of tokens to acquire
            block: If True, wait until tokens are available

        Returns:
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not block:
                return False

            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed * (self.time_window / self.max_requests)

            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")

        # Sleep outside the lock
        time.sleep(wait_time)

        with self.lock:
            self._refill_tokens()
            self.tokens -= tokens
            return True

    def get_optimal_delay(self) -> float:
        """
        Get the optimal delay between requests.

        Returns:
            Optimal delay in seconds
        """
        return self.min_interval

    def wait_if_needed(self):
        """Wait if needed to respect rate limits."""
        self.acquire(1, block=True)


class DataCache:
    """
    File-based cache that checks file age before re-downloading.
    Avoids unnecessary API calls for recent data.
    """

    def __init__(self, cache_dir: str, max_age_hours: int = 24):
        """
        Initialize data cache.

        Args:
            cache_dir: Directory for cached files
            max_age_hours: Maximum age of cached files in hours
        """
        self.cache_dir = Path(cache_dir)
        self.max_age = timedelta(hours=max_age_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"DataCache initialized: {cache_dir}, max_age={max_age_hours}h")

    def get_file_age(self, file_path: Path) -> Optional[timedelta]:
        """
        Get the age of a file.

        Args:
            file_path: Path to the file

        Returns:
            Age of the file as timedelta, or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age

    def is_fresh(self, file_path: Path) -> bool:
        """
        Check if a cached file is still fresh.

        Args:
            file_path: Path to the file

        Returns:
            True if file exists and is fresh, False otherwise
        """
        age = self.get_file_age(file_path)
        if age is None:
            return False

        is_fresh = age < self.max_age
        logger.debug(
            f"File {file_path.name}: age={age.total_seconds()/3600:.1f}h, "
            f"fresh={is_fresh}"
        )
        return is_fresh

    def get_cache_path(self, key: str) -> Path:
        """
        Get the cache file path for a given key.

        Args:
            key: Cache key (e.g., symbol name)

        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{key}.csv"

    def should_refresh(self, key: str) -> bool:
        """
        Check if data should be refreshed from API.

        Args:
            key: Cache key

        Returns:
            True if data should be refreshed, False if cache is fresh
        """
        cache_path = self.get_cache_path(key)
        return not self.is_fresh(cache_path)

    def invalidate(self, key: str):
        """
        Invalidate a cache entry.

        Args:
            key: Cache key to invalidate
        """
        cache_path = self.get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Invalidated cache for {key}")

    def clear_old_files(self):
        """Remove all files older than max_age."""
        removed = 0
        for file_path in self.cache_dir.glob("*.csv"):
            if not self.is_fresh(file_path):
                file_path.unlink()
                removed += 1

        if removed > 0:
            logger.info(f"Cleared {removed} old cache files")


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    Stops making requests after N consecutive failures.
    """

    # Circuit states
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, stop requests
    HALF_OPEN = "half_open"  # Testing if service recovered

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED
        self.lock = threading.Lock()

        logger.info(
            f"CircuitBreaker initialized: threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        with self.lock:
            if self.state == self.OPEN:
                if self._should_attempt_reset():
                    self.state = self.HALF_OPEN
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN. Too many failures "
                        f"({self.failure_count}/{self.failure_threshold}). "
                        f"Retry after {self.recovery_timeout}s"
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            if self.state == self.HALF_OPEN:
                self.state = self.CLOSED
                logger.info("Circuit breaker CLOSED (recovered)")

    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
                logger.error(
                    f"Circuit breaker OPEN after {self.failure_count} failures"
                )

    def reset(self):
        """Manually reset the circuit breaker."""
        with self.lock:
            self.failure_count = 0
            self.state = self.CLOSED
            logger.info("Circuit breaker manually reset")

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time
        }


class RequestBatcher:
    """
    Batches multiple requests to optimize API usage.
    Groups symbols to make efficient batch requests.
    """

    def __init__(self, batch_size: int = 10, max_wait: float = 1.0):
        """
        Initialize request batcher.

        Args:
            batch_size: Maximum number of items per batch
            max_wait: Maximum time to wait for a full batch (seconds)
        """
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.pending = []
        self.lock = threading.Lock()

        logger.info(
            f"RequestBatcher initialized: batch_size={batch_size}, "
            f"max_wait={max_wait}s"
        )

    def add(self, item: Any) -> List[Any]:
        """
        Add an item to the batch.

        Args:
            item: Item to add to batch

        Returns:
            Ready batch if batch_size reached, empty list otherwise
        """
        with self.lock:
            self.pending.append(item)

            if len(self.pending) >= self.batch_size:
                batch = self.pending[:self.batch_size]
                self.pending = self.pending[self.batch_size:]
                logger.debug(f"Batch ready: {len(batch)} items")
                return batch

            return []

    def flush(self) -> List[Any]:
        """
        Flush pending items as a batch.

        Returns:
            All pending items
        """
        with self.lock:
            if not self.pending:
                return []

            batch = self.pending
            self.pending = []
            logger.debug(f"Batch flushed: {len(batch)} items")
            return batch

    def get_pending_count(self) -> int:
        """Get number of pending items."""
        with self.lock:
            return len(self.pending)


class ProgressiveRetry:
    """
    Progressive retry with exponential backoff.
    Increases delay between retries to avoid overwhelming the API.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        """
        Initialize progressive retry.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

        logger.info(
            f"ProgressiveRetry initialized: max_retries={max_retries}, "
            f"base_delay={base_delay}s, backoff_factor={backoff_factor}"
        )

    def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with progressive retry.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed: {e}"
                    )

        raise last_exception

    def __call__(self, func: Callable) -> Callable:
        """Decorator for progressive retry."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)
        return wrapper


class APIOptimizer:
    """
    Combined API optimization utilities.
    Integrates rate limiting, caching, circuit breaking, and batching.
    """

    def __init__(
        self,
        rate_limit: int = 200,
        rate_window: float = 60.0,
        cache_dir: str = "data/historical",
        cache_max_age: int = 24,
        circuit_threshold: int = 5,
        circuit_timeout: float = 60.0,
        batch_size: int = 10,
        retry_attempts: int = 3
    ):
        """
        Initialize API optimizer with all components.

        Args:
            rate_limit: Maximum requests per rate_window
            rate_window: Rate limit window in seconds
            cache_dir: Directory for cached data
            cache_max_age: Maximum cache age in hours
            circuit_threshold: Failure threshold for circuit breaker
            circuit_timeout: Circuit breaker recovery timeout
            batch_size: Maximum batch size for requests
            retry_attempts: Maximum retry attempts
        """
        self.rate_limiter = RateLimiter(rate_limit, rate_window)
        self.cache = DataCache(cache_dir, cache_max_age)
        self.circuit_breaker = CircuitBreaker(circuit_threshold, circuit_timeout)
        self.batcher = RequestBatcher(batch_size)
        self.retry = ProgressiveRetry(max_retries=retry_attempts)

        logger.info("APIOptimizer initialized with all components")

    def optimized_request(
        self,
        func: Callable,
        symbol: str,
        *args,
        use_cache: bool = True,
        **kwargs
    ) -> Any:
        """
        Make an optimized API request with all protections.

        Args:
            func: API function to call
            symbol: Symbol/key for caching
            *args: Positional arguments for func
            use_cache: Whether to use caching
            **kwargs: Keyword arguments for func

        Returns:
            API response
        """
        # Check cache first
        if use_cache and not self.cache.should_refresh(symbol):
            logger.info(f"Using cached data for {symbol}")
            cache_path = self.cache.get_cache_path(symbol)
            # Return cache path for caller to load
            return cache_path

        # Wait for rate limit
        self.rate_limiter.wait_if_needed()

        # Make request with circuit breaker and retry
        def protected_call():
            return self.circuit_breaker.call(func, *args, **kwargs)

        return self.retry.execute(protected_call)

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all optimizer components.

        Returns:
            Status dictionary
        """
        return {
            "rate_limiter": {
                "optimal_delay": self.rate_limiter.get_optimal_delay(),
                "tokens_available": self.rate_limiter.tokens
            },
            "circuit_breaker": self.circuit_breaker.get_state(),
            "batcher": {
                "pending_count": self.batcher.get_pending_count()
            }
        }


# Example usage and optimal delays calculation
def calculate_optimal_delays(max_requests_per_minute: int = 200) -> Dict[str, float]:
    """
    Calculate optimal delays for API rate limits.

    Args:
        max_requests_per_minute: Maximum requests per minute

    Returns:
        Dictionary with delay recommendations
    """
    min_delay = 60.0 / max_requests_per_minute
    safe_delay = min_delay * 1.1  # 10% safety margin
    conservative_delay = min_delay * 1.2  # 20% safety margin

    return {
        "minimum_delay_seconds": min_delay,
        "safe_delay_seconds": safe_delay,
        "conservative_delay_seconds": conservative_delay,
        "requests_per_minute": max_requests_per_minute,
        "requests_per_hour": max_requests_per_minute * 60
    }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example: Calculate optimal delays for 200 req/min limit
    delays = calculate_optimal_delays(200)
    print("\nOptimal Delays for 200 requests/minute:")
    print(f"  Minimum delay: {delays['minimum_delay_seconds']:.3f}s")
    print(f"  Safe delay: {delays['safe_delay_seconds']:.3f}s")
    print(f"  Conservative delay: {delays['conservative_delay_seconds']:.3f}s")

    # Example: Initialize optimizer
    optimizer = APIOptimizer(
        rate_limit=200,
        rate_window=60.0,
        cache_dir="data/historical",
        cache_max_age=24
    )

    print("\nOptimizer Status:")
    status = optimizer.get_status()
    for component, details in status.items():
        print(f"  {component}: {details}")
