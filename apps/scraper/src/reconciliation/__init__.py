"""
APIx Cross-Source Fare Reconciliation Package.
"""

from .models import (
    APIxProductObservation,
    CanonicalOffer,
    MatchStatus,
    PriceSemantics,
    RawSourceObservation,
)
from .registry import SourceConfig, SourceRegistry
from .adapters import (
    BaseReconciliationAdapter,
    EaseMyTripReconciliationAdapter,
    GoogleFlightsReconciliationAdapter,
    IxigoReconciliationAdapter,
)
from .engine import CrossSourceReconciliationEngine, ReconciliationDiagnostics
from .pipeline import CrossSourceReconciliationPipeline
from .fingerprint import (
    compute_canonical_offer_fingerprint,
    compute_itinerary_fingerprint,
    compute_offer_fingerprint,
    normalize_flight_number,
    normalize_time_str,
)

from .policy import (
    INTERNATIONAL_CARRIERS,
    HIGHER_FARE_FAMILY_KEYWORDS,
    is_foreign_transit_carrier,
    is_higher_fare_family,
)

__all__ = [
    "APIxProductObservation",
    "CanonicalOffer",
    "MatchStatus",
    "PriceSemantics",
    "RawSourceObservation",
    "SourceConfig",
    "SourceRegistry",
    "BaseReconciliationAdapter",
    "GoogleFlightsReconciliationAdapter",
    "EaseMyTripReconciliationAdapter",
    "IxigoReconciliationAdapter",
    "CrossSourceReconciliationEngine",
    "ReconciliationDiagnostics",
    "CrossSourceReconciliationPipeline",
    "compute_canonical_offer_fingerprint",
    "compute_itinerary_fingerprint",
    "compute_offer_fingerprint",
    "normalize_flight_number",
    "normalize_time_str",
    "INTERNATIONAL_CARRIERS",
    "HIGHER_FARE_FAMILY_KEYWORDS",
    "is_foreign_transit_carrier",
    "is_higher_fare_family",
]
