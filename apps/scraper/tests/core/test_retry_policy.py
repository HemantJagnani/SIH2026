import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.retry_policy import RetryPolicy, NonRetryableError


@pytest.mark.asyncio
async def test_retry_policy_success_on_first_try():
    policy = RetryPolicy()
    
    async def success_func():
        return "success"
        
    result = await policy.execute(success_func)
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_policy_retries_transient_error():
    policy = RetryPolicy(max_retries=3, base_delay_ms=10)
    attempts = 0
    
    async def transient_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise asyncio.TimeoutError("Timeout")
        return "success"
        
    result = await policy.execute(transient_func)
    assert result == "success"
    assert attempts == 2


@pytest.mark.asyncio
async def test_retry_policy_raises_after_max_retries():
    policy = RetryPolicy(max_retries=2, base_delay_ms=10)
    attempts = 0
    
    async def always_fails():
        nonlocal attempts
        attempts += 1
        raise asyncio.TimeoutError("Timeout")
        
    with pytest.raises(asyncio.TimeoutError):
        await policy.execute(always_fails)
        
    assert attempts == 2


@pytest.mark.asyncio
async def test_retry_policy_does_not_retry_non_retryable():
    policy = RetryPolicy(max_retries=3, base_delay_ms=10)
    attempts = 0
    
    async def fails_hard():
        nonlocal attempts
        attempts += 1
        raise NonRetryableError("CAPTCHA")
        
    with pytest.raises(NonRetryableError):
        await policy.execute(fails_hard)
        
    assert attempts == 1  # Should only try once


@pytest.mark.asyncio
async def test_retry_policy_http_status_mapping():
    policy = RetryPolicy(max_retries=3, base_delay_ms=10)
    attempts = 0
    
    # We simulate a function that returns a response object with an HTTP status
    class DummyResponse:
        def __init__(self, status):
            self.status_code = status
            
    async def returns_502():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            return DummyResponse(502)
        return DummyResponse(200)
        
    def check_status(response):
        return response.status_code
        
    result = await policy.execute(returns_502, check_status=check_status)
    assert result.status_code == 200
    assert attempts == 2

    # Now test 403 Forbidden
    attempts = 0
    async def returns_403():
        nonlocal attempts
        attempts += 1
        return DummyResponse(403)
        
    with pytest.raises(NonRetryableError) as exc:
        await policy.execute(returns_403, check_status=check_status)
    
    assert "403" in str(exc.value)
    assert attempts == 1  # Should not retry 403
