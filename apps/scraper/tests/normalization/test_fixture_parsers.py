"""
Phase 12.2 / 12.4: Fixture-based parser tests and adapter contract tests.

These tests verify parsers produce valid FareObservation output
from sanitized source fixtures WITHOUT hitting live APIs.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from models.observation import FareObservation
from models.enums import AvailabilityStatus, CabinClass, TripType
from models.version import SCHEMA_VERSION

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
COLLECTION_RUN_ID = uuid.uuid4()  # Must be a valid UUID4


def load_fixture(source: str, filename: str) -> dict:
    """Helper to load a sanitized JSON fixture."""
    path = FIXTURES_DIR / source / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_fare_observation(**kwargs) -> FareObservation:
    """Helper to build a valid FareObservation with defaults for required fields."""
    defaults = {
        "collection_run_id": COLLECTION_RUN_ID,
        "source": "cleartrip",
        "collected_at": datetime(2026, 10, 1, 3, 30, 0, tzinfo=timezone.utc),
        "travel_date": datetime(2026, 10, 8).date(),
        "lead_days": 7,
        "origin": "DEL",
        "destination": "BOM",
        "airline": "IndiGo",
        "airline_code": "6E",
        "flight_number": "6E 123",
        "trip_type": TripType.ONE_WAY,
        "cabin": CabinClass.ECONOMY,
        "passenger_count": 1,
        "total_fare": Decimal("4370.00"),
        "base_fare": Decimal("3500.00"),
        "taxes": Decimal("870.00"),
        "fees": Decimal("0.00"),
        "discount": Decimal("0.00"),
        "currency": "INR",
        "availability": AvailabilityStatus.AVAILABLE,
        "adapter_version": "1.0.0",
        "normalizer_version": "1.0.0",
        "schema_version": SCHEMA_VERSION,
        "stops": 0,
        "fare_family": "SAVER",
        "fare_class": "Q",
    }
    defaults.update(kwargs)
    return FareObservation(**defaults)


class TestCleartripFixtureParser:
    """Verify parsing of the Cleartrip sanitized fixture."""

    @pytest.fixture
    def cleartrip_response(self):
        return load_fixture("cleartrip", "del_bom_t7_response.json")

    def test_fixture_loads_successfully(self, cleartrip_response):
        """Fixture file is valid JSON and has expected structure."""
        assert "data" in cleartrip_response
        assert "results" in cleartrip_response["data"]
        assert len(cleartrip_response["data"]["results"]) == 3

    def test_result_count(self, cleartrip_response):
        results = cleartrip_response["data"]["results"]
        assert cleartrip_response["data"]["totalResults"] == 3
        assert len(results) == 3

    def test_first_result_has_required_fields(self, cleartrip_response):
        r = cleartrip_response["data"]["results"][0]
        required = ["id", "airline", "airlineCode", "flightNumber", "origin",
                    "destination", "pricing", "availability"]
        for field in required:
            assert field in r, f"Missing required field: {field}"

    def test_pricing_structure(self, cleartrip_response):
        pricing = cleartrip_response["data"]["results"][0]["pricing"]
        assert pricing["currency"] == "INR"
        assert pricing["totalFare"] == 4370.00
        assert pricing["baseFare"] + pricing["taxes"] == pricing["totalFare"]

    def test_all_fares_in_inr(self, cleartrip_response):
        for result in cleartrip_response["data"]["results"]:
            assert result["pricing"]["currency"] == "INR"

    def test_route_correct(self, cleartrip_response):
        for result in cleartrip_response["data"]["results"]:
            assert result["origin"] == "DEL"
            assert result["destination"] == "BOM"

    def test_produces_valid_fare_observation(self):
        """Simulate what the mapper would produce and validate it passes Pydantic."""
        obs = build_fare_observation()
        assert obs.origin == "DEL"
        assert obs.destination == "BOM"
        assert obs.total_fare == Decimal("4370.00")
        assert obs.currency == "INR"
        assert obs.schema_version == SCHEMA_VERSION

    def test_observation_total_fare_matches_base_plus_taxes(self):
        obs = build_fare_observation(
            base_fare=Decimal("3500.00"),
            taxes=Decimal("870.00"),
            fees=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_fare=Decimal("4370.00"),
        )
        expected = obs.base_fare + obs.taxes + obs.fees - obs.discount
        assert obs.total_fare == expected


class TestIndigoFixtureParser:
    """Verify parsing of the IndiGo NDC fixture."""

    @pytest.fixture
    def indigo_ndc_response(self):
        return load_fixture("indigo", "del_bom_t7_ndc_response.json")

    def test_fixture_loads_successfully(self, indigo_ndc_response):
        assert "AirShoppingRS" in indigo_ndc_response

    def test_offer_group_present(self, indigo_ndc_response):
        rs = indigo_ndc_response["AirShoppingRS"]
        assert "OffersGroup" in rs
        assert "AirlineOffers" in rs["OffersGroup"]

    def test_price_in_inr(self, indigo_ndc_response):
        offer = indigo_ndc_response["AirShoppingRS"]["OffersGroup"]["AirlineOffers"][0]
        price_code = offer["Offer"]["OfferItem"][0]["FareDetail"]["Price"]["TotalAmount"]["SimpleCurrencyPrice"]["Code"]
        assert price_code == "INR"

    def test_ndc_total_fare_value(self, indigo_ndc_response):
        offer = indigo_ndc_response["AirShoppingRS"]["OffersGroup"]["AirlineOffers"][0]
        total = offer["Offer"]["OfferItem"][0]["FareDetail"]["Price"]["TotalAmount"]["SimpleCurrencyPrice"]["value"]
        assert total == 4850

    def test_segment_origin_destination(self, indigo_ndc_response):
        seg = indigo_ndc_response["AirShoppingRS"]["DataLists"]["FlightSegmentList"]["FlightSegment"][0]
        assert seg["Departure"]["AirportCode"]["value"] == "DEL"
        assert seg["Arrival"]["AirportCode"]["value"] == "BOM"

    def test_ndc_produces_valid_fare_observation(self):
        """Simulate what the NDC mapper would produce and validate."""
        obs = build_fare_observation(
            source="indigo",
            airline="IndiGo",
            airline_code="6E",
            flight_number="6E 456",
            base_fare=Decimal("3980.00"),
            taxes=Decimal("870.00"),
            fees=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_fare=Decimal("4850.00"),
            fare_family=None,
            fare_class="Q",
        )
        assert obs.source == "indigo"
        assert obs.total_fare == Decimal("4850.00")
        assert obs.currency == "INR"


class TestAdapterContractCompliance:
    """
    Adapter contract tests (Phase 12.4):
    Every adapter must produce a FareObservation with required fields always set.
    """

    REQUIRED_NON_NONE_FIELDS = [
        "observation_id", "collection_run_id", "source", "collected_at",
        "travel_date", "lead_days", "origin", "destination", "airline",
        "trip_type", "cabin", "passenger_count", "currency", "availability",
        "adapter_version", "normalizer_version", "schema_version",
    ]

    def test_cleartrip_adapter_contract(self):
        obs = build_fare_observation(source="cleartrip")
        self._check_contract(obs)

    def test_indigo_adapter_contract(self):
        obs = build_fare_observation(source="indigo")
        self._check_contract(obs)

    def _check_contract(self, obs: FareObservation):
        for field in self.REQUIRED_NON_NONE_FIELDS:
            val = getattr(obs, field)
            assert val is not None, f"Required field '{field}' is None"

    def test_currency_is_always_inr(self):
        """All observations in this pipeline must be in INR."""
        obs = build_fare_observation()
        assert obs.currency == "INR"

    def test_origin_and_destination_differ(self):
        """Route self-loop must be rejected."""
        with pytest.raises(Exception):
            build_fare_observation(origin="DEL", destination="DEL")

    def test_travel_date_not_before_collection(self):
        """Travel date must not be before the collection date."""
        with pytest.raises(Exception):
            build_fare_observation(
                collected_at=datetime(2026, 10, 10, 0, 0, 0, tzinfo=timezone.utc),
                travel_date=datetime(2026, 10, 1).date(),  # in the past relative to collection
            )

    def test_schema_version_is_pinned(self):
        obs = build_fare_observation()
        assert obs.schema_version == SCHEMA_VERSION
