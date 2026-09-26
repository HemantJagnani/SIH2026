"""
Unit Tests for APIx Phase 2 Canonical Models & Fingerprints.
Tests:
- RawFareObservation
- NormalizedFareObservation
- ProductStratum
- ItineraryFingerprint
- OfferFingerprint
- Full normalization pipeline on real scraped dataset
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import pytest

from models.canonical import (
    RawFareObservation,
    NormalizedFareObservation,
    ProductStratum,
    classify_travel_day_type,
    classify_departure_time_band,
    classify_lead_time_class,
    classify_stop_category,
)
from models.fingerprint import compute_itinerary_fingerprint, compute_offer_fingerprint
from normalization.pipeline import normalize_record, normalize_dataset


def test_product_stratum_deterministic_hash():
    """Verify that ProductStratum generates identical hashes for identical specifications."""
    stratum1 = ProductStratum(
        origin="DEL",
        destination="BOM",
        travel_day_type="WEEKDAY",
        departure_time_band="MORNING",
        cabin="ECONOMY",
        fare_family_group="STANDARD",
        baggage_group="STANDARD",
        stop_category="NONSTOP",
        passenger_type="ADULT",
        lead_time_class="T+7",
    )
    stratum2 = ProductStratum(
        origin="del",  # lower case should produce same id
        destination="bom",
        travel_day_type="weekday",
        departure_time_band="morning",
        cabin="economy",
        fare_family_group="standard",
        baggage_group="standard",
        stop_category="nonstop",
        passenger_type="adult",
        lead_time_class="t+7",
    )
    assert stratum1.stratum_id == stratum2.stratum_id
    assert len(stratum1.stratum_id) == 64  # SHA-256


def test_itinerary_and_offer_fingerprints():
    """Verify deterministic behavior of itinerary and offer fingerprints."""
    d = date(2026, 9, 29)
    itin1 = compute_itinerary_fingerprint("DEL", "BOM", d, "IndiGo", "6E-2054", "07:00", "09:15", 0)
    itin2 = compute_itinerary_fingerprint("del", "bom", d, "indigo", "6e-2054", "07:00", "09:15", 0)
    assert itin1 == itin2

    # Different flight number must produce different itinerary fingerprint
    itin_diff = compute_itinerary_fingerprint("DEL", "BOM", d, "IndiGo", "6E-9999", "07:00", "09:15", 0)
    assert itin1 != itin_diff

    # Offer fingerprint matches for same offer characteristics
    off1 = compute_offer_fingerprint(itin1, "STANDARD", "ECONOMY", "STANDARD")
    off2 = compute_offer_fingerprint(itin1, "standard", "economy", "standard")
    assert off1 == off2

    # Different cabin produces different offer fingerprint
    off_biz = compute_offer_fingerprint(itin1, "STANDARD", "BUSINESS", "STANDARD")
    assert off1 != off_biz


def test_normalized_fare_observation_validation():
    """Verify NormalizedFareObservation enforces Decimal monetary precision and validates INR."""
    obs = NormalizedFareObservation(
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 29),
        lead_days=7,
        airline="IndiGo",
        flight_number="6E-2054",
        total_fare=Decimal("7500.50"),
        source="easemytrip",
        collection_run_id="825fa969-5811-49c8-9854-40637fd438a2",
    )
    assert isinstance(obs.total_fare, Decimal)
    assert obs.total_fare == Decimal("7500.50")
    assert obs.currency == "INR"
    assert obs.route == "DEL-BOM"
    assert obs.travel_day_type == "WEEKDAY"
    assert obs.lead_time_class == "T+7"
    assert obs.month == "2026-09"
    assert len(obs.itinerary_fingerprint) == 64
    assert len(obs.offer_fingerprint) == 64
    assert len(obs.product_stratum_id) == 64

    # Non-INR must raise ValueError
    with pytest.raises(ValueError, match="APIx only accepts INR currency"):
        NormalizedFareObservation(
            origin="DEL",
            destination="BOM",
            travel_date=date(2026, 9, 29),
            lead_days=7,
            airline="IndiGo",
            flight_number="6E-2054",
            total_fare=Decimal("7500.50"),
            currency="USD",
            source="easemytrip",
            collection_run_id="825fa969-5811-49c8-9854-40637fd438a2",
        )


def test_raw_fare_observation_structure():
    """Verify RawFareObservation captures verbatim raw fields and payload."""
    raw = RawFareObservation(
        source="easemytrip",
        origin_raw="DEL",
        destination_raw="BOM",
        travel_date_raw="2026-09-29",
        lead_days_raw=7,
        price_raw="₹ 6,529.00",
        raw_payload={"card_index": 1, "raw_text": "Air India Express IX-1165 Rs. 6529"},
    )
    assert raw.source == "easemytrip"
    assert raw.price_raw == "₹ 6,529.00"
    assert raw.raw_payload["card_index"] == 1


def test_normalization_pipeline_on_real_easemytrip_dataset():
    """Verify normalizing all 145 real observations from easemytrip_parsed_data.json."""
    json_path = Path("easemytrip_parsed_data.json")
    assert json_path.exists(), "easemytrip_parsed_data.json must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    assert len(records) == 145
    normalized_list = normalize_dataset(records)

    # All 145 records must normalize successfully
    assert len(normalized_list) == 145

    # Check properties of normalized observations
    for obs in normalized_list:
        assert isinstance(obs, NormalizedFareObservation)
        assert isinstance(obs.total_fare, Decimal)
        assert obs.total_fare > Decimal("0")
        assert obs.origin == "DEL"
        assert obs.destination == "BOM"
        assert obs.currency == "INR"
        assert obs.lead_time_class == "T+7"
        assert obs.departure_time_local is not None  # Timings successfully extracted!
        assert obs.arrival_time_local is not None
        assert obs.departure_time_band in ("EARLY_MORNING", "MORNING", "AFTERNOON", "EVENING")
        assert obs.quality_status in ("VALID", "DUPLICATE")

    # Now verify that duplicate ingestion is properly detected and tagged:
    records_with_duplicates = records + [records[0], records[1], records[2]]
    normalized_with_dups = normalize_dataset(records_with_duplicates)
    assert len(normalized_with_dups) == 148
    
    dups = [o for o in normalized_with_dups if o.quality_status == "DUPLICATE"]
    assert len(dups) == 3
    for d in dups:
        assert d.duplicate_group_id is not None
        assert d.duplicate_group_id.startswith("dup_")
