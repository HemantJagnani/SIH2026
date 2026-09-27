"""
Cross-Source Fare Reconciliation Engine for APIx.
Implements §5, §6, §7, §8, §10, §12, and §13 of the APIx Cross-Source Specification.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
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
        self.missing_fields_by_source: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

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
            "missing_fields_by_source": {k: dict(v) for k, v in self.missing_fields_by_source.items()},
        }


class CrossSourceReconciliationEngine:
    """
    Deterministic cross-source reconciliation engine.
    Converts multi-source observations into canonical offers without hardcoded source branches.
    """

    def __init__(self, registry: Optional[SourceRegistry] = None):
        self.registry = registry or SourceRegistry.get_registry()

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
        4. Detect price conflicts without averaging or silent selection (§7).
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
        # Group by (source, canonical_offer_fingerprint, total_fare)
        unique_source_offers: List[CanonicalOffer] = []
        seen_source_fingerprints: Set[Tuple[str, str, Optional[Decimal]]] = set()

        for o in offers:
            key = (o.source, o.canonical_offer_fingerprint, o.total_fare)
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
        # (route, travel_date, airline_normalized, flight_number_normalized, departure_time_normalized, stops, cabin, fare_family_normalized)
        def build_match_key(o: CanonicalOffer) -> Tuple[Any, ...]:
            norm_fn = normalize_flight_number(o.flight_number)
            norm_dep = normalize_time_str(o.departure_time)
            # Group fare family: standard/saver are considered the baseline tier across sources
            fam = o.fare_family.upper()
            base_tier = (
                "BASELINE_SAVER"
                if any(k in fam for k in ["SAVER", "VALUE", "STANDARD", "SPICESAVER", "NOT_PROVIDED", "UNKNOWN"])
                else fam
            )
            return (
                o.route.upper(),
                o.travel_date,
                normalize_flight_number(o.airline),  # normalize carrier name
                norm_fn,
                norm_dep,
                o.stops,
                o.cabin.upper(),
                base_tier,
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
                    diag.unmatched_observations += 1
                    diag.canonical_offers_by_source[item.source] += 1
                    final_canonical_offers.append(item)
                continue

            # Check price semantics compatibility (§11)
            semantics_set = set(o.price_semantics for o in group)
            if any(s in (PriceSemantics.UNKNOWN_PRICE_DEFINITION, PriceSemantics.DISPLAYED_FROM) for s in semantics_set):
                # Price semantics incompatible or uncertain
                for item in group:
                    item.match_status = MatchStatus.PROBABLE_MATCH
                    item.match_confidence = 0.5
                    item.reconciliation_timestamp = now_utc
                    diag.probable_matches += 1
                    diag.canonical_offers_by_source[item.source] += 1
                    final_canonical_offers.append(item)
                continue

            # Check prices across sources (§7)
            price_map: Dict[str, Decimal] = {}
            for item in group:
                if item.total_fare is not None:
                    price_map[item.source] = item.total_fare

            unique_prices = set(price_map.values())
            has_price_conflict = len(unique_prices) > 1

            if has_price_conflict:
                diag.price_conflicts += 1
                match_status = MatchStatus.PRICE_CONFLICT_REVIEW
                match_confidence = 0.8
            else:
                diag.exact_cross_source_matches += 1
                match_status = MatchStatus.EXACT_MATCH
                match_confidence = 1.0

            # Merge information, NOT observations (§6)
            merged_offer = self._merge_canonical_offers(group, match_status, match_confidence, price_map, has_price_conflict, now_utc)
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
        has_price_conflict: bool,
        reconciled_at: datetime,
    ) -> CanonicalOffer:
        """Merges multiple source offers of the exact same product into a single CanonicalOffer."""
        # Base representation from first offer
        base = offers[0]
        
        all_source_obs_ids: List[str] = []
        all_sources: List[str] = []
        merged_provenance: Dict[str, str] = {}
        
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
            all_source_obs_ids.extend(o.source_observation_ids)
            for s in o.source_names:
                if s not in all_sources:
                    all_sources.append(s)
            
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

        # If price conflict: do NOT average and do NOT silently pick. Total fare = None or first if exact match
        if has_price_conflict:
            canonical_fare = None
        else:
            canonical_fare = base.total_fare

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
            source_count=len(all_sources),
            match_status=match_status,
            match_confidence=match_confidence,
            field_provenance=merged_provenance,
            price_by_source=price_map,
            price_conflict=has_price_conflict,
            reconciliation_timestamp=reconciled_at,
            itinerary_fingerprint=base.itinerary_fingerprint,
            offer_fingerprint=base.offer_fingerprint,
            canonical_offer_fingerprint=base.canonical_offer_fingerprint,
        )
