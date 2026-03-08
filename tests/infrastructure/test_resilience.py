import pytest
import time
from infrastructure.resilience import retry, CircuitBreaker, CircuitBreakerOpen, with_circuit_breaker


# --- Retry Tests ---


@pytest.mark.asyncio
async def test_retry_succeeds_first_try():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01)
    async def succeeds():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await succeeds()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01)
    async def fails_twice():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("temporary error")
        return "recovered"

    result = await fails_twice()
    assert result == "recovered"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    @retry(max_attempts=2, base_delay=0.01)
    async def always_fails():
        raise ValueError("permanent error")

    with pytest.raises(ValueError, match="permanent error"):
        await always_fails()


@pytest.mark.asyncio
async def test_retry_only_retries_specified_exceptions():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))
    async def raises_type_error():
        nonlocal call_count
        call_count += 1
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        await raises_type_error()
    assert call_count == 1


# --- Circuit Breaker Tests ---


def test_circuit_breaker_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, name="test")
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, name="test")
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "CLOSED"
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False


def test_circuit_breaker_resets_on_success():
    cb = CircuitBreaker(failure_threshold=3, name="test")
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb._failure_count == 0


def test_circuit_breaker_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="test")
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "OPEN"
    time.sleep(0.15)
    assert cb.state == "HALF_OPEN"
    assert cb.allow_request() is True


@pytest.mark.asyncio
async def test_with_circuit_breaker_decorator():
    cb = CircuitBreaker(failure_threshold=2, name="test_dec")

    @with_circuit_breaker(cb)
    async def protected_call():
        return "success"

    result = await protected_call()
    assert result == "success"
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_with_circuit_breaker_opens_on_failure():
    cb = CircuitBreaker(failure_threshold=1, name="test_fail")

    @with_circuit_breaker(cb)
    async def always_fails():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await always_fails()

    assert cb.state == "OPEN"

    with pytest.raises(CircuitBreakerOpen):
        await always_fails()
