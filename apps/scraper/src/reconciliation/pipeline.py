"""
Cross-Source Fare Reconciliation Pipeline for APIx.
Orchestrates the complete flow per §14 of the APIx Cross-Source Specification:
Raw Source Observations
        ↓
Source Normalization
        ↓
Canonical Offer Reconciliation
        ↓
Same-product Deduplication
        ↓
APIx Product Definition
        ↓
Comparable Baseline Observation
        ↓
Price Formation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .adapters import (
    BaseReconciliationAdapter,
    EaseMyTripReconciliationAdapter,
    GoogleFlightsReconciliationAdapter,
    IxigoReconciliationAdapter,
)
from .engine import CrossSourceReconciliationEngine, ReconciliationDiagnostics
from .models import (
    APIxProductObservation,
    CanonicalOffer,
    MatchStatus,
    PriceSemantics,
    RawSourceObservation,
)
from .registry import SourceRegistry

logger = logging.getLogger(__name__)

FOREIGN_CARRIERS = {
    "Kuwait Airways", "Emirates", "Etihad", "SriLankan", "Oman Air",
    "KUWAIT AIRWAYS", "EMIRATES", "ETIHAD", "SRILANKAN", "OMAN AIR"
}


class CrossSourceReconciliationPipeline:
    """
    End-to-end pipeline orchestrating source-agnostic multi-channel fare reconciliation.
    """

    def __init__(self, registry: Optional[SourceRegistry] = None):
        self.registry = registry or SourceRegistry.get_registry()
        self.engine = CrossSourceReconciliationEngine(registry=self.registry)
        
        # Instantiate adapters for registered sources
        self._adapter_instances: Dict[str, BaseReconciliationAdapter] = {
            "google_flights": GoogleFlightsReconciliationAdapter(),
            "easemytrip": EaseMyTripReconciliationAdapter(),
            "ixigo": IxigoReconciliationAdapter(),
        }

    def register_adapter(self, adapter: BaseReconciliationAdapter) -> None:
        """Register a custom or future source adapter dynamically."""
        self._adapter_instances[adapter.source_id.lower()] = adapter

    def normalize_batch(
        self,
        raw_items: Sequence[Dict[str, Any] | RawSourceObservation]
    ) -> List[CanonicalOffer]:
        """
        Pass 1: Source Normalization.
        Uses registered adapters to convert native source records into CanonicalOffer objects.
        """
        normalized_offers: List[CanonicalOffer] = []

        for item in raw_items:
            src = item.source if isinstance(item, RawSourceObservation) else item.get("source", "unknown")
            adapter = self._adapter_instances.get(src.lower())
            
            if not adapter:
                logger.warning(f"No adapter registered for source '{src}'. Skipping item.")
                continue
                
            try:
                can_offer = adapter.normalize(item)
                normalized_offers.append(can_offer)
            except Exception as e:
                logger.error(f"Error normalizing item from {src}: {e}", exc_info=True)

        return normalized_offers

    def run(
        self,
        raw_items: Sequence[Dict[str, Any] | RawSourceObservation]
    ) -> Tuple[List[APIxProductObservation], List[CanonicalOffer], ReconciliationDiagnostics]:
        """
        Executes full pipeline:
        1. Normalization
        2. Cross-Source Reconciliation & Deduplication
        3. APIx Product Comparability Assessment
        
        Returns:
            Tuple of:
            - List of APIxProductObservation (valid comparable baseline fares)
            - List of CanonicalOffer (excluded / review offers, e.g. price conflicts, foreign transit)
            - ReconciliationDiagnostics (telemetry and audit counts)
        """
        # Step 1: Normalize
        normalized_offers = self.normalize_batch(raw_items)

        # Step 2: Cross-Source Reconciliation & Same-Product Deduplication
        reconciled_offers, diagnostics = self.engine.reconcile(normalized_offers)

        # Step 3: APIx Product Comparability Assessment (§14)
        valid_apix_observations: List[APIxProductObservation] = []
        excluded_offers: List[CanonicalOffer] = []

        for offer in reconciled_offers:
            # Check 1: Foreign Transit Carrier (Cabotage Violation)
            if offer.airline.upper() in FOREIGN_CARRIERS:
                offer.match_status = MatchStatus.NO_MATCH
                excluded_offers.append(offer)
                continue

            # Check 2: Price Conflict Review
            if offer.match_status == MatchStatus.PRICE_CONFLICT_REVIEW or offer.price_conflict:
                excluded_offers.append(offer)
                continue

            # Check 3: Insufficient Data or Missing Mandatory Total Price
            if offer.match_status == MatchStatus.INSUFFICIENT_DATA or offer.total_fare is None or offer.total_fare <= 0:
                excluded_offers.append(offer)
                continue

            # Check 4: Price Semantics Compatibility
            if offer.price_semantics not in (PriceSemantics.DISPLAYED_TOTAL, PriceSemantics.DISPLAYED_FARE):
                excluded_offers.append(offer)
                continue

            # Check 5: Cabin Class Invariance
            if offer.cabin.upper() != "ECONOMY":
                excluded_offers.append(offer)
                continue

            # Qualifying comparable baseline observation
            apix_obs = APIxProductObservation(
                canonical_offer_id=offer.canonical_offer_id,
                route=offer.route,
                origin=offer.origin,
                destination=offer.destination,
                travel_date=offer.travel_date,
                lead_time=offer.lead_time,
                airline=offer.airline,
                flight_number=offer.flight_number,
                departure_time=offer.departure_time,
                arrival_time=offer.arrival_time,
                stops=offer.stops,
                cabin=offer.cabin,
                fare_family=offer.fare_family,
                baggage=offer.baggage,
                refundability=offer.refundability,
                total_fare=offer.total_fare,
                currency=offer.currency,
                is_comparable_baseline=True,
                sources_contributing=offer.source_names,
                price_by_source=offer.price_by_source,
                field_provenance=offer.field_provenance,
                match_status=offer.match_status,
            )
            valid_apix_observations.append(apix_obs)

        return valid_apix_observations, excluded_offers, diagnostics
