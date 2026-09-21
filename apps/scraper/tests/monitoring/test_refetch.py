"""
Tests for Phase 9: Controlled Refetch.

Covers:
- Successful refetch with consistent fare
- Successful refetch with changed fare
- Refetch blocked by CAPTCHA (must not bypass)
- Refetch blocked by 403 / ACCESS_RESTRICTED
- Refetch blocked by rate limiter
- Maximum retry enforcement
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from adapters.models import CollectionResult, CollectionStatus, FareSearchRequest, CollectionMode
from models.enums import TripType, CabinClass
from models.observation import FareObservation, AvailabilityStatus
from models.version import SCHEMA_VERSION
from core.rate_limiter import RateLimiter, SourceBlockedError
from monitoring.refetch import controlled_refetch, DEFAULT_MAX_REFETCH_ATTEMPTS
from monitoring.models import RefetchOutcome

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_OBS_ID = uuid.uuid4()
_RUN_ID = uuid.uuid4()
_ORIGINAL_FARE = Decimal("4740.00")

_REQUEST = FareSearchRequest(
    source="cleartrip",
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 9, 28),
    lead_days=7,
    trip_type=TripType.ONE_WAY,
    cabin=CabinClass.ECONOMY,
    adults=1,
    currency="INR",
    collection_mode=CollectionMode.API,
)


def _make_observation(total_fare: Decimal = _ORIGINAL_FARE) -> FareObservation:
    return FareObservation(
        collection_run_id=_RUN_ID,
        source="cleartrip",
        collected_at=_NOW,
        travel_date=date(2026, 9, 28),
        lead_days=7,
        origin="DEL",
        destination="BOM",
        airline="IndiGo",
        flight_number="6E-5001",
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        passenger_count=1,
        availability=AvailabilityStatus.AVAILABLE,
        total_fare=total_fare,
        currency="INR",
        adapter_version="1.0.0",
        normalizer_version="1.0.0",
        schema_version=SCHEMA_VERSION,
    )


def _make_collection_result(
    status: CollectionStatus,
    obs_fare: Decimal | None = None,
    http_status: int | None = 200,
) -> CollectionResult:
    observations = []
    if obs_fare is not None:
        observations.append(_make_observation(obs_fare))
    return CollectionResult(
        status=status,
        observations=observations,
        request_id=uuid.uuid4(),
        collection_timestamp=_NOW,
        adapter_version="1.0.0",
        parser_version="1.0.0",
        http_status=http_status,
    )


def _unblocked_rate_limiter() -> RateLimiter:
    """Rate limiter that never blocks."""
    limiter = RateLimiter()
    return limiter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refetch_consistent():
    """When refetch returns same fare, outcome is CONSISTENT."""
    adapter = MagicMock()
    adapter.collect = AsyncMock(
        return_value=_make_collection_result(CollectionStatus.SUCCESS, obs_fare=_ORIGINAL_FARE)
    )
    limiter = _unblocked_rate_limiter()

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
    )

    assert result.outcome == RefetchOutcome.CONSISTENT
    assert result.refetched_total_fare == _ORIGINAL_FARE


@pytest.mark.asyncio
async def test_refetch_changed():
    """When refetch returns different fare, outcome is CHANGED."""
    different_fare = Decimal("8500.00")  # Very different
    adapter = MagicMock()
    adapter.collect = AsyncMock(
        return_value=_make_collection_result(CollectionStatus.SUCCESS, obs_fare=different_fare)
    )
    limiter = _unblocked_rate_limiter()

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
    )

    assert result.outcome == RefetchOutcome.CHANGED
    assert result.refetched_total_fare == different_fare


@pytest.mark.asyncio
async def test_refetch_blocked_by_captcha():
    """CAPTCHA response must be recorded as CAPTCHA_BLOCKED — never bypassed."""
    adapter = MagicMock()
    adapter.collect = AsyncMock(
        return_value=_make_collection_result(CollectionStatus.CAPTCHA_PRESENT, http_status=403)
    )
    limiter = _unblocked_rate_limiter()

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
    )

    # CRITICAL: CAPTCHA must NEVER be bypassed
    assert result.outcome == RefetchOutcome.CAPTCHA_BLOCKED
    assert result.refetched_total_fare is None


@pytest.mark.asyncio
async def test_refetch_blocked_by_403():
    """ACCESS_RESTRICTED must be recorded as such — never bypassed."""
    adapter = MagicMock()
    adapter.collect = AsyncMock(
        return_value=_make_collection_result(CollectionStatus.ACCESS_RESTRICTED, http_status=403)
    )
    limiter = _unblocked_rate_limiter()

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
    )

    assert result.outcome == RefetchOutcome.ACCESS_RESTRICTED
    assert result.refetched_total_fare is None


@pytest.mark.asyncio
async def test_refetch_blocked_by_rate_limiter():
    """If rate limiter blocks the source, refetch must abort immediately."""
    adapter = MagicMock()
    adapter.collect = AsyncMock()   # Should not be called

    limiter = MagicMock()
    limiter.check = MagicMock(side_effect=SourceBlockedError("cleartrip", "BLOCKED"))

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
    )

    assert result.outcome == RefetchOutcome.ACCESS_RESTRICTED
    # Adapter should never have been called
    adapter.collect.assert_not_called()


@pytest.mark.asyncio
async def test_refetch_rate_limited():
    """RATE_LIMITED response from source is correctly mapped."""
    adapter = MagicMock()
    adapter.collect = AsyncMock(
        return_value=_make_collection_result(CollectionStatus.RATE_LIMITED, http_status=429)
    )
    limiter = _unblocked_rate_limiter()

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
    )

    assert result.outcome == RefetchOutcome.RATE_LIMITED


@pytest.mark.asyncio
async def test_refetch_not_attempted_when_max_zero():
    """max_attempts=0 must prevent any refetch."""
    adapter = MagicMock()
    adapter.collect = AsyncMock()   # Should not be called

    limiter = _unblocked_rate_limiter()

    result = await controlled_refetch(
        observation_id=_OBS_ID,
        original_fare=_ORIGINAL_FARE,
        request=_REQUEST,
        adapter=adapter,
        rate_limiter=limiter,
        max_attempts=0,
    )

    assert result.outcome == RefetchOutcome.NOT_ATTEMPTED
    adapter.collect.assert_not_called()
