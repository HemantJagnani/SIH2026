"""
Comprehensive Test Suite for Cross-Source Fare Reconciliation Layer.
Covers all 16 test specifications from §16 of the APIx Cross-Source Specification.
"""

from decimal import Decimal
import pytest

from reconciliation.models import (
    CanonicalOffer,
    MatchStatus,
    PriceSemantics,
    RawSourceObservation,
)
from reconciliation.registry import SourceConfig, SourceRegistry
from reconciliation.adapters import (
    BaseReconciliationAdapter,
    EaseMyTripReconciliationAdapter,
    GoogleFlightsReconciliationAdapter,
    IxigoReconciliationAdapter,
)
from reconciliation.engine import CrossSourceReconciliationEngine
from reconciliation.pipeline import CrossSourceReconciliationPipeline


@pytest.fixture
def engine():
    return CrossSourceReconciliationEngine()


@pytest.fixture
def pipeline():
    return CrossSourceReconciliationPipeline()


# ── TEST 1: Google + EaseMyTrip identical offer → one canonical offer ─────────
def test_1_google_easemytrip_identical_offer(pipeline):
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_001",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "lead_days": 7,
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "arrival_time_local": "12:15",
        "stops": 0,
        "cabin": "ECONOMY",
        "total_fare": 6500.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_001",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "lead_days": 7,
        "airline": "IndiGo",
        "flight_number": "6E204",
        "departure_time_local": "10:00",
        "arrival_time_local": "12:15",
        "stops": 0,
        "cabin": "ECONOMY",
        "fare_family": "Saver",
        "cabin_baggage_kg": 7,
        "checkin_baggage_kg": 15,
        "refund_status": "NON_REFUNDABLE",
        "total_fare": 6500.0,
    }

    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt])

    assert len(valid_obs) == 1, "Should merge identical offer into exactly 1 canonical APIx observation"
    can = valid_obs[0]
    assert can.flight_number == "6E204"
    assert can.total_fare == Decimal("6500")
    assert set(can.sources_contributing) == {"google_flights", "easemytrip"}
    assert can.match_status == MatchStatus.EXACT_MATCH
    assert diag.exact_cross_source_matches == 1


# ── TEST 2: Google + EaseMyTrip + Ixigo identical offer → one canonical offer ─
def test_2_three_sources_identical_offer(pipeline):
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_101",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India",
        "flight_number": "AI-805",
        "departure_time_local": "08:00",
        "stops": 0,
        "total_fare": 7000.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_101",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India",
        "flight_number": "AI805",
        "departure_time_local": "08:00",
        "stops": 0,
        "fare_family": "STANDARD",
        "total_fare": 7000.0,
    }
    raw_ixigo = {
        "source": "ixigo",
        "observation_id": "ixi_101",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India",
        "flight_number": "AI-805",
        "departure_time_local": "08:00",
        "stops": 0,
        "fare_family": "STANDARD",
        "total_fare": 7000.0,
    }

    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt, raw_ixigo])

    assert len(valid_obs) == 1, "Three sources for same product must yield exactly 1 canonical APIx observation"
    assert set(valid_obs[0].sources_contributing) == {"google_flights", "easemytrip", "ixigo"}
    assert valid_obs[0].match_status == MatchStatus.EXACT_MATCH


# ── TEST 3: Different flight numbers → separate offers ────────────────────────
def test_3_different_flight_numbers(pipeline):
    raw_1 = {
        "source": "google_flights",
        "observation_id": "gf_201",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_2 = {
        "source": "google_flights",
        "observation_id": "gf_202",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-5312",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }

    valid_obs, _, _ = pipeline.run([raw_1, raw_2])
    assert len(valid_obs) == 2, "Different flight numbers must produce separate canonical offers"


# ── TEST 4: Same flight but different fare family → separate offers ───────────
def test_4_different_fare_families(pipeline):
    raw_saver = {
        "source": "easemytrip",
        "observation_id": "emt_301",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "fare_family": "Saver",
        "total_fare": 6500.0,
    }
    raw_flexi = {
        "source": "easemytrip",
        "observation_id": "emt_302",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "fare_family": "FlexiPlus",
        "total_fare": 7800.0,
    }

    normalized = pipeline.normalize_batch([raw_saver, raw_flexi])
    reconciled, _ = pipeline.engine.reconcile(normalized)

    assert len(reconciled) == 2, "Different fare families on the same flight must remain separate canonical offers"
    assert any(o.fare_family == "Saver" for o in reconciled)
    assert any(o.fare_family == "FlexiPlus" for o in reconciled)


# ── TEST 5: Same flight with different baggage conditions → separate offers ───
def test_5_different_baggage_conditions(pipeline):
    raw_15kg = {
        "source": "easemytrip",
        "observation_id": "emt_401",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "SpiceJet",
        "flight_number": "SG-123",
        "departure_time_local": "14:00",
        "stops": 0,
        "fare_family": "STANDARD",
        "checkin_baggage_kg": 15,
        "total_fare": 5500.0,
    }
    raw_20kg = {
        "source": "easemytrip",
        "observation_id": "emt_402",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "SpiceJet",
        "flight_number": "SG-123",
        "departure_time_local": "14:00",
        "stops": 0,
        "fare_family": "SpiceMax",
        "checkin_baggage_kg": 20,
        "total_fare": 6900.0,
    }

    normalized = pipeline.normalize_batch([raw_15kg, raw_20kg])
    reconciled, _ = pipeline.engine.reconcile(normalized)
    assert len(reconciled) == 2, "Different baggage conditions must remain separate canonical offers"


# ── TEST 6: Missing Google fields → merge safely without fabrication ──────────
def test_6_missing_google_fields_merged_safely(pipeline):
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_501",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Akasa Air",
        "flight_number": "QP-1102",
        "departure_time_local": "15:30",
        "stops": 0,
        "total_fare": 5800.0,
        # baggage, refundability NOT provided by Google
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_501",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Akasa Air",
        "flight_number": "QP-1102",
        "departure_time_local": "15:30",
        "stops": 0,
        "fare_family": "Saver",
        "cabin_baggage_kg": 7,
        "checkin_baggage_kg": 15,
        "refund_status": "NON_REFUNDABLE",
        "total_fare": 5800.0,
    }

    valid_obs, _, _ = pipeline.run([raw_gf, raw_emt])
    assert len(valid_obs) == 1
    can = valid_obs[0]
    assert "7kg cabin + 15kg checkin" in can.baggage
    assert can.refundability == "NON_REFUNDABLE"
    assert can.field_provenance["baggage"] == "easemytrip"
    assert can.field_provenance["refundability"] == "easemytrip"


# ── TEST 7: Different prices for same apparent offer → PRICE_CONFLICT_REVIEW ──
def test_7_different_prices_flagged_for_review(pipeline):
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_601",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_601",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7200.0,  # Price differs!
    }

    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt])
    assert len(valid_obs) == 0, "Conflicting prices must NOT enter baseline price calculation silently"
    assert len(excluded) == 1
    conflicted = excluded[0]
    assert conflicted.match_status == MatchStatus.PRICE_CONFLICT_REVIEW
    assert conflicted.price_conflict is True
    assert conflicted.price_by_source["google_flights"] == Decimal("6500")
    assert conflicted.price_by_source["easemytrip"] == Decimal("7200")
    assert diag.price_conflicts == 1


# ── TEST 8: Google DOM duplicate → one physical source observation ────────────
def test_8_google_dom_duplicate(pipeline):
    raw_1 = {
        "source": "google_flights",
        "observation_id": "gf_701a",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_2 = {
        "source": "google_flights",
        "observation_id": "gf_701b",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }

    valid_obs, _, diag = pipeline.run([raw_1, raw_2])
    assert len(valid_obs) == 1, "Duplicate DOM extractions must collapse to 1 physical source offer"
    assert diag.duplicates_by_source["google_flights"] == 1


# ── TEST 9: EaseMyTrip duplicate → one physical source observation ────────────
def test_9_easemytrip_duplicate(pipeline):
    raw_1 = {
        "source": "easemytrip",
        "observation_id": "emt_801a",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "fare_family": "Saver",
        "total_fare": 6500.0,
    }
    raw_2 = {
        "source": "easemytrip",
        "observation_id": "emt_801b",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "fare_family": "Saver",
        "total_fare": 6500.0,
    }

    valid_obs, _, diag = pipeline.run([raw_1, raw_2])
    assert len(valid_obs) == 1
    assert diag.duplicates_by_source["easemytrip"] == 1


# ── TEST 10: Google-only offer → retained ─────────────────────────────────────
def test_10_google_only_offer(pipeline):
    raw = {
        "source": "google_flights",
        "observation_id": "gf_only",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India Express",
        "flight_number": "IX-101",
        "departure_time_local": "06:00",
        "stops": 0,
        "total_fare": 5400.0,
    }
    valid_obs, _, diag = pipeline.run([raw])
    assert len(valid_obs) == 1
    assert valid_obs[0].flight_number == "IX101"
    assert valid_obs[0].match_status == MatchStatus.NO_MATCH
    assert valid_obs[0].fare_family == "NOT_PROVIDED", "Missing Google Flights fare family must normalize to NOT_PROVIDED, never STANDARD"
    assert "fare_family" not in valid_obs[0].field_provenance
    assert diag.unmatched_observations == 1


# ── TEST 11: EaseMyTrip-only offer → retained ─────────────────────────────────
def test_11_easemytrip_only_offer(pipeline):
    raw = {
        "source": "easemytrip",
        "observation_id": "emt_only",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India Express",
        "flight_number": "IX-102",
        "departure_time_local": "07:00",
        "stops": 0,
        "fare_family": "Value",
        "total_fare": 5600.0,
    }
    valid_obs, _, diag = pipeline.run([raw])
    assert len(valid_obs) == 1
    assert valid_obs[0].flight_number == "IX102"
    assert valid_obs[0].match_status == MatchStatus.NO_MATCH


# ── TEST 12: Ixigo-only offer → retained ──────────────────────────────────────
def test_12_ixigo_only_offer(pipeline):
    raw = {
        "source": "ixigo",
        "observation_id": "ixi_only",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "SpiceJet",
        "flight_number": "SG-819",
        "departure_time_local": "18:30",
        "stops": 0,
        "total_fare": 6100.0,
    }
    valid_obs, _, diag = pipeline.run([raw])
    assert len(valid_obs) == 1
    assert valid_obs[0].flight_number == "SG819"
    assert valid_obs[0].match_status == MatchStatus.NO_MATCH


# ── TEST 13: Probable match → NOT automatically merged ────────────────────────
def test_13_probable_match_not_automatically_merged(pipeline):
    # Same flight number but departure time differs significantly (e.g. 10:00 vs 14:00)
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_prob",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_prob",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "14:00",  # Different flight timing!
        "stops": 0,
        "total_fare": 6500.0,
    }

    normalized = pipeline.normalize_batch([raw_gf, raw_emt])
    reconciled, _ = pipeline.engine.reconcile(normalized)

    assert len(reconciled) == 2, "Flights with different schedule times must not be merged"


# ── TEST 14: Insufficient identifying fields → INSUFFICIENT_DATA ──────────────
def test_14_insufficient_identifying_fields(pipeline):
    raw_missing_fn = {
        "source": "google_flights",
        "observation_id": "gf_insufficient",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "UNKNOWN",  # Missing flight number!
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }

    valid_obs, excluded, diag = pipeline.run([raw_missing_fn])
    assert len(valid_obs) == 0, "Observations missing crucial identifiers must not enter valid baseline"
    assert len(excluded) == 1
    assert excluded[0].match_status == MatchStatus.INSUFFICIENT_DATA
    assert diag.insufficient_data_observations == 1


# ── TEST 15: Different price semantics → not automatically comparable ─────────
def test_15_different_price_semantics_not_comparable(pipeline):
    raw_total = {
        "source": "google_flights",
        "observation_id": "gf_total",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_from = {
        "source": "ixigo",
        "observation_id": "ixi_from",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }

    norm_gf = pipeline._adapter_instances["google_flights"].normalize(raw_total)
    norm_ixi = pipeline._adapter_instances["ixigo"].normalize(raw_from)
    norm_ixi.price_semantics = PriceSemantics.DISPLAYED_FROM  # "Starting from" price, not guaranteed total

    reconciled, diag = pipeline.engine.reconcile([norm_gf, norm_ixi])
    assert len(reconciled) == 2, "Offers with incompatible price semantics must remain separate"
    assert diag.probable_matches == 2


# ── TEST 16: Future-source registration without modifying core logic ──────────
def test_16_future_source_registration(pipeline):
    class MockFutureSourceAdapter(BaseReconciliationAdapter):
        @property
        def source_id(self) -> str:
            return "future_ota"

        @property
        def source_name(self) -> str:
            return "Future OTA"

        def normalize(self, raw_record):
            return self._build_canonical_offer(
                raw_id=raw_record.get("id", "future_001"),
                origin=raw_record.get("src", "DEL"),
                destination=raw_record.get("dst", "BOM"),
                travel_date=raw_record.get("date", "2026-10-04"),
                airline=raw_record.get("carrier", "IndiGo"),
                flight_number=raw_record.get("fn", "6E-204"),
                departure_time=raw_record.get("dep", "10:00"),
                arrival_time="12:15",
                total_fare=raw_record.get("fare", 6500.0),
                stops=0,
            )

    # 1. Register future source in SourceRegistry
    custom_config = SourceConfig(
        source_id="future_ota",
        source_name="Future OTA",
        supported_fields={"route", "airline", "flight_number", "departure_time", "total_fare"},
    )
    pipeline.registry.register_source(custom_config)

    # 2. Register future adapter in pipeline
    pipeline.register_adapter(MockFutureSourceAdapter())

    # 3. Test reconciliation with existing sources
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_future_test",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_future = {
        "source": "future_ota",
        "id": "future_123",
        "src": "DEL",
        "dst": "BOM",
        "date": "2026-10-04",
        "carrier": "IndiGo",
        "fn": "6E-204",
        "dep": "10:00",
        "fare": 6500.0,
    }

    valid_obs, _, diag = pipeline.run([raw_gf, raw_future])
    assert len(valid_obs) == 1, "Future source must integrate and reconcile seamlessly"
    assert set(valid_obs[0].sources_contributing) == {"google_flights", "future_ota"}
    assert diag.exact_cross_source_matches == 1
