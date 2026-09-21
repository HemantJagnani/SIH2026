"""
Tests for Phase 1 canonical contract models.

Covers:
- All enums (CollectionStatus, TripType, CabinClass, AvailabilityStatus,
  CollectionMode, JobLifecycleStatus)
- FareSearchRequest (defaults, validators, edge cases)
- PassengerCount
- FareObservation (all fields, validators, schema version)
- RawObservation
- CollectionResult (properties)

Source: spec §6, §11, §12, §13, §40, §44 Phase 1.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from models import (
    AvailabilityStatus,
    CabinClass,
    CollectionMode,
    CollectionResult,
    CollectionStatus,
    FareObservation,
    FareSearchRequest,
    JobLifecycleStatus,
    PassengerCount,
    RawObservation,
    SCHEMA_VERSION,
    TripType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_raw_obs(**overrides) -> RawObservation:
    defaults = dict(
        collection_run_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        source="indigo",
        collection_timestamp=datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc),
        collection_method=CollectionMode.API,
        parser_version="1.0.0",
        adapter_version="1.0.0",
    )
    defaults.update(overrides)
    return RawObservation(**defaults)


def make_observation(**overrides) -> FareObservation:
    defaults = dict(
        collection_run_id=uuid.uuid4(),
        source="indigo",
        collected_at=datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc),
        travel_date=date(2026, 9, 28),
        lead_days=7,
        origin="DEL",
        destination="BOM",
        airline="IndiGo",
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        passenger_count=1,
        availability=AvailabilityStatus.AVAILABLE,
        adapter_version="1.0.0",
        normalizer_version="1.0.0",
    )
    defaults.update(overrides)
    return FareObservation(**defaults)


def make_request(**overrides) -> FareSearchRequest:
    defaults = dict(
        source="indigo",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 28),
        lead_days=7,
        collection_mode=CollectionMode.API,
    )
    defaults.update(overrides)
    return FareSearchRequest(**defaults)


# ===========================================================================
# Enums
# ===========================================================================

class TestEnums:
    def test_collection_status_all_values(self):
        """Spec §12: all 13 statuses must exist."""
        expected = {
            "SUCCESS", "NO_RESULTS", "SOLD_OUT", "NOT_FOUND", "SOURCE_ERROR",
            "TIMEOUT", "RATE_LIMITED", "ACCESS_RESTRICTED", "CAPTCHA_PRESENT",
            "PARSER_ERROR", "VALIDATION_ERROR", "NORMALIZATION_ERROR", "UNKNOWN_ERROR",
        }
        actual = {s.value for s in CollectionStatus}
        assert actual == expected

    def test_trip_type_values(self):
        assert TripType.ONE_WAY.value == "ONE_WAY"
        assert TripType.ROUND_TRIP.value == "ROUND_TRIP"

    def test_cabin_class_has_unknown(self):
        """UNKNOWN must exist for sources that don't specify cabin. Spec §13."""
        assert CabinClass.UNKNOWN.value == "UNKNOWN"

    def test_availability_status_sold_out_not_zero(self):
        """SOLD_OUT must be a distinct value, not confused with zero price. Spec §20."""
        assert AvailabilityStatus.SOLD_OUT.value == "SOLD_OUT"
        assert AvailabilityStatus.SOLD_OUT != AvailabilityStatus.AVAILABLE

    def test_lifecycle_status_happy_path(self):
        """Spec §40: all happy-path statuses exist."""
        happy = {
            "CREATED", "QUEUED", "RUNNING", "SOURCE_RESPONSE",
            "EXTRACTED", "NORMALIZED", "VALIDATED", "QUALITY_CHECKED", "PUBLISHED",
        }
        actual = {s.value for s in JobLifecycleStatus}
        assert happy.issubset(actual)

    def test_lifecycle_status_failure_paths(self):
        """Spec §40: all failure-path statuses exist."""
        failure = {
            "FAILED", "RESTRICTED", "TIMEOUT",
            "NORMALIZATION_EXCEPTION", "AI_FALLBACK", "RESOLVED", "QUARANTINED",
        }
        actual = {s.value for s in JobLifecycleStatus}
        assert failure.issubset(actual)

    def test_enums_are_strings(self):
        """All enums must be str subclasses for JSON/Pydantic serialization."""
        assert isinstance(CollectionStatus.SUCCESS, str)
        assert isinstance(TripType.ONE_WAY, str)
        assert isinstance(CabinClass.ECONOMY, str)
        assert isinstance(AvailabilityStatus.AVAILABLE, str)
        assert isinstance(CollectionMode.API, str)


# ===========================================================================
# PassengerCount
# ===========================================================================

class TestPassengerCount:
    def test_defaults_match_spec(self):
        """Spec §6: defaults are adults=1, children=0, infants=0."""
        pc = PassengerCount()
        assert pc.adults == 1
        assert pc.children == 0
        assert pc.infants == 0

    def test_adults_must_be_at_least_one(self):
        with pytest.raises(ValidationError):
            PassengerCount(adults=0)

    def test_no_negative_children(self):
        with pytest.raises(ValidationError):
            PassengerCount(children=-1)

    def test_no_negative_infants(self):
        with pytest.raises(ValidationError):
            PassengerCount(infants=-1)


# ===========================================================================
# FareSearchRequest
# ===========================================================================

class TestFareSearchRequest:
    def test_valid_request(self):
        req = make_request()
        assert req.source == "indigo"
        assert req.origin == "DEL"
        assert req.destination == "BOM"
        assert req.lead_days == 7

    def test_defaults_match_spec(self):
        """Spec §6: adults=1, children=0, infants=0, cabin=ECONOMY, trip=ONE_WAY, currency=INR."""
        req = make_request()
        assert req.passenger_count.adults == 1
        assert req.passenger_count.children == 0
        assert req.passenger_count.infants == 0
        assert req.cabin == CabinClass.ECONOMY
        assert req.trip_type == TripType.ONE_WAY
        assert req.currency == "INR"

    def test_iata_codes_uppercased(self):
        """IATA codes must be normalized to uppercase."""
        req = make_request(origin="del", destination="bom")
        assert req.origin == "DEL"
        assert req.destination == "BOM"

    def test_origin_equals_destination_raises(self):
        """Spec §20: origin must differ from destination."""
        with pytest.raises(ValidationError, match="must differ"):
            make_request(origin="DEL", destination="DEL")

    def test_non_inr_currency_raises(self):
        """Spec §6: currency must be INR."""
        with pytest.raises(ValidationError, match="INR"):
            make_request(currency="USD")

    def test_request_id_auto_generated(self):
        r1 = make_request()
        r2 = make_request()
        assert r1.request_id != r2.request_id

    def test_request_id_can_be_provided(self):
        fixed_id = uuid.uuid4()
        req = make_request(request_id=fixed_id)
        assert req.request_id == fixed_id

    def test_frozen_model(self):
        """FareSearchRequest must be immutable."""
        req = make_request()
        with pytest.raises(Exception):
            req.source = "cleartrip"  # type: ignore[misc]


# ===========================================================================
# RawObservation
# ===========================================================================

class TestRawObservation:
    def test_valid_raw_observation(self):
        raw = make_raw_obs()
        assert raw.source == "indigo"
        assert raw.parser_version == "1.0.0"
        assert raw.adapter_version == "1.0.0"

    def test_http_status_range(self):
        """HTTP status must be a valid 3-digit code."""
        raw = make_raw_obs(http_status=200)
        assert raw.http_status == 200

    def test_invalid_http_status_raises(self):
        with pytest.raises(ValidationError):
            make_raw_obs(http_status=99)

    def test_response_time_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            make_raw_obs(response_time_ms=-1)

    def test_optional_fields_default_to_none(self):
        raw = make_raw_obs()
        assert raw.raw_evidence_uri is None
        assert raw.http_status is None
        assert raw.source_url_or_endpoint_reference is None


# ===========================================================================
# FareObservation
# ===========================================================================

class TestFareObservation:
    def test_valid_minimal_observation(self):
        obs = make_observation()
        assert obs.source == "indigo"
        assert obs.origin == "DEL"
        assert obs.destination == "BOM"
        assert obs.airline == "IndiGo"

    def test_observation_id_auto_generated(self):
        o1 = make_observation()
        o2 = make_observation()
        assert o1.observation_id != o2.observation_id

    def test_schema_version_matches_constant(self):
        """Every observation must carry the current schema version. Spec §44."""
        obs = make_observation()
        assert obs.schema_version == SCHEMA_VERSION

    def test_wrong_schema_version_raises(self):
        with pytest.raises(ValidationError, match="schema_version mismatch"):
            make_observation(schema_version="0.0.0")

    def test_iata_codes_uppercased(self):
        obs = make_observation(origin="del", destination="bom")
        assert obs.origin == "DEL"
        assert obs.destination == "BOM"

    def test_origin_equals_destination_raises(self):
        """Spec §20: origin must differ from destination."""
        with pytest.raises(ValidationError, match="must differ"):
            make_observation(origin="DEL", destination="DEL")

    def test_travel_date_before_collection_raises(self):
        """Spec §20: travel_date >= collection_date."""
        with pytest.raises(ValidationError, match="travel_date"):
            make_observation(
                collected_at=datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc),
                travel_date=date(2026, 9, 20),  # yesterday
            )

    def test_optional_fare_fields_default_to_none(self):
        obs = make_observation()
        assert obs.base_fare is None
        assert obs.taxes is None
        assert obs.fees is None
        assert obs.discount is None
        assert obs.total_fare is None

    def test_fare_fields_accept_decimal(self):
        obs = make_observation(
            base_fare=Decimal("3500.00"),
            taxes=Decimal("800.00"),
            fees=Decimal("200.00"),
            discount=Decimal("0.00"),
            total_fare=Decimal("4500.00"),
        )
        assert obs.total_fare == Decimal("4500.00")

    def test_negative_fare_raises(self):
        """Spec §20: total_fare >= 0."""
        with pytest.raises(ValidationError):
            make_observation(total_fare=Decimal("-100.00"))

    def test_sold_out_is_not_zero_price(self):
        """Spec §20: SOLD_OUT availability != zero price. Validate they are distinct."""
        obs = make_observation(
            availability=AvailabilityStatus.SOLD_OUT,
            total_fare=None,  # Sold-out: no fare, NOT zero
        )
        assert obs.availability == AvailabilityStatus.SOLD_OUT
        assert obs.total_fare is None  # Explicitly null, not zero

    def test_currency_uppercased(self):
        obs = make_observation(currency="inr")
        assert obs.currency == "INR"

    def test_stops_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            make_observation(stops=-1)

    def test_passenger_count_at_least_one(self):
        with pytest.raises(ValidationError):
            make_observation(passenger_count=0)


# ===========================================================================
# CollectionResult
# ===========================================================================

class TestCollectionResult:
    def test_successful_result(self):
        raw = make_raw_obs()
        obs = make_observation()
        result = CollectionResult(
            status=CollectionStatus.SUCCESS,
            raw=raw,
            observations=[obs],
        )
        assert result.is_success is True
        assert result.observation_count == 1

    def test_failed_result_empty_observations(self):
        raw = make_raw_obs()
        result = CollectionResult(
            status=CollectionStatus.TIMEOUT,
            raw=raw,
            observations=[],
            error_message="Request timed out after 30s",
        )
        assert result.is_success is False
        assert result.observation_count == 0
        assert result.error_message == "Request timed out after 30s"

    def test_rate_limited_result(self):
        raw = make_raw_obs()
        result = CollectionResult(
            status=CollectionStatus.RATE_LIMITED,
            raw=raw,
            error_message="Source returned 429",
        )
        assert result.status == CollectionStatus.RATE_LIMITED
        assert result.is_success is False

    def test_captcha_result(self):
        """Spec §12 & §29: CAPTCHA must be recorded, not bypassed."""
        raw = make_raw_obs()
        result = CollectionResult(
            status=CollectionStatus.CAPTCHA_PRESENT,
            raw=raw,
            error_message="CAPTCHA detected; job paused.",
        )
        assert result.status == CollectionStatus.CAPTCHA_PRESENT

    def test_default_observations_is_empty_list(self):
        raw = make_raw_obs()
        result = CollectionResult(status=CollectionStatus.NO_RESULTS, raw=raw)
        assert result.observations == []
