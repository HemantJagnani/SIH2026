"""
Retry policy for the web collection framework.

Spec §30:
- Retry: timeout, network error, 502, 503, 504 with exponential backoff + jitter.
- Do NOT retry: 401, 403, CAPTCHA, parser failure, validation failure.
"""

import asyncio
import logging
import random
from typing import Callable, Any, TypeVar, Awaitable

logger = logging.getLogger(__name__)

T = TypeVar('T')

class NonRetryableError(Exception):
    """Raised when an error occurs that should not be retried."""
    pass


class TransientHttpError(Exception):
    """Raised for 502, 503, 504 errors so they can be retried."""
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"Transient HTTP error: {status}")


class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay_ms: int = 1000):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms

    def is_retryable(self, exc: Exception, http_status: int | None = None) -> bool:
        """
        Determine if an exception or HTTP status warrants a retry.
        Spec §30: Only transient failures are retryable.
        """
        if isinstance(exc, NonRetryableError):
            return False

        if isinstance(exc, asyncio.TimeoutError):
            return True

        if http_status is not None:
            # 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout
            if http_status in (502, 503, 504):
                return True
            # 401 Unauthorized, 403 Forbidden, 429 Too Many Requests (if not handled by rate limiter)
            if http_status in (401, 403):
                return False

        # In a real system, we'd also check for specific network errors (e.g., aiohttp.ClientError)
        # We default to False for safety, to avoid infinitely retrying logic errors.
        return False

    async def execute(self, func: Callable[[], Awaitable[T]], check_status: Callable[[T], int | None] = lambda _: None) -> T:
        """
        Execute an async function with exponential backoff and jitter.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                result = await func()
                
                # We might need to inspect the result for HTTP status if the client doesn't raise exceptions for 5xx
                http_status = check_status(result)
                if http_status and http_status in (502, 503, 504):
                    # Treat these status codes as exceptions to trigger retry
                    raise TransientHttpError(http_status)
                    
                if http_status and http_status in (401, 403):
                    raise NonRetryableError(f"Access restricted HTTP error: {http_status}")

                return result

            except Exception as e:
                # If we've hit max retries or the error isn't retryable, raise it
                is_retryable = self.is_retryable(e, getattr(e, 'status', None))
                
                if attempt >= self.max_retries or not is_retryable:
                    logger.error(f"Failed after {attempt} attempts. Error: {e}, Retryable: {is_retryable}")
                    raise

                # Calculate delay with exponential backoff and jitter
                delay_ms = self.base_delay_ms * (2 ** (attempt - 1))
                # Add up to 20% jitter
                jitter = random.uniform(0, 0.2 * delay_ms)
                sleep_seconds = (delay_ms + jitter) / 1000.0

                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {sleep_seconds:.2f}s...")
                await asyncio.sleep(sleep_seconds)
