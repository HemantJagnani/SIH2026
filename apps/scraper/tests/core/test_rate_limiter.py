import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.rate_limiter import RateLimiter, RateLimitConfig


def test_rate_limiter_configures_successfully():
    limiter = RateLimiter()
    config = RateLimitConfig(max_concurrency=5, requests_per_minute=30, delay_between_requests_ms=1000)
    
    limiter.configure("indigo", config)
    assert "indigo" in limiter._configs
    assert limiter._configs["indigo"].max_concurrency == 5


def test_rate_limiter_blocks_source():
    limiter = RateLimiter()
    
    assert not limiter.is_blocked("indigo")
    limiter.block_source("indigo", "CAPTCHA detected")
    assert limiter.is_blocked("indigo")


def test_rate_limiter_raises_on_blocked_source():
    limiter = RateLimiter()
    limiter.block_source("indigo", "403 Forbidden")
    
    with pytest.raises(PermissionError) as exc_info:
        limiter.check_request("indigo")
        
    assert "blocked" in str(exc_info.value)
    assert "403 Forbidden" in str(exc_info.value)


def test_rate_limiter_allows_unblocked_source():
    limiter = RateLimiter()
    # Should not raise
    limiter.check_request("indigo")
