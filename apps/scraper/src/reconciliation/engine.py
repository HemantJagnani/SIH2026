"""
Cross-Source Fare Reconciliation Engine for APIx.
Implements §5, §6, §7, §8, §10, §12, and §13 of the APIx Cross-Source Specification.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .fingerprint import (
    compute_canonical_offer_fingerprint,
    compute_itinerary_fingerprint,
    normalize_flight_number,
    normalize_time_str,
)
from .models import (
    CanonicalOffer,
    MatchStatus,
    PriceSemantics,
    RawSourceObservation,
)
from .registry import SourceRegistry

logger = logging.getLogger(__name__)


class ReconciliationDiagnostics:
    """Detailed audit metrics and diagnostic counts per §13."""
    def __init__(self):
        self.observations_by_source: Dict[str, int] = defaultdict(int)
        self.duplicates_by_source: Dict[str, int] = defaultdict(int)
        self.canonical_offers_by_source: Dict[str, int] = defaultdict(int)
        self.exact_cross_source_matches: int = 0
        self.probable_matches: int = 0
        self.unmatched_observations: int = 0
        self.insufficient_data_observations: int = 0
        self.price_conflicts: int = 0
        self.price_variances_aggregated: int = 0
        self.unresolved_conflicts: int = 0
        self.foreign_transit_exclusions: int = 0
        self.higher_fare_family_exclusions: int = 0
        self.missing_fields_by_source: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def merge(self, other: "ReconciliationDiagnostics") -> None:
        """Merges telemetry metrics from another stratum's diagnostics."""
        for k, v in other.observations_by_source.items():
            self.observations_by_source[k] += v
        for k, v in other.duplicates_by_source.items():
            self.duplicates_by_source[k] += v
        for k, v in other.canonical_offers_by_source.items():
            self.canonical_offers_by_source[k] += v
        self.exact_cross_source_matches += other.exact_cross_source_matches
        self.probable_matches += other.probable_matches
        self.unmatched_observations += other.unmatched_observations
        self.insufficient_data_observations += other.insufficient_data_observations
        self.price_conflicts += other.price_conflicts
        self.price_variances_aggregated += other.price_variances_aggregated
        self.unresolved_conflicts += other.unresolved_conflicts
        self.foreign_transit_exclusions += other.foreign_transit_exclusions
        self.higher_fare_family_exclusions += other.higher_fare_family_exclusions
        for src, fields in other.missing_fields_by_source.items():
            for f, cnt in fields.items():
                self.missing_fields_by_source[src][f] += cnt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observations_by_source": dict(self.observations_by_source),
            "duplicates_by_source": dict(self.duplicates_by_source),
            "canonical_offers_by_source": dict(self.canonical_offers_by_source),
            "exact_cross_source_matches": self.exact_cross_source_matches,
            "probable_matches": self.probable_matches,
            "unmatched_observations": self.unmatched_observations,
            "insufficient_data_observations": self.insufficient_data_observations,
            "price_conflicts": self.price_conflicts,
            "price_variances_aggregated": self.price_variances_aggregated,
            "unresolved_conflicts": self.unresolved_conflicts,
            "foreign_transit_exclusions": self.foreign_transit_exclusions,
            "higher_fare_family_exclusions": self.higher_fare_family_exclusions,
            "missing_fields_by_source": {k: dict(v) for k, v in self.missing_fields_by_source.items()},
        }


class CrossSourceReconciliationEngine:
    """
    Deterministic cross-source reconciliation engine.
    Converts multi-source observations into canonical offers without hardcoded source branches.
    """

    def __init__(self, registry: Optional[SourceRegistry] = None, price_tolerance: Decimal = Decimal("1.00")):
        self.registry = registry or SourceRegistry.get_registry()
        self.price_tolerance = price_tolerance

    def reconcile(
        self,
        offers: Sequence[CanonicalOffer],
    ) -> Tuple[List[CanonicalOffer], ReconciliationDiagnostics]:
        """
        Executes cross-source reconciliation on a sequence of normalized CanonicalOffer items.
        
        Steps:
        1. Track diagnostics and missing fields.
        2. Deduplicate same-source duplicates (§10A).
        3. Match cross-source offers on primary dimensions (§5).
        4. Detect price variance & aggregate valid comparable source prices using arithmetic mean (§7).
        5. Merge field depth with complete provenance (§6).
        6. Return unified canonical offers with complete lineage (§12).
        """
        diag = ReconciliationDiagnostics()
        now_utc = datetime.now(timezone.utc)

        # ── 1. Telemetry and Missing Fields Tracking ──
        for o in offers:
            src = o.source
            diag.observations_by_source[src] += 1
            
            for field_name in ["arrival_time", "fare_family", "baggage", "refundability"]:
                val = getattr(o, field_name, None)
                if val in (None, "UNKNOWN", "NOT_PROVIDED"):
                    diag.missing_fields_by_source[src][field_name] += 1

        # ── 2. Same-Source Deduplication (§10A) ──
        # Group by (source, stratum, canonical_offer_fingerprint, total_fare)
        # Stratum (route, lead_time) guarantees independent sampling strata are protected
        unique_source_offers: List[CanonicalOffer] = []
        seen_source_fingerprints: Set[Tuple[str, Tuple[str, str], str, Optional[Decimal]]] = set()

        for o in offers:
            stratum = ((o.route or "").upper(), (o.lead_time or "T+0").upper())
            key = (o.source, stratum, o.canonical_offer_fingerprint, o.total_fare)
            if key in seen_source_fingerprints:
                diag.duplicates_by_source[o.source] += 1
                continue
            seen_source_fingerprints.add(key)
            unique_source_offers.append(o)

        # ── 3. Check for Insufficient Identifying Data (§5) ──
        valid_for_matching: List[CanonicalOffer] = []
        final_canonical_offers: List[CanonicalOffer] = []

        for o in unique_source_offers:
            if (
                not o.flight_number
                or o.flight_number in ("UNKNOWN", "UNKNOWN_FLIGHT")
                or not o.travel_date
                or not o.route
            ):
                o.match_status = MatchStatus.INSUFFICIENT_DATA
                o.match_confidence = 0.0
                diag.insufficient_data_observations += 1
                diag.canonical_offers_by_source[o.source] += 1
                final_canonical_offers.append(o)
            else:
                valid_for_matching.append(o)

        # ── 4. Cross-Source Matching (§5, §6, §7, §8) ──
        # Primary matching key:
        # (route, travel_date, airline_normalized, flight_number_normalized, departure_time_normalized, stops, cabin, fare_family_normalized, baggage_tier, passenger_type)
        def build_match_key(o: CanonicalOffer) -> Tuple[Any, ...]:
            norm_fn = normalize_flight_number(o.flight_number)
            norm_dep = normalize_time_str(o.departure_time)
            # Group fare family: standard/saver are considered the baseline tier across sources
            fam = (o.fare_family or "").upper()
            base_tier = (
                "BASELINE_SAVER"
                if any(k in fam for k in ["SAVER", "VALUE", "STANDARD", "SPICESAVER", "NOT_PROVIDED", "UNKNOWN"])
                else fam
            )
            bag_tier = f"{o.checkin_baggage_kg}KG" if o.checkin_baggage_kg and o.checkin_baggage_kg > 15 else "STD_BAGGAGE"
            return (
                o.route.upper(),
                (o.lead_time or "T+0").upper(),
                o.travel_date,
                normalize_flight_number(o.airline),  # normalize carrier name
                norm_fn,
                norm_dep,
                o.stops,
                o.cabin.upper(),
                base_tier,
                bag_tier,
                o.passenger_type.upper(),
            )

        match_groups: Dict[Tuple[Any, ...], List[CanonicalOffer]] = defaultdict(list)
        for o in valid_for_matching:
            match_groups[build_match_key(o)].append(o)

        for match_key, group in match_groups.items():
            if len(group) == 1:
                # Unmatched single source offer
                single = group[0]
                single.match_status = MatchStatus.NO_MATCH
                single.match_confidence = 1.0
                single.reconciliation_timestamp = now_utc
                single.aggregation_method = "SINGLE_SOURCE"
                single.aggregation_source_count = 1
                single.source_count = 1
                diag.unmatched_observations += 1
                diag.canonical_offers_by_source[single.source] += 1
                final_canonical_offers.append(single)
                continue

            # Group has multiple offers across sources: check if from distinct sources
            sources_in_group = set(o.source for o in group)
            
            # If all from the same source (e.g. different fare families that mapped to same base), keep separate
            if len(sources_in_group) == 1:
                for item in group:
                    item.match_status = MatchStatus.NO_MATCH
                    item.reconciliation_timestamp = now_utc
                    item.aggregation_method = "SINGLE_SOURCE"
                    item.aggregation_source_count = 1
                    item.source_count = 1
                    diag.unmatched_observations += 1
                    diag.canonical_offers_by_source[item.source] += 1
                    final_canonical_offers.append(item)
                continue

            # Check price semantics compatibility (§11)
            semantics_set = set(o.price_semantics for o in group)
            incompatible_semantics = (
                any(s in (PriceSemantics.UNKNOWN_PRICE_DEFINITION, PriceSemantics.DISPLAYED_FROM) for s in semantics_set)
                or len(semantics_set) > 1
            )
            if incompatible_semantics:
                # Price semantics incompatible or uncertain: do not average
                for item in group:
                    item.match_status = MatchStatus.PRICE_CONFLICT_UNRESOLVED
                    item.match_confidence = 0.5
                    item.reconciliation_timestamp = now_utc
                    diag.probable_matches += 1
                    diag.unresolved_conflicts += 1
                    diag.canonical_offers_by_source[item.source] += 1
                    final_canonical_offers.append(item)
                continue

            # Check prices across sources (§7)
            # Collect one price per source (same-source DOM duplicates deduplicated in step 2)
            price_map: Dict[str, Decimal] = {}
            for item in group:
                if item.total_fare is not None and item.total_fare > 0:
                    if item.source not in price_map:
                        price_map[item.source] = item.total_fare

            valid_prices = list(price_map.values())
            if not valid_prices:
                for item in group:
                    item.match_status = MatchStatus.INSUFFICIENT_DATA
                    diag.insufficient_data_observations += 1
                    diag.canonical_offers_by_source[item.source] += 1
                    final_canonical_offers.append(item)
                continue

            price_delta = max(valid_prices) - min(valid_prices)
            has_price_variance = price_delta > self.price_tolerance

            if has_price_variance:
                diag.price_conflicts += 1
                diag.price_variances_aggregated += 1
                match_status = MatchStatus.PRICE_VARIANCE_AGGREGATED
                match_confidence = 0.95
            else:
                diag.exact_cross_source_matches += 1
                match_status = MatchStatus.PRICE_CONSISTENT
                match_confidence = 1.0

            # Merge information and aggregate source prices via arithmetic mean (§6, §7)
            merged_offer = self._merge_canonical_offers(
                group, match_status, match_confidence, price_map, has_price_variance, now_utc
            )
            for src in sources_in_group:
                diag.canonical_offers_by_source[src] += 1
            final_canonical_offers.append(merged_offer)

        return final_canonical_offers, diag

    def _merge_canonical_offers(
        self,
        offers: List[CanonicalOffer],
        match_status: MatchStatus,
        match_confidence: float,
        price_map: Dict[str, Decimal],
        has_price_variance: bool,
        reconciled_at: datetime,
    ) -> CanonicalOffer:
        """Merges multiple source offers of the exact same product into a single CanonicalOffer."""
        # Base representation from first offer
        base = offers[0]
        
        all_source_obs_ids: List[str] = []
        all_sources: List[str] = []
        merged_provenance: Dict[str, str] = {}
        source_timestamps: Dict[str, str] = {}
        
        # Best fields from any source with richer data
        best_arrival = base.arrival_time
        best_fare_family = base.fare_family
        best_baggage = base.baggage
        best_cb_kg = base.cabin_baggage_kg
        best_ci_kg = base.checkin_baggage_kg
        best_refund = base.refundability
        best_change = base.changeability
        best_duration = base.duration_minutes

        for o in offers:
            for oid in o.source_observation_ids:
                if oid not in all_source_obs_ids:
                    all_source_obs_ids.append(oid)
            for s in o.source_names:
                if s not in all_sources:
                    all_sources.append(s)
            
            if o.source and o.source not in source_timestamps:
                ts_str = o.search_timestamp.isoformat() if hasattr(o.search_timestamp, "isoformat") else str(o.search_timestamp)
                source_timestamps[o.source] = ts_str
            
            # Merge richer arrival time
            if best_arrival in ("UNKNOWN", "NOT_PROVIDED") and o.arrival_time not in ("UNKNOWN", "NOT_PROVIDED"):
                best_arrival = o.arrival_time
                merged_provenance["arrival_time"] = o.source
                
            # Merge richer fare family
            if best_fare_family in ("STANDARD", "UNKNOWN", "NOT_PROVIDED") and o.fare_family not in ("STANDARD", "UNKNOWN", "NOT_PROVIDED"):
                best_fare_family = o.fare_family
                merged_provenance["fare_family"] = o.source
                
            # Merge richer baggage
            if best_baggage in ("NOT_PROVIDED", "UNKNOWN") and o.baggage not in ("NOT_PROVIDED", "UNKNOWN"):
                best_baggage = o.baggage
                best_cb_kg = o.cabin_baggage_kg
                best_ci_kg = o.checkin_baggage_kg
                merged_provenance["baggage"] = o.source
                
            # Merge richer refundability
            if best_refund in ("UNKNOWN", "NOT_PROVIDED") and o.refundability not in ("UNKNOWN", "NOT_PROVIDED"):
                best_refund = o.refundability
                merged_provenance["refundability"] = o.source

            # Copy existing provenance
            for k, v in o.field_provenance.items():
                if k not in merged_provenance:
                    merged_provenance[k] = v

        # Calculate canonical fare: arithmetic mean of all valid source prices
        valid_prices = [p for p in price_map.values() if p is not None and p > 0]
        if len(valid_prices) > 1:
            mean_fare = sum(valid_prices) / Decimal(str(len(valid_prices)))
            canonical_fare = mean_fare.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            aggregation_method = "ARITHMETIC_MEAN"
            aggregation_source_count = len(valid_prices)
        elif len(valid_prices) == 1:
            canonical_fare = valid_prices[0]
            aggregation_method = "SINGLE_SOURCE"
            aggregation_source_count = 1
        else:
            canonical_fare = None
            aggregation_method = "NO_VALID_PRICE"
            aggregation_source_count = 0

        return CanonicalOffer(
            canonical_offer_id=f"can_reconciled_{base.flight_number}_{base.departure_time.replace(':', '')}_{len(all_sources)}src",
            route=base.route,
            origin=base.origin,
            destination=base.destination,
            travel_date=base.travel_date,
            search_timestamp=base.search_timestamp,
            lead_time=base.lead_time,
            airline=base.airline,
            airline_code=base.airline_code,
            flight_number=base.flight_number,
            departure_time=base.departure_time,
            arrival_time=best_arrival,
            duration_minutes=best_duration,
            stops=base.stops,
            cabin=base.cabin,
            fare_family=best_fare_family,
            baggage=best_baggage,
            cabin_baggage_kg=best_cb_kg,
            checkin_baggage_kg=best_ci_kg,
            refundability=best_refund,
            changeability=best_change,
            passenger_type=base.passenger_type,
            total_fare=canonical_fare,
            currency=base.currency,
            price_semantics=base.price_semantics,
            source=",".join(all_sources),
            source_observation_ids=all_source_obs_ids,
            source_names=all_sources,
            source_ids=all_sources,
            source_count=len(all_sources),
            match_status=match_status,
            match_confidence=match_confidence,
            field_provenance=merged_provenance,
            price_by_source=price_map,
            source_prices=price_map,
            source_timestamps=source_timestamps,
            aggregation_method=aggregation_method,
            aggregation_source_count=aggregation_source_count,
            price_conflict=False,
            reconciliation_timestamp=reconciled_at,
            itinerary_fingerprint=base.itinerary_fingerprint,
            offer_fingerprint=base.offer_fingerprint,
            canonical_offer_fingerprint=base.canonical_offer_fingerprint,
        )
