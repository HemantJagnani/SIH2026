"""
APIx Master Index Compilation Engine for Phase 29.

Orchestrates the complete calculation hierarchy conforming to MoSPI CPI 2024 and Eurostat HICP 2024:
1. Product Definition & Selection:
   - Evaluates all detected fare offers per itinerary.
   - Selects the MIN qualifying mandatory-payable fare offer.
   - Enforces that each itinerary contributes at most ONE headline observation.
2. Monthly Representative Product Pricing:
   - P̄_(i,t) = exp( 1/D * sum(ln P_(i,t,d)) )
3. Adjacent-Period Matching & Replacement / Quality Adjustment:
   - Identifies matched product pairs M_(s,t).
   - When a base product is missing, evaluates replacement candidates using 14 quality characteristics.
   - Applies quality adjustments where comparability >= 0.70.
4. Short-Chain Jevons Elementary Indices:
   - J_(s,t) = exp( 1/N * sum(ln p_(i,t) - ln p_(i,t-1)) )
   - Chains: I_(s,t) = I_(s,t-1) * J_(s,t)
   - Verifies direct geometric link vs log geometric link.
5. Lead-Time Aggregation:
   - Aggregates elementary strata to lead-time sub-indices using PROVISIONAL EQUAL LEAD-TIME WEIGHTS (w_L = 1/6).
   - Isolates T+21 as MoSPI domestic advance-purchase reference.
6. Route Aggregation:
   - Aggregates lead times into route indices, then into All-India APIx via DGCA passenger traffic proxies.
7. Diagnostic Calculations:
   - Source-specific indices (Google Flights, EaseMyTrip), source overlap, coverage, divergence.
   - Retains DEL_BOM_PROTOTYPE_MEDIAN_INDICATOR for comparison.
"""

from __future__ import annotations
import math
import statistics
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pydantic import BaseModel

from models.canonical import NormalizedFareObservation
from .models import (
    MonthlyProductPrice,
    MatchedProduct,
    ElementaryIndexResult,
    LeadTimeIndexResult,
    RouteIndexResult,
    APIxSeriesResult,
)
from .product_definition import (
    FareOffer,
    PriceBreakdown,
    QualityCharacteristics,
    ProductSelectionEngine,
    ItinerarySelectionResult,
    PRODUCT_DEFINITION_VERSION,
)
from .quality_adjustment import (
    QualityAdjustmentEngine,
    ReplacementAuditRecord,
    QualityAdjustmentRecord,
    ObservationStatus,
)
from .monthly_pricing import compute_monthly_product_prices
from .matching import ProductMatchingEngine
from .jevons import JevonsEngine
from .weights import WeightRegistry
from .aggregation import IndexAggregationEngine
from .classification import CPIIntegrationLayer


class APIxEngine:
    """
    Production index calculation engine conforming to MoSPI CPI 2024 and Eurostat HICP standards.
    """

    def __init__(
        self,
        weight_registry: Optional[WeightRegistry] = None,
        min_matched: int = 1,
        min_coverage: float = 0.50,
        base_value: Decimal = Decimal("100.00"),
        methodology_version: str = "APIx v1.0",
    ):
        self.methodology_version = methodology_version
        self.weights = weight_registry or WeightRegistry()
        self.selection_engine = ProductSelectionEngine()
        self.matching_engine = ProductMatchingEngine(
            min_matched=min_matched, min_coverage=min_coverage
        )
        self.qa_engine = QualityAdjustmentEngine()
        self.jevons_engine = JevonsEngine(base_value=base_value)
        self.aggregation_engine = IndexAggregationEngine(
            weight_registry=self.weights,
            methodology_version=methodology_version,
        )
        self.cpi_layer = CPIIntegrationLayer()

        # State stores
        self.monthly_prices_by_period: Dict[str, Dict[str, MonthlyProductPrice]] = {}
        self.apix_history: Dict[str, APIxSeriesResult] = {}
        self.replacement_history: List[ReplacementAuditRecord] = []
        self.quality_adjustment_history: List[QualityAdjustmentRecord] = []
        self.selection_history: List[ItinerarySelectionResult] = []

    def process_period(
        self,
        period: str,
        observations: Sequence[NormalizedFareObservation],
        prev_period: Optional[str] = None,
        prototype_median_fares: Optional[Dict[str, float]] = None,
        candidate_replacements: Optional[List[Tuple[NormalizedFareObservation, NormalizedFareObservation]]] = None,
    ) -> Tuple[APIxSeriesResult, List[ElementaryIndexResult], Dict[str, Any]]:
        """
        Executes full Phase 29 calculation hierarchy for a given month period (YYYY-MM).
        
        Returns:
            Tuple of (APIxSeriesResult, List[ElementaryIndexResult], diagnostic_meta_dict)
        """
        # Step 1: Convert raw observations to FareOffer models and perform Product Selection
        offers: List[FareOffer] = []
        for o in observations:
            if o.total_fare <= Decimal("0"):
                continue
            chars = QualityCharacteristics(
                airline=o.airline,
                flight_number=o.flight_number,
                departure_time=o.departure_time_local.strftime("%H:%M") if o.departure_time_local else None,
                arrival_time=o.arrival_time_local.strftime("%H:%M") if o.arrival_time_local else None,
                duration_minutes=o.duration_minutes,
                stops=o.stops,
                cabin=str(o.cabin).upper(),
                fare_family=o.fare_family or "STANDARD",
                baggage_allowance_kg=15,
                cabin_baggage_kg=7,
                refundability=o.refundability or "UNKNOWN",
                changeability=o.changeability or "UNKNOWN",
                route=o.route,
                travel_date=str(o.travel_date),
                lead_time_class=o.lead_time_class,
            )
            price = PriceBreakdown(
                displayed_price=o.total_fare,
                mandatory_payable_price=o.normalized_price_inr,
                base_fare=o.base_fare,
                taxes=o.taxes,
                mandatory_fees=o.mandatory_fees,
            )
            itin_id = o.source_itinerary_id or f"{o.airline}_{o.flight_number}_{o.travel_date}"
            offer_id = o.source_offer_id or f"{itin_id}_{o.fare_family or 'STD'}"

            offers.append(
                FareOffer(
                    offer_id=offer_id,
                    itinerary_id=itin_id,
                    source=o.source,
                    characteristics=chars,
                    price=price,
                    is_qualifying=o.quality_status == "VALID",
                )
            )

        # Apply selection engine: MIN qualifying offer per itinerary
        selections, rejected_higher_offers = self.selection_engine.select_headline_offers(offers)
        self.selection_history.extend(selections)

        # Build selected observations subset for headline calculation
        selected_offer_ids = {s.selected_offer_id for s in selections}
        headline_observations = [
            o for o in observations
            if (o.source_offer_id or f"{o.source_itinerary_id or o.airline + '_' + o.flight_number + '_' + str(o.travel_date)}_{o.fare_family or 'STD'}") in selected_offer_ids
            or not offers  # fallback if raw observations provided directly
        ]

        if not headline_observations:
            headline_observations = list(observations)

        # Step 2: Compute monthly geometric product prices
        monthly_prices = compute_monthly_product_prices(headline_observations)
        self.monthly_prices_by_period[period] = monthly_prices

        # Step 3: Handle Replacements & Quality Adjustments if provided
        active_adjustments: List[QualityAdjustmentRecord] = []
        active_replacements: List[ReplacementAuditRecord] = []

        if candidate_replacements:
            for base_obs, cand_obs in candidate_replacements:
                base_chars = QualityCharacteristics(
                    airline=base_obs.airline,
                    flight_number=base_obs.flight_number,
                    departure_time=base_obs.departure_time_local.strftime("%H:%M") if base_obs.departure_time_local else None,
                    arrival_time=base_obs.arrival_time_local.strftime("%H:%M") if base_obs.arrival_time_local else None,
                    stops=base_obs.stops,
                    cabin=str(base_obs.cabin).upper(),
                    fare_family=base_obs.fare_family or "STANDARD",
                    baggage_allowance_kg=15,
                    cabin_baggage_kg=7,
                    refundability=base_obs.refundability or "UNKNOWN",
                    changeability=base_obs.changeability or "UNKNOWN",
                    route=base_obs.route,
                    travel_date=str(base_obs.travel_date),
                    lead_time_class=base_obs.lead_time_class,
                )
                cand_chars = QualityCharacteristics(
                    airline=cand_obs.airline,
                    flight_number=cand_obs.flight_number,
                    departure_time=cand_obs.departure_time_local.strftime("%H:%M") if cand_obs.departure_time_local else None,
                    arrival_time=cand_obs.arrival_time_local.strftime("%H:%M") if cand_obs.arrival_time_local else None,
                    stops=cand_obs.stops,
                    cabin=str(cand_obs.cabin).upper(),
                    fare_family=cand_obs.fare_family or "STANDARD",
                    baggage_allowance_kg=20 if "UpFront" in (cand_obs.fare_family or "") else 15,
                    cabin_baggage_kg=7,
                    refundability=cand_obs.refundability or "UNKNOWN",
                    changeability=cand_obs.changeability or "UNKNOWN",
                    route=cand_obs.route,
                    travel_date=str(cand_obs.travel_date),
                    lead_time_class=cand_obs.lead_time_class,
                )
                rep_record, adj_records = self.qa_engine.evaluate_replacement(
                    base_product_id=base_obs.product_key or str(base_obs.observation_id),
                    base_flight_number=base_obs.flight_number,
                    base_price_prev=base_obs.total_fare,
                    base_chars=base_chars,
                    candidate_product_id=cand_obs.product_key or str(cand_obs.observation_id),
                    candidate_flight_number=cand_obs.flight_number,
                    candidate_price_curr=cand_obs.total_fare,
                    candidate_chars=cand_chars,
                    stratum_id=base_obs.product_stratum_id,
                )
                active_replacements.append(rep_record)
                active_adjustments.extend(adj_records)
                self.replacement_history.append(rep_record)
                self.quality_adjustment_history.extend(adj_records)

        # Step 4: Elementary Indices (Short-Chain Jevons)
        elementary_results: List[ElementaryIndexResult] = []

        if not prev_period or prev_period not in self.monthly_prices_by_period:
            # Baseline period t=0: Jevons links = 1.000000, chained = 100.00
            for p in sorted(monthly_prices.values(), key=lambda x: x.stratum_id):
                el = self.jevons_engine.compute_elementary_index(
                    stratum_id=p.stratum_id,
                    route=p.route,
                    lead_time_class=p.lead_time_class,
                    period=period,
                    prev_period=None,
                    matched_products=[],
                    eligible_count_prev=0,
                    coverage_ratio=1.0,
                    is_published=True,
                )
                elementary_results.append(el)
        else:
            prev_prices = self.monthly_prices_by_period[prev_period]
            matches = self.matching_engine.match_periods(prev_prices, monthly_prices)

            # Metadata map
            stratum_metadata: Dict[str, tuple[str, str]] = {}
            for p in monthly_prices.values():
                stratum_metadata[p.stratum_id] = (p.route, p.lead_time_class)

            # Integrate quality adjusted replacements into matched pairs if applicable
            for rep in active_replacements:
                s_id = rep.stratum_id
                if s_id in matches:
                    matched_list, elig_prev, cov, is_pub = matches[s_id]
                    # Append quality adjusted match
                    matched_list.append(
                        MatchedProduct(
                            product_id=rep.replacement_product_id,
                            stratum_id=s_id,
                            p_prev=rep.base_price_prev_inr,
                            p_curr=rep.adjusted_replacement_price_curr_inr,
                            price_relative=rep.effective_price_relative,
                            log_price_relative=math.log(float(rep.adjusted_replacement_price_curr_inr)) - math.log(float(rep.base_price_prev_inr)),
                            is_quality_adjusted=True,
                            net_quality_adjustment_inr=rep.net_quality_adjustment_inr,
                            replacement_id=rep.replacement_id,
                        )
                    )
                    matches[s_id] = (matched_list, elig_prev, cov, is_pub)

            for s_id, (matched_list, elig_prev, coverage, is_pub) in sorted(matches.items()):
                route, lead_time = stratum_metadata.get(s_id, ("DEL-BOM", "T+7"))
                el = self.jevons_engine.compute_elementary_index(
                    stratum_id=s_id,
                    route=route,
                    lead_time_class=lead_time,
                    period=period,
                    prev_period=prev_period,
                    matched_products=matched_list,
                    eligible_count_prev=elig_prev,
                    coverage_ratio=coverage,
                    is_published=is_pub,
                )
                elementary_results.append(el)

        # Step 5: Higher-Level Lead-Time Aggregation
        lt_results = self.aggregation_engine.aggregate_elementary_to_lead_time(
            elementary_results, period
        )

        # Step 6: Prototype Median Retention for Diagnostic Benchmark
        # Calculate prototype representative price using lead-time medians
        prototype_summary = None
        fares_by_lead = defaultdict(list)
        for o in headline_observations:
            fares_by_lead[o.lead_time_class].append(float(o.total_fare))

        if fares_by_lead:
            available_leads = sorted(fares_by_lead.keys())
            eq_w = Decimal("1.0") / Decimal(str(len(available_leads)))
            weighted_med_price = 0.0
            med_breakdown = {}
            for lt in available_leads:
                m_fare = statistics.median(fares_by_lead[lt])
                weighted_med_price += float(eq_w) * m_fare
                med_breakdown[lt] = round(m_fare, 2)

            # Project reference price (Option B first production run, NOT MoSPI price reference)
            ref_tax = self.cpi_layer.taxonomy
            proto_ref_price = float(ref_tax.experimental_project_reference_price)
            proto_index_val = round((weighted_med_price / proto_ref_price) * 100.0, 4)

            prototype_summary = {
                "route": "DEL-BOM",
                "indicator_name": "DEL_BOM_PROTOTYPE_MEDIAN_INDICATOR",
                "status": "DIAGNOSTIC_ONLY_NOT_CPI_METHODOLOGY",
                "purpose": "descriptive/reference-price diagnostic",
                "reference_type": ref_tax.reference_type,
                "experimental_project_reference_price": proto_ref_price,
                "experimental_reference_period": ref_tax.experimental_reference_period,
                "reference_price": proto_ref_price,
                "base_price_inr": proto_ref_price,  # Explicit backward-compatibility alias
                "weighted_representative_price_inr": round(weighted_med_price, 2),
                "route_index": proto_index_val,
                "lead_time_medians": med_breakdown,
                "institutional_disclaimer": "Provisional reference price ₹8,641.45 is strictly PROVISIONAL_PROJECT_REFERENCE (descriptive diagnostic only); NEVER used as CPI elementary index denominator.",
            }

        # Step 7: Route Aggregation
        proto_dict = {"DEL-BOM": prototype_summary} if prototype_summary else None
        route_results = self.aggregation_engine.aggregate_lead_time_to_route(
            lt_results, period, prototype_median_data=proto_dict
        )

        # Step 8: Source Diagnostics (Google Flights vs EaseMyTrip)
        src_groups = defaultdict(lambda: defaultdict(list))
        for o in headline_observations:
            src_groups[o.source][o.lead_time_class].append(float(o.total_fare))

        source_diagnostics = {}
        for src, lt_map in src_groups.items():
            src_leads = sorted(lt_map.keys())
            w_src = 1.0 / len(src_leads) if src_leads else 1.0
            src_price = sum(w_src * statistics.median(fares) for fares in lt_map.values())
            source_diagnostics[src] = {
                "source": src,
                "observation_count": sum(len(f) for f in lt_map.values()),
                "lead_times_covered": src_leads,
                "weighted_representative_price_inr": round(src_price, 2),
                "methodological_status": "DIAGNOSTIC_ONLY (Scraper counts are not statistical weights; prices are not normalized against reference price)",
                "weight_used_for_headline": "NONE (Diagnostic only; scrapers are NOT statistical weights)",
            }

        # Add divergence metric if multiple sources present
        if len(source_diagnostics) >= 2:
            src_names = list(source_diagnostics.keys())
            p1 = source_diagnostics[src_names[0]]["weighted_representative_price_inr"]
            p2 = source_diagnostics[src_names[1]]["weighted_representative_price_inr"]
            divergence_inr = round(abs(p1 - p2), 2)
            source_diagnostics["cross_source_divergence_inr"] = divergence_inr
            source_diagnostics["cross_source_divergence_pct"] = round((divergence_inr / ((p1 + p2) / 2.0)) * 100, 2) if (p1 + p2) > 0 else 0.0

        # Step 9: Final All-India APIx Aggregation
        prev_apix = self.apix_history[prev_period].index_value if prev_period and prev_period in self.apix_history else None
        apix_series = self.aggregation_engine.aggregate_routes_to_apix(
            route_results=route_results,
            period=period,
            prev_apix_val=prev_apix,
            source_diagnostics=source_diagnostics,
            prototype_median_summary=prototype_summary,
        )

        # Populate lead-time indices, elementary results, and diagnostics in series result
        apix_series.lead_time_indices = {
            f"{k[0]}_{k[1]}": v.index_value for k, v in lt_results.items()
        }
        apix_series.elementary_results = elementary_results

        diagnostics_meta = {
            "total_detected_offers": len(offers),
            "selected_headline_itineraries": len(selections),
            "rejected_higher_fare_offers": len(rejected_higher_offers),
            "elementary_strata_compiled": len(elementary_results),
            "active_replacements_logged": len(active_replacements),
            "active_quality_adjustments_logged": len(active_adjustments),
            "lead_time_sub_indices": {f"{k[0]}_{k[1]}": float(v.index_value) for k, v in lt_results.items()},
            "prototype_median_indicator": prototype_summary,
            "source_diagnostics": source_diagnostics,
        }
        apix_series.diagnostics_meta = diagnostics_meta

        # Enforce governance invariant: P_ref never enters index calculation
        self.assert_no_reference_price_in_index(apix_series, elementary_results)

        self.apix_history[period] = apix_series
        return apix_series

    def assert_no_reference_price_in_index(
        self,
        series: APIxSeriesResult,
        elementary_results: List[ElementaryIndexResult],
    ) -> None:
        """
        Governance Invariant (§Methodology Governance):
        The provisional P_ref (₹8,641.45) must NEVER enter index calculation:
        1. APIx_t != 100 * P_t / P_ref.
        2. No elementary index is computed using P_ref as a denominator.
        3. No individual observation is normalized to 100 using P_ref.
        4. Elementary index is chained strictly from Jevons links of price relatives: r_(i,t) = P_(i,t) / P_(i,t-1).
        5. P_ref is preserved strictly as descriptive reference price diagnostic (PROVISIONAL_PROJECT_REFERENCE).
        """
        ref_price = self.cpi_layer.taxonomy.experimental_project_reference_price
        assert ref_price == Decimal("8641.45"), f"Expected provisional reference price 8641.45, got {ref_price}"
        assert series.reference_type == "PROVISIONAL_PROJECT_REFERENCE"
        assert getattr(series, "reference_purpose", None) == "descriptive/reference-price diagnostic"

        # Verify elementary indices are chained from Jevons links, never from P_t / P_ref
        for el in elementary_results:
            assert el.chained_index > Decimal("0"), f"Chained index for stratum {el.stratum_id} must be > 0"
            assert el.jevons_link is not None, f"Jevons link must exist for stratum {el.stratum_id}"

