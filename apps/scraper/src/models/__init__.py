"""
Public re-exports for the models package.

Import from here in the rest of the codebase:

    from models import FareSearchRequest, FareObservation, CollectionResult
    from models import CollectionStatus, CabinClass, TripType
"""

from .enums import (
    AvailabilityStatus,
    CabinClass,
    CollectionMode,
    CollectionStatus,
    JobLifecycleStatus,
    TripType,
)
from .observation import FareObservation, FlightSegment
from .raw_observation import RawObservation
from .request import FareSearchRequest, PassengerCount
from .result import CollectionResult
from .version import SCHEMA_VERSION

from .canonical import (
    RawFareObservation,
    NormalizedFareObservation,
    ProductStratum,
    classify_travel_day_type,
    classify_departure_time_band,
    classify_lead_time_class,
    classify_stop_category,
)
from .fingerprint import (
    compute_itinerary_fingerprint,
    compute_offer_fingerprint,
)

from .provenance import (
    FieldStatus,
    MissingReason,
    ExtractionMode,
    FieldProvenance,
)
from .itinerary import (
    Itinerary,
    FlightSegment,
    FareOffer,
    PriceStatus,
)
from .enrichment import (
    EnrichmentType,
    EnrichmentStatus,
    EnrichmentTask,
    EnrichmentPolicy,
    MAX_ENRICHMENT_ATTEMPTS,
)

__all__ = [
    # Enums
    "AvailabilityStatus",
    "CabinClass",
    "CollectionMode",
    "CollectionStatus",
    "JobLifecycleStatus",
    "TripType",
    "FieldStatus",
    "MissingReason",
    "ExtractionMode",
    "PriceStatus",
    "EnrichmentType",
    "EnrichmentStatus",
    # Models
    "FareObservation",
    "FlightSegment",
    "Itinerary",
    "FareOffer",
    "FieldProvenance",
    "EnrichmentTask",
    "EnrichmentPolicy",
    "RawObservation",
    "RawFareObservation",
    "NormalizedFareObservation",
    "ProductStratum",
    "FareSearchRequest",
    "PassengerCount",
    "CollectionResult",
    # Fingerprints & Classifiers
    "compute_itinerary_fingerprint",
    "compute_offer_fingerprint",
    "classify_travel_day_type",
    "classify_departure_time_band",
    "classify_lead_time_class",
    "classify_stop_category",
    # Constants
    "SCHEMA_VERSION",
    "MAX_ENRICHMENT_ATTEMPTS",
]

