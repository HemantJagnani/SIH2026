"""
Tests for Phase 9: Source Health Tracker.

Covers:
- Successful run tracking
- Partially failed run
- CAPTCHA / 403 tracking (distinct conditions)
- Parser error tracking
- Observation yield calculation
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from adapters.models import CollectionResult, CollectionStatus
from monitoring.source_health import compute_source_health
from monitoring.models import SourceHealthSnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    status: CollectionStatus,
    obs_count: int = 0,
    response_time_ms: int | None = None,
    http_status: int | None = None,
) -> CollectionResult:
    """Build a minimal CollectionResult for testing."""
    from models.observation import FareObservation, AvailabilityStatus
    from models.enums import TripType, CabinClass
    from models.version import SCHEMA_VERSION

    observations = []
    now = datetime.now(timezone.utc)
    run_id = uuid.uuid4()

    for _ in range(obs_count):
        obs = FareObservation(
            collection_run_id=run_id,
            source="test_source",
            collected_at=now,
            travel_date=date(2026, 10, 1),
            lead_days=10,
            origin="DEL",
            destination="BOM",
            airline="IndiGo",
            trip_type=TripType.ONE_WAY,
            cabin=CabinClass.ECONOMY,
            passenger_count=1,
            availability=AvailabilityStatus.AVAILABLE,
            total_fare=Decimal("4500.00"),
            currency="INR",
            adapter_version="1.0.0",
            normalizer_version="1.0.0",
            schema_version=SCHEMA_VERSION,
        )
        observations.append(obs)

    return CollectionResult(
        status=status,
        observations=observations,
        request_id=uuid.uuid4(),
        collection_timestamp=now,
        adapter_version="1.0.0",
        parser_version="1.0.0",
        response_time_ms=response_time_ms,
        http_status=http_status,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_source_health_all_success():
    """All successful jobs should produce success_rate=1.0."""
    results = [
        _make_result(CollectionStatus.SUCCESS, obs_count=10),
        _make_result(CollectionStatus.SUCCESS, obs_count=8),
        _make_result(CollectionStatus.SUCCESS, obs_count=12),
    ]
    snapshot = compute_source_health("cleartrip", results)

    assert snapshot.total_jobs == 3
    assert snapshot.successful_jobs == 3
    assert snapshot.failed_jobs == 0
    assert snapshot.success_rate == 1.0
    assert snapshot.total_observations == 30
    assert snapshot.observation_yield_per_success == 10.0


def test_source_health_partial_failure():
    """Mixed success / failure should compute correct rates."""
    results = [
        _make_result(CollectionStatus.SUCCESS, obs_count=5),
        _make_result(CollectionStatus.TIMEOUT),
        _make_result(CollectionStatus.SOURCE_ERROR),
        _make_result(CollectionStatus.SUCCESS, obs_count=7),
    ]
    snapshot = compute_source_health("indigo", results)

    assert snapshot.total_jobs == 4
    assert snapshot.successful_jobs == 2
    assert snapshot.failed_jobs == 2
    assert snapshot.success_rate == 0.5
    assert snapshot.timeout_count == 1
    assert snapshot.source_error_count == 1
    assert snapshot.total_observations == 12
    assert snapshot.observation_yield_per_success == 6.0


def test_source_health_captcha_tracked_distinctly():
    """CAPTCHA and ACCESS_RESTRICTED are separate counters."""
    results = [
        _make_result(CollectionStatus.CAPTCHA_PRESENT),
        _make_result(CollectionStatus.CAPTCHA_PRESENT),
        _make_result(CollectionStatus.ACCESS_RESTRICTED),
        _make_result(CollectionStatus.SUCCESS, obs_count=10),
    ]
    snapshot = compute_source_health("cleartrip", results)

    assert snapshot.captcha_count == 2
    assert snapshot.access_restricted_count == 1
    # CAPTCHA and 403/access-restricted should never be merged
    assert snapshot.captcha_count != snapshot.access_restricted_count
    assert snapshot.captcha_rate == 0.5
    assert snapshot.access_restricted_rate == 0.25


def test_source_health_parser_error_tracked():
    """Parser errors must be tracked distinctly from other errors."""
    results = [
        _make_result(CollectionStatus.PARSER_ERROR),
        _make_result(CollectionStatus.PARSER_ERROR),
        _make_result(CollectionStatus.SUCCESS, obs_count=5),
    ]
    snapshot = compute_source_health("makemytrip", results)

    assert snapshot.parser_error_count == 2
    assert round(snapshot.parser_error_rate, 4) == round(2 / 3, 4)


def test_source_health_response_time_computed():
    """Average and median response times should be computed correctly."""
    results = [
        _make_result(CollectionStatus.SUCCESS, obs_count=5, response_time_ms=100),
        _make_result(CollectionStatus.SUCCESS, obs_count=5, response_time_ms=200),
        _make_result(CollectionStatus.SUCCESS, obs_count=5, response_time_ms=300),
    ]
    snapshot = compute_source_health("yatra", results)

    assert snapshot.avg_response_time_ms == 200.0
    assert snapshot.median_response_time_ms == 200.0


def test_source_health_empty_results():
    """Empty result list should return default zero-valued snapshot."""
    snapshot = compute_source_health("cleartrip", [])

    assert snapshot.total_jobs == 0
    assert snapshot.success_rate == 0.0
    assert snapshot.total_observations == 0


def test_source_health_no_results_not_merged_with_captcha():
    """NO_RESULTS and CAPTCHA_PRESENT must never be collapsed."""
    results = [
        _make_result(CollectionStatus.NO_RESULTS),
        _make_result(CollectionStatus.CAPTCHA_PRESENT),
    ]
    snapshot = compute_source_health("cleartrip", results)

    assert snapshot.captcha_count == 1
    # NO_RESULTS does not increment captcha or access_restricted counters
    assert snapshot.access_restricted_count == 0
    assert snapshot.failed_jobs == 2   # Both are non-SUCCESS
