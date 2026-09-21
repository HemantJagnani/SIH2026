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
from .observation import FareObservation
from .raw_observation import RawObservation
from .request import FareSearchRequest, PassengerCount
from .result import CollectionResult
from .version import SCHEMA_VERSION

__all__ = [
    # Enums
    "AvailabilityStatus",
    "CabinClass",
    "CollectionMode",
    "CollectionStatus",
    "JobLifecycleStatus",
    "TripType",
    # Models
    "FareObservation",
    "RawObservation",
    "FareSearchRequest",
    "PassengerCount",
    "CollectionResult",
    # Constants
    "SCHEMA_VERSION",
]
