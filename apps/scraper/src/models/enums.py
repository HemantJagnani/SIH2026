"""
Enums for the India Airfare Price Index pipeline.

Defined per spec §12 (Collection status), §13 (FareObservation fields),
§40 (Collection lifecycle), and §6 (Collection mode).

All enums are string-based for JSON serialization compatibility with
PostgreSQL and Pydantic models.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# §12 – Collection Status
# Every collection job must result in one of these explicit statuses.
# Do not turn every failure into price = NULL.
# ---------------------------------------------------------------------------

class CollectionStatus(str, Enum):
    """
    Explicit outcome status for every collection job attempt.
    Source: spec §12.
    """
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    SOLD_OUT = "SOLD_OUT"
    NOT_FOUND = "NOT_FOUND"
    SOURCE_ERROR = "SOURCE_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    CAPTCHA_PRESENT = "CAPTCHA_PRESENT"
    PARSER_ERROR = "PARSER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# ---------------------------------------------------------------------------
# §6 – Collection Mode
# How data was collected from the source.
# ---------------------------------------------------------------------------

class CollectionMode(str, Enum):
    """
    Mechanism used to collect data from a source.
    Source: spec §6.
    """
    API = "API"
    HTTP = "HTTP"
    BROWSER = "BROWSER"


# ---------------------------------------------------------------------------
# §6 / §13 – Trip Type
# ---------------------------------------------------------------------------

class TripType(str, Enum):
    """
    One-way or round-trip itinerary type.
    Source: spec §6, §13.
    """
    ONE_WAY = "ONE_WAY"
    ROUND_TRIP = "ROUND_TRIP"


# ---------------------------------------------------------------------------
# §13 – Cabin Class
# ---------------------------------------------------------------------------

class CabinClass(str, Enum):
    """
    Cabin class of the fare offer.
    Source: spec §13.
    """
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# §13 – Availability Status
# IMPORTANT: Never interpret SOLD_OUT as zero price.
# ---------------------------------------------------------------------------

class AvailabilityStatus(str, Enum):
    """
    Seat availability status for a given fare observation.
    Source: spec §13.

    WARNING: SOLD_OUT is not the same as price=0. Never equate the two.
    """
    AVAILABLE = "AVAILABLE"
    SOLD_OUT = "SOLD_OUT"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# §40 – Collection Job Lifecycle Status
# Full happy path AND failure paths are represented.
# ---------------------------------------------------------------------------

class JobLifecycleStatus(str, Enum):
    """
    Lifecycle state of a collection job, from creation to publication.
    Source: spec §40.

    Happy path:
        CREATED → QUEUED → RUNNING → SOURCE_RESPONSE → EXTRACTED
        → NORMALIZED → VALIDATED → QUALITY_CHECKED → PUBLISHED

    Failure paths:
        RUNNING → FAILED | RESTRICTED | TIMEOUT
        EXTRACTED → NORMALIZATION_EXCEPTION → AI_FALLBACK
                 → RESOLVED | QUARANTINED
    """
    # Happy path
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SOURCE_RESPONSE = "SOURCE_RESPONSE"
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    VALIDATED = "VALIDATED"
    QUALITY_CHECKED = "QUALITY_CHECKED"
    PUBLISHED = "PUBLISHED"

    # Runtime failure paths
    FAILED = "FAILED"
    RESTRICTED = "RESTRICTED"
    TIMEOUT = "TIMEOUT"

    # Normalization / AI exception paths
    NORMALIZATION_EXCEPTION = "NORMALIZATION_EXCEPTION"
    AI_FALLBACK = "AI_FALLBACK"
    RESOLVED = "RESOLVED"
    QUARANTINED = "QUARANTINED"
