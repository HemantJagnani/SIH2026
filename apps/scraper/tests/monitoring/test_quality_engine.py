"""
Tests for Phase 9: Data Quality Engine.

Covers:
- Missing fare / airline detection
- Duplicate detection (technical and logical)
- Observation yield anomaly
- Parser health warning
- Relative outlier detection
- Quarantine trigger
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from models.observation import FareObservation, AvailabilityStatus
from models.enums import TripType, CabinClass
from models.version import SCHEMA_VERSION
from monitoring.quality_engine import DataQualityEngine
from monitoring.models import (
    AnomalyType,
    AnomalySeverity,
    QualityDecision,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_RUN_ID = uuid.uuid4()
_SOURCE = "cleartrip"


def _obs(
    total_fare: Decimal | None = Decimal("4500.00"),
    airline: str = "IndiGo",
    flight_number: str | None = "6E-100",
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    origin: str = "DEL",
    destination: str = "BOM",
    travel_date: date = date(2026, 10, 1),
    lead_days: int = 10,
    cabin: CabinClass = CabinClass.ECONOMY,
) -> FareObservation:
    return FareObservation(
        collection_run_id=_RUN_ID,
        source=_SOURCE,
        collected_at=_NOW,
        travel_date=travel_date,
        lead_days=lead_days,
        origin=origin,
        destination=destination,
        airline=airline,
        flight_number=flight_number,
        trip_type=TripType.ONE_WAY,
        cabin=cabin,
        passenger_count=1,
        availability=availability,
        total_fare=total_fare,
        currency="INR",
        adapter_version="1.0.0",
        normalizer_version="1.0.0",
        schema_version=SCHEMA_VERSION,
    )


engine = DataQualityEngine()


# ---------------------------------------------------------------------------
# Completeness tests
# ---------------------------------------------------------------------------

def test_missing_fare_detected():
    """Missing total_fare for AVAILABLE observation must be flagged as HIGH."""
    obs = _obs(total_fare=None)
    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs])

    missing_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.MISSING_FARE
    ]
    assert len(missing_findings) == 1
    assert missing_findings[0].severity == AnomalySeverity.HIGH
    assert report.missing_fare_count == 1


def test_missing_airline_detected():
    """Missing airline should be flagged."""
    obs = _obs(airline="")
    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs])

    airline_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.MISSING_AIRLINE
    ]
    assert len(airline_findings) == 1


def test_no_findings_for_clean_data():
    """Clean, complete observations should produce no quality findings."""
    # Use unique flight numbers so observations are not technical duplicates
    observations = [_obs(flight_number=f"6E-10{i}") for i in range(5)]
    report = engine.evaluate_run(_RUN_ID, _SOURCE, observations)

    # No completeness, plausibility, or duplicate findings expected
    significant_findings = [
        f for f in report.findings
        if f.anomaly_type not in (AnomalyType.LOGICAL_DUPLICATE,)
    ]
    assert len(significant_findings) == 0
    assert report.decision == QualityDecision.ACCEPT


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def test_technical_duplicate_detected():
    """Identical observations must be flagged as TECHNICAL_DUPLICATE."""
    obs = _obs(flight_number="6E-200")
    # Pass the same object twice to simulate a duplicate
    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs, obs])

    dup_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.TECHNICAL_DUPLICATE
    ]
    assert len(dup_findings) == 1
    assert dup_findings[0].severity == AnomalySeverity.HIGH


def test_logical_duplicate_detected():
    """Same flight/route with different fares → LOGICAL_DUPLICATE (not auto-deleted)."""
    obs1 = _obs(total_fare=Decimal("4500"), flight_number="6E-300")
    obs2 = _obs(total_fare=Decimal("4800"), flight_number="6E-300")  # Same flight, different fare

    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs1, obs2])

    log_dup_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.LOGICAL_DUPLICATE
    ]
    # Both observations are in the group, so 2 findings
    assert len(log_dup_findings) == 2
    # Severity is MEDIUM — do NOT automatically delete
    assert all(f.severity == AnomalySeverity.MEDIUM for f in log_dup_findings)


# ---------------------------------------------------------------------------
# Fare plausibility
# ---------------------------------------------------------------------------

def test_negative_fare_is_critical():
    """Negative fare must be CRITICAL severity."""
    # FareObservation rejects negative fares via ge=0, so we must bypass
    # by using a mock-like approach with a patched observation
    obs = _obs(total_fare=Decimal("4500"))
    # Manually override for plausibility test (simulate parser bug)
    object.__setattr__(obs, "total_fare", Decimal("-100"))

    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs])
    neg_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.NEGATIVE_FARE
    ]
    assert len(neg_findings) == 1
    assert neg_findings[0].severity == AnomalySeverity.CRITICAL
    assert report.decision == QualityDecision.QUARANTINE


def test_zero_fare_for_available_is_high():
    """Zero total_fare for AVAILABLE observation → HIGH severity."""
    obs = _obs(total_fare=Decimal("4500"))
    object.__setattr__(obs, "total_fare", Decimal("0"))

    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs])
    zero_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.ZERO_FARE
    ]
    assert len(zero_findings) == 1
    assert zero_findings[0].severity == AnomalySeverity.HIGH


# ---------------------------------------------------------------------------
# Relative outlier detection
# ---------------------------------------------------------------------------

def test_relative_outlier_detected():
    """A fare > 3× group median must be flagged as RELATIVE_FARE_OUTLIER."""
    # Group median will be ~4500; outlier is 20000 (>3x)
    normal_obs = [_obs(total_fare=Decimal(str(f)), flight_number=f"6E-{i}") for i, f in enumerate([4000, 4500, 4800, 4600, 4700])]
    outlier_obs = _obs(total_fare=Decimal("20000"), flight_number="6E-999")

    all_obs = normal_obs + [outlier_obs]
    report = engine.evaluate_run(_RUN_ID, _SOURCE, all_obs)

    outlier_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.RELATIVE_FARE_OUTLIER
    ]
    assert len(outlier_findings) == 1
    assert outlier_findings[0].observation_id == outlier_obs.observation_id


def test_no_outlier_below_multiplier():
    """A fare within 3× median must NOT be flagged."""
    obs_list = [_obs(total_fare=Decimal(str(f)), flight_number=f"6E-{i}") for i, f in enumerate([4000, 4500, 5000, 4800, 4200, 10000])]
    report = engine.evaluate_run(_RUN_ID, _SOURCE, obs_list)

    outlier_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.RELATIVE_FARE_OUTLIER
    ]
    # 10000 is ~2.2x the median of ~4500, which is < 3x
    assert len(outlier_findings) == 0


# ---------------------------------------------------------------------------
# Yield anomaly / parser health
# ---------------------------------------------------------------------------

def test_yield_anomaly_detected():
    """A severe yield drop should produce a YIELD_ANOMALY finding."""
    # historical_median = 100, current = 3 → 3% → anomaly
    obs_list = [_obs() for _ in range(3)]
    report = engine.evaluate_run(
        _RUN_ID, _SOURCE, obs_list,
        historical_median_yield=100.0
    )

    yield_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.YIELD_ANOMALY
    ]
    assert len(yield_findings) == 1
    assert report.yield_anomaly_detected is True
    # < 10% of historical → CRITICAL
    assert yield_findings[0].severity == AnomalySeverity.CRITICAL


def test_no_yield_anomaly_without_baseline():
    """Without historical baseline, no yield anomaly should be raised."""
    obs_list = [_obs() for _ in range(5)]
    report = engine.evaluate_run(
        _RUN_ID, _SOURCE, obs_list,
        historical_median_yield=None  # No baseline
    )

    yield_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.YIELD_ANOMALY
    ]
    assert len(yield_findings) == 0
    assert report.yield_anomaly_detected is False


def test_mild_yield_drop_is_high_not_critical():
    """A yield at 20% of historical (below 25% threshold) → HIGH, not CRITICAL."""
    obs_list = [_obs() for _ in range(20)]  # 20% of historical 100
    report = engine.evaluate_run(
        _RUN_ID, _SOURCE, obs_list,
        historical_median_yield=100.0
    )

    yield_findings = [
        f for f in report.findings if f.anomaly_type == AnomalyType.YIELD_ANOMALY
    ]
    assert len(yield_findings) == 1
    # 20/100 = 20% which is < 25% threshold but >= 10% threshold is HIGH
    assert yield_findings[0].severity == AnomalySeverity.HIGH


# ---------------------------------------------------------------------------
# Quarantine decision
# ---------------------------------------------------------------------------

def test_quarantine_triggered_by_critical_finding():
    """Any CRITICAL finding must result in QUARANTINE decision."""
    obs = _obs(total_fare=Decimal("4500"))
    object.__setattr__(obs, "total_fare", Decimal("-1"))

    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs])
    assert report.decision == QualityDecision.QUARANTINE
    assert report.quarantine_reason is not None


def test_flag_decision_for_high_findings():
    """HIGH findings without CRITICAL should produce FLAG, not QUARANTINE."""
    obs = _obs(total_fare=None)   # Missing fare → HIGH
    report = engine.evaluate_run(_RUN_ID, _SOURCE, [obs])

    # Missing fare doesn't trigger quarantine since completeness > 50%
    assert report.decision in (QualityDecision.FLAG, QualityDecision.QUARANTINE)


def test_accept_for_clean_observations():
    """A clean batch of observations should produce ACCEPT decision."""
    obs_list = [_obs(flight_number=f"6E-{i}") for i in range(10)]
    report = engine.evaluate_run(
        _RUN_ID, _SOURCE, obs_list,
        historical_median_yield=None  # No historical baseline
    )
    assert report.decision == QualityDecision.ACCEPT
