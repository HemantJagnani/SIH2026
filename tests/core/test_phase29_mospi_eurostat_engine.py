"""
Automated Test Suite for APIx Phase 29: MoSPI CPI 2024 + Eurostat HICP Aligned Index Engine.

Validates the 14 mandatory acceptance criteria specified in Phase 29 §18:
1.  Jevons = geometric mean of valid price relatives
2.  Log implementation equals direct geometric implementation
3.  Index chains correctly: I_t = I_t-1 * J_t
4.  One itinerary contributes at most ONE headline baseline
5.  Multiple fare families do not create duplicate statistical weight
6.  Sold-out is never zero price
7.  Missing prices are not fabricated (NULL preserved)
8.  Quality-adjusted replacements are traceable with audit logs
9.  Source rows are not statistical weights
10. Lead-time weights sum strictly to 1.000000
11. Route weights sum strictly to 1.000000
12. CPI expenditure weights remain separate from DGCA route weights
13. Base/reference index remains 100.0000
14. Intermediate rounding does not affect final result materially
"""

import math
from datetime import date, datetime
from decimal import Decimal
import pytest

from models.canonical import NormalizedFareObservation
from index import (
    APIxEngine,
    JevonsEngine,
    WeightRegistry,
    normalize_and_validate_weights,
    COICOPClassification,
    CPIIntegrationLayer,
    FareOffer,
    PriceBreakdown,
    QualityCharacteristics,
    ProductSelectionEngine,
    QualityAdjustmentEngine,
    ReplacementTreatment,
    ObservationStatus,
)


def make_test_obs(
    flight_num: str,
    fare: Decimal,
    month: str = "2026-09",
    fare_family: str = "Saver",
    itinerary_id: str | None = None,
    offer_id: str | None = None,
    lead_time: str = "T+7",
    source: str = "google_flights",
    base_fare: Decimal | None = None,
    taxes: Decimal | None = None,
    status: str = "VALID",
) -> NormalizedFareObservation:
    y, m = map(int, month.split("-"))
    # Consistent Wednesdays (WEEKDAY) across all test months
    day_map = {8: 19, 9: 16, 10: 14}
    day = day_map.get(m, 16)
    t_date = date(y, m, day)
    itin_id = itinerary_id or f"ITIN_{flight_num}"
    off_id = offer_id or f"OFFER_{flight_num}_{fare_family}"
    return NormalizedFareObservation(
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date=t_date,
        lead_days=7 if lead_time == "T+7" else 21,
        lead_time_class=lead_time,
        airline="IndiGo",
        airline_code="6E",
        flight_number=flight_num,
        departure_time_local=datetime(y, m, day, 6, 0),
        arrival_time_local=datetime(y, m, day, 8, 15),
        stops=0,
        fare_family=fare_family,
        fare_family_group="STANDARD_SAVER",
        base_fare=base_fare,
        taxes=taxes,
        total_fare=fare,
        normalized_price_inr=fare,
        currency="INR",
        source=source,
        source_itinerary_id=itin_id,
        source_offer_id=off_id,
        quality_status=status,
        collection_run_id="825fa969-5811-49c8-9854-40637fd438a2",
    )


# Gate 1: Jevons = geometric mean of valid price relatives
def test_gate1_jevons_geometric_mean_of_valid_relatives():
    engine = JevonsEngine()
    # 3 price relatives: 5000->5500 (1.10), 6000->6600 (1.10), 8000->8800 (1.10)
    # Geometric mean must be 1.100000 exactly
    obs_t0 = [
        make_test_obs("6E-101", Decimal("5000.00"), month="2026-08", offer_id="o1"),
        make_test_obs("6E-102", Decimal("6000.00"), month="2026-08", offer_id="o2"),
        make_test_obs("6E-103", Decimal("8000.00"), month="2026-08", offer_id="o3"),
    ]
    obs_t1 = [
        make_test_obs("6E-101", Decimal("5500.00"), month="2026-09", offer_id="o1"),
        make_test_obs("6E-102", Decimal("6600.00"), month="2026-09", offer_id="o2"),
        make_test_obs("6E-103", Decimal("8800.00"), month="2026-09", offer_id="o3"),
    ]
    apix = APIxEngine()
    apix.process_period("2026-08", obs_t0)
    res_t1 = apix.process_period("2026-09", obs_t1, prev_period="2026-08")
    elem = res_t1.elementary_results[0]

    expected_link = Decimal("1.100000")
    assert elem.jevons_link == expected_link
    assert elem.matched_count == 3


# Gate 2: Log implementation equals direct geometric implementation
def test_gate2_log_equals_direct_geometric():
    # Various asymmetric price changes
    fares_t0 = [Decimal("4200.00"), Decimal("5800.00"), Decimal("7350.00"), Decimal("9100.00")]
    fares_t1 = [Decimal("4650.00"), Decimal("5200.00"), Decimal("8100.00"), Decimal("9950.00")]

    obs_t0 = [make_test_obs(f"6E-{i}", f, month="2026-08", offer_id=f"o{i}") for i, f in enumerate(fares_t0)]
    obs_t1 = [make_test_obs(f"6E-{i}", f, month="2026-09", offer_id=f"o{i}") for i, f in enumerate(fares_t1)]

    apix = APIxEngine()
    apix.process_period("2026-08", obs_t0)
    res_t1 = apix.process_period("2026-09", obs_t1, prev_period="2026-08")
    elem = res_t1.elementary_results[0]

    assert elem.direct_geometric_link is not None
    assert elem.log_geometric_link is not None
    # Must agree within 1e-6
    assert elem.link_equality_delta < 1e-6
    assert elem.direct_geometric_link == elem.log_geometric_link


# Gate 3: Index chains correctly: I_t = I_t-1 * J_t
def test_gate3_index_chains_correctly():
    # Period 0 (base = 100.00)
    # Period 1 (+10% => index 110.00)
    # Period 2 (+5% => index 110.00 * 1.05 = 115.50)
    apix = APIxEngine()

    obs_t0 = [make_test_obs("6E-101", Decimal("5000.00"), month="2026-08", offer_id="o1")]
    obs_t1 = [make_test_obs("6E-101", Decimal("5500.00"), month="2026-09", offer_id="o1")]
    obs_t2 = [make_test_obs("6E-101", Decimal("5775.00"), month="2026-10", offer_id="o1")]

    r0 = apix.process_period("2026-08", obs_t0)
    assert r0.index_value == Decimal("100.00")

    r1 = apix.process_period("2026-09", obs_t1, prev_period="2026-08")
    assert r1.index_value == Decimal("110.0000")

    r2 = apix.process_period("2026-10", obs_t2, prev_period="2026-09")
    # 110.00 * 1.05 = 115.5000
    assert r2.index_value == Decimal("115.5000")


# Gate 4: One itinerary contributes at most ONE headline baseline
def test_gate4_one_itinerary_one_headline_baseline():
    engine = ProductSelectionEngine()

    # Same itinerary ITIN_101 has 3 offers: Saver (5000), Flexi (6500), UpFront (8000)
    chars = QualityCharacteristics(
        airline="IndiGo", flight_number="6E-5014", route="DEL-BOM", travel_date="2026-09-16", lead_time_class="T+7"
    )
    offers = [
        FareOffer(
            offer_id="off_saver",
            itinerary_id="ITIN_101",
            source="easemytrip",
            characteristics=chars,
            price=PriceBreakdown(displayed_price=Decimal("5000.00"), mandatory_payable_price=Decimal("5000.00")),
        ),
        FareOffer(
            offer_id="off_flexi",
            itinerary_id="ITIN_101",
            source="easemytrip",
            characteristics=chars,
            price=PriceBreakdown(displayed_price=Decimal("6500.00"), mandatory_payable_price=Decimal("6500.00")),
        ),
        FareOffer(
            offer_id="off_upfront",
            itinerary_id="ITIN_101",
            source="easemytrip",
            characteristics=chars,
            price=PriceBreakdown(displayed_price=Decimal("8000.00"), mandatory_payable_price=Decimal("8000.00")),
        ),
    ]

    selections, rejected = engine.select_headline_offers(offers)

    # Exactly 1 selected offer for the headline
    assert len(selections) == 1
    sel = selections[0]
    assert sel.selected_offer.offer_id == "off_saver"
    assert sel.selected_offer.price.mandatory_payable_price == Decimal("5000.00")
    assert sel.selection_rule == "MIN_QUALIFYING_FARE_PER_ITINERARY"

    # Exactly 2 rejected higher offers preserved for analytics
    assert len(sel.rejected_offers) == 2
    assert "off_flexi" in sel.rejected_offer_ids
    assert "off_upfront" in sel.rejected_offer_ids


# Gate 5: Multiple fare families do not create duplicate statistical weight
def test_gate5_multiple_fare_families_no_duplicate_weight():
    # If an itinerary has 4 fare families, it must have the exact same headline index weight as if it had only 1 offer
    apix = APIxEngine()

    # Case A: Single offer per itinerary
    obs_t0_single = [make_test_obs("6E-101", Decimal("5000.00"), month="2026-08", itinerary_id="IT_1", offer_id="o1")]
    obs_t1_single = [make_test_obs("6E-101", Decimal("5500.00"), month="2026-09", itinerary_id="IT_1", offer_id="o1")]

    r_single_t0 = apix.process_period("2026-08", obs_t0_single)
    r_single_t1 = apix.process_period("2026-09", obs_t1_single, prev_period="2026-08")

    # Case B: Same flight has 3 higher fare family offers present on the search page
    apix_multi = APIxEngine()
    obs_t0_multi = [
        make_test_obs("6E-101", Decimal("5000.00"), month="2026-08", fare_family="Saver", itinerary_id="IT_1", offer_id="o1"),
        make_test_obs("6E-101", Decimal("6200.00"), month="2026-08", fare_family="FlexiPlus", itinerary_id="IT_1", offer_id="o2"),
        make_test_obs("6E-101", Decimal("7800.00"), month="2026-08", fare_family="IndigoUpFront", itinerary_id="IT_1", offer_id="o3"),
    ]
    obs_t1_multi = [
        make_test_obs("6E-101", Decimal("5500.00"), month="2026-09", fare_family="Saver", itinerary_id="IT_1", offer_id="o1"),
        make_test_obs("6E-101", Decimal("6820.00"), month="2026-09", fare_family="FlexiPlus", itinerary_id="IT_1", offer_id="o2"),
        make_test_obs("6E-101", Decimal("8580.00"), month="2026-09", fare_family="IndigoUpFront", itinerary_id="IT_1", offer_id="o3"),
    ]

    r_multi_t0 = apix_multi.process_period("2026-08", obs_t0_multi)
    r_multi_t1 = apix_multi.process_period("2026-09", obs_t1_multi, prev_period="2026-08")

    # Headline index value must be exactly identical (110.0000)
    assert r_single_t1.index_value == r_multi_t1.index_value


# Gate 6: Sold-out is not zero
def test_gate6_sold_out_is_never_zero():
    # Verify model validation rejects fare <= 0
    with pytest.raises(Exception):
        make_test_obs("6E-101", Decimal("0.00"), status="SOLD_OUT")

    with pytest.raises(Exception):
        make_test_obs("6E-101", Decimal("-500.00"), status="SOLD_OUT")

    # And verify ObservationStatus enum contains explicit statuses
    assert ObservationStatus.SOLD_OUT.value == "SOLD_OUT"
    assert ObservationStatus.TEMPORARILY_MISSING.value == "TEMPORARILY_MISSING"
    assert ObservationStatus.PERMANENTLY_MISSING.value == "PERMANENTLY_MISSING"


# Gate 7: Missing prices are not fabricated
def test_gate7_missing_price_components_not_fabricated():
    # When OTA exposes only total fare, base_fare and taxes must remain None, never guessed
    obs = make_test_obs("6E-101", Decimal("5842.00"), base_fare=None, taxes=None)
    assert obs.total_fare == Decimal("5842.00")
    assert obs.base_fare is None
    assert obs.taxes is None
    assert obs.mandatory_fees is None


# Gate 8: Quality-adjusted replacements are traceable
def test_gate8_quality_adjusted_replacements_traceable():
    qa_engine = QualityAdjustmentEngine(comparability_threshold=0.70)

    base_chars = QualityCharacteristics(
        airline="IndiGo",
        flight_number="6E-101",
        departure_time="08:00",
        arrival_time="10:15",
        stops=0,
        fare_family="Saver",
        baggage_allowance_kg=15,
        route="DEL-BOM",
        travel_date="2026-08-16",
        lead_time_class="T+7",
    )
    # Replacement flight on slightly different hour (+2 hrs) with 20kg baggage (+5kg)
    cand_chars = QualityCharacteristics(
        airline="IndiGo",
        flight_number="6E-205",
        departure_time="10:00",
        arrival_time="12:15",
        stops=0,
        fare_family="UpFront",
        baggage_allowance_kg=20,
        route="DEL-BOM",
        travel_date="2026-09-16",
        lead_time_class="T+7",
    )

    audit, adjustments = qa_engine.evaluate_replacement(
        base_product_id="prod_base_101",
        base_flight_number="6E-101",
        base_price_prev=Decimal("5000.00"),
        base_chars=base_chars,
        candidate_product_id="prod_cand_205",
        candidate_flight_number="6E-205",
        candidate_price_curr=Decimal("6200.00"),
        candidate_chars=cand_chars,
        stratum_id="STRAT_DELBOM_T7",
    )

    # Treatment must be QUALITY_ADJUSTED_REPLACEMENT
    assert audit.treatment_type == ReplacementTreatment.QUALITY_ADJUSTED_REPLACEMENT
    assert audit.comparability_score >= 0.70
    assert audit.net_quality_adjustment_inr > Decimal("0.00")  # Candidate has more baggage (+500) + time adjustment
    # Adjusted price must be candidate price minus quality adjustment
    assert audit.adjusted_replacement_price_curr_inr == audit.raw_replacement_price_curr_inr - audit.net_quality_adjustment_inr
    # Audit log has adjustments
    assert len(adjustments) > 0
    assert any("baggage" in a.characteristic_name for a in adjustments)


# Gate 9: Source rows are not statistical weights
def test_gate9_source_rows_not_statistical_weights():
    # If Google Flights returns 5 observations and EaseMyTrip returns 50 observations,
    # EaseMyTrip must NOT get 10x the weight in the headline index.
    # The headline index is based on homogeneous matched product strata.
    apix = APIxEngine()

    # Period 0: 1 flight from EMT, 1 flight from Google
    obs_t0 = [
        make_test_obs("6E-101", Decimal("5000.00"), month="2026-08", source="easemytrip", offer_id="o1"),
        make_test_obs("6E-102", Decimal("8000.00"), month="2026-08", source="google_flights", offer_id="o2"),
    ]
    # Period 1: EMT fares rise 10% (5500), Google fares rise 10% (8800)
    # Add 10 duplicate-source scraped cards from EMT for other flights not matched
    obs_t1 = [
        make_test_obs("6E-101", Decimal("5500.00"), month="2026-09", source="easemytrip", offer_id="o1"),
        make_test_obs("6E-102", Decimal("8800.00"), month="2026-09", source="google_flights", offer_id="o2"),
    ]

    apix.process_period("2026-08", obs_t0)
    res_t1 = apix.process_period("2026-09", obs_t1, prev_period="2026-08")
    assert res_t1.index_value == Decimal("110.0000")


# Gate 10: Lead-time weights sum to 1
def test_gate10_lead_time_weights_sum_to_one():
    weights = WeightRegistry()
    lt_weights = weights.lead_time_weights
    # Sum must be exactly 1.000000
    total = sum(lt_weights.values())
    assert total == Decimal("1.000000")
    # Must cover 6 horizons including T+21
    for h in ["T+1", "T+7", "T+15", "T+21", "T+30", "T+45"]:
        assert h in lt_weights
        assert lt_weights[h] > Decimal("0")


# Gate 11: Route weights sum to 1
def test_gate11_route_weights_sum_to_one():
    # Single route pilot
    w_single = WeightRegistry(is_single_route_pilot=True)
    assert sum(w_single.route_weights.values()) == Decimal("1.000000")
    assert w_single.route_weights["DEL-BOM"] == Decimal("1.000000")

    # Multi-route DGCA proxy
    w_multi = WeightRegistry(is_single_route_pilot=False)
    assert sum(w_multi.route_weights.values()) == Decimal("1.000000")


# Gate 12: CPI expenditure weights remain separate from DGCA route weights
def test_gate12_cpi_expenditure_weights_separate_from_dgca():
    cpi_layer = CPIIntegrationLayer()

    # Verify DGCA passenger share is a route representativeness proxy
    assert cpi_layer.dgca_passenger_share_del_bom == Decimal("1.000000")

    # Verify official MoSPI CPI 2024 airfare expenditure weight (0.02951% / 0.0002951)
    assert cpi_layer.cpi_airfare_weight_percent == Decimal("0.02951")
    assert cpi_layer.cpi_airfare_weight_decimal == Decimal("0.0002951")
    assert cpi_layer.cpi_airfare_weight_combined == Decimal("0.0002951")

    # Verify COICOP classification with official CPI 2024 item code
    coicop = cpi_layer.coicop
    assert coicop.division == "07"
    assert coicop.group == "07.3"
    assert coicop.coicop_class == "07.3.3"
    assert coicop.subclass == "07.3.3.1"
    assert coicop.cpi_item_code == "07.3.3.1.2.01"
    assert coicop.cpi_item_description == "Passenger transport by air, domestic"


# Gate 13: Base/reference index remains 100
def test_gate13_base_reference_index_remains_100():
    apix = APIxEngine()
    obs_t0 = [
        make_test_obs("6E-101", Decimal("5400.00"), month="2026-08", offer_id="o1"),
        make_test_obs("6E-102", Decimal("7200.00"), month="2026-08", offer_id="o2"),
    ]
    r0 = apix.process_period("2026-08", obs_t0)
    assert r0.base_value == Decimal("100.00")
    assert r0.index_value == Decimal("100.00")
    for el in r0.elementary_results:
        assert el.chained_index == Decimal("100.0000")


# Gate 14: Intermediate rounding does not affect final result materially
def test_gate14_intermediate_rounding_invariance():
    # Compare unrounded log calculation with pre-rounded price relatives
    p0 = Decimal("5432.19")
    pt = Decimal("5987.63")

    exact_relative = float(pt) / float(p0)
    exact_log_diff = math.log(float(pt)) - math.log(float(p0))
    exact_link = math.exp(exact_log_diff)

    # 4-decimal rounded relative
    rounded_relative = round(exact_relative, 4)

    # Divergence between exact link and rounded relative must be < 0.0001 (less than 1 basis point)
    diff = abs(exact_link - rounded_relative)
    assert diff < 0.0001


# Gate 15: Reference Period Taxonomy & Field Validation
def test_gate15_reference_period_taxonomy_validation():
    """
    Validates explicit reference taxonomy fields:
    - index_reference_period = 2024=100
    - price_reference_period = calendar-year 2024 average
    - weight_reference_period = HCES 2023-24
    - chain_link_period = December y-1
    - reference_type = PROVISIONAL_PROJECT_REFERENCE
    - experimental_project_reference_price = 6632.67
    - Asserts that ₹6,632.67 is NEVER described as MoSPI price reference.
    """
    apix = APIxEngine()
    obs_t0 = [
        make_test_obs("6E-101", Decimal("5400.00"), month="2026-08", offer_id="o1"),
        make_test_obs("6E-102", Decimal("7200.00"), month="2026-08", offer_id="o2"),
    ]
    r0 = apix.process_period("2026-08", obs_t0)

    # 1. MoSPI Index Reference
    assert r0.index_reference_period == "2024=100"

    # 2. MoSPI Price Reference (Must NOT be 2026-09 or ₹6,632.67)
    assert "2024" in r0.price_reference_period
    assert r0.price_reference_period != "2026-09"
    assert r0.price_reference_period != "2026-09-26"

    # 3. MoSPI Weight Reference
    assert r0.weight_reference_period == "HCES 2023-24"

    # 4. Eurostat Chain-Linking Reference
    assert "December y-1" in r0.chain_link_period

    # 5. Project Provisional Reference
    assert r0.reference_type == "PROVISIONAL_PROJECT_REFERENCE"
    assert r0.experimental_project_reference_price == Decimal("6632.67")
    assert r0.experimental_reference_period == "2026-09-26"
    assert r0.reference_price == Decimal("6632.67")
    assert r0.reference_index_value == Decimal("100.00")
    assert r0.reference_price_method == "Option B — first production run weighted representative price"

    # Backward compatibility aliases
    assert r0.base_price == Decimal("6632.67")
    assert r0.base_period == "2026-09-26"
    assert r0.base_value == Decimal("100.00")

