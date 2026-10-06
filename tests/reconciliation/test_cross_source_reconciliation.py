"""
Comprehensive Test Suite for Cross-Source Fare Reconciliation Layer.
Covers all 16 test specifications from §16 of the APIx Cross-Source Specification.
"""

from decimal import Decimal
from typing import Any
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
    assert can.match_status in (MatchStatus.PRICE_CONSISTENT, MatchStatus.EXACT_MATCH)
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
    assert valid_obs[0].match_status in (MatchStatus.PRICE_CONSISTENT, MatchStatus.EXACT_MATCH)


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


# ── TEST 7: Different prices for same apparent offer → PRICE_VARIANCE_AGGREGATED ──
def test_7_different_prices_arithmetic_mean_aggregated(pipeline):
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
    assert len(valid_obs) == 1, "Price variance must be aggregated with arithmetic mean, not excluded"
    assert len(excluded) == 0
    obs = valid_obs[0]
    assert obs.match_status == MatchStatus.PRICE_VARIANCE_AGGREGATED
    assert obs.total_fare == Decimal("6850.00")
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.aggregation_source_count == 2
    assert obs.price_by_source["google_flights"] == Decimal("6500.0")
    assert obs.price_by_source["easemytrip"] == Decimal("7200.0")
    assert diag.price_variances_aggregated == 1


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

        def normalize(self, raw_record: Any):
            raw = raw_record if isinstance(raw_record, dict) else getattr(raw_record, "raw_payload", {})
            return self._build_canonical_offer(
                raw_id=raw.get("id", "future_001"),
                origin=raw.get("src", "DEL"),
                destination=raw.get("dst", "BOM"),
                travel_date=raw.get("date", "2026-10-04"),
                airline=raw.get("carrier", "IndiGo"),
                flight_number=raw.get("fn", "6E-204"),
                departure_time=raw.get("dep", "10:00"),
                arrival_time="12:15",
                total_fare=raw.get("fare", 6500.0),
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


# ══════════════════════════════════════════════════════════════════════════════
# §11 EXPLICIT METHODOLOGY TESTS: TESTS A THROUGH K
# ══════════════════════════════════════════════════════════════════════════════

def test_a_two_sources_same_price(pipeline):
    """A. 2 sources, same price: Google ₹6500 + EMT ₹6500 → one observation ₹6500."""
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_a",
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
        "observation_id": "emt_a",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt])
    assert len(valid_obs) == 1
    assert len(excluded) == 0
    obs = valid_obs[0]
    assert obs.total_fare == Decimal("6500.00")
    assert obs.match_status in (MatchStatus.PRICE_CONSISTENT, MatchStatus.EXACT_MATCH)
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.aggregation_source_count == 2
    assert obs.source_count == 2
    assert obs.price_by_source == {"google_flights": Decimal("6500.0"), "easemytrip": Decimal("6500.0")}


def test_b_two_sources_different_prices(pipeline):
    """B. 2 sources, different prices: Google ₹6500 + EMT ₹7200 → one observation ₹6850."""
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_b",
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
        "observation_id": "emt_b",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7200.0,
    }
    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt])
    assert len(valid_obs) == 1
    assert len(excluded) == 0
    obs = valid_obs[0]
    assert obs.total_fare == Decimal("6850.00")
    assert obs.match_status == MatchStatus.PRICE_VARIANCE_AGGREGATED
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.aggregation_source_count == 2


def test_c_three_sources_different_prices(pipeline):
    """C. 3 sources, different prices: ₹6500, ₹7200, ₹6800 → one observation ₹6833.33."""
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_c",
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
        "observation_id": "emt_c",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7200.0,
    }
    raw_ixi = {
        "source": "ixigo",
        "observation_id": "ixi_c",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6800.0,
    }
    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt, raw_ixi])
    assert len(valid_obs) == 1
    assert len(excluded) == 0
    obs = valid_obs[0]
    # (6500 + 7200 + 6800) / 3 = 20500 / 3 = 6833.33
    assert obs.total_fare == Decimal("6833.33")
    assert obs.match_status == MatchStatus.PRICE_VARIANCE_AGGREGATED
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.aggregation_source_count == 3


def test_d_single_source(pipeline):
    """D. Single source → one observation at source price, method = SINGLE_SOURCE."""
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_d",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    valid_obs, excluded, diag = pipeline.run([raw_gf])
    assert len(valid_obs) == 1
    assert len(excluded) == 0
    obs = valid_obs[0]
    assert obs.total_fare == Decimal("6500.00")
    assert obs.source_count == 1
    assert obs.aggregation_method == "SINGLE_SOURCE"
    assert obs.aggregation_source_count == 1
    assert obs.match_status == MatchStatus.NO_MATCH


def test_e_different_fare_family(pipeline):
    """E. Different fare family → remain separate canonical products."""
    raw_saver = {
        "source": "easemytrip",
        "observation_id": "emt_saver",
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
        "observation_id": "emt_flexi",
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
    norm = pipeline.normalize_batch([raw_saver, raw_flexi])
    reconciled, _ = pipeline.engine.reconcile(norm)
    assert len(reconciled) == 2, "Different fare families must remain separate canonical offers"


def test_f_different_baggage_conditions(pipeline):
    """F. Different baggage/product conditions → remain separate canonical products."""
    raw_15kg = {
        "source": "easemytrip",
        "observation_id": "emt_15kg",
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
        "observation_id": "emt_20kg",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "SpiceJet",
        "flight_number": "SG-123",
        "departure_time_local": "14:00",
        "stops": 0,
        "fare_family": "STANDARD",
        "checkin_baggage_kg": 20,
        "total_fare": 6900.0,
    }
    norm = pipeline.normalize_batch([raw_15kg, raw_20kg])
    reconciled, _ = pipeline.engine.reconcile(norm)
    assert len(reconciled) == 2, "Different baggage tiers must remain separate canonical offers"


def test_g_incompatible_price_semantics(pipeline):
    """G. Incompatible price semantics (DISPLAYED_TOTAL + DISPLAYED_FROM) → do not average."""
    raw_total = {
        "source": "google_flights",
        "observation_id": "gf_sem_tot",
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
        "observation_id": "ixi_sem_from",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6800.0,
    }
    norm_gf = pipeline._adapter_instances["google_flights"].normalize(raw_total)
    norm_ixi = pipeline._adapter_instances["ixigo"].normalize(raw_from)
    norm_ixi.price_semantics = PriceSemantics.DISPLAYED_FROM

    reconciled, diag = pipeline.engine.reconcile([norm_gf, norm_ixi])
    assert len(reconciled) == 2, "Incompatible price semantics must NOT be averaged"
    assert all(o.match_status == MatchStatus.PRICE_CONFLICT_UNRESOLVED for o in reconciled)


def test_h_different_physical_flights(pipeline):
    """H. Different physical flights (flight number or departure time) → remain separate."""
    raw_flight1 = {
        "source": "google_flights",
        "observation_id": "gf_h1",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_flight2 = {
        "source": "google_flights",
        "observation_id": "gf_h2",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-5312",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    valid_obs, _, _ = pipeline.run([raw_flight1, raw_flight2])
    assert len(valid_obs) == 2, "Different flight numbers must produce separate canonical offers"


def test_i_same_source_dom_duplicates(pipeline):
    """I. Same-source DOM duplicates → deduplicate before source aggregation."""
    raw_gf1 = {
        "source": "google_flights",
        "observation_id": "gf_dup1",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_gf2 = {
        "source": "google_flights",
        "observation_id": "gf_dup2",
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
        "observation_id": "emt_i",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7200.0,
    }
    valid_obs, _, diag = pipeline.run([raw_gf1, raw_gf2, raw_emt])
    assert len(valid_obs) == 1, "Duplicate DOM extractions must collapse before source aggregation"
    obs = valid_obs[0]
    # (6500 + 7200) / 2 = 6850.00
    assert obs.total_fare == Decimal("6850.00")
    assert obs.source_count == 2
    assert diag.duplicates_by_source["google_flights"] >= 1


def test_j_four_otas_with_four_prices(pipeline):
    """J. Four OTAs with four prices → one canonical/APIx observation with arithmetic mean."""
    class MockOTAFourAdapter(BaseReconciliationAdapter):
        @property
        def source_id(self) -> str:
            return "makemytrip"

        @property
        def source_name(self) -> str:
            return "MakeMyTrip"

        def normalize(self, raw_record: Any):
            raw = raw_record if isinstance(raw_record, dict) else getattr(raw_record, "raw_payload", {})
            return self._build_canonical_offer(
                raw_id=raw.get("observation_id", "mmt_01"),
                origin=raw.get("origin", "DEL"),
                destination=raw.get("destination", "BOM"),
                travel_date=raw.get("travel_date", "2026-10-04"),
                airline=raw.get("airline", "IndiGo"),
                flight_number=raw.get("flight_number", "6E-204"),
                departure_time=raw.get("departure_time_local", "10:00"),
                arrival_time="12:15",
                total_fare=raw.get("total_fare", 6600.0),
                stops=0,
            )

    custom_config = SourceConfig(
        source_id="makemytrip",
        source_name="MakeMyTrip",
        supported_fields={"route", "airline", "flight_number", "departure_time", "total_fare"},
    )
    pipeline.registry.register_source(custom_config)
    pipeline.register_adapter(MockOTAFourAdapter())

    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_j",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6000.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_j",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6200.0,
    }
    raw_ixi = {
        "source": "ixigo",
        "observation_id": "ixi_j",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6400.0,
    }
    raw_mmt = {
        "source": "makemytrip",
        "observation_id": "mmt_j",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6600.0,
    }

    valid_obs, excluded, diag = pipeline.run([raw_gf, raw_emt, raw_ixi, raw_mmt])
    assert len(valid_obs) == 1, "4 OTAs with 4 prices must produce exactly 1 canonical APIx observation"
    obs = valid_obs[0]
    # (6000 + 6200 + 6400 + 6600) / 4 = 25200 / 4 = 6300.00
    assert obs.total_fare == Decimal("6300.00")
    assert obs.source_count == 4
    assert obs.aggregation_source_count == 4
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.match_status == MatchStatus.PRICE_VARIANCE_AGGREGATED


def test_k_raw_lineage_preserved(pipeline):
    """K. Verify raw lineage is preserved across all required audit dimensions."""
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_k_01",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India",
        "flight_number": "AI-805",
        "departure_time_local": "08:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_k_01",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India",
        "flight_number": "AI805",
        "departure_time_local": "08:00",
        "stops": 0,
        "fare_family": "STANDARD",
        "total_fare": 7200.0,
    }
    raw_ixi = {
        "source": "ixigo",
        "observation_id": "ixi_k_01",
        "origin": "DEL",
        "destination": "BOM",
        "travel_date": "2026-10-04",
        "airline": "Air India",
        "flight_number": "AI-805",
        "departure_time_local": "08:00",
        "stops": 0,
        "fare_family": "STANDARD",
        "total_fare": 6800.0,
    }

    valid_obs, _, _ = pipeline.run([raw_gf, raw_emt, raw_ixi])
    assert len(valid_obs) == 1
    obs = valid_obs[0]

    # Verify all lineage attributes specified in requirement §5
    assert obs.source_count == 3
    assert set(obs.source_ids) == {"google_flights", "easemytrip", "ixigo"}
    assert set(obs.source_observation_ids) == {"gf_k_01", "emt_k_01", "ixi_k_01"}
    assert obs.price_by_source == {
        "google_flights": Decimal("6500.0"),
        "easemytrip": Decimal("7200.0"),
        "ixigo": Decimal("6800.0"),
    }
    assert obs.source_prices == obs.price_by_source
    assert len(obs.source_timestamps) == 3
    assert all(k in obs.source_timestamps for k in ["google_flights", "easemytrip", "ixigo"])
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.aggregation_source_count == 3
    assert obs.total_fare == Decimal("6833.33")


# ── GOVERNANCE REGRESSION TESTS: STRATUM-AWARENESS & PRODUCT-DEFINITION GATES ──

def test_governance_a_stratum_independence_no_cross_leadtime_dedup(pipeline):
    """
    Test A: Same physical flight in T+1 and T+7 is NOT cross-deduplicated.
    Both must survive into valid APIx observations as independent sampling strata.
    """
    raw_t1 = {
        "source": "google_flights",
        "observation_id": "gf_delbom_t1",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_t7 = {
        "source": "google_flights",
        "observation_id": "gf_delbom_t7",
        "route": "DEL-BOM",
        "lead_time": "T+7",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }

    valid_obs, excluded, diag = pipeline.run([raw_t1, raw_t7])
    assert len(valid_obs) == 2, "Same flight at T+1 and T+7 must NEVER be cross-deduplicated"
    assert len(excluded) == 0
    assert sum(diag.duplicates_by_source.values()) == 0
    lead_times = {o.lead_time for o in valid_obs}
    assert lead_times == {"T+1", "T+7"}


def test_governance_b_flexiplus_excluded(pipeline):
    """
    Test B: FlexiPlus (and other higher fare families) is strictly excluded from APIx baseline.
    """
    raw_flex = {
        "source": "easemytrip",
        "observation_id": "emt_flex_01",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "fare_family": "FlexiPlus",
        "stops": 0,
        "total_fare": 8500.0,
    }
    raw_standard = {
        "source": "easemytrip",
        "observation_id": "emt_std_01",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "fare_family": "STANDARD",
        "stops": 0,
        "total_fare": 6500.0,
    }

    valid_obs, excluded, diag = pipeline.run([raw_flex, raw_standard])
    assert len(valid_obs) == 1, "Only standard saver tier enters baseline"
    assert valid_obs[0].fare_family == "STANDARD"
    assert len(excluded) == 1
    assert excluded[0].fare_family == "FlexiPlus"
    assert diag.higher_fare_family_exclusions == 1


def test_governance_c_gulf_air_excluded(pipeline):
    """
    Test C: Gulf Air domestic-looking transit is strictly excluded as cabotage violation.
    """
    raw_gulf = {
        "source": "google_flights",
        "observation_id": "gf_gulf_01",
        "route": "BLR-GOI",
        "lead_time": "T+7",
        "travel_date": "2026-10-10",
        "airline": "Gulf Air",
        "flight_number": "GF-61",
        "departure_time_local": "06:00",
        "stops": 1,
        "total_fare": 61131.0,
    }
    valid_obs, excluded, diag = pipeline.run([raw_gulf])
    assert len(valid_obs) == 0, "Gulf Air must be excluded from domestic baseline"
    assert len(excluded) == 1
    assert excluded[0].airline == "Gulf Air"
    assert diag.foreign_transit_exclusions == 1


def test_governance_d_singapore_airlines_excluded(pipeline):
    """
    Test D: Singapore Airlines domestic-looking transit is strictly excluded as cabotage violation.
    """
    raw_sia = {
        "source": "google_flights",
        "observation_id": "gf_sia_01",
        "route": "HYD-CCU",
        "lead_time": "T+15",
        "travel_date": "2026-10-18",
        "airline": "Singapore Airlines",
        "flight_number": "SQ-501",
        "departure_time_local": "23:10",
        "stops": 1,
        "total_fare": 49221.0,
    }
    valid_obs, excluded, diag = pipeline.run([raw_sia])
    assert len(valid_obs) == 0, "Singapore Airlines must be excluded from domestic baseline"
    assert len(excluded) == 1
    assert excluded[0].airline == "Singapore Airlines"
    assert diag.foreign_transit_exclusions == 1


def test_governance_e_existing_foreign_carriers_remain_excluded(pipeline):
    """
    Test E: Existing foreign carriers (Kuwait Airways, Emirates, Etihad, SriLankan, Oman Air) remain excluded.
    """
    carriers = ["Kuwait Airways", "Emirates", "Etihad", "SriLankan", "Oman Air"]
    raw_items = [
        {
            "source": "google_flights",
            "observation_id": f"gf_fc_{i}",
            "route": "DEL-BOM",
            "lead_time": "T+1",
            "travel_date": "2026-10-04",
            "airline": carrier,
            "flight_number": f"FC-{i}",
            "departure_time_local": "14:00",
            "stops": 1,
            "total_fare": 35000.0,
        }
        for i, carrier in enumerate(carriers)
    ]
    valid_obs, excluded, diag = pipeline.run(raw_items)
    assert len(valid_obs) == 0, "All international carriers must be excluded"
    assert len(excluded) == 5
    assert diag.foreign_transit_exclusions == 5


def test_governance_f_multi_source_same_product_aggregation_still_works(pipeline):
    """
    Test F: Multi-source same-product aggregation still works:
    Google ₹6,500 + EaseMyTrip ₹7,200 = one observation ₹6,850.
    """
    raw_gf = {
        "source": "google_flights",
        "observation_id": "gf_f",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6500.0,
    }
    raw_emt = {
        "source": "easemytrip",
        "observation_id": "emt_f",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7200.0,
    }
    valid_obs, _, diag = pipeline.run([raw_gf, raw_emt])
    assert len(valid_obs) == 1, "Two sources for same product in same cell must collapse to 1 observation"
    obs = valid_obs[0]
    # (6500 + 7200) / 2 = 6850.00
    assert obs.total_fare == Decimal("6850.00")
    assert obs.source_count == 2
    assert obs.aggregation_method == "ARITHMETIC_MEAN"
    assert obs.match_status == MatchStatus.PRICE_VARIANCE_AGGREGATED


def test_governance_g_different_lead_time_cells_remain_independent(pipeline):
    """
    Test G: Different lead-time cells remain independent:
    DEL-BOM T+1 (GF ₹6000 + EMT ₹6200 -> ₹6100) and
    DEL-BOM T+7 (GF ₹7000 + EMT ₹7400 -> ₹7200)
    produce 2 distinct observations, one in each cell.
    """
    raw_t1_gf = {
        "source": "google_flights",
        "observation_id": "gf_t1",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6000.0,
    }
    raw_t1_emt = {
        "source": "easemytrip",
        "observation_id": "emt_t1",
        "route": "DEL-BOM",
        "lead_time": "T+1",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 6200.0,
    }
    raw_t7_gf = {
        "source": "google_flights",
        "observation_id": "gf_t7",
        "route": "DEL-BOM",
        "lead_time": "T+7",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7000.0,
    }
    raw_t7_emt = {
        "source": "easemytrip",
        "observation_id": "emt_t7",
        "route": "DEL-BOM",
        "lead_time": "T+7",
        "travel_date": "2026-10-04",
        "airline": "IndiGo",
        "flight_number": "6E-204",
        "departure_time_local": "10:00",
        "stops": 0,
        "total_fare": 7400.0,
    }

    valid_obs, _, diag = pipeline.run([raw_t1_gf, raw_t1_emt, raw_t7_gf, raw_t7_emt])
    assert len(valid_obs) == 2, "Must produce exactly 2 observations, one for T+1 and one for T+7"
    by_lt = {o.lead_time: o for o in valid_obs}
    assert "T+1" in by_lt and "T+7" in by_lt

    # T+1: (6000 + 6200) / 2 = 6100.00
    assert by_lt["T+1"].total_fare == Decimal("6100.00")
    assert by_lt["T+1"].source_count == 2

    # T+7: (7000 + 7400) / 2 = 7200.00
    assert by_lt["T+7"].total_fare == Decimal("7200.00")
    assert by_lt["T+7"].source_count == 2

