"""Resilience patterns for OracleForge infrastructure adapters.

Provides retry with exponential backoff and circuit breaker decorators
for wrapping external service calls (Oracle, GCP, AlloyDB).
"""

import logging
import time
import functools
from typing import Callable, Any, Type, Tuple
from domain.exceptions import InfrastructureError, ConnectionError as OFConnectionError

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay cap in seconds.
        exponential_base: Multiplier for exponential backoff.
        retryable_exceptions: Tuple of exception types that trigger a retry.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            raise last_exception  # Should not reach here

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            raise last_exception

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern implementation.

    States:
    - CLOSED: Normal operation, requests pass through.
    - OPEN: Requests are blocked, fail-fast with CircuitBreakerOpen.
    - HALF_OPEN: One test request is allowed to check recovery.

    Args:
        failure_threshold: Number of failures before opening circuit.
        recovery_timeout: Seconds to wait before trying half-open.
        name: Identifier for logging.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, name: str = ""):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "CLOSED"

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "HALF_OPEN"
        return self._state

    def record_success(self):
        """Record a successful call, resetting the circuit."""
        self._failure_count = 0
        self._state = "CLOSED"

    def record_failure(self):
        """Record a failed call, potentially opening the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
            logger.warning(
                f"Circuit breaker '{self.name}' OPENED after "
                f"{self._failure_count} failures"
            )

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        state = self.state
        if state == "CLOSED":
            return True
        if state == "HALF_OPEN":
            return True
        return False


class CircuitBreakerOpen(InfrastructureError):
    """Raised when a circuit breaker is open and blocking requests."""

    def __init__(self, breaker_name: str):
        super().__init__(
            f"Circuit breaker '{breaker_name}' is OPEN — service unavailable",
            details=f"Breaker: {breaker_name}",
            retryable=True,
        )


def with_circuit_breaker(breaker: CircuitBreaker):
    """Decorator that wraps a function with circuit breaker protection."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if not breaker.allow_request():
                raise CircuitBreakerOpen(breaker.name)
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if not breaker.allow_request():
                raise CircuitBreakerOpen(breaker.name)
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
