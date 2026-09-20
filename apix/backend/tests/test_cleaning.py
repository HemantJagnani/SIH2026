"""Unit tests for the cleaning pipeline."""
import pytest
from datetime import date, datetime, timezone

from app.services.cleaning.pipeline import (
    validate_observation,
    make_duplicate_key,
    clean_observations,
)
from app.services.ingestion.source_adapter import RawFareObservation


def make_obs(**kwargs) -> RawFareObservation:
    defaults = dict(
        source_name="airline_direct",
        airline_code="6E",
        origin="DEL",
        destination="BOM",
        search_timestamp=datetime.now(timezone.utc),
        travel_date=date(2026, 9, 5),
        lead_days=7,
        fare_class="economy",
        passenger_count=1,
        base_fare=5000.0,
        taxes=900.0,
        airport_charges=300.0,
        convenience_fee=0.0,
        total_fare=6200.0,
        currency="INR",
        availability="available",
        raw_payload={"synthetic": True},
    )
    defaults.update(kwargs)
    return RawFareObservation(**defaults)


def test_valid_observation():
    obs = make_obs()
    status, reason = validate_observation(obs)
    assert status == "valid"
    assert reason is None


def test_negative_fare_invalid():
    obs = make_obs(total_fare=-100.0)
    status, reason = validate_observation(obs)
    assert status == "invalid"
    assert "Negative" in reason


def test_non_inr_currency_invalid():
    obs = make_obs(currency="USD")
    status, reason = validate_observation(obs)
    assert status == "invalid"
    assert "currency" in reason.lower()


def test_sold_out_is_missing():
    obs = make_obs(availability="sold_out", total_fare=None)
    status, reason = validate_observation(obs)
    assert status == "missing"


def test_missing_price_is_missing():
    obs = make_obs(total_fare=None, availability="available")
    status, reason = validate_observation(obs)
    assert status == "missing"


def test_same_origin_destination_invalid():
    obs = make_obs(origin="DEL", destination="DEL")
    status, reason = validate_observation(obs)
    assert status == "invalid"


def test_invalid_lead_days():
    obs = make_obs(lead_days=-1)
    status, reason = validate_observation(obs)
    assert status == "invalid"


def test_unsupported_fare_class():
    obs = make_obs(fare_class="luxury")
    status, reason = validate_observation(obs)
    assert status == "invalid"


def test_duplicate_detection():
    obs1 = make_obs()
    obs2 = make_obs()  # identical
    results = clean_observations([obs1, obs2])
    statuses = [r.quality_status for r in results]
    # One valid, one duplicate
    assert "valid" in statuses
    assert "duplicate" in statuses


def test_no_false_duplicate():
    obs1 = make_obs(airline_code="6E")
    obs2 = make_obs(airline_code="AI")  # different airline → not a duplicate
    results = clean_observations([obs1, obs2])
    statuses = [r.quality_status for r in results]
    assert statuses.count("valid") == 2
    assert "duplicate" not in statuses


def test_outlier_flagged():
    obs_normal = make_obs(total_fare=5000.0)
    obs_outlier = make_obs(total_fare=25000.0, airline_code="AI")  # 5× median
    results = clean_observations([obs_normal, obs_outlier])
    outlier_results = [r for r in results if r.outlier_flag]
    assert len(outlier_results) >= 1


def test_all_anomalies_pipeline():
    """End-to-end test of the cleaning pipeline with various anomalies."""
    from app.services.ingestion.mock_adapter import generate_synthetic_dataset
    from app.core.config import settings

    raw = generate_synthetic_dataset(
        start_date=settings.BASE_DATE,
        num_days=5,
        seed=42,
    )
    results = clean_observations(raw)
    assert len(results) == len(raw)  # All records preserved

    # There should be at least some valid, some duplicates, some outliers
    statuses = [r.quality_status for r in results]
    assert "valid" in statuses
    assert "duplicate" in statuses or "missing" in statuses
