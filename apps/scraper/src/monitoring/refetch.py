"""
Controlled Refetch — Phase 9 §6.

When an observation is flagged as a suspicious outlier, a controlled
refetch may be performed to verify the original fare before escalating
to AI verification.

Safety rules:
- Uses the same source, route, date, and parameters as the original.
- Obeys the existing RateLimiter — never bypasses it.
- Never bypasses CAPTCHA, 403, bot challenges, or auth restrictions.
- max_refetch_attempts is configurable (default: 1).
- If the refetch itself is blocked, records the appropriate outcome.

Spec Phase 9 §6.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from adapters.base import FareSourceAdapter
from adapters.models import CollectionStatus, FareSearchRequest
from core.rate_limiter import RateLimiter, SourceBlockedError
from monitoring.models import RefetchOutcome, RefetchResult

logger = logging.getLogger(__name__)

# Default maximum refetch attempts (configurable)
DEFAULT_MAX_REFETCH_ATTEMPTS = 1


async def controlled_refetch(
    observation_id: uuid.UUID,
    original_fare: Decimal | None,
    request: FareSearchRequest,
    adapter: FareSourceAdapter,
    rate_limiter: RateLimiter,
    max_attempts: int = DEFAULT_MAX_REFETCH_ATTEMPTS,
) -> RefetchResult:
    """
    Perform a single controlled refetch of the original request.

    The refetch uses the same source/route/date/cabin and obeys all
    rate limiting and access restrictions. Results are compared to the
    original fare to determine if the anomaly is consistent.

    Args:
        observation_id: UUID of the suspicious observation.
        original_fare: The total_fare from the original observation.
        request: The exact FareSearchRequest used to collect the original.
        adapter: The source adapter to use for the refetch.
        rate_limiter: Active rate limiter — must be respected.
        max_attempts: Maximum allowed refetch attempts (default 1).

    Returns:
        RefetchResult describing the outcome.
    """
    if max_attempts < 1:
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.NOT_ATTEMPTED,
            error_message="max_attempts < 1; refetch disabled.",
        )

    logger.info(
        "[refetch] Attempting controlled refetch for observation %s "
        "(source=%s route=%s->%s date=%s)",
        observation_id,
        request.source,
        request.origin,
        request.destination,
        request.travel_date,
    )

    # --- Check rate limiter BEFORE making the request ---
    try:
        rate_limiter.check(request.source)
    except SourceBlockedError as exc:
        logger.warning(
            "[refetch] Source '%s' is blocked — refetch aborted: %s",
            request.source,
            exc,
        )
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.ACCESS_RESTRICTED,
            error_message=str(exc),
            max_attempts=max_attempts,
        )

    # --- Perform the refetch ---
    try:
        result = await adapter.collect(request)
    except Exception as exc:
        logger.error("[refetch] Unexpected error during refetch: %s", exc)
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.ERROR,
            error_message=str(exc),
            max_attempts=max_attempts,
        )

    # --- Map CollectionStatus → RefetchOutcome ---
    status = result.status

    if status == CollectionStatus.CAPTCHA_PRESENT:
        logger.warning(
            "[refetch] CAPTCHA encountered for source '%s' — access restriction "
            "recorded. NOT bypassing.", request.source
        )
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.CAPTCHA_BLOCKED,
            http_status=result.http_status,
            max_attempts=max_attempts,
        )

    if status in (CollectionStatus.ACCESS_RESTRICTED,):
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.ACCESS_RESTRICTED,
            http_status=result.http_status,
            max_attempts=max_attempts,
        )

    if status == CollectionStatus.RATE_LIMITED:
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.RATE_LIMITED,
            http_status=result.http_status,
            max_attempts=max_attempts,
        )

    if status in (CollectionStatus.NO_RESULTS, CollectionStatus.NOT_FOUND):
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.NO_RESULTS,
            http_status=result.http_status,
            max_attempts=max_attempts,
        )

    if status != CollectionStatus.SUCCESS or not result.observations:
        return RefetchResult(
            observation_id=observation_id,
            original_total_fare=original_fare,
            outcome=RefetchOutcome.ERROR,
            http_status=result.http_status,
            error_message=result.error_message or f"Unexpected status: {status}",
            max_attempts=max_attempts,
        )

    # --- Compare original vs refetched fare ---
    # Use the first observation as the primary result
    refetched_obs = result.observations[0]
    refetched_fare = refetched_obs.total_fare

    # "Consistent" = fares match within a small rounding tolerance
    TOLERANCE = Decimal("1.00")
    if (
        original_fare is not None
        and refetched_fare is not None
        and abs(refetched_fare - original_fare) <= TOLERANCE
    ):
        outcome = RefetchOutcome.CONSISTENT
        logger.info(
            "[refetch] Refetch CONSISTENT for %s: original=%s refetched=%s",
            observation_id,
            original_fare,
            refetched_fare,
        )
    else:
        outcome = RefetchOutcome.CHANGED
        logger.info(
            "[refetch] Refetch CHANGED for %s: original=%s refetched=%s",
            observation_id,
            original_fare,
            refetched_fare,
        )

    return RefetchResult(
        observation_id=observation_id,
        original_total_fare=original_fare,
        refetched_total_fare=refetched_fare,
        outcome=outcome,
        http_status=result.http_status,
        max_attempts=max_attempts,
    )
